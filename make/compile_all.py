# -*- coding: utf-8 -*-

'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import utils
import compile_lib_z
import compile_lib_core
import compile_lib_gdi
import compile_lib_osutil
import compile_lib_screencapture
import compile_os_win_launcher
import compile_os_win_service
import compile_os_win_updater

class CompileAll():
    
    def run(self):
        bok=True
        arstatus=[]
        utils.info("BEGIN COMPILE ALL")
        try:
            self._compile(compile_lib_z,arstatus)
            self._compile(compile_lib_core,arstatus)
            self._compile(compile_lib_gdi,arstatus)
            self._compile(compile_lib_osutil,arstatus)
            if utils.is_windows():
                self._compile(compile_os_win_launcher,arstatus)
                self._compile(compile_os_win_service,arstatus)
                self._compile(compile_os_win_updater,arstatus)
            self._compile(compile_lib_screencapture,arstatus)
            utils.info("END COMPILE ALL")
        except:
            bok=False
            utils.info("ERROR COMPILE ALL")
        
        utils.info("")
        utils.info("")
        utils.info("COMPILATION STATUS:")
        for n in arstatus:
            utils.info(n)
        utils.info("")
        if bok:
            utils.info("ALL COMPILED CORRECTLY.")
        else:
            utils.info("ERRORS OCCURRED DURING COMPILATION.")
        
    
    def _compile(self,md,ars):
        mcp = md.Compile()
        smsg=mcp.get_name()
        try:
            mcp.run()
            smsg+=" - OK!"
            ars.append(smsg)
        except Exception as e:
            smsg+=" - ERROR: " + utils.exception_to_string(e)
            ars.append(smsg)
            raise e
        
    
        
if __name__ == "__main__":
    m = CompileAll()
    m.run()
    
    
    
    
    
    
    