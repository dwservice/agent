# -*- coding: utf-8 -*-
'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import common
import utils
import agent
import native
import ctypes
import ipc
import time

def test_cb_sound_encode_result(sz, pdata):
    print("sz:" + str(sz))    

def test_cb_sound_data(sz, pdata):
    common._libmap["test_buff_data"].append(pdata[0:sz])

if __name__ == "__main__":   
    
    common.func_sound_encode_result=test_cb_sound_encode_result
    common._libmap["cb_sound_data"]=test_cb_sound_data
    sound_listlibs = native.load_libraries_with_deps("soundcapture")
    sound_module = sound_listlibs[0]
    
    capses = ctypes.c_void_p()
    aconf = common.AUDIO_CONFIG()
    aconf.numChannels = 2
    aconf.sampleRate = 48000
    aconf.bufferFrames = int(aconf.sampleRate*(20.0/1000.0))
    
    common._libmap["test_buff_data"]=[]
    
    iret = sound_module.DWASoundCaptureStart(ctypes.byref(aconf),common.cb_sound_data,ctypes.byref(capses))
    print("DWASoundCaptureStart: " +str(iret))
    
    
    bf = ctypes.create_string_buffer(2048)
    l = sound_module.DWASoundCaptureGetDetectOutputName(capses,bf,2048);
    if l>0:
        sodn=bf.value[0:l]
    else:
        sodn=""
    print("DWASoundCaptureGetDetectOutputName: " +sodn)
    
    print("SLEEP 2")
    time.sleep(2)
    
    sound_module.DWASoundCaptureStop(capses);
    print("DWASoundCaptureStop")
    
        
    fulldt = "".join(common._libmap["test_buff_data"])
    print("FULL DATA len: " + str(len(fulldt)))
    
    encses = ctypes.c_void_p()
    sound_module.DWASoundCaptureOPUSEncoderInit(ctypes.byref(aconf),ctypes.byref(encses))
    
    #aa=ctypes.cast(ctypes.c_void_p(resp["frame_data"]),ctypes.c_void_p)
    #aa = ctypes.POINTER(fulldt)
    
    iret = sound_module.DWASoundCaptureOPUSEncode(encses, fulldt, len(fulldt), common.cb_sound_encode_result)
    print("DWASoundCaptureOPUSEncode: " +str(iret))
    print("\n\n")
    
    sound_module.DWASoundCaptureOPUSEncoderTerm(encses)
    
    
    native.unload_libraries(sound_listlibs)
    print("END")

