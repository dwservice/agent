# -*- coding: utf-8 -*-

'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import compile_generic

class Compile(compile_generic.Compile):
    
    def __init__(self):
        compile_generic.Compile.__init__(self,"lib_gdi")

    def get_os_config(self,osn):
        conf=None
        if osn=="windows":
            conf={}
            conf["outname"]="dwaggdi.dll" 
            conf["cpp_include_paths"]=[] 
            conf["cpp_library_paths"]=conf["cpp_include_paths"]
            conf["libraries"]=["gdi32", "shell32", "user32", "userenv"]
            conf["linker_flags"]="-static-libgcc -static-libstdc++"
        elif osn=="linux":
            conf={}
            conf["outname"]="dwaggdi.so" 
            conf["cpp_include_paths"]=[] 
            conf["cpp_library_paths"]=conf["cpp_include_paths"]
            conf["libraries"]=["X11", "Xpm"]
        elif osn=="mac":
            None
            '''
            conf={}
            conf["outname"]="dwaggdi.dylib" 
            conf["cpp_include_paths"]=[] 
            conf["cpp_library_paths"]=conf["cpp_include_paths"]
            conf["libraries"]=[] 
            '''
        return conf

if __name__ == "__main__":
    m = Compile()
    m.run()
    
    
    
    
    
    
    