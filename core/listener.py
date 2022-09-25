# -*- coding: utf-8 -*-

'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import threading
import time
import ipc
import json
import os
import hashlib
import base64
import utils


##############################
######### IPCSERVER ##########
##############################
class IPCServer(threading.Thread):
    def __init__(self,agent):
        threading.Thread.__init__(self, name="ListenerIPCServer")
        self._agent=agent
        self._prop = None
        self._status = None
        self._config = None
    
    def start(self):
        self._prop = ipc.Property()
        fieldsdef=[]
        fieldsdef.append({"name":"counter","size":30})
        fieldsdef.append({"name":"state","size":5})
        fieldsdef.append({"name":"connections","size":20}) #TO REMOVE 2021-02-11
        fieldsdef.append({"name":"group","size":100*5})
        fieldsdef.append({"name":"name","size":100*5})        
        fieldsdef.append({"name":"request_pid","size":20})
        fieldsdef.append({"name":"request_data","size":1024*16})
        fieldsdef.append({"name":"response_data","size":1024*16})        
        fieldsdef.append({"name":"sessions_status","size":1024*512})
        def fix_perm(fn):
            self._agent.get_osmodule().set_file_permission_everyone(fn)            
        self._prop.create("status_config", fieldsdef, fix_perm)
        self._prop.set_property("response_data","")
        self._prop.set_property("request_data","")
        self._prop.set_property("request_pid","")
        
        self._status=IPCStatus(self._agent,self._prop)
        self._status.start();
        self._config=IPCConfig(self._agent,self._prop)
        self._config.start();
    
    def close(self):
        if self._config!=None:
            self._config.close();
            self._config.join(5000)
        if self._status!=None:
            self._status.close();
            self._status.join(5000)
        self._prop.close()

class IPCStatus(threading.Thread):
    def __init__(self,agent,prop):
        threading.Thread.__init__(self, name="ListenerIPCStatus")
        self.daemon=True
        self._agent=agent
        self._prop=prop
        self._bclose=False
        self._cnt=0

    def run(self):
        logwait=60*10
        while not self._bclose:
            if self._cnt==utils.sys_maxsize:
                self._cnt=0
            else:
                self._cnt+=1
            try:
                self._prop.set_property("counter", str(self._cnt))
                self._prop.set_property("state", str(self._agent.get_status()))
                
                self._prop.set_property("group", "") #TO REMOVE 2022-09-13
                
                sapp = self._agent.get_name()
                if sapp is None:
                    sapp=""
                if utils.is_py2():
                    sapp=sapp.encode("unicode-escape");
                self._prop.set_property("name", sapp)
                
                jo = self._agent.get_active_sessions_status()                
                self._prop.set_property("connections", str(len(jo))) #TO REMOVE 2021-02-11                
                self._prop.set_property("sessions_status", json.dumps(jo))
            except:
                e=utils.get_exception()
                if logwait>=60*10:
                    logwait=0
                    self._agent.write_except(e)                    
                logwait+=1
            time.sleep(1)
                
        self._bclose=True        
    
    def close(self):
        self._bclose=True
        

class IPCConfig(threading.Thread):
    
    def __init__(self,agent,prop):
        threading.Thread.__init__(self, name="ListenerIPCConfig")
        self.daemon=True
        self._agent=agent
        self._prop=prop
        self._bclose=False
        self._cnt=0
        
    
    def run(self):

        while not self._bclose:
            #VARIFICA NUOVE RICHIESTE DI CONFIGURAZIONE
            request_pid = self._prop.get_property("request_pid");
            if request_pid!="":
                try:
                    request_data = None
                    #Wait 2 seconds for request
                    for i in range(20):
                        request_data = self._prop.get_property("request_data");
                        if request_data!="":
                            break
                        time.sleep(0.1)
                    if request_data is not None:
                        self._prop.set_property("response_data",self._invoke_request(request_data))
                        #Wait 2 seconds for read response
                        for i in range(20):
                            if self._prop.get_property("request_data")=="":
                                break
                            time.sleep(0.1)
                except:
                    e=utils.get_exception()
                    self._agent.write_except(e);
                self._prop.set_property("response_data","")
                self._prop.set_property("request_data","")
                self._prop.set_property("request_pid","")
            time.sleep(0.1)
        self._bclose=True
    
    def _invoke_request(self, request_data):
        if request_data!=None:
            try:
                prms=json.loads(request_data)
                req = prms["_request"]
                func = getattr(self,  '_req_' + req)
                try:
                    return func(prms)
                except:
                    e=utils.get_exception()
                    return "ERROR:" + utils.exception_to_string(e)
            except:
                return "ERROR:INVALID_REQUEST"
        else:
            return "ERROR:INVALID_REQUEST"
    
    def _req_check_auth(self, prms):
        if "_user" in prms and "_password" in prms :
            usr=prms["_user"]
            pwd=prms["_password"]
            if self._agent.check_config_auth(usr, pwd):
                return "OK"
        return "ERROR:FORBIDDEN"
    
    #COMPATIBILITY OLD AGENT UI VERSION 25-05-2022
    def _req_change_pwd(self, prms):
        return self._req_change_config_pwd(prms)

    def _req_change_config_pwd(self, prms):
        if 'nopassword' in prms:
            nopwd = prms['nopassword']
            if nopwd=='true':
                self._agent.set_config_password("")
                return "OK"
            else:
                return "ERROR:INVALID_AUTHENTICATION"
        elif 'password' in prms:
            pwd = prms['password']
            self._agent.set_config_password(pwd)
            return "OK"
        else:
            return "ERROR:INVALID_AUTHENTICATION"
    
    def _req_change_session_pwd(self, prms):
        if 'nopassword' in prms:
            nopwd = prms['nopassword']
            if nopwd=='true':
                self._agent.set_session_password("")
                return "OK"
            else:
                return "ERROR:INVALID_AUTHENTICATION"
        elif 'password' in prms:
            pwd = prms['password']
            self._agent.set_session_password(pwd)
            return "OK"
        else:
            return "ERROR:INVALID_AUTHENTICATION"
    
    def _req_set_config(self, prms):
        if "key" in prms and "value" in prms:
            key=prms["key"]
            value=prms["value"]
            self._agent.set_config_str(key, value)
            return "OK"
        return "ERROR:INVALID_PARAMETERS."
    
    def _req_get_config(self, prms):
        if "key" in prms:
            key=prms["key"]
            return "OK:" + self._agent.get_config_str(key)
        return "ERROR:INVALID_PARAMETERS."
    
    def _req_remove_key(self, prms):
        self._agent.remove_key()
        return "OK"
    
    def _req_install_key(self, prms):
        if "code" in prms:
            code=prms["code"]
            self._agent.install_key(code)
            return "OK"
        return "ERROR:INVALID_PARAMETERS."
    
    def _req_install_new_agent(self, prms):
        #user, password, name, id
        if "user" in prms and "password" in prms and "name" in prms:
            user=prms["user"]
            password=prms["password"]
            name=prms["name"]
            self._agent.install_new_agent(user,password,name)
            return "OK"
        return "ERROR:INVALID_PARAMETERS."
    
    def _req_set_proxy(self, prms):
        ptype = None
        host = None
        port = None
        user = None
        password = None
        if 'type' in prms:
            ptype = prms['type']
        if 'host' in prms:
            host = prms['host']
        if 'port' in prms and prms['port'] is not None and prms['port'].strip()!="":
            port = int(prms['port'])
        if 'user' in prms:
            user = prms['user']
        if 'password' in prms:
            password = prms['password']
        self._agent.set_proxy(ptype,  host,  port,  user,  password)
        return "OK"

    def _req_accept_session(self, prms):
        if "id" in prms:
            sid=prms["id"]
            self._agent.accept_session(sid)
            return "OK"
        return "ERROR:INVALID_PARAMETERS."
    
    def _req_reject_session(self, prms):
        if "id" in prms:
            sid=prms["id"]
            self._agent.reject_session(sid)
            return "OK"
        return "ERROR:INVALID_PARAMETERS."
    
    def close(self):
        self._bclose=True

class IPCClient():
    
    def __init__(self,path=None):
        self._prop=ipc.Property()
        self._prop.open("status_config",bpath=path)
    
    def close(self):
        self._prop.close()
        self._prop=None
    
    def is_close(self):
        return self._prop is None or self._prop.is_close()

    def get_property(self,name):
        return self._prop.get_property(name)

    def send_request(self, usr, pwd, req, prms=None):
        sret=""
        try:
            spid=str(os.getpid())
            bok=False
            #Attende 40 secondi
            cnt=self._prop.get_property("counter")
            testcnt=0
            for i in range(400):
                bok=True
                if self._prop.get_property("request_pid")=="": #PRONTO AD ACCETTARE RICHIESTE
                    self._prop.set_property("request_pid",spid)
                    if prms is None:
                        prms={}
                    prms["_request"]=req
                    prms["_user"]=usr
                    #Hash password
                    encpwd=hashlib.sha256(utils.str_to_bytes(pwd,"utf8")).digest()
                    encpwd=base64.b64encode(encpwd)
                    prms["_password"]=utils.bytes_to_str(encpwd)
                    
                    self._prop.set_property("request_data",json.dumps(prms))
                    self._prop.set_property("response_data","")
                    break
                time.sleep(0.1)
                testcnt+=1
                if testcnt==20:
                    testcnt=0
                    appcnt=self._prop.get_property("counter")
                    if cnt==appcnt:
                        break
            if bok:
                #Attende 40 secondi
                cnt=self._prop.get_property("counter")
                testcnt=0
                for i in range(400):
                    sret=self._prop.get_property("response_data")
                    #Gestione concorrenza
                    if self._prop.get_property("request_pid")!=spid:
                        sret=""
                        break
                    if sret!="":
                        break
                    time.sleep(0.1)
                    testcnt+=1
                    if testcnt==20:
                        testcnt=0
                        appcnt=self._prop.get_property("counter")
                        if cnt==appcnt:
                            break
                if self._prop.get_property("request_pid")==spid:
                    self._prop.set_property("response_data","")
                    self._prop.set_property("request_data","")
                if sret=="":
                    sret = 'ERROR:REQUEST_TIMEOUT'
            else:
                sret = 'ERROR:REQUEST_TIMEOUT'
        except: 
            sret = 'ERROR:REQUEST_TIMEOUT'
        return sret



###############################
######### HTTPSERVER ##########
###############################
#CREATO PER USI FUTURI
class HttpServer(threading.Thread):
    
    def __init__(self, port,  agent):
        threading.Thread.__init__(self, name="HttpServer")
        self.daemon=True
        self._agent = agent
        self._port = port
        self._close=False
        self._httpd = None
    
    def run(self):        
        self._httpd = HttpConfigServer(self._port,  self._agent)
        self._close=False
        while not self._close:
            self._httpd.handle_request()

    def close(self):
        if  not self._close:
            self._close=True
            try:
                self._httpd.server_close()
            except:
                None
            self._httpd = None

'''
La versione attiva lascia la porta aperta in linux e mac
quella commentata da testare non vorrei che self._httpd.shutdown() blocca il thread principale
class HttpServer(threading.Thread):
    
    def __init__(self, port,  agent):
        threading.Thread.__init__(self, name="AgentListener")
        self.daemon=True
        self._agent = agent
        self._port = port
        self._close=False
        self._httpd = None
    
    def run(self):        
        self._httpd = HttpConfigServer(self._port,  self._agent)
        self._close=False
        self._httpd.serve_forever()
        self._httpd = None

    def close(self):
        if  not self._close:
            self._close=True
            self._httpd.shutdown() 
'''
class HttpConfigServer(utils.HTTPServer):
    
    def __init__(self, port, agent):
        server_address = ('127.0.0.1', port)
        utils.HTTPServer.__init__(self, server_address, HttpConfigHandler)
        self._agent = agent
    
    def get_agent(self):
        return self._agent


class HttpConfigHandler(utils.BaseHTTPRequestHandler):

    def do_GET(self):
        #Legge richiesta
        o = utils.url_parse(self.path)
        nm = o.path
        qs = utils.url_parse_qs(o.query)
        #Invia risposta
        resp={}
        resp['code']=404
        if 'code' in resp:
            self.send_response(resp['code'])
        else:
            self.send_response(200)
        if 'headers' in resp:
            hds = resp['headers']
            for k in hds.keys():
                self.send_header(k, hds[k])
            self.end_headers()
        if 'data' in resp:
            self.wfile.write(resp['data'])
        
    def do_HEAD(self):
        self.send_response(404)

    def do_POST(self):
        self.send_response(404)
    
    def log_message(self, format, *args):
        return



if __name__ == "__main__":
    ac = HttpServer(9000, None)
    ac.start()
    ac.join()
    
    
    
    
