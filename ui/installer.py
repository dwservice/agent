# -*- coding: utf-8 -*-

'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''

import os
import hashlib
import json
import shutil
import time
import sys
import messages
import ui
import communication
import stat
import platform
import listener
import gdi
import importlib
import zlib
import base64
import sharedmem
import ctypes
import subprocess
import utils
import traceback


_MAIN_URL = "https://www.dwservice.net/"
_MAIN_URL_QA = "https://qa.dwservice.net:7742/"
_MAIN_URL_SVIL = "https://svil.dwservice.net:7732/dws_site/"
_NATIVE_PATH = u'native'
_RUNTIME_PATH = u'runtime'

def get_native():
    if gdi.is_windows():
        return NativeWindows()
    elif gdi.is_linux():
        return NativeLinux()
    elif gdi.is_mac():
        return NativeMac()
        
def stop_monitor(installpath):
    try:
        stopfilename = installpath + utils.path_sep + u"monitor.stop"
        if not utils.path_exists(stopfilename):
            stopfile = utils.file_open(stopfilename, "w", encoding='utf-8')
            stopfile.close()
        time.sleep(5) #Attende in modo che si chiudono i monitor
        utils.path_remove(stopfilename) 
    except:
        None

def exception_to_string(e):
    bamsg=False;
    try:
        if len(e.message)>0:
            bamsg=True;
    except:
        None
    try:
        appmsg=None
        if bamsg:
            appmsg=e.message
        elif isinstance(e, unicode) or isinstance(e, str):
            appmsg=e
        else:
            try:
                appmsg=unicode(e)
            except:
                appmsg=str(e)
        try:
            if isinstance(appmsg, unicode):
                return appmsg
            elif isinstance(appmsg, str):
                return appmsg.decode("UTF8")
        except:
            return unicode(appmsg, errors='replace')
    except:
        return "Unexpected error."

def get_stacktrace_string():
    try:
        s = traceback.format_exc();
        if s is None:
            s=u""
        if isinstance(s, unicode):
            return s;
        else:
            try:
                return s.decode("UTF8")
            except:
                return unicode(s, errors='replace')
    except:
        return "Unexpected error."

class NativeLinux:
    def __init__(self):
        self._name=None
        self._current_path=None
        self._install_path=None
        self._etc_path = u"/etc/dwagent"
    
    def set_name(self, k):
        self._name=k
    
    def set_current_path(self, pth):
        self._current_path=pth
    
    def set_install_path(self, pth):
        self._install_path=pth
        
    def set_install_log(self, log):
        self._install_log=log
        
    def get_proposal_path(self):
        return u'/usr/share/dwagent' 
    
    def get_install_path(self) :
        if utils.path_exists(self._etc_path):
            f = utils.file_open(self._etc_path)
            try:
                ar = json.loads(f.read())
                pth = ar['path']
                if utils.path_exists(pth):
                    return pth
            finally:
                f.close()
        return  None
    
    def is_task_running(self, pid):
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True
    
    def check_init_run(self):
        return None         
     
    def check_init_install(self, onlycheck=False):
        if os.geteuid() != 0: #DEVE ESSERE EUID
            return messages.get_message("linuxRootPrivileges")
        return None
    
    def check_init_uninstall(self):
        if os.geteuid() != 0: #DEVE ESSERE EUID
            return messages.get_message("linuxRootPrivileges")
        return None

    def stop_service(self):
        ret = utils.system_call(self._install_path + utils.path_sep + u"native" + utils.path_sep + u"dwagsvc stop", shell=True, stdout=self._install_log, stderr=subprocess.STDOUT)
        self._install_log.flush()
        return ret==0
    
    def start_service(self):
        ret = utils.system_call(self._install_path + utils.path_sep + u"native" + utils.path_sep + u"dwagsvc start", shell=True, stdout=self._install_log, stderr=subprocess.STDOUT)
        self._install_log.flush()
        return ret==0
    
    def replace_key_file(self, path,  key,  val):
        fin = utils.file_open(path, "r", encoding='utf-8')
        data = fin.read()
        fin.close()
        fout = utils.file_open(path, "w", encoding='utf-8')
        fout.write(data.replace(key,val))
        fout.close()
        
    def prepare_file_service(self, pth):
        #Service
        fdwagsvc=pth + utils.path_sep + u"dwagsvc"
        self.replace_key_file(fdwagsvc, u"@PATH_DWA@",  self._install_path)
        utils.path_change_permissions(fdwagsvc,  stat.S_IRWXU + stat.S_IRGRP + stat.S_IROTH)
        fdwagent=pth + utils.path_sep + u"dwagent.service"
        self.replace_key_file(fdwagent, u"@PATH_DWA@",  self._install_path)
        utils.path_change_permissions(fdwagent,  stat.S_IRUSR + stat.S_IWUSR + stat.S_IRGRP + stat.S_IROTH)
    
    def prepare_file_sh(self, pth):
        #DWAgent
        appf=pth + utils.path_sep + u"dwagent"
        self.replace_key_file(appf, u"@PATH_DWA@",  self._install_path)
        utils.path_change_permissions(appf,  stat.S_IRWXU + stat.S_IRGRP +  stat.S_IXGRP + stat.S_IROTH + stat.S_IXOTH)
        
        #DWAgent
        appf=pth + utils.path_sep + u"configure"
        self.replace_key_file(appf, u"@PATH_DWA@",  self._install_path)
        utils.path_change_permissions(appf,  stat.S_IRWXU + stat.S_IRGRP +  stat.S_IXGRP + stat.S_IROTH + stat.S_IXOTH)
        
        #DWAgent
        appf=pth + utils.path_sep + u"uninstall"
        self.replace_key_file(appf, u"@PATH_DWA@",  self._install_path)
        utils.path_change_permissions(appf,  stat.S_IRWXU + stat.S_IRGRP +  stat.S_IXGRP + stat.S_IROTH + stat.S_IXOTH)
        
        #Menu
        fmenuconf=pth + utils.path_sep + u"dwagent.desktop"
        if utils.path_exists(fmenuconf):
            self.replace_key_file(fmenuconf, u"@PATH_DWA@",  self._install_path)
            utils.path_change_permissions(fmenuconf,  stat.S_IRWXU + stat.S_IRGRP + stat.S_IRWXO)
        
    
    #LO USA ANCHE agent.py
    def prepare_file_monitor(self, pth):
        appf=pth + utils.path_sep + u"systray"
        if utils.path_exists(appf):
            self.replace_key_file(appf, u"@PATH_DWA@",  self._install_path)
            utils.path_change_permissions(appf,  stat.S_IRWXU + stat.S_IRGRP +  stat.S_IXGRP + stat.S_IROTH + stat.S_IXOTH)
        
        fmenusystray=pth + utils.path_sep + u"systray.desktop"
        if utils.path_exists(fmenusystray):
            self.replace_key_file(fmenusystray, u"@PATH_DWA@",  self._install_path)
            utils.path_change_permissions(fmenusystray,  stat.S_IRWXU + stat.S_IRGRP + stat.S_IRWXO)
    
    def prepare_file(self):
        self.prepare_file_service(self._install_path + utils.path_sep + u"native")
        self.prepare_file_sh(self._install_path + utils.path_sep + u"native")
        self.prepare_file_monitor(self._install_path + utils.path_sep + u"native")
    
    def prepare_file_runonfly(self, runcode):
        None
    
    def start_runonfly(self, runcode):
        pargs=[]
        pargs.append(sys.executable)
        pargs.append(u'agent.pyc')
        pargs.append(u'-runonfly')
        pargs.append(u'-filelog')
        if runcode is not None:
            pargs.append(u'runcode=' + runcode)
        
        libenv = os.environ
        libenv["LD_LIBRARY_PATH"]=utils.path_absname(self._current_path + utils.path_sep + u"runtime" + utils.path_sep + u"lib")
        return subprocess.Popen(pargs, env=libenv)

    
    def prepare_runtime_by_os(self,ds):
        utils.path_makedir(ds)
        utils.path_makedir(ds + utils.path_sep + u"bin")
        utils.path_makedir(ds + utils.path_sep + u"lib")
        utils.path_symlink(sys.executable, ds + utils.path_sep + u"bin" + utils.path_sep + u"dwagent")
        return True;
    
    def install_service(self):
        ret = utils.system_call(self._install_path + utils.path_sep + u"native" + utils.path_sep + u"dwagsvc install", shell=True, stdout=self._install_log, stderr=subprocess.STDOUT)
        self._install_log.flush()
        return ret==0
    
    def delete_service(self):
        ret = utils.system_call(self._install_path + utils.path_sep + u"native" + utils.path_sep + u"dwagsvc delete", shell=True, stdout=self._install_log, stderr=subprocess.STDOUT)
        self._install_log.flush()
        return ret==0
    
    def install_auto_run_monitor(self):
        try:
            pautos = u"/etc/xdg/autostart"
            utils.path_copy(self._install_path + utils.path_sep + u"native" + utils.path_sep + u"systray.desktop", pautos + utils.path_sep + u"dwagent_systray.desktop")
            utils.path_change_permissions(pautos + utils.path_sep + u"dwagent_systray.desktop",  stat.S_IRWXU + stat.S_IRGRP + stat.S_IRWXO)
            #SI DEVE LANCIARE CON L'UTENTE CONNESSO A X
            #Esegue il monitor
            #os.system(self._install_path + utils.path_sep + u"native" + utils.path_sep + u"dwaglnc systray &")
        except:
            None
        return True
    
    def remove_auto_run_monitor(self):
        try:
            fnm = u"/etc/xdg/autostart/dwagent_systray.desktop"
            if utils.path_exists(fnm):
                utils.path_remove(fnm)
        except:
            None
        return True
    
    def install_extra(self):
        return True
    
    def install_shortcuts(self):
        try:
            #Crea MENU
            utils.system_call(self._install_path + utils.path_sep + u"native" + utils.path_sep + u"dwagsvc install_shortcuts", shell=True, stdout=self._install_log, stderr=subprocess.STDOUT)
            self._install_log.flush()
            
            #CREA /etc/dwagent
            if utils.path_exists(self._etc_path):
                utils.path_remove(self._etc_path)
            ar = {'path': self._install_path}
            s = json.dumps(ar, sort_keys=True, indent=1)
            f = utils.file_open(self._etc_path, 'wb')
            f.write(s)
            f.close()
            return True
        except:
            return False
        
        
    def remove_shortcuts(self) :
        try:
            #RIMUOVE /etc/dwagent
            if utils.path_exists(self._etc_path):
                utils.path_remove(self._etc_path)
                
            #RIMUOVE MENU
            utils.system_call(self._install_path + utils.path_sep + u"native" + utils.path_sep + u"dwagsvc uninstall_shortcuts", shell=True, stdout=self._install_log, stderr=subprocess.STDOUT)
            self._install_log.flush()
        
            return True
        except:
            return False

class NativeMac:
    def __init__(self):
        self._name=None
        self._current_path=None
        self._install_path=None
        self._lncdmn_path = u"/Library/LaunchDaemons/net.dwservice.agsvc.plist"

    def set_name(self, k):
        self._name=k
    
    def set_current_path(self, pth):
        self._current_path=pth

    def set_install_path(self, pth):
        self._install_path=pth
        
    def set_install_log(self, log):
        self._install_log=log
        
    def get_proposal_path(self):
        return u'/Library/DWAgent' 
    
    def get_install_path(self) :
        #Verificare la cartella dei servizi
        if utils.path_exists(self._lncdmn_path) and utils.path_islink(self._lncdmn_path):
            return utils.path_dirname(utils.path_dirname(utils.path_realname(self._lncdmn_path)))
        
        #COMPATIBILITA CON INSTALLAZIONI PRECEDENTI
        oldlncdmn_path = u"/Library/LaunchDaemons/net.dwservice.agent.plist"
        if utils.path_exists(oldlncdmn_path) and utils.path_islink(oldlncdmn_path):
            return utils.path_dirname(utils.path_dirname(utils.path_realname(oldlncdmn_path)))
        
        oldlncdmn_path = u"/System/Library/LaunchDaemons/org.dwservice.agent.plist"
        if utils.path_exists(oldlncdmn_path) and utils.path_islink(oldlncdmn_path):
            return utils.path_dirname(utils.path_dirname(utils.path_realname(oldlncdmn_path)))
        
        return  None             
    
    def is_task_running(self, pid):
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True
    
    def check_init_run(self):
        return None
    
    def check_init_install(self, onlycheck=False):
        if os.geteuid() != 0: #DEVE ESSERE EUID
            if onlycheck:
                return messages.get_message("linuxRootPrivileges")
            else:
                f = utils.file_open(u"runasadmin.install", 'wb')
                f.close()
                raise SystemExit
        return None
    
    def check_init_uninstall(self):
        if os.geteuid() != 0: #DEVE ESSERE EUID
            return messages.get_message(u"linuxRootPrivileges")
        return None

    def _get_os_ver(self):
        try:
            sver = platform.mac_ver()[0]
            ar = sver.split(".")
            if len(ar)==0:
                return [99999,99999]
            elif len(ar)==1:
                return [int(ar[0]),0]
            else:
                return [int(ar[0]),int(ar[1])]
        except:
            return [99999,99999]

    def _bootstrap_agent(self,pn):
        arver=self._get_os_ver()
        if arver[0]<10 or (arver[0]==10 and arver[1]<=9):
            utils.system_call(u"sudo -u $(id -nu `stat -f '%u' /dev/console`) launchctl load -S Aqua /Library/LaunchAgents/" + pn, shell=True, stdout=self._install_log, stderr=subprocess.STDOUT)
            self._install_log.flush()
        else:
            utils.system_call(u"launchctl bootstrap gui/`stat -f '%u' /dev/console` /Library/LaunchAgents/" + pn, shell=True, stdout=self._install_log, stderr=subprocess.STDOUT)
            self._install_log.flush()
    
    def _bootout_agent(self,pn):
        arver=self._get_os_ver()
        if arver[0]<10 or (arver[0]==10 and arver[1]<=9):
            utils.system_call(u"launchctl unload /Library/LaunchAgents/" + pn, shell=True, stdout=self._install_log, stderr=subprocess.STDOUT)
            self._install_log.flush()
            utils.system_call(u"for USER in `users`; do sudo -u $USER launchctl unload -S Aqua /Library/LaunchAgents/" + pn + "; done", shell=True, stdout=self._install_log, stderr=subprocess.STDOUT)
            self._install_log.flush()
        else:
            utils.system_call(u"launchctl bootout gui/0 /Library/LaunchAgents/" + pn, shell=True, stdout=self._install_log, stderr=subprocess.STDOUT)
            self._install_log.flush()
            utils.system_call(u"for USER in `users`; do launchctl bootout gui/`id -u $USER` /Library/LaunchAgents/" + pn + "; done", shell=True, stdout=self._install_log, stderr=subprocess.STDOUT)
            self._install_log.flush()
        
    def stop_service(self):
        #Arresta GUILauncher
        self._bootout_agent(u"net.dwservice.agguilnc.plist")
        ret =utils.system_call(self._install_path + utils.path_sep + u"native" + utils.path_sep + u"dwagsvc stop", shell=True, stdout=self._install_log, stderr=subprocess.STDOUT)
        self._install_log.flush()
        return ret==0
    
    def start_service(self):
        ret = utils.system_call(self._install_path + utils.path_sep + u"native" + utils.path_sep + u"dwagsvc start", shell=True, stdout=self._install_log, stderr=subprocess.STDOUT)
        self._install_log.flush()
        bret = (ret==0)
        if bret:
            #Avvia GUILauncher
            self._bootstrap_agent(u"net.dwservice.agguilnc.plist")
        return bret
    
    def replace_key_file(self, path, enc,  key,  val):
        fin=utils.file_open(path, "r", enc)
        data = fin.read()
        fin.close()
        fout=utils.file_open(path,"w", enc)
        fout.write(data.replace(key,val))
        fout.close()
            
    def prepare_file_service(self, pth):
        #Service
        fapp=pth + utils.path_sep + "dwagsvc"
        self.replace_key_file(fapp, "utf-8", "@PATH_DWA@",  self._install_path)
        utils.path_change_permissions(fapp,  stat.S_IRWXU + stat.S_IRGRP + stat.S_IROTH)
        
        fapp=pth + utils.path_sep + "dwagsvc.plist"
        self.replace_key_file(fapp, "utf-8", "@PATH_DWA@",  self._install_path)
        utils.path_change_permissions(fapp,  stat.S_IRUSR + stat.S_IWUSR + stat.S_IRGRP + stat.S_IROTH)
        
        #GUI Launcher
        fapp=pth + utils.path_sep + "dwagguilnc"
        utils.path_change_permissions(fapp,  stat.S_IRWXU + stat.S_IRGRP + stat.S_IXGRP + stat.S_IROTH + stat.S_IXOTH)
        
        fapp=pth + utils.path_sep + "dwagguilnc.plist"
        self.replace_key_file(fapp, "utf-8", "@PATH_DWA@",  self._install_path)
        utils.path_change_permissions(fapp,  stat.S_IRUSR + stat.S_IWUSR + stat.S_IRGRP + stat.S_IROTH)
    
    def prepare_file_app(self, pth):
                
        shutil.copytree(pth + u"/DWAgent.app",pth + u"/Configure.app")
        shutil.copytree(pth + u"/DWAgent.app",pth + u"/Uninstall.app")
                
        utils.path_change_permissions(pth + u"/DWAgent.app/Contents/MacOS/DWAgent",  stat.S_IRUSR + stat.S_IWUSR + stat.S_IXUSR + stat.S_IRGRP + stat.S_IXGRP + stat.S_IROTH + stat.S_IXOTH)           
        self.replace_key_file(pth + u"/DWAgent.app/Contents/Info.plist", "utf-8", u"@EXE_NAME@" ,  u"DWAgent")
        self.replace_key_file(pth + u"/DWAgent.app/Contents/MacOS/DWAgent", "utf-8",u"@MOD_DWA@",  u"monitor")
        self.replace_key_file(pth + u"/DWAgent.app/Contents/MacOS/DWAgent", "utf-8",u"@PATH_DWA@",  self._install_path)
        
        shutil.move(pth + u"/Configure.app/Contents/MacOS/DWAgent",  pth + "/Configure.app/Contents/MacOS/Configure")
        utils.path_change_permissions(pth + u"/Configure.app/Contents/MacOS/Configure",  stat.S_IRUSR + stat.S_IWUSR + stat.S_IXUSR + stat.S_IRGRP + stat.S_IXGRP + stat.S_IROTH + stat.S_IXOTH)
        self.replace_key_file(pth + u"/Configure.app/Contents/Info.plist", "utf-8", u"@EXE_NAME@" ,  u"Configure")
        self.replace_key_file(pth + u"/Configure.app/Contents/MacOS/Configure", "utf-8",u"@MOD_DWA@",  u"configure")
        self.replace_key_file(pth + u"/Configure.app/Contents/MacOS/Configure", "utf-8",u"@PATH_DWA@",  self._install_path)
        
        shutil.move(pth + u"/Uninstall.app/Contents/MacOS/DWAgent",  pth + "/Uninstall.app/Contents/MacOS/Uninstall")
        utils.path_change_permissions(pth + u"/Uninstall.app/Contents/MacOS/Uninstall",  stat.S_IRUSR + stat.S_IWUSR + stat.S_IXUSR + stat.S_IRGRP + stat.S_IXGRP + stat.S_IROTH + stat.S_IXOTH)
        self.replace_key_file(pth + u"/Uninstall.app/Contents/Info.plist", "utf-8", u"@EXE_NAME@" ,  u"Uninstall")
        self.replace_key_file(pth + u"/Uninstall.app/Contents/MacOS/Uninstall", "utf-8",u"@MOD_DWA@",  u"uninstall")
        self.replace_key_file(pth + u"/Uninstall.app/Contents/MacOS/Uninstall", "utf-8",u"@PATH_DWA@",  self._install_path)
        
    
    def prepare_file_monitor(self, pth):
        fapp=pth + utils.path_sep + "dwagsystray"
        utils.path_change_permissions(fapp,  stat.S_IRWXU + stat.S_IRGRP + stat.S_IXGRP + stat.S_IROTH + stat.S_IXOTH)
        
        fapp=pth + utils.path_sep + "dwagsystray.plist"
        self.replace_key_file(fapp, "utf-8", "@PATH_DWA@",  self._install_path)
        utils.path_change_permissions(fapp,  stat.S_IRUSR + stat.S_IWUSR + stat.S_IRGRP + stat.S_IROTH)
        
    
    def prepare_file(self):
        self.prepare_file_service(self._install_path + utils.path_sep + u"native")
        self.prepare_file_app(self._install_path + utils.path_sep + u"native")
        self.prepare_file_monitor(self._install_path + utils.path_sep + u"native")
    
    def prepare_file_runonfly(self, runcode):
        None

    def start_runonfly(self, runcode):
        pargs=[]
        pargs.append(sys.executable)
        pargs.append(u'agent.pyc')
        pargs.append(u'-runonfly')
        pargs.append(u'-filelog')
        if runcode is not None:
            pargs.append(u'runcode=' + runcode)
        libenv = os.environ
        libenv["LD_LIBRARY_PATH"]=utils.path_absname(self._current_path + utils.path_sep + u"runtime" + utils.path_sep + u"lib")
        return subprocess.Popen(pargs, env=libenv)

    def prepare_runtime_by_os(self,ds):
        return False;
    
    def install_service(self):
        ret = utils.system_call(self._install_path + utils.path_sep + u"native" + utils.path_sep + u"dwagsvc install", shell=True, stdout=self._install_log, stderr=subprocess.STDOUT)
        self._install_log.flush()
        return ret==0
    
    def delete_service(self):
        ret = utils.system_call(self._install_path + utils.path_sep + u"native" + utils.path_sep + u"dwagsvc delete", shell=True, stdout=self._install_log, stderr=subprocess.STDOUT)
        self._install_log.flush()
        return ret==0
    
    def install_auto_run_monitor(self):
        ret = utils.system_call(self._install_path + utils.path_sep + u"native" + utils.path_sep + u"dwagsvc installAutoRun", shell=True, stdout=self._install_log, stderr=subprocess.STDOUT)
        self._install_log.flush()
        bret = (ret==0)
        if bret:
            #Avvia systray
            self._bootstrap_agent(u"net.dwservice.agsystray.plist")
        return bret
        
    
    def remove_auto_run_monitor(self):
        #Chiude tutti systray
        self._bootout_agent(u"net.dwservice.agsystray.plist")
        ret = utils.system_call(self._install_path + utils.path_sep + u"native" + utils.path_sep + u"dwagsvc removeAutoRun", shell=True, stdout=self._install_log, stderr=subprocess.STDOUT)
        self._install_log.flush()
        return ret==0
    
    def install_extra(self):
        return True
    
    def install_shortcuts(self):
        try:
            pathsrc = self._install_path + utils.path_sep + u"native/"
            pathdst = u"/Applications/"
            if utils.path_exists(pathdst):
                shutil.copytree(pathsrc+u"DWAgent.app", pathdst+u"DWAgent.app", symlinks=True)
            return True
        except:
            return False
        
        
    def remove_shortcuts(self) :
        try:
            pathsrc = u"/Applications/DWAgent.app"
            if utils.path_exists(pathsrc):
                utils.path_remove(pathsrc)
            return True
        except:
            return False


if gdi.is_windows():
    import types
    import _subprocess
    from ctypes import byref, windll, c_char_p, c_wchar_p, c_void_p, Structure, sizeof, c_wchar, WinError
    from ctypes.wintypes import BYTE, WORD, LPWSTR, BOOL, DWORD, LPVOID, HANDLE

    class NativeWindowsPopenUnicodeSTARTUPINFOW(Structure):
        _fields_ = [
            ("cb",              DWORD),  ("lpReserved",    LPWSTR),
            ("lpDesktop",       LPWSTR), ("lpTitle",       LPWSTR),
            ("dwX",             DWORD),  ("dwY",           DWORD),
            ("dwXSize",         DWORD),  ("dwYSize",       DWORD),
            ("dwXCountChars",   DWORD),  ("dwYCountChars", DWORD),
            ("dwFillAtrribute", DWORD),  ("dwFlags",       DWORD),
            ("wShowWindow",     WORD),   ("cbReserved2",   WORD),
            ("lpReserved2",     ctypes.POINTER(BYTE)), ("hStdInput",     HANDLE),
            ("hStdOutput",      HANDLE), ("hStdError",     HANDLE),
        ]
    
    
    class NativeWindowsPopenUnicodePROCESS_INFORMATION(Structure):
        _fields_ = [
            ("hProcess",         HANDLE), ("hThread",          HANDLE),
            ("dwProcessId",      DWORD),  ("dwThreadId",       DWORD),
        ]
    
    
    class NativeWindowsPopenUnicodeHANDLE(ctypes.c_void_p):
    
        def __init__(self, *a, **kw):
            super(NativeWindowsPopenUnicodeHANDLE, self).__init__(*a, **kw)
            self.closed = False
    
        def Close(self):
            if not self.closed:
                windll.kernel32.CloseHandle(self)
                self.closed = True
    
        def __int__(self):
            return self.value

    
    NativeWindowsPopenUnicodeCreateProcessW = windll.kernel32.CreateProcessW
    NativeWindowsPopenUnicodeCreateProcessW.argtypes = [
        c_char_p, c_wchar_p, c_void_p,
        c_void_p, BOOL, DWORD, LPVOID, c_char_p,
        ctypes.POINTER(NativeWindowsPopenUnicodeSTARTUPINFOW), ctypes.POINTER(NativeWindowsPopenUnicodePROCESS_INFORMATION),
    ]
    NativeWindowsPopenUnicodeCreateProcessW.restype = BOOL

    class NativeWindowsPopenUnicode(subprocess.Popen):
        
        def _createProcessW(self, executable, args, _p_attr, _t_attr,
                          inherit_handles, creation_flags, env, cwd,
                          startup_info):
            si = NativeWindowsPopenUnicodeSTARTUPINFOW(
                dwFlags=startup_info.dwFlags,
                wShowWindow=startup_info.wShowWindow,
                cb=sizeof(NativeWindowsPopenUnicodeSTARTUPINFOW),
                hStdInput=int(startup_info.hStdInput),
                hStdOutput=int(startup_info.hStdOutput),
                hStdError=int(startup_info.hStdError),
            )    
            wenv = None
            if env is not None:
                '''
                env = (unicode("").join([
                    unicode("%s=%s\0") % (k, v)
                    for k, v in env.items()])) + unicode("\0")
                '''
                appenv=[]
                for k, v in env.items():
                    k = unicode(k)
                    n= ctypes.windll.kernel32.GetEnvironmentVariableW(k, None, 0)
                    if n>0:
                        buf= ctypes.create_unicode_buffer(u'\0'*n)
                        ctypes.windll.kernel32.GetEnvironmentVariableW(k, buf, n)
                        appenv.append(unicode("%s=%s\0") % (k , buf.value))
                appenv.append(unicode("\0"))
                env = unicode("").join(appenv)
                wenv = (c_wchar * len(env))()
                wenv.value = env
        
            pi = NativeWindowsPopenUnicodePROCESS_INFORMATION()
            creation_flags |= 0x00000400 #CREATE_UNICODE_ENVIRONMENT
        
            if NativeWindowsPopenUnicodeCreateProcessW(executable, args, None, None,
                              inherit_handles, creation_flags,
                              wenv, cwd, byref(si), byref(pi)):
                return (NativeWindowsPopenUnicodeHANDLE(pi.hProcess), NativeWindowsPopenUnicodeHANDLE(pi.hThread),
                        pi.dwProcessId, pi.dwThreadId)
            raise WinError()
    
    
        def _execute_child(self, args, executable, preexec_fn, close_fds,
                               cwd, env, universal_newlines,
                               startupinfo, creationflags, shell, to_close,
                               p2cread, p2cwrite,
                               c2pread, c2pwrite,
                               errread, errwrite):
                """Execute program (MS Windows version)"""
    
                if not isinstance(args, types.StringTypes):
                    args = subprocess.list2cmdline(args)
    
                # Process startup details
                if startupinfo is None:
                    startupinfo = subprocess.STARTUPINFO()
                if None not in (p2cread, c2pwrite, errwrite):
                    startupinfo.dwFlags |= _subprocess.STARTF_USESTDHANDLES
                    startupinfo.hStdInput = p2cread
                    startupinfo.hStdOutput = c2pwrite
                    startupinfo.hStdError = errwrite
    
                if shell:
                    startupinfo.dwFlags |= _subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = _subprocess.SW_HIDE
                    comspec = os.environ.get("COMSPEC", unicode("cmd.exe"))
                    args = unicode('{} /c "{}"').format (comspec, args)
                    if (_subprocess.GetVersion() >= 0x80000000 or
                            utils.path_basename(comspec).lower() == "command.com"):
                        w9xpopen = self._find_w9xpopen()
                        args = unicode('"%s" %s') % (w9xpopen, args)
                        creationflags |= _subprocess.CREATE_NEW_CONSOLE
    
                def _close_in_parent(fd):
                    fd.Close()
                    to_close.remove(fd)
    
                try:
                    hp, ht, pid, tid = self._createProcessW(executable, args,
                                             None, None,
                                             int(not close_fds),
                                             creationflags,
                                             env,
                                             cwd,
                                             startupinfo)
                except subprocess.pywintypes.error, e:
                    raise WindowsError(*e.args)
                finally:
                    if p2cread is not None:
                        _close_in_parent(p2cread)
                    if c2pwrite is not None:
                        _close_in_parent(c2pwrite)
                    if errwrite is not None:
                        _close_in_parent(errwrite)
    
                self._child_created = True
                self._handle = hp
                self.pid = pid
                ht.Close()



    NativeWindowsRegCloseKey = ctypes.windll.advapi32.RegCloseKey
    NativeWindowsRegCloseKey.restype = ctypes.c_long
    NativeWindowsRegCloseKey.argtypes = [ctypes.c_void_p]
    
    NativeWindowsRegOpenKeyEx = ctypes.windll.advapi32.RegOpenKeyExW
    NativeWindowsRegOpenKeyEx.restype = ctypes.c_long
    NativeWindowsRegOpenKeyEx.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_ulong,
                             ctypes.c_ulong, ctypes.POINTER(ctypes.c_void_p)]
    
    RegQueryValueEx = ctypes.windll.advapi32.RegQueryValueExW
    RegQueryValueEx.restype = ctypes.c_long
    RegQueryValueEx.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.POINTER(ctypes.wintypes.DWORD), ctypes.POINTER(ctypes.wintypes.DWORD),
                                ctypes.POINTER(ctypes.wintypes.BYTE), ctypes.POINTER(ctypes.wintypes.DWORD)]



class NativeWindows:
        
    def __init__(self):
        self._name=None
        self._current_path=None
        self._install_path=None
        self._os_env=None
        self._py_exe=None
        self._runtime=None
    
    def set_name(self, k):
        self._name=k
        self._runtime=k.lower() + u".exe"
    
    def set_current_path(self, pth):
        self._current_path=pth
    
    def set_install_path(self, pth):
        self._install_path=pth
        
    def set_install_log(self, log):
        None
        #self._install_log=log

    def get_proposal_path(self):
        return unicode(os.environ["ProgramFiles"]) + utils.path_sep + self._name
    
    def get_install_path(self) :
        vret = None
        try:
            rk = ctypes.c_void_p()
            #HKEY_LOCAL_MACHINE = 0x80000002
            ret = NativeWindowsRegOpenKeyEx(ctypes.c_void_p(0x80000002), u"Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\" + self._name, 0, 0x20019, ctypes.cast(ctypes.byref(rk), ctypes.POINTER(ctypes.c_void_p)))
            if ret == 0:
                sz = 256
                tp = ctypes.wintypes.DWORD()
                while True:
                    tmp_size = ctypes.wintypes.DWORD(sz)
                    buf = ctypes.create_string_buffer(sz)
                    ret = RegQueryValueEx(rk, u"InstallLocation", ctypes.POINTER(ctypes.wintypes.DWORD)(),
                                         ctypes.byref(tp),
                                         ctypes.cast(buf, ctypes.POINTER(ctypes.wintypes.BYTE)), ctypes.byref(tmp_size))
                    if ret != 234:
                        break
                    sz *= 2
                if ret == 0:
                    if tp.value == 1 or tp.value == 2:
                        vret = ctypes.wstring_at(buf, tmp_size.value // 2).rstrip(u'\x00')
                    elif tp.value != 4 or tp.value != 7:
                        vret = ctypes.string_at(buf, tmp_size.value)
                
                NativeWindowsRegCloseKey(rk)
            return vret
        except:
            None 
        return None
    
    def is_task_running(self, pid):
        return gdi.is_windows_task_running(pid)
    
    def check_init_run(self):
        if gdi.is_windows_user_in_admin_group():
            if gdi.is_windows_run_as_admin():
                if gdi.is_windows_process_elevated():
                    return None
                else:
                    f = utils.file_open(u"runasadmin.install", "wb", encoding='utf-8')
                    f.close()
                    raise SystemExit
            else:
                f = utils.file_open(u"runasadmin.run", "wb", encoding='utf-8')
                f.close()
                raise SystemExit
        else:
            return None
    
    def check_init_install(self, onlycheck=False):
        if gdi.is_windows_user_in_admin_group() and gdi.is_windows_run_as_admin():
            if gdi.is_windows_process_elevated():
                return None
            else:
                if onlycheck:
                    return messages.get_message("windowsAdminPrivileges")
                else:
                    f = utils.file_open(u"runasadmin.install", "wb", encoding='utf-8')
                    f.close()
                    raise SystemExit
        else:
            if onlycheck:
                return messages.get_message("windowsAdminPrivileges")
            else:
                f = utils.file_open(u"runasadmin.install", "wb", encoding='utf-8')
                f.close()
                raise SystemExit
                        
    
    def check_init_uninstall(self):
        if gdi.is_windows_user_in_admin_group() and gdi.is_windows_run_as_admin():
            try:
                if gdi.is_windows_process_elevated():
                    return None
                else:
                    return messages.get_message("windowsAdminPrivileges")
            except:
                return None #XP
        else:
            return messages.get_message("windowsAdminPrivileges")
        
    
    def prepare_file(self):
        #Scrive service.properties
        pth=self._install_path
        arf = []
        arf.append(u''.join([u"serviceName=",self._name,u"\r\n"]))
        #FIX UNICODE PATH
        arf.append(u''.join([u"pythonHome=runtime\r\n"]))
        arf.append(u''.join([u"pythonPath=",  pth, utils.path_sep, u"runtime", utils.path_sep, self._runtime, u"\r\n"]))
        arf.append(u"parameters=-S -m agent -filelog")
        f=utils.file_open(pth + utils.path_sep + u'native' + utils.path_sep + u'service.properties', 'w', encoding='utf-8') 
        f.write(u''.join(arf))
        f.close()
    
    def prepare_file_runonfly(self, runcode):
        #Scrive service.properties
        pth=self._install_path
        arf = []
        arf.append(u''.join([u"serviceName=",self._name + u"RunOnFly",u"\r\n"]))
        #FIX UNICODE PATH
        ar = self._current_path.split(utils.path_sep)
        arf.append(u''.join([u"pythonHome=.." + utils.path_sep + ar[len(ar)-1] + utils.path_sep + u"runtime\r\n"]))
        arf.append(u''.join([u"pythonPath=",  self._current_path, utils.path_sep, u"runtime", utils.path_sep, self._runtime, u"\r\n"]))
        arf.append(u"parameters=-S -m agent -runonfly -filelog")        
        if runcode is not None:
            arf.append(u" runcode=" + runcode)
        
        f=utils.file_open(pth + utils.path_sep + u'native' + utils.path_sep + u'service.properties', 'w', encoding='utf-8') 
        f.write(u''.join(arf))
        f.close()        
        self._os_env = os.environ
        self._os_env['PYTHONHOME'] = u".." + utils.path_sep + ar[len(ar)-1] + utils.path_sep + u"runtime"
        self._py_exe = self._current_path + utils.path_sep + u"runtime" + utils.path_sep + self._runtime    
    
    def start_runonfly(self, runcode):
        pargs=[]
        pargs.append(self._py_exe)
        pargs.append(u'-S')
        pargs.append(u'-m')
        pargs.append(u'agent')
        pargs.append(u'-runonfly')
        pargs.append(u'-filelog')
        if runcode is not None:
            pargs.append(u'runcode=' + runcode)         
        
        badmin=False
        if gdi.is_windows_user_in_admin_group() and gdi.is_windows_run_as_admin():
            try:
                if gdi.is_windows_process_elevated():
                    badmin=True
            except:
                badmin=True #XP
        if badmin:
            bsvcok=False
            cmd=u'"' + u'native' + utils.path_sep + u'dwagsvc.exe" startRunOnFly'
            appout = NativeWindowsPopenUnicode(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate() 
            lines = appout[0].splitlines()
            for l in lines:
                if l=='OK':
                    bsvcok = True
            if bsvcok==False:
                return NativeWindowsPopenUnicode(pargs, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=self._os_env)
            else:
                return None
        else:
            return NativeWindowsPopenUnicode(pargs, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=self._os_env)
    
    def prepare_runtime_by_os(self,ds):
        return False;    
    
    def executecmd(self, cmd):
        appout = NativeWindowsPopenUnicode(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
        lines = appout[0].splitlines()
        for l in lines:
            if l=='OK':
                return True
        return False
    
    def stop_service(self):
        cmd=u'"' + self._install_path + utils.path_sep + u'native' + utils.path_sep + u'dwagsvc.exe" stopService'
        return self.executecmd(cmd)
    
    def start_service(self):
        cmd=u'"' + self._install_path + utils.path_sep + u'native' + utils.path_sep + u'dwagsvc.exe" startService'
        return self.executecmd(cmd)
    
    def install_service(self):
        cmd=u'"' + self._install_path + utils.path_sep + u'native' + utils.path_sep + u'dwagsvc.exe" installService'
        return self.executecmd(cmd)
    
    def delete_service(self):
        cmd=u'"' + self._install_path + utils.path_sep + u'native' + utils.path_sep + u'dwagsvc.exe" deleteService'
        return self.executecmd(cmd)
        
    def install_auto_run_monitor(self):
        cmd=u'"' + self._install_path + utils.path_sep + u'native' + utils.path_sep + u'dwagsvc.exe" installAutoRun'
        b = self.executecmd(cmd)
        if b==True:
            #Esegue il monitor
            cmdmon=u'"' + self._install_path + utils.path_sep + u'native' + utils.path_sep + u'dwaglnc.exe" systray' 
            NativeWindowsPopenUnicode(cmdmon, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
        return b
    
    
    def remove_auto_run_monitor(self):
        cmd=u'"' + self._install_path + utils.path_sep + u'native' + utils.path_sep + u'dwagsvc.exe" removeAutoRun'
        return self.executecmd(cmd)
    
    def install_extra(self):
        return True
    
    def install_shortcuts(self) :
        cmd=u'"' + self._install_path + utils.path_sep + u'native' + utils.path_sep + u'dwagsvc.exe" installShortcuts'
        return self.executecmd(cmd)
            
    def remove_shortcuts(self) :
        cmd=u'"' + self._install_path + utils.path_sep + u'native' + utils.path_sep + u'dwagsvc.exe" removeShortcuts'
        return self.executecmd(cmd)


class Install:
    
    def __init__(self):
        self._gotoopt=None
        self._silent=False
        self._options={}
        self._native = get_native()
        self._main_url = None
        self._ambient="PROD"
        self._uinterface=None
        self._current_path=None;
        self._install_path=ui.VarString()
        self._install_log_path=None
        self._install_log=None
        self._inatall_agent_mode=None
        self._install_code=ui.VarString()
        self._run_code=ui.VarString()
        self._install_newag_user=ui.VarString()
        self._install_newag_password=ui.VarString("", True)
        self._install_newag_name=ui.VarString()
        self._proxy_type=ui.VarString("SYSTEM")
        self._proxy_host=ui.VarString("")
        self._proxy_port=ui.VarString("")
        self._proxy_user=ui.VarString("")
        self._proxy_password=ui.VarString("", True)
        self._proxy = None
        self._sharedmemclient = None
        self._name = None
        self._listen_port = 7950
        self._runWithoutInstall = False
        self._runWithoutInstallProxySet = False;
        self._runWithoutInstallAgentAlive = True
        self._runWithoutInstallAgentCloseByClient=False
        self._runWithoutInstallAgentCloseEnd=True
        self._bmock=False
        
    
    def _get_message(self, key):
        smsg = messages.get_message(key)
        if self._name is not None:
            return smsg.replace(u"DWAgent",self._name)
        else:
            return smsg
    
    def _get_main_url(self):
        if self._main_url is not None:
            return self._main_url
        elif self._ambient=="QA":
            return _MAIN_URL_QA
        elif self._ambient=="SVIL":
            return _MAIN_URL_SVIL
        return _MAIN_URL

    def _uinterface_action(self,e):
        if e["action"]=="CLOSE":
            self._runWithoutInstallAgentAlive=False
            self._runWithoutInstallAgentCloseByClient=True
            if self._uinterface.is_gui():
                cnt=0
                while not self._runWithoutInstallAgentCloseEnd:
                    time.sleep(1)
                    cnt+=1
                    if cnt>=20:
                        break
    
    def start(self, aropts={}):
        self._options=aropts
        
        #debug purpose
        if 'mock' in self._options:
            self._bmock = self._options['mock']
        
        #Load install.json
        appjs=None
        if utils.path_exists("install.json"):
            f=None
            try:
                f = utils.file_open("install.json")
                appjs = json.loads(f.read())
            except:
                None
            finally:
                if f is not None:
                    f.close()
        elif 'install.json' in self._options:
            appjs = self._options['install.json']
            del self._options['install.json']
        if appjs is not None:
            for p in appjs:
                if p=="lang":
                    messages.set_locale(appjs[p])
                else:
                    self._options[p]=appjs[p]
                    
        self._gotoopt=None
        if "mainurl" in self._options:
            self._main_url=self._options["mainurl"]
        if "logpath" in self._options:
            self._install_log_path=self._options["logpath"]
            if self._install_log_path[len(self._install_log_path)-1:]==utils.path_sep or self._install_log_path[len(self._install_log_path)-1:]=='"':
                self._install_log_path=self._install_log_path[0:len(self._install_log_path)-1]
            if utils.path_isdir(self._install_log_path):
                self._install_log_path = self._install_log_path + utils.path_sep + "dwaginstall.log"
        if "gotoopt" in self._options:
            self._gotoopt=self._options["gotoopt"]
        bgui=True
        if "gui" in self._options:
            bgui=self._options["gui"]
        self._silent=False;
        if "silent" in self._options:
            self._silent=self._options["silent"]
            if self._silent:
                bgui=False
                messages.set_locale(None)
            self._gotoopt="install"        
                
        if "name" in self._options:
            self._name=unicode(self._options["name"])
            self._native.set_name(self._name)
        else:
            self._native.set_name(u"DWAgent")
        
        self._current_path=os.getcwdu()
        if self._current_path.endswith(utils.path_sep) is True:
            self._current_path=self._current_path[0:len(self._current_path)-1]
        self._native.set_current_path(self._current_path)
        if self._silent:
            self._runWithoutInstall=False
        prmsui = {}
        if "title" in self._options:
            prmsui["title"]=self._options["title"]
        else:
            prmsui["title"]="DWAgent"
        if "topinfo" in self._options:
            prmsui["topinfo"]=self._options["topinfo"]
        if "topimage" in self._options:
            prmsui["topimage"]=self._options["topimage"]
        if "logo" in self._options:
            prmsui["logo"]=self._options["logo"]
        if "leftcolor" in self._options:
            prmsui["leftcolor"]=self._options["leftcolor"]
        self._uinterface = ui.UI(prmsui, self.step_init)
        
        if not self._silent:
            self._uinterface.set_action(self._uinterface_action)
        self._uinterface.start(bgui) 
        self.close_req()
                
        #CHIUDE LOG
        try:
            if self._install_log is not None:
                self._install_log.close()
        except:
            None
        
        

    '''def _read_info_file(self):
        try:
            f = utils.file_open("info.json")
            prop = json.loads(f.read())
            f.close()   
            return prop
        except Exception:
            return None'''
    
    def step_init(self, curui):
        #Verifica version dell'installer se è valida per la macchina
        if not gdi.is_windows() and not gdi.is_linux() and not gdi.is_mac():
            return ui.Message(self._get_message('versionInstallNotValid').format(""))
        if not self._silent:
            chs = ui.Chooser()
            if "welcometext" in self._options:
                m=unicode(self._options["welcometext"])
            else:            
                m=self._get_message('welcomeLicense') + "\n\n" + self._get_message('welcomeSecurity') + "\n\n" + self._get_message('welcomeSoftwareUpdates')
                
            chs.set_message(m)
            chs.set_message_height(300)
            if "mode" in self._options and self._options["mode"]=="install":
                chs.add("install", self._get_message('install'))
            elif "mode" in self._options and self._options["mode"]=="run":
                chs.add("runWithoutInstallation", self._get_message('runWithoutInstallation'))
            else:
                chs.add("install", self._get_message('install'))
                chs.add("runWithoutInstallation", self._get_message('runWithoutInstallation'))
            chs.add("decline", self._get_message('decline'))
            chs.set_variable(ui.VarString("decline"))
            chs.set_accept_key("install;runWithoutInstallation")
            
            if self._gotoopt is not None:
                return self.step_install_choose(chs)
            else:
                chs.next_step(self.step_install_choose)
                return chs
        else:
            return self.step_install_choose(curui)
    
    def step_install_choose(self, curui):
        sopt=None
        if self._gotoopt is not None and self._gotoopt=="install":
            self._gotoopt=None
            sopt="install"
        elif self._gotoopt is not None and self._gotoopt=="run":
            self._gotoopt=None
            sopt="run"
        elif self._gotoopt is not None:
            self._gotoopt=None
            return self.step_init(curui)
        else:
            if curui.get_key() is None and curui.get_variable().get()=="runWithoutInstallation":
                if not self._silent:
                    if not self._bmock:
                        msg = self._native.check_init_run()
                        if msg is not None:
                            return ui.Message(msg)
                    sopt="run"
            else:
                if not self._silent:
                    if not self._bmock:
                        msg = self._native.check_init_install()
                        if msg is not None:
                            return ui.Message(msg)
                sopt="install"
                
        if sopt=="run":
            self._runWithoutInstall=True
            return self.step_install(curui)
        else:
            self._runWithoutInstall=False
            return self.step_check_already_install(curui)

    def step_check_already_install(self, curui):
        if not self._bmock:
            pth = self._native.get_install_path()
        else:
            pth=None
        if pth is not None:     
            if self._silent:       
                try:
                    if self._install_log_path is not None:
                        if self._install_log is None:
                            self._install_log = utils.file_open(self._install_log_path, "wb", encoding='utf-8')
                        self._append_log(self._get_message('alreadyInstalled'))
                        self._install_log.close()
                        self._install_log=None
                        
                except:
                    None
            return ui.Message(self._get_message('alreadyInstalled'))
        else:
            if not self._silent:
                #Scelta percorso
                ipt = ui.Inputs()
                if self._install_path.get() is None:
                    self._install_path.set(self._native.get_proposal_path())
                ipt.set_message(self._get_message('selectPathInstall'))
                ipt.add('path', self._get_message('path'), self._install_path, True)
                ipt.prev_step(self.step_init)
                ipt.next_step(self.step_check_install_path)
                return ipt
            else:
                self._install_path.set(self._native.get_proposal_path())
                return self.step_check_install_path(curui)


    def step_check_install_path(self, curui):
        pth = self._install_path.get()
        if pth.startswith("#SVIL#"):
            self._ambient="SVIL"
            pth=pth[6:]
            self._install_path.set(pth)
        elif pth.startswith("#QA#"):
            self._ambient="QA"
            pth=pth[4:]
            self._install_path.set(pth)
        if not self._silent:
            if not self._bmock and utils.path_exists(pth):
                m=self._get_message('confirmInstall').format(pth) + u'\n' + self._get_message('warningRemovePath')
            else:
                m=self._get_message('confirmInstall').format(pth)
            chs = ui.Chooser()
            chs.set_message(m)
            chs.add("yes", self._get_message('yes'))
            chs.add("no", self._get_message('no'))
            chs.set_variable(ui.VarString("no"))
            chs.set_accept_key("yes")
            chs.prev_step(self.step_check_already_install)
            chs.next_step(self.step_install)
            return chs
        else:
            return self.step_install(curui)
    
    def _download_progress(self, rtp):
        if "downloadtext" in self._options:
            dwnmsg=self._options["downloadtext"]
        else:
            dwnmsg=self._get_message('downloadFile')
        perc = int((float(rtp.get_byte_transfer()) / float(rtp.get_byte_length())) * 100.0)
        msg=dwnmsg.format(rtp.get_property('file_name'))
        prog = rtp.get_property('prog_start') + ((rtp.get_property('prog_end') - rtp.get_property('prog_start')) * (float(perc)/100.0))
        if "downloadtext" in self._options:
            perc=None
        self._uinterface.wait_message(msg, perc, prog)
    
    def _download_file(self, node_url, name, version, pstart,  pend):
        pth = self._install_path.get()
        url = node_url +  "getAgentFile.dw?name=" + name + "&version=" + version
        file_name = pth + utils.path_sep + name
        #Scarica il file
        rtp = communication.Response_Transfer_Progress({'on_data': self._download_progress})
        rtp.set_property('file_name', name)
        rtp.set_property('prog_start', pstart)
        rtp.set_property('prog_end', pend)
        communication.download_url_file(url, file_name, self._proxy, rtp)
    
    def _check_hash_file(self, name, shash):
        pth = self._install_path.get()
        fpath=pth + utils.path_sep + name
        
        md5 = hashlib.md5()
        with utils.file_open(fpath,'rb') as f: 
            for chunk in iter(lambda: f.read(8192), b''): 
                md5.update(chunk)
        h = md5.hexdigest()
        if h!=shash:
            raise Exception("Hash not valid. (file '{0}').".format(name))

    def _unzip_file(self, name, unzippath):
        pth = self._install_path.get()
        #Decoprime il file
        if unzippath!='':
            unzippath+=utils.path_sep 
        fpath=pth + utils.path_sep + name
        zfile = utils.zipfile_open(fpath)
        for nm in zfile.namelist():
            npath=pth + utils.path_sep + unzippath
            appnm = nm
            appar = nm.split("/")
            if (len(appar)>1):
                appnm = appar[len(appar)-1]
                npath+= nm[0:len(nm)-len(appnm)].replace("/",utils.path_sep)
            if not utils.path_exists(npath):
                utils.path_makedirs(npath)
            npath+=appnm
            fd = utils.file_open(npath,"wb")
            fd.write(zfile.read(nm))
            fd.close()
        zfile.close()
    
    def load_prop_json(self, fname):
        f = utils.file_open(fname)
        prp  = json.loads(f.read())
        f.close()
        return prp        
    
    def store_prop_json(self, prp, fname):
        s = json.dumps(prp, sort_keys=True, indent=1)
        f = utils.file_open(fname, 'wb')
        f.write(s)
        f.close()
    
    def obfuscate_password(self, pwd):
        return base64.b64encode(zlib.compress(pwd))

    def read_obfuscated_password(self, enpwd):
        return zlib.decompress(base64.b64decode(enpwd))
        
    def _download_files(self, pstart, pend):
        iniperc=0;
        if "downloadtext" in self._options:
            dwnmsg=self._options["downloadtext"]
            iniperc=None
        else:
            dwnmsg=self._get_message('downloadFile')
        
        if self._bmock:
            msg=dwnmsg.format(u'MOCK')
            self._uinterface.wait_message(msg,  None,  pstart)
            time.sleep(2)
            self._uinterface.wait_message(msg, None,  pend)
            return
        
        pth = self._install_path.get()
        fileversions = {}
        
        msg=dwnmsg.format(u'config.xml')
        self._uinterface.wait_message(msg,  iniperc,  pstart)
        prpconf = communication.get_url_prop(self._get_main_url() + "getAgentFile.dw?name=config.xml", self._proxy )
        if "name" in self._options:
            prpconf["name"] = self._options["name"]
        if "topinfo" in self._options:
            prpconf["topinfo"]=self._options["topinfo"]
        if "topimage" in self._options and utils.path_exists(self._options["topimage"]):
            if gdi.is_windows():
                prpconf["topimage"]=u'topimage.png'
                utils.path_copy(self._options["topimage"], pth + utils.path_sep + u'topimage.png')            
        if "logo" in self._options and utils.path_exists(self._options["logo"]):
            if gdi.is_windows():
                prpconf["logo"]=u'logo.ico'
                utils.path_copy(self._options["logo"], pth + utils.path_sep + u'logo.ico')                
        if "leftcolor" in self._options:
            prpconf["leftcolor"]=self._options["leftcolor"]                    
        if not self._runWithoutInstall:
            if "listenport" in self._options:
                prpconf['listen_port'] = self._options["listenport"]
            else:
                prpconf['listen_port'] = self._listen_port
        
        if self._runWithoutInstall:
            try:
                if utils.path_exists(self._install_path.get() + utils.path_sep +  u'config.json'):
                    appconf = self.load_prop_json(self._install_path.get() + utils.path_sep +  u'config.json')
                    if "preferred_run_user" in appconf:
                        prpconf["preferred_run_user"]=appconf["preferred_run_user"]
            except:
                None
                
        self.store_prop_json(prpconf, pth + utils.path_sep + u'config.json')
        
        if not (self._runWithoutInstall and utils.path_exists(pth + utils.path_sep + u"config.json") 
                and utils.path_exists(pth + utils.path_sep + u"fileversions.json") and utils.path_exists(pth + utils.path_sep + u"agent.pyc") 
                and utils.path_exists(pth + utils.path_sep + u"communication.pyc") and utils.path_exists(pth + utils.path_sep + u"sharedmem.pyc")):
            msg=dwnmsg.format('files.xml')
            self._uinterface.wait_message(msg, iniperc,  pstart)
            prpfiles = communication.get_url_prop(self._get_main_url() + "getAgentFile.dw?name=files.xml", self._proxy )
            
            if "nodeUrl" in prpfiles:
                node_url = prpfiles['nodeUrl']
            if node_url is None or node_url=="":
                raise Exception("Download files: Node not available.")        
            
            fls = []
            
            import detectinfo
            appnsfx = detectinfo.get_native_suffix()
            if not self._runWithoutInstall:
                if appnsfx is not None:
                    fls.append({'name':u'agentupd_' + appnsfx + '.zip', 'unzippath':u'native'})
            
            fls.append({'name':'agent.zip', 'unzippath':''})
            if not self._runWithoutInstall:
                fls.append({'name':u'agentui.zip', 'unzippath':u''})
            fls.append({'name':u'agentapps.zip', 'unzippath':u''})
            
            if appnsfx is not None:
                if not appnsfx=="linux_generic":
                    if not self._runWithoutInstall:
                        fls.append({'name':u'agentui_' + appnsfx + u'.zip', 'unzippath':u'native'})
                    fls.append({'name':u'agentlib_' + appnsfx + u'.zip', 'unzippath':u'native'})
            step = (pend-pstart) / float(len(fls))
            pos = pstart
            for i in range(len(fls)):
                fnm=fls[i]['name'];
                file_name = pth + utils.path_sep + fnm
                #Elimina file
                try:
                    utils.path_remove(file_name)
                except Exception:
                    None
                #Scarica file
                self._append_log(u"Download file " + fnm + " ...")
                self._download_file(node_url, fnm, prpfiles[fnm + '@version'], pos,  pos+step)
                self._append_log(u"Download file " + fnm + u".OK!")
                #Verifica hash
                self._append_log(u"Check file hash " + fnm + " ...")
                self._check_hash_file(fnm, prpfiles[fnm + '@hash'])
                self._append_log(u"Check file hash " + fnm + u".OK!")
                #Unzip file
                self._append_log(u"Unzip file " + fnm + " ...")
                self._unzip_file(fnm, fls[i]['unzippath'])
                self._append_log(u"Unzip file " + fnm + u".OK!")
                #Elimina file
                try:
                    utils.path_remove(file_name)
                except Exception:
                    None
                fileversions[fnm ]=prpfiles[fnm + '@version']
                pos+=step
            
            #Scrive files.json
            self.store_prop_json(fileversions, pth + utils.path_sep + u'fileversions.json')
        
    
    def _count_file_in_path(self, valid_path):
        x = 0
        for root, dirs, files in utils.path_walk(valid_path):
            for f in files:
                x = x+1
        return x

    def _copy_tree_file(self, fs, fd, msginfo):
        if utils.path_isdir(fs):
            if not utils.path_exists(fd):
                utils.path_makedirs(fd)
            lst=utils.path_list(fs)
            for fname in lst:
                self._copy_tree_file(fs + utils.path_sep + fname, fd + utils.path_sep + fname, msginfo)
        else:
            msginfo["progr"]+=msginfo["step"]
            perc =  int(((msginfo["progr"] - msginfo["pstart"] ) / (msginfo["pend"] - msginfo["pstart"] )) * 100.0)
            self._uinterface.wait_message(msginfo["message"], perc,  msginfo["progr"])
            if utils.path_exists(fd):
                utils.path_remove(fd)
            if utils.path_islink(fs):
                linkto = utils.path_readlink(fs)
                utils.path_symlink(linkto, fd)
            else:
                utils.path_copy(fs, fd)
                
        
    def _copy_tree(self, fs, ds, msg, pstart, pend):
        self._uinterface.wait_message(msg, 0, pstart)
        #Conta file
        nfile = self._count_file_in_path(fs)
        step = (pend-pstart) / nfile
        self._copy_tree_file(fs, ds, {'message':msg,  'pstart':pstart,  'pend':pend,  'progr':pstart, 'step':step })
    
    def _make_directory(self, pstart, pend):
        if self._bmock:
            return 
            
        pth = self._install_path.get()
        if utils.path_exists(pth):
            self._uinterface.wait_message(self._get_message('removeFile'), None, pstart)
            try:
                try:
                    self._native.stop_service()
                    self._native.delete_service()
                except:
                    None 
                utils.path_remove(pth)
            except:
                raise Exception(u'Can not remove path.') #Inserire messaggio in lingua
            
        #Crea le cartelle necessarie
        try:
            self._uinterface.wait_message(self._get_message('pathCreating'),  None, pend)
            utils.path_makedirs(pth)
        except:
            raise Exception(self._get_message('pathNotCreate'))
        
    def copy_runtime(self,pstart, pend):
        if self._bmock:
            msg=self._get_message('copyFiles')
            self._uinterface.wait_message(msg,  None,  pstart)
            time.sleep(1)
            self._uinterface.wait_message(msg,  None,  pend)
            return
        ds=self._install_path.get() + utils.path_sep + "runtime"
        msg=self._get_message('copyFiles')
        if utils.path_exists(_RUNTIME_PATH):
            self._copy_tree(_RUNTIME_PATH,ds,msg,pstart,pend)
        else:
            if not self._native.prepare_runtime_by_os(ds):
                raise Exception(self._get_message('missingRuntime'))
    
    
    def copy_native(self,pstart, pend):
        if self._bmock:
            msg=self._get_message('copyFiles')
            self._uinterface.wait_message(msg,  None,  pstart)
            time.sleep(1)
            self._uinterface.wait_message(msg,  None,  pend)
            return
        
        if not utils.path_exists(_NATIVE_PATH):
            raise Exception(self._get_message('missingNative'))            
        ds= self._install_path.get() + utils.path_sep + "native"
        msg=self._get_message('copyFiles')
        self._copy_tree(_NATIVE_PATH,ds,msg,0.76, 0.8)
    
    def _install_service(self, pstart, pend):
        if self._bmock:
            msg=self._get_message('installService')
            self._uinterface.wait_message(msg,  None,  pstart)
            time.sleep(1)
            msg=self._get_message('startService')
            self._uinterface.wait_message(msg,  None,  pstart)
            time.sleep(1)
            self._uinterface.wait_message(msg,  None,  pend)
            return
        msg=self._get_message('installService')
        self._uinterface.wait_message(msg, None,  pstart)
        
        #Rimuove un eventuale vecchia installazione
        self._append_log(u"Service - Try to remove dirty installation...")
        self._native.stop_service()
        self._native.delete_service()
                
        #Installa nuovo servizio
        self._append_log(u"Service - Installation...")
        if not self._native.install_service():
            raise Exception(self._get_message('installServiceErr'))
            
        #avvia il servizio
        self._append_log(u"Service - Starting...")
        msg=self._get_message('startService')
        self._uinterface.wait_message(msg, None,  pend)
        if not self._native.start_service():
            raise Exception(self._get_message("startServiceErr"))        
    
    def _install_monitor(self, pstart, pend):
        if self._bmock:
            msg=self._get_message('installMonitor')
            self._uinterface.wait_message(msg,  None,  pstart)
            time.sleep(1)
            self._uinterface.wait_message(msg,  None,  pend)
            return
        
        msg=self._get_message('installMonitor')
        self._uinterface.wait_message(msg,  None, pstart)        
        
        #Arresta un eventuale monitor attivo
        self._append_log(u"Monitor - Stopping...")
        stop_monitor(self._install_path.get())
        
        #Rimuove vecchia installazione
        self._append_log(u"Monitor - Try to remove dirty installation...")
        self._native.remove_auto_run_monitor()
        
        self._append_log(u"Monitor - Installing...")
        if not self._native.install_auto_run_monitor():
            raise Exception(self._get_message('installMonitorErr'))
        self._uinterface.wait_message(msg,  None, pend)
    
    def _install_shortcuts(self, pstart, pend):
        if self._bmock:
            msg=self._get_message('installShortcuts')
            self._uinterface.wait_message(msg,  None,  pstart)
            time.sleep(1)
            self._uinterface.wait_message(msg,  None,  pend)
            return
        
        msg=self._get_message('installShortcuts')
        self._uinterface.wait_message(msg,  None, pstart)
        
        #Rimuove collegamenti
        self._append_log(u"Shortcut - Try to remove dirty installation...")
        self._native.remove_shortcuts()
        
        #Installazione collegamneti
        self._append_log(u"Shortcut - Installing...")
        if not self._native.install_shortcuts():
            raise Exception(self._get_message('installShortcutsErr'))
        self._uinterface.wait_message(msg,  None, pend)
    
    def step_config_init(self, curui):
        #Benvenuto
        chs = ui.Chooser()
        m=self._get_message('configureInstallAgent')
        chs.set_message(m)
        chs.set_key("chooseInstallMode")
        chs.set_param('firstConfig',curui.get_param('firstConfig',False))
        chs.add("installCode", self._get_message('configureInstallCode'))
        chs.add("installNewAgent", self._get_message('configureInstallNewAgent'))        
        chs.set_variable(ui.VarString("installCode"))
        chs.next_step(self.step_config)
        return chs
    
    def step_config(self, curui):
        if curui.get_param('tryAgain',False):
            if curui.get_variable().get()=='configureLater':
                return ui.Message(self._get_message('endInstallConfigLater'))
        
        if curui.get_key() is not None and curui.get_key()=='chooseInstallMode':
            self._inatall_agent_mode=curui.get_variable().get()
        
        if self._inatall_agent_mode=="installNewAgent":
            ipt = ui.Inputs()
            ipt.set_key('configure')
            ipt.set_param('firstConfig',curui.get_param('firstConfig',False))
            ipt.set_message(self._get_message('enterInstallNewAgent'))
            if self._install_newag_user.get() is None:
                self._install_newag_user.set("")
            ipt.add('user', self._get_message('dwsUser'), self._install_newag_user, True)
            if self._install_newag_password.get() is None:
                self._install_newag_password.set("")
            ipt.add('password', self._get_message('dwsPassword'), self._install_newag_password, True)
            if self._install_newag_name.get() is None:
                self._install_newag_name.set("")
            ipt.add('name', self._get_message('agentName'), self._install_newag_name, True)
        else:
            ipt = ui.Inputs()
            ipt.set_key('configure')
            ipt.set_param('firstConfig',curui.get_param('firstConfig',False))
            if self._install_code.get() is None:
                self._install_code.set("")
            ipt.set_message(self._get_message('enterInstallCode'))
            ipt.add('code', self._get_message('code'), self._install_code, True)
        ipt.prev_step(self.step_config_init)
        ipt.next_step(self.step_config_install_request)
        return ipt
    
    def send_req(self, req, prms=None):
        try:
            if self._sharedmemclient==None or self._sharedmemclient.is_close():
                self._sharedmemclient=listener.SharedMemClient(self._install_path.get())
            return self._sharedmemclient.send_request("admin", "", req, prms)
        except: 
            return 'ERROR:REQUEST_TIMEOUT'
    
    def close_req(self):
        if self._sharedmemclient!=None and not self._sharedmemclient.is_close():
            self._sharedmemclient.close()
    
    def _send_proxy_config(self):
        pt = ''
        if self._proxy.get_port() is not None:
            pt=str(self._proxy.get_port())
        return self.send_req("set_proxy",{'type': self._proxy.get_type(), 
                                   'host': self._proxy.get_host(), 
                                   'port': pt, 
                                   'user': self._proxy.get_user(), 
                                   'password': self._proxy.get_password()})
    
    def step_configure_proxy_type(self, curui):
        chs = ui.Chooser()
        chs.set_key(curui.get_key())
        chs.set_message(self._get_message('chooseProxyType'))
        chs.add("SYSTEM", self._get_message('proxySystem'))
        chs.add("HTTP", self._get_message('proxyHttp'))
        chs.add("SOCKS4", self._get_message('proxySocks4'))
        chs.add("SOCKS4A", self._get_message('proxySocks4a'))
        chs.add("SOCKS5", self._get_message('proxySocks5'))
        chs.add("NONE", self._get_message('proxyNone'))
        chs.set_variable(self._proxy_type)
        if curui.get_key()=="install":
            if not self._runWithoutInstall:
                chs.prev_step(self.step_check_install_path)
            else:
                chs.prev_step(self.step_init)
        elif curui.get_key()=="runonfly":
            None #non abilita il tasto prev
        else:
            chs.prev_step(self.step_config)
        chs.next_step(self.step_configure_proxy_info)
        return chs
    
    def step_configure_proxy_info(self, curui):
        if curui.get_variable().get()=='HTTP' or curui.get_variable().get()=='SOCKS4' or curui.get_variable().get()=='SOCKS4A' or curui.get_variable().get()=='SOCKS5':
            ipt = ui.Inputs()
            ipt.set_key(curui.get_key())
            ipt.set_message(self._get_message('proxyInfo'))
            ipt.add('proxyHost', self._get_message('proxyHost'), self._proxy_host,  True)
            ipt.add('proxyPort', self._get_message('proxyPort'), self._proxy_port,  True)
            ipt.add('proxyAuthUser', self._get_message('proxyAuthUser'), self._proxy_user,  False)
            ipt.add('proxyAuthPassword', self._get_message('proxyAuthPassword'), self._proxy_password,  False)
            ipt.prev_step(self.step_configure_proxy_type)
            ipt.next_step(self.step_configure_proxy_set)
            return ipt
        else:
            self._proxy_host.set("")
            self._proxy_port.set("")
            self._proxy_user.set("")
            self._proxy_password.set("")
            return self.step_configure_proxy_set(curui)
    
    def step_configure_proxy_set(self, curui):
        if curui.get_param('tryAgain',False):
            if curui.get_variable() is not None and curui.get_variable().get()=='configureLater':
                return self.step_config(curui)
        #Verifica se la porta è numerica
        oldprx = self._proxy
        self._proxy=communication.ProxyInfo()
        self._proxy.set_type(self._proxy_type.get())
        self._proxy.set_host(self._proxy_host.get())
        if self._proxy_type.get()=='HTTP' or self._proxy_type.get()=='SOCKS4' or self._proxy_type.get()=='SOCKS4A' or self._proxy_type.get()=='SOCKS5':
            try:
                self._proxy.set_port(int(self._proxy_port.get()))
            except:
                self._proxy = oldprx
                return ui.ErrorDialog(self._get_message("validInteger") .format(self._get_message('proxyPort')))
        self._proxy.set_user(self._proxy_user.get())
        self._proxy.set_password(self._proxy_password.get())
        if curui.get_key()=='install':
            curui.set_key('retryDownloadProxy')
            return self.step_install(curui)
        elif curui.get_key()=="runonfly":
            curui.set_key('retryRunOnFlyProxy')
            return self.step_runonfly(curui)
        else:
            try:
                s=self._send_proxy_config()
                if s=='OK':
                    return self.step_config_install_request(curui)
                elif s=="ERROR:REQUEST_TIMEOUT":
                    return ui.ErrorDialog(self._get_message('errorConnectionConfig'))
                else:
                    return ui.ErrorDialog(s) 
            except:
                chs = ui.Chooser()
                chs.set_key(curui.get_key())
                chs.set_param("tryAgain", True)
                chs.set_message(self._get_message('errorConnectionConfig'))
                chs.add("noTryAgain", self._get_message('noTryAgain'))
                chs.add("configureLater", self._get_message('configureLater'))
                chs.set_variable(ui.VarString("noTryAgain"))
                chs.prev_step(self.step_config)
                chs.next_step(self.step_configure_proxy_set)
                return chs
            return self._configure_proxy_set(curui)

    def step_config_install_request(self, curui):
        if self._bmock:
            self._append_log(u"End Installation.")
            return ui.Message(self._get_message('endInstall'))
        
        if not self._silent:
            if curui.get_param('tryAgain',False):
                if curui.get_variable().get()=='configureLater':
                    return ui.Message(self._get_message('endInstallConfigLater'))
                elif curui.get_variable().get()=='configProxy':
                    return self.step_configure_proxy_type(curui)
        
        if self._silent:
            if "key" in self._options:
                self._inatall_agent_mode="installCode"
                self._install_code.set(self._options["key"])
            elif "user" in self._options and "password" in self._options:
                self._inatall_agent_mode="installNewAgent"
                self._install_newag_user.set(self._options["user"])
                self._install_newag_password.set(self._options["password"])
                if "agentName" in self._options:
                    self._install_newag_name.set(self._options["agentName"])
                else:
                    self._install_newag_name.set(platform.node())
            else:
                self._append_log(u"End Installation.")
                return ui.Message(self._get_message('endInstall'))
            
        if self._inatall_agent_mode=="installNewAgent":
            self._append_log(u"Create new Agent ...")
            msg=self._get_message('createNewAgent')
        else:
            self._append_log(u"Check Install Code ...")
            msg=self._get_message('checkInstallCode')            
        self._uinterface.wait_message(msg)
        page = None
        try:
            #Imposta il proxy
            if curui.get_param('firstConfig',False) and self._proxy is not None:
                s=self._send_proxy_config()
                if s!='OK':
                    if s=="ERROR:REQUEST_TIMEOUT":
                        self._append_log(u"Error Configure: Request timeout")
                        return ui.ErrorDialog(self._get_message('errorConnectionConfig'))
                    else:
                        self._append_log(u"Error Configure: " + s)
                        return ui.ErrorDialog(s)
            #Verifica codice
            s = None
            if self._inatall_agent_mode=="installNewAgent":
                s = self.send_req("install_new_agent",{'user': self._install_newag_user.get(), 'password': self._install_newag_password.get(), 'name':self._install_newag_name.get()})
            else:
                s = self.send_req("install_key",{'code': self._install_code.get().strip().replace(" ", "")})
            if s=='OK':
                self._append_log(u"End Installation.")
                return ui.Message(self._get_message('endInstall'))
            elif s=="ERROR:INVALID_CODE" or s=="ERROR:INVALID_USER_PASSWORD" or s=="ERROR:NAME_NOT_VALID" or s=="ERROR:ALREADY_EXISTS" or s=="ERROR:AGENT_MAX":
                if not self._silent:
                    chs = ui.Chooser()
                    chs.set_key('configure')
                    chs.set_param('tryAgain',True)
                    if s=="ERROR:INVALID_CODE":
                        chs.set_message(self._get_message('errorInvalidCode'))
                    elif s=="ERROR:INVALID_USER_PASSWORD":
                        chs.set_message(self._get_message('errorInvalidUserPassword'))
                    elif s=="ERROR:NAME_NOT_VALID":
                        chs.set_message(self._get_message('errorAgentNameNotValid'))
                    elif s=="ERROR:ALREADY_EXISTS":
                        chs.set_message(self._get_message('errorAgentAlreadyExsists').format(self._install_newag_name.get()))
                    elif s=="ERROR:AGENT_MAX":
                        chs.set_message(self._get_message('errorAgentMax'))
                    else:
                        chs.set_message(s)
                    chs.add("reEnter", self._get_message('reEnterData'))
                    chs.add("configureLater", self._get_message('configureLater'))
                    chs.set_variable(ui.VarString("reEnter"))
                    chs.next_step(self.step_config)
                    chs.prev_step(self.step_config)
                    return chs
                else:
                    appse=s.split(":")[1];
                    self._append_log(u"Error Configure: " + appse)
                    return ui.ErrorDialog(appse)
            elif s=="ERROR:CONNECT_ERROR":
                if not self._silent:
                    chs = ui.Chooser()
                    chs.set_key('configure')
                    chs.set_param('tryAgain',True)
                    chs.set_message(self._get_message('errorConnectionQuestion'))
                    chs.add("configProxy", self._get_message('yes'))
                    chs.add("noTryAgain", self._get_message('noTryAgain'))
                    chs.add("configureLater", self._get_message('configureLater'))
                    chs.set_variable(ui.VarString("noTryAgain"))
                    chs.prev_step(self.step_config)
                    chs.next_step(self.step_config_install_request)
                    return chs
                else:
                    appse="Connect Error";
                    self._append_log(u"Error Configure: " + appse)
                    return ui.ErrorDialog(appse)
            
            elif s=="ERROR:REQUEST_TIMEOUT":
                self._append_log(u"Error Configure: Request timeout")
                return ui.ErrorDialog(self._get_message('errorConnectionConfig'))
            else:
                self._append_log(u"Error Configure: " + s)
                return ui.ErrorDialog(s) 
        except Exception as e:
            if not self._silent:
                chs = ui.Chooser()
                chs.set_key('configure')
                chs.set_param('tryAgain',True)
                chs.set_message(self._get_message('errorConnectionConfig'))
                chs.add("noTryAgain", self._get_message('noTryAgain'))
                chs.add("configureLater", self._get_message('configureLater'))
                chs.set_variable(ui.VarString("noTryAgain"))
                chs.prev_step(self.step_config)
                chs.next_step(self.step_config_install_request)
                return chs
            else:
                self._append_log(u"Error Configure: " + exception_to_string(e))
                return ui.ErrorDialog(exception_to_string(e))
        finally:
            if page is not None:
                page.close()
    
    def _append_log(self, txt):
        try:
            if not self._bmock:
                if self._install_log is not None:
                    self._install_log.write(unicode(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())) + u" - " + txt + u"\n")
                    self._install_log.flush()
        except:
            None    
    
    def _runonfly_update(self,pthsrc,pthdst):
        lst=utils.path_list(pthsrc)
        for fname in lst:
            if utils.path_isfile(pthsrc + utils.path_sep + fname):
                if utils.path_isfile(pthdst + utils.path_sep + fname):
                    utils.path_remove(pthdst + utils.path_sep + fname)
                utils.path_copy(pthsrc + utils.path_sep + fname, pthdst + utils.path_sep + fname)
            elif utils.path_isdir(pthsrc + utils.path_sep + fname):
                self._runonfly_update(pthsrc + utils.path_sep + fname,pthdst + utils.path_sep + fname)
    
    
    #COMPATIBILITA' VERSIONI PRECEDENTI DI RUNONFLY
    def _fix_runonfly_old_version(self):
        if utils.path_exists(u"fileversions.json"):            
            fver = self.load_prop_json('fileversions.json')
            if 'agent.zip' in fver:
                lver = long(fver['agent.zip'])
                if lver<1484751796000:
                    self._append_log(u"Fixing old version...")
                    sys.path.insert(0,self._install_path.get())
                    objlib = importlib.import_module("agent")
                    try:
                        reload(objlib)
                        func = getattr(objlib,  'Main')
                        appcls = func(["-runonfly","-filelog"])
                        #IMPOSTARE IL PROXY
                        appcls._read_config_file()
                        appcls._load_config()
                        appcls._update_ready=False
                        bnoupd = appcls._check_update()
                        #appcls.set_runonfly_action(self._runonfly_action)
                        #appcls.start()
                    finally:
                        if appcls is not None:
                            try:
                                appcls.unload_library()
                            except:
                                None
                        sys.path.remove(sys.path[0])
                    if bnoupd:
                        raise Exception("") #GESTITO IN step_runonfly
                    return True
        return False                
        
    def _step_runonfly_conn_msg(self, usr, pwd):
        appwmsg=[]        
        if "runputcode" in self._options and self._options["runputcode"]:
            if "runtoptext" in self._options:                            
                appwmsg.append(self._options["runtoptext"])
            else:
                appwmsg.append(self._get_message("runWithoutInstallationOnlineTopPutCode"))
            appwmsg.append(u"\n\n\n\n")
            if "runbottomtext" in self._options:                            
                appwmsg.append(self._options["runbottomtext"])
            else:
                appwmsg.append(self._get_message("runWithoutInstallationOnlineBottomPutCode"))
        else:
            if "runtoptext" in self._options:                            
                appwmsg.append(self._options["runtoptext"])
            else:
                appwmsg.append(self._get_message("runWithoutInstallationOnlineTop"))
            appwmsg.append(u"\n\n")
            appwmsg.append(self._get_message("runWithoutInstallationOnlineUser").format(usr))
            appwmsg.append(u"\n\n")
            appwmsg.append(self._get_message("runWithoutInstallationOnlinePassword").format(pwd))
            appwmsg.append(u"\n\n")
            if "runbottomtext" in self._options:                            
                appwmsg.append(self._options["runbottomtext"])
            else:
                appwmsg.append(self._get_message("runWithoutInstallationOnlineBottom"))
        self._uinterface.wait_message(u"".join(appwmsg), allowclose=True)
     
    def step_runonfly_putcode(self, curui):
        ipt = ui.Inputs()
        ipt.set_key('configure')
        #ipt.set_param('firstConfig',curui.get_param('firstConfig',False))
        if self._run_code.get() is None:
            self._run_code.set("")
        ipt.set_message(self._get_message('enterRunCode'))
        ipt.add('code', self._get_message('code'), self._run_code, True)
        ipt.prev_step(self.step_init)
        ipt.next_step(self.step_runonfly)
        return ipt
     
    def step_runonfly(self, curui):
        if self._bmock:
            self._uinterface.wait_message(self._get_message("runWithoutInstallationStarting"))
            time.sleep(1)
            self._step_runonfly_conn_msg("MOCK","MOCK")
            while self._runWithoutInstallAgentAlive:
                time.sleep(1)
            return ui.Message(self._get_message('runWithoutInstallationEnd')) 
        
        #Prepare file
        self._append_log(u"Prepare file...")
        if "runputcode" in self._options and self._options["runputcode"]:
            self._native.prepare_file_runonfly(self._run_code.get())
        else:
            self._native.prepare_file_runonfly(None)
        self._append_log(u"Prepare file.OK!")
        
        #Start agent
        if self._proxy is not None:
            prpconf = self.load_prop_json(self._install_path.get() + utils.path_sep +  u'config.json')
            if self._proxy.get_type() is not None:
                prpconf['proxy_type'] = self._proxy.get_type()
            if self._proxy.get_host() is not None:
                prpconf['proxy_host'] = self._proxy.get_host()
            if self._proxy.get_port() is not None:
                prpconf['proxy_port'] = self._proxy.get_port()
            if self._proxy.get_user() is not None:
                prpconf['proxy_user'] = self._proxy.get_user()
            else:
                prpconf['proxy_user'] = ""
            if self._proxy.get_password() is not None:
                prpconf['proxy_password'] = self.obfuscate_password(self._proxy.get_password())
            else:
                prpconf['proxy_password'] = ""
            self.store_prop_json(prpconf, self._install_path.get() + utils.path_sep +  u'config.json')
        
        if curui.get_key() is not None and curui.get_key()=='retryRunOnFly':
            if curui.get_variable().get()=='configProxy':
                curui.set_key('runonfly')
                return self.step_configure_proxy_type(curui)
        
        self._append_log(u"Changing current directory to " + utils.path_absname(self._install_path.get()) + " ...")
        utils.system_changedir(self._install_path.get())
        self._runWithoutInstallAgentCloseEnd=False
        runcode_notfound=False
        runcode_connected=False
        pstsharedmem=None
        try:   
            while self._runWithoutInstallAgentAlive:
                self._uinterface.wait_message(self._get_message("runWithoutInstallationStarting"))
                self._append_log(u"Starting...")
                if utils.path_exists(u"update"):
                    self._append_log(u"Updating...")
                    self._uinterface.wait_message(self._get_message("runWithoutInstallationUpdating"))
                    self._runonfly_update(u"update",".")
                    utils.path_remove(u"update")
            
                #COMPATIBILITA' VERSIONI PRECEDENTI DI RUNONFLY
                if self._fix_runonfly_old_version():
                    if utils.path_exists(u"update"):
                        self._uinterface.wait_message(self._get_message("runWithoutInstallationUpdating"))
                        self._runonfly_update(u"update",".")
                        utils.path_remove(u"update")
            
                #CHECK FILE
                if utils.path_exists(u"dwagent.pid"):
                    utils.path_remove(u"dwagent.pid")
                if utils.path_exists(u"dwagent.start"):
                    utils.path_remove(u"dwagent.start")
                if utils.path_exists(u"dwagent.stop"):
                    utils.path_remove(u"dwagent.stop")
                if utils.path_exists(u"dwagent.status"):
                    utils.path_remove(u"dwagent.status")
                
                #Scrive pid
                f = utils.file_open(u"dwagent.pid", 'wb')
                f.write(str(os.getpid()))
                f.close()            
                 
                #Avvia il servizio
                self._append_log(u"Run... ")
                if "runputcode" in self._options and self._options["runputcode"]:
                    ponfly=self._native.start_runonfly(self._run_code.get())
                else:
                    ponfly=self._native.start_runonfly(None)
                #Attende L'avvio
                cnt=0
                while (not utils.path_exists(u"dwagent.start")):
                    time.sleep(1)
                    cnt+=1
                    if cnt>10: #10 Secondi
                        raise Exception("") #GESTITO SOTTO
                if utils.path_exists(u"dwagent.start"):
                    utils.path_remove(u"dwagent.start")
                self._append_log(u"Started.")
                
                #GESTISCE STATO
                pstsharedmem = sharedmem.Property()
                pstsharedmem.open("runonfly")
                agpid=int(pstsharedmem.get_property("pid"))
                curst=""
                while self._native.is_task_running(agpid) and (ponfly is None or ponfly.poll() is None):
                    st = pstsharedmem.get_property("status")
                    if st!=curst:
                        curst=st
                        if st=="CONNECTED":
                            if "runputcode" in self._options and self._options["runputcode"]:
                                runcode_connected=True
                                self._step_runonfly_conn_msg(None,None)
                            else:            
                                usr=pstsharedmem.get_property("user")
                                usr=usr[0:3] + u"-" + usr[3:6] + u"-" + usr[6:9] + u"-" + usr[9:]
                                self._step_runonfly_conn_msg(usr, pstsharedmem.get_property("password"))                            
                        elif st=="CONNECTING":
                            self._uinterface.wait_message(self._get_message("runWithoutInstallationConnecting"), allowclose=True)
                        elif st=="RUNCODE_NOTFOUND":
                            if "runputcode" in self._options and self._options["runputcode"]:
                                self._runWithoutInstallAgentAlive=False
                                if runcode_connected:
                                    self._runWithoutInstallAgentCloseByClient=True
                                else:
                                    runcode_notfound=True
                        elif st is not None and st.startswith("WAIT:"):
                            retry=int(st.split(":")[1])
                            if retry>3:
                                self._runWithoutInstallAgentAlive=False
                            else:
                                self._uinterface.wait_message(self._get_message("runWithoutInstallationWait").format(str(retry)), allowclose=True)

                    if self._runWithoutInstallAgentAlive==False:
                        break
                    time.sleep(1)
                
                if runcode_notfound==False:
                    self._uinterface.wait_message(self._get_message("runWithoutInstallationClosing"))
                
                f = utils.file_open(u"dwagent.stop", 'wb')
                f.close()
                cnt=0
                while self._native.is_task_running(agpid) and (ponfly is None or ponfly.poll() is None):
                    time.sleep(1)
                    cnt+=1
                    if cnt>5: #5 Secondi
                        break
                
                pstsharedmem.close()
                pstsharedmem=None
                time.sleep(1)
                
        except Exception as e:
            f = utils.file_open(u"dwagent.stop", 'wb')
            f.close()
            try:
                if pstsharedmem is not None:
                    pstsharedmem.close()
                    pstsharedmem=None
            except:
                None
            utils.system_changedir(self._current_path)
            self._runWithoutInstallAgentCloseEnd=True
            #Se non è partito l'agente potrebbe dipendere da un problema di file corrotti
            self._append_log(u"Error: " + exception_to_string(e) + u"\n" + get_stacktrace_string())
            return ui.Message(self._get_message("runWithoutInstallationUnexpectedError").format(utils.path_absname(self._install_path.get())) + "\n\n" + str(e))
            
        
        utils.system_changedir(self._current_path)
        self._runWithoutInstallAgentCloseEnd=True
        if self._runWithoutInstallAgentCloseByClient:            
            return ui.Message(self._get_message('runWithoutInstallationEnd'))  
        else:
            self._runWithoutInstallAgentAlive=True
            if runcode_notfound:
                return ui.ErrorDialog(self._get_message('errorInvalidCode'))                
            else:
                chs = ui.Chooser()
                chs.set_key("retryRunOnFly")
                chs.set_message(self._get_message('errorConnectionQuestion'))
                chs.add("configProxy", self._get_message('yes'))
                chs.add("noTryAgain", self._get_message('noTryAgain'))
                chs.set_variable(ui.VarString("noTryAgain"))
                chs.next_step(self.step_runonfly)
                return chs
        
            
    
    def step_install(self, curui):
        if utils.path_exists(self._current_path + utils.path_sep + "ambient.svil"):
            self._ambient="SVIL"
        elif utils.path_exists(self._current_path + utils.path_sep + "ambient.qa"):
            self._ambient="QA"
            
        if not self._silent:
            if curui.get_key() is None and curui.get_variable().get()=="no":
                return ui.Message(self._get_message('cancelInstall'))
            
            if curui.get_key() is not None and curui.get_key()=='retryDownload':
                if curui.get_variable().get()=='configProxy':
                    curui.set_key('install')
                    return self.step_configure_proxy_type(curui)
        
        
        if self._runWithoutInstall:
            if self._name is None:
                self._install_path.set(u".." + utils.path_sep + u"dwagentonfly")
            else:
                self._install_path.set(u".." + utils.path_sep + self._name.lower() + u"onfly")
            #Carica proxy da file
            if self._runWithoutInstallProxySet==False and utils.path_exists(self._install_path.get() + utils.path_sep + u"config.json"):
                self._runWithoutInstallProxySet=True
                prpconf=self.load_prop_json(self._install_path.get() + utils.path_sep + u"config.json")
                if 'proxy_type' in prpconf and prpconf['proxy_type']!="":
                    self._proxy=communication.ProxyInfo()
                    self._proxy.set_type(prpconf['proxy_type'])
                    self._proxy_type.set(prpconf['proxy_type'])
                    if 'proxy_host' in prpconf:
                        self._proxy.set_host(prpconf['proxy_host'])
                        self._proxy_host.set(prpconf['proxy_host'])
                    if 'proxy_port' in prpconf and prpconf['proxy_port']!="":
                        self._proxy.set_port(prpconf['proxy_port'])
                        self._proxy_port.set(str(prpconf['proxy_port']))
                    if 'proxy_user' in prpconf:
                        self._proxy.set_user(prpconf['proxy_user'])
                        self._proxy_user.set(prpconf['proxy_user'])
                    if 'proxy_password' in prpconf and prpconf['proxy_password']!="":
                        self._proxy.set_password(self.obfuscate_password(prpconf['proxy_password']))
        
        pth = self._install_path.get()
        if pth.endswith(utils.path_sep) is True:
            pth=pth[0:len(pth)-1]
        
        if not self._bmock:
            if self._runWithoutInstall and not utils.path_exists(pth):
                utils.path_makedir(pth)
                
        #Inizializza log
        if not self._bmock:
            if self._install_log is None:
                try:
                    if self._install_log_path is not None:
                        try:
                            self._install_log = utils.file_open(self._install_log_path, "wb", encoding='utf-8')
                        except:
                            None
                    if self._install_log is None:
                        self._install_log = utils.file_open(u'install.log', "wb", encoding='utf-8')
                except:
                    try:
                        self._install_log = utils.file_open(u".." + utils.path_sep + u'dwagent_install.log', "wb", encoding='utf-8')                    
                    except:
                        None
            
        
        self._install_path.set(unicode(pth))
        #Imposta path per native
        self._native.set_install_path(unicode(pth))
        self._native.set_install_log(self._install_log)
            
            
        try:
            #Verifica permessi di amministratore (SOLO se silent altrimenti gia' lo ha fatto precedentemente
            if self._silent: 
                msg = self._native.check_init_install(True)
                if msg is not None:
                    raise Exception(msg)
        
            
            if not self._runWithoutInstall:
                if curui.get_key()!='retryDownload' and curui.get_key()!='retryDownloadProxy':
                    #Crea cartella
                    self._append_log(u"Make folder " + pth + u"...")
                    self._make_directory(0.01, 0.02)
                    self._append_log(u"Make folder " + pth + u".OK!")
                                        
            #Copia Licenza
            if not self._bmock:
                pthlic = self._install_path.get() + utils.path_sep + u"LICENSES"
                if not utils.path_exists(pthlic):
                    utils.path_makedirs(pthlic)
                    #if not self._runWithoutInstall:
                    utils.path_copy(u"LICENSES" + utils.path_sep + u"README", self._install_path.get() + utils.path_sep + u"README")
                    utils.path_copy(u"LICENSES" + utils.path_sep + u"runtime", pthlic + utils.path_sep + u"runtime")
                    utils.path_copy(u"LICENSES" + utils.path_sep + u"core", pthlic + utils.path_sep + u"core")
                    utils.path_copy(u"LICENSES" + utils.path_sep + u"ui", pthlic + utils.path_sep + u"ui")
            #Download file
            try:
                self._append_log(u"Download files...")
                if not self._runWithoutInstall:
                    self._download_files(0.03, 0.5)
                else:
                    self._download_files(0.01, 0.9)
                self._append_log(u"Download files.OK!")
            except Exception as e:
                if not self._silent:
                    self._append_log(u"Error Download files: " + exception_to_string(e) + u"\n" + get_stacktrace_string())
                    chs = ui.Chooser()
                    chs.set_key("retryDownload")
                    chs.set_message(exception_to_string(e) + u"\n\n" + self._get_message('errorConnectionQuestion'))
                    chs.add("configProxy", self._get_message('yes'))
                    chs.add("noTryAgain", self._get_message('noTryAgain'))
                    chs.set_variable(ui.VarString("noTryAgain"))
                    if not self._runWithoutInstall:
                        chs.prev_step(self.step_check_install_path)
                    else:
                        chs.prev_step(self.step_init)
                        self._install_path.set(None)
                    chs.next_step(self.step_install)
                    return chs
                else:
                    raise Exception(u"Error Download files: " + exception_to_string(e) + u"\n" + get_stacktrace_string())
            
            if not self._runWithoutInstall:
                #Copia Runtime
                self._append_log(u"Copy runtime...")
                self.copy_runtime(0.51, 0.75)
                self._append_log(u"Copy runtime.OK!")
                #Copia Native
                self._append_log(u"Copy native...")
                self.copy_native(0.76, 0.8)           
                self._append_log(u"Copy native.OK!")
                #Prepare file
                self._append_log(u"Prepare file...")
                if not self._bmock:
                    self._native.prepare_file()
                self._append_log(u"Prepare file.OK!")
                
                #Installa Servizio
                self._append_log(u"Install service...")
                self._install_service(0.81, 0.85)
                self._append_log(u"Install service.OK!")
                
                #Installa Monitor
                self._append_log(u"Install monitor...")
                self._install_monitor(0.86, 0.90)
                self._append_log(u"Install monitor.OK!")
                
                #Installa Shortcuts
                self._append_log(u"Install Shortcuts...")
                self._install_shortcuts(0.91,  1)
                self._append_log(u"Install Shortcuts.OK!")
                
                #Installazioni specifiche per os
                self._append_log(u"Install Extra OS...")
                if not self._bmock:
                    self._native.install_extra()
                self._append_log(u"Install Extra OS.OK!")
                
                #Inizia la configurazione
                if not self._silent:
                    curui.set_param('firstConfig',True)
                    return self.step_config_init(curui)
                else:
                    curui.set_param('firstConfig',False)
                    return self.step_config_install_request(curui)
                
            else:
                #Aggiorna cacerts.pem
                if not self._bmock:
                    utils.path_copy('cacerts.pem',self._install_path.get() + utils.path_sep + 'cacerts.pem')
                
                #Copia Native
                self._append_log(u"Copy native...")
                self.copy_native(0.91, 1)
                self._append_log(u"Copy native.OK!")
                
                if "runputcode" in self._options and self._options["runputcode"]:
                    return self.step_runonfly_putcode(curui)
                else:                    
                    return self.step_runonfly(curui)
            
        except Exception as e:            
            self._append_log(u"Error Install: " + exception_to_string(e))
            return ui.ErrorDialog(exception_to_string(e)) 
            

class Uninstall:
    def __init__(self):
        self._native = get_native()
        self._uinterface=None
        self._install_path=None
        self._options=None
        #self._install_log_path=None
        self._silent=False;
        self._name=None
    
    def _get_message(self, key):
        smsg = messages.get_message(key)
        if self._name is not None:
            return smsg.replace(u"DWAgent",self._name)
        else:
            return smsg
        
    def start(self, aropts={}):
        self._options=aropts
        #if "logpath" in self._options:
        #    self._install_log_path=self._options["logpath"]
        bgui=True
        if "gui" in self._options:
            bgui=self._options["gui"]
        self._silent=False;
        if "silent" in self._options:
            self._silent=self._options["silent"]
            if self._silent:
                bgui=False
                messages.set_locale(None)     
        
        confjson={}
        try:
            f = utils.file_open('config.json')
            confjson = json.loads(f.read())
            f.close()
        except Exception:
            None
        prmsui={}
        if "name" in confjson:
            self._name=unicode(confjson["name"])
            self._native.set_name(self._name)
        else:            
            self._native.set_name(u"DWAgent")
        prmsui["title"]=self._get_message('titleUninstall')
        if "topinfo" in confjson:
            prmsui["topinfo"]=confjson["topinfo"]
        if "topimage" in confjson:
            prmsui["topimage"]=confjson["topimage"]
        if "logo" in confjson:
            prmsui["logo"]=confjson["logo"]
        if "leftcolor" in confjson:
            prmsui["leftcolor"]=confjson["leftcolor"]            
        self._uinterface = ui.UI(prmsui, self.step_init)
        self._uinterface.start(bgui)
        
        #CHIUDE IL LOG
        try:
            if self._install_log is not None:
                self._install_log.close()
        except:
            None
        
    def step_init(self, curui):
        msg = self._native.check_init_uninstall()
        if msg is not None:
            return ui.Message(msg)
        self._install_path = self._native.get_install_path()
        if self._install_path is None:
            return ui.Message(self._get_message('notInstalled'))
        else:
            if self._silent==False:
                self._install_path = unicode(self._install_path)
                #Conferma disinstallazione
                chs = ui.Chooser()
                chs.set_message(self._get_message('confirmUninstall'))
                chs.add("yes", self._get_message('yes'))
                chs.add("no", self._get_message('no'))
                chs.set_variable(ui.VarString("no"))
                chs.set_accept_key("yes")
                chs.next_step(self.step_remove)
                return chs
            else:
                return self.step_remove(curui)
    
    def _uninstall_monitor(self, pstart, pend):
        msg=self._get_message('uninstallMonitor')
        self._uinterface.wait_message(msg,  None, pstart)
        stop_monitor(self._install_path)
        self._native.remove_auto_run_monitor()
    
    def _uninstall_service(self, pstart, pend):
        msg=self._get_message('uninstallService')
        self._uinterface.wait_message(msg,  None, pstart)
        self._native.stop_service()
        self._native.delete_service()
    
    def _uninstall_shortcuts(self, pstart, pend):
        msg=self._get_message('uninstallShortcuts')
        self._uinterface.wait_message(msg,  None, pstart)
        self._native.remove_shortcuts()
    
    def _append_log(self, txt):
        try:
            if self._install_log is not None:
                self._install_log.write(unicode(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())) + u" - " + txt + u"\n")
                self._install_log.flush()
        except:
            None   
    
    def step_remove(self, curui):
        if self._silent==False:
            if curui.get_key() is None and curui.get_variable().get()=="no":
                return ui.Message(self._get_message('cancelUninstall'))
        try:
            #Inizializza log
            try:
                self._install_log = utils.file_open(u"unistall.log", "wb", encoding='utf-8')
            except:
                try:
                    self._install_log = utils.file_open(u".." + utils.path_sep + u"dwagent_unistall.log", "wb", encoding='utf-8')                    
                except:
                    None
            
            self._native.set_install_path(self._install_path)
            self._native.set_install_log(self._install_log)
            
            self._append_log(u"Uninstall monitor...")
            self._uninstall_monitor(0.01, 0.4)
            
            self._append_log(u"Uninstall service...")
            self._uninstall_service(0.41, 0.8)
            
            self._append_log(u"Uninstall shortcuts...")
            self._uninstall_shortcuts(0.81, 1)
    
            #Scrive file per eliminazione della cartella
            f = utils.file_open(self._install_path + utils.path_sep + u"agent.uninstall", "w")
            f.write("\x00")
            f.close()

            self._append_log(u"End Uninstallation.")
            return ui.Message(self._get_message('endUninstall'))
        except Exception as e:
            self._append_log(u"Error Uninstall: " + exception_to_string(e))
            return ui.ErrorDialog(exception_to_string(e))
            

def fmain(args): #SERVE PER MACOS APP
    i = None
    arotps={}
    arotps["gui"]=True
    for arg in args: 
        if arg.lower() == "uninstall":
            i = Uninstall()
        elif arg.lower() == "-console":
            arotps["gui"]=False
        elif arg.lower() == "-silent":
            arotps["silent"]=True
        elif arg.lower().startswith("gotoopt="):
            arotps["gotoopt"]=arg[8:]
        elif arg.lower().startswith("key="):
            arotps["key"]=arg[4:]
        elif arg.lower().startswith("user="):
            arotps["user"]=arg[5:]
        elif arg.lower().startswith("password="):
            arotps["password"]=arg[9:]
        elif arg.lower().startswith("name="):
            arotps["agentName"]=arg[5:]
        elif arg.lower().startswith("logpath="):
            arotps["logpath"]=arg[8:]
        elif arg.lower().startswith("lang="):
            try:
                messages.set_locale(arg[5:])
            except:
                None            
    if i is None:
        i = Install()
    i.start(arotps)    
    sys.exit(0)
    
if __name__ == "__main__":
    fmain(sys.argv)    
    
    