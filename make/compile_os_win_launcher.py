# -*- coding: utf-8 -*-

'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import utils
import os

PRJNAME="os_win_launcher"

CONF = {}
CONF["pathsrc"]=".." + os.sep + PRJNAME + os.sep + "src"
CONF["pathdst"]=utils.PATHTMP + os.sep + PRJNAME

CONF_WINDOWS={}
CONF_WINDOWS["outname"]="dwaglnc.exe" 
CONF_WINDOWS["cpp_include_paths"]=[]
CONF_WINDOWS["cpp_library_paths"]=CONF_WINDOWS["cpp_include_paths"]
CONF_WINDOWS["libraries"]=["user32", "advapi32", "userenv", "shell32"]
CONF["windows"]=CONF_WINDOWS


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
    
    
    
    
    
    