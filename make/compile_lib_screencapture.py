# -*- coding: utf-8 -*-
'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import utils
import os

PRJNAME="lib_screencapture"

CONF = {}
CONF["pathsrc"]=".." + os.sep + PRJNAME + os.sep + "src"
CONF["pathdst"]=utils.PATHTMP + os.sep + PRJNAME

CONF_WINDOWS={}
CONF_WINDOWS["outname"]="dwagscreencapture.dll" 
CONF_WINDOWS["cpp_include_paths"]=[utils.PATHTMP + os.sep + "lib_z", utils.PATHTMP + os.sep + "lib_turbojpeg"]
CONF_WINDOWS["cpp_library_paths"]=CONF_WINDOWS["cpp_include_paths"]
CONF_WINDOWS["libraries"]=["zlib1", "turbojpeg", "gdi32", "userenv"]
CONF["windows"]=CONF_WINDOWS

CONF_LINUX={}
CONF_LINUX["outname"]="dwagscreencapture.so" 
CONF_LINUX["cpp_include_paths"]=[utils.PATHTMP + os.sep + "lib_z", utils.PATHTMP + os.sep + "lib_turbojpeg"] 
CONF_LINUX["cpp_library_paths"]=CONF_LINUX["cpp_include_paths"]
CONF_LINUX["libraries"]=["X11", "z", "turbojpeg", "Xext", "dl", "Xtst"]
CONF["linux"]=CONF_LINUX

CONF_MAC={}
CONF_MAC["outname"]="dwagscreencapture.dylib" 
CONF_MAC["cpp_include_paths"]=[utils.PATHTMP + os.sep + "lib_z", utils.PATHTMP + os.sep + "lib_turbojpeg"] 
CONF_MAC["cpp_library_paths"]=CONF_MAC["cpp_include_paths"]
CONF_MAC["libraries"]=["z", "turbojpeg"]
CONF_MAC["frameworks"]=["ApplicationServices","SystemConfiguration","IOKit","Carbon"]
CONF["mac"]=CONF_MAC

class Compile():
    
    def get_name(self):
        return PRJNAME;
    
    def set_cpp_compiler_flags(self, osn, flgs):
        if osn in CONF:
            CONF[osn]["cpp_compiler_flags"]=flgs
    
    def set_linker_flags(self, osn, flgs):
        if osn in CONF:
            CONF[osn]["linker_flags"]=flgs
    
    def run(self):
        utils.info("BEGIN " + self.get_name())
        utils.make_tmppath()
        utils.remove_from_native(CONF)
        confos=utils.compile_lib(CONF)
        if confos is not None:
            if utils.is_mac(): 
                utils.system_exec(["install_name_tool -change \"/usr/local/lib/libz.1.dylib\" \"@loader_path/libz.dylib\" " + confos["outname"]], CONF["pathdst"])
                utils.system_exec(["install_name_tool -change \"/opt/libjpeg-turbo/lib/libturbojpeg.0.2.0.dylib\" \"@loader_path/libturbojpeg.dylib\" " + confos["outname"]], CONF["pathdst"])
            utils.copy_to_native(CONF)
        utils.info("END " + self.get_name())

if __name__ == "__main__":    
    m = Compile()
    m.run()
    
    
    
    
    
    