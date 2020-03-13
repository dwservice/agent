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
import codecs
import subprocess
import io
import agent
import json

try:
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
                    self._last_timeout=long(time.time() * 1000)
                    prprequest = json.loads(data.to_str("utf8"))
                    if prprequest["type"]==ShellManager.REQ_TYPE_INITIALIZE:
                        sid=prprequest["id"]
                        shl = Linux(self, sid, prprequest["cols"], prprequest["rows"])
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
        self._last_timeout=long(time.time() * 1000)
        try:
            self._semaphore.acquire()
            try:
                bwait=False
                while not self._bclose:
                    if bwait:
                        self._semaphore.wait(0.2)
                    bwait=True
                    elapsed=long(time.time() * 1000)-self._last_timeout
                    if elapsed<0:
                        self._last_timeout=long(time.time() * 1000) #Modificato orario pc
                    elif elapsed>1000:
                        self._timeout_cnt+=1;
                        self._last_timeout=long(time.time() * 1000)
                    if self._timeout_cnt>=SHELL_INTERVALL_TIMEOUT:
                        self.terminate()
                    else:
                        arrem=[]
                        for idx in self._shell_list:
                            try:                                
                                #apptm=long(time.time() * 1000)                                
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
                                    print("SEND: len:" + str(len(appsend)) + "  time:" + str(long(time.time() * 1000)-apptm) + "\n")'''
                            except Exception as er:
                                try:
                                    snd = {}
                                    snd["id"]=idx
                                    if not self._shell_list[idx].is_terminate():
                                        snd["error"]=True
                                    snd["terminate"]=True
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

class Linux():
    
    def __init__(self,mgr, sid, col, row):
        self._manager=mgr
        self._id=sid
        self._cols=col
        self._rows=row
        self._path="/bin/bash"
        self._bterm = False
        self._semaphore = threading.Condition()
    
    def get_id(self):
        return self._id
    
    def _getutf8lang(self):
        try:
            p = subprocess.Popen("locale | grep LANG=", stdout=subprocess.PIPE, shell=True)
            (po, pe) = p.communicate()
            p.wait()
            if len(po) > 0:
                ar = po.split("\n")[0].split("=")[1].split(".")
                if ar[1].upper()=="UTF8" or ar[1].upper()=="UTF-8":
                    return ar[0] 
        except:
            None
        try:                
            p = subprocess.Popen("locale -a", stdout=subprocess.PIPE, shell=True)
            (po, pe) = p.communicate()
            p.wait()
            if len(po) > 0:
                arlines = po.split("\n")
                for r in arlines:
                    ar = r.split(".")
                    if len(ar)>1 and ar[0].upper()=="EN_US" and (ar[1].upper()=="UTF8" or ar[1].upper()=="UTF-8"):
                        return ar[0]
                #If not found get the first utf8
                for r in arlines:
                    ar = r.split(".")
                    if len(ar)>1 and (ar[1].upper()=="UTF8" or ar[1].upper()=="UTF-8"):
                        return ar[0]
        except:
            None
        return None
    
    def initialize(self):
        
        ppid, pio = pty.fork()
        if ppid == 0: #Processo figlo
            
            stdin = 0
            stdout = 1
            stderr = 2
            
            env = {}
            env["TERM"] = "xterm"
            
            env["SHELL"] = self._path
            env["PATH"] = os.environ['PATH']
            applng=os.environ.get('LANG')
            if applng is not None:
                if not (applng.upper().endswith(".UTF8") or applng.upper().endswith(".UTF-8")):
                    applng=None
            if applng is None:
                applng = self._getutf8lang()
            if applng is not None:                
                env["LANG"] = applng
            env["PYTHONIOENCODING"] = "utf_8"
            
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
            os.chdir("/")
            os.execvpe(self._path, [], env)
            os._exit(0)

        
        fl = fcntl.fcntl(sys.stdin, fcntl.F_GETFL)
        fcntl.fcntl(pio, fcntl.F_SETFL, fl | os.O_NONBLOCK)
         
        fcntl.ioctl(pio, termios.TIOCSWINSZ, struct.pack("hhhh", self._rows, self._cols, 0, 0))
                   
        self.ppid = ppid
        self.pio = pio
        
        self._reader = io.open(pio, 'rb', closefd=False)
        self._writer = io.open(pio, 'wt', encoding="UTF-8", closefd=False)
 

    def _processIsAlive(self):
        try:
            os.waitpid(self.ppid, os.WNOHANG)
            os.kill(self.ppid, 0) # kill -0 tells us it's still alive
            return True
        except OSError:
            return False
        
    def terminate(self):
        self._bterm=True
        self._reader.close()
        self._writer.close()
        if self._processIsAlive():
            os.kill(self.ppid, signal.SIGTERM)
            time.sleep(0.5)
        if self._processIsAlive():
            os.kill(self.ppid, signal.SIGKILL)
            os.waitpid(self.ppid, 0)                
        
    def is_terminate(self):
        if not self._processIsAlive():
            self._bterm=True
            return True
        return self._bterm
    
    def change_rows_cols(self, rows, cols):
        fcntl.ioctl(self.pio, termios.TIOCSWINSZ, struct.pack("hhhh", rows, cols, 0, 0))
        
    def write_inputs(self, c):        
        if self._bterm == None:
            return
        if self._bterm == None:
            return
        if not isinstance(c, unicode):
            c=c.decode("utf8");
        self._writer.write(c)
        self._writer.flush()

    def read_update(self):
        #inpSet = [ self.pio ]
        #inpReady, outReady, errReady = select.select(inpSet, [], [], 0)
        #if self.pio in inpReady:
        #reader = io.open(self.pio, 'rb', closefd=False,buffering=1024)
        #output=reader.read(self._rows*self._cols*16)
        #output=reader.read(128)
        #reader.close()
        #output=self._reader.read(self._rows*self._cols)
        return self._reader.read()

                
'''class Windows():

    def __init__(self, sid, col, row):
        self._id=sid
        self._col=col
        self._row=row
        self._cur_file = None
        self._cur_row = 0
        self._cur_col = 0
        self._cur_cmd = ""
        self._cur_cmd_pos = 0
        self._cur_cmd_ins_mode=False
        self._cur_cmd_notify = []
        self._history_cmd= []
        self._history_cmd_pos = -1
        self._history_cmd_max = 5
        self._bterm = False
        self._semaphore = threading.Condition()
        self._pre_data = ""
        
    def get_id(self):
        return self._id
    
    def initialize(self):
        #Legge il codepage di cmd
        a = os.popen('chcp')
        self._chcp = a.read()
        a.close()
        self._chcp="cp" + self._chcp.split(":")[1].strip()
        
        #Crea file di output
        tn=tempfile.mkstemp()[1]
        self._tfile =  codecs.open(tn, 'wb')
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE
        self._process = subprocess.Popen(['cmd.exe'], shell=False, 
                                       stdin=subprocess.PIPE, stdout=self._tfile, 
                                       stderr=subprocess.STDOUT,  startupinfo=si)
        
                                       
        self._cur_file = codecs.open(tn, 'r', self._chcp)
        #self._process.stdin.write("MODE CON: COLS=" + str(self._col)+ " LINES=" + str(self._row) + "\n")
    
    def terminate(self):
        self._bterm=True
        self._cur_file.close()
        try:
            self._process.stdin.write("exit\r\n")
            self._process.stdin.flush()
            time.sleep(0.5) #Attende 500 ms
        except:
            None
        poll = self._process.poll()
        if poll == None:
            try:
                self._process.terminate()
            except:
                None
            try:
                self._process.kill()
            except:
                None
            self._tfile.close()
    
    def is_terminate(self):
        return self._bterm
    
    def write_char(self,  schr):
        poll = self._process.poll()
        if poll != None:
            raise Exception("Shell closed.") 
        self._semaphore.acquire()
        try:
            if schr=="RETURN":
                self._add_history_cmd()
                #Invia il comando
                self._process.stdin.write(self._cur_cmd.encode(self._chcp) + "\r\n")
                self._process.stdin.flush()
                self._cur_cmd=""
                self._cur_cmd_pos=0
                self._cur_cmd_notify=[]
                time.sleep(0.1) #Attende 100 ms
            elif schr=="BACKSPACE": 
                if self._cur_cmd_pos>0:
                    self._cur_cmd=self._cur_cmd [:self._cur_cmd_pos-1] + self._cur_cmd[self._cur_cmd_pos:]
                    self._cur_cmd_pos-=1
                    self._update_cmd()
                    self._update_cmd_pos()
            elif schr=="DELETE": 
                if self._cur_cmd_pos<len(self._cur_cmd):
                    self._cur_cmd=self._cur_cmd [:self._cur_cmd_pos] + self._cur_cmd[self._cur_cmd_pos+1:]
                    self._update_cmd()
                    self._update_cmd_pos()
            elif schr=="LEFT": 
                if self._cur_cmd_pos>0:
                    self._cur_cmd_pos-=1
                    self._update_cmd_pos()
            elif schr=="RIGHT": 
                if self._cur_cmd_pos<len(self._cur_cmd):
                    self._cur_cmd_pos+=1
                    self._update_cmd_pos()
            elif schr=="UP": 
                if len(self._history_cmd)>0:
                    if self._history_cmd_pos==-1:
                        self._history_cmd_pos=len(self._history_cmd)
                    if self._history_cmd_pos>0:
                        self._clear_cmd()
                        self._history_cmd_pos-=1
                        self._cur_cmd=self._history_cmd[self._history_cmd_pos]
                        self._cur_cmd_pos=len(self._cur_cmd)
                        self._update_cmd()
                        self._update_cmd_pos()  
            elif schr=="DOWN":
                if len(self._history_cmd)>0:
                    if self._history_cmd_pos!=-1:
                        if self._history_cmd_pos<len(self._history_cmd)-1:
                            self._clear_cmd()
                            self._history_cmd_pos+=1
                            self._cur_cmd=self._history_cmd[self._history_cmd_pos]
                            self._cur_cmd_pos=len(self._cur_cmd)
                            self._update_cmd()
                            self._update_cmd_pos()
            elif schr=="PAGEUP": 
                if len(self._history_cmd)>0:
                    self._clear_cmd()
                    self._history_cmd_pos=0
                    self._cur_cmd=self._history_cmd[self._history_cmd_pos]
                    self._cur_cmd_pos=len(self._cur_cmd)
                    self._update_cmd()
                    self._update_cmd_pos()
            elif schr=="PAGEDOWN": 
                if len(self._history_cmd)>0:
                    self._clear_cmd()
                    self._history_cmd_pos=len(self._history_cmd)-1
                    self._cur_cmd=self._history_cmd[self._history_cmd_pos]
                    self._cur_cmd_pos=len(self._cur_cmd)
                    self._update_cmd()
                    self._update_cmd_pos()
            elif schr=="HOME": 
                if self._cur_cmd_pos>0:
                    self._cur_cmd_pos=0
                    self._update_cmd_pos()
            elif schr=="END": 
                if self._cur_cmd_pos<len(self._cur_cmd):
                    self._cur_cmd_pos=len(self._cur_cmd)
                    self._update_cmd_pos()
            elif schr=="INSERT": 
                self._cur_cmd_ins_mode=not self._cur_cmd_ins_mode
                self._update_cmd_pos()
            elif schr=="CTRL+C": 
                self._process.stdin.write("\x03")
                self._process.stdin.flush()
            else:
                if len(schr)==1:
                    if not self._cur_cmd_ins_mode or self._cur_cmd_pos==len(self._cur_cmd):
                        self._cur_cmd=self._cur_cmd [:self._cur_cmd_pos] + schr + self._cur_cmd[self._cur_cmd_pos:]
                    else:
                        self._cur_cmd=self._cur_cmd [:self._cur_cmd_pos] + schr + self._cur_cmd[self._cur_cmd_pos+1:]
                    self._cur_cmd_pos+=1
                    self._update_cmd()
                    self._update_cmd_pos()
        finally:
            self._semaphore.release()                
    
    def _add_history_cmd(self):
        self._history_cmd_pos=-1
        if self._cur_cmd.strip()!="":
            if len(self._history_cmd)==0 or self._history_cmd[len(self._history_cmd)-1].strip()!=self._cur_cmd.strip():
                self._history_cmd.append(self._cur_cmd)
                if len(self._history_cmd)>self._history_cmd_max:
                    del self._history_cmd[0]
    
    def _clear_cmd(self):
        s=self._cur_cmd
        rw=self._cur_row
        cl=self._cur_col
        while (cl+len(s)>=self._col):
            itm = {
                   'type': 'remove', 
                   'row': rw, 
                   'col': cl,  
                   'len': self._col-cl
                   }
            self._cur_cmd_notify.append(itm)
            rw+=1
            cl=0
            s=s[self._col-cl:]
        itm = {
               'type': 'remove', 
               'row': rw, 
               'col': cl,  
               'len': self._col-cl
               }
        self._cur_cmd_notify.append(itm)
        
        
    def _update_cmd(self):
        s=self._cur_cmd
        rw=self._cur_row
        cl=self._cur_col
        while (cl+len(s)>=self._col):
            s1=s[:self._col-cl]
            s2=s[self._col-cl:]
            itm = {
                   'type': 'update', 
                   'row': rw, 
                   'col': cl,  
                   'text': s1
                   }
            self._cur_cmd_notify.append(itm)
            if rw<self._row-1:
                    rw+=1
            else:
                self._cur_row-=1
                itm = {
                    'type': 'scroll', 
                    'row': 1
                }
                self._cur_cmd_notify.append(itm)
            cl=0
            s=s2
        itm = {
               'type': 'update', 
               'row': rw, 
               'col': cl,  
               'text': s
               }
        self._cur_cmd_notify.append(itm)
        lnrem=self._col-(cl+len(s));
        if lnrem>0:
            itm = {
               'type': 'remove', 
               'row': rw, 
               'col': cl+len(s),  
               'len': lnrem
               }
        self._cur_cmd_notify.append(itm)
                
    def _update_cmd_pos(self):
        ps=self._cur_cmd_pos
        cl=self._cur_col
        rw=self._cur_row
        while (cl+ps>=self._col):
            ps-=(self._col-cl)
            if rw<self._row-1:
                rw+=1
            cl=0
        itm = {
            'type': 'position', 
            'row': rw, 
            'col': cl+ps, 
            'ins': self._cur_cmd_ins_mode
           }
        self._update_pos(self._cur_cmd_notify, itm)
        
    def _update_pos(self, ar, itm):
        #Rimuove eventuali vecchie posizioni
        for obj in ar:
            if obj['type'] == 'position':
                ar.remove(obj)
        ar.append(itm)
        
    
    def _parse(self, s):
        arret=[]
        if len(self._cur_cmd_notify)>0:
            arret=self._cur_cmd_notify
            self._cur_cmd_notify=[]
        if s!="":
            ar = s.splitlines()
            for i in range(len(ar)):
                s=ar[i]
                if len(s)>0:
                    while (self._cur_col+len(s)>=self._col):
                        s1=s[:self._col-self._cur_col]
                        s2=s[self._col-self._cur_col:]
                        itm = {
                               'type': 'update', 
                               'row': self._cur_row, 
                               'col': self._cur_col,  
                               'text': s1
                               }
                        arret.append(itm)
                        if self._cur_row<self._row-1:
                            self._cur_row+=1
                        else:
                            itm = {
                            'type': 'scroll', 
                            'row': 1
                            }
                            arret.append(itm)
                        self._cur_col=0
                        s=s2
                    if len(s)>0:
                        itm = {
                               'type': 'update', 
                               'row': self._cur_row, 
                               'col': self._cur_col,  
                               'text': s
                               }
                        arret.append(itm)
                        self._cur_col+=len(s)
                if i<len(ar)-1:
                    if self._cur_row<self._row-1:
                        self._cur_row+=1
                    else:
                        itm = {
                           'type': 'scroll', 
                           'row': 1
                        }
                        arret.append(itm)
                    self._cur_col=0
                itm = {
                   'type': 'position', 
                   'row': self._cur_row, 
                   'col': self._cur_col, 
                   'ins': self._cur_cmd_ins_mode
                   }
                self._update_pos(arret,  itm)
        return arret
    
    def read_update(self, inputs):
        if inputs is not None:
            inputs = inputs.split("|")
            for i in range(len(inputs)):
                schr=inputs[i]
                if schr=="PIPE":
                    schr="|"
                self.write_char(schr)
        poll = self._process.poll()
        if poll != None:
            raise Exception("Shell closed.") 
        self._semaphore.acquire()
        try:
            data = self._pre_data + self._cur_file.read(1024*8)
            self._pre_data=""
            if data.endswith("\r"):
                data=data[:len(data)-1]
                self._pre_data="\r"
            return self._parse(data)
        finally:
            self._semaphore.release()
    

   
if __name__ == "__main__":
    #a = os.popen('chcp')
    #chcp = a.read()
    #a.close()
    #chcp="cp" + chcp.split(":")[1].strip()
    
    p = subprocess.Popen("powershell", stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False)
    
    #f = codecs.open(p.stdout, 'r', chcp)
    
    #p.stdin.write("$OutputEncoding = New-Object -typename System.Text.UTF8Encoding\n")
    
    p.stdin.write(u"top@à\n\r".encode('unicode_escape'))
    #import io
    #reader = io.TextIOWrapper(p.stdout, encoding=chcp)
    while True:
        ln=p.stdout.read(1)
        print ln
        if ln is None:
            break
    
    ln=p.stdout.readline()
    
    #(po, pe) = p.communicate()
    #p.wait()
    #print po
    #print pe
    
'''  
