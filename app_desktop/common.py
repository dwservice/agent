# -*- coding: utf-8 -*-

'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import ctypes

_libmap={}
_libmap["lastID"]=0l
_libmap["capscrID"]=0l

#CALLBACKS
SCRDBGFUNC = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_wchar_p)
SCRENCRESFUNC = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_char))
SNDDATAFUNC = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_uint, ctypes.POINTER(ctypes.c_char))
SNDENCRESFUNC = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_char))

@SCRDBGFUNC  
def cb_debug_print(s):
    f = _libmap["cb_debug_print"]
    if f is not None:
        f(s)

func_screen_encode_result=None
@SCRENCRESFUNC
def cb_screen_encode_result(sz, pdata):
    func_screen_encode_result(sz, pdata)
    
@SNDDATAFUNC
def cb_sound_data(sz, pdata):
    f = _libmap["cb_sound_data"]
    if f is not None:
        f(sz, pdata)

func_sound_encode_result=None
@SNDENCRESFUNC
def cb_sound_encode_result(sz, pdata):
    func_sound_encode_result(sz, pdata)    


TOKEN_RESOLUTION=0 #DATA=W-H 
TOKEN_FRAME=2 #DATA=L-X-Y-W-H-IMG - L=End frame (1:YES 0:NO)
TOKEN_CURSOR=3 #DATA=V-X-Y-W-H-OFFX-OFFY-IMG - V=Visible (1:YES 0:NO)
TOKEN_MONITOR=10 #DATA=SZ
TOKEN_SUPPORTED_FRAME=11 #DATA=CNT-S1-S2-...
TOKEN_FPS=600
TOKEN_FRAME_TIME=800 
TOKEN_FRAME_TYPE=801
TOKEN_FRAME_LOCKED=701
TOKEN_FRAME_UNLOCKED=702
TOKEN_AUDIO_TYPE=809
TOKEN_AUDIO_DATA=810
TOKEN_AUDIO_ERROR=811
TOKEN_SESSION_ID=900
TOKEN_SESSION_ALIVE=901
TOKEN_SESSION_ERROR=999
TOKEN_SESSION_STATS=991

VK_SHIFT          = 0x10
VK_CONTROL        = 0x11
VK_ALT            = 0x12



TYPE_FRAME_PALETTE_V1 =  0
TYPE_FRAME_TJPEG_V1 = 100
TYPE_FRAME_TJPEG_V2 = 101

MAX_CURSOR_IMAGE_SIZE=256
RGB_IMAGE_DIFFSIZE = 1000
MONITORS_INFO_ITEM_MAX=1000;

class MONITORS_INFO_ITEM(ctypes.Structure):
    _fields_ = [("index",ctypes.c_int),
                ("x",ctypes.c_int),
                ("y",ctypes.c_int),
                ("width",ctypes.c_int),
                ("height",ctypes.c_int),
                ("changed",ctypes.c_int),
                ("internal", ctypes.c_void_p)]

class MONITORS_INFO(ctypes.Structure):
    _fields_ = [("count",ctypes.c_int),
                ("changed",ctypes.c_int),
                ("monitor", MONITORS_INFO_ITEM*MONITORS_INFO_ITEM_MAX)]

class RGB_IMAGE_CHANGE_AREA(ctypes.Structure):
    _fields_ = [("x",ctypes.c_int),
                ("y",ctypes.c_int),
                ("width",ctypes.c_int),
                ("height",ctypes.c_int)]
                
class RGB_IMAGE_MOVE_AREA(ctypes.Structure):
    _fields_ = [("x",ctypes.c_int),
                ("y",ctypes.c_int),
                ("width",ctypes.c_int),
                ("height",ctypes.c_int),
                ("xdest",ctypes.c_int),
                ("ydest",ctypes.c_int)]

class RGB_IMAGE(ctypes.Structure):
    _fields_ = [("width",ctypes.c_int),
                ("height",ctypes.c_int),
                ("sizedata",ctypes.c_long),
                ("data", ctypes.c_void_p),
                ("sizechangearea",ctypes.c_int),
                ("changearea", RGB_IMAGE_CHANGE_AREA*RGB_IMAGE_DIFFSIZE),
                ("sizemovearea",ctypes.c_int),                                                
                ("movearea", RGB_IMAGE_MOVE_AREA*RGB_IMAGE_DIFFSIZE)]

class CURSOR_IMAGE(ctypes.Structure):
    _fields_ = [("visible",ctypes.c_int),
                ("x",ctypes.c_int),
                ("y",ctypes.c_int),
                ("offx",ctypes.c_int),
                ("offy",ctypes.c_int),
                ("width",ctypes.c_int),
                ("height",ctypes.c_int),
                ("changed",ctypes.c_int),
                ("sizedata",ctypes.c_long),
                ("data", ctypes.c_void_p),
                ("internal", ctypes.c_void_p)]

  
class AUDIO_CONFIG(ctypes.Structure):
    _fields_ = [("sampleRate",ctypes.c_uint),
                ("numChannels",ctypes.c_uint),
                ("bufferFrames",ctypes.c_uint)]
    


