# -*- coding: utf-8 -*-
'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import compile_generic
import os
import utils

class Compile(compile_generic.Compile):
    
    def __init__(self):
        compile_generic.Compile.__init__(self,"lib_screencapture")
    
    def get_os_config(self,osn):
        conf=None
        if osn=="windows":
            conf={}
            conf["outname"]="dwagscreencapture.dll" 
            conf["cpp_include_paths"]=[self.get_path_tmp() + os.sep + "lib_z", self.get_path_tmp() + os.sep + "lib_turbojpeg"]
            conf["cpp_library_paths"]=conf["cpp_include_paths"]
            conf["libraries"]=["zlib1", "turbojpeg", "gdi32", "userenv"]
            conf["linker_flags"]="-static-libgcc -static-libstdc++" #DA RIMUOVERE E CORREGGERE config.json "lib_dependencies": ["stdcpp",...
        elif osn=="linux":
            conf={}
            conf["outname"]="dwagscreencapture.so" 
            conf["cpp_include_paths"]=[self.get_path_tmp() + os.sep + "lib_z", self.get_path_tmp() + os.sep + "lib_turbojpeg"] 
            conf["cpp_library_paths"]=conf["cpp_include_paths"]
            conf["libraries"]=["X11", "z", "turbojpeg", "Xext", "dl", "Xtst"]
        elif osn=="mac":
            conf={}
            conf["outname"]="dwagscreencapture.dylib" 
            conf["cpp_include_paths"]=[self.get_path_tmp() + os.sep + "lib_z", self.get_path_tmp() + os.sep + "lib_turbojpeg"] 
            conf["cpp_library_paths"]=conf["cpp_include_paths"]
            conf["libraries"]=["z", "turbojpeg"]
            conf["frameworks"]=["ApplicationServices","SystemConfiguration","IOKit","Carbon"]
        return conf
        
    def before_copy_to_native(self,osn):
        if utils.is_mac(): 
            confos=self._conf[osn]
            utils.system_exec(["install_name_tool -change \"/usr/local/lib/libz.1.dylib\" \"@loader_path/libz.dylib\" " + confos["outname"]], self._conf["pathdst"])
            utils.system_exec(["install_name_tool -change \"/opt/libjpeg-turbo/lib/libturbojpeg.0.2.0.dylib\" \"@loader_path/libturbojpeg.dylib\" " + confos["outname"]], self._conf["pathdst"])

if __name__ == "__main__":    
    m = Compile()
    m.run()
    
    
    
    
    
    