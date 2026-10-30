# -*- coding: utf-8 -*-
'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''

import os
import sys
import shutil
import communication
import threading
import time
import json
import string
import random
import zipfile
import gzip
import signal
import platform
import hashlib
import listener
import ctypes
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
    return "".join([random.choice(c) for x in utils.nrange(n)])
        
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
    
def read_json_file(nm):
    c=None
    try:
        try:
            f = utils.file_open(nm, 'rb')
        except:
            e = utils.get_exception()
            raise Exception("Error reading " + nm + " file. " + utils.exception_to_string(e))
        try:
            s=f.read()
            c = json.loads(utils.bytes_to_str(s,"utf8"))
        except:
            e = utils.get_exception()
            raise Exception("Error parse " + nm +" file: " + utils.exception_to_string(e))
        finally:
            f.close()        
    except:
        e = utils.get_exception()
        if utils.path_exists(nm+".bk"):
            try:
                f = utils.file_open(nm+".bk", 'rb')
                s=f.read()
                c = json.loads(utils.bytes_to_str(s,"utf8"))
                f.close()
                if utils.path_exists(nm):
                    utils.path_remove(nm)
                utils.path_copy(nm+".bk", nm)
            except:
                raise e
        else:
            raise e
    if utils.path_exists(nm+".bk"):
        utils.path_remove(nm+".bk")
    return c

def write_json_file(nm,jo):
    s = json.dumps(jo, sort_keys=True, indent=1)
    if utils.path_exists(nm) and not utils.path_exists(nm+".bk"):
        utils.path_copy(nm, nm+".bk")
    f = utils.file_open(nm, 'wb')
    f.write(utils.str_to_bytes(s,"utf8"))
    utils.file_sync(f)
    f.close()
    if utils.path_exists(nm+".bk"):
        utils.path_remove(nm+".bk")

class Agent():
    _STATUS_OFFLINE = 0
    _STATUS_ONLINE = 1
    _STATUS_ONLINE_DISABLE = 2
    _STATUS_DISABLE = 3
    _STATUS_UPDATING = 10
    _CONNECTION_TIMEOUT= 60
    
    def __init__(self,args):
        
        if utils.path_exists(".srcmode"):
            sys.path.append("..")
        
        #Create log
        self._noctrlfile=False
        self._bstop=False
        self._truncate_service_log_enable=True
        self._truncate_service_log_counter=utils.Counter(10) #10 seconds        
        self._runonfly=False
        self._runonfly_conn_retry=0
        self._runonfly_user=None
        self._runonfly_password=None
        self._runonfly_password_stored=None
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
        #Init fields
        self._task_pool = None
        self._config=None
        self._brun=True
        self._brebootagent=False
        self._breloadconfig=True        
        if self._runonfly:
            self._cnt_min=0
            self._cnt_max=5
        else:
            self._cnt_min=5
            self._cnt_max=30
        self._cnt=0
        self._listener_ipc=None
        self._listener_ipc_load=True
        self._listener_http=None
        self._listener_http_load=True
        self._proxy_info=None       
        self._http_socket_pool=None 
        self._agent_conn = None
        self._sessions={}
        self._sessions_closing=set()
        self._sessions_update_status=""
        self._sessions_semaphore = threading.Condition()
        self._libs={}
        self._libs_apps_semaphore = threading.Condition()
        self._apps={}
        self._agent_enabled = True        
        self._agent_missauth = False
        self._agent_status = self._STATUS_OFFLINE
        self._agent_name = None
        self._agent_debug_mode = False
        self._agent_url_primary = None
        self._agent_key = None
        self._agent_password = None        
        self._agent_server = None
        self._agent_server_state = ""
        self._agent_distr = None        
        self._agent_versions=None
        self._agent_port= None
        self._agent_native_suffix=None
        self._agent_profiler=None
        self._agent_last_error=None
        self._agent_installer_ver=None        
        self._config_semaphore = threading.Condition()
        self._osmodule = native.get_instance()
        self._svcpid=None
    
    #KEEP COMPATIBILITY WITH OLD FOLDERS RUNONFLY
    def set_runonfly_action(self,action):
        self._runonfly_action=action
    
    def _signal_handler(self, signal, frame):
        if self._noctrlfile==True:
            self._bstop=True
        else:
            f = utils.file_open("dwagent.stop", 'wb')
            f.close()           
    
    def _write_config_file(self):
        write_json_file("config.json",self._config)        
        
    def _read_config_file(self):
        self._config_semaphore.acquire()
        try:
            try:
                self._config = read_json_file("config.json")
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
    
    def _runonfly_gen_key(self):
        nc = random.randint(0, 99999999999)
        return '{:011}'.format(nc)
    
    def _runonfly_gen_pin(self):
        nc = random.randint(0, 9999)
        return '{:04}'.format(nc)
    
    def _load_config(self):
        #self.write_info("load configuration...")
        #CHECK agentConnectionPropertiesUrl
        self._agent_url_primary = self.get_config('url_primary', None)
        if self._agent_url_primary  is None:
            self.write_info("Missing url_primary configuration.")
            return False
        if not self._runonfly:
            self._agent_key = self.get_config('key', None)
            self._agent_password = self.get_config('password', None)
            if self._agent_password is not None:
                self._agent_password = read_obfuscated_password(self._agent_password)
        else:
            self._agent_key = "TMP@"
            if self._runonfly_runcode is not None:
                self._agent_key+="CODE"
                self._agent_password=self._runonfly_runcode
            else:
                if "preferred_run_user" in self._config:
                    self._agent_key+=self._config["preferred_run_user"]                    
                else:
                    self._agent_key+=self._runonfly_gen_key()
                    self._runonfly_password_stored=None
                    
                if self._runonfly_password_stored is None:
                    self._runonfly_password_stored=self._runonfly_gen_pin()
                self._agent_password = self._runonfly_password_stored
        
        #READ installer.ver
        try:
            if utils.path_exists(".srcmode"):
                self._agent_installer_ver="dev"
            else:
                ptver="native" + os.sep + "installer.ver"
                if utils.path_exists(ptver):
                    fver = utils.file_open(ptver, "rb")
                    self._agent_installer_ver=utils.bytes_to_str(fver.read())
                    fver.close()
        except:
            None
        
        return True
    
    def _get_connection_info(self):
        try:            
            lstnodes = self.get_config("nodes")
            if lstnodes is None or len(lstnodes)==0:
                try:
                    self.write_info("Get connection info...")
                    sver=""
                    if self._agent_installer_ver is not None:
                        sver="&version=" + self._agent_installer_ver
                    skey=""
                    if not self._runonfly:
                        skey="&key=" + self._agent_key
                    sdid=""                    
                    idid=self._get_agent_distr_id()                    
                    if idid is not None:
                        sdid="&distrID=" + str(idid)
                                        
                    appurl = self._agent_url_primary + "getAgentConnection.dw?osTypeCode=" + str(get_os_type_code()) + skey + sver + sdid            
                    prpurl = communication.get_url_prop(appurl, self.get_proxy_info())
                    
                    if prpurl["status"]=="error":
                        if prpurl['message']=="NO_NODE_AVAILABLE":
                            self.write_info("Error get connection info: no node available")
                        else:
                            self.write_info("Error get connection info: " + prpurl['message'])
                        return False
                    
                    lstnodes=prpurl["nodes"]
                    if not self._runonfly:
                        try:
                            self._set_config("nodes", lstnodes)
                        except:
                            None
                            
                    if "distr" in prpurl:
                        jodistr=prpurl["distr"]
                        if "id" in jodistr:
                            self._set_distr_update(jodistr["id"])

                except:
                    e = utils.get_exception()
                    if utils.is_connection_refused_exception(e):
                        m="Connection refused."
                    else:
                        m=utils.exception_to_string(e)
                    self.write_info("Error get connection info: " + m)
                    return False            
            
            prpnode=lstnodes[0]
            self._agent_server = get_prop(prpnode, 'server', None)
            if self._agent_server is None:
                self.write_info("Missing server configuration.")
                return False
            
            self._agent_port = get_prop(prpnode, 'port', "443")
            self.write_info("Node: " + self._agent_server)
            self.write_info("Proxy: " + self.get_proxy_info().get_type())
            
            return True
        except:
            e = utils.get_exception()
            self.write_except(e, "Unexpected error in _get_connection_info")
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
            self._proxy_info=None #Reload proxy
        finally:
            self._config_semaphore.release()
        self._reload_config()
    
    def install_new_agent(self, user, password, name, group=None, groupCreate=False):
        spapp = ";".join(self.get_supported_applications())
        sprmgroup=""
        if group is not None and group.strip()!="":
            sprmgroup="&group=" + utils.url_parse_quote_plus(group.strip())
            if groupCreate:
                sprmgroup+="&groupCreate=true"
        url = self._agent_url_primary + "installNewAgent.dw?user=" + utils.url_parse_quote_plus(user) + "&password=" + utils.url_parse_quote_plus(password) + sprmgroup + "&name=" + utils.url_parse_quote_plus(name) + "&osTypeCode=" + str(get_os_type_code()) +"&supportedApplications=" + utils.url_parse_quote_plus(spapp)
        try:
            prop = communication.get_url_prop(url, self.get_proxy_info())
        except:
            raise Exception("CONNECT_ERROR")
        if 'error' in prop:
            raise Exception(prop['error'])
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
    
    def _get_config_nosync(self, key,default=None):
        if self._config is not None:
            if key in self._config:
                return self._config[key]
            else:
                return default
        else:
            return default
    
    def get_config(self, key, default=None):
        self._config_semaphore.acquire()
        try:
            return self._get_config_nosync(key,default)
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
    
    def _set_config_nosync(self, key, val):
        if val is not None:
            self._config[key]=val
        else:
            if key in self._config:
                del self._config[key]
            else:
                return
        self._write_config_file()
    
    def _set_config(self, key, val):
        self._config_semaphore.acquire()
        try:
            self._set_config_nosync(key,val)
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
    
    def _download_agent_file(self, pth, fnm, maxattempts=1):
        attempt=0
        while True:
            try:
                attempt+=1
                urldwn = self.get_config('url_download', None)
                if urldwn is None:
                    urldwn=self._agent_url_primary
                upath=urldwn+pth
                upathnew=communication.download_url_file(upath, fnm, self.get_proxy_info(), None)
                if upath!=upathnew:
                    p=upathnew.find(pth)
                    if p>=0:
                        self._set_config("url_download", upathnew[0:p])
                break
            except Exception as e:
                self._set_config("url_download", None)
                if attempt>=maxattempts:
                    raise e
                else:
                    self.write_err("Error download file " + fnm + " (attempt " + str(attempt) +"): " + utils.exception_to_string(e))
                    time.sleep(2)

    def _unzip_file(self, fpath, unzippath, licpath=None):
        zfile = zipfile.ZipFile(fpath)
        try:
            for nm in zfile.namelist():
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
                utils.file_sync(fd)
                fd.close()
        finally:
            zfile.close()

    def _fix_old_fileversions(self,nmf,rnm,arcv,arlv):
        #FIX OLD VERSION 2024-01-15
        bret=False
        pthfv="fileversions.json"
        if utils.path_exists(pthfv):
            flsvers = read_json_file("fileversions.json")
            appnm = nmf
            arnm = appnm.split("/")
            if len(arnm)==2:
                arappnm=arnm[1].split(".")
                appnm=arappnm[0] + "_" + arnm[0] + "." + arappnm[1]
            if appnm in flsvers:                
                ofstm = int(flsvers[appnm])
                if arlv is None:
                    if int(ofstm)==int(arcv["time"]*1000):
                        self._set_agent_version(rnm,arcv)
                        bret=True
                del flsvers[appnm]
                if len(flsvers)==0 and not self._runonfly: #self._runonfly compatibility old installer20022024
                    utils.path_remove("fileversions.json")
                else:
                    write_json_file("fileversions.json", flsvers)
                return bret
        return bret
        #FIX OLD VERSION 2024-01-15
    
    def _get_latest_distr(self,distrcur=None):
        if utils.path_exists(".srcmode"):
            return None
        app_url = self._agent_url_primary + "getAgentConfig.dw?id=latest"
        if distrcur is not None:
            app_url+="&curid=" + str(distrcur["id"])
        if self._agent_installer_ver is not None:
            app_url+="&version=" + self._agent_installer_ver
        if not self._runonfly:
            app_url+="&key=" + self._agent_key
        prop=communication.get_url_prop(app_url,self.get_proxy_info())
        if "error" in prop:
            raise Exception(prop["error"])
        return prop
    
    def _get_agent_distr_nosync(self):
        if self._agent_distr is None:
            if utils.path_exists("distr.json"):
                self._agent_distr = read_json_file("distr.json")
        return self._agent_distr
    
    def _get_agent_distr_id(self):
        appdistr = self._get_agent_distr()
        if appdistr is not None:
            return appdistr["id"]
        else:
            return 0
    
    def _get_agent_distr(self):
        if utils.path_exists(".srcmode"):
            return None
        self._config_semaphore.acquire()
        try:
            return self._get_agent_distr_nosync()
        finally:
            self._config_semaphore.release()
                 
    def _load_agent_version(self):
        if self._agent_versions is None:
            if utils.path_exists("versions.json"):
                self._agent_versions=read_json_file("versions.json")
            else:
                self._agent_versions={}                        
    
    def _get_agent_version(self, nm):
        self._config_semaphore.acquire()
        try:
            self._load_agent_version()    
            if nm in self._agent_versions:
                return self._agent_versions[nm]
            else:
                return None
        finally:
            self._config_semaphore.release()        
    
    def _set_agent_version(self, nm, prp):
        self._config_semaphore.acquire()
        try:
            self._load_agent_version()
            self._agent_versions[nm]=prp
            write_json_file("versions.json",self._agent_versions)
        finally:
            self._config_semaphore.release()
        

    def _check_and_update_distr_file(self, distr_cur, upd_vers, name_file, folder):
        rnm="agent/" + name_file                
        arcv = distr_cur["files"][rnm]
        arlv = self._get_agent_version(rnm)        
        #FIX OLD VERSION 2024-01-15
        if self._fix_old_fileversions(name_file,rnm,arcv,arlv):
            return False
        #FIX OLD VERSION 2024-01-15
        if arlv is None or arcv["version"]!=arlv["version"]:
            if not utils.path_exists(folder):
                utils.path_makedirs(folder)
            self.write_info("Downloading file update " + name_file + "...")
            app_url = "app/" + arcv["file"]
            app_file = folder + "tmp.zip"
            if utils.path_exists(app_file):
                utils.path_remove(app_file)
            self._download_agent_file(app_url ,app_file)
            self._check_hash_file(app_file, arcv["md5"])
            self._unzip_file(app_file, folder)
            utils.path_remove(app_file)
            upd_vers[rnm]=arcv
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
    
    def _set_distr_update(self, nid):
        bret=False
        if utils.path_exists(".srcmode"):
            return bret
        self._config_semaphore.acquire()
        try:
            if self._get_config_nosync("updates_auto",True)==False:
                return bret
            if nid is None or nid==0:
                self._set_config_nosync("distr_update",None)
            elif self._get_config_nosync("distr_update") is None:
                distrcur=self._get_agent_distr_nosync()
                if distrcur is not None and distrcur["id"]<nid:
                    self._set_config_nosync("distr_update",{"id":nid})
                    bret=True
            else:
                if nid>self._get_config_nosync("distr_update")["id"]:
                    self._set_config_nosync("distr_update",{"id":nid})
                    bret=True
        finally:
            self._config_semaphore.release()
        return bret
    
    def _check_and_update_distr(self, firstchk=False):
        if utils.path_exists(".srcmode"):
            return False
        if not firstchk and self._runonfly:
            return False
        
        bret=False
        brestoreses=False
        try:            
            self._config_semaphore.acquire()
            try:
                distrcur=self._get_agent_distr_nosync()
                adu=self._get_config_nosync("distr_update")                
            finally:
                self._config_semaphore.release()
            
            if firstchk:
                if distrcur is not None:
                    self.write_info("Distr ID: " + str(distrcur["id"]))
                    if adu is None:
                        return bret
                    elif adu["id"]<=distrcur["id"]:
                        self._config_semaphore.acquire()
                        try:
                            self._set_config_nosync("distr_update", None)
                        finally:
                            self._config_semaphore.release()
                        return bret
            else:
                if distrcur is None or adu is None:
                    return bret
            
            if not firstchk:
                self._sessions_semaphore.acquire()
                try:
                    if len(self._sessions)==0:
                        self._sessions_update_status="INPROGRESS"
                        brestoreses=True
                finally:
                    self._sessions_semaphore.release()
                        
            if firstchk or brestoreses:
                self._unload_apps()
                #REMOVE updateTMP
                if utils.path_exists("updateTMP"):
                    shutil.rmtree("updateTMP")
                    
                if firstchk or adu["id"]>distrcur["id"]:
                    self.write_info("Distr updating...")
                    distrcur=self._get_latest_distr(distrcur)
                    upd_vers={}
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
                                if self._check_and_update_distr_file(distrcur, upd_vers, self._agent_native_suffix + "/agentupd.zip",  "updateTMP" + utils.path_sep + "native" + utils.path_sep):
                                    if utils.path_exists("updateTMP" + utils.path_sep + "native" + utils.path_sep + upd_libnm):
                                        if utils.path_exists("native" + utils.path_sep + upd_libnm):
                                            if utils.path_exists("native" + utils.path_sep + upd_libnm + "OLD"):
                                                utils.path_remove("native" + utils.path_sep + upd_libnm + "OLD")                                        
                                            utils.path_move("native" + utils.path_sep + upd_libnm,"native" + utils.path_sep + upd_libnm + "OLD")
                                            if utils.path_exists("native" + utils.path_sep + upd_libnm):
                                                raise Exception("Failed to update file: " + upd_libnm + ".")
                                        shutil.move("updateTMP" + utils.path_sep + "native" + utils.path_sep + upd_libnm, "native" + utils.path_sep + upd_libnm)
                                        if utils.path_exists("native" + utils.path_sep + upd_libnm):
                                            if utils.path_exists("native" + utils.path_sep + upd_libnm + "OLD"):
                                                utils.path_remove("native" + utils.path_sep + upd_libnm + "OLD")
                                        else:
                                            raise Exception("Failed to update file: " + upd_libnm + ".")
                    #AGENT
                    self._check_and_update_distr_file(distrcur, upd_vers, "agent.zip", "updateTMP" + utils.path_sep)
                    if not self._runonfly and not self._agent_native_suffix=="linux_generic":
                        if self._check_and_update_distr_file(distrcur, upd_vers, "agentui.zip", "updateTMP" + utils.path_sep):
                            self._monitor_update_file_create()
                    self._check_and_update_distr_file(distrcur, upd_vers, "agentapps.zip", "updateTMP" + utils.path_sep)
        
                    #LIB
                    if self._agent_native_suffix is not None:
                        if not self._agent_native_suffix=="linux_generic":
                            self._check_and_update_distr_file(distrcur, upd_vers, self._agent_native_suffix + "/agentlib.zip",  "updateTMP" + utils.path_sep + "native" + utils.path_sep)
                            
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
                            if self._check_and_update_distr_file(distrcur, upd_vers, self._agent_native_suffix + "/agentui.zip",  "updateTMP" + utils.path_sep + "native" + utils.path_sep):
                                self._monitor_update_file_create()
                                if utils.path_exists("updateTMP" + utils.path_sep + "native" + utils.path_sep + monitor_libnm):
                                    shutil.move("updateTMP" + utils.path_sep + "native" + utils.path_sep + monitor_libnm, "updateTMP" + utils.path_sep + "native" + utils.path_sep + monitor_libnm + "NEW")
                                        
                    if utils.path_exists("updateTMP"):
                        write_json_file("updateTMP" + os.sep + "distr.json",distrcur)
                        jonewver={}
                        self._config_semaphore.acquire()
                        try:
                            for k in self._agent_versions:
                                jonewver[k]=self._agent_versions[k]
                        finally:
                            self._config_semaphore.release()
                        for k in upd_vers:
                            jonewver[k]=upd_vers[k]
                        s = json.dumps(jonewver, sort_keys=True, indent=1)
                        f = utils.file_open("updateTMP" + utils.path_sep + "versions.json", "wb")
                        f.write(utils.str_to_bytes(s,"utf8"))
                        utils.file_sync(f)
                        f.close()
                        shutil.move("updateTMP", "update")
                        self._update_ready_reboot=True
                        self.write_info("Distr updated ID: " + str(distrcur["id"]) + ". Needs reboot.")
                        bret=True
                    else:
                        self._config_semaphore.acquire()
                        try:
                            write_json_file("distr.json",distrcur)
                            self._agent_distr = distrcur
                            self._set_config_nosync("distr_update", None)
                        finally:
                            self._config_semaphore.release()
                        self.write_info("Distr updated ID: " + str(distrcur["id"]))
                        try:
                            #UPDATE DISTR ID
                            m = {
                                'name':  'update', 
                                'distrID': str(distrcur["id"])
                            }
                            if self._agent_conn is not None:                
                                self._agent_conn.send_message(m)
                        except:
                            e = utils.get_exception()
                            self.write_except(e)
                else:
                    self._config_semaphore.acquire()
                    try:
                        self._set_config_nosync("distr_update", None)
                    finally:
                        self._config_semaphore.release()
                    
        except:
            self._config_semaphore.acquire()
            try:
                if not firstchk and adu is not None:
                    self._set_config_nosync("distr_update",None)
            finally:
                self._config_semaphore.release()
            e = utils.get_exception()
            self.write_info("Distr updating error: " + utils.exception_to_string(e))
        
        if brestoreses:
            self._sessions_semaphore.acquire()
            try:
                if not bret:
                    self._sessions_update_status=""
                else:
                    self._sessions_update_status="REBOOT"
                self._sessions_semaphore.notify_all()                    
            finally:
                self._sessions_semaphore.release()
        
        return bret
    
    def _finalize_distr_update(self):
        if utils.path_exists(".srcmode"):
            return
        
        #CHECK IF UPDATE COMPLETE CORRECTLY
        bupdst="OK"
        if utils.path_exists("updater.status"):
            f=None
            try:                
                f = utils.file_open("updater.status", 'r')
                bupdst=f.read()
            except:
                bupdst="ERROR"
            finally:
                if f is not None:
                    f.close()
                if bupdst!="ERROR":
                    utils.path_remove("updater.status")
        
        self._config_semaphore.acquire()
        try:
            adu=self._get_config_nosync("distr_update")
            if adu is not None:
                self._set_config_nosync("distr_update",None)
                if bupdst!="OK":
                    self.write_info("Updater failed.")
        finally:
            self._config_semaphore.release()            
        
                
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
        
        #FIX OLD VERSION 2024-05-30
        try:
            if is_linux():
                import stat
                pthas = u"/etc/xdg/autostart/dwagent_systray.desktop"
                if os.path.exists(pthas):
                    pthasstat = os.stat(pthas)
                    if bool(pthasstat.st_mode & stat.S_IWOTH) or bool(pthasstat.st_mode & stat.S_IWGRP):
                        os.chmod(pthas, stat.S_IRUSR + stat.S_IWUSR + stat.S_IRGRP + stat.S_IROTH)
        except:
            None
        #FIX OLD VERSION 2024-05-30
        
        #UPDATE UI LIBRARIES
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
        
        return bupdst
        
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
        
    def _reload_config(self):
        self._config_semaphore.acquire()
        try:
            self._cnt = 0
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
            self._cnt = 0
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
    
    def _set_elapsed_cnt(self,v):
        self._config_semaphore.acquire()
        try:
            self._cnt=v
        finally:
            self._config_semaphore.release()
    
    def _is_elapsed_max(self):
        self._config_semaphore.acquire()
        try:            
            if self._cnt>0:
                self._cnt-=1
                return False
            else:
                self._cnt=self._cnt_max
                return True
        finally:
            self._config_semaphore.release()
    
    def start(self):
        self.write_info("Start agent manager")
        ipc.initialize()
        
        #Start Profiler
        profcfg = None
        try:
            profcfg = read_json_file("config.json")
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
            #Read pid
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
                #Create .start
                f = utils.file_open("dwagent.start", 'wb')
                f.close()            
        
        #GUI LAUNCHER OLD VERSION 03/11/2021 (DO NOT REMOVE)
        if is_mac() and not self._runonfly:
            try:
                self.get_osmodule().init_guilnc(self)
            except:
                ge = utils.get_exception()
                self.write_except(ge, "INIT GUI LNC: ")
                
        if not utils.path_exists("native"):
            utils.path_makedirs("native")
                
        self._task_pool = communication.ThreadPool("Task", 50, 30, self.write_except)
        self._http_socket_pool=communication.HttpConnectionSocketPoll()
        self._http_socket_pool.start()
        
        bfirstreadconfig=True
        self._update_ready_reboot=False
        try:                        
            
            #Check for incomplete update
            if utils.path_exists("update"):
                self.write_info("Update incomplete: If the problem persists, try restarting the OS or reinstalling the Agent.")
                self._update_ready_reboot=True
                self._set_elapsed_cnt(30)
                while self.is_run() and not self._is_elapsed_max():
                    time.sleep(1)
                
            while self.is_run() is True and not self._is_reboot_agent() and not self._update_ready_reboot:
                if self._is_elapsed_max():
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
                                #FINALIZE DISTR UPDATE
                                bupdst=self._finalize_distr_update()
                                if bupdst=="ERROR":
                                    self.write_info("Update error: If the problem persists, try restarting the OS or reinstalling the Agent.")
                                    self._set_elapsed_cnt(30)
                                    while self.is_run() and not self._is_elapsed_max():
                                        time.sleep(1)
                                    break
                                #LOAD DEBUG MODE
                                self._agent_debug_mode = self.get_config('debug_mode',False)
                                if self._agent_debug_mode:
                                    self._logger.set_level(utils.LOGGER_DEBUG)
                                    if self._agent_profiler is not None:
                                        prfcfg={}
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
                    
                    #Read configurations
                    if self._config is not None:
                        if self._runonfly and self._agent_last_error is not None and self._agent_last_error=="#NEW_INSTALLER_REQUIRED":
                            self._runonfly_conn_retry=0
                        else:
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
                                    if self._get_connection_info() is True:
                                        if self._run_agent() is True:
                                            if self._runonfly:
                                                self._runonfly_conn_retry=0
                                            self._set_elapsed_cnt(random.randrange(self._cnt_min, self._cnt_max)) #Avoid reconnections at the same time
                                        elif self._agent_last_error is not None and self._agent_last_error=="#NODE_NOT_AVAILABLE":
                                            self._set_elapsed_cnt(2) #try reconnection after 2 seconds
                                elif not self._agent_missauth:
                                    self.write_info("Agent authentication configuration is missing.")
                                    self._agent_missauth=True
                                self._agent_status = self._STATUS_OFFLINE
                    if not self._update_ready_reboot and self._runonfly:
                        appst=self._runonfly_ipc.get_property("status")
                        if self._runonfly_runcode is not None and appst=="RUNCODE_NOTFOUND":
                            while self.is_run() is True and not self._is_reboot_agent() and not self._update_ready_reboot: #WAIT CLOSE INSTALLER
                                time.sleep(1)
                        elif self._agent_last_error is None or self._agent_last_error!="#NEW_INSTALLER_REQUIRED":
                            self._runonfly_conn_retry+=1
                            self._update_onfly_status("WAIT:" + str(self._runonfly_conn_retry))
                time.sleep(1)
        except KeyboardInterrupt:
            self.destroy()            
        except:
            ex=utils.get_exception()
            self.destroy()
            self.write_except(ex, "AGENT: ")

        self._close_all_sessions()
        self._task_pool.destroy()
        self._task_pool = None
        if self._http_socket_pool is not None:
            self._http_socket_pool.destroy()
            self._http_socket_pool.join(2)
            self._http_socket_pool=None
        
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
            self._truncate_service_log()
            if self._noctrlfile==True:
                return not self._bstop
            else:
                if utils.path_exists("dwagent.stop"):
                    return False
                if self._svcpid is not None:
                    if not self._check_pid(self._svcpid):
                        return False
                return self._brun
    
    def _truncate_service_log(self):
        try:
            if self._truncate_service_log_enable==True:
                if self._truncate_service_log_counter.is_elapsed():
                    self._truncate_service_log_counter.reset()
                    pthslg="native" + utils.path_sep + "service.log"
                    if utils.path_exists(pthslg):
                        sz=utils.path_size(pthslg)
                        if sz>=1*1024*1024:
                            with open(pthslg, "r+") as f:
                                f.truncate(0)
        except:
            self._truncate_service_log_enable=False
        
    
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
            
            #KEEP COMPATIBILITY WITH OLD FOLDERS RUNONFLY
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
        return m

    def _get_prop_conn(self):        
        prop_conn = {}
        prop_conn['host'] = self._agent_server
        prop_conn['port'] = self._agent_port
        prop_conn['instance'] = "dwservice"        
        prop_conn['localeID'] = "en_US"
        prop_conn['version'] = "1.2.5_80"
        prop_conn['ostype'] = str(get_os_type_code())
        if self._agent_installer_ver is not None:
            prop_conn['installerver'] = self._agent_installer_ver
        prop_conn["distrID"]=str(self._get_agent_distr_id())
        return prop_conn

    def _run_agent(self):
        if self._check_and_update_distr(True):
            return False
        self._agent_last_error=None
        if self._runonfly:
            self.write_info("Initializing agent (node: " + self._agent_server + ")..." )
        else:
            self.write_info("Initializing agent (key: " + self._agent_key + ", node: " + self._agent_server + ")..." )
        try:
            appconn = None
            try:
                self._agent_last_error=None
                prop_conn=self._get_prop_conn()
                prop_conn["userName"]='AG' + self._agent_key
                prop_conn["password"]=self._agent_password
                appconn = Connection(self, None, prop_conn, self.get_proxy_info())
                self._agent_conn=AgentConn(self, appconn)
            except:
                ee = utils.get_exception()
                if utils.is_connection_refused_exception(ee):
                    self._agent_last_error="#CONNECTION_REFUSED"
                else:
                    self._agent_last_error=str(ee)
                try:
                    if appconn is not None:
                        appconn.close()
                except:
                    self.write_except(utils.get_exception(), "Close connection")
                try:
                    if not self._runonfly:
                        try:
                            if not self._agent_last_error.startswith("#LIMIT_") and not self._agent_last_error=="#ALREADY_ONLINE":
                                lstnodes = self.get_config("nodes")
                                lstnodes.pop(0)
                                if len(lstnodes)==0:
                                    lstnodes=None
                                self._set_config("nodes", lstnodes)
                        except:
                            None
                    elif self._runonfly_runcode==None:
                        if self._agent_last_error=="#ALREADY_ONLINE":
                            try:
                                if "preferred_run_user" in self._config:
                                    self._set_config("preferred_run_user",None)
                            except:
                                None
                except:
                    None
                raise ee
            self._sessions_semaphore.acquire()
            try:
                self._sessions_update_status=""
            finally:
                self._sessions_semaphore.release()
            self._unload_apps()
            #ready agent
            self._suppapps=";".join(self.get_supported_applications())
            self._update_supported_apps(True)
            m = self._get_sys_info()
            m["name"]="ready"
            m["supportedKeepAlive"]=True
            m["supportedPingStats"]=False
            m["supportedRecovery"]=self.get_config_str('recovery_session')
            m["distrID"]=str(self._get_agent_distr_id())
            self._agent_conn.send_message(m)
            if self._runonfly:
                self.write_info("Initialized agent (node: " + self._agent_server + ").")
            else:            
                self.write_info("Initialized agent (key: " + self._agent_key + ", node: " + self._agent_server + ").")                
            if self._agent_server_state=="D":
                self._agent_status = self._STATUS_ONLINE_DISABLE
            else:
                self._agent_status = self._STATUS_ONLINE
            while self.is_run() and not self._is_reboot_agent() and not self._is_reload_config() and not self._agent_conn.is_close():
                time.sleep(1)
                if self._check_and_update_distr():
                    break
                self._update_supported_apps(False)
            if self._runonfly:
                self._runonfly_user=None
                self._runonfly_password=None
        except KeyboardInterrupt:
            self.destroy()
        except:
            if self._agent_last_error is not None and self._agent_last_error.startswith("#"):
                try:
                    me=self._agent_last_error[1:]
                    if self._agent_last_error=="#CONNECTION_REFUSED":
                        me="Connection refused."
                    elif self._agent_last_error=="#ALREADY_ONLINE":
                        me="Already online."
                    elif self._agent_last_error=="#REMOVED_KEY":
                        if not self._runonfly:
                            self.remove_key()
                            me="Key no longer valid. Agent authentication configuration has been deleted."
                    elif self._agent_last_error=="#NODE_NOT_AVAILABLE":
                        me="Node " + self._agent_server + " not available."   
                    elif self._agent_last_error=="#NEW_INSTALLER_REQUIRED":
                        self._runonfly_user="ERRVER000DOWNLOAD-NEW-VERSION!"
                        self._runonfly_password="INSTALLER NOT VALID!"
                        self._update_onfly_status("CONNECTED")
                        self._runonfly_conn_retry=0
                        me = "New installer required."
                    elif self._agent_last_error=="#RUNCODE_NOTFOUND":
                        self._update_onfly_status("RUNCODE_NOTFOUND")
                        me="Run code not found."
                    self.write_info("Error initializing agent: " + me)
                except:
                    einst = utils.get_exception()            
                    self.write_except(einst)                
            else:
                einst = utils.get_exception()
                self.write_except(einst)
        finally:
            if self._agent_conn is not None:
                if self._runonfly:
                    self.write_info("Terminated agent (node: " + self._agent_server + ")." )
                else:
                    self.write_info("Terminated agent (key: " + self._agent_key + ", node: " + self._agent_server + ")." )
                try:
                    appmm = self._agent_conn
                    self._agent_conn=None                
                    appmm.close()
                except:
                    self.write_except(utils.get_exception(), "Close connection")            
        return self._agent_last_error==None

    def get_supported_applications(self):
        return applications.get_supported(self)
    
    def _update_libs_apps_file(self, tp, name, name_file):                
        rnm="agent/" + name_file
        arcv = self._get_agent_distr()["files"][rnm]
        arlv = self._get_agent_version(rnm)
        #FIX OLD VERSION 2024-01-15
        if self._fix_old_fileversions(name_file,rnm,arcv,arlv):
            return False
        #FIX OLD VERSION 2024-01-15
        if arlv is None or arcv["version"]!=arlv["version"]:
            if tp=="app":
                self.write_info("App " + name + " updating...")
            elif tp=="lib":
                self.write_info("Lib " + name + " updating...")
            arnf = name_file.split("/")                
            app_file = arnf[len(arnf)-1]
            if utils.path_exists(app_file):
                utils.path_remove(app_file)            
            app_url = "app/" + arcv["file"]
            self._download_agent_file(app_url,app_file,5)
            self._check_hash_file(app_file, arcv["md5"])
            self._unzip_file(app_file, "")
            utils.path_remove(app_file)
            self._set_agent_version(rnm,arcv)
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
            if tp=="app":
                name_file="app_" + name + ".zip"
            elif tp=="lib":
                name_file=self._agent_native_suffix + "/lib_" + name + ".zip"
            if "agent/"+name_file in self._get_agent_distr()["files"]:
                if tp=="app" and not utils.path_exists("app_" + name):
                    utils.path_makedirs("app_" + name)
                bup = self._update_libs_apps_file(tp, name, name_file)
                if bup:
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
            raise Exception("Error update " + tp + " " + name + ": " + utils.exception_to_string(e) + ". If the problem persists, try restarting the Agent or the OS.")
    
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
                fn=native.get_filename_conf(cnflib)
                if fn is not None:
                    if cnflib["refcount"]==0:
                        if "lib_dependencies" in cnflib:
                            for ln in cnflib["lib_dependencies"]:
                                self.load_lib(ln)
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
                fn=native.get_filename_conf(cnflib)
                if fn is not None:
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
            func_destroy = getattr(md, 'destroy')
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
                self._apps[name]=ret
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
            if self._agent_debug_mode:
                self.write_except(e)
            else:
                self.write_err(utils.exception_to_string(e))
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
            
    def _unload_apps_if_idle(self):
        # Same lock order as session publication: apps -> sessions. Release the
        # sessions lock before calling app destroy methods, retaining the app
        # registry lock so a new session cannot race with the idle unload.
        with self._libs_apps_semaphore:
            with self._sessions_semaphore:
                if self._sessions:
                    return
            self._unload_apps()

    def _fire_close_conn_apps(self, idconn):
        # Snapshot app instances, but never run their callbacks under either
        # the app registry lock or the global sessions lock.
        with self._libs_apps_semaphore:
            apps = list(self._apps.values())
        for md in apps:
            try:
                func = getattr(md, 'on_conn_close', None)
                if func is not None:
                    func(idconn)
            except:
                self.write_except(utils.get_exception())
    
    def _close_all_sessions(self):
        with self._sessions_semaphore:
            sessions = [(sid, ses) for sid, ses in self._sessions.items()
                        if sid not in self._sessions_closing]
            self._sessions_closing.update(sid for sid, ses in sessions)
        for sid, ses in sessions:
            try:
                try:
                    ses.close()
                finally:
                    self._fire_close_conn_apps(sid)
            except:
                self.write_err(utils.exception_to_string(utils.get_exception()))
            finally:
                with self._sessions_semaphore:
                    if self._sessions.get(sid) is ses:
                        del self._sessions[sid]
                    self._sessions_closing.discard(sid)
        self._unload_apps_if_idle()

    def open_session(self, msg):
        resp = {}
        supp_rcr = self.get_config('recovery_session',True)
        conn_rcr = None 
        appconn = None
        try:
            iconntimeout = None
            if "connectionTimeout" in msg:
                try:
                    iconntimeout=utils.Counter(int(msg["connectionTimeout"])-2)
                except:
                    None
            if iconntimeout is None:
                iconntimeout=utils.Counter(8)
            
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
            while True:
                with self._sessions_semaphore:
                    while (self._sessions_update_status == "INPROGRESS"
                           and not iconntimeout.is_elapsed()):
                        self._sessions_semaphore.wait(0.1)
                    if self._sessions_update_status != "":
                        raise Exception("Open session failed: Update in progress.")
                with self._libs_apps_semaphore:
                    with self._sessions_semaphore:
                        if self._sessions_update_status == "INPROGRESS":
                            continue
                        if self._sessions_update_status != "":
                            raise Exception("Open session failed: Update in progress.")
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
                    break
        except:
            ee = utils.get_exception()
            if appconn is not None:
                appconn.close()
            raise ee
        resp["systemInfo"]=self._get_sys_info()
        resp["supportedRecovery"]=supp_rcr
        resp["distrID"]=str(self._get_agent_distr_id())
        return resp        

    def close_session(self, ses):
        sid = ses.get_idsession()
        with self._sessions_semaphore:
            if self._sessions.get(sid) is not ses or sid in self._sessions_closing:
                return
            # Keep closing sessions registered until callbacks finish. Updates
            # and app unloading must not mistake in-flight cleanup for idle.
            self._sessions_closing.add(sid)
        try:
            self._fire_close_conn_apps(sid)
        finally:
            with self._sessions_semaphore:
                if self._sessions.get(sid) is ses:
                    del self._sessions[sid]
                self._sessions_closing.discard(sid)
        self._unload_apps_if_idle()
        
    
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
    
    def _set_header_authorization(self,hds,props):
        auth=utils.bytes_to_str(utils.enc_base64_encode(utils.str_to_bytes(self._agent_key + ":" + props["key"],"utf8")))
        hds["Authorization"]="Basic %s" % (auth)

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
        self._raw = self._open_socket(self._prop_conn)
    
    def _open_socket(self, prop):
        hds = {}
        for k in prop:
            if prop[k] is not None:
                hds["dw_" + k]=prop[k]
        opts={}
        if self._proxy_info is not None:
            opts["proxy_info"]=self._proxy_info
        opts["send_keepalive"]={"intervall":30, "threshold":5}
        opts["events"]={"on_data": self._on_data, "on_close": self._on_close, "on_except" : self._on_except}
        r = communication.WebSocket("https://" + prop['host'] + ":" + prop['port'] + "/openraw.dw",hds,opts)
        r.open()
        return r
    
    def send(self,data):        
        self._raw.send_bytes(data)
    
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
            
    #def _on_data(self, dt):
    def _on_data(self, tp, dt):
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
                        self._raw = self._open_socket(prop)
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
        self._intervall=0
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
        self._bdestroy=False
    
    def get_connection(self, sid):
        if self._bdestroy:
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
        if self._bdestroy:
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
        if self._bdestroy:
            return
        self._bdestroy=True
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
                cntRequestReceived=msg["cntRequestReceived"]
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
            if bfsz>communication.WebSocket.FRAME_SIZE_MAX:
                bfsz=communication.WebSocket.FRAME_SIZE_MAX
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
                ba.extend(dt)
                self._send_conn(self._conn, ba)
                break
            except:
                e = utils.get_exception()
                print(e)
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
            if tm is not None:
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
                if "state" in msg:
                    self._agent._agent_server_state=msg["state"]
                    if self._agent._agent_server_state=="D":
                        self._agent._agent_status = self._agent._STATUS_ONLINE_DISABLE
                    else:
                        self._agent._agent_status = self._agent._STATUS_ONLINE
                if "agentName" in msg:
                    self._agent._agent_name=msg["agentName"]
                if "currentDistrID" in msg:
                    try:                        
                        self._agent._set_distr_update(int(msg["currentDistrID"]))
                    except:
                        None
                if self._agent._runonfly:
                    if "runOnFlyAgentID" in msg:
                        self._agent._agent_key=msg["runOnFlyAgentID"]
                        rnus=self._agent._agent_key[4:]
                        if self._agent._runonfly_user!=rnus:
                            self._agent._runonfly_user=rnus
                            if self._agent._runonfly_runcode is None:
                                try:
                                    if "preferred_run_user" not in self._agent._config or self._agent._config["preferred_run_user"]!=self._agent._runonfly_user:
                                        self._agent._set_config("preferred_run_user",self._agent._runonfly_user)
                                except:
                                    None
                            self._agent._runonfly_password=self._agent._runonfly_password_stored
                    if "runOnFlyAgentPassword" in msg:
                        self._agent._agent_password=msg["runOnFlyAgentPassword"]
                                                
                    self._agent._update_onfly_status("CONNECTED")
                    self._agent._runonfly_conn_retry=0                    
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
            elif msg_name=="openSession":
                resp=self._agent.open_session(msg)
            if resp is not None:
                self.send_response(msg, resp)
        except:
            e = utils.get_exception()
            if self._agent._agent_debug_mode:
                self._agent.write_except(e)            
            else:
                self._agent.write_err(utils.exception_to_string(e))
            if 'requestKey' in msg:
                m = {
                    'name': 'error',
                    'requestKey':  msg['requestKey'],
                    'class':  e.__class__.__name__,
                    'message':  utils.exception_to_string(e)
                }
                try:
                    self.send_message(m)
                except:
                    e = utils.get_exception()
                    if self._agent._agent_debug_mode:
                        self._agent.write_except(e)

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
                if "url" in msg:
                    self.send_message(self._download(msg))
                else:
                    self.send_message(self._downloadOLD(msg))
            elif msg_name=="upload":
                if "url" in msg:
                    self.send_message(self._upload(msg))
                else:
                    self.send_message(self._uploadOLD(msg))
            elif msg_name=="websocket":
                if "url" in msg:
                    self.send_message(self._websocket(msg))
                else:
                    self.send_message(self._websocketOLD(msg))
            elif msg_name=="websocketsimulate": #OLD
                self.send_message(self._websocketsimulate(msg))
            else:
                raise Exception("Invalid message name: " + msg_name)                
        except:
            e = utils.get_exception()            
            if self._agent._agent_debug_mode:
                self._agent.write_except(e)
            else:
                self._agent.write_err(utils.exception_to_string(e))
            if 'requestKey' in msg:
                self.send_response_error(msg,e.__class__.__name__ ,utils.exception_to_string(e))
            
    def _load_app(self, msg):
        resp = ""
        try:
            app_name = msg["parameter_name"]
            self._agent.get_app(app_name)
            resp = "K:null"
        except:
            e = utils.get_exception()
            m = utils.exception_to_string(e)
            self._agent.write_err(m)
            resp=  ":".join(["E", m])
        return resp
    
    def _request(self, msg):
        resp = ""
        try:
            app_name = msg["module"]
            cmd_name = msg["command"]
            if app_name=="core":
                if cmd_name=="load_app":
                    return self._load_app(msg)
                else:
                    raise Exception('Command ' + cmd_name + ' not found in core.')
            else:
                cmd_name = msg["command"]
                params = {}
                params["requestKey"]=msg['requestKey']
                sck = "parameter_"
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
        wsock = WebSocket(self, msg)
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
            raise e
        resp['name']='response'
        resp['requestKey']=msg['requestKey']
        return resp
    
    def _websocketOLD(self, msg):        
        rid=msg["idRaw"]
        conn = self._cpool.get_connection(rid) 
        if conn is None:
            raise Exception("Connection not found (id: " + rid + ")")
        wsock = WebSocketOLD(self,conn, msg)
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
        fdownload = Download(self, msg)
        resp = {}   
        try:
            self._agent.invoke_app(msg['module'],  "download",  self,  fdownload)
            if not fdownload.is_accept():
                raise Exception("Download file not accepted")
        except:
            e = utils.get_exception()
            try:
                fdownload.close()
            except:
                None
            raise e
        resp['name']='response'
        resp['requestKey']=msg['requestKey']
        return resp
    
    def _upload(self, msg):
        fupload = Upload(self, msg)
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
            raise e
        resp['name']='response'
        resp['requestKey']=msg['requestKey']
        return resp
    
    def _downloadOLD(self, msg):
        rid=msg["idRaw"]
        conn = self._cpool.get_connection(rid) 
        if conn is None:
            raise Exception("Connection not found (id: " + rid + ")")
        fdownload = DownloadOLD(self, conn, msg)
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
    
    def _uploadOLD(self, msg):
        rid=msg["idRaw"]
        conn = self._cpool.get_connection(rid) 
        if conn is None:
            raise Exception("Connection not found (id: " + rid + ")")
        fupload = UploadOLD(self, conn, msg)
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
    DATA_BYTES = ord('b')
    
    def __init__(self, parent, props):
        self._parent=parent
        self._agent=self._parent._agent 
        self._props=props
        self._baccept=False
        self._bclose=False
        self._app_on_close=None
        self._app_on_data=None
        self._wsock=None
        self._simulate=self._props["simulate"]
    
    def accept(self, priority, events):
        if events is not None:
            if "on_close" in events:
                self._app_on_close = events["on_close"]
            if "on_data" in events:
                self._app_on_data = events["on_data"]
        
        hds = {}
        self._agent._set_header_authorization(hds,self._props)
        opts={}
        if self._parent._conn._proxy_info is not None:
            opts["proxy_info"]=self._parent._conn._proxy_info
        opts["events"]={"on_data": self._on_data, "on_close": self._on_close, "on_except" : self._on_except}        
        opts["bandwidth_calculator_send"]=self._parent._bwsendcalc
        opts["http_socket_pool"]=self._agent._http_socket_pool
        if not self._simulate:        
            self._wsock = communication.WebSocket(self._props["url"],hds,opts)
        else:            
            self._wsock = communication.WebSocketSimulate(self._props["url"],hds,opts)
        self._wsock.open()        
        self._baccept=True
                
    
    def is_accept(self):
        return self._baccept
    
    def get_properties(self):
        return self._props
    
    def _on_data(self, tp, dt):
        self._parent._set_last_activity_time()
        if self._app_on_data is not None:
            self._app_on_data(self, tp, dt)            
    
    def _on_close(self):
        if self._app_on_close is not None:
            self._app_on_close()
    
    def _on_except(self, e):
        self._agent.write_except(e)        
    
    def get_send_buffer_size(self):
        bsz = self._parent.get_send_buffer_size()
        if not self._simulate and bsz>self._wsock.FRAME_SIZE_MAX:
            bsz=self._wsock.FRAME_SIZE_MAX
        return bsz
    
    def send_list_string(self,data):
        self._parent._set_last_activity_time()
        for i in range(len(data)):
            self._wsock.send_string(data[i])
    
    def send_list_bytes(self,data):
        self._parent._set_last_activity_time()
        for i in range(len(data)):
            self._wsock.send_bytes(data[i])
    
    def send_string(self,data):
        self._parent._set_last_activity_time()
        self._wsock.send_string(data)        
    
    def send_bytes(self,data):
        self._parent._set_last_activity_time()        
        self._wsock.send_bytes(data)
    
    def is_close(self):
        return self._wsock.is_close()
    
    def close(self):
        self._wsock.close()
    

class WebSocketOLD:
    DATA_STRING = ord('s')
    DATA_BYTES = ord('b')
    
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
                self._data.extend(data)
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
                        self._len=-1
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
                ba.extend(bytearray(st.pack(len(dt)+1,WebSocketOLD.DATA_STRING)))
                ba.extend(utils.str_to_bytes(dt,"utf8"))
            self._parent._send_conn(self._conn,ba)
    
    def send_list_bytes(self,data):
        self._parent._set_last_activity_time()
        if not self._bclose:
            st=struct.Struct("!IB")
            ba=bytearray()
            for i in range(len(data)):
                dt=data[i]
                ba.extend(bytearray(st.pack(len(dt)+1,WebSocketOLD.DATA_BYTES)))
                ba.extend(dt)
            self._parent._send_conn(self._conn,ba)
    
    def send_string(self,data):
        self._parent._set_last_activity_time()
        if not self._bclose:            
            ba=bytearray(struct.pack("!IB",len(data)+1,WebSocketOLD.DATA_STRING))
            ba.extend(utils.str_to_bytes(data,"utf8"))
            self._parent._send_conn(self._conn,ba)
    
    def send_bytes(self,data):
        self._parent._set_last_activity_time()
        if not self._bclose:
            ba=bytearray(struct.pack("!IB",len(data)+1,WebSocketOLD.DATA_BYTES))
            ba.extend(data)
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


#OLD TO REMOVE
class WebSocketSimulate:
    DATA_STRING = 's'
    DATA_BYTES = 'b'
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
                        #Send responses
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
                                lensend += len(sdt["data"])
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
    
    def __init__(self, parent, props):
        self._parent=parent
        self._agent=self._parent._agent
        self._props=props
        self._path=None
        self._name=None
        self._bclose = False
        self._baccept=False
        self._status="I"
        self._httpupl=None
    
    def accept(self, path):
        self._path=path
        self._name=utils.path_basename(self._path)
        self._status="T"
        self._baccept=True        
        hds = {}
        self._agent._set_header_authorization(hds,self._props)
        opts={}
        if self._parent._conn._proxy_info is not None:
            opts["proxy_info"]=self._parent._conn._proxy_info
        opts["events"]={"on_start": self._on_start, "on_progress": self._on_progress, "on_complete" : self._on_complete, "on_except" : self._on_except}        
        opts["bandwidth_calculator_send"]=self._parent._bwsendcalc
        opts["http_socket_pool"]=self._agent._http_socket_pool        
        self._httpupl = communication.HttpUpload(self._props["url"],self._path,hds,opts)
        self._httpupl.start()
    
    def is_accept(self):
        return self._baccept
    
    def get_properties(self):
        return self._props
    
    def get_name(self):
        return self._name
        
    def get_path(self):
        return self._path
        
    def get_status(self):
        return self._status
    
    def close(self):
        if self._httpupl is not None:
            self._httpupl.close()
    
    def is_close(self):
        return self._bclose
            
    def _on_start(self):        
        self._parent.inc_activities_value("downloads")
    
    def _on_progress(self, p, l, bps):
        self._parent._set_last_activity_time()        
    
    def _on_complete(self):        
        self._status="C"
        self._bclose=True
        self._parent.dec_activities_value("downloads")        
    
    def _on_except(self, e):        
        self._status="E"
        self._bclose=True
        self._parent.dec_activities_value("downloads")        
        if self._agent._agent_debug_mode:
            self._agent.write_except(e)            
        else:
            self._agent.write_err(utils.exception_to_string(e))

class Upload():
    
    def __init__(self, parent, props):
        self._parent=parent
        self._agent=self._parent._agent
        self._props=props
        self._path=None
        self._tmppath=None
        self._name=None        
        self._bclose = False
        self._baccept=False
        self._status="I"
        self._httpdwn=None
        
    def accept(self, path):
        try:
            sprnpath=utils.path_dirname(path)    
            while True:
                r="".join([random.choice("0123456789") for x in utils.nrange(6)])            
                self._tmppath=sprnpath + utils.path_sep + "temporary" + r + ".dwsupload"
                if not utils.path_exists(self._tmppath):
                    utils.file_open(self._tmppath, 'wb').close() #Crea il file per imposta i permessi
                    self._agent.get_osmodule().fix_file_permissions("CREATE_FILE",self._tmppath)
                    break
            
            self._path=path
            self._name=utils.path_basename(self._path)
            self._status="T"
            self._baccept=True
            hds = {}
            self._agent._set_header_authorization(hds,self._props)
            opts={}
            if self._parent._conn._proxy_info is not None:
                opts["proxy_info"]=self._parent._conn._proxy_info
            opts["events"]={"on_start": self._on_start, "on_progress": self._on_progress, "on_complete" : self._on_complete, "on_except" : self._on_except}        
            opts["bandwidth_calculator_send"]=self._parent._bwsendcalc
            opts["http_socket_pool"]=self._agent._http_socket_pool                        
            self._httpdwn = communication.HttpDownload(self._props["url"],self._tmppath,hds,opts)
            self._httpdwn.start()
        except:
            e = utils.get_exception()
            self._remove_temp_file()
            raise e
    
    def _remove_temp_file(self):
        if self._tmppath is not None:
            try:
                if utils.path_exists(self._tmppath):
                    utils.path_remove(self._tmppath)
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
        
    def get_status(self):
        return self._status
    
    def close(self):
        if self._httpdwn is not None:
            self._httpdwn.close()
    
    def is_close(self):
        return self._bclose
            
    def _on_start(self):        
        self._parent.inc_activities_value("uploads")        
    
    def _on_progress(self, p, l, bps):                        
        self._parent._set_last_activity_time()        
    
    def _on_complete(self):        
        self._status="C"
        self._bclose=True
        self._parent.dec_activities_value("uploads")
        shutil.move(self._tmppath, self._path)
    
    def _on_except(self, e):
        self._status="E"
        self._bclose=True
        self._parent.dec_activities_value("uploads")
        if self._agent._agent_debug_mode:
            self._agent.write_except(e)            
        else:
            self._agent.write_err(utils.exception_to_string(e))
        

class DownloadOLD():

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
            
    def _on_data_conn(self, data):
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


class UploadOLD():

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
        self._cnt_send_status=None
        try:
            sprnpath=utils.path_dirname(path)    
            while True:
                r="".join([random.choice("0123456789") for x in utils.nrange(6)])            
                self._tmpname=sprnpath + utils.path_sep + "temporary" + r + ".dwsupload"
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
                        self._enddatafile=True
                        #SCRIVE FILE
                        try:
                            utils.file_sync(self._fltmp)
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
                        lndt=len(data)-1
                        self._fltmp.write(utils.buffer_new(data,1,lndt))
                        self._calcbps.add(lndt)
                        if self._cnt_send_status is None or self._cnt_send_status.is_elapsed(0.5):
                            self._parent._send_conn(self._conn, bytearray("T" + str(self._calcbps.get_transfered()) + ";" + str(self._calcbps.get_bps()) , "utf8"))
                            if self._cnt_send_status is None:
                                self._cnt_send_status=utils.Counter()
                            else:
                                self._cnt_send_status.reset()
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
    
