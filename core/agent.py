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
import base64
import zlib
import zipfile
import gzip
import StringIO
import signal
import platform
import logging.handlers
import hashlib
import listener
import traceback
import ctypes
import shutil
import sharedmem
import importlib 
import urllib
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

def load_osmodule():
    return native.get_instance()

def unload_osmodule(omdl):
    omdl.unload_library();

def get_prop(prop,key,default=None):
    if key in prop:
        return prop[key]
    return default
        
def generate_key(n):
    c = "".join([string.ascii_lowercase, string.ascii_uppercase,  string.digits])
    return "".join([random.choice(c) 
                    for x in xrange(n)])
        
def str2bool(v):
        return v.lower() in ("yes", "true", "t", "1")    

def bool2str(v):
    if v is None or v is False:
        return 'False'
    else:
        return 'True'

def hash_password(pwd):
    encoded = hashlib.sha256(pwd).digest()
    encoded = base64.b64encode(encoded)
    return encoded

def check_hash_password(pwd, encoded_pwd):
    pwd=hash_password(pwd)
    pwd_len   = len(pwd)
    encoded_pwd_len = len(encoded_pwd)
    result = pwd_len ^ encoded_pwd_len
    if encoded_pwd_len > 0:
        for i in xrange(pwd_len):
            result |= ord(pwd[i]) ^ ord(encoded_pwd[i % encoded_pwd_len])
    return result == 0

def obfuscate_password(pwd):
    return base64.b64encode(zlib.compress(pwd))

def read_obfuscated_password(enpwd):
    return zlib.decompress(base64.b64decode(enpwd))
    
class StdRedirect(object):
    
    def __init__(self,lg,lv):
        self._logger = lg;
        self._level = lv;
        
    def write(self, data):
        for line in data.rstrip().splitlines():
            self._logger.log(self._level, line.rstrip())

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
        self._logger = logging.getLogger()
        hdlr = None
        self._noctrlfile=False
        self._bstop=False
        self._runonfly=False
        self._runonfly_conn_retry=0
        self._runonfly_user=None
        self._runonfly_password=None
        self._runonfly_runcode=None
        self._runonfly_sharedmem=None        
        self._runonfly_action=None #RIMASTO PER COMPATIBILITA' CON VECCHIE CARTELLE RUNONFLY
        for arg in args: 
            if arg=='-runonfly':
                self._runonfly=True
            elif arg=='-filelog':
                hdlr = logging.handlers.RotatingFileHandler(u'dwagent.log', 'a', 1000000, 3)
            elif arg=='-noctrlfile':
                signal.signal(signal.SIGTERM, self._signal_handler)
                self._noctrlfile=True
            elif arg.lower().startswith("runcode="):
                self._runonfly_runcode=arg[8:]
        if not self._runonfly:
            self._runonfly_runcode=None
        if hdlr is None:
            hdlr = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        hdlr.setFormatter(formatter)
        self._logger.addHandler(hdlr) 
        self._logger.setLevel(logging.INFO)
        #Reindirizza stdout e stderr
        sys.stdout=StdRedirect(self._logger,logging.DEBUG);
        sys.stderr=StdRedirect(self._logger,logging.ERROR);
        
        #Inizializza campi
        self._task_pool = None
        self._path_config='config.json'
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
        self._sharedmemserver=None
        self._httpserver=None
        self._proxy_info=None
        self._connection = None
        self._main_temp_msg = None
        self._debug_path = None
        self._debug_indentation_max=-1
        self._debug_thread_filter=None
        self._debug_class_filter="apps.*"
        self._debug_info = {}
        self._sessions={}
        self._libs={}
        self._apps={}
        self._apps_to_reload={}
        self._agent_log_semaphore = threading.Condition()
        self._connections_semaphore = threading.Condition()
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
        
        self._config_semaphore = threading.Condition()
        self._osmodule = load_osmodule();
        self._svcpid=None
        
        #Inizializza il path delle shared mem
        sharedmem.init_path()
    
    def unload_library(self):
        if self._osmodule is not None:
            unload_osmodule(self._osmodule);
            self._osmodule=None
    
    #RIMASTO PER COMPATIBILITA' CON VECCHIE CARTELLE RUNONFLY
    def set_runonfly_action(self,action):
        self._runonfly_action=action
    
    def _signal_handler(self, signal, frame):
        if self._noctrlfile==True:
            self._bstop=True
        else:
            f = utils.file_open("dwagent.stop", 'wb')
            f.close()           
    
    def _debug_trunc_msg(self, msg, sz):
        smsg="None"
        if msg is not None:
            smsg=u""
            try:
                if isinstance(msg, str):
                    smsg = unicode(msg.decode('ascii', 'ignore'))
                else:
                    smsg = str(msg)
            except Exception as e:
                smsg = u"EXCEPTION:" + unicode(utils.exception_to_string(e))
            if len(smsg)>sz:
                smsg=smsg[0:sz] + u" ..."
            smsg = smsg.replace("\n", " ").replace("\r", " ").replace("\t", "   ");
        return smsg
    
    def _debug_filter_check(self,nm,flt):
        if flt is not None:
            ar = flt.split(";")
            for f in ar:
                if f.startswith("*") and nm.endswith(f[1:]):
                    return True
                elif f.endswith("*") and nm.startswith(f[0:len(f)-1]):
                    return True
                elif nm==f:
                    return True
            return False
        return True
    
    def _debug_func(self, frame, event, arg): 
        #sys._getframe(0)
        if event == "call" or event == "return":
            try:
                bshow = True
                fcode = frame.f_code
                flocs = frame.f_locals
                fn = utils.path_absname(unicode(fcode.co_filename))
                if not fcode.co_name.startswith("<") and fn.startswith(self._debug_path):
                    fn = fn[len(self._debug_path):]
                    fn = fn.split(".")[0]
                    fn = fn.replace(utils.path_sep,".")
                    nm = fcode.co_name
                    if flocs is not None and "self" in flocs:
                        flocssf=flocs["self"]
                        nm = flocssf.__class__.__name__ + "." +nm
                    nm=fn + u"." + nm
                    thdn = threading.current_thread().name
                    if thdn not in self._debug_info:
                        self._debug_info[thdn]={}
                        self._debug_info[thdn]["time"]=[]
                        self._debug_info[thdn]["indent"]=0
                    debug_time=self._debug_info[thdn]["time"]
                    debug_indent=self._debug_info[thdn]["indent"]                    
                    bshow=self._debug_indentation_max==-1 or debug_indent<=self._debug_indentation_max
                    #THREAD NAME
                    if bshow:
                        bshow=self._debug_filter_check(thdn, self._debug_thread_filter)
                    #CLASS NAME
                    if bshow:
                        bshow=self._debug_filter_check(nm, self._debug_class_filter)
                    #VISUALIZZA
                    if bshow:
                        if event == "return":
                            debug_indent -= 1
                        soper=""
                        arpp = []
                        if event == "call":
                            soper="INIT"
                            debug_time.append(long(time.time() * 1000))
                            if flocs is not None:
                                sarg=[]
                                for k in flocs:
                                    if not k is "self":
                                        sarg.append(unicode(k.decode('ascii', 'ignore')) + u"=" + self._debug_trunc_msg(flocs[k], 20))
                                if len(sarg)>0:
                                    arpp.append(u"args: " + u",".join(sarg))
                            
                        elif event == "return":
                            soper="TERM"
                            tm = debug_time.pop()
                            arpp.append(u"time: " + str(long(time.time() * 1000) - tm) + u" ms")
                            arpp.append(u"return: " + self._debug_trunc_msg(arg, 80))
                                
                        armsg=[]
                        armsg.append(u"   "*debug_indent + nm + u" > " + soper)
                        if len(arpp)>0:
                            armsg.append(u" ")
                            armsg.append(u"; ".join(arpp))
                        self.write_debug(u"".join(armsg))
                        if event == "call":
                            debug_indent += 1
                        self._debug_info[thdn]["indent"]=debug_indent
            except Exception as e:
                self.write_except(e)
    
    def _write_config_file(self):
        s = json.dumps(self._config, sort_keys=True, indent=1)
        f = utils.file_open(self._path_config, 'wb')
        f.write(s)
        f.close()
        
    def _read_config_file(self):
        self._config_semaphore.acquire()
        try:
            try:
                f = utils.file_open(self._path_config)
            except Exception as e:
                self.write_err("Error reading config file. " + utils.exception_to_string(e));
                self._config = None
                return
            try:
                self._config = json.loads(f.read())
                self.write_info("Readed config file.");
            except Exception as e:
                self.write_err("Error parse config file: " + utils.exception_to_string(e));
                self._config = None
            finally:
                f.close()
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
        self._connections_semaphore.acquire()
        try:
            return len(self._sessions)
        finally:
            self._connections_semaphore.release()
    
    def get_active_session_count(self, ckint=30):
        cnt=0;
        self._connections_semaphore.acquire()
        try:
            tm = time.time()
            for sid in self._sessions.keys():
                if tm-self._sessions[sid].get_last_activity_time()<=ckint:
                    cnt+=1
        finally:
            self._connections_semaphore.release()
        return cnt
    
    def _load_config(self):
        #self.write_info("load configuration...");
        #VERIFICA agentConnectionPropertiesUrl
        self._agent_url_primary = self._get_config('url_primary', None)
        if self._agent_url_primary  is None:
            self.write_info("Missing url_primary configuration.");
            return False
        if not self._runonfly:
            self._agent_key = self._get_config('key', None)
            self._agent_password = self._get_config('password', None)
        else:
            self._agent_key = None
            self._agent_password = None
        return True
    
    
    def _load_agent_properties(self):
        self.write_info("Reading agent properties...");
        try:
            app_url = None
            prp_url = None
            if not self._runonfly:
                if self._agent_key is None or self._agent_password is None:
                    return False
                self._agent_password = read_obfuscated_password(self._agent_password)
                app_url = self._agent_url_primary + "getAgentProperties.dw?key=" + self._agent_key
            else:
                spapp = ";".join(self.get_supported_applications())
                app_url = self._agent_url_primary + "getAgentPropertiesOnFly.dw?osTypeCode=" + str(get_os_type_code()) +"&supportedApplications=" + urllib.quote_plus(spapp)
                if self._runonfly_runcode is not None:
                    app_url += "&runCode=" + urllib.quote_plus(self._runonfly_runcode)
                elif "preferred_run_user" in self._config:
                    app_url += "&preferredRunUser=" + urllib.quote_plus(self._config["preferred_run_user"])
            try:
                prp_url = communication.get_url_prop(app_url, self.get_proxy_info())
                if "error" in prp_url:
                    self.write_info("Error read agentUrlPrimary: " + prp_url['error']);
                    if prp_url['error']=="INVALID_KEY":
                        if not self._runonfly:
                            self.remove_key();
                    if self._runonfly_runcode is not None and prp_url['error']=="RUNCODE_NOTFOUND":
                        self._update_onfly_status("RUNCODE_NOTFOUND");
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
                                        
            except Exception as e:
                self.write_info("Error reading agentUrlPrimary: " + utils.exception_to_string(e));
                return False
                
            appst = get_prop(prp_url, 'state', None)
            if appst=="D":
                self.write_info("Agent disabled.")
                return False
            elif appst=="S":
                self.write_info("Agent suppressed.")
                if not self._runonfly:
                    self.remove_key();
                return False
            self._agent_server = get_prop(prp_url, 'server', None)
            if self._agent_server is None:
                self.write_info("Missing server configuration.")
                return False
            self._agent_port = get_prop(prp_url, 'port', "7730")
            self._agent_method_connect_port = get_prop(prp_url, 'methodConnectPort', None)
            self._agent_instance = get_prop(prp_url, 'instance', None)
            if self._agent_instance is None:
                self.write_info("Missing instance configuration.")
                return False
            self._agent_version= get_prop(prp_url, 'agentVersion', None)
            
            
            self.write_info("Primary url: " + self._agent_url_primary)
            self.write_info("Proxy: " + self.get_proxy_info().get_type())
            self.write_info("Readed agent properties.")
            return True
        except Exception as e:
            self.write_info("Error reading agentUrlPrimary: " + utils.exception_to_string(e));
            return False
    
    def set_config_password(self, pwd):
        self._config_semaphore.acquire()
        try:
            self._config['config_password']=hash_password(pwd)
            self._write_config_file()
        finally:
            self._config_semaphore.release()
    
    def check_config_auth(self, usr, pwd):
        cp=self._get_config('config_password', hash_password(""))
        return usr=="admin" and pwd==cp
    
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
        url = self._agent_url_primary + "installNewAgent.dw?user=" + urllib.quote_plus(user) + "&password=" + urllib.quote_plus(password) + "&name=" + urllib.quote_plus(name) + "&osTypeCode=" + str(get_os_type_code()) +"&supportedApplications=" + urllib.quote_plus(spapp)
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
        url = self._agent_url_primary + "checkInstallCode.dw?code=" + urllib.quote_plus(code) + "&osTypeCode=" + str(get_os_type_code()) +"&supportedApplications=" + urllib.quote_plus(spapp)
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
    
    
    def _get_config(self, key, default=None):
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
            return bool2str(self._get_config(key))
        elif (key=="key"):
            v = self._get_config(key)
            if v is None:
                v=""
            return v
        elif (key=="proxy_type"):
            return self._get_config(key, "SYSTEM")
        elif (key=="proxy_host"):
            return self._get_config(key, "")
        elif (key=="proxy_port"):
            v = self._get_config(key)
            if v is None:
                return ""
            else:
                return str(v)
        elif (key=="proxy_user"):
            return self._get_config(key, "")
        elif (key=="monitor_tray_icon"):
            v = self._get_config(key)
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
        elif (key=="monitor_tray_icon"):
            b=str2bool(val)
            self._set_config(key, b)
        else:
            raise Exception("INVALID_CONFIG_KEY")
    
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
                #print "UNZIP:" + nm
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
                self.write_info("Downloaded file update " + name_file + ".")
                return True
        return False
    
    def _monitor_update_file_create(self):
        try:
            if not utils.path_exists("monitor.update"):
                stopfile= utils.file_open("monitor.update", "w")
                stopfile.close()
                time.sleep(5)
        except Exception as e:
            self.write_except(e)
    
    def _monitor_update_file_delete(self):
        try:
            if utils.path_exists("monitor.update"):
                utils.path_remove("monitor.update") 
        except Exception as e:
            self.write_except(e)
                
    def _check_update(self):
        #IN SVILUPPO NON DEVE AGGIORNARE
        if utils.path_exists(".srcmode"):
            return True
        if self._is_reboot_agent() or self._update_ready:
            return False
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
                '''
                DA ELIMINARE IN SEGUITO
                if utils.path_exists("images"):
                    lst=utils.path_list("images")
                    for fname in lst:
                        if not (fname == "logo.ico" or fname == "logo.icns" or fname == "logo.png"):
                            utils.path_remove("images" + utils.path_sep + fname)
                '''
            except:
                None
            #FIX OLD VERSION 2018-12-20
            
            
            #Verifica se è presente un aggiornamento incompleto
            if utils.path_exists("update"):
                self.write_info("Update incomplete: Needs reboot.")
                self._update_ready=True
                return False
                
            #LEGGE 'fileversions.json'
            f = utils.file_open('fileversions.json')
            cur_vers = json.loads(f.read())
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
            except Exception as e:
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
            self._check_update_file(cur_vers, rem_vers, "agent.zip",  "updateTMP" + utils.path_sep)
            if not self._runonfly and not self._agent_native_suffix=="linux_generic":
                if self._check_update_file(cur_vers, rem_vers, "agentui.zip",  "updateTMP" + utils.path_sep):
                    self._monitor_update_file_create()
            self._check_update_file(cur_vers, rem_vers, "agentapps.zip",  "updateTMP" + utils.path_sep)
                                    
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
                f.write(s)
                f.close()
                shutil.move("updateTMP", "update")
                self.write_info("Update ready: Needs reboot.")
                self._update_ready=True
                return False
        except Exception as e:
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
            self._breloadagentcnt=communication.Counter(ms)
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
        
        #Carica native suffix        
        self._agent_native_suffix=detectinfo.get_native_suffix()

        #Scrive info nel log
        appuname=None
        try:
            appuname=str(platform.uname())
            if len(appuname)>=2:
                appuname=appuname[1:len(appuname)-1]
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
            self._runonfly_sharedmem=sharedmem.Property()
            self._runonfly_sharedmem.create("runonfly", fieldsdef)
            self._runonfly_sharedmem.set_property("status", "CONNECTING")
            self._runonfly_sharedmem.set_property("user", "")
            self._runonfly_sharedmem.set_property("password", "")
            self._runonfly_sharedmem.set_property("pid", str(os.getpid()))
        
        if not self._runonfly or self._runonfly_action is None:
            #Legge pid
            self._check_pid_cnt=0
            self._svcpid=None
            if utils.path_exists("dwagent.pid"):
                try:
                    f = utils.file_open("dwagent.pid")
                    spid = f.read()
                    f.close()
                    self._svcpid = int(spid)
                except Exception:
                    None
            
            if self._noctrlfile==False:
                #Crea il file .start
                f = utils.file_open("dwagent.start", 'wb')
                f.close()
            
        
        if is_mac() and not self._runonfly:
            try:
                self.get_osmodule().init_guilnc(self)
            except Exception as ge:
                self.write_except(ge, "INIT GUI LNC: ")
                
        #Crea cartelle necessarie
        if not utils.path_exists("native"):
            utils.path_makedirs("native")
                
        #Crea taskpool
        self._task_pool = communication.ThreadPool("Task", 50, 30, self.write_except)
        
        #Avvia agent status
        if not self._runonfly:
            try:
                self._sharedmemserver=listener.SharedMemServer(self)
                self._sharedmemserver.start()
            except Exception as asc:
                self.write_except(asc, "INIT STATUSCONFIG LISTENER: ")
        self._update_ready=False
        
        bfirstreadconfig=True
        while self.is_run() is True and not self._is_reboot_agent() and not self._update_ready:
            if self._elapsed_max():
                communication.release_detected_proxy()
                if self._runonfly:
                    self._update_onfly_status("CONNECTING")
                #Ricarica il config file
                if self._is_reload_config():
                    self._read_config_file()
                    if self._config is not None:
                        self._reload_config_reset()
                        if bfirstreadconfig:
                            bfirstreadconfig=False
                            #CARICA DEBUG MODE
                            self._agent_debug_mode = self._get_config('debug_mode',False)
                            self._debug_indentation_max = self._get_config('debug_indentation_max',self._debug_indentation_max)
                            self._debug_thread_filter = self._get_config('debug_thread_filter',self._debug_thread_filter)
                            self._debug_class_filter = self._get_config('debug_class_filter',self._debug_class_filter)
                            if self._agent_debug_mode:
                                self._logger.setLevel(logging.DEBUG)
                                self._debug_path=os.getcwdu();
                                if not self._debug_path.endswith(utils.path_sep):
                                    self._debug_path+=utils.path_sep
                                threading.setprofile(self._debug_func)
                            
                            
                        
                
                #Avvia il listener (PER USI FUTURI)
                if not self._runonfly:
                    if self._httpserver is None:
                        try:
                            self._httpserver = listener.HttpServer(self._get_config('listen_port', 7950), self)
                            self._httpserver.start()                
                        except Exception as ace:
                            self.write_except(ace, "INIT LISTENER: ")
                        
                self._reboot_agent_reset()
                
                #Legge la configurazione
                skiponflyretry=False
                if self._config is not None:
                    self._agent_enabled = self._get_config('enabled',True)
                    if self._agent_enabled is False:
                        if self._agent_status != self._STATUS_DISABLE:
                            self.write_info("Agent disabled")
                            self._agent_status = self._STATUS_DISABLE
                    elif self._load_config() is True:
                        if self._runonfly or (self._agent_key is not None and self._agent_password is not None):
                            self._agent_missauth=False
                            self.write_info("Agent enabled")
                            self._agent_status = self._STATUS_UPDATING
                            #Verifica se ci sono aggiornamenti
                            if self._check_update() is True:
                                if self._load_agent_properties() is True:                                    
                                    if self._run_agent() is True and self._get_config('enabled',True):
                                        self._cnt = self._cnt_max
                                        self._cnt_random = random.randrange(self._cnt_min, self._cnt_max) #Evita di avere connessioni tutte assieme
                                        skiponflyretry=True
                        elif not self._agent_missauth:
                            self.write_info("Missing agent authentication configuration.");
                            self._agent_missauth=True
                        self._agent_status = self._STATUS_OFFLINE
                if not self._update_ready and self._runonfly:                    
                    appst=self._runonfly_sharedmem.get_property("status")
                    if self._runonfly_runcode is not None and appst=="RUNCODE_NOTFOUND":
                        while self.is_run() is True and not self._is_reboot_agent() and not self._update_ready: #ATTENDE CHIUSURA INSTALLER
                            time.sleep(1)
                    elif skiponflyretry==False:
                        self._runonfly_conn_retry+=1
                        self._update_onfly_status("WAIT:" + str(self._runonfly_conn_retry))
            time.sleep(1)
        self._task_pool.destroy()
        self._task_pool = None
        
        if self._httpserver is not None:
            try:
                self._httpserver.close()
            except Exception as ace:
                self.write_except(ace, "TERM LISTNER: ")
        
        if self._sharedmemserver is not None:
            try:
                self._sharedmemserver.close()
            except Exception as ace:
                self.write_except(ace, "TERM STATUSCONFIG LISTENER: ")
        
        if self._runonfly_sharedmem is not None:
            try:
                self._runonfly_sharedmem.close()
                self._runonfly_sharedmem=None
            except Exception as ace:
                self.write_except(ace, "CLOSE RUNONFLY SHAREDMEM: ")
        
        
        if is_mac() and not self._runonfly:
            try:
                self.get_osmodule().term_guilnc()
            except Exception as ge:
                self.write_except(ge, "TERM GUI LNC: ")
          
        self.write_info("Stop agent manager");
        
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
        if self._sharedmemserver is not None:
            try:
                self._sharedmemserver.close()
            except Exception as ace:
                self.write_except(ace, "TERM STATUS LISTENER: ")

    def _write_log(self, level, msg):
        self._agent_log_semaphore.acquire()
        try:
            ar = []
            ar.append(unicode(threading.current_thread().name))
            ar.append(u" ")
            if isinstance(msg, str):
                msg = unicode(msg, errors='replace')
            ar.append(msg)
            self._logger.log(level, u"".join(ar))
        finally:
            self._agent_log_semaphore.release()

    def write_info(self, msg):
        self._write_log(logging.INFO,  msg)

    def write_err(self, msg):
        self._write_log(logging.ERROR,  msg)
        
    def write_debug(self, msg):
        if self._agent_debug_mode:
            self._write_log(logging.DEBUG,  msg)
    
    def write_except(self, e,  tx = u""):
        if isinstance(tx, str):
            tx = unicode(tx, errors='replace')
        msg = tx
        msg += utils.exception_to_string(e)
        msg += u"\n" + utils.get_stacktrace_string()
        #msg += e.__class__.__name__
        #if e.args is not None and len(e.args)>0 and e.args[0] != '':
        #        msg = e.args[0]
        self._write_log(logging.ERROR,  msg)
    
    def _update_onfly_status(self,st):
        if self._runonfly:
            if self._runonfly_sharedmem is not None:
                if st!="ISRUN":
                    self._runonfly_sharedmem.set_property("status", st)
                    if st=="CONNECTED":
                        if self._runonfly_user is not None and self._runonfly_password is not None:
                            self._runonfly_sharedmem.set_property("user", self._runonfly_user)
                            self._runonfly_sharedmem.set_property("password", self._runonfly_password)
                        else:                            
                            self._runonfly_sharedmem.set_property("user", "")
                            self._runonfly_sharedmem.set_property("password", "")
                    else:
                        self._runonfly_sharedmem.set_property("user", "")
                        self._runonfly_sharedmem.set_property("password", "")
            
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
    
    def _run_agent(self):
        self.write_info("Initializing agent (key: " + self._agent_key + ", node: " + self._agent_server + ")..." );
        conn = None
        try:
            prop = {}
            prop['host'] = self._agent_server
            prop['port'] = self._agent_port
            prop['methodConnectPort']  = self._agent_method_connect_port
            prop['instance'] = self._agent_instance
            prop['userName'] = 'AG' + self._agent_key
            prop['password'] = self._agent_password
            prop['localeID'] = 'en_US'
            prop['version'] = self._agent_version
            conn = communication.Connection({"on_data": self._on_data, "on_except": self.write_except});
            conn.open(prop, self.get_proxy_info())
            self._connection=conn
            self._connections={}
            self._main_temp_msg={"length":0, "read":0, "data":utils.Bytes(), "fire":self._fire_msg}
            self._sessions={}
            self._apps={}
            self._apps_to_reload={}
            self._reload_agent_reset()
            #ready agent
            suppapps=";".join(self.get_supported_applications());
            m = {
                    'name':  'ready', 
                    'osType':  get_os_type(),
                    'osTypeCode':  str(get_os_type_code()), 
                    'fileSeparator':  utils.path_sep,
                    'supportedApplications': suppapps
                }
            hwnm = detectinfo.get_hw_name()
            if hwnm is not None:
                m["hwName"]=hwnm
            #Invia le informazioni di file version
            if not utils.path_exists(".srcmode"):
                f = utils.file_open('fileversions.json')
                cur_vers = json.loads(f.read())
                f.close()
                for vn in cur_vers:
                    if vn[0:4]!="app_":
                        m["version@" + vn]=cur_vers[vn]
            
            self._send_message(conn,m)
            self._agent_status = self._STATUS_ONLINE
            self.write_info("Initialized agent (key: " + self._agent_key + ", node: " + self._agent_server + ")." );
            if self._runonfly:
                self._update_onfly_status("CONNECTED")
                self._runonfly_conn_retry=0
                try:
                    if self._runonfly_runcode is None:
                        self._set_config("preferred_run_user",self._agent_key.split('@')[1]);
                except:
                    None
            checksuppappscnt=communication.Counter(20*1000) #20 SECONDS
            while self.is_run() and not conn.is_close() and not self._is_reboot_agent() and not self._is_reload_config():
                time.sleep(1)
                cntses=0;
                self._connections_semaphore.acquire()
                try:
                    cntses=len(self._sessions)
                    if cntses==0 and self._is_reload_agent():
                        break #RELOAD AGENT
                finally:
                    self._connections_semaphore.release()
                self._reload_apps(cntses==0)           
                #CHECK IF SUPPORTED APPS IS CHANGED
                if checksuppappscnt.is_elapsed():
                    checksuppappscnt.reset()
                    sapps=";".join(self.get_supported_applications());
                    if suppapps!=sapps:
                        suppapps=sapps
                        m = {
                            'name':  'update', 
                            'supportedApplications': suppapps
                        }
                        self._send_message(conn,m)
            if self._runonfly:
                self._runonfly_user=None
                self._runonfly_password=None
            return True
        except Exception as inst:
            self.write_except(inst)
            return False
        finally:
            self._close_all_sessions()
            if conn is not None:
                self.write_info("Terminated agent (key: " + self._agent_key + ", node: " + self._agent_server + ")." );
                self._connection=None
                self._sessions={}
                self._unload_apps()
                conn.close()
            self._reload_agent_reset()
    
    
    def get_supported_applications(self):
        return applications.get_supported(self)
    
    def _update_libs_apps_file(self, cur_vers, rem_vers, name_file):
        if name_file in cur_vers:
            cv = cur_vers[name_file]
        else:
            cv = "0"
        rv  = rem_vers[name_file + '@version']
        if cv!=rv:
            app_file = name_file
            if utils.path_exists(app_file):
                utils.path_remove(app_file)
            self.write_info("Downloading file " + name_file + "...")
            app_url = self._agent_url_node + "getAgentFile.dw?name=" + name_file + "&version=" + rem_vers[name_file + '@version']
            communication.download_url_file(app_url ,app_file, self.get_proxy_info(), None)
            self._check_hash_file(app_file, rem_vers[name_file + '@hash'])
            self._unzip_file(app_file, "")
            utils.path_remove(app_file)
            cur_vers[name_file]=rv
            self.write_info("Downloaded file " + name_file + ".")
            return True
        return False
    
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
            self.write_info("Checking update " + tp + " " + name + "...")
            rem_vers=None
            try:
                app_url = self._agent_url_node + "getAgentFile.dw?name=files.xml"
                rem_vers = communication.get_url_prop(app_url, self.get_proxy_info())
            except Exception as e:
                raise Exception("Error read files.xml: "  + utils.exception_to_string(e))
            if "error" in rem_vers:
                raise Exception("Error read files.xml: " + rem_vers['error'])
            #Verifica se esiste l'applicazione
            arfiles = rem_vers['files'].split(";")
            if tp=="app":
                zipname="app_" + name + ".zip"
            elif tp=="lib":
                zipname="lib_" + name + "_" + self._agent_native_suffix + ".zip"
            if self._update_libs_apps_file_exists(arfiles, zipname):
                #bupdatefvers=False 
                f = utils.file_open('fileversions.json')
                cur_vers = json.loads(f.read())
                f.close()
                if tp=="app" and not utils.path_exists("app_" + name):
                    utils.path_makedirs("app_" + name)
                bup = self._update_libs_apps_file(cur_vers, rem_vers, zipname)                
                if bup:                
                    s = json.dumps(cur_vers , sort_keys=True, indent=1)
                    f = utils.file_open("fileversions.json", "wb")
                    f.write(s)
                    f.close()
                    if tp=="app":
                        self.write_info("Updated app " + name + ".")
                    elif tp=="lib":
                        self.write_info("Updated lib " + name + ".")
                if tp=="app":
                    self._update_app_dependencies(name)
                elif tp=="lib":
                    self._update_lib_dependencies(name)

            else:
                if tp=="app":
                    self.write_info("App " + name + " not found.")
                elif tp=="lib":
                    self.write_info("Lib " + name + " not found (maybe it is not necessary for this OS).")
        except Exception as e:
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
                    self.write_info("Loaded lib " + name + ".")
        except Exception as e:
            self.write_except("Error loading lib " + name + ": " + utils.exception_to_string(e));
            raise e
    
    def load_lib(self, name):
        self._libs_apps_semaphore.acquire()
        try:            
            self._init_lib(name)
            cnflib=self._libs[name]
            if cnflib["refcount"]==0:
                if "lib_dependencies" in cnflib:
                    for ln in cnflib["lib_dependencies"]:
                        self.load_lib(ln)
                fn = cnflib["filename_" + native.get_suffix()]
                cnflib["refobject"]=native._load_lib_obj(fn)
            cnflib["refcount"]+=1
            return cnflib["refobject"]
        except Exception as e:
            raise e
        finally:
            self._libs_apps_semaphore.release()        
        
    def unload_lib(self, name):
        self._libs_apps_semaphore.acquire()
        try:
            cnflib=self._libs[name]
            cnflib["refcount"]-=1
            if cnflib["refcount"]==0:
                native._unload_lib_obj(cnflib["refobject"])
                if "lib_dependencies" in cnflib:
                    for ln in cnflib["lib_dependencies"]:
                        self.unload_lib(ln)
                cnflib["refobject"]=None
                del self._libs[name]
                self.write_info("Unloaded lib " + name + ".")
        except Exception as e:
            self.write_except("Error unloading lib " + name + ": " + utils.exception_to_string(e));
            raise e
        finally:
            self._libs_apps_semaphore.release()
    
    
    def _get_app_config(self,name):
        pthfc="app_" + name + utils.path_sep + "config.json"
        if utils.path_exists(".srcmode"):
            pthfc=".." + utils.path_sep + pthfc
        if utils.path_exists(pthfc):
            f = utils.file_open(pthfc)             
            conf = json.loads(f.read())
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
        except Exception as e:         
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
                self.write_info("Unloaded app " + name + ".")
            return bret
        except AttributeError:
            return True
        except Exception as e:
            self.write_except("Error unloading app " + name + ": " + utils.exception_to_string(e))
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
                self.write_info("Loaded app " + name + ".")
            except Exception as e:
                raise Exception("Error loading app " + name + ": " + utils.exception_to_string(e))
    
    def get_app(self,name):
        self._libs_apps_semaphore.acquire()
        try:
            self._init_app(name)
            return self._apps[name]
        except Exception as e:
            self.write_except(e);
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
            except Exception as e:
                self.write_except(e)
    
    def _close_all_sessions(self):
        self._connections_semaphore.acquire()
        try:
            for sid in self._sessions.keys():
                #self._fire_close_conn_apps(sid)
                self._sessions[sid].close();
                #del conn[sid]
        finally:
            self._connections_semaphore.release()
    
    
    def _fire_msg(self, msg):
        try:
            if self._connection is None:
                return
            msg_name = msg["name"]
            if msg_name=="updateInfo":
                if "agentGroup" in msg:
                    self._agent_group=msg["agentGroup"]
                if "agentName" in msg:
                    self._agent_name=msg["agentName"]
            elif msg_name=="reboot":
                self._reboot_agent()
            elif msg_name=="reload":
                #WAIT RANDOM TIME BEFORE TO REBOOT AGENT
                wtime=random.randrange(0, 6*3600)*1000 # 6 ORE
                self._reload_agent(wtime)
            elif msg_name=="reloadApps":
                self._libs_apps_semaphore.acquire()
                try:
                    arAppsUpdated = msg["appsUpdated"].split(";")
                    for appmn in arAppsUpdated:
                        self._apps_to_reload[appmn]=True
                finally:
                    self._libs_apps_semaphore.release()
            elif msg_name=="reloadLibs":
                self._libs_apps_semaphore.acquire()
                try:
                    arLibsUpdated = msg["libsUpdated"].split(";")
                    for libmn in arLibsUpdated:
                        self._set_reload_apps_with_lib_deps(libmn)
                finally:
                    self._libs_apps_semaphore.release()
            elif msg_name=="openConnection":
                self.open_connection(msg)
            elif msg_name=="openSession":
                self.open_session(msg)
        except Exception as e:
            self.write_except(e)
            if 'requestKey' in msg:
                m = {
                    'name': 'error' , 
                    'requestKey':  msg['requestKey'] , 
                    'class':  e.__class__.__name__ , 
                    'message':  utils.exception_to_string(e)
                }
                if self._connection is not None:
                    self._send_message(self._connection,m)

    def _on_data(self, data):
        self.on_data_message(self._main_temp_msg,data)
    
    def _on_message(self,firemsg,dt):
        dt.decompress_zlib()
        firemsg(json.loads(dt.to_str("utf8")))  
    
    def _send_message(self, conn, msg):
        appm=utils.Bytes()
        appm.append_str(json.dumps(msg), "utf8")
        appm.compress_zlib()
        appm.insert_int(0, len(appm))
        conn.send(appm)        
    
    def on_data_message(self, tm, data):
        p=0
        while p<len(data):
            if tm["length"]==0:
                tm["length"] = struct.unpack("!I",data[p:p+4])[0]
                p+=4
            c=tm["length"]-tm["read"]
            rms=len(data)-p
            if rms<c:
                c=rms
            tm["data"].append_bytes(data.new_buffer(p,c))
            tm["read"]+=c
            p=p+c
            if tm["read"]==tm["length"]:
                self._task_pool.execute(self._on_message, tm["fire"],tm["data"])
                tm["length"]=0
                tm["read"]=0
                tm["data"]=utils.Bytes()
        
    
    def open_connection(self, msg):
        self._connections_semaphore.acquire()
        try:
            cn = Connection(self,msg["id"],msg["userName"],msg["password"])
            self._connections[cn.get_id()]=cn
        finally:
            self._connections_semaphore.release()
        m = {
                'name': 'response', 
                'requestKey':  msg["requestKey"], 
            }
        self._send_message(self._connection, m)
            
    def close_connection(self, cn):
        self._connections_semaphore.acquire()
        try:
            if cn.get_id() in self._connections:
                del self._connections[cn.get_id()]
        finally:
            self._connections_semaphore.release()
    
    def open_session(self, msg):
        sid=msg["idSession"]
        rid=msg["idRaw"]
        self._connections_semaphore.acquire()
        try:
            if not rid in self._connections:
                raise Exception("Connection not found (id: " + rid + ")")
            sinfo=Session(self,self._connections[rid],sid,json.loads(msg["permissions"]))
            self._sessions[sid]=sinfo                
        finally:
            self._connections_semaphore.release()
        m = {
                'name': 'response', 
                'requestKey':  msg["requestKey"], 
            }
        self._send_message(self._connection, m)
        self.write_info("openSession (id=" + sid + ")");


    def close_session(self, ses):
        self._connections_semaphore.acquire()
        try:
            sid = ses.get_idsession()
            self._fire_close_conn_apps(sid)
            del self._sessions[sid]
        finally:
            self._connections_semaphore.release()
        self.write_info("closeSession (id=" + sid + ")");
    
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
    def __init__(self, agent, sid, user, password):
        self._evt_on_data=None
        self._evt_on_close=None
        self._evt_on_except=None
        self._agent=agent
        self._id=sid
        prop = {}
        prop['host'] = self._agent._agent_server
        prop['port'] = self._agent._agent_port
        prop['methodConnectPort']  = self._agent._agent_method_connect_port
        prop['instance'] = self._agent._agent_instance
        prop['userName'] = user
        prop['password'] = password
        prop['localeID'] = 'en_US'
        prop['version'] = self._agent._agent_version
        self._conn = communication.Connection({"on_data": self._on_data, "on_except": self._on_except, "on_close":self._on_close});
        self._conn.open(prop, self._agent.get_proxy_info())
    
    def get_id(self):
        return self._id
    
    def send(self,data):
        self._conn.send(data)
    
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
        if "on_except" in evts:
            self._evt_on_except=evts["on_except"]
        else:
            self._evt_on_except=None
            
    def _on_data(self, dt):
        if self._evt_on_data is not None:
            self._evt_on_data(dt)
        
    def _on_close(self):
        self._agent.close_connection(self)
        if self._evt_on_close is not None:
            self._evt_on_close()
            
    def _on_except(self,e):
        if self._evt_on_except is not None:
            self._evt_on_except(e)
        else:
            self._agent.write_except(e)
    
    def close(self):
        self._agent.close_connection(self)
        self._conn.close()

class Session():
    
    def __init__(self, agent, conn, idses, perms):
        self._agent=agent
        self._bclose = False
        self._temp_msg={"length":0, "read":0, "data":utils.Bytes(), "fire":self._fire_msg}
        self._conn=conn
        self._conn.set_events({"on_close" : self._on_close, "on_data" : self._on_data})
        self._idsession= idses
        self._permissions = perms
        self._semaphore = threading.Condition()
        self._semaphore_req = threading.Condition()
        self._pending_req={}
        self._bwsendcalc=communication.BandwidthCalculator()
        self._lastacttm=time.time()

    def get_idsession(self):
        return self._idsession
    
    def get_permissions(self):
        return self._permissions
    
    def is_close(self):
        ret = True
        self._semaphore.acquire()
        try:
            ret=self._bclose
        finally:
            self._semaphore.release()
        return ret
    
    def get_last_activity_time(self):
        return self._lastacttm
    
    def _set_last_activity_time(self):
        self._lastacttm=time.time()
    
    def _on_data(self,data):
        self._set_last_activity_time()
        self._agent.on_data_message(self._temp_msg,data)
    
    def _fire_msg(self,msg):
        try:
            msg_name = msg["name"]
            if msg_name=="request":
                self._request(msg)
            elif msg_name=="download":
                self._download(msg)
            elif msg_name=="upload":
                self._upload(msg)
            elif msg_name=="websocket":
                self._websocket(msg)
            elif msg_name=="websocketsimulate":
                self._websocketsimulate(msg)
            else:
                raise Exception("Invalid message name: " + msg_name)
        except Exception as e:
            self._agent.write_except(e)
            if 'requestKey' in msg:
                m = {
                    'name': 'error' , 
                    'requestKey':  msg['requestKey'] , 
                    'class':  e.__class__.__name__ , 
                    'message':  utils.exception_to_string(e)
                }
                self._send_message(m)
    
    def _send_conn(self,conn,data):
        pos=0
        tosnd=len(data)
        while tosnd>0:
            bps = self._bwsendcalc.get_bps()
            bfsz = communication.calculate_buffer_size(bps)
            if bfsz is None:
                bfsz=self._connection.get_send_buffer_size()
            if bfsz>=tosnd:
                conn.send(data.new_buffer(pos,tosnd))
                self._bwsendcalc.add(tosnd)
                tosnd=0                
            else:
                conn.send(data.new_buffer(pos,bfsz))
                self._bwsendcalc.add(bfsz)
                tosnd-=bfsz
                pos+=bfsz

    
    def _send_message(self,msg):
        appm=utils.Bytes()
        appm.append_str(json.dumps(msg), "utf8")
        appm.compress_zlib()
        appm.insert_int(0, len(appm))
        self._send_conn(self._conn, appm)
           
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
        self._send_message(m);    
        
    def _request(self, msg):
        resp = ""
        try:
            app_name = msg["module"]
            cmd_name = msg["command"]
            params = {}
            params["requestKey"]=msg['requestKey']
            sck = "parameter_";
            for key in msg.iterkeys():
                if key.startswith(sck):
                    params[key[len(sck):]]=msg[key]
            resp=self._agent.invoke_app(app_name, cmd_name, self, params)
            if resp is not None:
                resp = ":".join(["K", resp])
            else:
                resp = "K:null"
        except Exception as e:
            m = utils.exception_to_string(e)
            self._agent.write_debug(m)
            resp=  ":".join(["E", m])
        self.send_response(msg, resp)
    
    def _websocket(self, msg):
        rid=msg["idRaw"]
        wsock=None
        self._agent._connections_semaphore.acquire()
        try:
            if not rid in self._agent._connections:
                raise Exception("Connection not found (id: " + rid + ")")
            wsock = WebSocket(self,self._agent._connections[rid], msg)  
        finally:
            self._agent._connections_semaphore.release()        
        try:
            self._agent.invoke_app(msg['module'],  "websocket",  self,  wsock)
            resp = {}
            if not wsock.is_accept():
                raise Exception("WebSocket not accepted")
        except Exception as e:
            try:
                wsock.close()
            except:
                None
            resp = {}
            resp["error"]=utils.exception_to_string(e)
        resp['name']='response'
        resp['requestKey']=msg['requestKey']
        self._send_message(resp)
    
    def _websocketsimulate(self, msg):
        rid=msg["idRaw"]
        wsock=None
        self._agent._connections_semaphore.acquire()
        try:
            if not rid in self._agent._connections:
                raise Exception("Connection not found (id: " + rid + ")")
            wsock = WebSocketSimulate(self,self._agent._connections[rid], msg)  
        finally:
            self._agent._connections_semaphore.release()
        try:
            self._agent.invoke_app(msg['module'],  "websocket",  self,  wsock)
            resp = {}
            if not wsock.is_accept():
                raise Exception("WebSocket not accepted")
        except Exception as e:
            try:
                wsock.close()
            except:
                None
            resp = {}
            resp["error"]=utils.exception_to_string(e)
        resp['name']='response'
        resp['requestKey']=msg['requestKey']
        self._send_message(resp)    
    
    def _download(self, msg):
        rid=msg["idRaw"]
        fdownload = None
        self._agent._connections_semaphore.acquire()
        try:
            if not rid in self._agent._connections:
                raise Exception("Connection not found (id: " + rid + ")")
            fdownload = Download(self, self._agent._connections[rid], msg)
        finally:
            self._agent._connections_semaphore.release()   
        try:
            self._agent.invoke_app(msg['module'],  "download",  self,  fdownload)
            resp = {}
            if fdownload.is_accept():
                mt = mimetypes.guess_type(fdownload.get_path())
                if mt is None or mt[0] is None or not isinstance(mt[0], str):
                    resp["Content-Type"] = "application/octet-stream"
                else:
                    resp["Content-Type"] = mt[0]
                resp["Content-Disposition"] = "attachment; filename=\"" + fdownload.get_name() + "\"; filename*=UTF-8''" + urllib.quote(fdownload.get_name().encode("utf-8"), safe='')
                #ret["Cache-Control"] = "no-cache, must-revalidate" NON FUNZIONA PER IE7
                #ret["Pragma"] = "no-cache"
                resp["Expires"] = "Sat, 26 Jul 1997 05:00:00 GMT"
                resp["Length"] = str(fdownload.get_length())
            else:
                raise Exception("Download file not accepted")
        except Exception as e:
            try:
                fdownload.close()
            except:
                None
            resp = {}
            resp["error"]=utils.exception_to_string(e)
        resp['name']='response'
        resp['requestKey']=msg['requestKey']
        self._send_message(resp)
    
    def _upload(self, msg):
        rid=msg["idRaw"]
        fupload = None
        self._agent._connections_semaphore.acquire()
        try:
            if not rid in self._agent._connections:
                raise Exception("Connection not found (id: " + rid + ")")
            fupload = Upload(self, self._agent._connections[rid], msg)
        finally:
            self._agent._connections_semaphore.release()
        try:
            self._agent.invoke_app(msg['module'],  "upload",  self,  fupload)
            resp = {}
            if not fupload.is_accept():
                raise Exception("Upload file not accepted")
        except Exception as e:
            try:
                fupload.close()
            except:
                None
            resp = {}
            resp["error"]=utils.exception_to_string(e)
        resp['name']='response'
        resp['requestKey']=msg['requestKey']
        self._send_message(resp)
    
    def _on_close(self):
        if not self._bclose:
            self._semaphore.acquire()
            try:
                self._bclose=True
            finally:
                self._semaphore.release()
            self._agent._task_pool.execute(self._agent.close_session,self)
    
    def close(self):
        if not self._bclose:
            self._semaphore.acquire()
            try:
                self._bclose=True
            finally:
                self._semaphore.release()
            self._agent.close_session(self)
            self._conn.close()
            

class WebSocket:
    DATA_STRING = ord('s')
    DATA_BYTES= ord('b');
    
    def __init__(self, parent, conn, props):
        self._parent=parent
        self._agent=self._parent._agent 
        self._conn=conn
        self._conn.set_events({"on_close" : self._on_close_conn, "on_data" : self._on_data_conn})
        self._props=props
        self._baccept=False
        self._bclose=False
        self._on_close=None
        self._on_data=None
        
            
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
                self._data=data
            else:
                self._data.append_bytes(data)
            try:
                while True:
                    if self._len==-1:
                        if len(self._data)>=4:
                            self._len = struct.unpack('!i', self._data[0:4])[0]
                        else:
                            break
                    if self._len>=0 and len(self._data)-4>=self._len:
                        apptp = self._data[5]
                        appdata = self._data.new_buffer(5,self._len)
                        self._data = self._data.new_buffer(4+self._len)
                        self._len=-1;
                        if self._on_data is not None:
                            self._on_data(self,apptp,appdata);
                    else:
                        break
            except:
                self.close();
                if self._on_close is not None:
                    self._on_close()
    
    
    def send_string(self,data):
        self._send(WebSocket.DATA_STRING,data)
    
    def send_bytes(self,data):
        self._send(WebSocket.DATA_BYTES,data)
        
    def _send(self,tpdata,data):
        self._parent._set_last_activity_time()
        if not self._bclose:
            dtsend=utils.Bytes()
            if type(data).__name__ == 'list':
                for i in range(len(data)):
                    dt=data[i]
                    dtsend.append_int(len(dtsend)+1)
                    dtsend.append_byte(tpdata)
                    if tpdata==WebSocket.DATA_STRING:
                        dtsend.append_bytes(utils.Bytes(dt))
                    else:
                        dtsend.append_bytes(dt)
                    
            else:
                dtsend.append_int(len(data)+1)
                dtsend.append_byte(tpdata)
                if tpdata==WebSocket.DATA_STRING:
                    dtsend.append_bytes(utils.Bytes(data))
                else:
                    dtsend.append_bytes(data)
            self._parent._send_conn(self._conn,dtsend)
       
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
    MAX_SEND_SIZE = 32*1024
    
    def __init__(self, parent, conn, props):
        self._parent=parent
        self._agent=self._parent._agent 
        self._conn=conn
        self._conn.set_events({"on_close" : self._on_close_conn, "on_data" : self._on_data_conn})
        self._props=props
        self._baccept=False
        self._bclose=False
        self._on_close=None
        self._on_data=None
        self._semaphore = threading.Condition()
        
    
    def accept(self, priority, events):
        if events is not None:
            if "on_close" in events:
                self._on_close = events["on_close"]
            if "on_data" in events:
                self._on_data = events["on_data"]
        self._qry_len=-1
        self._qry_data=utils.Bytes()
        self._pst_len=-1
        self._pst_data=utils.Bytes()
        self._qry_or_pst="qry"
        self._send_list=[]
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
                    self._qry_data.append_bytes(data)
                else:
                    self._pst_data.append_bytes(data)
                if self._qry_or_pst=="qry":
                    if self._qry_len==-1:
                        if len(self._qry_data)>=4:
                            self._qry_len = struct.unpack('!i', self._qry_data[0:4])[0]
                            self._qry_data = self._qry_data.new_buffer(4)
                    if self._qry_len!=-1 and len(self._qry_data)>=self._qry_len:
                        self._pst_data=self._qry_data.new_buffer(self._qry_len)
                        self._qry_data=self._qry_data.new_buffer(0,self._qry_len)
                        self._qry_or_pst="pst"
                if self._qry_or_pst=="pst":
                    if self._pst_len==-1:
                        if len(self._pst_data)>=4:
                            self._pst_len = struct.unpack('!i', self._pst_data[0:4])[0]
                            self._pst_data = self._pst_data.new_buffer(4)      
                    if self._pst_len!=-1 and len(self._pst_data)>=self._pst_len:
                        prpqry=None
                        if self._qry_len>0:
                            prpqry=communication.xml_to_prop(self._qry_data.to_str("utf8"))
                        self._qry_data=self._pst_data.new_buffer(self._pst_len)
                        self._pst_data=self._pst_data.new_buffer(0,self._pst_len)
                        prppst=None
                        if self._pst_len>0:
                            prppst=communication.xml_to_prop(self._pst_data.to_str("utf8"))
                        self._qry_or_pst="qry"
                        self._qry_len=-1
                        self._pst_len=-1
                        self._pst_data=""
                        
                        if self._on_data is not None:
                            cnt = int(prppst["count"])
                            for i in range(cnt):
                                tpdata = prppst["type_" + str(i)]
                                prprequest = utils.Bytes(prppst["data_" + str(i)])
                                if tpdata==WebSocketSimulate.DATA_BYTES:
                                    prprequest.decode_base64()
                                self._on_data(self, tpdata, utils.Bytes(prprequest))
                        #Invia risposte
                        self._semaphore.acquire()
                        try:
                            if len(self._send_list)==0 and "destroy" not in prppst:
                                appwt=250
                                if "wait" in prppst:
                                    appwt=int(prppst["wait"])
                                if appwt==0:
                                    self._semaphore.wait()
                                else:
                                    appwt=appwt/1000.0
                                    self._semaphore.wait(appwt)
                            if not self._bclose:
                                if len(self._send_list)>0:
                                    arsend = {}
                                    arcnt = 0
                                    lensend = 0
                                    app_send_list=[]
                                    for i in range(len(self._send_list)):
                                        if (len(app_send_list)>0) or (i>0 and (lensend + len(self._send_list[i]["data"])) > WebSocketSimulate.MAX_SEND_SIZE):
                                            app_send_list.append(self._send_list[i])
                                        else:
                                            arsend["type_" + str(i)]=self._send_list[i]["type"]
                                            arsend["data_" + str(i)]=self._send_list[i]["data"]
                                            lensend += len(self._send_list[i])
                                            arcnt+=1
                                    arsend["count"]=arcnt
                                    arsend["otherdata"]=len(app_send_list)>0
                                    self._send_response(json.dumps(arsend))
                                    self._send_list=app_send_list
                                else:
                                    self._send_response("")
                        finally:
                            self._semaphore.release()
                        if "destroy" in prppst:
                            self.close();
                            if self._on_close is not None:
                                self._on_close()
            except Exception as e:
                self.close();
                if self._on_close is not None:
                    self._on_close()
                    
    
    def _send_response(self,sdata):
        prop = {}
        prop["Cache-Control"] = "no-cache, must-revalidate"
        prop["Pragma"] = "no-cache"
        prop["Expires"] = "Sat, 26 Jul 1997 05:00:00 GMT"
        prop["Content-Encoding"] = "gzip"
        prop["Content-Type"] = "application/json; charset=utf-8"
        #prop["Content-Type"] = "application/octet-stream"
        
        
        bts = utils.Bytes()
        #AGGIUNGE HEADER
        shead = communication.prop_to_xml(prop)
        bts.append_int(len(shead))
        bts.append_str(shead,"ascii")
        
        #COMPRESS RESPONSE
        appout = StringIO.StringIO()
        f = gzip.GzipFile(fileobj=appout, mode='w', compresslevel=5)
        f.write(sdata)
        f.close()
        dt = appout.getvalue()
        
        #BODY LEN
        ln=len(dt)
        
        #BODY
        bts.append_int(ln)
        if ln>0:
            bts.append_bytes(utils.Bytes(dt))
        
        self._parent._send_conn(self._conn,bts)
        
    
    def send_string(self,data):
        self._send(WebSocketSimulate.DATA_STRING,data)
    
    def send_bytes(self,data):
        self._send(WebSocketSimulate.DATA_BYTES,data)
    
    def _send(self,tpdata,data): 
        self._parent._set_last_activity_time()
        if not self._bclose:
            self._semaphore.acquire()
            try:
                if type(data).__name__ == 'list':
                    for i in range(len(data)):
                        dt=data[i];
                        if tpdata==WebSocketSimulate.DATA_BYTES:
                            dt.encode_base64()
                        #print("LEN: " + str(len(data[i])) + " LEN B64: " + str(len(dt)))
                        self._send_list.append({"type": tpdata, "data": dt.to_str("utf8")})
                else:
                    dt=data;
                    if tpdata==WebSocketSimulate.DATA_BYTES:
                        dt.encode_base64()
                    #print("LEN: " + str(len(data)) + " LEN B64: " + str(len(dt)))
                    self._send_list.append({"type": tpdata, "data": dt.to_str("utf8")})
                self._semaphore.notifyAll()
            finally:
                self._semaphore.release()
    
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
            self._semaphore.acquire()
            try:
                self._send_list=[]
                self._semaphore.notifyAll()
            finally:
                self._semaphore.release()
            if self._conn is not None:
                self._conn.close()
                self._conn = None
                

class Download():

    def __init__(self, parent, conn, props):
        self._parent=parent
        self._agent=self._parent._agent
        self._conn=conn
        self._conn.set_events({"on_close" : self._on_close_conn, "on_data" : self._on_data_conn})
        self._props=props
        self._semaphore = threading.Condition()
        self._baccept=False

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
        fl=None
        try:
            fl = utils.file_open(self._path, 'rb')
            bsz=32*1024
            while not self.is_close():
                bts = utils.file_read(fl,bsz)
                ln = len(bts)
                if ln==0:
                    self._status="C"
                    break
                self._parent._set_last_activity_time()
                self._parent._send_conn(self._conn,bts)
                self._calcbps.add(ln)
                #print "DOWNLOAD - NAME:" + self._name + " SZ: " + str(len(s)) + " LEN: " + str(self._calcbps.get_transfered()) +  "  BPS: " + str(self._calcbps.get_bps())
        except Exception:
            self._status="E"
        finally:
            self.close()
            if fl is not None:
                fl.close()
        if self._conn is not None:
            self._conn.close()
            self._conn = None
    
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
        self._conn=conn
        self._conn.set_events({"on_close" : self._on_close_conn, "on_data" : self._on_data_conn})
        self._props=props
        self._semaphore = threading.Condition()
        self._baccept=False

    def accept(self, path):
        self._path=path
        self._name=utils.path_basename(self._path)
        if 'length' not in self._props:
            raise Exception("upload file length in none.")
        self._length=long(self._props['length'])
        self._calcbps=communication.BandwidthCalculator() 
            
        sprnpath=utils.path_dirname(path);    
        while True:
            r="".join([random.choice("0123456789") for x in xrange(6)])            
            self._tmpname=sprnpath + utils.path_sep + "temporary" + r + ".dwsupload";
            if not utils.path_exists(self._tmpname):
                utils.file_open(self._tmpname, 'wb').close() #Crea il file per imposta i permessi
                self._agent.get_osmodule().fix_file_permissions("CREATE_FILE",self._tmpname)
                self._fltmp = utils.file_open(self._tmpname, 'wb')
                break
        try:
            self._bclose = False
            self._status="T"
            self._enddatafile=False
            self._baccept=True
            self._last_time_transfered = 0
        except Exception as e:
            self._remove_temp_file()
            raise e
        
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
                    if data[0]==ord('C'): 
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
                            bts = utils.Bytes()
                            bts.append_str(self._status, "utf8")
                            self._parent._send_conn(self._conn,bts)
                        except Exception:
                            self._status = "E"
                            bts = utils.Bytes()
                            bts.append_str(self._status, "utf8")
                            self._parent._send_conn(self._conn,bts)
                        self.close()
                    else: #if data[0]=='D': 
                        data=data.new_buffer(1)
                        utils.file_write(self._fltmp, data)
                        self._calcbps.add(len(data))
                        #print "UPLOAD - NAME:" + self._name + " LEN: " + str(self._calcbps.get_transfered()) +  "  BPS: " + str(self._calcbps.get_bps())
                        
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
        if not self._bclose:
            self._semaphore.acquire()
            try:
                #print "UPLOAD - ONCLOSE"
                self._bclose=True
                self._remove_temp_file()
                if not self._enddatafile:
                    self._status = "E"
            finally:
                self._semaphore.release()
            if self._conn is not None:
                self._conn.close()
                self._conn = None
    
    def close(self):
        if not self._bclose:
            #print "UPLOAD - CLOSE"
            self._semaphore.acquire()
            try:
                self._bclose=True
                self._remove_temp_file()
                self._status  = "C"
            finally:
                self._semaphore.release()
            if self._conn is not None:
                self._conn.close()
                self._conn = None


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
    main.unload_library()
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
            sys.argv.remove(a1);
            
            objlib = importlib.import_module("app_" + name)
            func = getattr(objlib, 'run_main', None)
            func(sys.argv)
        elif a1 is not None and a1.lower()=="guilnc":
            if is_mac():
                bmain=False
                native.fmain(sys.argv)
    if bmain:
        fmain(sys.argv)
    
    
    
    