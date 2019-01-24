# -*- coding: utf-8 -*-

'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''

import messages
import ui
import sys
import listener
import utils
import json

class Configure:
    
    def __init__(self):
        #self._config_port = 7950
        #self._path_config='config.json'
        self._sharedmemclient=None
        self._install_code=ui.VarString()
        self._proxy_type=ui.VarString("SYSTEM")
        self._proxy_host=ui.VarString("")
        self._proxy_port=ui.VarString("")
        self._proxy_user=ui.VarString("")
        self._proxy_password=ui.VarString("", True)
        self._password=""
        self._main_menu_sel=ui.VarString("configureAgent")
        self._agent_menu_sel=ui.VarString("configureChangeInstallKey")
        self._password_menu_sel=ui.VarString("configureSetPassword")
        self._name=None
        
    
    def _get_message(self, key):
        smsg = messages.get_message(key)
        if self._name is not None:
            return smsg.replace(u"DWAgent",self._name)
        else:
            return smsg
    
    def send_req(self, req, prms=None):
        try:
            if self._sharedmemclient==None or self._sharedmemclient.is_close():
                self._sharedmemclient=listener.SharedMemClient()
            return self._sharedmemclient.send_request("admin", self._password, req, prms);
        except: 
            return 'ERROR:REQUEST_TIMEOUT'
    
    def close_req(self):
        if self._sharedmemclient!=None and not self._sharedmemclient.is_close():
            self._sharedmemclient.close()
            
    def check_auth(self):
        sret=self.send_req("check_auth", None)
        if sret=="OK":
            return True
        elif sret=="ERROR:FORBIDDEN":
            return False
        else:
            raise Exception(sret[6:])
    
    def get_config(self, key):
        sret=self.send_req("get_config", {'key':key})
        if sret[0:2]=="OK":
            return sret[3:]
        else:
            raise Exception(sret[6:])
        return sret     
    
    def set_config(self, key, val):
        sret=self.send_req("set_config", {'key':key, 'value':val})
        if sret!="OK":
            raise Exception(sret[6:])
            
    def uninstall_key(self):
        sret=self.send_req("remove_key", None)
        if sret!="OK":
            raise Exception(sret[6:])
        return sret  
    
    def install_key(self, code):
        sret=self.send_req("install_key", {'code':code})
        if sret!="OK":
            raise Exception(sret[6:])
        return sret  
    
    def change_pwd(self, pwd):
        if pwd!="":
            sret=self.send_req("change_pwd", {'password':self._change_pwd.get()})
        else:
            sret=self.send_req("change_pwd", {'nopassword':'true'})
        if sret!="OK":
            raise Exception(sret[6:])
        return sret  
    
    def is_agent_enable(self):
        s = self.get_config("enabled")
        return s=="True"
    
    def read_proxy_info(self):
        pt = self.get_config("proxy_type")
        self._proxy_type.set(pt)
        if self._proxy_type.get()=='HTTP' or self._proxy_type.get()=='SOCKS4' or self._proxy_type.get()=='SOCKS4A' or self._proxy_type.get()=='SOCKS5':
            self._proxy_host.set(self.get_config("proxy_host"))
            self._proxy_port.set(self.get_config("proxy_port"))
            self._proxy_user.set(self.get_config("proxy_user"))
    
    def start(self, bgui=True):
        
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
        prmsui["title"]=self._get_message('configureTitle')
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
        self.close_req();
            

    def step_init(self, curui):
        '''
        try:
            msg = ui.Message(self._get_message('configureWelcome'))
            msg.next_step(self.step_check_password)
        except Exception as e:
            msg = ui.Message(str(e))
        return msg
        '''
        return self.step_check_password(curui);
    
    def step_check_password(self, curui):
        try:
            if curui.get_key() is not None and curui.get_key()=='insert_password':
                self._password=self._ins_pwd.get()
            if not self.check_auth():
                if curui.get_key() is not None and curui.get_key()=='insert_password':
                    return ui.ErrorDialog(self._get_message('configureInvalidPassword'))
                return self.step_password(curui)
            else:
                return self.step_menu_main(curui)
        except:
            return ui.ErrorDialog(self._get_message('configureErrorConnection'))
    
    def step_password(self, curui):
        self._ins_pwd=ui.VarString("", True)
        ipt = ui.Inputs()
        ipt.set_key("insert_password")
        ipt.set_message(self._get_message('configureInsertPassword'))
        ipt.add('password', self._get_message('password'), self._ins_pwd,  True)
        ipt.next_step(self.step_check_password)
        return ipt
    
    def step_menu_main(self, curui):
        try:
            self.read_proxy_info()
        except:
            return ui.ErrorDialog(self._get_message('configureErrorConnection'))
        chs = ui.Chooser()
        chs.set_message(self._get_message('configureChooseOperation'))
        chs.add("configureAgent", self._get_message('configureAgent'))
        chs.add("configureProxy", self._get_message('configureProxy'))
        #chs.add("configureMonitor", self._get_message('configureMonitor'))
        chs.add("configurePassword", self._get_message('configurePassword'))
        #chs.add("configureExit", self._get_message('configureExit'))
        chs.set_variable(self._main_menu_sel)
        chs.next_step(self.step_menu_main_selected)
        return chs

    def step_menu_main_selected(self, curui):
        if curui.get_variable().get()=="configureAgent":
            return self.step_menu_agent(curui)
        elif curui.get_variable().get()=="configureProxy":
            curui.set_key("menuProxy")
            return self.step_configure_proxy_type(curui)
        elif curui.get_variable().get()=="configureMonitor":
            return self.step_menu_monitor(curui)
        elif curui.get_variable().get()=="configurePassword":
            return self.step_menu_password(curui)
        elif curui.get_variable().get()=="configureExit":
            return ui.Message(self._get_message('configureEnd'))
    
    def step_menu_agent(self, curui):
        try:
            self._install_code.set("")
            key = self.get_config("key")
            if key == "":
                return self.step_menu_agent_install_key_selected(curui)
            else:
                chs = ui.Chooser()
                chs.set_message(self._get_message('configureChooseOperation'))
                chs.add("configureChangeInstallKey", self._get_message('configureChangeInstallKey'))
                if self.is_agent_enable():
                    chs.add("configureDisableAgent", self._get_message('configureDisableAgent'))
                else:
                    chs.add("configureEnableAgent", self._get_message('configureEnableAgent'))
                chs.set_variable(self._agent_menu_sel)
                chs.prev_step(self.step_menu_main)
                chs.next_step(self.step_menu_agent_selected)
                return chs
        except:
            return ui.ErrorDialog(self._get_message('configureErrorConnection'))
            
    
    def step_menu_agent_selected(self, curui):
        if curui.get_variable().get()=="configureChangeInstallKey":
            return self.step_menu_agent_install_key(curui)
        elif curui.get_variable().get()=="configureEnableAgent":
            return self.step_menu_agent_enable(curui)
        elif curui.get_variable().get()=="configureDisableAgent":
            return self.step_menu_agent_disable(curui)
            
    def step_menu_agent_install_key(self, curui):
        chs = ui.Chooser()
        chs.set_message(self._get_message('configureUninstallKeyQuestion'))
        chs.add("yes", self._get_message('yes'))
        chs.add("no", self._get_message('no'))
        chs.set_variable(ui.VarString("no"))
        chs.set_accept_key("yes")
        chs.prev_step(self.step_menu_agent)
        chs.next_step(self.step_menu_agent_remove_key_selected)
        return chs
    
    def step_menu_agent_remove_key_selected(self, curui):
        if curui.get_variable().get()=='yes':
            try:
                self._uinterface.wait_message(self._get_message('configureUninstallationKey'),  0)
                self.uninstall_key()
            except:
                    return ui.ErrorDialog(self._get_message('configureErrorConnection'))
            return self.step_menu_agent_install_key_selected(curui)
        else:
            return self.step_menu_agent(curui)
    
    def step_menu_agent_install_key_selected(self, curui):
        ipt = ui.Inputs()
        ipt.set_message(self._get_message('enterInstallCode'))
        ipt.add('code', self._get_message('code'), self._install_code, True)
        ipt.prev_step(self.step_menu_agent)
        ipt.next_step(self.step_check_install_code)
        return ipt
    
    def step_check_install_code(self, curui):
        if curui.get_key() is not None and curui.get_key()=='tryAgain':
            if curui.get_variable().get()=='configureLater':
                return self.step_menu_main(curui)
            elif curui.get_variable().get()=='configProxy':
                curui.set_key("installCode")
                return self.step_configure_proxy_type(curui)
            elif curui.get_variable().get()=='reEnterCode':
                return self.step_menu_agent_install_key_selected(curui)
        msg=self._get_message('checkInstallCode')
        self._uinterface.wait_message(msg)
        key = self._install_code.get()
        try:
            self.install_key(key)
            msg = ui.Message(self._get_message('configureKeyInstalled'))
            msg.next_step(self.step_menu_main)
            return msg
        except Exception as e:
            s = str(e)
            if s=="INVALID_CODE":
                chs = ui.Chooser()
                chs.set_key("tryAgain")
                chs.set_message(self._get_message('errorInvalidCode'))
                chs.add("reEnterCode", self._get_message('reEnterCode'))
                chs.add("configureLater", self._get_message('configureLater'))
                chs.set_variable(ui.VarString("reEnterCode"))
                chs.prev_step(self.step_menu_agent_install_key_selected)
                chs.next_step(self.step_check_install_code)
                return chs
            elif s=="CONNECT_ERROR":
                chs = ui.Chooser()
                chs.set_key("tryAgain")
                chs.set_message(self._get_message('errorConnectionQuestion'))
                chs.add("configProxy", self._get_message('yes'))
                chs.add("noTryAgain", self._get_message('noTryAgain'))
                chs.add("configureLater", self._get_message('configureLater'))
                chs.set_variable(ui.VarString("noTryAgain"))
                chs.prev_step(self.step_menu_agent_install_key_selected)
                chs.next_step(self.step_check_install_code)
                return chs
            elif s=="REQUEST_TIMEOUT":
                return ui.ErrorDialog(self._get_message('configureErrorConnection'))
            else:
                return ui.ErrorDialog(s) 
    
    def step_configure_proxy_type(self, curui):
        chs = ui.Chooser()
        chs.set_key(curui.get_key())
        chs.set_message(self._get_message('chooseProxyType'))
        chs.add("SYSTEM", self._get_message('proxySystem'))
        chs.add("HTTP", self._get_message('proxyHttp'))
        chs.add("SOCKS4", self._get_message('proxySocks4'))
        chs.add("SOCKS4A", self._get_message('proxySocks4a'))
        chs.add("SOCKS45", self._get_message('proxySocks5'))
        chs.add("NONE", self._get_message('proxyNone'))
        chs.set_variable(self._proxy_type)
        
        if curui.get_key()=="menuProxy":
            chs.prev_step(self.step_menu_main)
        elif curui.get_key()=="installCode":
            chs.prev_step(self.step_menu_agent_install_key_selected)
        
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
        ar = curui.get_key().split('_')
        curui.set_key(ar[0]) 
        if len(ar)==2 and ar[1]=='tryAgain':
            if curui.get_variable() is not None and curui.get_variable().get()=='configureLater':
                if curui.get_key()=="menuProxy":
                    return self.step_menu_main(curui)
                elif curui.get_key()=="installCode":
                    return self.step_menu_agent_install_key_selected(curui)
        try:
            if self._proxy_type.get()=='HTTP' or self._proxy_type.get()=='SOCKS4' or self._proxy_type.get()=='SOCKS4A' or self._proxy_type.get()=='SOCKS5':
                try:
                    int(self._proxy_port.get())
                except:
                    return ui.ErrorDialog(self._get_message("validInteger") .format(self._get_message('proxyPort')))
            sret=self.send_req("set_proxy",  {'type': self._proxy_type.get(), 
                                                       'host':  self._proxy_host.get(), 
                                                       'port': self._proxy_port.get(), 
                                                       'user': self._proxy_user.get(), 
                                                       'password': self._proxy_password.get()})
            if sret!="OK":
                raise Exception(sret[6:])
        except:
            chs = ui.Chooser()
            chs.set_key(curui.get_key() + "_tryAgain")
            chs.set_message(self._get_message('errorConnectionConfig'))
            chs.add("noTryAgain", self._get_message('noTryAgain'))
            chs.add("configureLater", self._get_message('configureLater'))
            chs.set_variable(ui.VarString("noTryAgain"))
            if curui.get_key()=="menuProxy":
                chs.prev_step(self.step_menu_main)
            elif curui.get_key()=="installCode":
                chs.prev_step(self.step_menu_agent_install_key_selected)
            chs.next_step(self.step_configure_proxy_set)
            return chs
        if curui.get_key()=="menuProxy":
            msg = ui.Message(self._get_message('configureProxyEnd'))
            msg.next_step(self.step_menu_main)
            return msg
        elif curui.get_key()=="installCode":
            return self.step_check_install_code(curui)
        
    
    def step_menu_agent_enable(self, ui):
        chs = ui.Chooser()
        chs.set_message(self._get_message('configureEnableAgentQuestion'))
        chs.add("yes", self._get_message('yes'))
        chs.add("no", self._get_message('no'))
        chs.set_variable(ui.VarString("no"))
        chs.set_accept_key("yes")
        chs.prev_step(self.step_menu_agent)
        chs.next_step(self.step_menu_agent_enable_procede)
        return chs
    
    def step_menu_agent_disable(self, curui):
        chs = ui.Chooser()
        chs.set_message(self._get_message('configureDisableAgentQuestion'))
        chs.add("yes", self._get_message('yes'))
        chs.add("no", self._get_message('no'))
        chs.set_variable(ui.VarString("no"))
        chs.set_accept_key("yes")
        chs.prev_step(self.step_menu_agent)
        chs.next_step(self.step_menu_agent_disable_procede)
        return chs
        
    def step_menu_agent_enable_procede(self, curui):
        if curui.get_variable().get()=='yes':
            try:
                self.set_config("enabled", "True")
                msg = ui.Message(self._get_message('configureAgentEnabled'))
                msg.next_step(self.step_menu_main)
                return msg
            except:
                    return ui.ErrorDialog(self._get_message('configureErrorConnection'))
        else:
            return self.step_menu_agent(curui)
    
    def step_menu_agent_disable_procede(self, curui):
        if curui.get_variable().get()=='yes':
            try:
                self.set_config("enabled", "False")
                msg = ui.Message(self._get_message('configureAgentDisabled'))
                msg.next_step(self.step_menu_main)
                return msg
            except:
                    return ui.ErrorDialog(self._get_message('configureErrorConnection'))
        else:
            return self.step_menu_agent(curui)
    
    def step_menu_monitor(self, curui):
        chs = ui.Chooser()
        chs.set_message(self._get_message('configureChooseOperation'))
        chs.add("configureTrayIconVisibility", self._get_message('configureTrayIconVisibility'))
        chs.set_variable(ui.VarString("configureTrayIconVisibility"))
        chs.prev_step(self.step_menu_main)
        chs.next_step(self.step_menu_monitor_selected)
        return chs
    
    def step_menu_monitor_selected(self, ui):
        try:
            chs = ui.Chooser()
            chs.set_message(self._get_message('configureChooseMonitorTrayIconVisibility'))
            chs.add("yes", self._get_message('yes'))
            chs.add("no", self._get_message('no'))
            if self.get_config("monitor_tray_icon")=="True":
                chs.set_variable(ui.VarString("yes"))
            else:
                chs.set_variable(ui.VarString("no"))
            chs.prev_step(self.step_menu_monitor)
            chs.next_step(self.step_menu_monitor_procede)
            return chs
        except:
            return ui.ErrorDialog(self._get_message('configureErrorConnection'))
    
    def step_menu_monitor_procede(self, curui):
        try:
            if curui.get_variable().get()=='yes':
                self.set_config("monitor_tray_icon", "True")
            else:
                self.set_config("monitor_tray_icon", "False")
            msg = ui.Message(self._get_message('configureTrayIconOK'))
            msg.next_step(self.step_menu_main)
            return msg
        except:
            return ui.ErrorDialog(self._get_message('configureErrorConnection'))

    def step_menu_password(self, curui):
        chs = ui.Chooser()
        chs.set_message(self._get_message('configureChooseOperation'))
        chs.add("configureSetPassword", self._get_message('configureSetPassword'))
        chs.add("configureRemovePassword", self._get_message('configureRemovePassword'))
        chs.set_variable(self._password_menu_sel)
        chs.prev_step(self.step_menu_main)
        chs.next_step(self.step_config_password)
        return chs

    def step_config_password(self, curui):
        if curui.get_variable().get()=='configureSetPassword':
            self._change_pwd=ui.VarString("", True)
            self._change_repwd=ui.VarString("", True)
            ipt = ui.Inputs()
            ipt.set_key("set_password")
            ipt.set_message(self._get_message('configurePassword'))
            ipt.add('password', self._get_message('password'), self._change_pwd,  True)
            ipt.add('rePassword', self._get_message('rePassword'), self._change_repwd,  True)
            ipt.prev_step(self.step_menu_password)
            ipt.next_step(self.step_config_password_procede)
            return ipt
        elif curui.get_variable().get()=='configureRemovePassword':
            chs = ui.Chooser()
            chs.set_key("remove_password")
            chs.set_message(self._get_message('configureRemovePasswordQuestion'))
            chs.add("yes", self._get_message('yes'))
            chs.add("no", self._get_message('no'))
            chs.set_variable(ui.VarString("no"))
            chs.set_accept_key("yes")
            chs.prev_step(self.step_menu_password)
            chs.next_step(self.step_config_password_procede)
            return chs
    
    def step_config_password_procede(self, curui):
        if curui.get_key() is not None and curui.get_key()=='set_password':
            if self._change_pwd.get()==self._change_repwd.get():
                try:
                    self.change_pwd(self._change_pwd.get())
                    self._password=self._change_pwd.get()
                    msg = ui.Message(self._get_message('configurePasswordUpdated'))
                    msg.next_step(self.step_menu_main)
                    return msg
                except:
                    return ui.ErrorDialog(self._get_message('configureErrorConnection'))
            else:
                return ui.ErrorDialog(self._get_message('configurePasswordErrNoMatch'))
        elif curui.get_key() is not None and curui.get_key()=='remove_password':
            if curui.get_variable().get()=='yes':
                try:
                    self.change_pwd("")
                    self._password=""
                    msg = ui.Message(self._get_message('configurePasswordUpdated'))
                    msg.next_step(self.step_menu_main)
                    return msg
                except:
                    return ui.ErrorDialog(self._get_message('configureErrorConnection'))
                
def fmain(args): #SERVE PER MACOS APP
    bgui=True
    for arg in args: 
        if arg.lower() == "-console":
            bgui=False
    i = Configure()
    i.start(bgui)

if __name__ == "__main__":
    fmain(sys.argv)
    
