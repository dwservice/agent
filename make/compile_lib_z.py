# -*- coding: utf-8 -*-

'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import utils
import os
import stat
import subprocess
import codecs

PRJNAME="lib_z"

CONF = {}
CONF["name"]="zlib"
CONF["version"]="1.2.11"
#CONF["urlsrc"]="https://www.dwservice.net/srcdeplib/zlib-" + CONF["version"] + ".tar.gz"
CONF["urlsrc"]="https://zlib.net/zlib-" + CONF["version"] + ".tar.gz"
CONF["pathdst"]=utils.PATHTMP + os.sep + PRJNAME

CONF_WINDOWS={}
CONF_WINDOWS["outname"]="zlib1.dll" 
CONF["windows"]=CONF_WINDOWS

CONF_LINUX={}
CONF_LINUX["outname"]="libz.so" 
CONF["linux"]=CONF_LINUX

CONF_MAC={}
CONF_MAC["outname"]="libz.so" 
CONF["mac"]=CONF_MAC


class Compile():
    
    def get_name(self):
        return CONF["name"];
    
    def run(self):
        utils.info("BEGIN " + self.get_name())
        utils.make_tmppath()
        tarname=CONF["name"] + "-" + CONF["version"] + ".tar.gz"        
        utils.remove_from_native(CONF)
        if os.path.exists(CONF["pathdst"]):
            utils.remove_path(CONF["pathdst"])
        if os.path.exists(utils.PATHTMP + os.sep + tarname):
            utils.remove_path(utils.PATHTMP + os.sep + tarname)
        if os.path.exists(utils.PATHTMP + os.sep + CONF["name"] + "-" + CONF["version"]):
            utils.remove_path(utils.PATHTMP + os.sep + CONF["name"] + "-" + CONF["version"])
        utils.download_file(CONF["urlsrc"], utils.PATHTMP + os.sep + tarname)
        utils.untar_file(utils.PATHTMP + os.sep + tarname, utils.PATHTMP)
        utils.remove_file(utils.PATHTMP + os.sep + tarname)
        os.rename(utils.PATHTMP + os.sep + CONF["name"] + "-" + CONF["version"], CONF["pathdst"])
        
        if utils.is_mac():
            #CORREGGE configure
            apppth=CONF["pathdst"] + os.sep + "configure"
            f = codecs.open(apppth, encoding='utf-8')
            appdata = f.read()
            f.close()
            appdata=appdata.replace('.dylib','.so').replace("-dynamiclib","-shared")
            os.remove(apppth)
            f = codecs.open(apppth, encoding='utf-8', mode='w+')
            f.write(appdata)
            f.close()
            os.chmod(apppth, stat.S_IRWXU)
            
        
        if utils.is_windows():
            utils.system_exec(["mingw32-make.exe", "-fwin32/Makefile.gcc"],CONF["pathdst"])
        else:
            utils.system_exec(["./configure"],CONF["pathdst"])
            utils.system_exec(["make"],CONF["pathdst"])
         
        if utils.is_mac():   
            #CORREGGE zutil.h
            apppth=CONF["pathdst"] + os.sep + "zutil.h"
            f = codecs.open(apppth, encoding='utf-8')
            appdata = f.read()
            f.close()
            appdata=appdata.replace('#  define local static','//#  define local static')
            os.remove(apppth)
            f = codecs.open(apppth, encoding='utf-8', mode='w+')
            f.write(appdata)
            f.close()
        
        utils.copy_to_native(CONF)
        utils.info("END " + self.get_name())

if __name__ == "__main__":
    m = Compile()
    m.run()
    
    
    
    
    