# -*- coding: utf-8 -*-

'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import compile_generic

class Compile(compile_generic.Compile):
    
    def __init__(self):
        compile_generic.Compile.__init__(self,"os_win_launcher")
    
    def get_os_config(self,osn):
        conf=None
        if osn=="windows":
            conf={}
            conf["outname"]="dwaglnc.exe" 
            conf["cpp_include_paths"]=[]
            conf["cpp_library_paths"]=conf["cpp_include_paths"]
            conf["libraries"]=["user32", "advapi32", "userenv", "shell32"]
            conf["linker_flags"]="-static-libgcc -static-libstdc++"
        return conf


if __name__ == "__main__":
    m = Compile()
    m.run()
    
    
    
    
    
    