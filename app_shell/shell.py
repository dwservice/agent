# -*- coding: utf-8 -*-

'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''

import threading
import errno
import os
import sys
import struct
import signal
import time
import utils
import subprocess
import io
import agent
import json
import native


try:
    from .os_win_pyconpty import conpty
except Exception as ex:
    None

try:
    import termios
    import pty
    import fcntl
    import select    
except:
    None

SHELL_TIMEOUT_CONNECTION = 40; #Seconds
SHELL_TIMEOUT_RECOVERY = 20; #Seconds
SHELL_VERSION = 1

# Poll only while cleaning up a child. There is no idle periodic worker.
SHELL_PROCESS_TERM_GRACE = 0.5
SHELL_PROCESS_KILL_GRACE = 0.5
SHELL_PROCESS_REAP_INTERVAL = 1.0


def _shell_process_exited(pid):
    try:
        waited, status = os.waitpid(pid, os.WNOHANG)
        return waited == pid
    except OSError as ex:
        if ex.errno == errno.ECHILD:
            return True
        if ex.errno == errno.EINTR:
            return False
        raise


def _wait_shell_process(pid, grace):
    deadline = time.monotonic() + grace
    while True:
        if _shell_process_exited(pid):
            return True
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False
        time.sleep(min(0.05, remaining))


def _stop_shell_foreground(pid, pio):
    # Signal only the foreground job of this still-open, owned PTY. Root
    # shells need explicit job cleanup too; terminal hangup alone is not
    # sufficient in every launch context. Never signal our own group.
    if pid < 1 or pio is None:
        return
    try:
        group = os.tcgetpgrp(pio)
        if group <= 1 or group == os.getpgrp():
            return
        if os.getsid(group) != pid:
            return
        os.killpg(group, signal.SIGTERM)
        deadline = time.monotonic() + SHELL_PROCESS_TERM_GRACE
        while os.tcgetpgrp(pio) == group:
            try:
                os.killpg(group, 0)
            except OSError as ex:
                if ex.errno == errno.ESRCH:
                    return
                raise
            if time.monotonic() >= deadline:
                # Recheck terminal ownership after the grace period, so a
                # foreground change cannot make us signal a stale group.
                if os.tcgetpgrp(pio) == group:
                    os.killpg(group, signal.SIGKILL)
                return
            time.sleep(0.05)
    except OSError:
        # No foreground group yet, job already gone or PTY already hung up.
        # Continue the bounded cleanup of the directly owned shell process.
        return


class ShellProcessReaper:
    """One lazy worker per Agent, shared across shell app reloads.

    Only this registry owns deferred child PIDs. It never sends signals and
    never uses a blocking waitpid. It exits as soon as the registry is empty.
    """
    def __init__(self, agent_main):
        self._agent_main = agent_main
        self._condition = threading.Condition()
        self._pending = set()
        self._thread = None

    def add(self, pid):
        with self._condition:
            self._pending.add(pid)
            if self._thread is None:
                self._thread = threading.Thread(target=self._run, name="ShellProcessReaper")
                self._thread.daemon = True
                self._thread.start()

    def _run(self):
        while True:
            with self._condition:
                if not self._pending:
                    self._thread = None
                    return
                pending = list(self._pending)
            for pid in pending:
                try:
                    if _shell_process_exited(pid):
                        with self._condition:
                            self._pending.discard(pid)
                except OSError:
                    # Keep ownership and retry; the initial deferral was logged.
                    pass
            with self._condition:
                if self._pending:
                    self._condition.wait(SHELL_PROCESS_REAP_INTERVAL)


class Shell():
    
    def __init__(self, agent_main):
        self._agent_main=agent_main
        self._list = {}
        self._list_semaphore = threading.Condition()
        # App construction is serialized by Agent.get_app. Retain the registry
        # on the Agent so an app reload cannot create one reaper per generation.
        if not hasattr(agent_main, '_shell_process_reaper'):
            agent_main._shell_process_reaper = ShellProcessReaper(agent_main)
        self._process_reaper = agent_main._shell_process_reaper
    
    def destroy(self,bforce):
        if not bforce:
            self._list_semaphore.acquire()
            try:
                if len(self._list)>0:
                    return False
            finally:
                self._list_semaphore.release()            
        return True
    
    def on_conn_close(self, idses):
        self._list_semaphore.acquire()
        lstcopy=None
        try:
            lstcopy=self._list.copy()
        finally:
            self._list_semaphore.release()
        
        for k in lstcopy.keys():
            sm = lstcopy[k]
            if sm.get_idses()==idses:
                try:
                    sm.terminate()
                except Exception as e:
                    self._agent_main.write_except(e,"AppShell:: on_conn_close terminate error:")
        
    
    def has_permission(self,cinfo):
        return self._agent_main.has_app_permission(cinfo,"shell"); 
    
    def _add_shell_manager(self, cinfo, wsock):
        itm = None
        self._list_semaphore.acquire()
        sid = None
        try:
            #CHECK FOR RECOVERY SESSION
            for k in self._list.keys():
                sm = self._list[k]
                if sm._cinfo==cinfo and sm.recovery(wsock):
                    return sm
                    
            #CREATE NEW
            while True:
                sid = agent.generate_key(10) 
                if sid not in self._list:
                    itm = ShellManager(self, cinfo, sid, wsock)
                    self._list[sid]=itm
                    break
        finally:
            self._list_semaphore.release()
        itm.start()
        return itm
    
    def _rem_shell_manager(self, sid):
        self._list_semaphore.acquire()
        try:
            if sid in self._list:
                del self._list[sid]
        finally:
            self._list_semaphore.release()    
    
    
    def req_websocket(self, cinfo, wsock):
        self._add_shell_manager(cinfo ,wsock)


class ShellManager(threading.Thread):
    
    def __init__(self, shlmain, cinfo, sid,  wsock):
        threading.Thread.__init__(self,  name="ShellManager")
        self._shlmain=shlmain
        self._cinfo=cinfo        
        self._idses = cinfo.get_idsession()
        self._id=sid        
        self._bclose=False        
        self._semaphore = threading.Condition()
        self._shell_list = {}
        self._timeout_counter=utils.Counter()
        self._recovery_supported = False
        self._recovery = False
        self._send_info = False        
        self._accept_websocket(wsock)
    
    def _accept_websocket(self,wsock):
        self._prop=wsock.get_properties()                
        self._websocket=wsock
        self._websocket.accept(10,{"on_close": self._on_close,"on_data":self._on_data})
    
    def _decode_data(self,data):        
        return utils.bytes_to_str(data,"utf8")
        
    def get_id(self):
        return self._id
    
    def get_idses(self):
        return self._idses
    
    def _is_user_match(self, word, n, pattern, m):
        if m == len(pattern):
            return n == len(word)
        if n == len(word):
            for i in range(m, len(pattern)):
                if pattern[i] != '*':
                    return False
     
            return True
        if pattern[m] == '?' or pattern[m] == word[n]:
            return self._is_user_match(word, n + 1, pattern, m + 1)
        if pattern[m] == '*':
            return self._is_user_match(word, n + 1, pattern, m) or self._is_user_match(word, n, pattern, m + 1)
        return False
 
    def _is_user_matching(self, word, pattern):
        return self._is_user_match(word, 0, pattern, 0)
    
    def is_user_allowed(self, u):
        try:
            uaw = self._shlmain._agent_main.get_config("shell.users_allowed",None)
            if uaw is not None:
                for itm in uaw:
                    if agent.is_windows():
                        if self._is_user_matching(u.lower(),itm["name"].lower()):
                            return itm["enable"]
                    else:                     
                        if self._is_user_matching(u,itm["name"]):
                            return itm["enable"]
                return False
            return True
        except Exception as ex:
            self._shlmain._agent_main.write_except(ex,"AppShell:: shell manager " + self._id + ":")
        return False
    
    def _on_data(self,websocket,tpdata,data):
        self._semaphore.acquire()
        try:
            if not self._bclose:
                try:
                    self._timeout_counter.reset()
                    
                    if tpdata == ord('s'):
                        prprequest = json.loads(data)
                    else:  #OLD TO REMOVE 19/12/2022
                        prprequest = json.loads(self._decode_data(data))
                    
                    if prprequest["type"]=="open" or prprequest["type"]==0: #28 04 23 NUMBERIC IS FOR COMPATIBILITY
                        sid=prprequest["id"]
                        if sid in self._shell_list:
                            shl=self._shell_list[sid]
                            shl.terminate()
                            del self._shell_list[sid]
                        if agent.is_windows():
                            shl = Windows(self, sid, prprequest["cols"], prprequest["rows"])
                        else:
                            shl = LinuxMac(self, sid, prprequest["cols"], prprequest["rows"])
                        shl.initialize()
                        self._shell_list[sid]=shl
                        self._semaphore.notifyAll()
                    elif prprequest["type"]=="close" or prprequest["type"]==1: #28 04 23 NUMBERIC IS FOR COMPATIBILITY
                        sid=prprequest["id"]
                        if sid in self._shell_list:
                            shl=self._shell_list[sid]
                            shl.terminate()
                            del self._shell_list[sid]
                            self._semaphore.notifyAll()
                    elif prprequest["type"]=="inputs" or prprequest["type"]==2: #28 04 23 NUMBERIC IS FOR COMPATIBILITY
                        sid=prprequest["id"]
                        if sid in self._shell_list:
                            shl=self._shell_list[sid]
                            sdata=prprequest["data"]
                            shl.write_inputs(sdata)
                            self._semaphore.notifyAll()
                    elif prprequest["type"]=="change_rows_cols" or prprequest["type"]==3: #28 04 23 NUMBERIC IS FOR COMPATIBILITY
                        sid=prprequest["id"]
                        if sid in self._shell_list:
                            shl=self._shell_list[sid]
                            rows=prprequest["rows"]
                            cols=prprequest["cols"]
                            shl.change_rows_cols(rows,cols)
                            self._semaphore.notifyAll()
                    elif prprequest["type"]=="init":
                        self._recovery_supported=True
                        self._send_info=True
                    elif prprequest["type"]=="term":
                        self._bclose=True
                    elif prprequest["type"]=="keepalive":
                        None
                except Exception as ex:
                    self._bclose=True
                    self._shlmain._agent_main.write_except(ex,"AppShell:: shell manager " + self._id + ":")
        finally:
            self._semaphore.release()
            
    def run(self):
        try:            
            self._semaphore.acquire()
            try:
                self._timeout_counter.reset()
                bwait=False
                while not self._bclose:
                    if bwait:
                        self._semaphore.wait(0.2)
                    bwait=True
                    tm=SHELL_TIMEOUT_CONNECTION
                    if self._recovery:
                        tm=SHELL_TIMEOUT_RECOVERY
                    if self._timeout_counter.is_elapsed(tm):
                        self._bclose=True
                        if self._recovery_supported and not self._recovery:
                            snd = {}
                            snd["type"]="info"
                            snd["version"]=SHELL_VERSION
                            snd["ids"]=[]
                            appsend = json.dumps(snd)
                            self._websocket.send_string(appsend)
                    elif not self._recovery:
                        if self._send_info:
                            self._send_info=False
                            snd = {}
                            snd["type"]="info"
                            snd["version"]=SHELL_VERSION
                            snd["ids"]=[]
                            for idx in self._shell_list:
                                snd["ids"].append(idx)
                            appsend = json.dumps(snd)
                            self._websocket.send_string(appsend)
                        arrem=[]
                        for idx in self._shell_list:
                            try:
                                #apptm=int(time.time() * 1000)                                
                                upd=self._shell_list[idx].read_update()
                                if upd is not None and len(upd)>0:
                                    bwait=False
                                    snd = {}
                                    snd["type"]="data"
                                    snd["id"]=idx
                                    snd["data"]=upd
                                    appsend = json.dumps(snd)
                                    self._websocket.send_string(appsend)
                                    '''print("*****************************************************************************\n")
                                    print("*****************************************************************************\n")
                                    print("*****************************************************************************\n")
                                    print("*****************************************************************************\n")
                                    print("SEND: len:" + str(len(appsend)) + "  time:" + str(int(time.time() * 1000)-apptm) + "\n")'''
                                if self._shell_list[idx].is_terminate():
                                    raise Exception("Process terminated.")
                            except Exception:
                                er=utils.get_exception()
                                try:
                                    snd = {}
                                    snd["type"]="data"
                                    snd["id"]=idx
                                    snd["terminate"]=True
                                    snd["data"]="\r\n" + str(er)
                                    appsend = json.dumps(snd)
                                    self._websocket.send_string(appsend)
                                except:
                                    None
                                if not self._shell_list[idx].is_terminate():
                                    self._shlmain._agent_main.write_except(er, "Error in shell(" + self._id + "): ")
                                arrem.append(idx)
                        for idx in arrem:
                            if idx in self._shell_list:
                                shl=self._shell_list[idx]
                                shl.terminate()
                                del self._shell_list[idx]                            
            finally:
                self._semaphore.release()
        except Exception as e:
            self.terminate()
            self._shlmain._agent_main.write_except(e,"AppShell:: shell manager error " + self._id + ":")        
        self._destroy()
    
    def _on_close(self):
        if self._recovery_supported:
            #WAIT RECOVERY
            self._semaphore.acquire()
            try:
                if not self._bclose:
                    self._timeout_counter.reset()
                    self._recovery=True        
            finally:
                self._semaphore.release()
        else:            
            self.terminate()        
    
    def recovery(self,wsock):
        bret=False
        self._semaphore.acquire()
        try:
            if not self._bclose and self._recovery:
                self._timeout_counter.reset()
                self._recovery=False
                self._accept_websocket(wsock)                                
                bret=True
        finally:
            self._semaphore.release()
        return bret

    def terminate(self):
        self._semaphore.acquire()
        try:
            self._bclose=True
        finally:
            self._semaphore.release()
    
    def _destroy(self):
        if self._id is not None:
            for idx in self._shell_list:
                try:
                    self._shell_list[idx].terminate()
                except:
                    self._shlmain._agent_main.write_err("AppShell:: shell manager error " + self._id + " in terminate shell(" + str(idx) + ")")
            self._shell_list = []
            if self._websocket is not None:
                self._websocket.close()
                self._websocket = None
            if self._id is not None:
                self._shlmain._rem_shell_manager(self._id)
            self._id=None
    
    def is_close(self):
        ret = True
        self._semaphore.acquire()
        try:
            ret=self._bclose
        finally:
            self._semaphore.release()
        return ret

class LoginRequest():
    
    def __init__(self, prt):
        self._parent=prt
        self._wait_counter=None
        self._clear()  

    def _clear(self):
        self._key="user"
        self._val=""
        self._user=None
        self._password=None
        self._pos=0
        self._soutput="\x1B[2J\x1B[HUser: "
    
    def read_update(self):
        if self._key=="complete":
            return None
        if self._key=="waitAndClear":
            if self._wait_counter.is_elapsed(3):
                self._wait_counter=None
                self._clear()
            else:
                return None
        s=self._soutput
        self._soutput=None
        if self._key=="loginIncorrect" and self._wait_counter.is_elapsed(1):            
            self._key="waitAndClear" 
            s="\r\nLogin incorrect"            
        if self._key=="openSession":
            self._key="complete"
            self._parent.open_session(self._user,self._password)
        return s
    
    def _append_to_output(self,c):
        if self._soutput is None:
            self._soutput=c
        else:
            self._soutput+=c
    
    def _write_inputs_char_size(self, s):
        p=0
        for c in s:
            p+=1
            if self._key=="user" and ord(c)>=11904:
                p+=1
        return p
    
    def write_inputs(self,c):
        if ord(c[0])==27:
            if self._key=="user":
                sep=c[1:]
                if sep=="[D": #LEFT
                    if self._pos>0:
                        psz = self._write_inputs_char_size(self._val[self._pos-1:self._pos])
                        self._append_to_output("\x1b[" + str(psz) + "D")
                        self._pos-=1
                elif sep=="[C": #RIGHT
                    if self._pos<len(self._val):
                        psz = self._write_inputs_char_size(self._val[self._pos:self._pos+1])
                        self._append_to_output("\x1b[" + str(psz) + "C")                        
                        self._pos+=1
                elif sep=="[H": #START
                    if self._pos>0:
                        psz = self._write_inputs_char_size(self._val[:self._pos])
                        self._append_to_output("\x1b[" + str(psz) + "D")
                        self._pos=0
                elif sep=="[F": #END
                    if self._pos<len(self._val):
                        psz = self._write_inputs_char_size(self._val[self._pos:])
                        self._append_to_output("\x1b[" + str(psz) + "C")
                        self._pos=len(self._val)
                elif sep=="[3~": #CANC
                    if self._pos<len(self._val):
                        lpart=self._val[0:self._pos]
                        rpart=self._val[self._pos+1:]
                        self._val=lpart+rpart
                        self._append_to_output("\x1b[K"+rpart)
                        rl = self._write_inputs_char_size(rpart)
                        if rl>0:
                            self._append_to_output("\x1b[" + str(rl) + "D")
            return
            
        for sc in c:
            if ord(sc)==27:
                return
            elif ord(sc)==13: #ENTER
                if self._key=="user" and len(self._val)>0:
                    self._user=self._val
                    self._key="password"
                    self._val=""
                    self._pos=0
                    self._soutput="\r\nPassword: "
                elif self._key=="password":
                    self._password=self._val
                    if self._parent.check_login(self._user,self._password):
                        self._soutput="\x1B[2J\x1B[H"
                        self._key="openSession"
                    else:
                        self._key="loginIncorrect"
                        self._soutput="\r\n"
                        self._wait_counter=utils.Counter()
            elif ord(sc)==127: #BACK SPACE
                if self._pos>0 and len(self._val)>0:
                    psz = self._write_inputs_char_size(self._val[self._pos-1:self._pos])                    
                    lpart=self._val[0:self._pos-1]
                    rpart=self._val[self._pos:]
                    self._val=lpart+rpart  
                    self._pos-=1                    
                    self._append_to_output("\x1b[" + str(psz) + "D\x1b[K"+rpart)
                    rl = self._write_inputs_char_size(rpart)
                    if rl>0:
                        self._append_to_output("\x1b[" + str(rl) + "D")
            elif ord(sc)>=32: #CHARACTER
                cv=sc
                if self._key=="password":
                    cv="*"
                lpart=self._val[0:self._pos]
                rpart=self._val[self._pos:]
                self._val=lpart + sc + rpart
                self._pos+=1
                self._append_to_output("\x1b[K"+cv+rpart)                
                rl = self._write_inputs_char_size(rpart)
                if rl>0:
                    self._append_to_output("\x1b[" + str(rl) + "D")
    
class LinuxMac():
    
    def __init__(self, mgr, sid, col, row):
        self._manager=mgr
        self._id=sid
        self._cols=col
        self._rows=row
        self._bterm = False
        self._semaphore = threading.Condition()
        self._rwenc="utf8"
        self._login_request=None
        self._ppid=-1
        self._pio=None
        self._reader=None
        self._writer=None
        self._libcrypt=None
        self._cleanup_started=False
        self._activity_registered=False
    
    def get_id(self):
        return self._id
        
    def _init_check_login(self):
        import pwd
        if agent.is_linux():
            try:
                import crypt
            except Exception as e:
                import ctypes
                import ctypes.util
                lib_name = ctypes.util.find_library("crypt") or ctypes.util.find_library("c")
                if lib_name is None:
                    raise("Library crypt not found.")
                self._libcrypt = ctypes.CDLL(lib_name)
                self._libcrypt.crypt.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
                self._libcrypt.crypt.restype = ctypes.c_char_p
    
    def initialize(self):
        try:
            bauth = self._manager._shlmain._agent_main.get_config('shell.enable_authentication', False)
            if bauth and os.getuid()==0:
                try:
                    self._init_check_login()
                except Exception as e:
                    self._manager._shlmain._agent_main.write_except(e,"AppShell:: missing python module pwd or crypt")
                    self.terminate()
                    return
                self._login_request = LoginRequest(self)
            else:
                self.open_session(None,None)
        except:
            self.terminate()
        
    def check_login(self,u,p):
        if self._manager.is_user_allowed(u):
            if agent.is_mac():
                return self._check_login_mac(u,p)
            else:
                return self._check_login_linux(u,p)
        return False        
    
    def _check_login_linux_password(self, p, phash):
        if self._libcrypt is not None:
            pw_bytes = p.encode("utf-8")
            salt_bytes = phash.encode("utf-8")
        
            res = self._libcrypt.crypt(pw_bytes, salt_bytes)
            if res is None:
                raise RuntimeError("crypt return null.")
            return res.decode("utf-8")==phash
        else:
            import crypt
            return crypt.crypt(p, phash)==phash
    
    def _check_login_linux(self,u,p):        
        try:
            phash = None
            if utils.path_exists("/etc/shadow"):
                with utils.file_open("/etc/shadow", "r") as sfile:
                    scontents = sfile.readlines()                
                for line in scontents:
                    if u in line:
                        sentry = line.strip().split(":")
                        phash = sentry[1]
            else:
                try:
                    import pwd
                    uinfo = pwd.getpwnam(u)
                    if uinfo is not None:
                        phash=uinfo.pw_passwd
                except:
                    None                    
            if phash is not None:
                return self._check_login_linux_password(p, phash)
            return False
        except:
            e = utils.get_exception()
            self._manager._shlmain._agent_main.write_except(e)            
        return False
    
    def _check_login_mac(self,u,p):
        try:
            cmd = ["/usr/bin/dscl", ".", "auth", u, p]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()            
            return process.returncode == 0         
        except:
            e = utils.get_exception()
            self._manager._shlmain._agent_main.write_except(e)            
        return False
    
    
    ##### TO REMOVE 20/08/2022 (moved into native); 15/03/2023 TODO FORM MAC AS WELL
    def _getutf8lang(self):
        altret=None
        try:
            p = subprocess.Popen("locale | grep LANG=", stdout=subprocess.PIPE, shell=True)
            (po, pe) = p.communicate()
            p.wait()
            if len(po) > 0:
                po = utils.bytes_to_str(po, "utf8")
                ar = po.split("\n")[0].split("=")[1].split(".")
                if ar[1].upper()=="UTF8" or ar[1].upper()=="UTF-8":
                    if ar[0].upper()=="C":
                        altret = ar[0] + "." + ar[1]
                    else:
                        return ar[0] + "." + ar[1]
        except:
            None        
        try:                
            p = subprocess.Popen("locale -a", stdout=subprocess.PIPE, shell=True)
            (po, pe) = p.communicate()
            p.wait()
            if len(po) > 0:
                po = utils.bytes_to_str(po, "utf8")
                arlines = po.split("\n")
                for r in arlines:
                    ar = r.split(".")
                    if len(ar)>1 and ar[0].upper()=="EN_US" and (ar[1].upper()=="UTF8" or ar[1].upper()=="UTF-8"):
                        if ar[0].upper()=="C":
                            altret = ar[0] + "." + ar[1]
                        else:
                            return ar[0] + "." + ar[1]
                #If not found get the first utf8
                for r in arlines:
                    ar = r.split(".")
                    if len(ar)>1 and (ar[1].upper()=="UTF8" or ar[1].upper()=="UTF-8"):
                        if ar[0].upper()=="C":
                            altret = ar[0] + "." + ar[1]
                        else:
                            return ar[0] + "." + ar[1]
        except:
            None
        return altret
    ##### TO REMOVE 20/08/2022 (moved into native)
    
    def open_session(self,u,p):
        try:
            ppid, pio = pty.fork()
            if ppid == 0: #Child process
                try:
                    stdin = 0
                    stdout = 1
                    stderr = 2
                    attrs = termios.tcgetattr(stdout)
                    iflag, oflag, cflag, lflag, ispeed, ospeed, cc = attrs
                    if 'IUTF8' in termios.__dict__:
                        iflag |= (termios.IXON | termios.IXOFF | termios.__dict__['IUTF8'])
                    else:
                        iflag |= (termios.IXON | termios.IXOFF | 0x40000)                
                    oflag |= (termios.OPOST | termios.ONLCR | termios.INLCR)
                    attrs = [iflag, oflag, cflag, lflag, ispeed, ospeed, cc]
                    termios.tcsetattr(stdout, termios.TCSANOW, attrs)
                    attrs = termios.tcgetattr(stdin)
                    iflag, oflag, cflag, lflag, ispeed, ospeed, cc = attrs
                    if 'IUTF8' in termios.__dict__:
                        iflag |= (termios.IXON | termios.IXOFF | termios.__dict__['IUTF8'])
                    else:
                        iflag |= (termios.IXON | termios.IXOFF | 0x40000)
                    oflag |= (termios.OPOST | termios.ONLCR | termios.INLCR)
                    attrs = [iflag, oflag, cflag, lflag, ispeed, ospeed, cc]
                    termios.tcsetattr(stdin, termios.TCSANOW, attrs)
                    os.dup2(stderr, stdout)
                    uid=None
                    udir=None
                    upshell=None
                    try:
                        import pwd
                        if u is None:
                            uinfo = pwd.getpwuid(os.getuid())
                        else:
                            uinfo = pwd.getpwnam(u)
                        uid=uinfo.pw_uid
                        udir=uinfo.pw_dir
                        upshell=uinfo.pw_shell
                    except:
                        None
                    if uid is None:
                        uid=os.getuid()
                    if udir is None:
                        udir="/"            
                    if upshell is None or not utils.path_exists(upshell):
                        upshell="/bin/bash"
                        if not utils.path_exists(upshell):
                            upshell="/bin/zsh"
                        if not utils.path_exists(upshell):
                            upshell="/bin/tcsh"
                        if not utils.path_exists(upshell):
                            upshell="/bin/csh"
                        if not utils.path_exists(upshell):
                            upshell="/bin/ksh"
                        if not utils.path_exists(upshell):
                            upshell="/bin/dash"
                        if not utils.path_exists(upshell):
                            upshell="/bin/ash"
                        if not utils.path_exists(upshell):
                            upshell="/bin/sh"

                    os.setuid(uid)
                    os.chdir(udir)
                    env = {}
                    env["TERM"] = "xterm"
                    env["SHELL"] = upshell
                    env["HOME"] = udir
                    env["PATH"] = os.environ['PATH']
                    applng=os.environ.get('LANG')
                    if applng is not None:
                        if not (applng.upper().endswith(".UTF8") or applng.upper().endswith(".UTF-8")):
                            applng=None
                    if applng is None:
                        ##### TO FIX 20/08/2022
                        if hasattr(native.get_instance(), "get_utf8_lang"):
                            applng = native.get_instance().get_utf8_lang()
                        else:
                            applng = self._getutf8lang()
                        ##### TO FIX 20/08/2022
                    if applng is not None:
                        env["LANG"] = applng
                    env["PYTHONIOENCODING"] = "utf_8"
                    arapp = upshell.split("/")
                    nargv=[arapp[len(arapp)-1]]
                    if upshell=="/bin/bash" or upshell=="/bin/zsh" or upshell=="/bin/sh" or upshell=="/bin/tcsh" or upshell=="/bin/csh" or upshell=="/bin/dash":
                        nargv.append("-l")
                    os.execvpe(upshell, nargv, env)
                    os._exit(0)
                except:
                    os._exit(1)

            # Take ownership before operations that can fail.
            self._ppid = ppid
            self._pio = pio
            fl = fcntl.fcntl(sys.stdin, fcntl.F_GETFL)
            fcntl.fcntl(pio, fcntl.F_SETFL, fl | os.O_NONBLOCK)
            fcntl.ioctl(pio, termios.TIOCSWINSZ, struct.pack("hhhh", self._rows, self._cols, 0, 0))
            self._ppid = ppid
            self._pio = pio
            self._reader = io.open(pio, 'rb', closefd=False)
            self._writer = io.open(pio, 'wb', closefd=False)
            try:
                self._manager._cinfo.inc_activities_value("shellSession")
                self._activity_registered=True
            except:
                None
            self._login_request = None
        except:
            self.terminate()

    def _processIsAlive(self):
        with self._semaphore:
            if self._cleanup_started or self._ppid < 0:
                return False
            try:
                if _shell_process_exited(self._ppid):
                    self._ppid = -1
                    return False
                return True
            except OSError:
                # Let terminate retain ownership and retry cleanup on an OS error.
                return True

    def terminate(self):
        with self._semaphore:
            if self._cleanup_started:
                return
            self._cleanup_started = True
            self._login_request = None
            self._bterm = True
            pid, pio = self._ppid, self._pio
            reader, writer = self._reader, self._writer
            registered = self._activity_registered
            self._ppid, self._pio = -1, None
            self._reader, self._writer = None, None
            self._activity_registered = False
        _stop_shell_foreground(pid, pio)
        if registered:
            try:
                self._manager._cinfo.dec_activities_value("shellSession")
            except:
                self._manager._shlmain._agent_main.write_except(utils.get_exception())
        # io.open(..., closefd=False) does not close the PTY master. Close it
        # explicitly too, releasing the terminal and hanging up foreground jobs.
        for stream in (reader, writer):
            if stream is not None:
                try:
                    stream.close()
                except:
                    pass
        if pio is not None:
            try:
                os.close(pio)
            except OSError:
                pass
        if pid < 0:
            return
        reaped = False
        try:
            reaped = _shell_process_exited(pid)
            if not reaped:
                try:
                    os.kill(pid, signal.SIGTERM)
                except OSError as ex:
                    if ex.errno != errno.ESRCH:
                        raise
                reaped = _wait_shell_process(pid, SHELL_PROCESS_TERM_GRACE)
            if not reaped:
                try:
                    os.kill(pid, signal.SIGKILL)
                except OSError as ex:
                    if ex.errno != errno.ESRCH:
                        raise
                reaped = _wait_shell_process(pid, SHELL_PROCESS_KILL_GRACE)
        except OSError:
            self._manager._shlmain._agent_main.write_except(utils.get_exception())
        finally:
            if not reaped:
                self._manager._shlmain._process_reaper.add(pid)
                self._manager._shlmain._agent_main.write_err(
                    "AppShell:: process %s not reaped within cleanup grace; deferring collection" % pid)
        
    def is_terminate(self):
        if self._login_request is not None:
            return False
        if not self._processIsAlive():
            self._bterm=True
            return True
        return self._bterm
    
    def change_rows_cols(self, rows, cols):
        if self._bterm == True:
            return        
        if self._login_request is not None:
            return
        try:
            fcntl.ioctl(self._pio, termios.TIOCSWINSZ, struct.pack("hhhh", rows, cols, 0, 0))
        except:
            self.terminate() 
        
    def write_inputs(self, c):        
        if self._bterm==True:
            return        
        try:
            if self._login_request is not None:
                return self._login_request.write_inputs(c)
            self._writer.write(utils.str_to_bytes(c,self._rwenc))
            self._writer.flush()
        except:
            self._writer=None #MAC fix exit
            self.terminate() 

    def read_update(self):
        if self._bterm==True:
            return None
        try:
            if self._login_request is not None:
                return self._login_request.read_update()
        
        
            #inpSet = [ self._pio ]
            #inpReady, outReady, errReady = select.select(inpSet, [], [], 0)
            #if self._pio in inpReady:
            #reader = io.open(self._pio, 'rb', closefd=False,buffering=1024)
            #output=reader.read(self._rows*self._cols*16)
            #output=reader.read(128)
            #reader.close()
            #output=self._reader.read(self._rows*self._cols)
            s = self._reader.read()
            if s is not None:
                return utils.bytes_to_str(s,self._rwenc)
            else:
                return s
        except:
            self.terminate()

class Windows():

    def __init__(self, mgr, sid, col, row):
        self._manager=mgr
        self._id = sid
        self._col = col
        self._row = row
        self._bterm = False
        self._semaphore = threading.Condition()
        self._cmd = u"cmd.exe"
        #self._cmd = u"powershell.exe -NonInteractive"
        self._pty = None
        self._rwenc="utf8"
        self._login_request=None

    def _write_err(self,m):
        self._manager._shlmain._agent_main.write_err("AppShell:: " + m)

    def _write_debug(self,m):
        self._manager._shlmain._agent_main.write_debug("AppShell:: " + m)

    def get_id(self):
        return self._id

    def initialize(self):
        bauth = self._manager._shlmain._agent_main.get_config('shell.enable_authentication', False)            
        if bauth and conpty.is_run_as_service():
            self._login_request = LoginRequest(self)
        else:
            self.open_session(None,None)

    def check_login(self,u,p):
        if self._manager.is_user_allowed(u):
            try:
                return conpty.check_login(u,p)
            except:
                return False
        return False

    def open_session(self,u,p):
        try:
            self._pty = conpty.ConPty(self._cmd, u, p, self._col, self._row, self._write_err)
            self._pty.open()        
            try:
                self._manager._cinfo.inc_activities_value("shellSession")
            except:
                None
            self._login_request=None
        except:
            self.terminate()

    def terminate(self):
        try:
            self._manager._cinfo.dec_activities_value("shellSession")
        except:
            None
        try:
            self._bterm = True
            self._pty.close()
        except:
            None

    def is_terminate(self):
        return self._bterm

    def write_inputs(self, c):
        if self._bterm == True:
            return
        try:
            if self._login_request is not None:
                return self._login_request.write_inputs(c)
            
            if c == '\r':
                c = '\r\n'
            if self._pty.get_status()=="OPEN":
                self._pty.write(c)
        except:
            self.terminate()       

    def read_update(self):
        if self._bterm==True:
            return None
        try:
            if self._login_request is not None:
                return self._login_request.read_update()
                    
            if self._pty.get_status()!="INIT" and self._pty.get_status()!="OPEN":
                raise Exception("")                
            bt = self._pty.read()
            if bt is not None and len(bt)>0:
                return utils.bytes_to_str(bt, self._rwenc)            
            else:
                return bt
        except:
            self.terminate()        
        
    def change_rows_cols(self, rows, cols):
        if self._bterm == True:
            return
        try:
            self._pty.resize(rows, cols)
        except:
            self.terminate() 
    

