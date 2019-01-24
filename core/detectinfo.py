# -*- coding: utf-8 -*-

'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''

import platform
import subprocess
import sys
import utils

def is_windows():
    return (platform.system().lower().find("window") > -1)

def is_linux():
    return (platform.system().lower().find("linux") > -1)

def is_mac():
    return (platform.system().lower().find("darwin") > -1)

def is_os_32bit():
    return not sys.maxsize > 2**32

def is_os_64bit():
    return sys.maxsize > 2**32

def get_hw_name():
    sapp = platform.machine()
    if is_linux() and len(sapp)>=3 and (sapp[0:3].lower()=="arm" or sapp[0:7].lower()=="aarch64"):
        #VERIFICA SE RASPBERRY
        try:
            if utils.path_exists("/sys/firmware/devicetree/base/model"):
                fin=utils.file_open("/sys/firmware/devicetree/base/model","r")
                appmdl = fin.read()
                fin.close()
                if "raspberry" in appmdl.lower():
                    return "RaspberryPi"
                elif "wandboard" in appmdl.lower():
                    return "Wandboard"
                elif "pine64" in appmdl.lower() or "rock64" in appmdl.lower():
                    return "Pine64"
        except:
            None
    return None


def get_native_suffix():
    try:
        hwnm = get_hw_name()
        if hwnm == "RaspberryPi":
            return "linux_armhf_v2"        
        elif hwnm == "Wandboard":
            return "linux_armhf_v1"
        elif hwnm == "Pine64":
            return "linux_arm64_v1"
        
        sapp = platform.machine()
        if sapp is not None:
            if sapp.upper()=="AMD64" or sapp.lower()=="x86_64" or sapp.lower()=="i386" or sapp.lower()=="x86" or (len(sapp)==4 and sapp[0]=="i" and sapp[2:4]=="86"):
                if is_linux():
                    if is_os_64bit():
                        return "linux_x86_64"
                    elif is_os_32bit():
                        return "linux_x86_32"
                elif is_windows():
                    if is_os_64bit():
                        return "win_x86_64"
                    elif is_os_32bit():
                        return "win_x86_32"
                elif is_mac():
                    if is_os_64bit():
                        return "mac_x86_64"
                    elif is_os_32bit():
                        return "mac_x86_32"                
            elif is_linux() and len(sapp)>=3 and sapp[0:3].lower()=="arm":
                try:
                    if is_os_64bit():
                        return "linux_arm64_v1"
                    else:
                        p = subprocess.Popen("readelf -A /proc/self/exe | grep Tag_ABI_VFP_args", stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                        (o, e) = p.communicate()
                        if len(e)==0:
                            if len(o)>0:
                                return "linux_armhf_v1"
                            else:
                                None
                                #return "linux_armel"
                except:
                    None
            elif is_linux() and len(sapp)>=3 and sapp[0:7].lower()=="aarch64":
                return "linux_arm64_v1"
    except:
        None
    if is_linux():
        return "linux_generic" 
    return None

if __name__ == "__main__":
    print get_native_suffix()
    