# -*- coding: utf-8 -*-

'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import os
import utils

'''
### TO CHECK
ARCH_X86_64="x86_64" 
ARCH_X86_32="x86_32"
'''

ARCH_WINDOWS_X86_64="win_x86_64"
ARCH_WINDOWS_X86_32="win_x86_32"
ARCH_WINDOWS_ARM64="win_arm64"

class Compile():
    
    def __init__(self,nm,lbl=None):
        self._conf={}
        self._name=nm
        self._label=lbl
        self._arch=None
        self._b32bit=False
    
    def get_name(self):
        if self._label is not None:
            return self._name + " (" + self._label + ")"; 
        else:
            return self._name;    
    
    def get_os_config(self,osn):
        None
    
    def set_arch(self, v):
        self._arch=v
    
    def _get_path_tp(self, pth):
        if self._arch is not None:
            pth+="_"+self._arch
        return pth
    
    def get_path_tmp(self):
        return self._get_path_tp(utils.PATHTMP)
    
    def get_path_native(self):
        return self._get_path_tp(utils.PATHNATIVE)
    
    def before_copy_to_native(self,osn):
        None
    
    def run(self):
        utils.info("BEGIN " + self.get_name())
        #PREPARE CONF        
        self._conf["pathprj"]=".." + os.sep + self._name
        self._conf["pathsrc"]=".." + os.sep + self._name + os.sep + "src"
        self._conf["pathdst"]=self.get_path_tmp() + os.sep + self._name
        osn=None
        if utils.is_windows():
            osn="windows"
        elif utils.is_linux():
            osn="linux"                        
        elif utils.is_mac():
            osn="mac"
        if self._arch is not None: 
            if self._arch.startswith("win_"):
                osn="windows"
            elif self._arch.startswith("linux_"):
                osn="linux"
            elif self._arch.startswith("mac_"):
                osn="mac"
            
        if osn is not None:
            self._conf["os"]=osn            
            appcnf=self.get_os_config(osn)
            if appcnf is not None:
                self._conf[osn]=appcnf
        
        if self._arch is not None and osn in self._conf:
            aopt=None
            
            '''
            ### TO CHECK
            if self._arch==ARCH_X86_64: 
                aopt="-arch x86_64"
            elif self._arch==ARCH_X86_32:
                aopt="-m32"
            '''
            if self._arch==ARCH_WINDOWS_X86_64:
                if utils.is_linux():
                    self._conf[osn]["cpp_command"]=os.path.abspath("../../../llvm-mingw-20260421-msvcrt-ubuntu-22.04-x86_64/bin/x86_64-w64-mingw32-g++")
                    self._conf[osn]["c_command"]=os.path.abspath("../../../llvm-mingw-20260421-msvcrt-ubuntu-22.04-x86_64/bin/x86_64-w64-mingw32-gcc")
                    #self._conf[osn]["cpp_command"]=os.path.abspath("../../../x86_64-w64-mingw32/bin/x86_64-w64-mingw32-g++")
                    #self._conf[osn]["c_command"]=os.path.abspath("../../../x86_64-w64-mingw32/bin/x86_64-w64-mingw32-gcc")
            elif self._arch==ARCH_WINDOWS_X86_32:
                if utils.is_linux():
                    self._conf[osn]["cpp_command"]=os.path.abspath("../../../i686-w64-mingw32/bin/i686-w64-mingw32-g++")
                    self._conf[osn]["c_command"]=os.path.abspath("../../../i686-w64-mingw32/bin/i686-w64-mingw32-gcc")
            elif self._arch==ARCH_WINDOWS_ARM64:
                if utils.is_linux():
                    self._conf[osn]["cpp_command"]=os.path.abspath("../../../llvm-mingw-20260421-ucrt-ubuntu-22.04-x86_64/bin/aarch64-w64-mingw32-g++")
                    self._conf[osn]["c_command"]=os.path.abspath("../../../llvm-mingw-20260421-ucrt-ubuntu-22.04-x86_64/bin/aarch64-w64-mingw32-gcc")
            
            if aopt is not None:
                if "linker_flags" not in self._conf[osn]:
                    self._conf[osn]["linker_flags"]=aopt
                else:
                    self._conf[osn]["linker_flags"]=aopt + " " + self._conf[osn]["linker_flags"]
                if "cpp_compiler_flags" not in self._conf[osn]:
                    self._conf[osn]["cpp_compiler_flags"]=aopt
                else:
                    self._conf[osn]["cpp_compiler_flags"]=aopt + " " + self._conf[osn]["cpp_compiler_flags"]       
        try:
            #START COMPILE CONF
            utils.make_tmppath(self.get_path_tmp())
            utils.remove_from_native(self.get_path_native(), self._conf)
            confos=utils.compile_lib(self._conf)
            if confos is not None:
                self.before_copy_to_native(osn)  
                utils.copy_to_native(self.get_path_native(),self._conf)
            utils.info("END " + self.get_name())
        except Exception as e:
            se=str(e)
            if se=="Compiler error." or se=="Linker error.":
                utils.info("ERROR " + self.get_name() + ": " + se)
                return
            else:
                raise e;        
        
        
        
        