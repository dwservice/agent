# -*- coding: utf-8 -*-

'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''

import ctypes
import utils
import os
import stat
import subprocess
import sys
import time
import sharedmem
import threading
import signal
import json

GUILNC_ARG_MAX=10
GUILNC_ARG_SIZE=1024

_nativemap={}
_nativemap["semaphore"] = threading.Condition()

def get_instance():
    oret=None
    _nativemap["semaphore"].acquire()
    try:
        if "instance" in _nativemap:
            oret=_nativemap["instance"]
        else:
            if utils.is_windows():
                oret = Windows()
            elif utils.is_linux():
                oret = Linux()
            elif utils.is_mac():
                oret = Mac()
            oret.load_library();
            _nativemap["instance"]=oret
    finally:
        _nativemap["semaphore"].release()
    return oret

def fmain(args):
    if utils.is_mac():
        if len(args)>1:
            a1=args[1]
            if a1 is not None and a1.lower()=="guilnc":
                main = Mac()
                main.start_guilnc()
                sys.exit(0)

def get_suffix():
    if utils.is_windows():
        return "win"
    elif utils.is_linux():
        return "linux"
    elif utils.is_mac():
        return "mac"
    return None

def get_library_config(name):
    fn=None
    if utils.path_exists(".srcmode"):
        fn=".." + utils.path_sep + "lib_" + name + utils.path_sep + "config.json"        
    else:
        fn="native" + utils.path_sep + "lib_" + name + ".json"
    if utils.path_exists(fn):
        f = utils.file_open(fn)
        jsapp = json.loads(f.read())
        f.close()
        return jsapp
    else:
        return None

def _load_libraries_with_deps(ar,name):
    cnflib=get_library_config(name)
    if "lib_dependencies" in cnflib:
        for ln in cnflib["lib_dependencies"]:
            _load_libraries_with_deps(ar,ln)
    fn = cnflib["filename_" + get_suffix()]
    ar.insert(0,_load_lib_obj(fn))

def load_libraries_with_deps(name):
    lstlibs=[]
    _load_libraries_with_deps(lstlibs,name)
    return lstlibs

def unload_libraries(lstlibs):
    for i in range(len(lstlibs)):
        _unload_lib_obj(lstlibs[i])

def _load_lib_obj(name):
    retlib = None
    if utils.is_windows():
        if not utils.path_exists(".srcmode"):
            retlib = ctypes.CDLL("native\\" + name)
        else:
            retlib = ctypes.CDLL("..\\make\\native\\" + name)
        if retlib is None:
            raise Exception("Missing library " + name + ".")
    elif utils.is_linux():
        if not utils.path_exists(".srcmode"):
            retlib  = ctypes.CDLL("native/" + name, ctypes.RTLD_GLOBAL)
        else: 
            retlib = ctypes.CDLL("../make/native/" + name, ctypes.RTLD_GLOBAL)
        if retlib is None:
            raise Exception("Missing library " + name + ".")
    elif utils.is_mac():
        if not utils.path_exists(".srcmode"):
            retlib  = ctypes.CDLL("native/" + name, ctypes.RTLD_GLOBAL)
        else: 
            retlib = ctypes.CDLL("../make/native/" + name, ctypes.RTLD_GLOBAL)
        if retlib is None:
            raise Exception("Missing library " + name + ".")
    return retlib;
    

def _unload_lib_obj(olib):
    if olib is not None:
        try:
            if utils.is_windows():
                import _ctypes
                _ctypes.FreeLibrary(olib._handle)
                del olib
            elif utils.is_linux():
                import _ctypes
                _ctypes.dlclose(olib._handle)
                del olib
            elif utils.is_mac():
                import _ctypes
                _ctypes.dlclose(olib._handle)
                del olib
        except:
            None
'''
del olib
    olib.dlclose(olib._handle)
while isLoaded('./mylib.so'):
    dlclose(handle)

It's so unclean that I only checked it works using:

def isLoaded(lib):
   libp = utils.path_absname(lib)
   ret = os.system("lsof -p %d | grep %s > /dev/null" % (os.getpid(), libp))
   return (ret == 0)

def dlclose(handle)
   libdl = ctypes.CDLL("libdl.so")
   libdl.dlclose(handle)
'''

class Windows():
        
    def __init__(self):
        self._dwaglib=None

    def load_library(self):
        if self._dwaglib is None:
            self._dwaglib = _load_lib_obj("dwaglib.dll");
    
    def unload_library(self):
        _unload_lib_obj(self._dwaglib)
        self._dwaglib=None
    
    def get_library(self):
        return self._dwaglib

    def task_kill(self, pid) :
        bret = self._dwaglib.taskKill(pid)
        return bret==1
    
    def is_task_running(self, pid):
        bret=self._dwaglib.isTaskRunning(pid);
        return bret==1
    
    def set_file_permission_everyone(self,file):
        self._dwaglib.setFilePermissionEveryone(file)    
    
    def fix_file_permissions(self,operation,path,path_src=None):
        None
               
    def is_gui(self):
        return True 

class Linux():
    
    def __init__(self):
        self._dwaglib=None
    
    def load_library(self):
        try:
            if self._dwaglib is None:
                self._dwaglib = _load_lib_obj("dwaglib.so")
        except:
            None
    
    def unload_library(self):
        _unload_lib_obj(self._dwaglib)
        self._dwaglib=None
    
    def get_library(self):
        return self._dwaglib 
    
    def task_kill(self, pid) :
        try:
            os.kill(pid, -9)
        except OSError:
            return False
        return True
    
    def is_task_running(self, pid):
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True
    
    def set_file_permission_everyone(self,f):
        utils.path_change_permissions(f, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH)
    
        
    def fix_file_permissions(self,operation,path,path_template=None):
        apppath=path
        if apppath.endswith(utils.path_sep):
            apppath=apppath[0:len(apppath)-1]
        apppath_template=path_template
        if apppath_template is not None:
            if apppath_template.endswith(utils.path_sep):
                apppath_template=apppath_template[0:len(apppath_template)-1]
        
        if operation=="CREATE_DIRECTORY":
            apppath_template=utils.path_dirname(path)    
            stat_info = utils.path_stat(apppath_template)
            mode = stat.S_IMODE(stat_info.st_mode)
            utils.path_change_permissions(path,mode)
            utils.path_change_owner(path, stat_info.st_uid, stat_info.st_gid)
        elif operation=="CREATE_FILE":
            apppath_template=utils.path_dirname(path)    
            stat_info = utils.path_stat(apppath_template)
            mode = stat.S_IMODE(stat_info.st_mode)
            utils.path_change_permissions(path, ((mode & ~stat.S_IXUSR) & ~stat.S_IXGRP) & ~stat.S_IXOTH)
            utils.path_change_owner(path, stat_info.st_uid, stat_info.st_gid)
        elif operation=="COPY_DIRECTORY" or operation=="COPY_FILE":
            if apppath_template is not None:
                stat_info = utils.path_stat(apppath_template)
                mode = stat.S_IMODE(stat_info.st_mode)
                utils.path_change_permissions(path,mode)
                stat_info = utils.path_stat(utils.path_dirname(path)) #PRENDE IL GRUPPO E L'UTENTE DELLA CARTELLA PADRE 
                utils.path_change_owner(path, stat_info.st_uid, stat_info.st_gid)
        elif operation=="MOVE_DIRECTORY" or operation=="MOVE_FILE":
            if apppath_template is not None:
                stat_info = utils.path_stat(apppath_template)
                mode = stat.S_IMODE(stat_info.st_mode)
                utils.path_change_permissions(path,mode)
                utils.path_change_owner(path, stat_info.st_uid, stat_info.st_gid)
        
    def is_gui(self):
        try:
            import detectinfo
            appnsfx = detectinfo.get_native_suffix()
            if not appnsfx=="linux_generic":
                appout = subprocess.Popen("ps ax -ww | grep 'X.*-auth .*'", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate() 
                lines = appout[0].splitlines()
                for l in lines:
                    if 'X.*-auth .*' not in l:
                        return True
        except:
            None
        return False
    

class Mac():
        
    def __init__(self):
        self._dwaglib = None
        self._propguilnc = None
        self._propguilnc_semaphore = threading.Condition()        
    
    def load_library(self):
        try:
            if self._dwaglib is None:
                lbn="dwaglib.dylib"
                #COMPATIBILITY BEFORE 14/11/2019
                if not utils.path_exists(".srcmode"):
                    if not utils.path_exists("native/"+lbn):
                        lbn="dwaglib.so"
                #COMPATIBILITY BEFORE 14/11/2019
                self._dwaglib = _load_lib_obj(lbn)
        except:
            None
    
    def unload_library(self):
        _unload_lib_obj(self._dwaglib)
        self._dwaglib=None
    
    def get_library(self):        
        return self._dwaglib
    
    def task_kill(self, pid) :
        try:
            os.kill(pid, -9)
        except OSError:
            return False
        return True
    
    def is_task_running(self, pid):
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True
    
    def set_file_permission_everyone(self,f):
        utils.path_change_permissions(f, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH)
    
    def fix_file_permissions(self,operation,path,path_src=None):
        apppath=path
        if apppath.endswith(utils.path_sep):
            apppath=apppath[0:len(apppath)-1]
        apppath_src=path_src
        if apppath_src is not None:
            if apppath_src.endswith(utils.path_sep):
                apppath_src=apppath_src[0:len(apppath_src)-1]
        else:
            apppath_src=utils.path_dirname(path)    
        stat_info = utils.path_stat(apppath_src)
        mode = stat.S_IMODE(stat_info.st_mode)
        if operation=="CREATE_DIRECTORY":
            utils.path_change_permissions(path,mode)
            utils.path_change_owner(path, stat_info.st_uid, stat_info.st_gid)
        elif operation=="CREATE_FILE":
            utils.path_change_permissions(path, ((mode & ~stat.S_IXUSR) & ~stat.S_IXGRP) & ~stat.S_IXOTH)
            utils.path_change_owner(path, stat_info.st_uid, stat_info.st_gid)
        elif operation=="COPY_DIRECTORY" or operation=="COPY_FILE":
            utils.path_change_permissions(path,mode)
            stat_info = utils.path_stat(utils.path_dirname(path)) #PRENDE IL GRUPPO E L'UTENTE DELLA CARTELLA PADRE 
            utils.path_change_owner(path, stat_info.st_uid, stat_info.st_gid)
        elif operation=="MOVE_DIRECTORY" or operation=="MOVE_FILE":
            utils.path_change_permissions(path,mode)
            utils.path_change_owner(path, stat_info.st_uid, stat_info.st_gid)
    
    def is_gui(self):
        return True
    
    #GESTIONE GUI LAUNCHER
    def _signal_handler(self, signal, frame):
        self._propguilnc_stop=True
        
    def start_guilnc(self):
        self._propguilnc_stop=False
        signal.signal(signal.SIGTERM, self._signal_handler)
        bload=False
        suid=str(os.getuid())
        spid=str(os.getpid())
        lnc = sharedmem.Property()
        prcs = []
        try:
            while not self._propguilnc_stop and utils.path_exists("guilnc.run"):
                if not bload:
                    if lnc.exists("gui_launcher_" + suid):
                        try:
                            lnc.open("gui_launcher_" + suid)
                            lnc.set_property("pid", spid)
                            bload=True
                        except:
                            time.sleep(1)
                    else:
                        time.sleep(1)
                if bload:
                    if lnc.get_property("state")=="LNC":
                        popenar=[]
                        popenar.append(sys.executable)
                        popenar.append(u'agent.pyc')
                        popenar.append(u'app=' + lnc.get_property("app"))
                        for i in range(GUILNC_ARG_MAX):
                            a = lnc.get_property("arg" + str(i))
                            if a=="":
                                break;
                            popenar.append(a)
                        libenv = os.environ
                        libenv["LD_LIBRARY_PATH"]=utils.path_absname("runtime/lib")
                        #print "Popen: " + " , ".join(popenar)
                        try:
                            p = subprocess.Popen(popenar, env=libenv)
                            prcs.append(p)
                            #print "PID: " + str(p.pid)
                            if p.poll() is None:
                                lnc.set_property("state", str(p.pid))
                            else:
                                lnc.set_property("state", "ERR")
                        except:
                            lnc.set_property("state", "ERR")
                    time.sleep(0.2)
                #Pulisce processi
                prcs = [p for p in prcs if p.poll() is None]
        finally:
            if bload:
                lnc.close()

    def init_guilnc(self,ag):
        self._propguilnc_semaphore.acquire()
        try:
            #COMPATIBILITA VERSIONI PRECEDENTI
            if utils.path_exists("native/dwagguilnc"):
                self._propguilnc = {}
                if not utils.path_exists("guilnc.run"):
                    f = utils.file_open("guilnc.run","wb")
                    f.close()
        finally:
            self._propguilnc_semaphore.release()        
    
    def term_guilnc(self):
        self._propguilnc_semaphore.acquire()
        try:
            if utils.path_exists("guilnc.run"):
                utils.path_remove("guilnc.run")
            if self._propguilnc is not None:
                for l in self._propguilnc:
                    self._propguilnc[l].close()
                self._propguilnc=None
        finally:
            self._propguilnc_semaphore.release()            
    
    def exec_guilnc(self, uid, app, args):
        self._propguilnc_semaphore.acquire()
        try:
            if self._propguilnc is not None:
                suid=str(uid)
                lnc = None
                if suid not in self._propguilnc:
                    lnc = sharedmem.Property()
                    fieldsdef=[]
                    fieldsdef.append({"name":"pid","size":20})
                    fieldsdef.append({"name":"state","size":20}) # ""=NESSUNA OPERAZIONE; "LNC"="ESEGUI"; "NUM"=PID ESEGUITO 
                    fieldsdef.append({"name":"app","size":100})
                    for i in range(GUILNC_ARG_MAX):
                        fieldsdef.append({"name":"arg" + str(i),"size":GUILNC_ARG_SIZE})
                    def fix_perm(fn):
                        utils.path_change_owner(fn, uid, -1)
                        utils.path_change_permissions(fn, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP)
                    lnc.create("gui_launcher_" + suid, fieldsdef, fix_perm)
                    self._propguilnc[suid]=lnc
                else:
                    lnc=self._propguilnc[suid]
                
                cnt=20.0                
                #PULISCE
                lnc.set_property("state","")
                lnc.set_property("app","")
                for i in range(GUILNC_ARG_MAX):
                    lnc.set_property("arg" + str(i),"")
                #RICHIESTA                        
                lnc.set_property("app", app)
                for i in range(len(args)):
                    lnc.set_property("arg" + str(i), args[i])
                st="LNC" 
                lnc.set_property("state", st)
                while st=="LNC" and cnt>0.0:
                    st = lnc.get_property("state")
                    time.sleep(0.2)
                    cnt-=0.2                        
                if st=="LNC":
                    lnc.set_property("state", "")
                    raise Exception("GUI launcher timeout.")
                if st=="ERR":
                    raise Exception("GUI launcher error.")
                return int(st)          
        finally:
            self._propguilnc_semaphore.release() 
        return None