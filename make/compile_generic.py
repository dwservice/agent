# -*- coding: utf-8 -*-

'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import os
import utils

class Compile():
    
    def __init__(self,nm):
        self._conf={}
        self._name=nm
        self._b32bit=False
    
    def get_name(self):
        return self._name;    
    
    def get_os_config(self,osn):
        None
    
    def set_32bit(self):
        self._b32bit=True
    
    def get_path_tmp(self):
        if self._b32bit:
            return utils.PATHTMP+"32"
        else:
            return utils.PATHTMP
    
    def get_path_native(self):
        if self._b32bit:
            return utils.PATHNATIVE+"32"
        else:
            return utils.PATHNATIVE
    
    def before_copy_to_native(self,osn):
        None
    
    def run(self):
        utils.info("BEGIN " + self.get_name())
        #PREPARE CONF        
        self._conf["pathsrc"]=".." + os.sep + self._name + os.sep + "src"
        self._conf["pathdst"]=self.get_path_tmp() + os.sep + self._name
        osn=None
        if utils.is_windows():
            osn="windows"
        elif utils.is_linux():
            osn="linux"                        
        elif utils.is_mac():
            osn="mac"
        if osn is not None:
            appcnf=self.get_os_config(osn)
            if appcnf is not None:
                self._conf[osn]=appcnf
        
        if self._b32bit and osn in self._conf:
            if "linker_flags" not in self._conf[osn]:
                self._conf[osn]["linker_flags"]="-m32"
            else:
                self._conf[osn]["linker_flags"]="-m32 " + self._conf[osn]["linker_flags"]
            if "cpp_compiler_flags" not in self._conf[osn]:
                self._conf[osn]["cpp_compiler_flags"]="-m32"
            else:
                self._conf[osn]["cpp_compiler_flags"]="-m32 " + self._conf[osn]["cpp_compiler_flags"]
                
        #START COMPILE CONF
        utils.make_tmppath(self.get_path_tmp())
        utils.remove_from_native(self.get_path_native(), self._conf)
        confos=utils.compile_lib(self._conf)
        if confos is not None:
            self.before_copy_to_native(osn)  
            utils.copy_to_native(self.get_path_native(),self._conf)
        utils.info("END " + self.get_name())
        
        
        