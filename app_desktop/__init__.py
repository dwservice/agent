# -*- coding: utf-8 -*-

'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import sys
import ctypes
from desktop import Desktop
from desktop import CaptureProcess

def get_instance(args):
    return Desktop(args)

def run_main(args):
    fmain(args)

def ctrlHandler(ctrlType):    
    return 1
         
def fmain(args): #SERVE PER MACOS APP
    if args[3]=="windows":
        try:
            #Evita che si chiude durante il logoff
            HandlerRoutine = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_uint)(ctrlHandler)
            ctypes.windll.kernel32.SetConsoleCtrlHandler(HandlerRoutine, 1)
        except:
            None
        
    captureprocess = CaptureProcess(None)
    if args[3]=="windows" and args[4]=="True":
        captureprocess._get_osmodule().setAsElevated(1)
    captureprocess.listen(args[1],args[2])
    captureprocess.destroy()    
    sys.exit(0)

if __name__ == "__main__":
    fmain(sys.argv)

