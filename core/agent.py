# -*- coding: utf-8 -*-
'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import communication
import threading
import time
import sys
import json
import string
import random
import os
import zipfile
import gzip
import signal
import platform
import hashlib
import listener
import ctypes
import shutil
import ipc
import importlib 
import applications
import struct
import utils
import mimetypes
import detectinfo
import native


def is_windows():
    return utils.is_windows()

def is_linux():
    return utils.is_linux()

def is_mac():
    return utils.is_mac()

def get_os_type():
    if is_linux():
        return "Linux"
    elif is_windows():
        return "Windows"
    elif is_mac():
        return "Mac"
    else:
        return "Unknown"

def get_os_type_code():
    if is_linux():
        return 0
    elif is_windows():
        return 1
    elif is_mac():
        return 2
    else:
        return -1

def get_prop(prop,key,default=None):
    if key in prop:
        return prop[key]
    return default
        
def generate_key(n):
    c = "".join([string.ascii_lowercase, string.ascii_uppercase,  string.digits])
    return "".join([random.choice(c) 
                    for x in utils.nrange(n)])
        
def str2bool(v):
        return v.lower() in ("yes", "true", "t", "1")    

def bool2str(v):
    if v is None or v is False:
        return 'False'
    else:
        return 'True'

def hash_password(pwd):
    encoded = hashlib.sha256(utils.str_to_bytes(pwd,"utf8")).digest()
    encoded = utils.enc_base64_encode(encoded)
    return utils.bytes_to_str(encoded)

def obfuscate_password(pwd):
    return utils.bytes_to_str(utils.enc_base64_encode(utils.zlib_compress(utils.str_to_bytes(pwd,"utf8"))))

def read_obfuscated_password(enpwd):
    return utils.bytes_to_str(utils.zlib_decompress(utils.enc_base64_decode(enpwd)),"utf8")
    
def read_config_file():
    c=None
    try:
        f = utils.file_open("config.json", 'rb')
    except:
        e = utils.get_exception()
        raise Exception("Error reading config file. " + utils.exception_to_string(e))
    try:
        s=f.read()
        c = json.loads(utils.bytes_to_str(s,"utf8"))
    except:
        e = utils.get_exception()
        raise Exception("Error parse config file: " + utils.exception_to_string(e))
    finally:
        f.close()
    return c

def write_config_file(jo):
    s = json.dumps(jo, sort_keys=True, indent=1)
    f = utils.file_open("config.json", 'wb')
    f.write(utils.str_to_bytes(s,"utf8"))
    f.close()

class Agent():
    _STATUS_OFFLINE = 0
    _STATUS_ONLINE = 1
    _STATUS_DISABLE = 3
    _STATUS_UPDATING = 10
    _CONNECTION_TIMEOUT= 60
    
    def __init__(self,args):
        
        if utils.path_exists(".srcmode"):
            sys.path.append("..")
        
        #Prepara il log
        self._noctrlfile=False
        self._bstop=False
        self._runonfly=False
        self._runonfly_conn_retry=0
        self._runonfly_user=None
        self._runonfly_password=None
        self._runonfly_runcode=None
        self._runonfly_ipc=None        
        self._runonfly_action=None #COMPATIBILITY WITH OLD FOLDER RUNONFLY
        logconf={}        
        for arg in args: 
            if arg=='-runonfly':
                self._runonfly=True
            elif arg=='-filelog':
                logconf["filename"]=u'dwagent.log'                
            elif arg=='-noctrlfile':
                signal.signal(signal.SIGTERM, self._signal_handler)
                self._noctrlfile=True
            elif arg.lower().startswith("runcode="):
                self._runonfly_runcode=arg[8:]
        if not self._runonfly:
            self._runonfly_runcode=None        
        self._logger = utils.Logger(logconf)        
        #Inizializza campi
        self._task_pool = None
        self._config=None
        self._brun=True
        self._brebootagent=False
        self._breloadconfig=True
        self._breloadagentcnt=None
        if self._runonfly:
            self._cnt_min=0
            self._cnt_max=10
        else:
            self._cnt_min=5
            self._cnt_max=30
        self._cnt_random=0
        self._cnt=self._cnt_max
        self._listener_ipc=None
        self._listener_ipc_load=True
        self._listener_http=None
        self._listener_http_load=True
        self._proxy_info=None        
        self._agent_conn = None
        self._agent_conn_version = 0
        self._sessions={}
        self._libs={}
        self._apps={}
        self._apps_to_reload={}
        self._node_files_info=None
        self._sessions_semaphore = threading.Condition()
        self._libs_apps_semaphore = threading.Condition()
        self._agent_enabled = True
        self._agent_missauth = False
        self._agent_status = self._STATUS_OFFLINE
        self._agent_group = None
        self._agent_name = None
        self._agent_debug_mode = False
        self._agent_url_primary = None
        self._agent_key = None
        self._agent_password = None
        self._agent_server = None
        self._agent_port= None
        self._agent_method_connect_port= None
        self._agent_instance= None
        self._agent_version = None
        self._agent_url_node = None
        self._agent_native_suffix=None
        self._agent_profiler=None
        self._config_semaphore = threading.Condition()
        self._osmodule = native.get_instance()
        self._svcpid=None        
    
    #RIMASTO PER COMPATIBILITA' CON VECCHIE CARTELLE RUNONFLY
    def set_runonfly_action(self,action):
        self._runonfly_action=action
    
    def _signal_handler(self, signal, frame):
        if self._noctrlfile==True:
            self._bstop=True
        else:
            f = utils.file_open("dwagent.stop", 'wb')
            f.close()           
    
    def _write_config_file(self):
        write_config_file(self._config)        
        
    def _read_config_file(self):
        self._config_semaphore.acquire()
        try:
            try:
                self._config = read_config_file()
            except:
                e = utils.get_exception()
                self.write_err(utils.exception_to_string(e))
                self._config = None
        finally:
            self._config_semaphore.release()
    
    def get_proxy_info(self):
        self._config_semaphore.acquire()
        try:
            if self._proxy_info is None:
                self._proxy_info=communication.ProxyInfo()
                if 'proxy_type' in self._config:
                    self._proxy_info.set_type(self._config['proxy_type'])
                else:
                    self._proxy_info.set_type("SYSTEM")
                if 'proxy_host' in self._config:
                    self._proxy_info.set_host(self._config['proxy_host'])
                if 'proxy_port' in self._config:
                    self._proxy_info.set_port(self._config['proxy_port'])
                if 'proxy_user' in self._config:
                    self._proxy_info.set_user(self._config['proxy_user'])
                if 'proxy_password' in self._config:
                    if self._config['proxy_password'] == "":
                        self._proxy_info.set_password("")
                    else:
                        self._proxy_info.set_password(read_obfuscated_password(self._config['proxy_password']))
            return self._proxy_info
        finally:
            self._config_semaphore.release()
    
    
    def get_osmodule(self):
        return self._osmodule 
    
    def get_group(self):
        return self._agent_group
    
    def get_name(self):
        return self._agent_name    
    
    def get_status(self):
        return self._agent_status
    
    def get_session_count(self):
        self._sessions_semaphore.acquire()
        try:
            return len(self._sessions)
        finally:
            self._sessions_semaphore.release()
    
    def get_active_sessions_status(self, ckint=30):
        ar = []
        self._sessions_semaphore.acquire()
        try:
            tm = time.time()
            for sid in self._sessions.keys():
                sesitm = self._sessions[sid]
                if tm-sesitm.get_last_activity_time()<=ckint and not sesitm.get_password_request():
                    itm={}
                    itm["idSession"] = sesitm.get_idsession()
                    itm["initTime"] = sesitm.get_init_time()
                    itm["accessType"] = sesitm.get_access_type()
                    itm["userName"] = sesitm.get_user_name()
                    itm["ipAddress"] = sesitm.get_ipaddress()
                    itm["waitAccept"] = sesitm.get_wait_accept()
                    itm["activities"] = sesitm.get_activities()
                    ar.append(itm)
        finally:
            self._sessions_semaphore.release()
        return ar
    
    def _load_config(self):
        #self.write_info("load configuration...")
        #VERIFICA agentConnectionPropertiesUrl
        self._agent_url_primary = self.get_config('url_primary', None)
        if self._agent_url_primary  is None:
            self.write_info("Missing url_primary configuration.")
            return False
        if not self._runonfly:
            self._agent_key = self.get_config('key', None)
            self._agent_password = self.get_config('password', None)
        else:
            self._agent_key = None
            self._agent_password = None
        return True
    
    
    def _load_agent_properties(self):
        self.write_info("Reading agent properties...")
        try:
            app_url = None
            prp_url = None
            if not self._runonfly:
                if self._agent_key is None or self._agent_password is None:
                    return False
                self._agent_password = read_obfuscated_password(self._agent_password)
                app_url = self._agent_url_primary + "getAgentProperties.dw?key=" + self._agent_key
            else:
                #READ installer.ver
                sver=""
                ptver="native" + os.sep + "installer.ver"
                if utils.path_exists(ptver):
                    fver = utils.file_open(ptver, "rb")
                    sver="&version=" + utils.bytes_to_str(fver.read())
                    fver.close()
                
                spapp = ";".join(self.get_supported_applications())                
                app_url = self._agent_url_primary + "getAgentPropertiesOnFly.dw?osTypeCode=" + str(get_os_type_code()) + sver + "&supportedApplications=" + utils.url_parse_quote_plus(spapp)
                if self._runonfly_runcode is not None:
                    app_url += "&runCode=" + utils.url_parse_quote_plus(self._runonfly_runcode)
                elif "preferred_run_user" in self._config:
                    app_url += "&preferredRunUser=" + utils.url_parse_quote_plus(self._config["preferred_run_user"])
            try:
                prp_url = communication.get_url_prop(app_url, self.get_proxy_info())
                if "error" in prp_url:
                    self.write_info("Error read agentUrlPrimary: " + prp_url['error'])
                    if prp_url['error']=="INVALID_KEY":
                        if not self._runonfly:
                            self.remove_key()
                    if self._runonfly_runcode is not None and prp_url['error']=="RUNCODE_NOTFOUND":
                        self._update_onfly_status("RUNCODE_NOTFOUND")
                    return False
                if self._runonfly:
                    self._agent_key = get_prop(prp_url, 'key', None)
                    apppwd = get_prop(prp_url, 'password', None)
                    arpwd = []
                    for i in reversed(range(len(apppwd))):
                        arpwd.append(apppwd[i:i+1])
                    self._agent_password="".join(arpwd)
                    if self._runonfly_runcode is None:
                        self._runonfly_user=get_prop(prp_url, 'userLogin', None)
                        self._runonfly_password=get_prop(prp_url, 'userPassword', None)
                                        
            except:
                e = utils.get_exception()
                self.write_info("Error reading agentUrlPrimary: " + utils.exception_to_string(e))
                return False
                
            appst = get_prop(prp_url, 'state', None)
            if appst=="D":
                self.write_info("Agent disabled.")
                return False
            elif appst=="S":
                self.write_info("Agent suppressed.")
                if not self._runonfly:
                    self.remove_key()
                return False
            self._agent_server = get_prop(prp_url, 'server', None)
            if self._agent_server is None:
                self.write_info("Missing server configuration.")
                return False
            self._agent_port = get_prop(prp_url, 'port', "7730")            
            self._agent_instance = get_prop(prp_url, 'instance', None)
            if self._agent_instance is None:
                self.write_info("Missing instance configuration.")
                return False
            self._agent_version= get_prop(prp_url, 'agentVersion', None)
            self._agent_conn_version=int(get_prop(prp_url, 'moduleAgentConnVersion', "0"))
            
            
            self.write_info("Primary url: " + self._agent_url_primary)
            self.write_info("Proxy: " + self.get_proxy_info().get_type())
            self.write_info("Readed agent properties.")
            return True
        except:
            e = utils.get_exception()
            self.write_info("Error reading agentUrlPrimary: " + utils.exception_to_string(e))
            return False
    
    def set_config_password(self, pwd):
        self._config_semaphore.acquire()
        try:
            if pwd=="":
                if "config_password" in self._config:
                    del self._config['config_password']
            else:
                self._config['config_password']=hash_password(pwd)
            self._write_config_file()
        finally:
            self._config_semaphore.release()
    
    def check_config_auth(self, usr, pwd):
        cp=self.get_config('config_password', hash_password(""))
        return usr=="admin" and pwd==cp
    
    def set_session_password(self, pwd):
        self._config_semaphore.acquire()
        try:
            if pwd=="":
                if "session_password" in self._config:
                    del self._config['session_password']
            else:
                self._config['session_password']=hash_password(pwd)
            self._write_config_file()
        finally:
            self._config_semaphore.release()
    
    def set_proxy(self, stype,  host,  port,  user,  password):
        if stype is None or (stype!='NONE' and stype!='SYSTEM' and stype!='HTTP' and stype!='SOCKS4' and stype!='SOCKS4A' and stype!='SOCKS5'):
            raise Exception("Invalid proxy type.")
        if (stype=='HTTP' or stype=='SOCKS4' or stype=='SOCKS4A' or stype=='SOCKS5') and host is None:
            raise Exception("Missing host.")
        if (stype=='HTTP' or stype=='SOCKS4' or stype=='SOCKS4A' or stype=='SOCKS5') and port is None:
            raise Exception("Missing port.")
        if port is not None and not isinstance(port, int) :
            raise Exception("Invalid port.")
        self._config_semaphore.acquire()
        try:
            self._config['proxy_type']=stype
            if host is not None:
                self._config['proxy_host']=host
            else:
                self._config['proxy_host']=""
            if port is not None:
                self._config['proxy_port']=port
            else:
                self._config['proxy_port']=""
            if user is not None:
                self._config['proxy_user']=user
            else:
                self._config['proxy_user']=""
            if password is not None:
                self._config['proxy_password']=obfuscate_password(password)
            else:
                self._config['proxy_password']=""
            self._write_config_file()
            self._proxy_info=None #In questo modo lo ricarica
        finally:
            self._config_semaphore.release()
        self._reload_config()
    
    def install_new_agent(self, user, password, name):
        spapp = ";".join(self.get_supported_applications())
        url = self._agent_url_primary + "installNewAgent.dw?user=" + utils.url_parse_quote_plus(user) + "&password=" + utils.url_parse_quote_plus(password) + "&name=" + utils.url_parse_quote_plus(name) + "&osTypeCode=" + str(get_os_type_code()) +"&supportedApplications=" + utils.url_parse_quote_plus(spapp)
        try:
            prop = communication.get_url_prop(url, self.get_proxy_info())
        except:
            raise Exception("CONNECT_ERROR")
        if 'error' in prop:
            raise Exception(prop['error'])
        #Installa chiave
        self._config_semaphore.acquire()
        try:
            self._config['key']=prop['key']
            self._config['password']=obfuscate_password(prop['password'])
            self._config['enabled']=True
            self._write_config_file()
        finally:
            self._config_semaphore.release()
        self._reload_config()
    
    def install_key(self,  code):
        spapp = ";".join(self.get_supported_applications())
        url = self._agent_url_primary + "checkInstallCode.dw?code=" + utils.url_parse_quote_plus(code) + "&osTypeCode=" + str(get_os_type_code()) +"&supportedApplications=" + utils.url_parse_quote_plus(spapp)
        try:
            prop = communication.get_url_prop(url, self.get_proxy_info())
        except:
            raise Exception("CONNECT_ERROR")
        if 'error' in prop:
            raise Exception(prop['error'])
        #Installa chiave
        self._config_semaphore.acquire()
        try:
            self._config['key']=prop['key']
            self._config['password']=obfuscate_password(prop['password'])
            self._config['enabled']=True
            self._write_config_file()
        finally:
            self._config_semaphore.release()
        self._reload_config()
        
    def remove_key(self):
        self._config_semaphore.acquire()
        try:
            bok=False
            if 'key' in self._config:
                del(self._config['key'])
                bok=True
            if 'password' in self._config:
                del(self._config['password'])
                bok=True
            if 'enabled' in self._config:
                del(self._config['enabled'])
                bok=True
            self._write_config_file()
        finally:
            self._config_semaphore.release()
        if not bok:
            raise Exception("KEY_NOT_INSTALLED")
        self._reload_config()
    
    
    def get_config(self, key, default=None):
        self._config_semaphore.acquire()
        try:
            if self._config is not None:
                if key in self._config:
                    return self._config[key]
                else:
                    return default
            else:
                return default
        finally:
            self._config_semaphore.release()
    
    def get_config_str(self, key):
        if (key=="enabled"):
            ve = self.get_config(key)
            if ve is None:
                ve=True
            return bool2str(ve)
        elif (key=="key"):
            v = self.get_config(key)
            if v is None:
                v=""
            return v
        elif (key=="proxy_type"):
            return self.get_config(key, "SYSTEM")
        elif (key=="proxy_host"):
            return self.get_config(key, "")
        elif (key=="proxy_port"):
            v = self.get_config(key)
            if v is None:
                return ""
            else:
                return str(v)
        elif (key=="proxy_user"):
            return self.get_config(key, "")
        elif (key=="monitor_desktop_notification"):
            v = self.get_config(key)
            if v=="visible" or v=="autohide" or v=="none": 
                return self.get_config(key)
            else:
                return "visible"
        elif (key=="monitor_tray_icon"):
            v = self.get_config(key)
            if v is None or v is True:
                v="True"
            else:
                v="False"
            return v
        elif (key=="recovery_session"):
            v = self.get_config(key)
            if v is None or v is True:
                v="True"
            else:
                v="False"
            return v
        elif (key=="unattended_access"):
            v = self.get_config(key)
            if v is None or v is True:
                v="True"
            else:
                v="False"
            return v
        else:
            raise Exception("INVALID_CONFIG_KEY")
    
    def _set_config(self, key, val):
        self._config_semaphore.acquire()
        try:
            self._config[key]=val
            self._write_config_file()
        finally:
            self._config_semaphore.release()

    def set_config_str(self, key, val):
        if (key=="enabled"):
            b=str2bool(val)
            self._set_config(key, b)
            self._reload_config()
        elif (key=="monitor_desktop_notification"):
            if val=="visible" or val=="autohide" or val=="none": 
                self._set_config(key, val)
        elif (key=="monitor_tray_icon"):
            b=str2bool(val)
            self._set_config(key, b)
        elif (key=="unattended_access"):
            b=str2bool(val)
            self._set_config(key, b)
        else:
            raise Exception("INVALID_CONFIG_KEY")
    
    def accept_session(self, sid):
        ses=None
        self._sessions_semaphore.acquire()
        try:
            if sid in self._sessions:
                ses = self._sessions[sid]                
        finally:
            self._sessions_semaphore.release()
        if ses is not None:
            ses.accept()
            
    def reject_session(self, sid):
        ses=None
        self._sessions_semaphore.acquire()
        try:
            if sid in self._sessions:
                ses = self._sessions[sid]
        finally:
            self._sessions_semaphore.release()
        if ses is not None:
            ses.reject()
    
    def _check_hash_file(self, fpath, shash):
        md5 = hashlib.md5()
        with utils.file_open(fpath,'rb') as f: 
            for chunk in iter(lambda: f.read(8192), b''): 
                md5.update(chunk)
        h = md5.hexdigest()
        if h!=shash:
            raise Exception("Hash not valid. (file '{0}').".format(fpath))

    def _unzip_file(self, fpath, unzippath, licpath=None):
        #Decoprime il file
        zfile = zipfile.ZipFile(fpath)
        try:
            for nm in zfile.namelist():
                #print("UNZIP:" + nm)
                npath=unzippath
                if nm.startswith("LICENSES"):
                    if licpath is not None:
                        npath=licpath                
                appnm = nm
                appar = nm.split("/")
                if (len(appar)>1):
                    appnm = appar[len(appar)-1]
                    npath+= nm[0:len(nm)-len(appnm)].replace("/",utils.path_sep)
                if not utils.path_exists(npath):
                    utils.path_makedirs(npath)
                npath+=appnm
                if utils.path_exists(npath):
                    utils.path_remove(npath)
                    if utils.path_exists(npath):
                        raise Exception("Cannot remove file " + npath + ".")
                fd = utils.file_open(npath,"wb")
                fd.write(zfile.read(nm))
                fd.close()
        finally:
            zfile.close()

    def _check_update_file(self, cur_vers, rem_vers, name_file, folder):
        if name_file in cur_vers:
            cv = cur_vers[name_file]
        else:
            cv = "0"
        if name_file + '@version' in rem_vers:
            rv = rem_vers[name_file + '@version']
            if cv!=rv:
                if not utils.path_exists(folder):
                    utils.path_makedirs(folder)
                self.write_info("Downloading file update " + name_file + "...")
                app_url = self._agent_url_node + "getAgentFile.dw?name=" + name_file + "&version=" + rem_vers[name_file + '@version']
                app_file = folder + name_file
                communication.download_url_file(app_url ,app_file, self.get_proxy_info(), None)
                self._check_hash_file(app_file, rem_vers[name_file + '@hash'])
                self._unzip_file(app_file, folder)
                utils.path_remove(app_file)
                cur_vers[name_file]=rv
                
                #TO REMOVE 03/11/2021 KEEP COMPATIBILITY WITH OLD LINUX INSTALLER
                try:
                    if name_file=="agent.zip":
                        if utils.path_exists(folder + "daemon.pyc"):
                            utils.path_remove(folder + "daemon.pyc")                            
                except:
                    None
                
                self.write_info("Downloaded file update " + name_file + ".")
                return True
        return False
    
    def _monitor_update_file_create(self):
        try:
            if not utils.path_exists("monitor.update"):
                stopfile= utils.file_open("monitor.update", "w")
                stopfile.close()
                time.sleep(5)
        except:
            e = utils.get_exception()
            self.write_except(e)
    
    def _monitor_update_file_delete(self):
        try:
            if utils.path_exists("monitor.update"):
                utils.path_remove("monitor.update") 
        except:
            e = utils.get_exception()
            self.write_except(e)
                
    def _check_update(self):
        #IN SVILUPPO NON DEVE AGGIORNARE
        if utils.path_exists(".srcmode"):
            return True
        if self._is_reboot_agent() or self._update_ready:
            return False
        if self._agent_conn_version>=11865:
            if self.get_session_count()>0:
                return True
        #self.write_info("Checking update...")
        try:
            
            #FIX OLD VERSION 2018-12-20
            try:
                if utils.path_exists("agent_listener.pyc"):
                    utils.path_remove("agent_listener.pyc")
                if utils.path_exists("agent_status_config.pyc"):
                    utils.path_remove("agent_status_config.pyc")
                if utils.path_exists("native_linux.pyc"):
                    utils.path_remove("native_linux.pyc")
                if utils.path_exists("native_windows.pyc"):
                    utils.path_remove("native_windows.pyc")
                if utils.path_exists("native_mac.pyc"):
                    utils.path_remove("native_mac.pyc")
                if utils.path_exists("user_interface.pyc"):
                    utils.path_remove("user_interface.pyc")
                if utils.path_exists("gdi.pyc"):
                    utils.path_remove("gdi.pyc")
                if utils.path_exists("messages"):
                    utils.path_remove("messages")
                if utils.path_exists("apps"):
                    utils.path_remove("apps")
                if utils.path_exists("LICENSES" + utils.path_sep + "agent"):
                    utils.path_remove("LICENSES" + utils.path_sep + "agent")
            except:
                None
            #FIX OLD VERSION 2018-12-20
            
            #FIX OLD VERSION 2021-09-22
            try:
                if utils.path_exists("sharedmem.pyc"):
                    utils.path_remove("sharedmem.pyc")
            except:
                None
            #FIX OLD VERSION 2021-09-22
            
            
            #Verifica se è presente un aggiornamento incompleto
            if utils.path_exists("update"):
                self.write_info("Update incomplete: Needs reboot.")
                self._update_ready=True
                return False
                
            #LEGGE 'fileversions.json'
            f = utils.file_open("fileversions.json","rb")
            cur_vers = json.loads(utils.bytes_to_str(f.read(), "utf8"))
            f.close()
            #LEGGE getAgentFile.dw?name=files.xml
            self._agent_url_node=None
            try:
                app_url = self._agent_url_primary + "getAgentFile.dw?name=files.xml"
                if self._agent_key is not None:
                    app_url += "&key=" + self._agent_key 
                rem_vers = communication.get_url_prop(app_url, self.get_proxy_info())
                if "error" in rem_vers:
                    self.write_info("Checking update: Error read files.xml: " + rem_vers['error'])
                    return False
                if "nodeUrl" in rem_vers:
                    self._agent_url_node=rem_vers['nodeUrl']
                if self._agent_url_node is None or self._agent_url_node=="":
                    self.write_info("Checking update: Error read files.xml: Node not available.")
                    return False
            except:
                e = utils.get_exception()
                self.write_info("Checking update: Error read files.xml: " + utils.exception_to_string(e))
                return False            

            #Rimuove updateTMP
            if utils.path_exists("updateTMP"):
                shutil.rmtree("updateTMP")
            
            #UPDATER
            if not self._runonfly:
                upd_libnm=None
                if not self._runonfly:
                    if self._agent_native_suffix is not None:
                        if is_windows():
                            upd_libnm="dwagupd.dll"               
                        elif is_linux():
                            upd_libnm="dwagupd"
                        elif is_mac():
                            upd_libnm="dwagupd"
                        
                    if upd_libnm is not None:
                        if self._check_update_file(cur_vers, rem_vers, "agentupd_" + self._agent_native_suffix + ".zip",  "updateTMP" + utils.path_sep + "native" + utils.path_sep):
                            if utils.path_exists("updateTMP" + utils.path_sep + "native" + utils.path_sep + upd_libnm):
                                if utils.path_exists("native" + utils.path_sep + upd_libnm):
                                    utils.path_remove("native" + utils.path_sep + upd_libnm)
                                shutil.move("updateTMP" + utils.path_sep + "native" + utils.path_sep + upd_libnm, "native" + utils.path_sep + upd_libnm)
                    
            #AGENT
            self._check_update_file(cur_vers, rem_vers, "agent.zip", "updateTMP" + utils.path_sep)
            if not self._runonfly and not self._agent_native_suffix=="linux_generic":
                if self._check_update_file(cur_vers, rem_vers, "agentui.zip", "updateTMP" + utils.path_sep):
                    self._monitor_update_file_create()
            self._check_update_file(cur_vers, rem_vers, "agentapps.zip", "updateTMP" + utils.path_sep)
                                    
            #LIB
            if self._agent_native_suffix is not None:
                if not self._agent_native_suffix=="linux_generic":
                    self._check_update_file(cur_vers, rem_vers, "agentlib_" + self._agent_native_suffix + ".zip",  "updateTMP" + utils.path_sep + "native" + utils.path_sep)                    
                    
            #GUI
            monitor_libnm=None
            if not self._runonfly and not self._agent_native_suffix=="linux_generic":
                if self._agent_native_suffix is not None:
                    if is_windows():
                        monitor_libnm="dwaggdi.dll"                
                    elif is_linux():
                        monitor_libnm="dwaggdi.so"
                    elif is_mac():
                        monitor_libnm="dwaggdi.so"
                #AGGIORNAMENTO LIBRERIE UI
                if monitor_libnm is not None:
                    if self._check_update_file(cur_vers, rem_vers, "agentui_" + self._agent_native_suffix + ".zip",  "updateTMP" + utils.path_sep + "native" + utils.path_sep):
                        self._monitor_update_file_create()
                        if utils.path_exists("updateTMP" + utils.path_sep + "native" + utils.path_sep + monitor_libnm):
                            shutil.move("updateTMP" + utils.path_sep + "native" + utils.path_sep + monitor_libnm, "updateTMP" + utils.path_sep + "native" + utils.path_sep + monitor_libnm + "NEW")
            
            if utils.path_exists("updateTMP"):
                s = json.dumps(cur_vers , sort_keys=True, indent=1)
                f = utils.file_open("updateTMP" + utils.path_sep + "fileversions.json", "wb")
                f.write(utils.str_to_bytes(s,"utf8"))
                f.close()
                shutil.move("updateTMP", "update")
                self.write_info("Update ready: Needs reboot.")
                self._update_ready=True
                return False
        except:
            e = utils.get_exception()
            if utils.path_exists("updateTMP"):
                shutil.rmtree("updateTMP")
            self.write_except(e)
            return False        
        
        #AGGIORNAMENTI LIBRERIE UI
        try:
            monitor_libnm=None
            if is_windows():
                monitor_libnm="dwaggdi.dll"
            elif is_linux():
                monitor_libnm="dwaggdi.so"
            elif is_mac():
                monitor_libnm="dwaggdi.so"
            if monitor_libnm is not None:
                if utils.path_exists("native" + utils.path_sep + monitor_libnm + "NEW"):
                    if utils.path_exists("native" + utils.path_sep + monitor_libnm):
                        utils.path_remove("native" + utils.path_sep + monitor_libnm)
                    shutil.move("native" + utils.path_sep + monitor_libnm + "NEW", "native" + utils.path_sep + monitor_libnm)
        except:
            self.write_except("Update monitor ready: Needs reboot.")
        self._monitor_update_file_delete()
        
        return True
    
    def _reload_config(self):
        self._config_semaphore.acquire()
        try:
            self._cnt = self._cnt_max
            self._cnt_random = 0
            self._breloadconfig=True
        finally:
            self._config_semaphore.release()
    
    def _reload_config_reset(self):
        self._config_semaphore.acquire()
        try:
            self._breloadconfig=False
        finally:
            self._config_semaphore.release()
    
    def _is_reload_config(self):
        self._config_semaphore.acquire()
        try:
            return self._breloadconfig
        finally:
            self._config_semaphore.release()    
    
    def _reboot_os(self):
        self.get_osmodule().reboot()
    
    def _reboot_agent(self):
        self._config_semaphore.acquire()
        try:
            self._cnt = self._cnt_max
            self._cnt_random = 0
            self._brebootagent=True
        finally:
            self._config_semaphore.release()
    
    def _reboot_agent_reset(self):
        self._config_semaphore.acquire()
        try:
            self._brebootagent=False
        finally:
            self._config_semaphore.release()
    
    def _is_reboot_agent(self):
        self._config_semaphore.acquire()
        try:
            return self._brebootagent
        finally:
            self._config_semaphore.release()    
    
    def _reload_agent(self, ms):
        self._config_semaphore.acquire()
        try:
            self._breloadagentcnt=utils.Counter(ms)
        finally:
            self._config_semaphore.release()
    
    def _reload_agent_reset(self):
        self._config_semaphore.acquire()
        try:
            self._breloadagentcnt=None
        finally:
            self._config_semaphore.release()
    
    def _is_reload_agent(self):
        self._config_semaphore.acquire()
        try:
            if self._breloadagentcnt is None:
                return False
            return self._breloadagentcnt.is_elapsed()
        finally:
            self._config_semaphore.release()
    
    def _elapsed_max(self):
        self._config_semaphore.acquire()
        try:
            if self._cnt_random>0:
                self._cnt_random=self._cnt_random-1
                return False
            else:
                if self._cnt >= self._cnt_max:
                    self._cnt_random = random.randrange(0, self._cnt_max) #Evita di avere connessioni tutte assieme
                    self._cnt=0
                    return True
                else:
                    self._cnt+=1
                    return False
        finally:
            self._config_semaphore.release()
    
    def start(self):
        self.write_info("Start agent manager")
        ipc.initialize()
        
        #Start Profiler
        profcfg = None
        try:
            profcfg = read_config_file()
            if not "profiler_enable" in profcfg or not profcfg["profiler_enable"]:
                profcfg = None
        except:
            None
        if profcfg is not None:
            self._agent_profiler = AgentProfiler(profcfg)
            self._agent_profiler.start()
        
        #Load native suffix        
        self._agent_native_suffix=detectinfo.get_native_suffix()

        #Write info nel log
        appuname=None
        try:
            appuname=str(platform.uname())
            p=appuname.find("(")
            if p>=0:
                appuname=appuname[p+1:len(appuname)-1]
        except:
            None
        if appuname is not None:
            self.write_info("System info: " + str(appuname))
        self.write_info("Runtime info: Python " + str(sys.version_info.major) + "." + str(sys.version_info.minor) + "." + str(sys.version_info.micro))
        self.write_info("SSL info: " + communication.get_ssl_info())
        if self._agent_native_suffix is not None:
            self.write_info("Native info: " + self._agent_native_suffix)
        else:
            self.write_info("Native info: unknown")            
        
        if self._runonfly:
            fieldsdef=[]
            fieldsdef.append({"name":"status","size":50})
            fieldsdef.append({"name":"user","size":30})
            fieldsdef.append({"name":"password","size":20})
            fieldsdef.append({"name":"pid","size":20})
            self._runonfly_ipc=ipc.Property()
            self._runonfly_ipc.create("runonfly", fieldsdef)
            self._runonfly_ipc.set_property("status", "CONNECTING")
            self._runonfly_ipc.set_property("user", "")
            self._runonfly_ipc.set_property("password", "")
            self._runonfly_ipc.set_property("pid", str(os.getpid()))
        
        if not self._runonfly or self._runonfly_action is None:
            #Legge pid
            self._check_pid_cnt=0
            self._svcpid=None
            if utils.path_exists("dwagent.pid"):
                try:
                    f = utils.file_open("dwagent.pid")
                    spid = utils.bytes_to_str(f.read())
                    f.close()
                    self._svcpid = int(spid)
                except:
                    None
            
            if self._noctrlfile==False:
                #Crea il file .start
                f = utils.file_open("dwagent.start", 'wb')
                f.close()
            
        
        #GUI LAUNCHER OLD VERSION 03/11/2021 (DO NOT REMOVE)
        if is_mac() and not self._runonfly:
            try:
                self.get_osmodule().init_guilnc(self)
            except:
                ge = utils.get_exception()
                self.write_except(ge, "INIT GUI LNC: ")
                
        #Crea cartelle necessarie
        if not utils.path_exists("native"):
            utils.path_makedirs("native")
                
        #Crea taskpool
        self._task_pool = communication.ThreadPool("Task", 50, 30, self.write_except)

        
        self._update_ready=False        
        try:
            bfirstreadconfig=True
            while self.is_run() is True and not self._is_reboot_agent() and not self._update_ready:
                if self._elapsed_max():
                    communication.release_detected_proxy()
                    if self._runonfly:
                        self._update_onfly_status("CONNECTING")
                    #Load Config file
                    if self._is_reload_config():
                        self._read_config_file()
                        if self._config is not None:
                            self._reload_config_reset()
                            if bfirstreadconfig:
                                bfirstreadconfig=False                                
                                #CARICA DEBUG MODE
                                prfcfg={}
                                self._agent_debug_mode = self.get_config('debug_mode',False)                                
                                if self._agent_debug_mode:
                                    self._logger.set_level(utils.LOGGER_DEBUG)
                                    prfcfg["debug_path"]=utils.os_getcwd()                                    
                                    if not prfcfg["debug_path"].endswith(utils.path_sep):
                                        prfcfg["debug_path"]+=utils.path_sep                                    
                                    prfcfg["debug_indentation_max"] = self.get_config('debug_indentation_max',-1)
                                    prfcfg["debug_thread_filter"] = self.get_config('debug_thread_filter',None)
                                    prfcfg["debug_class_filter"] = self.get_config('debug_class_filter',None)
                                    self._debug_profile=utils.DebugProfile(self,prfcfg)
                                    threading.setprofile(self._debug_profile.get_function)
                            #ssl_cert_required
                            if self.get_config('ssl_cert_required', True)==False:
                                communication.set_cacerts_path("")
                            
                            
                    #Start IPC listener
                    try:
                        if self.get_config('listener_ipc_enable', True):
                            if self._listener_ipc_load:
                                self._listener_ipc_load=False
                                self._listener_ipc=listener.IPCServer(self)
                                self._listener_ipc.start()
                    except:
                        self._listener_ipc = None
                        asc = utils.get_exception()
                        self.write_except(asc, "INIT STATUSCONFIG LISTENER: ")
                            
                    #Start HTTP listener (NOT USED)
                    if not self._runonfly:
                        if self.get_config('listener_http_enable',True):
                            if self._listener_http_load:
                                self._listener_http_load=False
                                try:
                                    httpprt=self.get_config('listen_port')
                                    if httpprt is None:
                                        httpprt=self.get_config('listener_http_port', 7950)
                                    self._listener_http = listener.HttpServer(httpprt, self)
                                    self._listener_http.start()
                                except:
                                    self._listener_http = None
                                    ace = utils.get_exception()
                                    self.write_except(ace, "INIT LISTENER: ")
                            
                    self._reboot_agent_reset()
                    
                    #Legge la configurazione
                    skiponflyretry=False
                    if self._config is not None:
                        self._agent_enabled = self.get_config('enabled',True)
                        if self._agent_enabled is False:
                            if self._agent_status != self._STATUS_DISABLE:
                                self.write_info("Agent disabled")
                                self._agent_status = self._STATUS_DISABLE
                            try:
                                self._close_all_sessions()
                            except:
                                None
                        elif self._load_config() is True:
                            if self._runonfly or (self._agent_key is not None and self._agent_password is not None):
                                self._agent_missauth=False
                                self.write_info("Agent enabled")
                                self._agent_status = self._STATUS_UPDATING
                                #Verifica se ci sono aggiornamenti
                                if self._check_update() is True:
                                    if self._load_agent_properties() is True:
                                        if self._run_agent() is True and self.get_config('enabled',True):
                                            self._cnt = self._cnt_max
                                            self._cnt_random = random.randrange(self._cnt_min, self._cnt_max) #Evita di avere connessioni tutte assieme
                                            skiponflyretry=True
                            elif not self._agent_missauth:
                                self.write_info("Missing agent authentication configuration.")
                                self._agent_missauth=True
                            self._agent_status = self._STATUS_OFFLINE
                    if not self._update_ready and self._runonfly:                    
                        appst=self._runonfly_ipc.get_property("status")
                        if self._runonfly_runcode is not None and appst=="RUNCODE_NOTFOUND":
                            while self.is_run() is True and not self._is_reboot_agent() and not self._update_ready: #ATTENDE CHIUSURA INSTALLER
                                time.sleep(1)
                        elif skiponflyretry==False:
                            self._runonfly_conn_retry+=1
                            self._update_onfly_status("WAIT:" + str(self._runonfly_conn_retry))
                time.sleep(1)
        except KeyboardInterrupt:
            self.destroy()            
        except:
            ex=utils.get_exception()
            self.destroy()
            self.write_except(ex, "AGENT: ")
            
            
        if self._agent_conn_version>=11865:
            self._close_all_sessions()            
        self._task_pool.destroy()
        self._task_pool = None
        
        if self._listener_http is not None:
            try:
                self._listener_http.close()
            except:
                ace = utils.get_exception()
                self.write_except(ace, "TERM LISTENER: ")
        
        if self._listener_ipc is not None:
            try:
                self._listener_ipc.close()
            except:
                ace = utils.get_exception()
                self.write_except(ace, "TERM STATUSCONFIG LISTENER: ")
        
        if self._runonfly_ipc is not None:
            try:
                self._runonfly_ipc.close()
                self._runonfly_ipc=None
            except:
                ace = utils.get_exception()
                self.write_except(ace, "CLOSE RUNONFLY SHAREDMEM: ")
        
        #GUI LAUNCHER OLD VERSION 03/11/2021 (DO NOT REMOVE)
        if is_mac() and not self._runonfly:
            try:
                self.get_osmodule().term_guilnc()
            except:
                ge = utils.get_exception()
                self.write_except(ge, "TERM GUI LNC: ")
        
        if self._agent_profiler is not None:
            self._agent_profiler.destroy()
            self._agent_profiler=None
        
        ipc.terminate()
        self.write_info("Stop agent manager")
        
    def _check_pid(self, pid):
        if self._svcpid is not None:
            if self._svcpid==-1:
                return False
            elif self._check_pid_cnt>15:
                self._check_pid_cnt=0
                if not self._osmodule.is_task_running(pid):
                    self._svcpid=-1
                    return False
            else:
                self._check_pid_cnt+=1
        return True

    def is_run(self):
        if self._runonfly and self._runonfly_action is not None:
            ret = self._update_onfly_status("ISRUN")
            if ret is not None:
                return ret
            return self._brun
        else:
            if self._noctrlfile==True:
                return not self._bstop
            else:
                if utils.path_exists("dwagent.stop"):
                    return False
                if self._svcpid is not None:
                    if not self._check_pid(self._svcpid):
                        return False
                return self._brun

    def destroy(self):
        self._brun=False
    
    def kill(self):
        if self._listener_ipc is not None:
            try:
                self._listener_ipc.close()
            except:
                ace = utils.get_exception()
                self.write_except(ace, "TERM STATUS LISTENER: ")

    
    def write_info(self, msg):
        self._logger.write(utils.LOGGER_INFO,  msg)

    def write_err(self, msg):
        self._logger.write(utils.LOGGER_ERROR,  msg)
        
    def write_debug(self, msg):
        if self._agent_debug_mode:
            self._logger.write(utils.LOGGER_DEBUG,  msg)
    
    def write_except(self, e,  tx = u""):        
        self._logger.write(utils.LOGGER_ERROR,  utils.get_exception_string(e,  tx))
    
    def _update_onfly_status(self,st):
        if self._runonfly:
            if self._runonfly_ipc is not None:
                if st!="ISRUN":
                    self._runonfly_ipc.set_property("status", st)
                    if st=="CONNECTED":
                        if self._runonfly_user is not None and self._runonfly_password is not None:
                            self._runonfly_ipc.set_property("user", self._runonfly_user)
                            self._runonfly_ipc.set_property("password", self._runonfly_password)
                        else:                            
                            self._runonfly_ipc.set_property("user", "")
                            self._runonfly_ipc.set_property("password", "")
                    else:
                        self._runonfly_ipc.set_property("user", "")
                        self._runonfly_ipc.set_property("password", "")
            
            #RIMASTO PER COMPATIBILITA' CON VECCHIE CARTELLE RUNONFLY
            if self._runonfly_action is not None:
                prm=None
                if st=="CONNECTED":
                    if self._runonfly_user is not None and self._runonfly_password is not None:
                        prm={"action":"CONNECTED","user":self._runonfly_user,"password":self._runonfly_password}
                    else:
                        prm={"action":"CONNECTED"}
                elif st=="CONNECTING":
                    prm={"action":"CONNECTING"}
                elif st=="ISRUN":
                    prm={"action":"ISRUN"}
                elif st is not None and st.startswith("WAIT:"):
                    prm={"action":"WAIT", "retry": int(st.split(":")[1])}            
                if prm is not None:
                    return self._runonfly_action(prm)            
        return None
    
    
    def _check_reloads(self):
        cntses=0;
        self._sessions_semaphore.acquire()
        try:
            cntses=len(self._sessions)
            if cntses==0 and self._is_reload_agent():
                return False
        finally:
            self._sessions_semaphore.release()
        self._reload_apps(cntses==0)
        return True
    
    def _update_supported_apps(self,binit):
        if binit:
            self._suppapps=";".join(self.get_supported_applications())
            self._suppappscheckcnt=utils.Counter(20) #20 SECONDS
        else:
            try:
                if self._suppappscheckcnt.is_elapsed():
                    self._suppappscheckcnt.reset()
                    sapps=";".join(self.get_supported_applications())
                    if self._suppapps!=sapps:
                        self._suppapps=sapps
                        m = {
                            'name':  'update', 
                            'supportedApplications': self._suppapps
                        }                
                        self._agent_conn.send_message(m)
            except:
                e = utils.get_exception()
                self.write_except(e)
    
    def _get_sys_info(self):
        m = {
                'osType':  get_os_type(),
                'osTypeCode':  str(get_os_type_code()), 
                'fileSeparator':  utils.path_sep,
                'supportedApplications': self._suppapps,                
            }        
        
        try:
            spv = platform.python_version()
            if spv is not None:
                m['python'] = spv
        except:
            None        
        
        hwnm = detectinfo.get_hw_name()
        if hwnm is not None:
            m["hwName"]=hwnm
        #Send versions info
        if not utils.path_exists(".srcmode"):
            f = utils.file_open("fileversions.json","rb")
            cur_vers = json.loads(utils.bytes_to_str(f.read(),"utf8"))
            f.close()
            for vn in cur_vers:
                if vn[0:4]!="app_":
                    m["version@" + vn]=cur_vers[vn]
        return m

    def _get_prop_conn(self):        
        prop_conn = {}
        prop_conn['host'] = self._agent_server
        prop_conn['port'] = self._agent_port        
        prop_conn['instance'] = self._agent_instance
        prop_conn['localeID'] = 'en_US'
        prop_conn['version'] = self._agent_version
        return prop_conn

    def _run_agent(self):
        self.write_info("Initializing agent (key: " + self._agent_key + ", node: " + self._agent_server + ")..." )
        try:
            appconn = None
            try:
                prop_conn=self._get_prop_conn()
                prop_conn["userName"]='AG' + self._agent_key
                prop_conn["password"]=self._agent_password
                appconn = Connection(self, None, prop_conn, self.get_proxy_info())
                self._agent_conn=AgentConn(self, appconn)                
            except:
                ee = utils.get_exception()
                if appconn is not None:
                    appconn.close()
                raise ee
                                           
            self._node_files_info=None
            self._apps={}
            self._apps_to_reload={}
            self._reload_agent_reset()
            #ready agent
            self._suppapps=";".join(self.get_supported_applications())
            self._update_supported_apps(True)
            m = self._get_sys_info()
            m["name"]="ready"
            m["supportedKeepAlive"]=True
            m["supportedPingStats"]=False
            m["supportedRecovery"]=self.get_config_str('recovery_session')
            self._agent_conn.send_message(m)
            self._agent_status = self._STATUS_ONLINE
            self.write_info("Initialized agent (key: " + self._agent_key + ", node: " + self._agent_server + ")." )
            if self._runonfly:
                self._update_onfly_status("CONNECTED")
                self._runonfly_conn_retry=0
                try:
                    if self._runonfly_runcode is None:
                        self._set_config("preferred_run_user",self._agent_key.split('@')[1])
                except:
                    None
            while self.is_run() and not self._is_reboot_agent() and not self._is_reload_config() and not self._agent_conn.is_close():
                time.sleep(1)
                if not self._check_reloads():
                    break;                
                self._update_supported_apps(False)

            if self._runonfly:
                self._runonfly_user=None
                self._runonfly_password=None
            return True
        except KeyboardInterrupt:
            self.destroy()
            return True
        except:
            inst = utils.get_exception()
            self.write_except(inst)
            return False
        finally:
            if self._agent_conn is not None:
                self.write_info("Terminated agent (key: " + self._agent_key + ", node: " + self._agent_server + ")." )
                appmm = self._agent_conn
                self._agent_conn=None
                appmm.close()                
            self._reload_agent_reset()
            

    def get_supported_applications(self):
        return applications.get_supported(self)
    
    def _update_libs_apps_file(self, tp, name, cur_vers, rem_vers, name_file):
        if name_file in cur_vers:
            cv = cur_vers[name_file]
        else:
            cv = "0"
        rv  = rem_vers[name_file + '@version']
        if cv!=rv:
            if tp=="app":
                self.write_info("App " + name + " updating...")
            elif tp=="lib":
                self.write_info("Lib " + name + " updating...")                
            app_file = name_file
            if utils.path_exists(app_file):
                utils.path_remove(app_file)
            app_url = self._agent_url_node + "getAgentFile.dw?name=" + name_file + "&version=" + rem_vers[name_file + '@version']
            communication.download_url_file(app_url ,app_file, self.get_proxy_info(), None)
            self._check_hash_file(app_file, rem_vers[name_file + '@hash'])
            self._unzip_file(app_file, "")
            utils.path_remove(app_file)
            cur_vers[name_file]=rv
            return True
        return False
    
    def _get_node_files_info(self):
        if self._node_files_info is None:
            try:
                app_url = self._agent_url_node + "getAgentFile.dw?name=files.xml"
                self._node_files_info = communication.get_url_prop(app_url, self.get_proxy_info())
            except:
                e = utils.get_exception()
                self._node_files_info=None
                raise Exception("Error read files.xml: "  + utils.exception_to_string(e))
            if "error" in self._node_files_info:
                self._node_files_info=None
                raise Exception("Error read files.xml: " + self._node_files_info['error'])
        return self._node_files_info
    
    def _update_libs_apps_file_exists(self,arfiles,name):
        for fn in arfiles:
            if fn==name:
                return True
        return False
    
    def _update_libs_apps(self,tp,name):
        if utils.path_exists(".srcmode"):
            if tp=="app":
                self._update_app_dependencies(name)
            elif tp=="lib":
                self._update_lib_dependencies(name)
            return
        try:
            rem_vers = self._get_node_files_info()
            arfiles = rem_vers['files'].split(";")
            if tp=="app":
                zipname="app_" + name + ".zip"
            elif tp=="lib":
                zipname="lib_" + name + "_" + self._agent_native_suffix + ".zip"
            if self._update_libs_apps_file_exists(arfiles, zipname):
                f = utils.file_open("fileversions.json","rb")
                cur_vers = json.loads(utils.bytes_to_str(f.read(),"utf8"))
                f.close()
                if tp=="app" and not utils.path_exists("app_" + name):
                    utils.path_makedirs("app_" + name)
                bup = self._update_libs_apps_file(tp, name, cur_vers, rem_vers, zipname)                
                if bup:                
                    s = json.dumps(cur_vers , sort_keys=True, indent=1)
                    f = utils.file_open("fileversions.json", "wb")
                    f.write(utils.str_to_bytes(s,"utf8"))
                    f.close()
                    if tp=="app":
                        self.write_info("App " + name + " updated.")
                    elif tp=="lib":
                        self.write_info("Lib " + name + " updated.")
                if tp=="app":
                    self._update_app_dependencies(name)
                elif tp=="lib":
                    self._update_lib_dependencies(name)

            else:
                None #OS not needs of this lib or app
        except:
            e = utils.get_exception()
            raise Exception("Error update " + tp + " " + name + ": " + utils.exception_to_string(e) + " Please reboot the agent or OS.")
    
    def _update_lib_dependencies(self,name):
        appcnf=native.get_library_config(name)
        if "lib_dependencies" in appcnf:
            for ln in appcnf["lib_dependencies"]:
                self._init_lib(ln)
    
    def _init_lib(self, name):
        try:
            if name not in self._libs:
                self._update_libs_apps("lib",name)
                appcnf=native.get_library_config(name)
                if appcnf is not None:
                    appcnf["refcount"]=0
                    self._libs[name]=appcnf                    
        except:    
            e = utils.get_exception()        
            raise e
    
    def load_lib(self, name):
        self._libs_apps_semaphore.acquire()
        try:            
            self._init_lib(name)
            if name in self._libs:
                cnflib=self._libs[name]
                if "filename_" + native.get_suffix() in cnflib:
                    if cnflib["refcount"]==0:
                        if "lib_dependencies" in cnflib:
                            for ln in cnflib["lib_dependencies"]:
                                self.load_lib(ln)
                        fn = cnflib["filename_" + native.get_suffix()]
                        cnflib["refobject"]=native._load_lib_obj(fn)
                    cnflib["refcount"]+=1
                    self.write_info("Lib " + name + " loaded.")
                    return cnflib["refobject"]
            return None
        except:
            e = utils.get_exception()
            self.write_except("Lib " + name + " load error: " + utils.exception_to_string(e))
            raise e
        finally:
            self._libs_apps_semaphore.release()        
        
    def unload_lib(self, name):
        self._libs_apps_semaphore.acquire()
        try:
            if name in self._libs:
                cnflib=self._libs[name]
                if "filename_" + native.get_suffix() in cnflib:
                    cnflib["refcount"]-=1
                    if cnflib["refcount"]==0:
                        native._unload_lib_obj(cnflib["refobject"])
                        if "lib_dependencies" in cnflib:
                            for ln in cnflib["lib_dependencies"]:
                                self.unload_lib(ln)
                        cnflib["refobject"]=None
                        del self._libs[name]
                        self.write_info("Lib " + name + " unloaded.")
        except:
            e = utils.get_exception()
            self.write_except("Lib " + name + " unload error: " + utils.exception_to_string(e))
            raise e
        finally:
            self._libs_apps_semaphore.release()
    
    
    def _get_app_config(self,name):
        pthfc="app_" + name + utils.path_sep + "config.json"
        if utils.path_exists(".srcmode"):
            pthfc=".." + utils.path_sep + pthfc
        if utils.path_exists(pthfc):
            f = utils.file_open(pthfc,"rb")
            conf = json.loads(utils.bytes_to_str(f.read(),"utf8"))
            f.close()
            return conf
        else:
            return None
    
    def _reload_apps(self,bforce):
        if utils.path_exists(".srcmode"):
            return
        #IF bforce=True DESTROY APP AND DEPENDENCIES
        #IF bforce=False DESTROY APP ONLY IF DEPENDENCIES ARE UNLOADED
        torem = {}
        self._libs_apps_semaphore.acquire()
        try:
            if len(self._apps_to_reload)>0:
                for appmn in self._apps_to_reload:
                    if self._apps_to_reload[appmn]==True:
                        self._reload_app(torem,appmn,bforce)
        except:
            e = utils.get_exception()         
            self.write_except(e)
        finally:
            try:
                if bforce:                        
                    self._apps_to_reload={}
                for appmn in torem:
                    if torem[appmn]==True:
                        if not bforce:                        
                            del self._apps_to_reload[appmn]
                        if appmn in self._apps:
                            del self._apps[appmn]                                
                
            finally:
                self._libs_apps_semaphore.release()
            
    
    def _set_reload_apps_with_lib_deps(self,libname):
        for appmn in self._apps:
            conf = self._get_app_config(appmn)
            if conf is not None:
                if "lib_dependencies" in conf:
                    for ap in conf["lib_dependencies"]:
                        if ap==libname:
                            self._apps_to_reload[appmn]=True
                            break
    
    def _reload_apps_with_lib_deps(self,torem,libname):
        #IF bforce=True DESTROY APP AND DEPENDENCIES
        #IF bforce=False DESTROY APP ONLY IF DEPENDENCIES ARE UNLOADED
        for appmn in self._apps:
            if not appmn in torem:
                conf = self._get_app_config(appmn)
                if conf is not None:
                    if "lib_dependencies" in conf:
                        for ap in conf["lib_dependencies"]:
                            if ap==libname:
                                self._reload_app(torem,appmn,True)
    
    def _reload_app(self,torem,name,bforce):
        #IF bforce=True DESTROY APP AND DEPENDENCIES
        #IF bforce=False DESTROY APP ONLY IF DEPENDENCIES ARE UNLOADED
        if not name in torem:
            torem[name]=True
            if name in self._apps:
                conf = self._get_app_config(name)
                if conf is not None:
                    if "lib_dependencies" in conf:
                        for ap in conf["lib_dependencies"]:
                            if bforce:
                                self._reload_apps_with_lib_deps(torem,ap)
                            else:
                                if ap in self._libs:
                                    cnflib=self._libs[ap]
                                    if cnflib["refcount"]>0:
                                        torem[name]=False
                                        return
                torem[name]=self._unload_app(name,bforce)                    
    
    def _update_app_dependencies(self,name):
        conf = self._get_app_config(name)
        if conf is not None:            
            if "lib_dependencies" in conf:
                for ln in conf["lib_dependencies"]:
                    self._init_lib(ln)
            if "app_dependencies" in conf:
                for ap in conf["app_dependencies"]:
                    self._init_app(ap)
    
    def _unload_app(self, name, bforce):
        try:
            md = self._apps[name]        
            func_destroy = getattr(md,  'destroy')
            bret = func_destroy(bforce)
            if bret:
                self.write_info("App " + name + " unloaded.")
            return bret
        except AttributeError:
            return True
        except:
            e = utils.get_exception()
            self.write_except("App " + name + " unload error: " + utils.exception_to_string(e))
            return False
                   
    def _init_app(self,name):
        if name not in self._apps:
            self._update_libs_apps("app",name)
            func=None
            try:
                utils.unload_package("app_" + name)
                objlib = importlib.import_module("app_" + name)
                func = getattr(objlib, 'get_instance', None)
                ret = func(self)
                self._apps[name]=ret;
                self.write_info("App " + name + " loaded.")
            except:
                e = utils.get_exception()
                raise Exception("App " + name + " load error: " + utils.exception_to_string(e))
    
    def get_app(self,name):
        self._libs_apps_semaphore.acquire()
        try:
            self._init_app(name)
            return self._apps[name]
        except:
            e = utils.get_exception()
            self.write_except(e)
            raise e
        finally:
            self._libs_apps_semaphore.release()
    
    
    def _unload_apps(self):
        self._libs_apps_semaphore.acquire()
        try:
            for k in self._apps:
                self._unload_app(k,True)
            self._apps={}
        finally:
            self._libs_apps_semaphore.release()
            
    def _fire_close_conn_apps(self, idconn):
        for k in self._apps:
            md = self._apps[k]
            try:
                func = None
                try:
                    func = getattr(md,  'on_conn_close')
                except AttributeError:
                    None
                if func is not None:
                    func(idconn)
            except:
                e = utils.get_exception()
                self.write_except(e)
    
    def _close_all_sessions(self):
        self._sessions_semaphore.acquire()
        try:
            for sid in self._sessions.keys():
                try:
                    ses = self._sessions[sid]
                    ses.close()
                    self._fire_close_conn_apps(sid)
                except:
                    ex = utils.get_exception()
                    self.write_err(utils.exception_to_string(ex))
            self._sessions={}
        finally:
            self._sessions_semaphore.release()        
        self._unload_apps()

    def open_session(self, msg):
        resp = {}
        supp_rcr = self.get_config('recovery_session',True)
        conn_rcr = None 
        appconn = None
        try:
            prop_conn = {}
            prop_conn['host'] = msg["connServer"]
            prop_conn['port'] = msg["connPort"]            
            prop_conn['instance'] = msg["connInstance"]
            prop_conn['localeID'] = 'en_US'
            prop_conn['version'] = msg["connVersion"]
            prop_conn['userName'] = msg["connUser"]
            prop_conn['password'] = msg["connPassword"]
            if supp_rcr==True:
                if "connRecoveryID" in msg:
                    conn_rcr=ConnectionRecovery(msg["connRecoveryID"])                    
                if "connRecoveryTimeout" in msg:
                    conn_rcr.set_timeout(int(msg["connRecoveryTimeout"]))
                if "connRecoveryIntervall" in msg:
                    conn_rcr.set_intervall(int(msg["connRecoveryIntervall"]))
                if "connRecoveryMaxAttempt" in msg:
                    conn_rcr.set_max_attempt(int(msg["connRecoveryMaxAttempt"]))
            appconn = Connection(self, None, prop_conn, self.get_proxy_info())
            sinfo=None
            self._sessions_semaphore.acquire()
            try:
                while True:
                    sid = generate_key(30)
                    if sid not in self._sessions:
                        sinfo=Session(self,appconn,sid,msg)
                        self._sessions[sid]=sinfo
                        resp["idSession"]=sid
                        resp["waitAccept"]=sinfo.get_wait_accept()
                        resp["passwordRequest"]=sinfo.get_password_request()      
                        if conn_rcr is not None:
                            conn_rcr.set_msg_log("session (id: " + sinfo.get_idsession() + ", node: " + sinfo.get_host()+")")
                            appconn.set_recovery_conf(conn_rcr)
                        break
            finally:
                self._sessions_semaphore.release()
        except:
            ee = utils.get_exception()
            if appconn is not None:
                appconn.close()
            raise ee        
        resp["systemInfo"]=self._get_sys_info()
        resp["supportedRecovery"]=supp_rcr
        return resp
        

    def close_session(self, ses):
        bcloseapps=False
        self._sessions_semaphore.acquire()
        try:
            sid = ses.get_idsession()
            if sid in self._sessions:
                del self._sessions[sid]                
                self._fire_close_conn_apps(sid)
            if len(self._sessions)==0:
                bcloseapps=True
        finally:
            self._sessions_semaphore.release()
        if bcloseapps:
            self._unload_apps()
        
    
    def get_app_permission(self,cinfo,name):
        prms = cinfo.get_permissions()
        if "applications" in prms:
            for a in prms["applications"]:
                if name == a["name"]:
                    return a
        return None
    
    def has_app_permission(self,cinfo,name):
        prms = cinfo.get_permissions()
        if prms["fullAccess"]:
            return True
        else:
            return self.get_app_permission(cinfo,name) is not None
    
    def invoke_app(self, app_name, cmd_name, cinfo, params):
        objmod = self.get_app(app_name)
        if not objmod.has_permission(cinfo):
            raise Exception('Permission denied to invoke app ' + app_name + '.')
        func=None
        try:
            func = getattr(objmod, 'req_' + cmd_name)
        except AttributeError:
            raise Exception('Command ' + cmd_name + ' not found in app ' + app_name + '.')
        else:
            ret = func(cinfo, params)
            return ret

class Connection():
    def __init__(self, agent, cpool, prop_conn, proxy_info):
        self._id=None
        self._evt_on_data=None
        self._evt_on_close=None
        self._evt_on_recovery=None
        self._evt_on_except=None        
        self._agent=agent
        self._cpool=cpool
        self._prop_conn=prop_conn
        self._proxy_info=proxy_info
        self._semaphore = threading.Condition()
        self._recovering=False
        self._recovery_conf=None
        self._destroy=False
        self._raw = communication.Connection({"on_data": self._on_data, "on_except": self._on_except, "on_close":self._on_close})
        self._raw.open(prop_conn, proxy_info)
    
    def send(self,data):
        self._raw.send(data)
    
    def set_events(self,evts):
        if evts is None:
            evts={}
        if "on_data" in evts:
            self._evt_on_data=evts["on_data"]
        else:
            self._evt_on_data=None
        if "on_close" in evts:
            self._evt_on_close=evts["on_close"]
        else:
            self._evt_on_close=None        
        if "on_recovery" in evts:
            self._evt_on_recovery=evts["on_recovery"]
        else:
            self._evt_on_recovery=None
        if "on_except" in evts:
            self._evt_on_except=evts["on_except"]
        else:
            self._evt_on_except=None
        if self._raw.is_close():
            raise Exception("Connection close.")
    
    def set_recovery_conf(self, rconf):
        self._recovery_conf=rconf
            
    def _on_data(self, dt):
        if self._evt_on_data is not None:
            self._evt_on_data(dt)
    
    def _set_recovering(self, r, d):
        bcloseraw=False
        self._semaphore.acquire()
        try:
            self._recovering=r
            if d is not None:
                if self._destroy==True and d==False:
                    bcloseraw=True
                else:
                    self._destroy=d
            self._semaphore.notify_all()
        finally:
            self._semaphore.release()
        if bcloseraw:
            self._raw.close()
    
    def wait_recovery(self):
        self._semaphore.acquire()
        try:
            self._semaphore.wait(0.5)
            while not self._destroy and self._recovering:
                self._semaphore.wait(0.2)
            return not self._destroy
        finally:
            self._semaphore.release()
    
    def _on_close(self):
        #RECOVERY CONN
        self._set_recovering(True,None)
        brecon=False
        breconmsg=False
        rconf = self._recovery_conf
        if rconf is not None and self._raw.is_connection_lost() and self._raw.is_close():
            breconmsg=True
            self._agent.write_info("Recovering " + rconf.get_msg_log() + "...")
            cntretry=utils.Counter()
            cntwait=utils.Counter()
            appattemp=0
            while not cntretry.is_elapsed(rconf.get_timeout()) and ((rconf.get_max_attempt()==0) or (appattemp<rconf.get_max_attempt())):
                if cntwait.is_elapsed(rconf.get_intervall()):
                    cntwait.reset()
                    try:
                        appattemp+=1
                        prop = self._prop_conn.copy()
                        prop['userName'] = "RECOVERY:" + prop['userName']
                        prop['password'] = rconf.get_id()
                        appraw = communication.Connection({"on_data": self._on_data, "on_except": self._on_except, "on_close":self._on_close})
                        appraw.open(prop, self._proxy_info)
                        self._raw=appraw
                        brecon = True
                        break
                    except:
                        None
                else:
                    time.sleep(0.2)
                self._semaphore.acquire()
                try:
                    if self._destroy==True:
                        return
                finally:
                    self._semaphore.release()
        
        if not brecon:
            if breconmsg:
                self._agent.write_info("Recovery " + rconf.get_msg_log() + " failed.")
            self._set_recovering(False,True)
            if self._cpool is not None:
                self._cpool.close_connection(self)
                self._cpool=None
            if self._evt_on_close is not None:
                self._evt_on_close()            
        else:
            if breconmsg:
                self._agent.write_info("Recovered " + rconf.get_msg_log() + ".")
            if self._evt_on_recovery is not None:
                self._evt_on_recovery()
            self._set_recovering(False,False)
                
    def _on_except(self,e):        
        if self._evt_on_except is not None:
            self._evt_on_except(e)
        else:
            self._agent.write_except(e)
    
    def is_close(self):
        self._semaphore.acquire()
        try:
            return self._destroy
        finally:
            self._semaphore.release()        
    
    def close(self):
        self._set_recovering(False,True)
        if self._cpool is not None:
            self._cpool.close_connection(self)
            self._cpool=None
        self._raw.close()
        

class ConnectionRecovery():
    def __init__(self, rid):
        self._id=rid
        self._timeout=0
        self._intervall=0 #RANDOM
        self._max_attempt=0 
        self._msg_log=None
    
    def get_msg_log(self):
        if self._msg_log is None:
            return "connection"
        else:
            return self._msg_log
    
    def set_msg_log(self, m):
        self._msg_log=m
    
    def get_id(self):
        return self._id
    
    def get_timeout(self):
        return self._timeout
    
    def set_timeout(self, t):
        self._timeout=t
    
    def get_intervall(self):
        if self._intervall<=0:
            if self._timeout>1:
                return random.randint(1, self._timeout)
            else:
                return 1
        return self._intervall
        
    def set_intervall(self,i):
        self._intervall=i
    
    def get_max_attempt(self):
        return self._max_attempt
        
    def set_max_attempt(self,a):
        self._max_attempt=a
        

class ConnectionPool():
    
    def __init__(self, agent, prop_conn, proxy_info):
        self._agent=agent
        self._prop_conn=prop_conn
        self._proxy_info=proxy_info
        self._list={}
        self._semaphore=threading.Condition()
        self._bdestory=False
    
    def get_connection(self, sid):
        if self._bdestory:
            return None
        conn=None
        self._semaphore.acquire()
        try:
            if sid in self._list:
                conn=self._list[sid]            
        finally:
            self._semaphore.release()
        return conn
    
    def open_connection(self, sid, usn, pwd):
        if self._bdestory:
            raise Exception("ConnectionPool destroyed")
        conn=None
        self._semaphore.acquire()
        try:
            if sid in self._list:
                raise Exception("id connection already exists.")
            prop_conn=self._prop_conn.copy()
            prop_conn["userName"]=usn
            prop_conn["password"]=pwd
            conn = Connection(self._agent,self,prop_conn,self._proxy_info)
            conn._id=sid
            self._list[sid]=conn
            #print("ConnectionPool: " + str(len(self._list)) + "   (open_connection)")
        finally:
            self._semaphore.release()
        return conn       
    
    def close_connection(self,conn):
        self._semaphore.acquire()
        try:
            if conn._id is not None:
                if conn._id in self._list:
                    del self._list[conn._id]
                    conn._id=None
                #print("ConnectionPool: " + str(len(self._list)) + "   (close_connection)")
        finally:
            self._semaphore.release()
    
    def destroy(self):
        if self._bdestory:
            return
        self._bdestory=True
        self._semaphore.acquire()
        try:
            ar=self._list.copy()
        finally:
            self._semaphore.release()
        for sid in ar:
            self._list[sid].close()
        self._list={}

class Message():
    
    def __init__(self, agent, conn):
        self._agent=agent
        self._temp_msg={"length":0, "read":0, "data":bytearray()}
        self._bwsendcalc=communication.BandwidthCalculator()
        self._lastacttm=time.time()
        self._lastreqcnt=0
        self._send_response_recovery=[]
        self._conn=conn
        self._conn.set_events({"on_close" : self._on_close, "on_data" : self._on_data, "on_recovery": self._on_recovery})
            
    def get_last_activity_time(self):
        return self._lastacttm
    
    def _set_last_activity_time(self):
        self._lastacttm=time.time()
    
    def on_data_message(self, data):    
        p=0
        while p<len(data):
            dt = None
            self._conn._semaphore.acquire()
            try:
                if self._temp_msg["length"]==0:
                    self._temp_msg["length"] = struct.unpack("!I",data[p:p+4])[0]
                    p+=4
                c=self._temp_msg["length"]-self._temp_msg["read"]
                rms=len(data)-p
                if rms<c:
                    c=rms
                self._temp_msg["data"]+=data[p:p+c]
                self._temp_msg["read"]+=c            
                p=p+c
                if self._temp_msg["read"]==self._temp_msg["length"]:
                    dt = self._temp_msg["data"]
            finally:
                self._conn._semaphore.release()
            if dt is not None:
                try:
                    dt = utils.zlib_decompress(dt)
                    msg=json.loads(dt.decode("utf8"))
                    if self._check_recovery_msg(msg):
                        self._agent._task_pool.execute(self._fire_msg, msg)
                except:
                    e = utils.get_exception()
                    self._agent.write_except(e)
                finally:
                    self._clear_temp_msg()
    
    def _check_recovery_msg(self,msg):
        if "requestCount" in msg:
            self._conn._semaphore.acquire()
            try:
                rc = msg["requestCount"]
                if rc>self._lastreqcnt+1:
                    msgskip={}
                    msgskip["requestKey"]="SKIP"
                    msgskip["begin"]=self._lastreqcnt+1
                    msgskip["end"]=rc-1
                    self._agent._task_pool.execute(self.send_message, msgskip)
                self._lastreqcnt=rc                
            finally:
                self._conn._semaphore.release()
        if msg["name"]=="recovery":
            if "cntRequestReceived" in msg:
                cntRequestReceived=msg["cntRequestReceived"];
                self._conn._semaphore.acquire()
                try:
                    appar=[]
                    for o in self._send_response_recovery: 
                        if o["requestCount"]>cntRequestReceived:
                            appar.append(o)
                    self._send_response_recovery=appar
                finally:
                    self._conn._semaphore.release()
            if "status" in msg and msg["status"]=="end":
                appar=[]
                self._conn._semaphore.acquire()
                try:                    
                    appar=[]
                    for o in self._send_response_recovery: 
                        appar.append(o)
                finally:
                    self._conn._semaphore.release()
                if len(appar)>0:
                    self._agent._task_pool.execute(self._send_message_recovery, appar)
            if "requestKey" in msg:
                resp={}
                resp["requestKey"]=msg["requestKey"]
                if "requestCount" in msg:
                    resp["requestCount"] = msg["requestCount"]
                self._agent._task_pool.execute(self.send_message, resp)            
            return False
        return True
    
    def _send_message_recovery(self,ar):
        for msg in ar:
            self.send_message(msg)
    
    def _on_data(self,data):
        self._set_last_activity_time()
        self.on_data_message(data)
    
    def _clear_temp_msg(self):
        self._conn._semaphore.acquire()
        try:
            self._temp_msg["length"]=0
            self._temp_msg["read"]=0
            self._temp_msg["data"]=bytearray()
        finally:
            self._conn._semaphore.release()
            
    def _on_recovery(self):
        self._clear_temp_msg()
    
    def _fire_msg(self, msg):
        None
    
    def get_send_buffer_size(self):
        return self._bwsendcalc.get_buffer_size()
    
    def _send_conn(self,conn,dt):
        pos=0
        tosnd=len(dt)
        while tosnd>0:
            bfsz=self.get_send_buffer_size()
            if bfsz>=tosnd:
                if pos==0:
                    conn.send(dt)
                else:
                    conn.send(utils.buffer_new(dt,pos,tosnd))
                self._bwsendcalc.add(tosnd)
                tosnd=0
            else:                
                conn.send(utils.buffer_new(dt,pos,bfsz))
                self._bwsendcalc.add(bfsz)
                tosnd-=bfsz
                pos+=bfsz
                
    
    def send_message(self,msg):
        while True:
            try:
                
                dt = utils.zlib_compress(bytearray(json.dumps(msg),"utf8"))
                ba=bytearray(struct.pack("!I",len(dt)))
                ba+=dt
                self._send_conn(self._conn, ba)
                break
            except:
                e = utils.get_exception()
                if not self._conn.wait_recovery():
                    raise e
           
    def send_response(self,msg,resp):
        m = {
                'name': 'response', 
                'requestKey':  msg['requestKey'], 
                'content':  resp
            }
        if "module" in msg:
            m["module"] = msg["module"]
        if "command" in msg:
            m["command"] = msg["command"]
        if "requestCount" in msg:
            m["requestCount"] = msg["requestCount"]
            self._conn._semaphore.acquire()
            try:
                self._send_response_recovery.append(m)
            finally:
                self._conn._semaphore.release()        
        self.send_message(m)
    
    def send_response_error(self,msg,scls,serr):
        m = {
                'name': 'error', 
                'requestKey':  msg['requestKey'], 
                'class':  scls, 
                'message':  serr
            }
        if "module" in msg:
            m["module"] = msg["module"]
        if "command" in msg:
            m["command"] = msg["command"]
        if "requestCount" in msg:
            m["requestCount"] = msg["requestCount"]
            self._conn._semaphore.acquire()
            try:
                self._send_response_recovery.append(m)
            finally:
                self._conn._semaphore.release()        
        self.send_message(m)
    
    def is_close(self):
        return self._conn.is_close()
    
    def _on_close(self):
        None
        
    def close(self):
        self._conn.close()        


class AgentConnPingStats(threading.Thread):
    def __init__(self, ac, msg):
        threading.Thread.__init__(self, name="AgentConnPingStats")
        self._agent_conn=ac
        self._msg=msg
        
    def run(self):
        nodes=self._msg["nodes"]
        resp=[]
        for itm in nodes:
            tm = communication.ping_url(itm["pingUrl"], self._agent_conn._agent.get_proxy_info())
            resp.append({"id":itm["id"],"ping":tm})
        m = {
            'name': 'pingStats',
            'stats': resp
        }
        self._agent_conn.send_message(m)
        self._agent_conn=None
        self._nodes=None

class AgentConn(Message):    
    
    def __init__(self, agent, conn):
        Message.__init__(self, agent, conn)
        
    def _fire_msg(self, msg):
        try:
            #if self._agent._connection is not None:
            #    return
            resp = None
            msg_name = msg["name"]
            if msg_name=="recoveryInfo":
                conn_rcr=None
                if "id" in msg:
                    conn_rcr=ConnectionRecovery(msg["id"])                    
                    conn_rcr.set_msg_log("agent (key: " + self._agent._agent_key + ", node: " + self._agent._agent_server + ")")                    
                if "timeout" in msg:
                    conn_rcr.set_timeout(int(msg["timeout"]))
                if "intervall" in msg:
                    conn_rcr.set_intervall(int(msg["intervall"]))
                if "attempt" in msg:
                    conn_rcr.set_max_attempt(int(msg["attempt"]))
                if conn_rcr is not None:
                    self._conn.set_recovery_conf(conn_rcr)
            elif msg_name=="updateInfo":
                if "agentGroup" in msg:
                    self._agent._agent_group=msg["agentGroup"]
                if "agentName" in msg:
                    self._agent._agent_name=msg["agentName"]
            elif msg_name=="keepAlive":
                m = {
                    'name':  'okAlive' 
                }
                self.send_message(m)
            elif msg_name=="pingStats":
                pstat=AgentConnPingStats(self, msg)
                pstat.start()                
            elif msg_name=="rebootOS":
                self._agent._reboot_os()
            elif msg_name=="reboot":
                self._agent._reboot_agent()
            elif msg_name=="reload":
                self._agent.write_info("Request reload Agent.")
                #WAIT RANDOM TIME BEFORE TO REBOOT AGENT
                wtime=random.randrange(0, 12*3600) # 12 HOURS
                self._agent._reload_agent(wtime)
            elif msg_name=="reloadApps":
                self._agent.write_info("Request reload Apps: " + msg["appsUpdated"] + ".")
                self._agent._libs_apps_semaphore.acquire()
                try:
                    self._agent._node_files_info=None
                    arAppsUpdated = msg["appsUpdated"].split(";")
                    for appmn in arAppsUpdated:
                        self._agent._apps_to_reload[appmn]=True
                finally:
                    self._agent._libs_apps_semaphore.release()
            elif msg_name=="reloadLibs":
                self._agent.write_info("Request reload Libs: " + msg["libsUpdated"] + ".")
                self._agent._libs_apps_semaphore.acquire()
                try:
                    self._agent._node_files_info=None
                    arLibsUpdated = msg["libsUpdated"].split(";")
                    for libmn in arLibsUpdated:
                        self._agent._set_reload_apps_with_lib_deps(libmn)
                finally:
                    self._agent._libs_apps_semaphore.release()
            elif msg_name=="openSession":
                resp=self._agent.open_session(msg)
            if resp is not None:
                self.send_response(msg, resp)
        except:
            e = utils.get_exception()
            self._agent.write_except(e)
            if 'requestKey' in msg:
                m = {
                    'name': 'error' , 
                    'requestKey':  msg['requestKey'] , 
                    'class':  e.__class__.__name__ , 
                    'message':  utils.exception_to_string(e)
                }
                self.send_message(m)
                #if self._agent._connection is not None:
                    #self.send_message(self._connection,m)

class Session(Message):
    
    def __init__(self, agent, conn, idses, msg):
        self._bclose = False
        self._idsession = idses
        self._init_time = time.time()
        self._host=conn._prop_conn["host"]
        self._permissions = json.loads(msg["permissions"])
        self._password = agent.get_config('session_password')
        if self._password=="":
            self._password=None
        self._password_attempt = 0
        self._wait_accept = not agent.get_config("unattended_access", True)
        self._ipaddress = ""        
        if "ipAddress" in msg:
            self._ipaddress = msg["ipAddress"]
        self._country_code = ""
        if "countryCode" in msg:
            self._country_code = msg["countryCode"]
        self._country_name = ""
        if "countryName" in msg:
            self._country_name = msg["countryName"]
        self._user_name = ""
        if "userName" in msg:
            self._user_name = msg["userName"]
        self._access_type = ""
        if "accessType" in msg:
            self._access_type = msg["accessType"]            
        
        self._activities = {}
        self._activities["screenCapture"] = False
        self._activities["shellSession"] = False
        self._activities["downloads"] = 0
        self._activities["uploads"] = 0
        self._cpool = ConnectionPool(agent,conn._prop_conn,conn._proxy_info)
        Message.__init__(self, agent, conn)
        self._log_open()


    def accept(self):
        if self._wait_accept:
            m = {
                'name':  'sessionAccepted' 
            }
            self.send_message(m)
            self._wait_accept=False
            self._log_open()            


    def reject(self):
        if self._wait_accept:
            m = {
                'name':  'sessionRejected' 
            }
            self.send_message(m)

    def get_idsession(self):
        return self._idsession
    
    def get_init_time(self):
        return self._init_time
    
    def get_access_type(self):
        return self._access_type
    
    def get_user_name(self):
        return self._user_name
    
    def get_ipaddress(self):
        return self._ipaddress
    
    def get_host(self):
        return self._host
        
    def get_password_request(self):
        return self._password is not None
    
    def get_wait_accept(self):
        return self._wait_accept
    
    def get_permissions(self):
        return self._permissions
    
    def inc_activities_value(self, k):
        self._agent._sessions_semaphore.acquire()
        try:
            self._activities[k]+=1
        finally:
            self._agent._sessions_semaphore.release()
    
    def dec_activities_value(self, k):
        self._agent._sessions_semaphore.acquire()
        try:
            self._activities[k]-=1
        finally:
            self._agent._sessions_semaphore.release()
    
    def get_activities(self):
        return self._activities
        
    def _fire_msg(self,msg):
        try:
            msg_name = msg["name"]
            if self._password is not None and msg_name!="keepalive" and msg_name!="checkpassword":
                if 'requestKey' in msg:
                    self.send_response(msg,"P:null")                    
                else:
                    raise Exception("session not accepted")
            if msg_name=="checkpassword":
                sresp="E"
                if self._password is None:
                    sresp="K"
                elif self._password==hash_password(msg["password"]):
                    sresp="K"
                    self._password=None
                    self._password_attempt=0
                    self._log_open()
                else:
                    self._password_attempt+=1
                    if self._password_attempt>=5:
                        sresp="D"
                m = {
                    'name': 'response' , 
                    'requestKey':  msg['requestKey'] , 
                    'content':  sresp
                }
                self.send_message(m)                
            elif self._wait_accept and msg_name!="keepalive":
                if 'requestKey' in msg:
                    self.send_response(msg,"W:null")                    
                else:
                    raise Exception("session not accepted")
            elif msg_name=="request":
                self.send_response(msg,self._request(msg))
            elif msg_name=="keepalive":
                m = {
                    'name': 'response' , 
                    'requestKey':  msg['requestKey'] , 
                    'message':  "okalive"
                }
                self.send_message(m)
            elif msg_name=="openConnection":
                self._cpool.open_connection(msg["id"], msg["userName"], msg["password"])
                m = {
                    'name': 'response', 
                    'requestKey':  msg["requestKey"], 
                }
                self.send_message(m)
            elif msg_name=="download":
                self.send_message(self._download(msg))
            elif msg_name=="upload":
                self.send_message(self._upload(msg))
            elif msg_name=="websocket":
                self.send_message(self._websocket(msg))
            elif msg_name=="websocketsimulate":
                self.send_message(self._websocketsimulate(msg))
            else:
                raise Exception("Invalid message name: " + msg_name)                
        except:
            e = utils.get_exception()
            self._agent.write_except(e)
            if 'requestKey' in msg:
                self.send_response_error(msg,e.__class__.__name__ ,utils.exception_to_string(e))
            
    def _request(self, msg):
        resp = ""
        try:
            app_name = msg["module"]
            cmd_name = msg["command"]
            params = {}
            params["requestKey"]=msg['requestKey']
            sck = "parameter_";
            for key in msg:
                if key.startswith(sck):
                    params[key[len(sck):]]=msg[key]
            resp=self._agent.invoke_app(app_name, cmd_name, self, params)
            if resp is not None:
                resp = ":".join(["K", resp])
            else:
                resp = "K:null"
        except:
            e = utils.get_exception()
            m = utils.exception_to_string(e)
            self._agent.write_debug(m)
            resp=  ":".join(["E", m])
        return resp        
    
    def _websocket(self, msg):        
        rid=msg["idRaw"]
        conn = self._cpool.get_connection(rid) 
        if conn is None:
            raise Exception("Connection not found (id: " + rid + ")")
        wsock = WebSocket(self,conn, msg)
        resp = {}        
        try:
            self._agent.invoke_app(msg['module'],  "websocket",  self,  wsock)            
            if not wsock.is_accept():
                raise Exception("WebSocket not accepted")
        except:
            e = utils.get_exception()
            try:
                wsock.close()
            except:
                None
            resp["error"]=utils.exception_to_string(e)            
        resp['name']='response'
        resp['requestKey']=msg['requestKey']
        return resp
    
    def _websocketsimulate(self, msg):
        rid=msg["idRaw"]
        conn = self._cpool.get_connection(rid) 
        if conn is None:
            raise Exception("Connection not found (id: " + rid + ")")
        wsock = WebSocketSimulate(self,conn, msg)
        resp = {}
        try:
            self._agent.invoke_app(msg['module'],  "websocket",  self,  wsock)
            if not wsock.is_accept():
                raise Exception("WebSocket not accepted")
        except:
            e = utils.get_exception()
            try:
                wsock.close()
            except:
                None
            resp["error"]=utils.exception_to_string(e)
        resp['name']='response'
        resp['requestKey']=msg['requestKey']
        return resp    
    
    def _download(self, msg):
        rid=msg["idRaw"]
        conn = self._cpool.get_connection(rid) 
        if conn is None:
            raise Exception("Connection not found (id: " + rid + ")")
        fdownload = Download(self, conn, msg)
        resp = {}   
        try:
            self._agent.invoke_app(msg['module'],  "download",  self,  fdownload)
            if fdownload.is_accept():
                mt = mimetypes.guess_type(fdownload.get_path())
                if mt is None or mt[0] is None or not isinstance(mt[0], str):
                    resp["Content-Type"] = "application/octet-stream"
                else:
                    resp["Content-Type"] = mt[0]
                resp["Content-Disposition"] = "attachment; filename=\"" + fdownload.get_name() + "\"; filename*=UTF-8''" + utils.url_parse_quote(fdownload.get_name().encode("utf-8"), safe='')
                #ret["Cache-Control"] = "no-cache, must-revalidate" NON FUNZIONA PER IE7
                #ret["Pragma"] = "no-cache"
                resp["Expires"] = "Sat, 26 Jul 1997 05:00:00 GMT"
                resp["Length"] = str(fdownload.get_length())
            else:
                raise Exception("Download file not accepted")
        except:
            e = utils.get_exception()
            try:
                fdownload.close()
            except:
                None
            resp["error"]=utils.exception_to_string(e)
        resp['name']='response'
        resp['requestKey']=msg['requestKey']
        return resp
    
    def _upload(self, msg):
        rid=msg["idRaw"]
        conn = self._cpool.get_connection(rid) 
        if conn is None:
            raise Exception("Connection not found (id: " + rid + ")")
        fupload = Upload(self, conn, msg)
        resp = {}
        try:
            self._agent.invoke_app(msg['module'],  "upload",  self,  fupload)
            if not fupload.is_accept():
                raise Exception("Upload file not accepted")
        except:
            e = utils.get_exception()
            try:
                fupload.close()
            except:
                None
            resp["error"]=utils.exception_to_string(e)
        resp['name']='response'
        resp['requestKey']=msg['requestKey']
        return resp
    
    def _log_open(self):
        if not self._wait_accept and self._password is None:
            self._agent.write_info("Open session (id: " + self._idsession + ", ip: " + self._ipaddress + ", node: " + self._host + ")")
    
    def _log_close(self):
        if not self._wait_accept and self._password is None:
            self._agent.write_info("Close session (id: " + self._idsession + ", ip: " + self._ipaddress + ", node: " + self._host + ")")        
    
    def _close_session(self):
        self._agent.close_session(self)
        self._log_close()        
    
    def _on_close(self):        
        self._agent._task_pool.execute(self._close_session)
        self._cpool.destroy()
    
    def close(self):
        self._agent._task_pool.execute(self._close_session)
        Message.close(self)
        self._cpool.destroy()        
            

class WebSocket:
    DATA_STRING = ord('s')
    DATA_BYTES= ord('b')
    
    def __init__(self, parent, conn, props):
        self._parent=parent
        self._agent=self._parent._agent 
        self._props=props
        self._baccept=False
        self._bclose=False
        self._on_close=None
        self._on_data=None
        self._conn=conn
        self._conn.set_events({"on_close" : self._on_close_conn, "on_data" : self._on_data_conn})
        
            
    def accept(self, priority, events):
        if events is not None:
            if "on_close" in events:
                self._on_close = events["on_close"]
            if "on_data" in events:
                self._on_data = events["on_data"]
        self._len=-1
        self._data=None
        self._baccept=True
                
    
    def is_accept(self):
        return self._baccept
    
    def get_properties(self):
        return self._props
    
    def _on_data_conn(self,data):
        self._parent._set_last_activity_time()
        if not self._bclose:
            if self._data is None:
                self._data=bytearray(data)
            else:
                self._data+=data
            try:
                while True:
                    if self._len==-1:
                        if len(self._data)>=4:
                            self._len=struct.unpack('!i', self._data[0:4])[0]
                        else:
                            break
                    if self._len>=0 and len(self._data)-4>=self._len:
                        apptp = self._data[5]
                        appdata = self._data[5:5+self._len]
                        del self._data[0:4+self._len]
                        self._len=-1;
                        if self._on_data is not None:
                            self._on_data(self,apptp,appdata)
                    else:
                        break
            except:
                self.close()
                if self._on_close is not None:
                    self._on_close()
    
    def get_send_buffer_size(self):
        return self._parent.get_send_buffer_size()
    
    
    def send_list_string(self,data):
        self._parent._set_last_activity_time()
        if not self._bclose:
            st=struct.Struct("!IB")
            ba=bytearray()
            for i in range(len(data)):
                dt=data[i]
                ba+=bytearray(st.pack(len(dt)+1,WebSocket.DATA_STRING))
                ba+=dt   
            self._parent._send_conn(self._conn,ba)
    
    def send_list_bytes(self,data):
        self._parent._set_last_activity_time()
        if not self._bclose:
            st=struct.Struct("!IB")
            ba=bytearray()
            for i in range(len(data)):
                dt=data[i]
                ba+=bytearray(st.pack(len(dt)+1,WebSocket.DATA_BYTES))
                ba+=dt
            self._parent._send_conn(self._conn,ba)
    
    def send_string(self,data):
        self._parent._set_last_activity_time()
        if not self._bclose:            
            ba=bytearray(struct.pack("!IB",len(data)+1,WebSocket.DATA_STRING))
            ba+=utils.str_to_bytes(data)
            self._parent._send_conn(self._conn,ba)
    
    def send_bytes(self,data):
        self._parent._set_last_activity_time()
        if not self._bclose:            
            ba=bytearray(struct.pack("!IB",len(data)+1,WebSocket.DATA_BYTES))
            ba+=data
            self._parent._send_conn(self._conn,ba)
    
    def _on_close_conn(self):
        self._destroy(True)
        if self._on_close is not None:
            self._on_close()
            
    def is_close(self):
        return self._bclose
    
    def close(self):
        self._destroy(False)
    
    def _destroy(self,bnow):
        if not self._bclose:
            self._bclose=True
            if self._conn is not None:
                self._conn.close()
                self._conn = None



class WebSocketSimulate:
    DATA_STRING = 's'
    DATA_BYTES = 'b';
    MAX_SEND_SIZE = 65*1024
    
    def __init__(self, parent, conn, props):
        self._parent=parent
        self._agent=self._parent._agent 
        self._props=props
        self._baccept=False
        self._bclose=False
        self._on_close=None
        self._on_data=None
        self._conn=conn
        self._conn.set_events({"on_close" : self._on_close_conn, "on_data" : self._on_data_conn})
        
    
    def accept(self, priority, events):
        if events is not None:
            if "on_close" in events:
                self._on_close = events["on_close"]
            if "on_data" in events:
                self._on_data = events["on_data"]
        self._qry_len=-1
        self._qry_data=bytearray()
        self._pst_len=-1
        self._pst_data=bytearray()
        self._qry_or_pst="qry"
        self._data_list=[]
        self._baccept=True
    
    def is_accept(self):
        return self._baccept
    
    def get_properties(self):
        return self._props
    
    def _on_data_conn(self,data):
        self._parent._set_last_activity_time()
        if not self._bclose:
            try:
                if self._qry_or_pst=="qry":
                    self._qry_data+=data
                else:
                    self._pst_data+=data
                if self._qry_or_pst=="qry":
                    if self._qry_len==-1:
                        if len(self._qry_data)>=4:
                            self._qry_len = struct.unpack('!i', self._qry_data[0:4])[0]
                            del self._qry_data[0:4]
                    if self._qry_len!=-1 and len(self._qry_data)>=self._qry_len:
                        self._pst_data=self._qry_data[self._qry_len:]
                        del self._qry_data[self._qry_len:]
                        self._qry_or_pst="pst"
                if self._qry_or_pst=="pst":
                    if self._pst_len==-1:
                        if len(self._pst_data)>=4:
                            self._pst_len = struct.unpack('!i', self._pst_data[0:4])[0]
                            del self._pst_data[0:4]
                    if self._pst_len!=-1 and len(self._pst_data)>=self._pst_len:
                        prpqry=None
                        if self._qry_len>0:
                            prpqry=communication.xml_to_prop(self._qry_data)
                        self._qry_data=self._pst_data[self._pst_len:]
                        del self._pst_data[self._pst_len:]
                        prppst=None
                        if self._pst_len>0:
                            prppst=communication.xml_to_prop(self._pst_data)
                        self._qry_or_pst="qry"
                        self._qry_len=-1
                        self._pst_len=-1
                        self._pst_data=bytearray()
                        
                        if self._on_data is not None:
                            cnt = int(prppst["count"])
                            for i in range(cnt):
                                tpdata = prppst["type_" + str(i)]
                                prprequest = prppst["data_" + str(i)]
                                if tpdata==WebSocketSimulate.DATA_BYTES:
                                    prprequest=utils.enc_base64_decode(prprequest)
                                else:
                                    prprequest=utils.str_to_bytes(prprequest,"utf8")
                                self._on_data(self, tpdata, prprequest)
                        #Invia risposte
                        arsend=None
                        if len(self._data_list)==0 and "destroy" not in prppst:
                            appwt=250
                            if "wait" in prppst:
                                appwt=int(prppst["wait"])
                            if appwt==0:
                                while not self._bclose and len(self._data_list)==0:
                                    time.sleep(0.01)
                            else:
                                appwt=appwt/1000.0
                                time.sleep(appwt)
                        if not self._bclose:
                            arsend = {}
                            arcnt = 0
                            lensend = 0
                            while len(self._data_list)>0 and lensend<WebSocketSimulate.MAX_SEND_SIZE:
                                sdt = self._data_list.pop(0)
                                arsend["type_" + str(arcnt)]=sdt["type"]
                                arsend["data_" + str(arcnt)]=sdt["data"]
                                lensend += len(sdt)
                                arcnt+=1
                            if arcnt>0:
                                arsend["count"]=arcnt
                                arsend["otherdata"]=len(self._data_list)>0
                                self._send_response(json.dumps(arsend))
                            else:
                                self._send_response("")
                        if "destroy" in prppst:
                            self.close()
                            if self._on_close is not None:
                                self._on_close()
            except:                
                self.close()
                if self._on_close is not None:
                    self._on_close()
                    
    
    def _send_response(self,sdata):
        st_I=struct.Struct("!I")
        
        prop = {}
        prop["Cache-Control"] = "no-cache, must-revalidate"
        prop["Pragma"] = "no-cache"
        prop["Expires"] = "Sat, 26 Jul 1997 05:00:00 GMT"
        prop["Content-Encoding"] = "gzip"
        prop["Content-Type"] = "application/json; charset=utf-8"
        #prop["Content-Type"] = "application/octet-stream"
        
        bts = bytearray()
        
        #AGGIUNGE HEADER
        shead = communication.prop_to_xml(prop)
        bts+=st_I.pack(len(shead))
        bts+=bytearray(shead,"ascii")

        #COMPRESS RESPONSE
        appout = utils.BytesIO()
        f = gzip.GzipFile(fileobj=appout, mode='w', compresslevel=5)
        f.write(utils.str_to_bytes(sdata))
        f.close()
        dt = appout.getvalue()
        
        #BODY LEN
        ln=len(dt)
        
        #BODY        
        bts+=st_I.pack(ln)
        if ln>0:
            bts+=dt            
        
        self._parent._send_conn(self._conn,bts)
        
    def get_send_buffer_size(self):
        return self._parent.get_send_buffer_size()
    
    def send_list_string(self,data):
        self._send_list(WebSocketSimulate.DATA_STRING,data)
    
    def send_list_bytes(self,data):
        self._send_list(WebSocketSimulate.DATA_BYTES,data)
    
    def send_string(self,data):
        self._send(WebSocketSimulate.DATA_STRING,data)
    
    def send_bytes(self,data):
        self._send(WebSocketSimulate.DATA_BYTES,data)
    
    def _send(self,tpdata,data): 
        self._parent._set_last_activity_time()
        if not self._bclose:
            dt=data
            if tpdata==WebSocketSimulate.DATA_BYTES:
                dt=utils.bytes_to_str(utils.enc_base64_encode(dt))
            #print("LEN: " + str(len(data)) + " LEN B64: " + str(len(dt)))
            self._data_list.append({"type": tpdata, "data": dt})
                        
    
    def _send_list(self,tpdata,data): 
        self._parent._set_last_activity_time()
        if not self._bclose:
            for i in range(len(data)):
                dt=data[i]
                if tpdata==WebSocketSimulate.DATA_BYTES:
                    dt=utils.bytes_to_str(utils.enc_base64_encode(dt))
                #print("LEN: " + str(len(data[i])) + " LEN B64: " + str(len(dt)))
                self._data_list.append({"type": tpdata, "data": dt})
            
                
    def _on_close_conn(self):
        self._destroy(True)
        if self._on_close is not None:
            self._on_close()
    
    def is_close(self):
        return self._bclose
    
    def close(self):
        self._destroy(False)
       

    def _destroy(self,bnow):
        if not self._bclose:
            self._bclose=True
            self._data_list=[]                
            if self._conn is not None:
                self._conn.close()
                self._conn = None
                

class Download():

    def __init__(self, parent, conn, props):
        self._parent=parent
        self._agent=self._parent._agent
        self._props=props
        self._semaphore = threading.Condition()
        self._baccept=False
        self._conn=conn
        self._conn.set_events({"on_close" : self._on_close_conn, "on_data" : self._on_data_conn})

    def accept(self, path):
        self._path=path
        self._name=utils.path_basename(self._path)
        self._length=utils.path_size(self._path)
        self._calcbps=communication.BandwidthCalculator()        
        self._bclose = False
        self._status="T"
        self._baccept=True        
        self._agent._task_pool.execute(self.run)
    
    def is_accept(self):
        return self._baccept
    
    def get_properties(self):
        return self._props
    
    def get_name(self):
        return self._name
        
    def get_path(self):
        return self._path
    
    def get_transfered(self):
        return self._calcbps.get_transfered()
    
    def get_length(self):
        return self._length
    
    def get_bps(self):
        return self._calcbps.get_bps()
    
    def get_status(self):
        return self._status   
    
    def run(self):
        self._parent.inc_activities_value("downloads")
        fl=None
        try:
            fl = utils.file_open(self._path, 'rb')
            bsz=32*1024
            while not self.is_close():
                bts = fl.read(bsz)
                ln = len(bts)
                if ln==0:
                    self._status="C"                    
                    break
                self._parent._set_last_activity_time()
                self._parent._send_conn(self._conn,bts)
                self._calcbps.add(ln)
                #print("DOWNLOAD - NAME:" + self._name + " SZ: " + str(len(s)) + " LEN: " + str(self._calcbps.get_transfered()) +  "  BPS: " + str(self._calcbps.get_bps()))
        except:
            self._status="E"            
        finally:
            self.close()
            if fl is not None:
                fl.close()
        if self._conn is not None:
            self._conn.close()
            self._conn = None
        self._parent.dec_activities_value("downloads")        
    
    def is_close(self):
        self._semaphore.acquire()
        try:
            return self._bclose
        finally:
            self._semaphore.release()
            
    def _on_data_conn(self,data):
        self._parent._set_last_activity_time()        
    
    def _on_close_conn(self):
        self._semaphore.acquire()
        try:
            if not self._bclose:
                if self._status=="T":
                    self._status="E"                    
                self._bclose=True
        finally:
            self._semaphore.release()
    
    def close(self):        
        self._semaphore.acquire()
        try:
            if not self._bclose:
                if self._status=="T":
                    self._status="C"                    
                self._bclose=True
        finally:
            self._semaphore.release()
        if not self._baccept and self._conn is not None:
            self._conn.close()
            self._conn = None


class Upload():

    def __init__(self, parent, conn, props):
        self._parent=parent
        self._agent=self._parent._agent
        self._props=props
        self._semaphore = threading.Condition()
        self._baccept=False
        self._bclose=True
        self._enddatafile=False
        self._conn=conn
        self._conn.set_events({"on_close" : self._on_close_conn, "on_data" : self._on_data_conn})

    def accept(self, path):
        self._path=path
        self._name=utils.path_basename(self._path)
        if 'length' not in self._props:
            raise Exception("upload file length in none.")
        self._length=int(self._props['length'])
        self._calcbps=communication.BandwidthCalculator() 
        self._cntSendstatus=None
        try:
            sprnpath=utils.path_dirname(path)    
            while True:
                r="".join([random.choice("0123456789") for x in utils.nrange(6)])            
                self._tmpname=sprnpath + utils.path_sep + "temporary" + r + ".dwsupload";
                if not utils.path_exists(self._tmpname):
                    utils.file_open(self._tmpname, 'wb').close() #Crea il file per imposta i permessi
                    self._agent.get_osmodule().fix_file_permissions("CREATE_FILE",self._tmpname)
                    self._fltmp = utils.file_open(self._tmpname, 'wb')
                    break
        
            self._bclose = False
            self._status="T"
            self._enddatafile=False
            self._baccept=True
            self._last_time_transfered = 0
        except:
            e = utils.get_exception()
            self._remove_temp_file()
            raise e
        self._parent.inc_activities_value("uploads")
        
    def _remove_temp_file(self):
        try:
            self._fltmp.close()
        except:
            None
        try:
            if utils.path_exists(self._tmpname):
                utils.path_remove(self._tmpname)
        except:
            None        
    
    def is_accept(self):
        return self._baccept
    
    def get_properties(self):
        return self._props
    
    def get_name(self):
        return self._name
        
    def get_path(self):
        return self._path
    
    def get_transfered(self):
        return self._calcbps.get_transfered()
    
    def get_length(self):
        return self._length
    
    def get_bps(self):
        return self._calcbps.get_bps()
    
    def get_status(self):
        return self._status  
    
    def _on_data_conn(self, data):
        self._parent._set_last_activity_time()
        self._semaphore.acquire()
        try:
            if not self._bclose:
                if self._status == "T":
                    if utils.bytes_get(data,0)==ord('C'): 
                        self._enddatafile=True;
                        #SCRIVE FILE
                        try:
                            self._fltmp.close()
                            if utils.path_exists(self._path):
                                if utils.path_isdir(self._path):
                                    raise Exception("")
                                else:
                                    utils.path_remove(self._path)
                            shutil.move(self._tmpname, self._path)
                            self._status = "C"
                            self._parent._send_conn(self._conn, bytearray(self._status, "utf8"))                            
                        except:
                            self._status = "E"
                            self._parent._send_conn(self._conn, bytearray(self._status, "utf8"))                            
                        self.close()
                    else: #if data[0]=='D': 
                        lndt=len(data)-1;
                        self._fltmp.write(utils.buffer_new(data,1,lndt))
                        self._calcbps.add(lndt)
                        if self._cntSendstatus is None or self._cntSendstatus.is_elapsed(0.5):
                            self._parent._send_conn(self._conn, bytearray("T" + str(self._calcbps.get_transfered()) + ";" + str(self._calcbps.get_bps()) , "utf8"))
                            if self._cntSendstatus is None:
                                self._cntSendstatus=utils.Counter()
                            else:
                                self._cntSendstatus.reset()
                        #print("UPLOAD - NAME:" + self._name + " LEN: " + str(self._calcbps.get_transfered()) +  "  BPS: " + str(self._calcbps.get_bps()))
                        
        except:
            self._status = "E"
        finally:
            self._semaphore.release()
        
    def is_close(self):
        ret = True
        self._semaphore.acquire()
        try:
            ret=self._bclose
        finally:
            self._semaphore.release()
        return ret
        
    def _on_close_conn(self):
        bclose = False
        self._semaphore.acquire()
        try:
            if not self._bclose:
                #print("UPLOAD - ONCLOSE")
                bclose = True
                self._bclose=True                
                self._remove_temp_file()
                if not self._enddatafile:
                    self._status = "E"
        finally:
            self._semaphore.release()
        if bclose is True:
            self._parent.dec_activities_value("uploads")
        if self._conn is not None:
            self._conn.close()
            self._conn = None
                
            
    
    def close(self):
        bclose = False
        self._semaphore.acquire()
        try:
            if not self._bclose:
                #print("UPLOAD - CLOSE")
                bclose = True
                self._bclose=True
                self._remove_temp_file()
                self._status  = "C"
        finally:
            self._semaphore.release()
        if bclose is True:
            self._parent.dec_activities_value("uploads")
        if self._conn is not None:
            self._conn.close()
            self._conn = None


class AgentProfiler(threading.Thread):
    
    def __init__(self,profcfg):
        self._destroy=False
        self._filename=None
        self._fileupdateintervall=10
        if "profiler_filename" in profcfg:
            self._fileupdateintervall=int(profcfg["profiler_fileupdateintervall"])
        if "profiler_filename" in profcfg:
            self._filename=profcfg["profiler_filename"]
        threading.Thread.__init__(self, name="AgentProfiler")

    def run(self):
        import yappi
        #yappi.set_clock_type("wall")
        #yappi.start(builtins=True)
        yappi.start()
        cntr = utils.Counter()
        while not self._destroy:
            if cntr.is_elapsed(self._fileupdateintervall):
                cntr.reset()
                if self._filename is not None:
                    f = open(self._filename,"w")
                    appmds=[]
                    #for k in sys.modules:
                    #    if k=="app_desktop" or k.startswith("app_desktop"):
                    #        appmds.append(sys.modules[k])    
                    appmds.append(sys.modules["communication"])
                    yappi.get_func_stats(
                        #filter_callback=lambda x: yappi.module_matches(x, appmds)
                        ).print_all(out=f, columns={
                            0: ("name", 80),
                            1: ("ncall", 10),
                            2: ("tsub", 8),
                            3: ("ttot", 8),
                            4: ("tavg", 8)
                        })                    
                    yappi.get_thread_stats().print_all(out=f, columns={
                        0: ("name", 30),
                        1: ("id", 5),
                        2: ("tid", 15),
                        3: ("ttot", 8),
                        4: ("scnt", 10)
                    })                    
                    f.close()
                
            time.sleep(1)
        
        yappi.stop()
            

    def destroy(self):
        self._destroy=True 
        

main = None

def ctrlHandler(ctrlType):
    return 1   


def fmain(args): #SERVE PER MACOS APP
    if is_windows():
        try:
            #Evita che si chiude durante il logoff
            HandlerRoutine = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_uint)(ctrlHandler)
            kernel32=ctypes.windll.kernel32
            kernel32.SetConsoleCtrlHandler(HandlerRoutine, 1)
        except:
            None
    
    main = Agent(args)
    main.start()
    sys.exit(0)
    

if __name__ == "__main__":    
    bmain=True
    if len(sys.argv)>1:
        a1=sys.argv[1]
        if a1 is not None and a1.lower().startswith("app="):
            if utils.path_exists(".srcmode"):
                sys.path.append("..")            
            bmain=False
            name=a1[4:]
            sys.argv.remove(a1)
            if name=="ipc":
                ipc.fmain(sys.argv)
            else:
                #COMPATIBILITY OLD VERSION 05/05/2021 (TO REMOVE)
                objlib = importlib.import_module("app_" + name)
                func = getattr(objlib, 'run_main', None)
                func(sys.argv)
        elif a1 is not None and a1.lower()=="guilnc": #GUI LAUNCHER OLD VERSION 03/11/2021 (DO NOT REMOVE)             
            if is_mac():
                bmain=False
                native.fmain(sys.argv)
    if bmain:
        fmain(sys.argv)
    
