# -*- coding: utf-8 -*-

'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
try:
    from . import messages
except: #FIX INSTALLER
    import messages
try:
    from . import gdi
except: #FIX INSTALLER
    import gdi
try:
    from . import ui
except: #FIX INSTALLER
    import ui
import os
import hashlib
import json
import shutil
import time
import sys
import communication
import stat
import platform
import listener
import importlib
import zlib
import base64
import ipc
import ctypes
import subprocess
import utils


_MAIN_URL = "https://www.dwservice.net/"
_MAIN_URL_QA = "https://qa.dwservice.net/"
_MAIN_URL_DEV = "https://dev.dwservice.net/dws_site/"
_NATIVE_PATH = u'native'
_RUNTIME_PATH = u'runtime'
_INSTALLER_VERSION=1

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

class NativeLinux:
    def __init__(self):
        self._name=None
        self._current_path=None
        self._install_path=None
        self._etc_path=None
        self._logo_path=u"/ui/images/logo.png"
    
    def set_name(self, k):
        self._name=k
        self._etc_path = u"/etc/" + self._name.lower()
    
    def set_logo_path(self, pth):
        self._logo_path=pth
    
    def set_current_path(self, pth):
        self._current_path=pth
    
    def set_install_path(self, pth):
        self._install_path=pth
        
    def set_install_log(self, log):
        self._install_log=log
        
    def get_proposal_path(self):
        return u"/usr/share/" + self._name.lower()
    
    def get_install_path(self) :
        if utils.path_exists(self._etc_path):
            f = utils.file_open(self._etc_path,"rb")
            try:
                s=f.read()
                ar = json.loads(utils.bytes_to_str(s,"utf8"))
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
    
    def replace_key_file(self, path, lst):
        fin = utils.file_open(path, "r", encoding='utf-8')
        data = fin.read()
        fin.close()
        fout = utils.file_open(path, "w", encoding='utf-8')
        for k in lst:
            data = data.replace(k,lst[k])
        fout.write(data)
        fout.close()
    
    def get_replace_list(self):
        return {
                u"@NAME@": self._name, 
                u"@EXE_NAME@": self._name.lower(), 
                u"@PATH_DWA@": self._install_path,
                u"@PATH_LOGOOS@": self._install_path + self._logo_path
            }
    
    def prepare_file_service(self, pth):
        lstrepl = self.get_replace_list()
        fdwagsvc=pth + utils.path_sep + u"dwagsvc"
        self.replace_key_file(fdwagsvc, lstrepl)
        utils.path_change_permissions(fdwagsvc,  stat.S_IRWXU + stat.S_IRGRP + stat.S_IROTH)
        fdwagent=pth + utils.path_sep + u"dwagent.service"
        if self._name.lower()!=u"dwagent":
            utils.path_rename(fdwagent,pth + utils.path_sep  + self._name.lower() + u".service")
            fdwagent=pth + utils.path_sep  + self._name.lower() + u".service"
        self.replace_key_file(fdwagent, lstrepl)
        utils.path_change_permissions(fdwagent,  stat.S_IRUSR + stat.S_IWUSR + stat.S_IRGRP + stat.S_IROTH)
    
    def prepare_file_sh(self, pth):
        lstrepl = self.get_replace_list()        
        appf=pth + utils.path_sep + u"dwagent"        
        if self._name.lower()!=u"dwagent":
            utils.path_rename(appf, pth + utils.path_sep + self._name.lower())
            appf=pth + utils.path_sep + self._name.lower()
        self.replace_key_file(appf, lstrepl)        
        utils.path_change_permissions(appf,  stat.S_IRWXU + stat.S_IRGRP +  stat.S_IXGRP + stat.S_IROTH + stat.S_IXOTH)
        
        appf=pth + utils.path_sep + u"configure"
        self.replace_key_file(appf, lstrepl)
        utils.path_change_permissions(appf,  stat.S_IRWXU + stat.S_IRGRP +  stat.S_IXGRP + stat.S_IROTH + stat.S_IXOTH)
        
        appf=pth + utils.path_sep + u"uninstall"
        self.replace_key_file(appf, lstrepl)
        utils.path_change_permissions(appf,  stat.S_IRWXU + stat.S_IRGRP +  stat.S_IXGRP + stat.S_IROTH + stat.S_IXOTH)
        
        #Menu
        fmenuconf=pth + utils.path_sep + u"dwagent.desktop"
        if utils.path_exists(fmenuconf):
            if self._name.lower()!=u"dwagent":
                utils.path_rename(fmenuconf, pth + utils.path_sep + self._name.lower() + u".desktop")
                fmenuconf=pth + utils.path_sep + self._name.lower() + u".desktop"        
            self.replace_key_file(fmenuconf, lstrepl)
            utils.path_change_permissions(fmenuconf,  stat.S_IRWXU + stat.S_IRGRP + stat.S_IRWXO)
        
    
    #LO USA ANCHE agent.py
    def prepare_file_monitor(self, pth):
        lstrepl = self.get_replace_list()
        appf=pth + utils.path_sep + u"systray"
        if utils.path_exists(appf):
            self.replace_key_file(appf, lstrepl)
            utils.path_change_permissions(appf,  stat.S_IRWXU + stat.S_IRGRP +  stat.S_IXGRP + stat.S_IROTH + stat.S_IXOTH)
        
        fmenusystray=pth + utils.path_sep + u"systray.desktop"
        if utils.path_exists(fmenusystray):
            self.replace_key_file(fmenusystray, lstrepl)
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
        pargs.append(u'agent.py')
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
        utils.path_symlink(sys.executable, ds + utils.path_sep + u"bin" + utils.path_sep + self._name.lower())
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
            utils.path_copy(self._install_path + utils.path_sep + u"native" + utils.path_sep + u"systray.desktop", pautos + utils.path_sep + self._name.lower() + u"_systray.desktop")
            utils.path_change_permissions(pautos + utils.path_sep + self._name.lower() + u"_systray.desktop",  stat.S_IRWXU + stat.S_IRGRP + stat.S_IRWXO)
            #SI DEVE LANCIARE CON L'UTENTE CONNESSO A X
            #Esegue il monitor
            #os.system(self._install_path + utils.path_sep + u"native" + utils.path_sep + u"dwaglnc systray &")
        except:
            None
        return True
    
    def remove_auto_run_monitor(self):
        try:
            fnm = u"/etc/xdg/autostart/" + self._name.lower() + u"_systray.desktop"
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
            f.write(utils.str_to_bytes(s,"utf8"))            
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
        self._current_path = None
        self._install_path = None
        self._svcnm = None
        #self._guilncnm = None
        self._systraynm = None
        self._logo_path=u"/ui/images/logo.icns"

    def set_name(self, k):
        self._name=k
        if self._name.lower()==u"dwagent":            
            self._svcnm = u"net.dwservice.agsvc"
            #self._guilncnm = u"net.dwservice.agguilnc"
            self._systraynm = u"net.dwservice.agsystray"
        else:
            self._svcnm = u"com.apiremoteaccess." + self._name.lower() + u"svc"
            #self._guilncnm = u"com.apiremoteaccess." + self._name.lower() + u"lnc"
            self._systraynm = u"com.apiremoteaccess." + self._name.lower() +  u"systray"
        
    def set_logo_path(self, pth):
        self._logo_path=pth
    
    def set_current_path(self, pth):
        self._current_path=pth

    def set_install_path(self, pth):
        self._install_path=pth
        
    def set_install_log(self, log):
        self._install_log=log
        
    def get_proposal_path(self):
        return u'/Library/' + self._name 
    
    def get_install_path(self) :        
        ldpth = u"/Library/LaunchDaemons/" + self._svcnm + u".plist"
        if utils.path_exists(ldpth) and utils.path_islink(ldpth):
            return utils.path_dirname(utils.path_dirname(utils.path_realname(ldpth)))
        
        if self._name.lower()==u"dwagent":
            #KEEP FOR COMPATIBILITY
            oldlncdmn_path = u"/Library/LaunchDaemons/net.dwservice.agent.plist"
            if utils.path_exists(oldlncdmn_path) and utils.path_islink(oldlncdmn_path):
                return utils.path_dirname(utils.path_dirname(utils.path_realname(oldlncdmn_path)))
            #KEEP FOR COMPATIBILITY                        
            oldlncdmn_path = u"/System/Library/LaunchDaemons/org.dwservice.agent.plist"
            if utils.path_exists(oldlncdmn_path) and utils.path_islink(oldlncdmn_path):
                return utils.path_dirname(utils.path_dirname(utils.path_realname(oldlncdmn_path)))        
        
        return None             
    
    def is_task_running(self, pid):
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True
    
    def check_init_run(self):
        return None
    
    def check_init_install(self, onlycheck=False):
        if os.geteuid() != 0: #MUST BE EUID
            if onlycheck:
                return messages.get_message("linuxRootPrivileges")
            else:
                f = utils.file_open(u"runasadmin.install", 'wb')
                f.close()
                raise SystemExit
        return None
    
    def check_init_uninstall(self):
        if os.geteuid() != 0: #MUST BE EUID
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
        #self._bootout_agent(self._guilncnm + u".plist")
        ret =utils.system_call(self._install_path + utils.path_sep + u"native" + utils.path_sep + u"dwagsvc stop", shell=True, stdout=self._install_log, stderr=subprocess.STDOUT)
        self._install_log.flush()
        return ret==0
    
    def start_service(self):
        ret = utils.system_call(self._install_path + utils.path_sep + u"native" + utils.path_sep + u"dwagsvc start", shell=True, stdout=self._install_log, stderr=subprocess.STDOUT)
        self._install_log.flush()
        bret = (ret==0)
        #if bret:
        #Avvia GUILauncher
        #    self._bootstrap_agent(self._guilncnm + u".plist")
        return bret
    
    def get_replace_list(self):
        return {
            u"@NAME@": self._name, 
            u"@EXE_NAME@": self._name.lower(), 
            u"@PATH_DWA@": self._install_path,
            u"@PATH_LOGOOS@": self._install_path + self._logo_path,
            u"@LDNAME_SERVICE@": self._svcnm ,
            #u"@LDNAME_GUILNC@": self._guilncnm ,
            u"@LDNAME_SYSTRAY@": self._systraynm 
        }
    
    def replace_key_file(self, path, enc,  lst):
        fin=utils.file_open(path, "r", enc)
        data = fin.read()
        fin.close()
        fout=utils.file_open(path,"w", enc)
        for k in lst:
            data = data.replace(k,lst[k])
        fout.write(data)
        fout.close()
            
    def prepare_file_service(self, pth):
        lstrepl = self.get_replace_list()
        #Service
        fapp=pth + utils.path_sep + "dwagsvc"
        self.replace_key_file(fapp, "utf-8", lstrepl)
        utils.path_change_permissions(fapp,  stat.S_IRWXU + stat.S_IRGRP + stat.S_IROTH)
        
        fapp=pth + utils.path_sep + "dwagsvc.plist"
        self.replace_key_file(fapp, "utf-8", lstrepl)
        utils.path_change_permissions(fapp,  stat.S_IRUSR + stat.S_IWUSR + stat.S_IRGRP + stat.S_IROTH)
        
        
        #GUI Launcher
        fapp=pth + utils.path_sep + "dwagguilnc"
        utils.path_change_permissions(fapp,  stat.S_IRWXU + stat.S_IRGRP + stat.S_IXGRP + stat.S_IROTH + stat.S_IXOTH)
        
        '''
        fapp=pth + utils.path_sep + "dwagguilnc.plist"
        self.replace_key_file(fapp, "utf-8", lstrepl)
        utils.path_change_permissions(fapp,  stat.S_IRUSR + stat.S_IWUSR + stat.S_IRGRP + stat.S_IROTH)
        '''
        
    
    def prepare_file_app(self, pth):
        utils.path_makedir(pth + u"/DWAgent.app/Contents/Resources")
        utils.path_copy(self._install_path + self._logo_path, pth + u"/DWAgent.app/Contents/Resources/Icon.icns")
        shutil.copytree(pth + u"/DWAgent.app",pth + u"/Configure.app")
        shutil.copytree(pth + u"/DWAgent.app",pth + u"/Uninstall.app")
        idname=u"net.dwservice."
        if self._name.lower()!=u"dwagent":
            shutil.move(pth + u"/DWAgent.app",pth + u"/" + self._name + u".app")            
            idname=u"com.apiremoteaccess."
        
        #DWAGENT        
        utils.path_change_permissions(pth + u"/" + self._name + u".app/Contents/MacOS/Run",  stat.S_IRUSR + stat.S_IWUSR + stat.S_IXUSR + stat.S_IRGRP + stat.S_IXGRP + stat.S_IROTH + stat.S_IXOTH)           
        lstrepl = self.get_replace_list()
        lstrepl["@MOD_DWA@"]=u"monitor"
        self.replace_key_file(pth + u"/" + self._name + u".app/Contents/MacOS/Run", "utf-8", lstrepl)
        lstrepl["@ID_NAME@"]=idname + lstrepl["@EXE_NAME@"] 
        self.replace_key_file(pth + u"/" + self._name + u".app/Contents/Info.plist", "utf-8", lstrepl)        
        
        #CONFIGURE
        utils.path_change_permissions(pth + u"/Configure.app/Contents/MacOS/Run",  stat.S_IRUSR + stat.S_IWUSR + stat.S_IXUSR + stat.S_IRGRP + stat.S_IXGRP + stat.S_IROTH + stat.S_IXOTH)
        lstrepl = self.get_replace_list()
        lstrepl["@MOD_DWA@"]=u"configure"
        self.replace_key_file(pth + u"/Configure.app/Contents/MacOS/Run", "utf-8", lstrepl)
        lstrepl["@NAME@"]=u"Configure"
        lstrepl["@EXE_NAME@"]=u"configure"        
        lstrepl["@ID_NAME@"]=idname + lstrepl["@EXE_NAME@"]
        self.replace_key_file(pth + u"/Configure.app/Contents/Info.plist", "utf-8", lstrepl)                
        
        #UNINSTALL        
        utils.path_change_permissions(pth + u"/Uninstall.app/Contents/MacOS/Run",  stat.S_IRUSR + stat.S_IWUSR + stat.S_IXUSR + stat.S_IRGRP + stat.S_IXGRP + stat.S_IROTH + stat.S_IXOTH)
        lstrepl = self.get_replace_list()
        lstrepl["@MOD_DWA@"]=u"uninstall"
        self.replace_key_file(pth + u"/Uninstall.app/Contents/MacOS/Run", "utf-8", lstrepl)
        lstrepl["@NAME@"]=u"Uninstall"
        lstrepl["@EXE_NAME@"]=u"uninstall"        
        lstrepl["@ID_NAME@"]=idname + lstrepl["@EXE_NAME@"]
        self.replace_key_file(pth + u"/Uninstall.app/Contents/Info.plist", "utf-8", lstrepl)                
        
    
    def prepare_file_monitor(self, pth):
        lstrepl = self.get_replace_list()
        
        fapp=pth + utils.path_sep + "dwagsystray"
        utils.path_change_permissions(fapp,  stat.S_IRWXU + stat.S_IRGRP + stat.S_IXGRP + stat.S_IROTH + stat.S_IXOTH)
        
        fapp=pth + utils.path_sep + "dwagsystray.plist"
        self.replace_key_file(fapp, "utf-8", lstrepl)
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
        pargs.append(u'agent.py')
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
        utils.path_symlink(sys.executable, ds + utils.path_sep + u"bin" + utils.path_sep + self._name.lower())
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
        ret = utils.system_call(self._install_path + utils.path_sep + u"native" + utils.path_sep + u"dwagsvc installAutoRun", shell=True, stdout=self._install_log, stderr=subprocess.STDOUT)
        self._install_log.flush()
        bret = (ret==0)
        if bret:
            #Avvia systray
            self._bootstrap_agent(self._systraynm + u".plist")
        return bret
        
    
    def remove_auto_run_monitor(self):
        #Chiude tutti systray
        self._bootout_agent(self._systraynm + u".plist")
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
                shutil.copytree(pathsrc + self._name + u".app", pathdst + self._name +u".app", symlinks=True)
            return True
        except:
            return False
        
        
    def remove_shortcuts(self) :
        try:
            pathsrc = u"/Applications/" + self._name + u".app"
            if utils.path_exists(pathsrc):
                utils.path_remove(pathsrc)
            return True
        except:
            return False


if gdi.is_windows():
    
    if utils.is_py2():
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
                    env = (utils.str_new("").join([
                        utils.str_new("%s=%s\0") % (k, v)
                        for k, v in env.items()])) + utils.str_new("\0")
                    '''
                    appenv=[]
                    for k, v in env.items():
                        k = utils.str_new(k)
                        n= ctypes.windll.kernel32.GetEnvironmentVariableW(k, None, 0)
                        if n>0:
                            buf= ctypes.create_unicode_buffer(u'\0'*n)
                            ctypes.windll.kernel32.GetEnvironmentVariableW(k, buf, n)
                            appenv.append(utils.str_new("%s=%s\0") % (k , buf.value))
                    appenv.append(utils.str_new("\0"))
                    env = utils.str_new("").join(appenv)
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
                        comspec = os.environ.get("COMSPEC", utils.str_new("cmd.exe"))
                        args = utils.str_new('{} /c "{}"').format (comspec, args)
                        if (_subprocess.GetVersion() >= 0x80000000 or
                                utils.path_basename(comspec).lower() == "command.com"):
                            w9xpopen = self._find_w9xpopen()
                            args = utils.str_new('"%s" %s') % (w9xpopen, args)
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
                    except subprocess.pywintypes.error as e:
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

    else:        
        
        from ctypes.wintypes import BYTE, WORD, LPWSTR, BOOL, DWORD, LPVOID, HANDLE
        
        NativeWindowsPopenUnicode=subprocess.Popen
                        
        dll_advapi32 = ctypes.WinDLL("advapi32")
        NativeWindowsRegCloseKey = dll_advapi32.RegCloseKey
        NativeWindowsRegCloseKey.restype = ctypes.c_long
        NativeWindowsRegCloseKey.argtypes = [ctypes.c_void_p]
        
        NativeWindowsRegOpenKeyEx = dll_advapi32.RegOpenKeyExW
        NativeWindowsRegOpenKeyEx.restype = ctypes.c_long
        NativeWindowsRegOpenKeyEx.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_ulong,
                                 ctypes.c_ulong, ctypes.POINTER(ctypes.c_void_p)]
        
        RegQueryValueEx = dll_advapi32.RegQueryValueExW
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
        self._logo_path=u"\\ui\\images\\logo.ico"
    
    def set_name(self, k):
        self._name=k
        self._runtime=k.lower() + u".exe"
    
    def set_logo_path(self, pth):
        self._logo_path=pth
    
    def set_current_path(self, pth):
        self._current_path=pth
    
    def set_install_path(self, pth):
        self._install_path=pth
        
    def set_install_log(self, log):
        None
        #self._install_log=log

    def get_proposal_path(self):
        return utils.str_new(os.environ["ProgramFiles"]) + utils.path_sep + self._name
    
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
                    f = utils.file_open(u"runasadmin.install", "w", encoding='utf-8')
                    f.close()
                    raise SystemExit
            else:
                f = utils.file_open(u"runasadmin.run", "w", encoding='utf-8')
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
                    f = utils.file_open(u"runasadmin.install", "w", encoding='utf-8')
                    f.close()
                    raise SystemExit
        else:
            if onlycheck:
                return messages.get_message("windowsAdminPrivileges")
            else:
                f = utils.file_open(u"runasadmin.install", "w", encoding='utf-8')
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
        arf.append(u''.join([u"iconPath=" ,  pth, self._logo_path + u"\r\n"]))
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
        arf.append(u''.join([u"iconPath=" ,  pth, self._logo_path + u"\r\n"]))
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
            lines = utils.bytes_to_str(appout[0],"utf8").splitlines()
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
        lines = utils.bytes_to_str(appout[0],"utf8").splitlines()
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
        self._ipc_client = None
        self._name = None
        self._listen_port = 7950
        self._runWithoutInstall = False
        self._runWithoutInstallProxySet = False;
        self._runWithoutInstallAgentAlive = True
        self._runWithoutInstallAgentCloseByClient=False
        self._runWithoutInstallAgentCloseEnd=True
        self._main_monitor=None
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
        elif self._ambient=="DEV":
            return _MAIN_URL_DEV
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
                f = utils.file_open("install.json","rb")
                s=f.read()
                appjs = json.loads(utils.bytes_to_str(s,"utf8"))
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
            self._name=utils.str_new(self._options["name"])
            self._native.set_name(self._name)
        else:
            self._native.set_name(u"DWAgent")
        
        self._current_path=utils.os_getcwd()
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
        applg = gdi._get_logo_from_conf(self._options,None)
        if applg != "":
            prmsui["logo"]=applg
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
                m=utils.str_new(self._options["welcometext"])
            else:            
                m=self._get_message('welcomeLicense') + "\n\n" 
                m+=self._get_message('welcomeSecurity') + "\n\n" 
                m+=self._get_message('welcomeSoftwareUpdates') + "\n\n\n"
                m+=self._get_message('welcomePrivacyTerms')
                                
                p1 = m.index("https://www.dwservice.net/")
                p2 = m.index(".html",p1)
                surl= m[p1:p2+5]
                chs.add_message_hyperlink(p1, len(surl), "https://www.dwservice.net/licenses-sources.html")
                
                mtc = self._get_message('termsAndConditions')                
                ptc = m.index("#TERMSANDCONDITIONS")                
                chs.add_message_hyperlink(ptc, len(mtc), "https://www.dwservice.net/terms-and-conditions.html")
                m=m.replace("#TERMSANDCONDITIONS", mtc)
                
                mpp = self._get_message('privacyPolicy')
                ppp = m.index("#PRIVACYPOLICY")                
                chs.add_message_hyperlink(ppp, len(mpp), "https://www.dwservice.net/gdpr.html")
                m=m.replace("#PRIVACYPOLICY", mpp)
                
                
                
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
                            self._install_log = utils.file_open(self._install_log_path, "w", encoding='utf-8')
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
        if pth.startswith("#DEV#"):
            self._ambient="DEV"
            pth=pth[5:]
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
        
        #TO REMOVE 03/11/2021 KEEP COMPATIBILITY WITH OLD LINUX INSTALLER
        try:
            if name=="agent.zip":
                if utils.path_exists(unzippath + "daemon.pyc"):
                    utils.path_remove(unzippath + "daemon.pyc")                    
        except:
            None
    
    def load_prop_json(self, fname):
        f = utils.file_open(fname, "rb")
        s=f.read()
        prp  = json.loads(utils.bytes_to_str(s,"utf8"))
        f.close()
        return prp        
    
    def store_prop_json(self, prp, fname):
        s = json.dumps(prp, sort_keys=True, indent=1)
        f = utils.file_open(fname, 'wb')
        f.write(utils.str_to_bytes(s,"utf8"))
        f.close()
    
    def obfuscate_password(self, pwd):
        return base64.b64encode(zlib.compress(pwd))

    def read_obfuscated_password(self, enpwd):
        return zlib.decompress(base64.b64decode(enpwd))
    
    def _copy_custom_images(self, prpconf, pth):
        ar = ["topimage", "logoxos", "logo16x16", "logo32x32", "logo48x48"]
        for nm in ar:
            if nm in prpconf and utils.path_exists(prpconf[nm]):
                dstpth = pth + utils.path_sep + "ui" + utils.path_sep + "images" + utils.path_sep + "custom"
                if not utils.path_exists(dstpth):
                    utils.path_makedirs(dstpth)
                utils.path_copy(self._options[nm], dstpth + utils.path_sep + self._options[nm])
    
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
        prpconf = communication.get_url_prop(self._get_main_url() + "getAgentFile.dw?name=config.xml", self._proxy)
        if "name" in self._options:
            prpconf["name"] = self._options["name"]
        if "topinfo" in self._options:
            prpconf["topinfo"]=self._options["topinfo"]
        if "topimage" in self._options and utils.path_exists(self._options["topimage"]):
            prpconf["topimage"]=self._options["topimage"]                        
        if "logoxos" in self._options and utils.path_exists(self._options["logoxos"]):
            prpconf["logoxos"]=self._options["logoxos"]
            self._native.set_logo_path(utils.path_sep + u"ui" + utils.path_sep + u"images" + utils.path_sep + u"custom" + utils.path_sep + prpconf["logoxos"])        
        if "logo16x16" in self._options and utils.path_exists(self._options["logo16x16"]):
            prpconf["logo16x16"]=self._options["logo16x16"]
        if "logo32x32" in self._options and utils.path_exists(self._options["logo32x32"]):
            prpconf["logo32x32"]=self._options["logo32x32"]
        if "logo48x48" in self._options and utils.path_exists(self._options["logo48x48"]):
            prpconf["logo48x48"]=self._options["logo48x48"]
        if "leftcolor" in self._options:
            prpconf["leftcolor"]=self._options["leftcolor"]                    
        if not self._runWithoutInstall:
            if "listenport" in self._options:
                prpconf['listen_port'] = self._options["listenport"]
            else:
                prpconf['listen_port'] = self._listen_port
        
        if self._runWithoutInstall:
            try:
                bmonok=False
                if self._uinterface.is_gui():
                    try:
                        try:
                            from ui import monitor
                        except: #FIX INSTALLER
                            import monitor
                        bmonok=True
                    except:
                        None
                if utils.path_exists(self._install_path.get() + utils.path_sep +  u'config.json'):				
                    appconf = self.load_prop_json(self._install_path.get() + utils.path_sep +  u'config.json')
                    if "preferred_run_user" in appconf:
                        prpconf["preferred_run_user"]=appconf["preferred_run_user"]
                    if bmonok:
                        if "unattended_access" in appconf:
                            prpconf["unattended_access"]=appconf["unattended_access"]
                        else:
                            prpconf["unattended_access"]=False
                    else:
                        prpconf["unattended_access"]=True
                else:
                    if bmonok:
                        prpconf["unattended_access"]=False
                    else:
                        prpconf["unattended_access"]=True
            except:
                None
        
        
        self._copy_custom_images(prpconf, pth)
        self.store_prop_json(prpconf, pth + utils.path_sep + u'config.json')
        
        if not (self._runWithoutInstall and utils.path_exists(pth + utils.path_sep + u"config.json") 
                and utils.path_exists(pth + utils.path_sep + u"fileversions.json") and utils.path_exists(pth + utils.path_sep + u"agent.py") 
                and utils.path_exists(pth + utils.path_sep + u"communication.py") and utils.path_exists(pth + utils.path_sep + u"ipc.py")):
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
            
            fls.append({'name':'agent.zip', 'unzippath':u''})
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
        ds=self._install_path.get() + utils.path_sep + "native"
        msg=self._get_message('copyFiles')
        self._copy_tree(_NATIVE_PATH,ds,msg,0.76, 0.8)
        
        #CREATE installer.ver
        dsver=ds + utils.path_sep + "installer.ver"
        if utils.path_exists(dsver):
            utils.path_remove(dsver)
        fver = utils.file_open(dsver,"wb")
        fver.write(utils.str_to_bytes(str(_INSTALLER_VERSION)))
        fver.close()
        
    
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
        chs = ui.Chooser()
        m=self._get_message('configureInstallAgent')
        chs.set_message(m)
        chs.set_key("chooseInstallMode")
        chs.set_param('firstConfig',curui.get_param('firstConfig',False))
        chs.add("installCode", self._get_message('configureInstallCode'))
        chs.add("installNewAgent", self._get_message('configureInstallNewAgent'))        
        chs.set_variable(ui.VarString("installCode"))
        chs.next_step(self.step_config)
        if "installputcode" in self._options and self._options["installputcode"]:
            return self.step_config(chs)
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
        if not ("installputcode" in self._options and self._options["installputcode"]):            
            ipt.prev_step(self.step_config_init)
        ipt.next_step(self.step_config_install_request)
        return ipt
    
    def send_req(self, req, prms=None):
        try:
            if self._ipc_client==None or self._ipc_client.is_close():
                self._ipc_client=listener.IPCClient(self._install_path.get())
            return self._ipc_client.send_request("admin", "", req, prms)
        except: 
            return 'ERROR:REQUEST_TIMEOUT'
    
    def close_req(self):
        if self._ipc_client!=None and not self._ipc_client.is_close():
            self._ipc_client.close()
    
    def _send_password_config(self):
        if "configPassword" in self._options:
            self.send_req("change_pwd",{'password': self._options["configPassword"]})
    
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
            if gdi.is_mac():
                time.sleep(10) #silent install on Mac 
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
                self._append_log(u"Error Configure: " + utils.exception_to_string(e))
                return ui.ErrorDialog(utils.exception_to_string(e))
        finally:
            if page is not None:
                page.close()
    
    def _append_log(self, txt):
        try:
            if not self._bmock:
                if self._install_log is not None:
                    self._install_log.write(utils.str_new(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())) + u" - " + txt + u"\n")
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
                lver = int(fver['agent.zip'])
                if lver<1484751796000:
                    self._append_log(u"Fixing old version...")
                    sys.path.insert(0,self._install_path.get())
                    objlib = importlib.import_module("agent")
                    try:
                        if utils.is_py2():
                            reload(objlib)                            
                        else:
                            importlib.reload(objlib)
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
        
        
        if not self._uinterface.is_gui() or self._bmock:
            self._uinterface.wait_message(u"".join(appwmsg), allowclose=True)
        else:
            try:
                try:
                    from ui import monitor
                except: #FIX INSTALLER
                    import monitor
                self._destroy_main_monitor()
                self._main_monitor = monitor.Main()
                self._main_monitor._set_config_base_path(self._install_path.get())
                pnl = self._main_monitor.prepare_runonfly_panel(self._uinterface._app, self._current_path, u"".join(appwmsg))                
                self._main_monitor.start("runonfly")
                self._uinterface.wait_panel(pnl,self._destroy_main_monitor, allowclose=True)
            except Exception as e:
                print(u"Error: " + utils.exception_to_string(e) + u"\n" + utils.get_stacktrace_string())
                self._append_log(u"Error: " + utils.exception_to_string(e) + u"\n" + utils.get_stacktrace_string())
                self._uinterface.wait_message(u"".join(appwmsg), allowclose=True)
    
    def _destroy_main_monitor(self):
        if self._main_monitor is not None:
            self._main_monitor.stop()
            self._main_monitor=None        
    
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
        pstipc=None
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
                f.write(utils.str_to_bytes(str(os.getpid())))
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
                pstipc = ipc.Property()
                pstipc.open("runonfly")
                agpid=int(pstipc.get_property("pid"))
                curst=""
                while self._native.is_task_running(agpid) and (ponfly is None or ponfly.poll() is None):
                    st = pstipc.get_property("status")
                    if st!=curst:
                        curst=st
                        if st=="CONNECTED":
                            if "runputcode" in self._options and self._options["runputcode"]:
                                runcode_connected=True
                                self._step_runonfly_conn_msg(None,None)
                            else:            
                                usr=pstipc.get_property("user")
                                usr=usr[0:3] + u"-" + usr[3:6] + u"-" + usr[6:9] + u"-" + usr[9:]
                                self._step_runonfly_conn_msg(usr, pstipc.get_property("password"))                            
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
                
                pstipc.close()
                pstipc=None
                time.sleep(1)
                
        except Exception as e:
            f = utils.file_open(u"dwagent.stop", 'wb')
            f.close()
            try:
                if pstipc is not None:
                    pstipc.close()
                    pstipc=None
            except:
                None
            utils.system_changedir(self._current_path)
            self._runWithoutInstallAgentCloseEnd=True
            #Se non è partito l'agente potrebbe dipendere da un problema di file corrotti
            self._append_log(u"Error: " + utils.exception_to_string(e) + u"\n" + utils.get_stacktrace_string())
            return ui.Message(self._get_message("runWithoutInstallationUnexpectedError").format(utils.path_absname(self._install_path.get())) + "\n\n" + utils.exception_to_string(e))
            
        
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
        if utils.path_exists(self._current_path + utils.path_sep + "ambient.dev"):
            self._ambient="DEV"
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
        
        if self._silent: 
            #SETUP PROXY
            if "proxyType" in self._options:
                self._proxy=communication.ProxyInfo()
                self._proxy.set_type(self._options["proxyType"])
            if self._proxy is not None and "proxyHost" in self._options:
                self._proxy.set_host(self._options["proxyHost"])
            if self._proxy is not None and "proxyPort" in self._options:
                self._proxy.set_port(int(self._options["proxyPort"]))
            if self._proxy is not None and "proxyUser" in self._options:
                self._proxy.set_user(self._options["proxyUser"])
            if self._proxy is not None and "proxyPassword" in self._options:
                self._proxy.set_password(self._options["proxyPassword"])
        
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
            
        
        self._install_path.set(utils.str_new(pth))
        #Imposta path per native
        self._native.set_install_path(utils.str_new(pth))
        self._native.set_install_log(self._install_log)
            
            
        try:
            #Verifica permessi di amministratore (SOLO se silent altrimenti gia' lo ha fatto precedentemente
            if self._silent: 
                msg = self._native.check_init_install(True)
                if msg is not None:
                    raise Exception(msg)
                if self._proxy is None:
                    self._append_log(u"Proxy NONE.")
                else:
                    self._append_log(u"Proxy " + self._proxy.get_type() + u" " + self._proxy.get_host() + u":" + str(self._proxy.get_port()) + u".")
        
            
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
                    self._append_log(u"Error Download files: " + utils.exception_to_string(e) + u"\n" + utils.get_stacktrace_string())
                    chs = ui.Chooser()
                    chs.set_key("retryDownload")
                    chs.set_message(utils.exception_to_string(e) + u"\n\n" + self._get_message('errorConnectionQuestion'))
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
                    raise Exception(u"Error Download files: " + utils.exception_to_string(e) + u"\n" + utils.get_stacktrace_string())
            
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
                    if self._proxy is not None:
                        self._send_proxy_config()
                    self._send_password_config()
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
            self._append_log(u"Error Install: " + utils.exception_to_string(e))
            return ui.ErrorDialog(utils.exception_to_string(e)) 
            

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
            f = utils.file_open("config.json", "rb")
            s=f.read()
            confjson = json.loads(utils.bytes_to_str(s,"utf8"))
            f.close()
        except Exception:
            None
        prmsui={}
        if "name" in confjson:
            self._name=utils.str_new(confjson["name"])
            self._native.set_name(self._name)
        else:
            self._native.set_name(u"DWAgent")
        prmsui["title"]=self._get_message('titleUninstall')
        if "topinfo" in confjson:
            prmsui["topinfo"]=confjson["topinfo"]
        if "topimage" in confjson:
            prmsui["topimage"]=u"ui" + utils.path_sep + u"images" + utils.path_sep + u"custom" + utils.path_sep + confjson["topimage"]
        applg = gdi._get_logo_from_conf(confjson, u"ui" + utils.path_sep + u"images" + utils.path_sep + u"custom" + utils.path_sep)
        if applg != "":
            prmsui["logo"]=applg
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
                self._install_path = utils.str_new(self._install_path)
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
                self._install_log.write(utils.str_new(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())) + u" - " + txt + u"\n")
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
            self._append_log(u"Error Uninstall: " + utils.exception_to_string(e))
            return ui.ErrorDialog(utils.exception_to_string(e))
            

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
        elif arg.lower().startswith("proxytype="):            
            arotps["proxyType"]=arg[10:]
        elif arg.lower().startswith("proxyhost="):            
            arotps["proxyHost"]=arg[10:]
        elif arg.lower().startswith("proxyport="):            
            arotps["proxyPort"]=arg[10:]
        elif arg.lower().startswith("proxyuser="):            
            arotps["proxyUser"]=arg[10:]
        elif arg.lower().startswith("proxypassword="):            
            arotps["proxyPassword"]=arg[14:]
        elif arg.lower().startswith("configpassword="):
            arotps["configPassword"]=arg[15:]
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
    
    