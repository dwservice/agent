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

_WIDTH=440
_HEIGHT=180
#_HEIGHT_BOTTOM=45
#_CONTENT_HEIGHT=_HEIGHT-_HEIGHT_BOTTOM
_WIDTH_RIGHT=140
_CONTENT_WIDTH=_WIDTH-_WIDTH_RIGHT
_HEIGHT_STATUS=30

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

       
class Main():
    
    def __init__(self):
        self._name=u"DWAgent"
        self._logo=None
        self._properties={}
        try:
            f = utils.file_open('config.json')
            self._properties = json.loads(f.read())
            f.close()
        except Exception:
            None
        if 'name' in self._properties:
            self._name=unicode(self._properties["name"])
        if "logo" in self._properties:
            self._logo=self._properties["logo"]
    
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
    
    def lock(self):
        self._homedir = get_user_dir() + utils.path_sep + u"." + self._name.lower()
        if not utils.path_exists(self._homedir):
            utils.path_makedirs(self._homedir)
        self._lockfilename = self._homedir + utils.path_sep + "monitor.lock"
        try:
            if is_linux():
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
        return images.get_image(name + ".ico")
       
    def get_info(self):
        ret={"state": "-1","connections":"0"}
        self._semaphore.acquire()
        try:
            if self._sharedmemclient==None or self._sharedmemclient.is_close():
                self._sharedmemclient=listener.SharedMemClient()
                self._status_cnt=-1

            cnt=long(self._sharedmemclient.get_property("counter"))
            if self._status_cnt!=cnt:
                self._status_cnt=cnt
                ret["state"] = self._sharedmemclient.get_property("state")
                try:
                    ret["connections"] = self._sharedmemclient.get_property("connections")
                except:
                    None
                try:
                    ret["group"] = self._sharedmemclient.get_property("group").decode("unicode-escape")
                except:
                    None
                try:
                    ret["name"] = self._sharedmemclient.get_property("name").decode("unicode-escape")
                except:
                    None
                return ret;
            else:
                return ret
        except Exception as e:
            print str(e)
            return ret
        finally:
            self._semaphore.release()
            
    def check_events(self):
        if self.check_stop():
            self._app.destroy()
            return
        if self.check_update():
            self._update=True
            self._app.destroy()
            return
        if self.check_show():
            self._app.show()
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
        
        if newst != self._cur_status or appar["connections"] != self._cur_connections:
            self._cur_status=newst 
            self._cur_connections=appar["connections"]
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
            apptx.append(self._get_message("monitorStatus"))
            apptx.append(u": ")
            apptx.append(self.msgst)
            apptx.append(u"\n")
            apptx.append(self._get_message("monitorConnections"))
            apptx.append(u": ")
            apptx.append(self._cur_connections)
            self._lbl_status.set_text(u"".join(apptx))
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
        msg=self._get_message('monitorDisableAgentQuestion')
        if self._cur_status=="DISABLE":
            msg=self._get_message('monitorEnableAgentQuestion')
        
        dlg = gdi.DialogMessage(gdi.DIALOGMESSAGE_ACTIONS_YESNO,gdi.DIALOGMESSAGE_LEVEL_INFO,self._app)
        dlg.set_title(self._get_message('monitorTitle'))
        dlg.set_message(msg)
        dlg.set_action(self._enable_disable_action)
        dlg.show();
    
    def configure(self, e):
        if is_windows():
            subprocess.call(["native" + utils.path_sep + "dwaglnc.exe" , "configure"]) 
        elif is_linux():
            subprocess.Popen(["native" + utils.path_sep + "configure"])
        elif is_mac():
            subprocess.Popen(["native/Configure.app/Contents/MacOS/Configure"])
    
    def run_update(self):
        #Lancia se stesso perche con il file monitor.update attende che le librerie si aggiornano
        if is_windows():
            subprocess.call(["native" + utils.path_sep + "dwaglnc.exe" , "systray"]) 
        elif is_linux():
            None
            #subprocess.Popen(["native" + utils.path_sep + "configure"])
        elif is_mac():
            None
            #subprocess.Popen(["native/Configure.app/Contents/MacOS/Configure"])
    
    def unistall(self, e):
        if is_windows():
            subprocess.call(["native" + utils.path_sep + "dwaglnc.exe" , "uninstall"]) 
        elif is_linux():
            sucmd=None
            if self._which("gksu"):
                sucmd="gksu"
            elif self._which("kdesu"):
                sucmd="kdesu"
            if sucmd is not None:
                subprocess.Popen([sucmd , utils.path_absname("native" + utils.path_sep + "uninstall")])
            else:
                dlg = gdi.DialogMessage(gdi.DIALOGMESSAGE_ACTIONS_OK,gdi.DIALOGMESSAGE_LEVEL_ERROR,self._app)
                dlg.set_title(self._get_message('monitorTitle'))
                dlg.set_message(self._get_message('monitorUninstallNotRun'))
                dlg.show();
        elif is_mac():
            subprocess.Popen(["native/Uninstall.app/Contents/MacOS/Uninstall"])      
    
    def _which(self, name):
        p = subprocess.Popen("which " + name, stdout=subprocess.PIPE, shell=True)
        (po, pe) = p.communicate()
        p.wait()
        return len(po) > 0     
    
    def printInfo(self):
        msgst=""
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
        print("Status: " + msgst)
        print("Connections: " + appar["connections"])
    
    
    def _actions_systray(self,e):
        if e["action"]=="show":
            self._app.show()
            self._app.to_front()
        elif e["action"]=="hide":
            self._app.hide()
        elif e["action"]=="enable":
            self.enable_disable(e)
        elif e["action"]=="disable":
            self.enable_disable(e)
        elif e["action"]=="configure":
            self.configure(e)
    
    def _window_action(self,e):
        if e["action"]==u"ONCLOSE":
            if self._monitor_tray_icon:
                e["source"].hide()
                e["cancel"]=True
        if e["action"]==u"NOTIFYICON_ACTIVATE":
            e["source"].show()
            e["source"].to_front()
        elif e["action"]==u"NOTIFYICON_CONTEXTMENU":
            pp=gdi.PopupMenu()
            pp.set_show_position(gdi.POPUP_POSITION_TOPLEFT)
            if not self._app.is_show():
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
            self._app.update_notifyicon(self.get_ico_file(icon), self._name + " - " + msg)
        
    def prepare_systray(self):
        ti=True
        try:
            if 'monitor_tray_icon' in self._properties:
                ti=self._properties['monitor_tray_icon']
        except Exception:
            None
        if self._monitor_tray_icon!=ti:
            msgst=self._get_message('monitorStatusNoService')
            self._app.show_notifyicon(self.get_ico_file(u"monitor_warning"), self._name + " - " + msgst)
            self._monitor_tray_icon=ti
    
    def prepare_window(self):
        self._cur_status="NOSERVICE"
        self._cur_connections=0
        #msgst=self._get_message('monitorStatusNoService')
        
        
        self._app = gdi.Window(gdi.WINDOW_TYPE_NORMAL_NOT_RESIZABLE,None,self._logo);
        self._app.set_title(self._get_message('monitorTitle'))
        self._app.set_size(_WIDTH, _HEIGHT)
        self._app.set_show_position(gdi.WINDOW_POSITION_CENTER_SCREEN)
        self._app.set_action(self._window_action)
        
        self._img_status_top = gdi.Panel()
        self._img_status_top.set_position(0, 0)
        self._img_status_top.set_size(_CONTENT_WIDTH, _HEIGHT_STATUS)
        self._img_status_top.set_background_gradient("ffffff", "ffffff", gdi.GRADIENT_DIRECTION_TOPBOTTOM)
        self._app.add_component(self._img_status_top)
        
        self._img_status_bottom = gdi.Panel()
        self._img_status_bottom.set_position(0, _HEIGHT-_HEIGHT_STATUS)
        self._img_status_bottom.set_size(_CONTENT_WIDTH,_HEIGHT_STATUS)
        self._img_status_bottom.set_background_gradient("ffffff", "ffffff", gdi.GRADIENT_DIRECTION_BOTTONTOP)
        self._app.add_component(self._img_status_bottom)
        
        
        self._lbl_status = gdi.Label()
        self._lbl_status.set_text_align(gdi.TEXT_ALIGN_CENTERMIDDLE)
        self._lbl_status.set_text(self._get_message('waiting'))
        self._lbl_status.set_position(0, _HEIGHT_STATUS)
        self._lbl_status.set_size(_CONTENT_WIDTH,_HEIGHT-(2*_HEIGHT_STATUS))
        self._app.add_component(self._lbl_status)
        
        
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
        #GESTIONE PROVVISORIA MAC
        if mode=="systray" and is_mac():
            while True:
                time.sleep(5)
            return
        
        self._semaphore = threading.Condition()
        self._sharedmemclient = None
        self._mode=mode
        self._monitor_tray_icon=False
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
        
            #Carica Maschera 
            self.prepare_window()
            
            #Attiva Eventi
            gdi.add_scheduler(0.5, self.update_status)
            #self._event=None
            gdi.add_scheduler(1, self.check_events)
            
            bshow=True
            if mode=="systray":
                self.prepare_systray()
                bshow=False
            
            gdi.loop(self._app, bshow)
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

if __name__ == "__main__":
    fmain(sys.argv)
    