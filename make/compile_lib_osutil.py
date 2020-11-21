# -*- coding: utf-8 -*-

'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import compile_generic

class Compile(compile_generic.Compile):
    
    def __init__(self):
        compile_generic.Compile.__init__(self,"lib_osutil")
    
    def get_os_config(self,osn):
        conf=None
        if osn=="windows":
            conf={}
            conf["outname"]="dwagosutil.dll" 
            conf["cpp_include_paths"]=[] 
            conf["cpp_library_paths"]=conf["cpp_include_paths"]
            conf["libraries"]=["psapi", "user32"]
            conf["linker_flags"]="-static-libgcc -static-libstdc++" #DA RIMUOVERE E CORREGGERE config.json "lib_dependencies": ["stdcpp",...
        elif osn=="linux":
            None
            '''
            conf={}
            conf["outname"]="dwagosutil.so" 
            conf["cpp_include_paths"]=[] 
            conf["cpp_library_paths"]=conf["cpp_include_paths"]
            conf["libraries"]=["X11", "Xpm"]
            '''
        elif osn=="mac":
            None
            '''
            conf={}
            conf["outname"]="dwagosutil.dylib" 
            conf["cpp_include_paths"]=[] 
            conf["cpp_library_paths"]=conf["cpp_include_paths"]
            conf["libraries"]=[] 
            '''
        return conf
        
if __name__ == "__main__":
    m = Compile()
    m.run()
    
    
    
    
    
    