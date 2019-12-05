# -*- coding: utf-8 -*-

'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import utils
import os
import shutil
import codecs
import detectinfo
import compile_lib_core
import compile_lib_gdi
import compile_lib_osutil
import compile_lib_screencapture
import compile_os_win_launcher
import compile_os_win_service
import compile_os_win_updater


class CompileAll():
    
    def __init__(self):
        self._cpp_compiler_flags=None
        self._linker_flags=None
        self._b32bit=False
    
    def set_32bit(self):
        self._b32bit=True
        self._cpp_compiler_flags="-m32"
        self._linker_flags="-m32"
    
    def run(self):
        bok=True        
        arstatus=[]
        utils.init_path(utils.PATHNATIVE)
        utils.info("BEGIN DEPENDENCIES")
        try:
            self._dependency("lib_z", "1.2.11", arstatus)
            self._dependency("lib_turbojpeg", "2.0.3", arstatus)
            utils.info("END DEPENDENCIES")
        except:
            bok=False
            utils.info("ERROR DEPENDENCIES")
        
        if bok:
            utils.info("BEGIN COMPILE ALL")
            try:
                self._compile(compile_lib_core,arstatus)
                self._compile(compile_lib_gdi,arstatus)
                self._compile(compile_lib_osutil,arstatus)
                if utils.is_windows():
                    self._compile(compile_os_win_launcher,arstatus)
                    self._compile(compile_os_win_service,arstatus)
                    self._compile(compile_os_win_updater,arstatus)
                self._compile(compile_lib_screencapture,arstatus)
                utils.info("END COMPILE ALL")
            except:
                bok=False
                utils.info("ERROR COMPILE ALL")
        
         
        utils.info("")
        utils.info("")
        utils.info("STATUS:")
        for n in arstatus:
            utils.info(n)
        utils.info("")
        if bok:
            utils.info("ALL COMPILED CORRECTLY.")
        else:
            utils.info("ERRORS OCCURRED.")
        
    
    def _compile(self,md,ars):
        mcp = md.Compile()
        smsg=mcp.get_name()
        try:
            cflgs=self._cpp_compiler_flags
            if cflgs is not None:
                if utils.is_windows():        
                    mcp.set_cpp_compiler_flags("windows",cflgs)                
                elif utils.is_linux():
                    mcp.set_cpp_compiler_flags("linux",cflgs)                
                elif utils.is_mac():
                    mcp.set_cpp_compiler_flags("mac",cflgs)
                    
            lflgs=self._linker_flags
            if lflgs is not None:
                if utils.is_windows():        
                    mcp.set_linker_flags("windows",lflgs)                
                elif utils.is_linux():
                    mcp.set_linker_flags("linux",lflgs)                
                elif utils.is_mac():
                    mcp.set_linker_flags("mac",lflgs)
                    
            mcp.run()
            smsg+=" - OK!"
            ars.append(smsg)
        except Exception as e:
            smsg+=" - ERROR: " + utils.exception_to_string(e)
            ars.append(smsg)
            raise e
    
    def _dependency_post_fix(self,snm,sver):
        spth=utils.PATHTMP + os.sep + snm;
        if snm=="lib_z":
            if utils.is_mac():   
                #CORREGGE zutil.h
                apppth=spth + os.sep + "zutil.h"
                f = codecs.open(apppth, encoding='utf-8')
                appdata = f.read()
                f.close()
                appdata=appdata.replace('#  define local static','//#  define local static')
                os.remove(apppth)
                f = codecs.open(apppth, encoding='utf-8', mode='w+')
                f.write(appdata)
                f.close()
    
    def _dependency(self,snm,sver,ars):        
        spth=utils.PATHTMP + os.sep + snm;
        smsg = snm + " " + sver
        utils.info("BEGIN " + snm)        
        try:
            conf = utils.read_json_file(spth + os.sep + snm + ".json")
            bupd=True; 
            if conf is not None:
                if "version" in conf:
                    if conf["version"]==sver:
                        bupd=False
                    else:
                        utils.info("incorrect version.")
                else:
                    utils.info("version not found.")
            else:
                utils.info("version not found.")
            if bupd:
                sfx = detectinfo.get_native_suffix()
                if sfx is None or "generic" in sfx:
                    utils.info("os not detected.")
                    raise Exception("You have to compile it manually.")
                if self._b32bit:
                    sfx=sfx.replace("64","32")                
                utils.init_path(spth)
                utils.info("download headers and library ...")
                nurl = utils.get_node_url()
                appnm="headers_" + snm + ".zip"
                utils.download_file(nurl + "getAgentFile.dw?name=" + appnm , spth + os.sep + appnm)
                utils.unzip_file(spth + os.sep + appnm, spth + os.sep)
                utils.remove_file(spth + os.sep + appnm)
                appnm=snm + "_" + sfx + ".zip"
                utils.download_file(nurl + "getAgentFile.dw?name=" + appnm , spth + os.sep + appnm)
                utils.unzip_file(spth + os.sep + appnm, spth + os.sep, "native/")
                utils.remove_file(spth + os.sep + appnm)
                #FIX Version
                conf = utils.read_json_file(spth + os.sep + snm + ".json")
                if conf is not None:
                    if "version" not in conf:
                        conf["version"]=sver
                        utils.write_json_file(conf, spth + os.sep + snm + ".json")
            
            #COPY LIB TO NATIVE
            for f in os.listdir(spth):
                if f.endswith('.dll') or f.endswith('.so') or f.endswith('.dylib'): 
                    shutil.copy2(spth + os.sep + f, utils.PATHNATIVE + os.sep + f)
            
            #POST FIX
            self._dependency_post_fix(snm,sver)
            
            smsg+=" - OK!"
            ars.append(smsg)
            utils.info("END " + snm)
        except Exception as e:
            smsg+=" - ERROR: " + utils.exception_to_string(e)
            ars.append(smsg)
            raise e
        
if __name__ == "__main__":
    m = CompileAll()
    #m.set_32bit()
    m.run()
    
    
    
    
    
    
    