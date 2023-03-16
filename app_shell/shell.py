# -*- coding: utf-8 -*-

'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''

import threading
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
    import pwd
    import crypt
    import termios
    import pty
    import fcntl
    import select    
except:
    None

SHELL_INTERVALL_TIMEOUT = 45; #Seconds

class Shell():
    
    def __init__(self, agent_main):
        self._agent_main=agent_main
        self._list = {}
        self._list_semaphore = threading.Condition()
    
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
                    self._agent_main.write_except(e,"AppShell:: on_conn_close error:")
            
    
    def has_permission(self,cinfo):
        return self._agent_main.has_app_permission(cinfo,"shell"); 
    
    def _add_shell_manager(self, cinfo, wsock):
        itm = None
        self._list_semaphore.acquire()
        key = None
        try:
            while True:
                key = agent.generate_key(10) 
                if key not in self._list:
                    itm = ShellManager(self, cinfo, key, wsock)
                    self._list[key]=itm
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
    
    REQ_TYPE_INITIALIZE=0
    REQ_TYPE_TERMINATE=1
    REQ_TYPE_INPUTS=2
    REQ_TYPE_CHANGE_ROWS_COLS=3
    
    def __init__(self, shlmain, cinfo, sid,  wsock):
        threading.Thread.__init__(self,  name="ShellManager")
        self._shlmain=shlmain
        self._cinfo=cinfo
        self._prop=wsock.get_properties()
        self._idses = cinfo.get_idsession()
        self._id=sid        
        self._bclose=False
        self._websocket=wsock
        self._semaphore = threading.Condition()
        self._shell_list = {}
        self._websocket.accept(10,{"on_close": self._on_close,"on_data":self._on_data})
                
    def _decode_data(self,data):        
        return utils.bytes_to_str(data,"utf8")
        
    def get_id(self):
        return self._id
    
    def get_idses(self):
        return self._idses
    
    def _on_data(self,websocket,tpdata,data):
        self._semaphore.acquire()
        try:
            if not self._bclose:
                try:
                    self._timeout_cnt=0;
                    self._last_timeout=int(time.time() * 1000)
                    
                    if tpdata == ord('s'):
                        prprequest = json.loads(data)
                    else:  #OLD TO REMOVE 19/12/2022
                        prprequest = json.loads(self._decode_data(data))
                    
                    if prprequest["type"]==ShellManager.REQ_TYPE_INITIALIZE:
                        sid=prprequest["id"]
                        if agent.is_windows():
                            shl = Windows(self, sid, prprequest["cols"], prprequest["rows"])
                        else:
                            shl = LinuxMac(self, sid, prprequest["cols"], prprequest["rows"])
                        shl.initialize()
                        self._shell_list[sid]=shl
                        self._semaphore.notifyAll()
                    elif prprequest["type"]==ShellManager.REQ_TYPE_TERMINATE:
                        sid=prprequest["id"]
                        if sid in self._shell_list:
                            shl=self._shell_list[sid]
                            shl.terminate()
                            del self._shell_list[sid]
                            self._semaphore.notifyAll()
                    elif prprequest["type"]==ShellManager.REQ_TYPE_INPUTS:
                        sid=prprequest["id"]
                        if sid in self._shell_list:
                            shl=self._shell_list[sid]
                            sdata=prprequest["data"]
                            shl.write_inputs(sdata)
                            self._semaphore.notifyAll()
                    elif prprequest["type"]==ShellManager.REQ_TYPE_CHANGE_ROWS_COLS:
                        sid=prprequest["id"]
                        if sid in self._shell_list:
                            shl=self._shell_list[sid]
                            rows=prprequest["rows"]
                            cols=prprequest["cols"]
                            shl.change_rows_cols(rows,cols)
                            self._semaphore.notifyAll()
                    elif prprequest["type"]=="alive":
                        None
                except Exception as ex:
                    self._bclose=True
                    self._shlmain._agent_main.write_except(ex,"AppShell:: shell manager " + self._id + ":")
        finally:
            self._semaphore.release()
        
    
    def run(self):
        self._timeout_cnt=0;
        self._last_timeout=int(time.time() * 1000)
        try:            
            self._semaphore.acquire()
            try:
                bwait=False
                while not self._bclose:
                    if bwait:
                        self._semaphore.wait(0.2)
                    bwait=True
                    elapsed=int(time.time() * 1000)-self._last_timeout
                    if elapsed<0:
                        self._last_timeout=int(time.time() * 1000)
                    elif elapsed>1000:
                        self._timeout_cnt+=1;
                        self._last_timeout=int(time.time() * 1000)
                    if self._timeout_cnt>=SHELL_INTERVALL_TIMEOUT:
                        self.terminate()
                    else:                        
                        arrem=[]
                        for idx in self._shell_list:
                            try:                                
                                #apptm=int(time.time() * 1000)                                
                                upd=self._shell_list[idx].read_update()
                                if upd is not None and len(upd)>0:
                                    bwait=False
                                    snd = {}
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
                                    snd["id"]=idx
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
        self._destroy();
    
    def _on_close(self):
        self.terminate();
    
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
    
    def write_inputs(self,c):
        if self._key=="loginIncorrect" or self._key=="waitAndClear" or self._key=="openSession" or self._key=="complete":
            return
        if len(c)==1:
            if ord(c)==13:
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
            elif ord(c)>=32:
                if ord(c)==127:
                    if self._pos>0 and len(self._val)>0:
                        lpart=self._val[0:self._pos-1]
                        rpart=self._val[self._pos:]
                        self._val=lpart+rpart  
                        self._pos-=1
                        self._append_to_output("\x1b[1D\x1b[K"+rpart)
                        rl = len(rpart)
                        if rl>0:
                            self._append_to_output("\x1b[" + str(rl) + "D")
                else:
                    cv=c
                    if self._key=="password":
                        cv="*"
                    lpart=self._val[0:self._pos]
                    rpart=self._val[self._pos:]
                    self._val=lpart + c + rpart
                    self._pos+=1
                    self._append_to_output("\x1b[K"+cv+rpart)
                    rl = len(rpart)
                    if rl>0:
                        self._append_to_output("\x1b[" + str(rl) + "D")
        elif self._key=="user" and ord(c[0])==27:
            sep=c[1:]
            if sep=="[D": #LEFT
                if self._pos>0:
                    self._append_to_output(c)
                    self._pos-=1                    
            elif sep=="[C": #RIGHT
                if self._pos<len(self._val):
                    self._append_to_output(c)
                    self._pos+=1
            elif sep=="[H": #START
                if self._pos>0:
                    self._append_to_output("\x1b[" + str(self._pos) + "D")
                    self._pos=0
            elif sep=="[F": #END
                if self._pos<len(self._val):
                    self._append_to_output("\x1b[" + str(len(self._val)-self._pos) + "C")
                    self._pos=len(self._val)
            elif sep=="[3~": #CANC
                if self._pos<len(self._val):
                    lpart=self._val[0:self._pos]
                    rpart=self._val[self._pos+1:]
                    self._val=lpart+rpart
                    self._append_to_output("\x1b[K"+rpart)
                    rl = len(rpart)
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
    
    def get_id(self):
        return self._id
    
    def initialize(self):
        try:
            if os.getuid()==0:
                self._login_request = LoginRequest(self)
            else:
                self.open_session(None,None)
        except:
            self.terminate() 
        
    
    def check_login(self,u,p):
        if agent.is_mac():
            return self._check_login_mac(u,p)
        else:
            return self._check_login_linux(u,p)
    
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
                    uinfo = pwd.getpwnam(u)
                    if uinfo is not None:
                        phash=uinfo.pw_passwd
                except:
                    None                    
            if phash is not None:
                return crypt.crypt(p, phash) == phash
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
                    if u is None:
                        uinfo = pwd.getpwuid(os.getuid())
                    else:
                        uinfo = pwd.getpwnam(u)
                    uid=uinfo.pw_uid
                    udir=uinfo.pw_dir
                    upshell=uinfo.pw_shell            
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
                    if upshell=="/bin/bash" or upshell=="/bin/zsh" or upshell=="/bin/sh":
                        nargv.append("--login")
                    if upshell=="/bin/tcsh" or upshell=="/bin/csh" or upshell=="/bin/dash":
                        nargv.append("-l")
                    os.execvpe(upshell, nargv, env)
                    os._exit(0)
                except:
                    os._exit(1)

            fl = fcntl.fcntl(sys.stdin, fcntl.F_GETFL)
            fcntl.fcntl(pio, fcntl.F_SETFL, fl | os.O_NONBLOCK)
            fcntl.ioctl(pio, termios.TIOCSWINSZ, struct.pack("hhhh", self._rows, self._cols, 0, 0))
            self._ppid = ppid
            self._pio = pio
            self._reader = io.open(pio, 'rb', closefd=False)
            self._writer = io.open(pio, 'wb', closefd=False)
            try:
                self._manager._cinfo.inc_activities_value("shellSession")
            except:
                None
            self._login_request = None
        except:
            self.terminate()

    def _processIsAlive(self):
        try:
            if self._ppid>=0:
                os.waitpid(self._ppid, os.WNOHANG)
                os.kill(self._ppid, 0) # kill -0 tells us it's still alive
                return True
            else:
                return False
        except OSError:
            return False
        
    def terminate(self):
        self._login_request=None        
        try:
            self._manager._cinfo.dec_activities_value("shellSession")
        except:
            None
        self._bterm=True        
        if self._reader is not None:
            try:
                self._reader.close()
            except:
                None
        if self._writer is not None:
            try:
                self._writer.close()
            except:
                None
        if self._ppid>=0:
            if self._processIsAlive():
                try:
                    os.kill(self._ppid, signal.SIGTERM)
                except:
                    None
                time.sleep(0.5)
            if self._processIsAlive():
                try:
                    os.kill(self._ppid, signal.SIGKILL)
                    os.waitpid(self._ppid, 0)
                except:
                    None
            self._ppid=-1
        
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
        self._cmd = "cmd.exe"
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
        self._login_request = LoginRequest(self)                

    def check_login(self,u,p):
        try:        
            return conpty.check_login(u,p)
        except:
            return False

    def open_session(self,u,p):
        try:
            self._pty = conpty.ConPty(self._cmd, self._col, self._row, self._write_err)
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
            self._pty.write(c)
        except:
            self.terminate()       

    def read_update(self):
        if self._bterm==True:
            return None
        try:
            if self._login_request is not None:
                return self._login_request.read_update()        
            #return self._pty.read()
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
    

