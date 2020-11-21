# -*- coding: utf-8 -*-
'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import utils
import os
import compile_generic

class Compile(compile_generic.Compile):
    
    def __init__(self):
        compile_generic.Compile.__init__(self,"lib_soundcapture")    
    
    def get_os_config(self,osn):
        conf=None
        if osn=="windows":
            conf={}
            conf["outname"]="dwagsoundcapture.dll" 
            conf["cpp_include_paths"]=[self.get_path_tmp() + os.sep + "lib_rtaudio", self.get_path_tmp() + os.sep + "lib_opus"]
            conf["cpp_library_paths"]=conf["cpp_include_paths"]
            conf["libraries"]=["rtaudio", "opus", "pthread"]
        elif osn=="linux":
            conf={}
            conf["outname"]="dwagsoundcapture.so" 
            conf["cpp_include_paths"]=[self.get_path_tmp() + os.sep + "lib_rtaudio", self.get_path_tmp() + os.sep + "lib_opus"] 
            conf["cpp_library_paths"]=conf["cpp_include_paths"]
            conf["libraries"]=["rtaudio", "opus"]
        elif osn=="mac":
            conf={}
            conf["outname"]="dwagsoundcapture.dylib" 
            conf["cpp_include_paths"]=[self.get_path_tmp() + os.sep + "lib_rtaudio", self.get_path_tmp() + os.sep + "lib_opus"] 
            conf["cpp_library_paths"]=conf["cpp_include_paths"]
            conf["libraries"]=["rtaudio","opus"]
        return conf
    
    def before_copy_to_native(self,osn):
        if utils.is_mac(): 
            confos=self._conf[osn] 
            utils.system_exec(["install_name_tool -change \"/usr/local/lib/librtaudio.6.dylib\" \"@loader_path/librtaudio.dylib\" " + confos["outname"]], self._conf["pathdst"])
            utils.system_exec(["install_name_tool -change \"/usr/local/lib/libopus.0.dylib\" \"@loader_path/libopus.dylib\" " + confos["outname"]], self._conf["pathdst"])

if __name__ == "__main__":    
    m = Compile()
    m.run()
    
    
    
    
    