# -*- coding: utf-8 -*-

'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import utils
import os

PRJNAME="lib_osutil"

CONF = {}
CONF["pathsrc"]=".." + os.sep + PRJNAME + os.sep + "src"
CONF["pathdst"]=utils.PATHTMP + os.sep + PRJNAME

CONF_WINDOWS={}
CONF_WINDOWS["outname"]="dwagosutil.dll" 
CONF_WINDOWS["cpp_include_paths"]=[] 
CONF_WINDOWS["cpp_library_paths"]=CONF_WINDOWS["cpp_include_paths"]
CONF_WINDOWS["libraries"]=["psapi", "user32"]
CONF["windows"]=CONF_WINDOWS

'''
CONF_LINUX={}
CONF_LINUX["outname"]="dwagosutil.so" 
CONF_LINUX["cpp_include_paths"]=[] 
CONF_LINUX["cpp_library_paths"]=CONF_LINUX["cpp_include_paths"]
CONF_LINUX["libraries"]=["X11", "Xpm"]
CONF["linux"]=CONF_LINUX

CONF_MAC={}
CONF_MAC["outname"]="dwagosutil.dylib" 
CONF_MAC["cpp_include_paths"]=[] 
CONF_MAC["cpp_library_paths"]=CONF_MAC["cpp_include_paths"]
CONF_MAC["libraries"]=[] 
CONF["mac"]=CONF_MAC
'''

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
            utils.copy_to_native(CONF)
        utils.info("END " + self.get_name())
        
if __name__ == "__main__":
    m = Compile()
    m.run()
    
    
    
    
    
    
    