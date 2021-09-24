# -*- coding: utf-8 -*-
'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import common
import struct
import utils
import agent
import native
import ctypes
import ipc
import time

_struct_h=struct.Struct("!h")

def test_cb_screen_encode_result(sz, pdata):
    print("sz:" + str(sz))
    sdata = pdata[0:sz]
    tp = _struct_h.unpack(sdata[0:2])[0]

if __name__ == "__main__":
    
    common.func_screen_encode_result=test_cb_screen_encode_result
    
    print("BEGIN")
    screen_listlibs = native.load_libraries_with_deps("screencapture")
    if agent.is_windows():
        cap_module = native._load_lib_obj("dwagscreencapturedesktopduplication.dll")
        #cap_module = native._load_lib_obj("dwagscreencapturebitblt.dll")
    elif agent.is_linux():
        cap_module = native._load_lib_obj("dwagscreencapturexorg.so")
    elif agent.is_mac():
        cap_module = native._load_lib_obj("dwagscreencapturequartzdisplay.dylib")
    
    screen_module = screen_listlibs[0]
    
    
    cap_module.DWAScreenCaptureLoad();
    
    moninfo = common.MONITORS_INFO()
    moninfo.count=0
    cap_module.DWAScreenCaptureGetMonitorsInfo(ctypes.byref(moninfo))
    print("monitor count:" + str(moninfo.count))
    
    mc = moninfo.count
    
    capses = ctypes.c_void_p()
    rgbimage = common.RGB_IMAGE()
    curimage = common.CURSOR_IMAGE()
    
    mi = common.MONITORS_INFO_ITEM()
    mi.index=moninfo.monitor[0].index
    mi.x=moninfo.monitor[0].x
    mi.y=moninfo.monitor[0].y
    mi.width=moninfo.monitor[0].width
    mi.height=moninfo.monitor[0].height
    
    iret = cap_module.DWAScreenCaptureInitMonitor(ctypes.byref(mi),ctypes.byref(rgbimage),ctypes.byref(capses))
    print("DWAScreenCaptureInitMonitor: " +str(iret))
    print("\n\n")
    
    encses = ctypes.c_void_p()
    screen_module.DWAScreenCaptureTJPEGEncoderInit(2,ctypes.byref(encses))
    #screen_module.DWAScreenCapturePaletteEncoderInit(1,ctypes.byref(encses))
    
    mmap = ipc.MemMap(20*1024*1024)
    
    for k in range(3):
        time.sleep(0.1)
        
        iret = cap_module.DWAScreenCaptureGetImage(capses);
        print("DWAScreenCaptureGetImage: " +str(iret))        
        print("CHANGE NUM:" + str(rgbimage.sizechangearea))
        for i in range(rgbimage.sizechangearea):
            print (str(rgbimage.changearea[i].x) + " " + str(rgbimage.changearea[i].y) + " " + str(rgbimage.changearea[i].width) + " " + str(rgbimage.changearea[i].height))
        print("MOVE NUM:" + str(rgbimage.sizemovearea))
        
        ucpu = cap_module.DWAScreenCaptureGetCpuUsage()
        print("DWAScreenCaptureGetCpuUsage: " + str(ucpu))    
    
                
        iret = cap_module.DWAScreenCaptureCursor(ctypes.byref(curimage));
        print("DWAScreenCaptureCursor iret:" + str(iret) + " visible:" + str(curimage.visible) + " x:" + str(curimage.x) + " y:" + str(curimage.y) + " offx:" + str(curimage.offx) + " offy:" + str(curimage.offy) + " w:" + str(curimage.width) + " h:" + str(curimage.height) + " changed:" + str(curimage.changed))
        
        tm = time.time()
        ltot = screen_module.DWAScreenCaptureTJPEGEncode(2,encses,90,32*1024,ctypes.byref(rgbimage),common.cb_screen_encode_result)
        #ltot = screen_module.DWAScreenCapturePaletteEncode(1,encses,32,32,32,rgbimage,cb_screen_encode_result)
        print("DWAScreenCaptureTJPEGEncode tm :" + str(time.time()-tm) + "  ltot:" + str(ltot))
                
        tm = time.time()
        mmap.seek(0)
        mmap.write("0")
        mmap.write(rgbimage)
        mmap.write((ctypes.c_char*(rgbimage.width*rgbimage.height*3)).from_address(rgbimage.data))
        print("writemmap tm :" + str(time.time()-tm) + "  POS:" + str(mmap.tell()))
        
                
        rgbimageother = common.RGB_IMAGE()
        tm = time.time()
        mmap.seek(0)
        mmap.read(1)
        bts = mmap.read(ctypes.sizeof(rgbimage))
        utils.convert_bytes_to_structure(rgbimageother,bts)
        bts = mmap.read(rgbimage.width*rgbimage.height*3)
        print("readmmap tm :" + str(time.time()-tm) + "  POS:" + str(mmap.tell()))
        
        print("\n\n")
    
    mmap.close()
    
    screen_module.DWAScreenCaptureTJPEGEncoderTerm(2,encses)
    #screen_module.DWAScreenCapturePaletteEncoderTerm(1,encses)
    cap_module.DWAScreenCaptureTermMonitor(capses)
    cap_module.DWAScreenCaptureUnload()
    native._unload_lib_obj(cap_module)
    native.unload_libraries(screen_listlibs)
    print("END")
