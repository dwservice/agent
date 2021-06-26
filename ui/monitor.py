# -*- coding: utf-8 -*-

'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''

import messages
import utils
import json
import sys
import subprocess
import threading
import listener
import gdi
import time
import images
import os

_WIDTH=550
_HEIGHT=300

_WIDTH_RIGHT=140
_CONTENT_WIDTH=_WIDTH-_WIDTH_RIGHT
_HEIGHT_STATUS_BAR=28
_HEIGHT_STATUS=60

MENU_SHOW = 1
MENU_HIDE = 2
MENU_ENABLE = 11
MENU_DISABLE = 12
MENU_CONFIGURE = 21

COLOR_NOSERVICE="949494"
COLOR_ONLINE="259126"
COLOR_OFFLINE="949494"
COLOR_UPDATING="bfba34"
COLOR_DISABLE="c21b1a"

TIMEOUT_REQ=5

def is_windows():
    return utils.is_windows()

def is_linux():
    return utils.is_linux()

def is_mac():
    return utils.is_mac()

def get_user_dir():
    try:
        import ctypes
        buf = ctypes.create_unicode_buffer(1024)
        ctypes.windll.shell32.SHGetFolderPathW(None, 40, None, 0, buf) #40 = CSIDL_PROFILE
        return buf.value
    except:
        return utils.path_expanduser("~")


class NotifyActivitiesHideEffect():
    def __init__(self, dlg):
        self._dlg = dlg
        self._cancel=False
        self._first=True
    
    def run(self):
        if self._cancel:
            return            
        if self._first:
            self._first=False
            gdi.add_scheduler(4, self.run)
        else:
            cx = self._dlg.get_x()+2
            self._dlg.set_position(cx,self._dlg.get_y())
            ar = gdi.get_screen_size()
            if cx>=ar["width"]:
                self._dlg.hide()
            else:            
                gdi.add_scheduler(0.05, self.run)

    def cancel(self):
        self._cancel=True

class NotifyActivities():
    def __init__(self, prt):
        self._parent=prt        
        self._list=[u"screencapture",u"shell",u"transfers"]
        self._sessions=False
        self._cmps={}
        self._visible_cmps={}
        self._screen_w=0
        self._screen_h=0
        self._dlg_y_gap=180                
        self._dlg_w=21
        self._move_y=None
        self._skip_click=False
        self._hide_effect=None
        self._dlg = gdi.Window(gdi.WINDOW_TYPE_POPUP)
        self._dlg.set_background("ffaa33")
        self._pnl = gdi.Panel()
        self._pnl.set_position(1, 1)      
        self._pnl.set_size(self._dlg_w, 20)  
        self._pnl.set_background("313536")
        self._dlg.add_component(self._pnl)        
        implogo = gdi.ImagePanel()
        implogo.set_position(2, 2)
        implogo.set_filename(images.get_image(u"logo16x16.bmp"))
        self._pnl.add_component(implogo)        
        
        for k in self._list:
            self._cmps[k] = gdi.ImagePanel()        
            self._cmps[k].set_filename(images.get_image(u"activities_" + k + u".bmp"))            
            self._dlg.add_component(self._cmps[k])
            self._visible_cmps[k]=False
            self._cmps[k].set_visible(False)
        
        self._sessions_last_update=self._sessions
        self._visible_cmps_last_update=self._visible_cmps.copy()
        self._dlg.set_action(self.on_action)
                
            
    def set_sessions(self, b):
        self._sessions=b
        
    def set_visible(self, k, b):        
        self._visible_cmps[k]=b
    
    def _move_y_timer(self):
        if self._move_y is not None:
            mp = gdi.get_mouse_position()
            ar = gdi.get_screen_size()
            if mp["x"]<=ar["width"]-self._dlg.get_width():
                self._move_y=None
            else:
                ny=mp["y"]-self._move_y            
                if ny>=0 and ny<=ar["height"]-120 and self._dlg.get_y()!=ny:
                    self._dlg.set_position(self._dlg.get_x(),ny)
                    self._dlg_y_gap=ar["height"]-ny
                self._skip_click=True
                gdi.add_scheduler(0.1, self._move_y_timer)
    
    def on_action(self,e):
        if e["action"]=="MOUSEBUTTONDOWN":            
            if e["button"]==1:
                self._move_y=e["y"]
                gdi.add_scheduler(0.1, self._move_y_timer)
        if e["action"]=="MOUSEBUTTONUP":
            self._move_y=None
        if e["action"]=="MOUSECLICK":
            if not self._skip_click:
                self._parent._app.show()
                self._parent._app.to_front()
            self._skip_click=False
    
    def update(self):
        bok=False
        if self._sessions_last_update != self._sessions:
            bok=True
        else:
            for k in self._list:
                if self._visible_cmps_last_update[k] != self._visible_cmps[k]:
                    bok=True
        ar = gdi.get_screen_size()
        if self._screen_w!=ar["width"] or self._screen_h!=ar["height"]:
            self._screen_w=ar["width"]
            self._screen_h=ar["height"]
            bok=True 
        if bok:
            if self._hide_effect is not None:
                self._hide_effect.cancel()
            if self._sessions:
                self._dlg_h=22
                for k in self._list:
                    if self._visible_cmps[k]:
                        self._cmps[k].set_position(3, self._dlg_h)
                        self._cmps[k].set_visible(True)
                        self._dlg_h+=18
                    else:
                        self._cmps[k].set_visible(False)
                self._dlg.set_position(self._screen_w-self._dlg_w,self._screen_h-self._dlg_y_gap)
                self._dlg.set_size(self._dlg_w, self._dlg_h)
                self._dlg.show()                
                if self._parent._monitor_desktop_notification=="autohide":                    
                    self._hide_effect = NotifyActivitiesHideEffect(self._dlg)
                    self._hide_effect.run()                                    
            else:
                self._dlg.hide()
                for k in self._list:
                    self._visible_cmps[k]=False
                    self._cmps[k].set_visible(False)
            self._sessions_last_update=self._sessions
            self._visible_cmps_last_update=self._visible_cmps.copy()
    
    def destroy(self):
        try:
            if self._dlg is not None:
                self._dlg.destroy()
        except:
            None
       
class Main():
    
    def __init__(self):
        self._name=u"DWAgent"
        self._logo=None
        self._properties={}
        self._config_base_path=None
        self._notifyActivities=None
        try:
            f = utils.file_open('config.json')
            self._properties = json.loads(f.read())
            f.close()
        except Exception:
            None
        if 'name' in self._properties:
            self._name=unicode(self._properties["name"])
        applg = gdi._get_logo_from_conf(self._properties, u"ui" + utils.path_sep + u"images" + utils.path_sep + u"custom" + utils.path_sep)
        if applg != "":
            self._logo=applg        
    
    def _get_message(self, key):
        smsg = messages.get_message(key)
        if not self._name==u"DWAgent":
            return smsg.replace(u"DWAgent",self._name)
        else:
            return smsg
    
    @staticmethod
    def get_instance():
        return Main._instance_monitor
    
    @staticmethod
    def set_instance(i):
        Main._instance_monitor=i
    
    def _set_config_base_path(self, pth):
        self._config_base_path=pth
        f = utils.file_open(self._config_base_path + os.sep + 'config.json')                
        self._properties = json.loads(f.read())
        f.close()
    
    def lock(self):
        self._homedir = get_user_dir() + utils.path_sep + u"." + self._name.lower()
        if not utils.path_exists(self._homedir):
            utils.path_makedirs(self._homedir)
        self._lockfilename = self._homedir + utils.path_sep + "monitor.lock"
        try:
            if is_linux() or is_mac():
                import fcntl
                self._lockfile = utils.file_open(self._lockfilename , "w")
                fcntl.lockf(self._lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
            else:
                if utils.path_exists(self._lockfilename ):
                    utils.path_remove(self._lockfilename ) 
                self._lockfile = utils.file_open(self._lockfilename , "w")
                self._lockfile.write("\x00")
        except:
            try:
                self._lockfile.close()
            except:
                None
            if self._mode=="systray":
                print ("An Instance is already running.")
            else:
                self.add_show_file()
            return False
        
        #self.remove_show_file()
        return True

    def unlock(self):
        self._lockfile.close()  
        try:
            utils.path_remove(self._lockfilename ) 
        except:
            None
        #self.remove_show_file()
        
    def check_stop(self):
        stopfilename = "monitor.stop"
        return utils.path_exists(stopfilename)
    
    def check_update(self):
        stopfilename = "monitor.update"
        return utils.path_exists(stopfilename)
    
    def add_show_file(self):
        showfilename  = self._homedir + utils.path_sep + "monitor.show"
        if not utils.path_exists(showfilename):
            f = utils.file_open(showfilename, "w")
            f.write("\x00")
            f.close()
        
    def remove_show_file(self):
        showfilename  = self._homedir + utils.path_sep + "monitor.show"        
        try:
            utils.path_remove(showfilename)
        except:
            None
    
    def check_show(self):
        showfilename = self._homedir + utils.path_sep + "monitor.show"
        return utils.path_exists(showfilename)
    
    def get_ico_file(self, name):
        return images.get_image(name + ".bmp")
    
    def get_activities(self, csts):
        ar = {}
        ar["sessions"]=len(csts)
        ar["screenCapture"]=0
        ar["shellSession"]=0
        ar["downloads"]=0
        ar["uploads"]=0
        for itm in csts:
            actvs = itm["activities"]
            if actvs["screenCapture"]>0:
                ar["screenCapture"]+=actvs["screenCapture"]
            if actvs["shellSession"]>0:
                ar["shellSession"]+=actvs["shellSession"]
            if actvs["downloads"] > 0:
                ar["downloads"]+=actvs["downloads"]
            if actvs["uploads"] > 0:
                ar["uploads"]+=actvs["uploads"]            
        return ar
    
    def get_info(self):
        ret={"state": "-1","sessions_status":[]}
        self._semaphore.acquire()
        try:
            if self._sharedmemclient==None or self._sharedmemclient.is_close():                
                self._sharedmemclient=listener.SharedMemClient(path=self._config_base_path)
                self._status_cnt=-1

            cnt=long(self._sharedmemclient.get_property("counter"))
            if self._status_cnt!=cnt:
                if self._status_cnt==-1: #SKIP FIRST READ
                    self._status_cnt=cnt
                    return ret;
                else:
                    self._status_cnt=cnt                
                    ret["state"] = self._sharedmemclient.get_property("state")
                    try:
                        ret["group"] = self._sharedmemclient.get_property("group").decode("unicode-escape")
                    except:
                        None
                    try:
                        ret["name"] = self._sharedmemclient.get_property("name").decode("unicode-escape")
                    except:
                        None
                    try:
                        if ret["state"]=='1':
                            csts = json.loads(self._sharedmemclient.get_property("sessions_status"))
                        else:
                            csts = []
                        ret["sessions_status"] = csts
                        if self._monitor_desktop_notification!="none":                            
                            if self._notifyActivities is None:
                                self._notifyActivities=NotifyActivities(self)                            
                            appar = self.get_activities(csts)
                            self._notifyActivities.set_sessions(appar["sessions"])
                            self._notifyActivities.set_visible("screencapture", appar["screenCapture"]>0)
                            self._notifyActivities.set_visible("shell", appar["shellSession"]>0)
                            self._notifyActivities.set_visible("transfers", (appar["downloads"]+appar["uploads"])>0)
                            self._notifyActivities.update()                            
                    except:
                        None
                    return ret;
            else:
                if self._monitor_desktop_notification!="none":
                    if self._notifyActivities is not None:                        
                        self._notifyActivities.set_sessions(False)
                        self._notifyActivities.update()
                        
                return ret
        except Exception as e:
            print str(e)
            return ret
        finally:
            self._semaphore.release()
            
    def check_events(self):
        if self.check_stop():
            if self._notifyActivities is not None:
                self._notifyActivities.destroy()
            if self._monitor_tray_icon:
                self._monitor_tray_obj.destroy()
            self._app.destroy()
            return
        if self.check_update():
            self._update=True
            if self._notifyActivities is not None:
                self._notifyActivities.destroy()
            if self._monitor_tray_icon:
                self._monitor_tray_obj.destroy()
            self._app.destroy()
            return
        if self.check_show():
            self._app.show()
            self._app.to_front()
            self.remove_show_file()
        gdi.add_scheduler(0.5, self.check_events)
    
    def update_status(self):
        bground=""
        self.msgst=""
        self.icofile=""
        stateBtnEnDis=True
        msgBtnEnDis="monitorDisable"
        appar = self.get_info()
        s=appar["state"]
        newst=""
        if s=='0': #STATUS_OFFLINE 
            newst="OFFLINE"
            self.msgst=self._get_message('monitorStatusOffline')
            bground=COLOR_OFFLINE
            self.icofile="monitor_grey"
        elif s=='1': #STATUS_ONLINE 
            newst="ONLINE"
            self.msgst=self._get_message('monitorStatusOnline')
            bground=COLOR_ONLINE
            self.icofile="monitor_green"
        elif s=='3': #STATUS_DISABLE 
            newst="DISABLE"
            self.msgst=self._get_message('monitorStatusDisabled')
            bground=COLOR_DISABLE
            msgBtnEnDis="monitorEnable"
            self.icofile="monitor_red"
        elif s=='10': #STATUS_UPDATING 
            newst="UPDATING"
            self.msgst=self._get_message('monitorStatusUpdating')
            bground=COLOR_UPDATING
            self.icofile="monitor_yellow"
        else:
            newst="NOSERVICE"
            stateBtnEnDis=False
            self.msgst=self._get_message('monitorStatusNoService')
            bground=COLOR_NOSERVICE
            self.icofile="monitor_warning"
        
        curact = self.get_activities(appar["sessions_status"])
        bchgact=False
        if self._cur_activities is None:
            bchgact=True
        else:
            for k in curact:
                if curact[k]!=self._cur_activities[k]:
                    bchgact=True
                    break;
        if newst != self._cur_status or bchgact is True:
            self._cur_status=newst 
            self._cur_activities=curact
            self._reload_activities=False
            self.update_systray(self.icofile, self.msgst)
            self._img_status_top.set_background_gradient(bground,"ffffff",gdi.GRADIENT_DIRECTION_TOPBOTTOM)
            self._img_status_bottom.set_background_gradient(bground,"ffffff",gdi.GRADIENT_DIRECTION_BOTTONTOP)
            apptx=[]
            bexline=False
            if "group" in appar and appar["group"]!="":
                apptx.append(appar["group"])
                apptx.append(u"\n")
                bexline=True
            if "name" in appar and appar["name"]!="":
                apptx.append(appar["name"])
                apptx.append(u"\n")
                bexline=True            
            if bexline is True:
                apptx.append(u"\n")
            apptx.append(self.msgst)
            self._lbl_status.set_text(u"".join(apptx))
                        
            
            if curact["sessions"]==0:
                self._lbl_notificationsn.set_visible(True)
                self._lbl_notificationsl.set_text("")
                self._lbl_notificationsr.set_text("")
            else:
                apptxl=""
                apptxr=""
                apptxl+=self._get_message('monitorSession') + ":"
                apptxr+=self._get_message('monitorActive') + " (" + str(curact["sessions"]) + ")"
                                
                if curact["screenCapture"]>0:
                    apptxl+="\n" + self._get_message('monitorScreenCapture') + ":"
                    apptxr+="\n" + self._get_message('monitorActive') + " (" + str(curact["screenCapture"]) + ")"
                
                if curact["shellSession"]>0:
                    apptxl+="\n" + self._get_message('monitorShellSession') + ":"
                    apptxr+="\n" + self._get_message('monitorActive') + " (" + str(curact["shellSession"]) + ")"
                
                if curact["downloads"]>0:
                    apptxl+="\n" + self._get_message('monitorDownload') + ":"
                    apptxr+="\n" + self._get_message('monitorActive') + " (" + str(curact["downloads"]) + ")"
                
                if curact["uploads"]>0:
                    apptxl+="\n" + self._get_message('monitorUpload') + ":"
                    apptxr+="\n" + self._get_message('monitorActive') + " (" + str(curact["uploads"]) + ")"
                
                self._lbl_notificationsn.set_visible(False)
                self._lbl_notificationsl.set_text(apptxl)
                self._lbl_notificationsr.set_text(apptxr)
            
            self._btconfig.set_enable(stateBtnEnDis)
            self._btends.set_text(self._get_message(msgBtnEnDis))
            self._btends.set_enable(stateBtnEnDis)
        
        gdi.add_scheduler(2, self.update_status)
    
    def send_req(self, usr, pwd, req, prms=None):
        self._semaphore.acquire()
        try:
            if self._sharedmemclient==None or self._sharedmemclient.is_close():
                self._sharedmemclient=listener.SharedMemClient()
            return self._sharedmemclient.send_request(usr, pwd, req, prms);
        except: 
            return 'ERROR:REQUEST_TIMEOUT'
        finally:
            self._semaphore.release()
            
    def set_config(self, pwd,  key, val):
        sret=self.send_req("admin", pwd, 'set_config',  {'key':key, 'value':val})
        if sret!="OK":
            raise Exception(sret[6:])

    
    def check_auth(self, pwd):
        sret=self.send_req("admin", pwd, "check_auth", None)
        if sret=="OK":
            return True
        elif sret=="ERROR:FORBIDDEN":
            return False
        else:
            raise Exception(sret[6:])
    
    def _enable_disable_action_pwd(self,e):
        if e["action"]=="PERFORMED":
            pwd = ""
            for c in e["window"].get_components():
                if c.get_name()=="txtPassword":
                    pwd=c.get_text()
            
            e["window"].destroy()        
            val = "false"
            mess_ok='monitorAgentDisabled'
            if self._cur_status=="DISABLE":
                val="true"
                mess_ok='monitorAgentEnabled'
            if self.check_auth(pwd):
                self.set_config(pwd, "enabled", val)
                dlg = gdi.DialogMessage(gdi.DIALOGMESSAGE_ACTIONS_OK,gdi.DIALOGMESSAGE_LEVEL_INFO,self._app)
                dlg.set_title(self._get_message('monitorTitle'))
                dlg.set_message(self._get_message(mess_ok))
                dlg.show();
            else:
                dlg = gdi.DialogMessage(gdi.DIALOGMESSAGE_ACTIONS_OK,gdi.DIALOGMESSAGE_LEVEL_ERROR,self._app)
                dlg.set_title(self._get_message('monitorTitle'))
                dlg.set_message(self._get_message('monitorInvalidPassword'))
                dlg.show();            
    
    def _enable_disable_action(self,e):
        if e["action"]=="DIALOG_YES":
            try:
                val = "false"
                mess_ok='monitorAgentDisabled'
                if self._cur_status=="DISABLE":
                    val="true"
                    mess_ok='monitorAgentEnabled'
                pwd = ""
                if self.check_auth(pwd):
                    self.set_config(pwd, "enabled", val)
                    dlg = gdi.DialogMessage(gdi.DIALOGMESSAGE_ACTIONS_OK,gdi.DIALOGMESSAGE_LEVEL_INFO,self._app)
                    dlg.set_title(self._get_message('monitorTitle'))
                    dlg.set_message(self._get_message(mess_ok))
                    dlg.show();
                else:
                    #RICHIEDE PASSWORD
                    dlg = gdi.Window(gdi.WINDOW_TYPE_DIALOG, self._app)
                    dlg.set_title(self._get_message('monitorTitle'))
                    dlg.set_size(220, 140)
                    dlg.set_show_position(gdi.WINDOW_POSITION_CENTER_SCREEN)
                    lbl = gdi.Label()
                    lbl.set_text(self._get_message('monitorEnterPassword'))
                    lbl.set_position(10, 10)
                    lbl.set_width(200)
                    dlg.add_component(lbl)
                    txt = gdi.TextBox()
                    txt.set_name("txtPassword");
                    txt.set_password_mask(True)
                    txt.set_position(10, 10+lbl.get_height())
                    txt.set_width(200)
                    dlg.add_component(txt)
                    pnlBottomH=55
                    pnl = gdi.Panel();
                    pnl.set_position(0, dlg.get_height()-pnlBottomH)
                    pnl.set_size(dlg.get_width(),pnlBottomH)
                    dlg.add_component(pnl)
                    bt = gdi.Button();
                    bt.set_position(int((dlg.get_width()/2)-(bt.get_width()/2)), 10)
                    bt.set_text(self._get_message('ok'))
                    bt.set_action(self._enable_disable_action_pwd)
                    pnl.add_component(bt)
                    dlg.show()
            except Exception as e:
                dlg = gdi.DialogMessage(gdi.DIALOGMESSAGE_ACTIONS_OK,gdi.DIALOGMESSAGE_LEVEL_ERROR,self._app)
                dlg.set_title(self._get_message('monitorTitle'))
                dlg.set_message(str(e))
                dlg.show();
    
    def enable_disable(self, e):
        if e["action"]=="PERFORMED":
            msg=self._get_message('monitorDisableAgentQuestion')
            if self._cur_status=="DISABLE":
                msg=self._get_message('monitorEnableAgentQuestion')
            
            dlg = gdi.DialogMessage(gdi.DIALOGMESSAGE_ACTIONS_YESNO,gdi.DIALOGMESSAGE_LEVEL_INFO,self._app)
            dlg.set_title(self._get_message('monitorTitle'))
            dlg.set_message(msg)
            dlg.set_action(self._enable_disable_action)
            dlg.show();
    
    def configure(self, e):
        if e["action"]=="PERFORMED":
            if is_windows():
                subprocess.call(["native" + utils.path_sep + "dwaglnc.exe" , "configure"]) 
            elif is_linux():
                self._runproc(["native" + utils.path_sep + "configure"])
            elif is_mac():
                #KEEP FOR COMPATIBILITY
                if utils.path_exists("native/Configure.app/Contents/MacOS/Configure"):
                    self._runproc(["native/Configure.app/Contents/MacOS/Configure"])
                else:
                    self._runproc(["native/Configure.app/Contents/MacOS/Run"])
            
            
    def run_update(self):
        #Lancia se stesso perche con il file monitor.update attende che le librerie si aggiornano
        if is_windows():
            subprocess.call(["native" + utils.path_sep + "dwaglnc.exe" , "systray"]) 
        elif is_linux():
            self._runproc(["native" + utils.path_sep + self._name.lower(),"systray","&"])
        elif is_mac():
            None            
    
    def unistall(self, e):
        if e["action"]=="PERFORMED":
            if is_windows():
                subprocess.call(["native" + utils.path_sep + "dwaglnc.exe" , "uninstall"]) 
            elif is_linux():
                sucmd=None
                if self._which("gksu"):
                    sucmd="gksu"
                elif self._which("kdesu"):
                    sucmd="kdesu"
                if sucmd is not None:
                    osenv = os.environ
                    libenv = {}
                    for k in osenv:
                        if k!="LD_LIBRARY_PATH":
                            libenv[k]=osenv[k]
                    subprocess.Popen([sucmd , utils.path_absname("native" + utils.path_sep + "uninstall")],env=libenv)
                else:
                    dlg = gdi.DialogMessage(gdi.DIALOGMESSAGE_ACTIONS_OK,gdi.DIALOGMESSAGE_LEVEL_ERROR,self._app)
                    dlg.set_title(self._get_message('monitorTitle'))
                    dlg.set_message(self._get_message('monitorUninstallNotRun'))
                    dlg.show();
            elif is_mac():
                self._runproc(["open", "-a", os.path.abspath("native/Uninstall.app")])
                  
    
    def _runproc(self, ar, ev=None):
        if ev is None:
            p = subprocess.Popen(ar)
        else:
            p = subprocess.Popen(ar,env=ev)
        p.communicate()
        p.wait()
    
    def _which(self, name):
        p = subprocess.Popen("which " + name, stdout=subprocess.PIPE, shell=True)
        (po, pe) = p.communicate()
        p.wait()
        return len(po) > 0     
    
    def printInfo(self):
        msgst=u""
        appar = self.get_info()
        s=appar["state"]
        if s=='0': #STATUS_OFFLINE 
            msgst=self._get_message('monitorStatusOffline')
        elif s=='1': #STATUS_ONLINE 
            msgst=self._get_message('monitorStatusOnline')
        elif s=='3': #STATUS_DISABLE 
            msgst=self._get_message('monitorStatusDisabled')
        elif s=='10': #STATUS_UPDATING 
            msgst=self._get_message('monitorStatusUpdating')
        else:
            msgst=self._get_message('monitorStatusNoService')
        print(self._get_message('monitorStatus') + u": " + msgst) 
        print(self._get_message('monitorSession') + u" : " + self._get_message('monitorActive') + u" (" + str(appar["sessions"]) + u")")
        if appar["screenCapture"]>0:
            print(self._get_message('monitorScreenCapture')+ u": " + self._get_message('monitorActive') + u" (" + str(appar["screenCapture"]) + u")")            
        
        if appar["shellSession"]>0:
            print(self._get_message('monitorShellSession')+ u": " + self._get_message('monitorActive') + u" (" + str(appar["shellSession"]) + u")")
                    
        if appar["downloads"]>0:
            print(self._get_message('monitorDownload')+ u": " + self._get_message('monitorActive') + u" (" + str(appar["downloads"]) + u")")
                    
        if appar["uploads"]>0:
            print(self._get_message('monitorUpload')+ u": " + self._get_message('monitorActive') + u" (" + str(appar["uploads"]) + u")")
            
            
    
    def _actions_systray(self,e):
        if e["action"]=="PERFORMED":
            if e["name"]=="show":
                self._app.show()
                self._app.to_front()
            elif e["name"]=="hide":
                self._app.hide()
            elif e["name"]=="enable":
                self.enable_disable(e)
            elif e["name"]=="disable":
                self.enable_disable(e)
            elif e["name"]=="configure":
                self.configure(e)
    
    def _window_action(self,e):
        if e["action"]==u"ONCLOSE":
            if self._monitor_tray_icon:
                e["source"].hide()
                e["cancel"]=True        
            elif self._notifyActivities is not None:
                self._notifyActivities.destroy()
            
    
    def notify_action(self, e):
        if e["action"]==u"ACTIVATE":
            e["source"].get_object("window").show()
            e["source"].get_object("window").to_front()
        elif e["action"]==u"CONTEXTMENU":
            pp=gdi.PopupMenu()
            if not e["source"].get_object("window").is_show():
                pp.add_item("show",self._get_message('monitorShow'))
            else:
                pp.add_item("hide",self._get_message('monitorHide'))
            
            if self._cur_status!="NOSERVICE":
                if self._cur_status=="DISABLE":
                    pp.add_item("enable",self._get_message('monitorEnable'))
                else:
                    pp.add_item("disable",self._get_message('monitorDisable'))
                pp.add_item("configure",self._get_message('monitorConfigure'))
            pp.set_action(self._actions_systray);
            pp.show()
    
    def update_systray(self,icon,msg):
        if self._monitor_tray_icon:
            self._monitor_tray_obj.update(self.get_ico_file(icon), self._name + " - " + msg)
        
    def prepare_systray(self):
        ti=True
        try:
            if 'monitor_tray_icon' in self._properties:
                ti=self._properties['monitor_tray_icon']
        except Exception:
            None
        if self._monitor_tray_icon!=ti:
            msgst=self._get_message('monitorStatusNoService')
            self._monitor_tray_obj=gdi.NotifyIcon(self.get_ico_file(u"monitor_warning"), self._name + " - " + msgst)
            self._monitor_tray_obj.set_object("window",self._app)
            self._monitor_tray_obj.set_action(self.notify_action)            
            self._monitor_tray_icon=ti
    
    def prepare_window(self):
        self._cur_status="NOSERVICE"
        self._cur_activities=None
        #msgst=self._get_message('monitorStatusNoService')
        
        
        self._app = gdi.Window(gdi.WINDOW_TYPE_NORMAL_NOT_RESIZABLE,None,self._logo);
        self._app.set_title(self._get_message('monitorTitle'))
        self._app.set_size(_WIDTH, _HEIGHT)
        self._app.set_show_position(gdi.WINDOW_POSITION_CENTER_SCREEN)
        self._app.set_action(self._window_action)
                
        
        self._img_status_top = gdi.Panel()
        self._img_status_top.set_position(0, 0)
        self._img_status_top.set_size(_CONTENT_WIDTH, _HEIGHT_STATUS_BAR)
        self._img_status_top.set_background_gradient("ffffff", "ffffff", gdi.GRADIENT_DIRECTION_TOPBOTTOM)
        self._app.add_component(self._img_status_top)
        
        
        self._lbl_status = gdi.Label()
        self._lbl_status.set_background("ffffff")
        self._lbl_status.set_opaque(True)
        self._lbl_status.set_text_align(gdi.TEXT_ALIGN_CENTERMIDDLE)
        self._lbl_status.set_text(self._get_message('waiting'))
        self._lbl_status.set_position(0, _HEIGHT_STATUS_BAR)
        #self._lbl_status.set_size(_CONTENT_WIDTH,int((_HEIGHT-(2*_HEIGHT_STATUS_BAR))/2.8))
        self._lbl_status.set_size(_CONTENT_WIDTH,_HEIGHT_STATUS)        
        self._app.add_component(self._lbl_status)
        
        self._img_status_bottom = gdi.Panel()
        self._img_status_bottom.set_position(0, self._lbl_status.get_y() + self._lbl_status.get_height())
        self._img_status_bottom.set_size(_CONTENT_WIDTH,_HEIGHT_STATUS_BAR)
        self._img_status_bottom.set_background_gradient("ffffff", "ffffff", gdi.GRADIENT_DIRECTION_BOTTONTOP)
        self._app.add_component(self._img_status_bottom)
        
        self._lbl_notificationst = gdi.Label()
        self._lbl_notificationst.set_background("d9d9d9")
        self._lbl_notificationst.set_opaque(True)
        self._lbl_notificationst.set_text_align(gdi.TEXT_ALIGN_CENTERMIDDLE)
        self._lbl_notificationst.set_text(self._get_message('monitorCurrentActivities'))
        self._lbl_notificationst.set_position(0, self._img_status_bottom.get_y() + self._img_status_bottom.get_height())
        self._lbl_notificationst.set_size(_CONTENT_WIDTH,25)
        self._app.add_component(self._lbl_notificationst)
        
        self._lbl_notificationsl = gdi.Label()
        self._lbl_notificationsl.set_background("ffffff")
        self._lbl_notificationsl.set_opaque(True)
        self._lbl_notificationsl.set_text_align(gdi.TEXT_ALIGN_RIGHTMIDDLE)
        self._lbl_notificationsl.set_position(0, self._lbl_notificationst.get_y() + self._lbl_notificationst.get_height())
        self._lbl_notificationsl.set_size(int(_CONTENT_WIDTH/2),_HEIGHT-(self._lbl_notificationst.get_y() + self._lbl_notificationst.get_height()))
        self._app.add_component(self._lbl_notificationsl)
        
        self._lbl_notificationsr = gdi.Label()
        self._lbl_notificationsr.set_background("ffffff")
        self._lbl_notificationsr.set_opaque(True)
        self._lbl_notificationsr.set_text_align(gdi.TEXT_ALIGN_LEFTMIDDLE)
        self._lbl_notificationsr.set_position(int(_CONTENT_WIDTH/2), self._lbl_notificationsl.get_y())
        self._lbl_notificationsr.set_size(self._lbl_notificationsl.get_width(),self._lbl_notificationsl.get_height())
        self._app.add_component(self._lbl_notificationsr)
        
        self._lbl_notificationsn = gdi.Label()
        self._lbl_notificationsn.set_background("ffffff")
        self._lbl_notificationsn.set_position(0,self._lbl_notificationsl.get_y()+(int(self._lbl_notificationsl.get_height()/2)-(26/2)))
        self._lbl_notificationsn.set_text(self._get_message('monitorNoActivities'))
        self._lbl_notificationsn.set_text_align(gdi.TEXT_ALIGN_CENTERMIDDLE)
        self._lbl_notificationsn.set_size(_CONTENT_WIDTH,26)
        self._lbl_notificationsn.set_opaque(True)
        self._app.add_component(self._lbl_notificationsn)
                
        self._pnl_bottom = gdi.Panel()
        self._pnl_bottom.set_position(_CONTENT_WIDTH, 0)
        self._pnl_bottom.set_size(_WIDTH_RIGHT, _HEIGHT)
        self._app.add_component(self._pnl_bottom)
        
        wbtn=_WIDTH_RIGHT-20
        hbtn=36
        appy=10
        
        self._btends = gdi.Button()
        self._btends.set_position(10, appy)
        self._btends.set_size(wbtn, hbtn)
        self._btends.set_text(self._get_message('monitorDisable'))
        self._btends.set_action(self.enable_disable)
        self._btends.set_enable(False)
        self._pnl_bottom.add_component(self._btends)
        appy+=hbtn+6        
        
        self._btconfig = gdi.Button()
        self._btconfig.set_position(10, appy)
        self._btconfig.set_size(wbtn, hbtn)
        self._btconfig.set_text(self._get_message('monitorConfigure'))
        self._btconfig.set_action(self.configure)
        self._btconfig.set_enable(False)
        self._pnl_bottom.add_component(self._btconfig)
        appy+=hbtn+6
        
        self._btunistall = gdi.Button()
        self._btunistall.set_position(10, appy)
        self._btunistall.set_size(wbtn, hbtn)
        self._btunistall.set_text(self._get_message('monitorUninstall'))
        self._btunistall.set_action(self.unistall)
        self._pnl_bottom.add_component(self._btunistall)
        appy+=hbtn+6
        
    def start(self, mode):        
        self._semaphore = threading.Condition()
        self._sharedmemclient = None
        self._mode=mode
        self._monitor_tray_icon=False
        self._monitor_tray_obj=None
        self._monitor_desktop_notification="visible"
        self._update=False
        if mode=="info":
            self.printInfo()
        else:
            if not self.lock():
                if mode=="window":
                    self.add_show_file()
                return            
            
            while self.check_update() or self.check_stop():
                time.sleep(2) #Attende finché il server non cancella l'update file o lo stop file
        
            try:
                if 'monitor_desktop_notification' in self._properties:
                    self._monitor_desktop_notification=self._properties['monitor_desktop_notification']
            except Exception:
                None
            
            #Carica Maschera 
            self.prepare_window()            
            if mode=="systray":
                self.prepare_systray()
            else:
                self._app.show()
            
            #Attiva Eventi
            gdi.add_scheduler(0.5, self.update_status)
            
            #self._event=None
            gdi.add_scheduler(1, self.check_events)
            
            gdi.loop()
            self.unlock()
            if self._update:
                self.run_update()
        if self._sharedmemclient is not None:
            self._sharedmemclient.close()

def fmain(args): #SERVE PER MACOS APP
    try:
        mode = None
        for arg in args: 
            if arg.lower() == "systray":
                mode = "systray"
                break
            elif arg.lower() == "window":
                mode = "window"
                break
            elif arg.lower() == "info":
                mode = "info"
                break
        if mode is not None:
            main = Main()
            Main.set_instance(main)
            main.start(mode)
        else:
            try:
                main = Main()
                Main.set_instance(main)
                main.start("window")
            except:
                main = Main()
                Main.set_instance(main)
                main.start("info")
        sys.exit(0)
    except Exception as e:
        print str(e)
        sys.exit(1)

def ctrlHandler(ctrlType):    
    return 1

if __name__ == "__main__":
    fmain(sys.argv)
    