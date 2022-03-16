# -*- coding: utf-8 -*-

'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''

import agent
import threading
import json
import time
import struct
import os
import stat
import utils
import ctypes
import native
import subprocess
from . import common


##### TO FIX 22/09/2021
try:
    TMP_bytes_to_str=utils.bytes_to_str
    TMP_str_to_bytes=utils.str_to_bytes
    TMP_str_new=utils.str_new
    TMP_bytes_join=utils.bytes_join
    TMP_bytes_get=utils.bytes_get
except:
    TMP_bytes_to_str=lambda b, enc="ascii": b.decode(enc, errors="replace")
    TMP_str_to_bytes=lambda s, enc="ascii": s.encode(enc, errors="replace")
    def TMP_py2_str_new(o):
        if isinstance(o, unicode):
            return o 
        elif isinstance(o, str):
            return o.decode("utf8", errors="replace")
        else:
            return str(o).decode("utf8", errors="replace")
    TMP_str_new=TMP_py2_str_new
    TMP_bytes_join=lambda ar: "".join(ar)
    TMP_bytes_get=lambda b, i: ord(b[i])

try:    
    import sys
    if sys.version_info[0]==2:        
        if utils.path_exists(os.path.dirname(__file__) + os.sep + "__pycache__"):
            utils.path_remove(os.path.dirname(__file__) + os.sep + "__pycache__")
except: 
    None
##### TO FIX 22/09/2021

########################################################################################################################
##### OLD 27/07/2021 TO REMOVE      
########################################################################################################################
BIPCOK=False
try:
    import ipc
    BIPCOK=True
except:
    None


    
####### TO REMOVE (IT IS INSIDE IPC)
if BIPCOK==True:  
    class ProcessInActiveConsole(ipc.Process):
        def __init__(self, mdl, func, args=None, forcesubprocess=False):
            ipc.Process.__init__(self, mdl, func, args, self._process_fix_perm, forcesubprocess)
            self._forcesubprocess=forcesubprocess
            self._currentconsole=None
            self._currentconsolecounter=utils.Counter()
            
        
        def _process_fix_perm(self):
            jo={}
            appconsole = self._currentconsole
            if (utils.is_mac() or utils.is_linux()) and appconsole!=None and "uid" in appconsole and appconsole["uid"]!=os.getuid():
                jo["mode"]=stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH
            return jo
        
        def _get_linux_envirionment(self,uid,tty):
            bwaylanderr=False
            lstret={}
            
            #DETECT BY PROCESS
            if uid!=-1:       
                lst = native.get_instance().get_process_ids()
                try:
                    bok=False
                    cnt = utils.Counter()
                    while not bok and cnt.get_value()<=2:
                        for pid in lst:
                            if native.get_instance().get_process_uid(pid)==uid:
                                lstret={}
                                arenv = native.get_instance().get_process_environ(pid)
                                for apps in arenv:                        
                                    if apps=="XAUTHORITY" or apps=="DISPLAY" or apps.startswith("WAYLAND_") or apps.startswith("XDG_") or apps.startswith("LC_"):
                                        lstret[apps]=arenv[apps]
                                        #print("DETECT BY PROCESS- " + apps + ": " + lstret[apps])                                        
                                if ("DISPLAY" in lstret and "XAUTHORITY" in lstret):                                    
                                    bok=True
                                    break
                                lstret={}
                        time.sleep(0.5)
                except:
                    lstret={}
            
            #DETECT BY WHAT OF w COMMAND
            swhatcmd=None
            if uid!=-1:            
                try:
                    import pwd
                    pwinfo=pwd.getpwuid(uid)
                    if pwinfo is not None and pwinfo.pw_name is not None:
                        data = subprocess.Popen(["w"], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
                        so, se = data.communicate()
                        if so is not None and len(so)>0:
                            so=TMP_bytes_to_str(so, "utf8")
                            ar = so.split("\n")
                            del ar[0]
                            bhead=True
                            pwhat=-1
                            for s in ar:
                                if bhead:
                                    #DETECT WHAT position
                                    bhead=False
                                    pwhat = s.upper().index("WHAT")                                
                                elif pwhat>=0 and s.split(" ")[0].rstrip(" ")==pwinfo.pw_name:
                                    swhatcmd = s[pwhat:].lstrip(" ").rstrip(" ")
                                    break
                except:
                    None
            if swhatcmd is not None:
                try:
                    lst = native.get_instance().get_process_ids()
                    for pid in lst:
                        sst = native.get_instance().get_process_stat(pid)
                        if native.get_instance().get_process_uid(pid)==uid:
                            bok=False
                            lret = native.get_instance().get_process_cmdline(pid)
                            lcmd=" ".join(lret).lstrip(" ").rstrip(" ")
                            if lcmd==swhatcmd:
                                arenv = native.get_instance().get_process_environ(pid)
                                for apps in arenv:                        
                                    if apps=="XAUTHORITY" or apps=="DISPLAY" or apps.startswith("WAYLAND_") or apps.startswith("XDG_") or apps.startswith("LC_"):
                                        lstret[apps]=arenv[apps]
                                        #print("DETECT BY WHAT OF w COMMAND - " + apps + ": " + lstret[apps])
                                break
                                                
                except:
                    None
            
            #DETECT DISPLAY BY w COMMAND
            if uid!=-1:
                try:
                    import pwd
                    pwinfo=pwd.getpwuid(uid)
                    if pwinfo is not None and pwinfo.pw_name is not None:
                        data = subprocess.Popen(["w"], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
                        so, se = data.communicate()
                        if so is not None and len(so)>0:
                            so=TMP_bytes_to_str(so, "utf8")
                            ar = so.split("\n")
                            del ar[0]
                            bhead=True
                            ptty=-1
                            for s in ar:
                                if bhead:
                                    #DETECT WHAT position
                                    bhead=False
                                    ptty = s.upper().index("TTY")                                
                                elif ptty>=0 and s.split(" ")[0].rstrip(" ")==pwinfo.pw_name:
                                    sdisplay = s[ptty:]
                                    sdisplay=sdisplay[0:sdisplay.index(" ")]
                                    if len(sdisplay)==2:
                                        if sdisplay[0]==":" and sdisplay[1].isdigit():
                                            sdsp=sdisplay
                                    elif len(sdisplay)==4:
                                        if sdisplay[0]==":" and sdisplay[1].isdigit() and sdisplay[2]=="." and sdisplay[3].isdigit():
                                            sdsp=sdisplay
                                    if sdsp is not None:
                                        lstret["DISPLAY"] = sdsp
                                        #print("DETECT DISPLAY BY w COMMAND - DISPLAY: " + lstret["DISPLAY"])
                                        break
                except:
                    None
            
            #DETECT BY CMDLINE
            try:
                if tty is not None:
                    st = os.stat("/dev/" + tty)
                lst = native.get_instance().get_process_ids()
                for pid in lst:
                    sst = native.get_instance().get_process_stat(pid)
                    if (tty is None or sst["tty"]==st.st_rdev) and (uid==-1 or native.get_instance().get_process_uid(pid)==uid):
                        lret = native.get_instance().get_process_cmdline(pid)
                        bok=False
                        sxauth=None
                        sdsp=None
                        for i in range(len(lret)):
                            if i==0:
                                scmd = lret[i]
                                arcmd = scmd.split("/")
                                if len(arcmd)>0:
                                    scmd=arcmd[len(arcmd)-1]
                                    if scmd.upper()=="X" or "XORG" in scmd.upper():
                                        bok=True
                                    elif scmd.upper()=="XWAYLAND":
                                        bwaylanderr=True
                            if bok:
                                sitm = lret[i]
                                if i>0 and lret[i-1]=="-auth":
                                    sxauth=sitm
                                elif len(sitm)==2:
                                    if sitm[0]==":" and sitm[1].isdigit():
                                        sdsp=sitm
                                elif len(sitm)==4:
                                    if sitm[0]==":" and sitm[1].isdigit() and sitm[2]=="." and sitm[3].isdigit():
                                        sdsp=sitm
                        if sxauth is not None:
                            lstret["XAUTHORITY"] = sxauth                            
                            #print("DETECT BY CMDLINE - XAUTHORITY: " + lstret["XAUTHORITY"])                            
                        if sdsp is not None:
                            lstret["DISPLAY"] = sdsp
                            #print("DETECT BY CMDLINE - DISPLAY: " + lstret["DISPLAY"])
                        if bok:
                            bwaylanderr=False
                            break
                
            except:
                None
            
            if bwaylanderr or (("XDG_SESSION_TYPE" in lstret) and (lstret["XDG_SESSION_TYPE"].upper()=="WAYLAND")):
                raise Exception("XWayland is not supported.")                
            
            if "DISPLAY" not in lstret:
                lstret["DISPLAY"]=":0"
                
            if "XAUTHORITY" in lstret:
                sxauth = lstret["XAUTHORITY"]
                if not os.path.exists(sxauth):
                    try:
                        p = sxauth.rindex("/")
                        if p>=0:
                            sxauthdir = sxauth[0:p]
                            os.makedirs(sxauthdir, 0o700)
                            fd = os.open(sxauth,os.O_RDWR|os.O_CREAT, 0o600)
                            os.close(fd)                                                        
                    except:
                        None
            
            if "XAUTHORITY" not in lstret and (uid!=-1 or tty is not None): 
                return self._get_linux_envirionment(-1, None)
            
            '''
            if "DISPLAY" in lstret:
                print("DISPLAY: " + lstret["DISPLAY"])
            if "XAUTHORITY" in lstret:
                print("XAUTHORITY: " + lstret["XAUTHORITY"])
            '''
            
            return lstret
        
        def _load_linux_console_info(self,appconsole):
            if appconsole is not None:
                stty=appconsole["tty"]
                #print("\n\nTTY: " + stty)
                pwinfo=None
                try:
                    import pwd
                    if os.getuid()==0 and "cktype" in appconsole and appconsole["cktype"]!="":
                        if appconsole["cktype"]=="USER_NAME":
                            pwinfo=pwd.getpwnam(appconsole["ckvalue"])
                        elif appconsole["cktype"]=="USER_ID":
                            pwinfo=pwd.getpwuid(appconsole["ckvalue"])
                    else:
                        pwinfo=pwd.getpwuid(os.getuid())
                except:
                    None
                
                appuid=-1
                libenv={}
                if pwinfo is not None:
                    #print("uid: " + str(pwinfo.pw_uid))                                    
                    appconsole["user"] = pwinfo.pw_name
                    appconsole["uid"] = pwinfo.pw_uid
                    appconsole["gid"] = pwinfo.pw_gid
                    appconsole["home"] = pwinfo.pw_dir
                    appuid=pwinfo.pw_uid
                else:
                    libenv = os.environ
                
                lstret = self._get_linux_envirionment(appuid, stty)
                for k in lstret:
                    libenv[k]=lstret[k]
                if pwinfo is not None:
                    libenv['HOME'] = appconsole["home"]
                    libenv['LOGNAME'] = appconsole["user"]
                    libenv['USER'] = appconsole["user"]
                appconsole["env"]=libenv
        
        def _load_mac_console_info(self,appconsole):
            if appconsole is not None:
                pwinfo=None            
                try:
                    import pwd
                    if os.getuid()==0:
                        pwinfo=pwd.getpwuid(appconsole["uid"])
                    else:
                        pwinfo=pwd.getpwuid(os.getuid())
                except:
                    None                
                libenv = os.environ                
                if pwinfo is not None:
                    try:
                        appconsole["user"] = pwinfo.pw_name
                        appconsole["gid"] = pwinfo.pw_gid
                        appconsole["home"] = pwinfo.pw_dir
                        libenv['HOME'] = appconsole["home"]
                        libenv['LOGNAME'] = appconsole["user"]
                        libenv['USER'] = appconsole["user"]
                    except:
                        None
                appconsole["env"]=libenv
        
        def _init_process_demote(self,user_uid, user_gid):
            def set_ids():
                os.setgid(user_gid)
                os.setuid(user_uid)
            return set_ids        

        def _is_old_windows(self):
            return (utils.is_windows() and (native.get_instance().is_win_xp()==1 or native.get_instance().is_win_2003_server()==1))
        
        def is_change_console(self):
            if self._currentconsole is not None and self._currentconsolecounter.is_elapsed(1):
                self._currentconsolecounter.reset()
                appc=self._detect_console()
                if appc is not None:
                    if utils.is_windows():
                        if self._is_old_windows() and appc["id"]>0:
                            native.get_instance().win_station_connect()
                            time.sleep(1)
                            return True
                        elif appc["id"]!=self._currentconsole["id"]:
                            return True
                    elif utils.is_mac():
                        if appc["uid"]!=self._currentconsole["uid"]:
                            return True
                    elif utils.is_linux():
                        if appc["tty"]!=self._currentconsole["tty"]:
                            if appc["cktype"]=="" or appc["cktype"]!=self._currentconsole["cktype"]:
                                return True
                            else:
                                return appc["ckvalue"]!=self._currentconsole["ckvalue"]
            return False
        
        def _detect_console(self):
            if utils.is_windows():
                return {"id": native.get_instance().get_active_console_id()}            
            elif utils.is_mac():
                return {"uid": native.get_instance().get_console_user_id()}            
            elif utils.is_linux():
                try:
                    ar={}
                    stty=native.get_instance().get_tty_active()
                    if stty is not None:
                        ar["tty"] = stty
                        ar["cktype"] = ""
                        ar["ckvalue"] = ""
                        try:
                            if os.getuid()==0:
                                sbuf = None
                                offset = 0                        
                                with open('/var/run/utmp', 'rb') as fd:
                                    sbuf = fd.read()
                                if sbuf is not None:
                                    while offset < len(sbuf):
                                        arutmp = ipc._struct_utmp.unpack_from(sbuf, offset)
                                        stype=arutmp[0]
                                        if stype==7: #USER_PROCESS
                                            appstty=arutmp[2].rstrip(b'\0')
                                            if appstty==stty:
                                                ar["cktype"]="USER_NAME"
                                                ar["ckvalue"]=arutmp[4].rstrip(b'\0')
                                                break                                     
                                        offset += ipc._struct_utmp.size
                        except:
                            None
                        if ar["cktype"]=="":
                            try:    
                                st = os.stat("/dev/" + stty)
                                ar["cktype"]="USER_ID"
                                ar["ckvalue"]=st.st_uid
                            except:
                                None
                        #print("_detect_console_:" + ar["cktype"] + " " + str(ar["ckvalue"]))
                        return ar
                except:
                    None 
                
            return None
        
        def _create_process(self, args):        
            if utils.is_windows():
                if self._forcesubprocess:
                    self._currentconsole=None
                    self._process=subprocess.Popen(args)
                    self._ppid=self._process.pid
                else:
                    '''
                    runaselevatore=u"False"
                    if self._get_screen_module().DWAScreenCaptureIsUserInAdminGroup()==1:
                        if self._get_screen_module().DWAScreenCaptureIsRunAsAdmin()==1:
                            if self._get_screen_module().DWAScreenCaptureIsProcessElevated()==1:
                                runaselevatore=u"True"
                    '''            
                    appcmd=u"\"" + self._py_exe_path + u"\" -S -m agent " + TMP_str_new(args[2]) + u" " + TMP_str_new(args[3]) #+ u" " + TMP_str_new(str(self._agent_main._agent_debug_mode)) + u" windows " + runaselevatore            
                    self._process=None
                    self._ppid = native.get_instance().start_process_in_active_console(appcmd,self._py_home_path)
                    if self._ppid==-1:
                        self._ppid=None
                        self._currentconsole=None
                        raise Exception("Start process error")
            elif utils.is_linux():
                bfaultback=True
                if self._currentconsole!=None and "env" in self._currentconsole:
                    try:
                        libenv=self._currentconsole["env"]
                        if utils.path_exists("runtime"):
                            libenv["LD_LIBRARY_PATH"]=utils.path_absname("runtime/lib")
                        elif "LD_LIBRARY_PATH" in os.environ:
                            libenv["LD_LIBRARY_PATH"]=os.environ["LD_LIBRARY_PATH"]
                        self._process=subprocess.Popen(args, env=libenv, preexec_fn=self._init_process_demote(self._currentconsole["uid"], self._currentconsole["gid"]))                        
                        self._ppid=self._process.pid
                        bfaultback=False
                    except:
                        None
                if bfaultback:
                    libenv = os.environ
                    lstret = self._get_linux_envirionment(-1, None)
                    for k in lstret:
                        libenv[k]=lstret[k]
                    if utils.path_exists("runtime"):
                        libenv["LD_LIBRARY_PATH"]=utils.path_absname("runtime/lib")
                    elif "LD_LIBRARY_PATH" in os.environ:
                        libenv["LD_LIBRARY_PATH"]=os.environ["LD_LIBRARY_PATH"]
                    self._process=subprocess.Popen(args, env=libenv)
                    self._ppid=self._process.pid
                    
            elif utils.is_mac():
                bfaultback=True
                self._ppid=None
                if not self._forcesubprocess:
                    if not hasattr(native.get_instance(), "is_old_guilnc") or native.get_instance().is_old_guilnc():                
                        #GUI LAUNCHER OLD VERSION 03/11/2021 (DO NOT REMOVE)
                        if self._currentconsole!=None and "uid" in self._currentconsole:
                            self._ppid=native.get_instance().exec_guilnc(self._currentconsole["uid"],"ipc",[args[3]])
                    else:
                        if self._currentconsole!=None and "env" in self._currentconsole:
                            try:
                                libenv=self._currentconsole["env"]
                                if utils.path_exists("runtime"):
                                    libenv["DYLD_LIBRARY_PATH"]=utils.path_absname("runtime/lib")
                                elif "DYLD_LIBRARY_PATH" in os.environ:
                                    libenv["DYLD_LIBRARY_PATH"]=os.environ["DYLD_LIBRARY_PATH"]
                                self._process=subprocess.Popen(args, env=libenv, preexec_fn=self._init_process_demote(self._currentconsole["uid"], self._currentconsole["gid"]))                        
                                self._ppid=self._process.pid
                                bfaultback=False
                            except:
                                None
                                                
                if self._ppid is not None:
                    self._process = None
                    bfaultback=False                                    
                if bfaultback:
                    libenv = os.environ
                    if utils.path_exists("runtime"):
                        libenv["DYLD_LIBRARY_PATH"]=utils.path_absname("runtime/lib")
                    elif "DYLD_LIBRARY_PATH" in os.environ:
                        libenv["DYLD_LIBRARY_PATH"]=os.environ["DYLD_LIBRARY_PATH"]
                    self._process=subprocess.Popen(args, env=libenv)
                    self._ppid=self._process.pid
                    
                
        def _start_ipc(self):
            try:            
                self._currentconsole=self._detect_console()
                if utils.is_linux():                
                    self._load_linux_console_info(self._currentconsole)
                elif utils.is_mac():
                    self._load_mac_console_info(self._currentconsole)
                ipc.Process._start_ipc(self)
                self._currentconsolecounter.reset()
            except:
                ex = utils.get_exception()
                self._currentconsole=None
                raise ex    

####### TO REMOVE (IT IS INSIDE IPC)
    
    
class Desktop():

    def __init__(self, agent_main):
        self._agent_main=agent_main
        self._process = None
        self._list = {}
        self._list_semaphore = threading.Condition()        
                    
    def destroy(self, bforce):
        lstcopy=None
        self._list_semaphore.acquire()
        try:
            if not bforce and len(self._list)>0:
                return False
            lstcopy=self._list.copy()
        finally:
            self._list_semaphore.release()
        for k in lstcopy.keys():
            dm = lstcopy[k]
            dm.destroy()
        if not self._process is None:
            self._process.destroy()
            self._process=None            
        return True
        
    def on_conn_close(self, idses):
        lstcopy=None
        self._list_semaphore.acquire()
        try:
            lstcopy=self._list.copy()
        finally:
            self._list_semaphore.release()
        
        for k in lstcopy.keys():
            dm = lstcopy[k]
            if dm.get_idses()==idses:
                try:
                    dm.destroy()
                except:
                    e = utils.get_exception()
                    self._agent_main.write_except(e,"AppDesktop:: on_conn_close error:")
            
    def has_permission(self,cinfo):
        return self._agent_main.has_app_permission(cinfo,"desktop");
    
    def _add_desktop_manager(self, cinfo, wsock):
        itm = None
        key = None
        self._list_semaphore.acquire()
        try:
            while True:
                key = agent.generate_key(10) 
                if key not in self._list:
                    if self._process is None:
                        self._process = DesktopProcessCapture(self._agent_main)
                        self._process.start()
                    itm = DesktopSession(self, cinfo, key, wsock)
                    self._list[key]=itm
                    
                    break
        finally:
            self._list_semaphore.release()        
        itm.start()
        return itm
    
    def _rem_desktop_manager(self, sid):
        self._list_semaphore.acquire()
        try:
            if sid in self._list:
                del self._list[sid]
                if len(self._list)==0 and not self._process is None:
                    self._process.destroy()
                    self._process=None
                
        finally:
            self._list_semaphore.release()
    
    def _get_desktop_manager(self, sid):
        self._list_semaphore.acquire()
        try:
            if sid in self._list:
                return self._list[sid]
        finally:
            self._list_semaphore.release()
        return None
    
    def _get_desktop_manager_check_permissions(self,cinfo,sid):
        dm=self._get_desktop_manager(sid)
        if dm is not None and cinfo.get_idsession()==dm.get_idses():
            return dm;
        else:
            raise Exception("Permission denied. Invalid id.")
        
    def req_copy_text(self,cinfo,params):
        sid = agent.get_prop(params,"id", "")
        dm=self._get_desktop_manager_check_permissions(cinfo,sid)
        sret={}
        sret["text"]=dm.copy_text();
        return json.dumps(sret)
    
    def req_paste_text(self,cinfo,params):
        sret=""
        sid = agent.get_prop(params,"id", "")
        s = agent.get_prop(params,"text", "")
        dm=self._get_desktop_manager_check_permissions(cinfo,sid)
        dm.paste_text(s);
        return sret
    
    def req_websocket(self, cinfo, wsock):
        self._add_desktop_manager(cinfo, wsock)        


class DesktopProcessCapture(threading.Thread):
    
    def __init__(self, agent_main):
        threading.Thread.__init__(self,  name="DesktopProcessCapture")
        self._struct_Q=struct.Struct("!Q")
        self._bdestroy=False
        self._agent_main=agent_main
        self._screen_module=None
        self._sound_module=None
        self._sound_status=None                
        self._supported_frame=None
        self._semaphore = threading.Condition()
        self._strm=None
        self._process=None
        self._process_init=False
        self._process_status="stopped"
        self._process_last_error=None
        self._last_copy_text=None        
        self._id=0        
        self._monitors=None 
        self._monitorsid=0       
        #self._cpdebug=None
        self._debug_forcesubprocess=False
        try:
            self._debug_forcesubprocess=self._agent_main.get_config("desktop.debug_forcesubprocess",False)
        except:
            None
        
        
    def is_destroy(self):
        return self._bdestroy
    
    def destroy(self):
        self._bdestroy=True
        
    def get_supported_frame(self):
        self._semaphore.acquire()
        try:
            if self._supported_frame is None:
                self._supported_frame=[]
                v = self._screen_module.DWAScreenCaptureTJPEGEncoderVersion()
                if v>=2:
                    self._supported_frame.append(common.TYPE_FRAME_TJPEG_V2)
                if v>=1:
                    self._supported_frame.append(common.TYPE_FRAME_TJPEG_V1)
                v = self._screen_module.DWAScreenCapturePaletteEncoderVersion()
                if v>=1:
                    self._supported_frame.append(common.TYPE_FRAME_PALETTE_V1)
            return self._supported_frame
        finally:
            self._semaphore.release()
    
    def get_sound_status(self):
        self._semaphore.acquire()
        try:
            return self._sound_status
        finally:
            self._semaphore.release()    
    
    def get_monitors(self):
        self._semaphore.acquire()
        try:
            return self._monitors
        finally:
            self._semaphore.release()
    
    def get_last_error(self):
        return self._process_last_error;
    
    def get_last_copy_text(self):
        return self._last_copy_text
    
    def _init_screen_module(self):
        if self._screen_module is None:
            self._screen_module = self._agent_main.load_lib("screencapture")                         
        return self._screen_module

    def _term_screen_module(self):
        if self._screen_module is not None:
            self._agent_main.unload_lib("screencapture")
            self._screen_module=None;
    
    def _is_old_windows(self):
        return (utils.is_windows() and (native.get_instance().is_win_xp()==1 or native.get_instance().is_win_2003_server()==1))
            
    def _init_sound_module(self):
        if not self._is_old_windows():
            if self._sound_module is None:
                try:
                    soundenable = False
                    try:
                        soundenable = self._agent_main.get_config("desktop.sound_enable", True);
                    except:
                        None
                    if soundenable:
                        self._sound_module = self._agent_main.load_lib("soundcapture")
                except:
                    e = utils.get_exception()
                    self._agent_main.write_err("Sound library load error: " + utils.exception_to_string(e))
        return self._sound_module
    
    def _term_sound_module(self):
        if self._sound_module is not None:
            self._agent_main.unload_lib("soundcapture")
            self._sound_module=None;
    
    def get_id(self):
        return self._id
    
    def get_status(self):
        return self._process_status
    
    def _destroy_sound_nosync(self):
        if self._sound_status is not None:
            try:
                if "memmap" in self._sound_status:
                    memmap=self._sound_status["memmap"]
                    memmap.seek(0)
                    memmap.write(b"C")
                    memmap.close()
            except:
                None
            self._sound_status=None        
        
    def _destroy_monitors_nosync(self):
        if self._monitors is not None:
            try:
                if "memmap" in self._monitors:
                    memmap=self._monitors["memmap"]
                    memmap.seek(0)
                    memmap.write(b"C")
                    memmap.close()
            except:
                None
            self._monitors=None
            
    def _destroy_process(self):
        self._semaphore.acquire()
        try:
            self._destroy_sound_nosync()
            self._destroy_monitors_nosync()
        finally:
            self._semaphore.release()            
        try:
            if self._strm!=None:
                self._strm.close()                
        except:
            e = utils.get_exception()            
            self._agent_main.write_except(e)        
        self._strm=None
        if self._process is not None: 
            self._process.close()
        self._process_status="stopped"
    
    def _write_obj(self, obj):
        st = self.get_status()
        if st=="started":
            self._strm.write_obj(obj)
        else:
            raise Exception("Process not started.")
    
    def _must_destory_process(self):
        return ((self._process is not None and (not self._process.is_running() or self._process.is_change_console())) 
                or (self._strm is not None and self._strm.is_closed())) 
    
    def _strm_read_timeout(self, strm):
        if self._must_destory_process():
            return True
        return self.is_destroy()
    
    def run(self):
        #DOWNLOAD SCREEN LIB
        self._init_screen_module()
        #DOWNLOAD AUDIO LIB
        self._init_sound_module()        
        try:
            while not self.is_destroy():
                try:
                    if self._must_destory_process():
                        self._destroy_process()                    
                    if self._process_status=="stopped":
                        if self._process is None or not self._process.is_running():
                            prcargs=[]         
                            if hasattr(self._agent_main, "_app_desktop_capture_fallback_lib") and self._agent_main._app_desktop_capture_fallback_lib is not None:
                                prcargs.append("capture_fallback_lib=" + self._agent_main._app_desktop_capture_fallback_lib)
                            
                            ##### TO FIX 22/09/2021
                            if hasattr(ipc, "ProcessInActiveConsole"):
                                self._process=ipc.ProcessInActiveConsole("app_desktop.capture", "ProcessCapture", prcargs, forcesubprocess=self._debug_forcesubprocess)
                            else:
                                self._process=ProcessInActiveConsole("app_desktop.capture", "ProcessCapture", prcargs, forcesubprocess=self._debug_forcesubprocess)
                            ##### TO FIX 22/09/2021
                            
                            self._strm=self._process.start()
                            self._strm.set_read_timeout_function(self._strm_read_timeout)
                            self._process_last_error=None
                            self._process_status="started"
                    if self._process_status=="started":
                        jo = self._strm.read_obj()
                        if jo==None:
                            raise Exception("Stream closed")
                        sreq = jo["request"]
                        if sreq==u"MONITORS_CHANGED":
                            bwrite=False
                            self._semaphore.acquire()
                            try:
                                self._destroy_monitors_nosync()
                                if "error_code" in jo:
                                    self._monitors={"list": jo["monitors"], "error_code": jo["error_code"]}                                    
                                else:
                                    self._monitors={"list": jo["monitors"]}
                                    self._monitorsid+=1
                                    self._monitors["id"]=self._monitorsid
                                    szmmap=1 
                                    for i in range(len(self._monitors["list"])):
                                        mon = self._monitors["list"][i]
                                        mon["pos"]=szmmap
                                        l=1+8+ctypes.sizeof(common.RGB_IMAGE)+(mon["width"]*mon["height"]*3)                                
                                        szmmap+=l
                                    #CURSOR
                                    l=ctypes.sizeof(common.CURSOR_IMAGE)+8+common.MAX_CURSOR_IMAGE_SIZE
                                    self._monitors["curpos"]=szmmap
                                    szmmap+=l
                                    #FPS
                                    self._monitors["fpspos"]=szmmap
                                    szmmap+=1                                                                
                                    memmap = ipc.MemMap(szmmap, fixperm=self._process.get_fixperm())
                                    memmap.seek(0)
                                    memmap.write(b"O")
                                    memmap.write(self._struct_Q.pack(0))                                                                
                                    self._monitors["memmap"]=memmap
                                    self._monitors["cond"]=ipc.Condition(fixperm=self._process.get_fixperm())
                                    bwrite=True
                            finally:
                                self._semaphore.release()
                            if bwrite:
                                self._write_obj({u"request":u"INIT_SCREEN_CAPTURE",u"monitors":self._monitors})                                
                        elif sreq==u"SOUND_STATUS":
                            bwrite=False
                            self._semaphore.acquire()
                            try:
                                self._destroy_sound_nosync()
                                self._sound_status=jo
                                if self._sound_status["status"]==u"OK":
                                    szmmap=1+8+8+jo["memmap_size"]
                                    self._sound_status["memmap_size"] = jo["memmap_size"]
                                    self._sound_status["memmap"] = ipc.MemMap(szmmap, fixperm=self._process.get_fixperm())
                                    self._sound_status["memmap"].seek(0)
                                    self._sound_status["memmap"].write(b"O")
                                    self._sound_status["memmap"].write(self._struct_Q.pack(0))                                    
                                    self._sound_status["cond"]=ipc.Condition(fixperm=self._process.get_fixperm())
                                    bwrite=True
                            finally:
                                self._semaphore.release()
                            if bwrite:
                                self._write_obj({u"request":u"INIT_SOUND_CAPTURE",u"cond":self._sound_status["cond"],u"memmap":self._sound_status["memmap"]})
                        elif sreq==u"COPY_TEXT":
                            self._last_copy_text=jo["text"]
                        elif sreq==u"RAISE_ERROR":
                            if "capture_fallback_lib" in jo:
                                self._agent_main._app_desktop_capture_fallback_lib=jo["capture_fallback_lib"]
                                if "message" in jo:
                                    self._agent_main.write_err("AppDesktop:: Process capture error: " + jo["message"]) 
                                self._agent_main.write_err("AppDesktop:: Process capture fallback library: " + self._agent_main._app_desktop_capture_fallback_lib)                               
                            else:
                                self._agent_main._app_desktop_capture_fallback_lib=None
                                self.destroy()
                            self._process_last_error=jo["message"]
                            self._destroy_process()
                    else:
                        time.sleep(1)
                except:
                    e = utils.get_exception()
                    strmsg=utils.exception_to_string(e)                    
                    self._process_last_error=strmsg
                    if strmsg=="XWayland is not supported.":
                        self.destroy()                    
                    self._destroy_process()
                    if not self.is_destroy():
                        self._agent_main.write_err("AppDesktop:: Process capture error: " + self._process_last_error)
                    time.sleep(1)
        except:
            try:
                e = utils.get_exception()
                self._process_last_error=utils.exception_to_string(e)
            except:
                self._process_last_error="Process not started."
        self.destroy()
        self._destroy_process()
        if self._process is not None:
            self._process.join(2)
            self._process=None
        #UNLOAD DLL
        self._term_screen_module()
        self._term_sound_module()
               
        
        
    def inputs(self, mon, sinps):
        bok = True
        if utils.is_windows() and "CTRLALTCANC" in sinps:
            if self._screen_module.DWAScreenCaptureSAS():
                bok = False            
        if bok: 
            self._write_obj({u"request":u"INPUTS",u"monitor":mon,u"inputs":sinps})
    
    def copy_text(self, mon):
        self._last_copy_text=None
        self._write_obj({u"request":u"COPY_TEXT",u"monitor":mon})
            
    def paste_text(self, mon, stxt):
        self._write_obj({u"request":u"PASTE_TEXT",u"monitor":mon, u"text": stxt})
            
        


class DesktopSession(threading.Thread):
        
    def __init__(self, dskmain, cinfo, sid,  wsock):
        threading.Thread.__init__(self,  name="DesktopSession" + sid)
        self._struct_h=struct.Struct("!h")
        self._struct_hh=struct.Struct("!hh")
        self._struct_hb=struct.Struct("!hb")
        self._struct_B=struct.Struct("!B")
        self._dskmain=dskmain
        self._process=self._dskmain._process
        self._cinfo=cinfo
        prms = cinfo.get_permissions()
        if prms["fullAccess"]:
            self._allow_inputs=True
            self._allow_audio=True
        else:
            pret=self._dskmain._agent_main.get_app_permission(cinfo,"desktop")
            if pret["fullAccess"]:
                self._allow_inputs=True
                self._allow_audio=True
            else:
                if "allowScreenInput" in pret:
                    self._allow_inputs=pret["allowScreenInput"]
                else:
                    self._allow_inputs=False
                if "allowAudio" in pret:
                    self._allow_audio=pret["allowAudio"]
                else:
                    self._allow_audio=True
        
        self._prop=wsock.get_properties()
        self._idses=cinfo.get_idsession()
        self._id=sid
        self._bdestroy=False
        self._websocket=wsock
        self._keepalive_counter = None
        self._keepalive_send = False        
        self._websocket.accept(10,{"on_close": self._on_websocket_close,"on_data":self._on_websocket_data})
        self._websocket_send_lock = threading.RLock()
        self._cursor_visible = True
        self._supported_frame=None
        self._process_id=-1        
        self._monitor=-1
        self._monitor_count=-1
        self._frame_type=-1 # 0=DATA_PALETTE_COMPRESS_V1; 100=DATA_TJPEG_v1"; 101=DATA_TJPEG_v2"
        self._frame_type_to_send=False
        self._frame_in_progress=False        
        self._frame_intervall_fps_min=5.0
        self._frame_intervall_fps=self._frame_intervall_fps_min
        self._frame_intervall_wait=1.0/self._frame_intervall_fps        
        self._frame_intervall_time_counter=utils.Counter()                
        self._frame_distance=0
        self._audio_type=-1
        self._audio_type_to_send=False
        self._audio_enable=True
        self._slow_mode=False
        self._slow_mode_counter=None
        self._ping=-1
        self._ping_sent=False
        self._ping_counter=None        
        self._send_stats = False
        self._stats_counter=None
        self._stats_capture_fps=0
        self._stats_sent_size=[]
        self._stats_sent_frame=0
        self._stats_sent_bytes=0
        self._stats_ffps=0
        self._stats_bps=0
        self._stats_frame_value=[]
        self._stats_bytes_value=[]        
        self._stats_time=[]
        self._stat_ffps_itf=1.0
        self._stat_max_distance_tm=0                
        self._semaphore_st=threading.Condition()
        self._quality=9
        self._quality_detect_value=9        
        self._quality_detect_counter=None
        self._quality_detect_wait=0.0                
        self._quality_request=-1
        self._process_encoder=None
        self._process_encoder_stream=None
        self._process_encoder_alive=False
        self._process_encoder_event=None
        self._process_encoder_read_thread=None
        self._process_encoder_monitorsid=-1
        self._process_encoder_init=False                        
        self._init_session_to_send=True
        self._init_counter=utils.Counter()
        self._init_err_msg=None
        self._debug_forcesubprocess=False
        try:
            self._debug_forcesubprocess=self._dskmain._agent_main.get_config("desktop.debug_forcesubprocess",False)
        except:
            None
            
        ##### TO FIX 22/09/2021
        try:
            utils.Bytes()
            self._send_list_bytes=self._send_list_bytes_OLD
            self._send_bytes=self._send_bytes_OLD
            self._decode_data=self._decode_data_OLD            
        except:
            self._send_list_bytes=self._send_list_bytes_NEW
            self._send_bytes=self._send_bytes_NEW
            self._decode_data=self._decode_data_NEW
        ##### TO FIX 22/09/2021
            
    def get_id(self):
        return self._id
    
    def get_idses(self):
        return self._idses
    
    def _on_websocket_data(self,websocket,tpdata,data):
        if not self._bdestroy:
            try:
                if self._keepalive_counter is not None:
                    self._keepalive_counter.reset()                
                prprequest = json.loads(self._decode_data(data))
                if prprequest is not None and "frametime" in prprequest:
                    #print("frame received. Time: " + prprequest["frametime"])                    
                    tm = float(prprequest["frametime"])
                    self.received_frame(tm)
                if prprequest is not None and "inputs" in prprequest:
                    if not self._allow_inputs:
                        raise Exception("Permission denied (inputs).")                    
                    self._process.inputs(self._monitor,prprequest["inputs"])                                                                
                if prprequest is not None and "cursor" in prprequest:
                    if prprequest["cursor"]=="true":
                        self._cursor_visible=True
                    elif prprequest["cursor"]=="false":
                        self._cursor_visible=False
                if prprequest is not None and "monitor" in prprequest:                    
                    self._monitor = int(prprequest["monitor"])                    
                    if prprequest is not None and "acceptFrameType" in prprequest:
                        arft = prprequest["acceptFrameType"].split(";")
                        if self._supported_frame is not None:
                            for f in range (len(self._supported_frame)):
                                tf=self._supported_frame[f]                            
                                for i in range(len(arft)):
                                    if int(arft[i])==tf:
                                        self._frame_type=tf
                                        self._frame_type_to_send=True
                                        break
                                if self._frame_type_to_send==True:
                                    break
                    
                    if prprequest is not None and "acceptAudioType" in prprequest:
                        if not self._allow_audio:
                            raise Exception("Permission denied (audio).")
                        arft = prprequest["acceptAudioType"].split(";")
                        for i in range(len(arft)):
                            v = int(arft[i])
                            if v==0:
                                self._audio_type=v
                                self._audio_type_to_send=True                                                                
                                break
                    try:
                        if self._process_encoder_event is not None:
                            self._process_encoder_event.set()                            
                    except:
                        None
                            
                if prprequest is not None and "slow" in prprequest:
                    self._slow_mode=prprequest["slow"]=="true"
                if prprequest is not None and "quality" in prprequest:
                    self._quality_request=int(prprequest["quality"])
                if prprequest is not None and "keepalive" in prprequest:
                    if self._keepalive_counter is None:
                        self._keepalive_counter = utils.Counter()
                    self._keepalive_send = True
                if prprequest is not None and "audioEnable" in prprequest:
                    self._audio_enable=prprequest["audioEnable"]=="true"
                if prprequest is not None and "sendStats" in prprequest:
                    b=prprequest["sendStats"]=="true"                    
                    self._send_stats=b
            except:
                ex = utils.get_exception()
                if self._process.get_status()=="started":
                    self._dskmain._agent_main.write_err("AppDesktop:: on_websoket_data error. ID: " + self._id + " - Error:" + utils.exception_to_string(ex))            
            
   
    def _on_websocket_close(self):
        self.destroy();
    
    ##### TO FIX 22/09/2021
    def _decode_data_OLD(self,data):
        return data.to_str("utf8")
    
    def _decode_data_NEW(self,data):        
        return data.decode("utf8")
    
    def _send_bytes_NEW(self, bts):
        with self._websocket_send_lock:
            self._websocket.send_bytes(bts)
    
    def _send_list_bytes_NEW(self, bts):
        with self._websocket_send_lock:
            self._websocket.send_list_bytes(bts)
    
    def _send_bytes_OLD(self, bts):
        with self._websocket_send_lock:
            self._websocket.send_bytes(utils.Bytes(bts))
    
    def _send_list_bytes_OLD(self, bts):
        with self._websocket_send_lock:
            self._websocket.send_list_bytes(map(lambda b: utils.Bytes(b), bts))
    ##### TO FIX 22/09/2021
    
    def check_destroy(self):
        if self._init_counter is not None and self._init_counter.is_elapsed(15):
            if self._process.get_status()=="started":
                self._init_err_msg = "Session not started."
            else:
                appmsg = self._process.get_last_error()
                if appmsg is None:
                    appmsg="Process not started."
                self._init_err_msg = appmsg 
            raise Exception(self._init_err_msg)
        if self._keepalive_counter is not None and self._keepalive_counter.is_elapsed(10.0):
            self._init_err_msg = None
            self.destroy()
            return False
        else:
            if self._keepalive_send:
                self._keepalive_send=False
                bts=self._struct_h.pack(common.TOKEN_SESSION_ALIVE)
                self._send_bytes(bts)
        if self._process_encoder is not None and not self._process_encoder.is_running():
            return False
        return not self.is_destroy() and not self._process.is_destroy()

    def _strm_read_timeout(self, strm):
        return not self.check_destroy()
        
    def received_frame(self,tm): 
        #CALCULATE PING
        if self._ping_sent:
            self._ping=self._ping_counter.get_value()
            self._ping_counter.reset()
            self._ping_sent=False
            return
        self._semaphore_st.acquire()
        try:
            self._received_frame_nosync()
            self._semaphore_st.notify_all()
        finally:
            self._semaphore_st.release()
    
    def _received_frame_nosync(self):        
        self._frame_distance-=1
        self._stats_sent_frame+=1
        self._stats_sent_bytes+=self._stats_sent_size.pop(0)
        
        if self._stats_counter is None: #FIRST FRAME
            self._stats_counter=utils.Counter()
            self._slow_mode_counter=utils.Counter()
        
        #self.calc_stats()    
            
    def send_init_session(self):
        #SEND ID        
        sdataid=self._struct_h.pack(common.TOKEN_SESSION_ID)+TMP_str_to_bytes(self._id)
        self._send_bytes(sdataid)
    
        #START KEEP ALIVE MANAGER
        self._send_bytes(self._struct_h.pack(common.TOKEN_SESSION_ALIVE))
        
        #TYPE=11 DATA=CNT-S1-S2-... -> SUPPORTED FRAME            
        self._supported_frame=self._process.get_supported_frame()
        spar = []
        spar.append(self._struct_hh.pack(common.TOKEN_SUPPORTED_FRAME,3))
        for sf in self._supported_frame:
            spar.append(self._struct_h.pack(sf))
        self._send_bytes(TMP_bytes_join(spar))
    
    
    def calc_stats(self):
        if self._stats_counter is not None and self._stats_counter.is_elapsed(1):
            apptm = self._stats_counter.get_value()
            self._stats_counter.reset()                    
            self._stats_frame_value.append(self._stats_sent_frame)
            self._stats_bytes_value.append(self._stats_sent_bytes)            
            self._stats_time.append(apptm)            
            if len(self._stats_frame_value)>1:
                self._stats_frame_value.pop(0)
                self._stats_bytes_value.pop(0)
                self._stats_time.pop(0)                          
                        
            stm = sum(self._stats_time)
            self._stats_ffps=float(sum(self._stats_frame_value))/stm
            self._stats_sent_frame=0
            self._stats_bps=int(float(sum(self._stats_bytes_value))/stm)
            self._stats_sent_bytes=0            
            if self._stats_ffps>0:
                self._stat_ffps_itf=1.0/self._stats_ffps
                self._stat_max_distance_tm=1.0
                if self._ping>=0:
                    self._stat_max_distance_tm+=self._ping
            else:
                self._stat_ffps_itf=1.0
                self._stat_max_distance_tm=0            
            appcheck = self._frame_intervall_fps/3.0
            
            bchange=False
            if self._stats_ffps<appcheck:
                self._frame_intervall_fps=self._frame_intervall_fps/1.5
                bchange=True
            elif self._stats_ffps>appcheck*2.0:
                self._frame_intervall_fps=self._frame_intervall_fps*1.5
                bchange=True
            if bchange==True:
                if self._frame_intervall_fps<self._frame_intervall_fps_min:
                    self._frame_intervall_fps=self._frame_intervall_fps_min
                self._frame_intervall_wait=1.0/self._frame_intervall_fps
                
            if self._send_stats is True:
                try:
                    jostats = {}
                    jostats["fps"]=int(self._stats_ffps) 
                    jostats["fpsmax"]=int(self._frame_intervall_fps)
                    jostats["fpscap"]=int(self._stats_capture_fps)
                    jostats["bps"]=self._stats_bps
                    if self._stats_ffps>0:
                        jostats["tdiff"]=int(self._frame_distance*(1000.0/self._stats_ffps))
                    else:
                        jostats["tdiff"]=0
                    jostats["fdiff"]=self._frame_distance
                    if self._ping==-1:
                        jostats["ping"]=0
                    else:
                        jostats["ping"]=int(self._ping*1000)                        
                    jostats["qa"]=self._quality
                    apps=json.dumps(jostats)                    
                    ba=bytearray(apps,"utf8")
                    ba[0:0]=self._struct_h.pack(common.TOKEN_SESSION_STATS)
                    self._send_bytes(ba)
                except:
                    print(utils.get_exception())
        
    
    def detect_qa(self):
        if self._quality_request==-1 and self._slow_mode is False: #DA SISTEMARE
            if self._quality_detect_counter is None:
                self._quality_detect_counter=utils.Counter()
            if self._quality_detect_counter.is_elapsed(1):                
                self._quality_detect_wait-=(self._ping/2.0)
                if self._quality_detect_wait<0:
                    self._quality_detect_wait=0                
                perc = self._quality_detect_wait/self._quality_detect_counter.get_value()
                #print(TMP_str_new(perc)
                if perc>=0.7:
                    if self._quality_detect_value>0:
                        self._quality_detect_value-=1
                if perc<=0.3 and self._stats_ffps>self._frame_intervall_fps_min:
                    if self._quality_detect_value<9:
                        self._quality_detect_value+=1
                
                self._quality_detect_counter.reset()
                self._quality_detect_wait=0.0
        else:
            self._quality_detect_counter=None
            self._quality_detect_wait=0.0
    
    def wait_screen_distance(self):
        w = self._frame_intervall_wait-self._frame_intervall_time_counter.get_value()
        if w>0:
            time.sleep(w)
        self._frame_intervall_time_counter.reset()
        self._semaphore_st.acquire()
        try:
            if self._slow_mode_counter is not None:
                self._slow_mode_counter.reset()
            while self.check_destroy() and self._process.get_status()=="started" and self._process.get_id()==self._process_id:
                bwait=False
                if self._frame_type!=-1 and self._monitor!=-1:
                    self.calc_stats()
                    self.detect_qa()
                    bwait=self._frame_distance*self._stat_ffps_itf>self._stat_max_distance_tm
                    if (not bwait and (self._slow_mode is False or self._slow_mode_counter is None or self._slow_mode_counter.is_elapsed(4)) and
                        self._frame_in_progress==False):
                        return True
                apptm = time.time()
                self._semaphore_st.wait(0.25)
                elp = time.time()-apptm
                if self._quality_detect_counter is not None and bwait==True and elp>0.0:
                    self._quality_detect_wait+=elp
        finally:
            self._semaphore_st.release()
        return False
    
    def _destroy_process_encoder(self, bforce=False):
        if self._process_encoder_init==True or bforce==True:
            if self._process_encoder_stream is not None:
                self._process_encoder_stream.close()
                self._process_encoder_stream=None        
            try:
                if self._process_encoder_event is not None:
                    self._process_encoder_event.set()
            except:
                None
            if self._process_encoder is not None:
                self._process_encoder.close()
                self._process_encoder.join(1)
                self._process_encoder=None
            self._process_encoder_init=False
        
        self._process_encoder_monitorsid=-1
        self._frame_in_progress=False
    
    def _strm_process_encoder_read_timeout(self, strm):
        return self.is_destroy()
    
    def _process_encoder_read(self):
        while True:
            sdata = None
            try: 
                sdata = self._process_encoder_stream.read_bytes()
            except:
                None
            if sdata==None:
                break 
            self._init_counter=None
            if len(sdata)>0:
                lst=[]
                tp = self._struct_h.unpack(sdata[0:2])[0]                
                if tp==common.TOKEN_FRAME:
                    #CALCULATE PING
                    if self._ping_counter is None or (self._ping_counter.is_elapsed(5) and sum(self._stats_sent_size)==0 and self._frame_distance==0):
                        if self._ping_counter is None:
                            self._ping_counter = utils.Counter()
                        else:
                            self._ping_counter.reset()
                        self._ping_sent=True
                        lst.append(self._struct_h.pack(common.TOKEN_FRAME_TIME)+TMP_str_to_bytes(TMP_str_new(time.time())))
                        lst.append(self._struct_hb.pack(2,1))
                        self._send_list_bytes(lst)
                        lst=[]
                    
                    bsend=True
                    self._semaphore_st.acquire()
                    try:
                        p = len(self._stats_sent_size)-1
                        if p==-1:
                            p=0
                            self._stats_sent_size.append(int(len(sdata)))
                        else:
                            self._stats_sent_size[p]+=int(len(sdata))
                        if TMP_bytes_get(sdata,2)==1:
                            self._frame_distance+=1
                            if self._stats_sent_size[p]==3:
                                self._stats_sent_size[p]=0
                                self._received_frame_nosync()
                                bsend=False
                            self._stats_sent_size.append(0)                        
                        self._semaphore_st.notify_all()
                    finally:
                        self._semaphore_st.release()                    
                    if bsend:                    
                        if TMP_bytes_get(sdata,2)==1:
                            lst.append(self._struct_h.pack(common.TOKEN_FRAME_TIME)+TMP_str_to_bytes(TMP_str_new(time.time())))
                        lst.append(sdata)
                        #print("frame sent. Time: " + TMP_str_new(tm))
                elif tp==common.TOKEN_CURSOR:
                    if self._cursor_visible==True:
                        lst.append(sdata)
                elif tp==common.TOKEN_AUDIO_DATA: #TOKEN AUDIO
                    if self._audio_type_to_send==False:
                        lst.append(sdata)
                elif tp==common.TOKEN_FPS:
                    self._stats_capture_fps=self._struct_B.unpack(sdata[2:3])[0]
                else:
                    lst.append(sdata)
                                                    
                if len(lst)>0 and self._websocket is not None:
                    self._send_list_bytes(lst)            
            else:
                self._semaphore_st.acquire()
                try:
                    self._frame_in_progress=False
                    if self._quality_detect_counter is not None:
                        self._quality_detect_counter.start()
                    self._semaphore_st.notify_all()
                finally:
                    self._semaphore_st.release()
                
    def run(self):
        baudioenable=None
        bframelocked=False
        try:
            self._cinfo.inc_activities_value("screenCapture")
        except:
            None        
        try:
            while self.check_destroy():
                if self._process_encoder==None:
                    self._process_encoder = ipc.Process("app_desktop.encoder", "ProcessEncoder", forcesubprocess=self._debug_forcesubprocess)
                    self._process_encoder_stream = self._process_encoder.start()
                    self._process_encoder_stream.set_read_timeout_function(self._strm_process_encoder_read_timeout)
                    self._process_encoder_read_thread=threading.Thread(target=self._process_encoder_read, name="DesktopSessionProcessRead" + TMP_str_new(self._id))
                    self._process_encoder_read_thread.start()
                                        
                if self._process.get_status()=="started":                    
                    if self._process.get_id()!=self._process_id:
                        self._destroy_process_encoder()
                        self._process_id=self._process.get_id()
                else:
                    self._destroy_process_encoder()
                
                if self._process.get_status()=="started" and self._process_encoder is not None:
                    monitors=self._process.get_monitors()
                    if monitors is None:
                        time.sleep(0.25)
                    else:
                        if self._init_session_to_send==True:
                            self._init_session_to_send=False
                            self.send_init_session()
                        if self._monitor_count!=len(monitors["list"]):
                            #TYPE=10 DATA=SZ -> MONITOR COUNT
                            self._monitor_count=len(monitors["list"])
                            if self._monitor_count==0 and "error_code" in monitors:
                                if bframelocked==False:
                                    bframelocked=True
                                    self._send_bytes(self._struct_h.pack(common.TOKEN_FRAME_LOCKED))
                            else:
                                if bframelocked==True:
                                    bframelocked=False
                                    self._send_bytes(self._struct_h.pack(common.TOKEN_FRAME_UNLOCKED))
                                self._send_bytes(self._struct_hh.pack(common.TOKEN_MONITOR,self._monitor_count))
                        
                        if self._frame_type!=-1 and self._monitor!=-1 and self._monitor_count>0:
                            try:
                                if self._process_encoder_init==False:
                                    self._process_encoder_event = ipc.Event()
                                    self._process_encoder_stream.write_obj({u"request":u"INIT",u"event":self._process_encoder_event,u"image_type":self._frame_type})
                                    self._process_encoder_init=True
                                                                                
                                if self._process_encoder_monitorsid!=monitors["id"]:
                                    self._process_encoder_stream.write_obj({u"request":u"SET_MONITORS",u"monitors":monitors})
                                    self._process_encoder_monitorsid=monitors["id"]                                
                                
                                soundstatus=self._process.get_sound_status()
                                if soundstatus is not None:
                                    if self._audio_type_to_send==True:
                                        self._audio_type_to_send=False
                                        if soundstatus["status"]==u"OK":
                                            self._send_bytes(self._struct_hh.pack(common.TOKEN_AUDIO_TYPE,0)) #0=opus
                                            self._process_encoder_stream.write_obj({u"request":u"START_SOUND", u"status":soundstatus})
                                            baudioenable=True
                                        else:
                                            err_msg="Unknown error."
                                            if "message" in soundstatus:
                                                err_msg=soundstatus["message"]
                                            ba=bytearray(err_msg,"utf8")
                                            ba[0:0]=self._struct_h.pack(common.TOKEN_AUDIO_ERROR)                                            
                                            self._send_bytes(ba)
                                    if baudioenable is not None and self._audio_enable!=baudioenable:
                                        baudioenable=not baudioenable
                                        self._process_encoder_stream.write_obj({u"request":u"SET_SOUND_ENABLE", u"value":baudioenable})                                    
                                
                                if self._frame_type_to_send==True:
                                    self._frame_type_to_send=False
                                    self._send_bytes(self._struct_hh.pack(common.TOKEN_FRAME_TYPE,self._frame_type))                                                    
                                
                                if self.wait_screen_distance():
                                    if self._quality_request!=-1:
                                        self._quality=self._quality_request
                                    else:
                                        self._quality=self._quality_detect_value
                                        #if self._quality_detect_value!=-1:
                                        #    self._quality=self._quality_detect_value
                                        #    self._quality_detect_value=-1
                                    self._frame_in_progress=True
                                    if self._quality_detect_counter is not None:
                                        self._quality_detect_counter.stop()
                                    self._process_encoder_stream.write_obj({u"request":u"ENCODE", u"monitor":self._monitor, u"quality":self._quality,u"send_buffer_size":self._websocket.get_send_buffer_size()})
                            except:
                                self._destroy_process_encoder()
                        else:        
                            time.sleep(0.25)
                else:        
                    time.sleep(0.25)
                
        except:
            e = utils.get_exception()
            if not self.is_destroy():
                if self._dskmain._agent_main._agent_debug_mode:
                    self._dskmain._agent_main.write_err(utils.get_stacktrace_string())                
                appmsg = self._process.get_last_error()
                if appmsg is None:
                    appmsg = utils.exception_to_string(e)
                self._dskmain._agent_main.write_err("AppDesktop:: session id: " + self._id + " error: "  + appmsg)                
        
        try:
            self._cinfo.dec_activities_value("screenCapture")
        except:
            None
        
        bsndmsg = not (self._process_encoder is not None and not self._process_encoder.is_running())
        self._destroy_process_encoder(True)
        if not self.is_destroy():
            if bsndmsg:            
                if self._init_err_msg is None:
                    appmsg = self._process.get_last_error()
                    if appmsg is None:
                        appmsg="Process not started."
                    self._init_err_msg=appmsg
                try:
                    self._send_bytes(self._struct_h.pack(common.TOKEN_SESSION_ERROR) + self._init_err_msg.encode("ascii", errors='replace'))
                except:
                    None
            self.destroy()
        if self._websocket is not None:
            self._websocket.close()
            self._websocket=None
        
        self._dskmain._rem_desktop_manager(self._id)
        self._id=None        
        
    def copy_text(self):
        if not self._allow_inputs:
            raise Exception("Permission denied (inputs).")
        self._process.copy_text(self._monitor)
        cnt = utils.Counter()
        while True:
            apps = self._process.get_last_copy_text()
            if apps is not None:
                return apps
            time.sleep(0.5)
            if self.is_destroy() or cnt.is_elapsed(10):
                return ""        
    
    def paste_text(self,s):
        if not self._allow_inputs:
            raise Exception("Permission denied (inputs).")
        if s is not None:
            self._process.paste_text(self._monitor,s)
    
    def destroy(self):
        self._bdestroy=True             
    
    def is_destroy(self):
        return self._bdestroy    
 
     
