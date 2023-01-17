# -*- coding: utf-8 -*-

'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''

import os
import sys
import importlib
import urllib
import json
import codecs

URL="https://www.dwservice.net/"
PROXY_TYPE="SYSTEM"  #HTTP or SOCKS4 or SOCKS4A or SOCKS5 or NONE
PROXY_HOST=""
PROXY_PORT=0
PROXY_USER=""
PROXY_PASSWORD=""


def is_py2():
    return sys.version_info[0]==2

if is_py2():
    def _py2_str_new(o):
        if isinstance(o, unicode):
            return o 
        elif isinstance(o, str):
            return o.decode("utf8", errors="replace")
        else:
            return str(o).decode("utf8", errors="replace")
    str_new=_py2_str_new
    url_parse_quote_plus=urllib.quote_plus
else:
    import urllib.parse
    str_new=str    
    url_parse_quote_plus=urllib.parse.quote_plus
str_to_bytes=lambda s, enc="ascii": s.encode(enc, errors="replace")

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
            appmsg=str_new(e.message)
        else:
            appmsg=str_new(e)
        return appmsg
    except:
        return u"Unexpected error."
   

if __name__ == "__main__":
    print("This script generate core/config.json")
    print("")
    pthconfig=".." + os.sep + "core" + os.sep + "config.json"
    if os.path.exists(pthconfig):
        print("Error: File core/config.json already exists. Please remove before.")
    else:
        sys.path.insert(0,".." + os.sep + "core")
        objlibcom = importlib.import_module("communication")
        set_cacerts_path = getattr(objlibcom, 'set_cacerts_path', None)
        get_url_prop = getattr(objlibcom, 'get_url_prop', None)
        ProxyInfo = getattr(objlibcom, 'ProxyInfo', None)        
        objlibagt = importlib.import_module("agent")
        obfuscate_password = getattr(objlibagt, 'obfuscate_password', None)
        print("Create a new agent from your www.dwservice.net account to getting installation code.")
        appcodemsg=u"Enter the code: "
        if is_py2():
            code  = raw_input(appcodemsg)
        else:
            code  = input(appcodemsg)
        
        url = URL + "checkInstallCode.dw?code=" + url_parse_quote_plus(code) # + "&osTypeCode=" + str(get_os_type_code()) +"&supportedApplications=" + urllib.quote_plus(spapp)
        try:
            set_cacerts_path(".." + os.sep + "core" + os.sep + "cacerts.pem")
            prx=ProxyInfo()
            prx.set_type(PROXY_TYPE)
            if not PROXY_HOST=="":
                prx.set_host(PROXY_HOST)
            if PROXY_PORT>0:
                prx.set_host(PROXY_PORT)
            if not PROXY_USER=="":
                prx.set_host(PROXY_USER)
            if not PROXY_PASSWORD=="":
                prx.set_host(PROXY_PASSWORD)
            print("Check installation code...")
            prop = get_url_prop(url, prx)
            if 'error' in prop:
                print("installation code error: " + prop['error'])
            else:
                config={}
                config['url_primary']=URL
                config['key']=prop['key']
                config['password']=obfuscate_password(prop['password'])
                config['enabled']=True
                config['debug_indentation_max']=0                
                config['debug_mode']=True
                config['develop_mode']=True                
                config['proxy_type']=PROXY_TYPE
                config['proxy_host']=PROXY_HOST
                config['proxy_port']=PROXY_PORT   
                config['proxy_user']=PROXY_USER
                config['proxy_password']=PROXY_PASSWORD                
                s = json.dumps(config, sort_keys=True, indent=1)
                f = codecs.open(pthconfig, 'wb')
                f.write(str_to_bytes(s))
                f.close()
                print("file core/config.json generated.")
        except Exception as e:
            print("Connection error: " + exception_to_string(e))
        
    print("")
    print("END.")
    
    
    
    