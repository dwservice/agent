# -*- coding: utf-8 -*-

'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''

import ctypes
import threading
import utils
import ipc
import common
import native
import struct

class ProcessEncoderPalette():
    
    def __init__(self, scrmdl, ver):
        self._scrmdl=scrmdl
        self._ver=ver
        self._qa=-1
        self._redsize=0
        self._greensize=0
        self._bluesize=0
    
    def initialize(self,encses):
        self._scrmdl.DWAScreenCapturePaletteEncoderInit(self._ver,ctypes.byref(encses))        
    
    def terminate(self,encses):
        self._scrmdl.DWAScreenCapturePaletteEncoderTerm(self._ver,encses)        
    
    def encode(self,encses,joreq,rgbimage,cb_screen_encode_result):
        self._load_qa_conf(joreq["quality"])
        self._scrmdl.DWAScreenCapturePaletteEncode(self._ver,encses,self._redsize,self._greensize,self._bluesize,ctypes.byref(rgbimage),cb_screen_encode_result)

    def _load_qa_conf(self, qa):
        if self._qa==qa:
            return
        self._qa=qa
        if qa==0:
            self._redsize=4
            self._greensize=4
            self._bluesize=4
        elif qa==1:
            self._redsize=8
            self._greensize=4
            self._bluesize=4
        elif qa==2:
            self._redsize=8
            self._greensize=8
            self._bluesize=4
        elif qa==3:
            self._redsize=8
            self._greensize=8
            self._bluesize=8
        elif qa==4:
            self._redsize=16
            self._greensize=8
            self._bluesize=8
        elif qa==5:
            self._redsize=16
            self._greensize=16
            self._bluesize=8
        elif qa==6:
            self._redsize=16
            self._greensize=16
            self._bluesize=16
        elif qa==7:
            self._redsize=32
            self._greensize=16
            self._bluesize=16
        elif qa==8:
            self._redsize=32
            self._greensize=32
            self._bluesize=16
        elif qa==9:
            self._redsize=32
            self._greensize=32
            self._bluesize=32
        else:
            self._redsize=32
            self._greensize=32
            self._bluesize=32


class ProcessEncoderTJPEG():
    
    def __init__(self, scrmdl, ver):
        self._scrmdl=scrmdl
        self._ver=ver
        self._qa=-1
        self._qaenc=-1
    
    def initialize(self,encses):
        self._scrmdl.DWAScreenCaptureTJPEGEncoderInit(self._ver,ctypes.byref(encses))        
    
    def terminate(self,encses):
        self._scrmdl.DWAScreenCaptureTJPEGEncoderTerm(self._ver,encses)        
    
    def encode(self,encses,joreq,rgbimage,cb_screen_encode_result):
        self._load_qa_conf(joreq["quality"])
        self._scrmdl.DWAScreenCaptureTJPEGEncode(self._ver,encses,self._qaenc,joreq["send_buffer_size"],ctypes.byref(rgbimage),cb_screen_encode_result)

    def _load_qa_conf(self, qa):
        if self._qa==qa:
            return
        self._qa=qa
        if qa==0:
            self._qaenc=30
        elif qa==1:
            self._qaenc=35
        elif qa==2:
            self._qaenc=40
        elif qa==3:
            self._qaenc=45
        elif qa==4:
            self._qaenc=50
        elif qa==5:
            self._qaenc=60
        elif qa==6:
            self._qaenc=70
        elif qa==7:
            self._qaenc=80
        elif qa==8:
            self._qaenc=85
        elif qa==9:
            self._qaenc=90
        else:
            self._qaenc=90 

class ProcessEncoder(ipc.ChildProcessThread):    
    
    def _on_init(self):
        self._struct_h=struct.Struct("!h")
        self._struct_hh=struct.Struct("!hh")
        self._struct_hhh=struct.Struct("!hhh")
        self._struct_hB=struct.Struct("!hB")
        self._struct_Q=struct.Struct("!Q")
        self._listlibscr = None
        self._scrmdl = None
        self._listlibsnd = None
        self._sndmdl = None
        self._encinst= None
        self._monitors=[]
        self._skipevent=None                
        self._curmon=-2
        self._cond=None
        self._memmap=None
        self._multiview=None
        self._curpos=-1
        self._curid=0
        self._curx=-1
        self._cury=-1
        self._curvis=False
        self._curcounter=utils.Counter()
        self._sound_enable=True
        self._sound_cond=None
        self._sound_memmap=None
        self._sound_aconf=None
        self._sound_encses=None
        self._sound_memmap_limit=-1
        self._sound_cid=0
        self._sound_thread=None
        self._write_lock = threading.RLock()
        self._fps_cnt=utils.Counter()
    
    def _init(self,joreq):
        self._skipevent=joreq["event"]
        imgtp=joreq["image_type"]
        if imgtp==common.TYPE_FRAME_TJPEG_V2: 
            self._encinst = ProcessEncoderTJPEG(self._scrmdl,2)
        elif imgtp==common.TYPE_FRAME_TJPEG_V1:
            self._encinst = ProcessEncoderTJPEG(self._scrmdl,1)
        elif imgtp==common.TYPE_FRAME_PALETTE_V1:
            self._encinst = ProcessEncoderPalette(self._scrmdl,1)   
    
    def _set_monitors(self,joreq):        
        self._close_monitors()
        self._monitors=joreq["monitors"]["list"]
        self._memmap=joreq["monitors"]["memmap"]
        self._cond=joreq["monitors"]["cond"]
        self._curpos=joreq["monitors"]["curpos"]
        for mon in self._monitors:
            mon["curcapid"]=0
            mon["fpscurcapid"]=0
            mon["curcapst"]="K"
            mon["encses"]=None                        
        self._curmon=-2
        self._multiview=None
        self._curid=0
        self._curx=-1
        self._cury=-1
        self._curvis=False
    
    def _start_sound(self,joreq):
        jostatus=joreq["status"]
        self._sound_cond=jostatus["cond"]
        self._sound_memmap=jostatus["memmap"]
        self._sound_memmap_size=jostatus["memmap_size"]
        self._sound_aconf = common.AUDIO_CONFIG()
        self._sound_aconf.numChannels = jostatus["num_channels"]
        self._sound_aconf.sampleRate = jostatus["sample_rate"]
        self._sound_aconf.bufferFrames = jostatus["buffer_frames"]
        self._listlibsnd = native.load_libraries_with_deps("soundcapture")
        self._sndmdl = self._listlibsnd[0]
        self._sound_encses = ctypes.c_void_p()
        iret = self._sndmdl.DWASoundCaptureOPUSEncoderInit(ctypes.byref(self._sound_aconf),ctypes.byref(self._sound_encses))
        self._sound_memmap_limit=-1
        self._sound_cid=0
        self._sound_thread=threading.Thread(target=self.encode_sound, name="ProcessEncoderSound")
        self._sound_thread.start()

    def encode_sound(self):
        common.func_sound_encode_result=self._sound_encode_result
        try:    
            while not self.is_destroy():
                data=None
                self._sound_cond.acquire()
                try:
                    self._sound_memmap.seek(0)
                    st = self._sound_memmap.read(1)
                    if st=="O":
                        cid=self._struct_Q.unpack(self._sound_memmap.read(8))[0]
                        if self._sound_enable==True and self._sound_cid!=cid:
                            self._sound_cid=cid
                            plim=self._struct_Q.unpack(self._sound_memmap.read(8))[0]
                            if self._sound_memmap_limit==-1:
                                self._sound_memmap_limit=plim
                            elif self._sound_memmap_limit<plim:
                                self._sound_memmap.seek(17+self._sound_memmap_limit)
                                data=self._sound_memmap.read(plim-self._sound_memmap_limit)
                                self._sound_memmap_limit=plim
                            else:
                                szrem = self._sound_memmap_size-self._sound_memmap_limit
                                if szrem>0:
                                    self._sound_memmap.seek(17+self._sound_memmap_limit)
                                    data1 = self._sound_memmap.read(szrem)
                                    self._sound_memmap.seek(17)
                                    data2 = self._sound_memmap.read(plim)
                                    data = "".join([data1,data2])
                                else:
                                    self._sound_memmap.seek(17)
                                    data = self._sound_memmap.read(plim)
                                self._sound_memmap_limit=plim
                        else:
                            self._sound_cond.wait(0.5)                                                                      
                    if st=="C":
                        break                        
                finally:
                    self._sound_cond.release()
                if data is not None:
                    iret = self._sndmdl.DWASoundCaptureOPUSEncode(self._sound_encses, data, len(data), common.cb_sound_encode_result)
        except:
            ex = utils.get_exception()
            print("ProcessEncoderSound:" + str(ex))
        finally:
            self._close_sound()
         
         
    def _sound_encode_result(self, sz, pdata):
        try:
            if self.is_destroy():
                return
            with self._write_lock:
                self._stream.write_bytes(pdata[0:sz])            
        except:
            ex = utils.get_exception()
            if not self.is_destroy():
                self.destroy()
                print("_sound_encode_result: err" + str(ex))            
    
    def _close_sound(self):        
        if self._sound_memmap is not None:
            self._sound_memmap.close()
            self._sound_memmap=None
        self._sound_cond=None
        if self._sound_encses is not None:
            self._sndmdl.DWASoundCaptureOPUSEncoderTerm(self._sound_encses)
            self._sound_encses=None
    
    def _multimon_changed(self):
        w=0
        h=0
        self._multiview={"gx":0,"gy":0}
        for mon in self._monitors:
            if mon["x"]<self._multiview["gx"]:
                self._multiview["gx"]=mon["x"]
            if mon["y"]<self._multiview["gy"]:
                self._multiview["gy"]=mon["y"]
        self._multiview["gx"]=abs(self._multiview["gx"])
        self._multiview["gy"]=abs(self._multiview["gy"])
        self._multiview["st"]="K"
        for mon in self._monitors:
            if mon["encses"] is not None:
                self._encinst.terminate(mon["encses"])       
            mon["encses"]=ctypes.c_void_p()
            self._encinst.initialize(mon["encses"])
            mon["curcapid"]=0
            mon["fpscurcapid"]=0
            mon["curcapst"]="K"
            if self._multiview["gx"]+mon["x"]+mon["width"]>w:
                w=self._multiview["gx"]+mon["x"]+mon["width"]
            if self._multiview["gy"]+mon["y"]+mon["height"]>h:
                h=self._multiview["gy"]+mon["y"]+mon["height"]
        self._stream.write_bytes(self._struct_hhh.pack(common.TOKEN_RESOLUTION,w,h))
        
    def _singlemon_changed(self):
        self._multiview=None       
        mon = self._monitors[self._curmon]
        if mon["encses"] is not None:
            self._encinst.terminate(mon["encses"])       
        mon["encses"]=ctypes.c_void_p()
        self._encinst.initialize(mon["encses"])
        mon["curcapid"]=0
        mon["fpscurcapid"]=0
        mon["curcapst"]="K"
        self._stream.write_bytes(self._struct_hhh.pack(common.TOKEN_RESOLUTION,mon["width"],mon["height"]))
        
        
    def _multimon_encode(self,joreq):
        bexit=False
        bchange=False
        rgbimages=None
        self._cond.acquire()
        try:
            while not self.is_destroy() and not self._skipevent.is_set():
                multiviewst="K"
                rgbimages=[]
                for mon in self._monitors:
                    rgbimage=None
                    self._memmap.seek(0)
                    st = self._memmap.read(1)
                    if st=="O":
                        self._memmap.seek(mon["pos"])
                        capst=self._memmap.read(1)
                        if capst=="K":
                            capid=self._struct_Q.unpack(self._memmap.read(8))[0]
                            if mon["curcapid"]!=capid:
                                mon["curcapid"]=capid
                                rgbimage=common.RGB_IMAGE()
                                btsi=self._memmap.read(ctypes.sizeof(rgbimage))
                                utils.convert_bytes_to_structure(rgbimage,btsi)
                                btsd = self._memmap.read(rgbimage.sizedata)
                                rgbimage.data=ctypes.cast(ctypes.c_char_p(btsd),ctypes.c_void_p)
                        elif capst=="P":
                            multiviewst=capst
                            break
                    elif st=="C":
                        bexit=True
                        break   
                    rgbimages.append(rgbimage)
                    if rgbimage is not None:                                                            
                        bchange=True            
                self._cursor_encode()
                if self._multiview["st"]!=multiviewst:
                    if multiviewst=="K":
                        self._stream.write_bytes(self._struct_h.pack(common.TOKEN_FRAME_UNLOCKED))
                    elif multiviewst=="P":
                        self._stream.write_bytes(self._struct_h.pack(common.TOKEN_FRAME_LOCKED))
                    self._multiview["st"]=multiviewst
                if bchange==True or bexit==True:                    
                    self._cond.notify_all()
                    break
                else:                    
                    self._cond.wait(0.25)                    
        finally:
            self._cond.release()
        
        if not bexit:
            for i in range(len(self._monitors)):
                mon = self._monitors[i]
                rgbimage=None
                if i<len(rgbimages):
                    rgbimage=rgbimages[i]                
                if rgbimage is not None:
                    self._multiview["ox"]=self._multiview["gx"]+mon["x"]
                    self._multiview["oy"]=self._multiview["gy"]+mon["y"]
                    self._multiview["type2"]=True
                    self._encinst.encode(mon["encses"],joreq,rgbimage,common.cb_screen_encode_result)
            
            
    def _singlemon_encode(self,joreq):
        mon = self._monitors[self._curmon]
        rgbimage=None
        self._cond.acquire()        
        try:
            while not self.is_destroy() and not self._skipevent.is_set():
                self._memmap.seek(0)
                st = self._memmap.read(1)
                if st=="O":
                    self._memmap.seek(mon["pos"])
                    capst=self._memmap.read(1)
                    if capst=="K":
                        if mon["curcapst"]=="P":
                            self._stream.write_bytes(self._struct_h.pack(common.TOKEN_FRAME_UNLOCKED))
                        mon["curcapst"]=capst
                        capid=self._struct_Q.unpack(self._memmap.read(8))[0]
                        if mon["curcapid"]!=capid:
                            mon["curcapid"]=capid
                            rgbimage=common.RGB_IMAGE()
                            btsi=self._memmap.read(ctypes.sizeof(rgbimage))
                            utils.convert_bytes_to_structure(rgbimage,btsi)
                            btsd = self._memmap.read(rgbimage.sizedata)
                            rgbimage.data=ctypes.cast(ctypes.c_char_p(btsd),ctypes.c_void_p)
                            self._cursor_encode()
                            self._cond.notify_all()
                            break
                        else:                            
                            self._cursor_encode()
                    elif capst=="P":
                        if mon["curcapst"]!="P":
                            self._stream.write_bytes(self._struct_h.pack(common.TOKEN_FRAME_LOCKED))
                        mon["curcapst"]=capst
                elif st=="C":
                    break
                self._cond.wait(0.25)                    
        finally:
            self._cond.release()
        if rgbimage is not None:                            
            self._encinst.encode(mon["encses"],joreq,rgbimage,common.cb_screen_encode_result)
            #print("ltot:" + str(ltot))
        
        
    def _cursor_encode(self):
        if self._curcounter.is_elapsed(0.02):
            bencode=False
            curimage=common.CURSOR_IMAGE()
            self._memmap.seek(self._curpos)
            btsi=self._memmap.read(ctypes.sizeof(curimage))
            utils.convert_bytes_to_structure(curimage,btsi)            
            if self._curx!=curimage.x or self._cury!=curimage.y or self._curvis!=curimage.visible:
                self._curx=curimage.x
                self._cury=curimage.y
                self._curvis=curimage.visible
                bencode=True
            
            curid=self._struct_Q.unpack(self._memmap.read(8))[0]
            if self._curid!=curid:
                self._curid=curid
                btsd = self._memmap.read(curimage.sizedata)
                curimage.data=ctypes.cast(ctypes.c_char_p(btsd),ctypes.c_void_p)
                bencode=True
            else:
                curimage.sizedata=0
                
            if bencode==True:
                self._scrmdl.DWAScreenCaptureCursorEncode(1,ctypes.byref(curimage),common.cb_screen_encode_result)
                #print("cursor encode: " + str(self._curx) + " : " + str(self._cury) + " sz=" + str(curimage.sizedata)) 
            
            self._curcounter.reset()
    
    def _calc_fps(self):
        if self._fps_cnt.is_elapsed(1):
            cptfps=0
            elp = 1.0/self._fps_cnt.get_value()
            for i in range(len(self._monitors)):
                mon = self._monitors[i]
                if i==0:
                    cptfps=int((mon["curcapid"]-mon["fpscurcapid"])*elp)
                else:
                    c=int((mon["curcapid"]-mon["fpscurcapid"])*elp)
                    if c>cptfps:
                        cptfps=c
                mon["fpscurcapid"]=mon["curcapid"]
                
            if cptfps<0:
                cptfps=0 
            elif cptfps>255:
                cptfps=255
            self._fps_cnt.reset()
            self._stream.write_bytes(self._struct_hB.pack(common.TOKEN_FPS,cptfps))
    
    def _strm_read_timeout(self,strm):
        return self.is_destroy()
    
    def run(self):
        common.func_screen_encode_result=self._screen_encode_result
        self._listlibscr = native.load_libraries_with_deps("screencapture")
        self._scrmdl = self._listlibscr[0]
        self._stream.set_read_timeout_function(self._strm_read_timeout)        
        try:
            while not self.is_destroy():
                joreq = None
                try:
                    joreq = self._stream.read_obj()
                except:
                    None
                if joreq is None:
                    break
                sreq = joreq["request"]
                if sreq==u"INIT":
                    self._init(joreq)
                elif sreq==u"SET_MONITORS":
                    self._set_monitors(joreq)
                elif sreq==u"START_SOUND":
                    self._start_sound(joreq)
                elif sreq==u"SET_SOUND_ENABLE":
                    self._sound_enable=joreq["value"]
                elif sreq==u"ENCODE":
                    m = joreq["monitor"]-1
                    if self._curmon!=m:
                        self._curmon=m
                        if m==-1 and len(self._monitors)>1: #MULTIMONITOR
                            self._multimon_changed()
                        elif m>=0 and m<=len(self._monitors)-1:  #SINGLEMONITOR
                            self._singlemon_changed()
                    if m==-1 and len(self._monitors)>1: #MULTIMONITOR
                        self._multimon_encode(joreq)
                    elif m>=0 and m<=len(self._monitors)-1: #SINGLEMONITOR
                        self._singlemon_encode(joreq)
                    self._calc_fps()
                    if not self.is_destroy():
                        self._skipevent.clear()
                        self._stream.write_bytes("")                            
        except:
            ex = utils.get_exception()
            if not self.is_destroy():
                print("ProcessEncoder:" + str(ex))
        finally:
            self._close_monitors()
            native.unload_libraries(self._listlibscr)            
            if self._sound_thread is not None:
                self._sound_thread.join(2)
                if self._sound_thread.is_alive():                
                    self._close_sound()
            else:
                self._close_sound()
            if self._listlibsnd is not None:
                native.unload_libraries(self._listlibsnd)            
            self._stream.close()
        
    
    def _close_monitors(self):
        if self._memmap is not None:
            self._memmap.close()
            self._memmap=None
        self._cond=None
        if self._monitors is not None:
            for mon in self._monitors:
                if mon["encses"] is not None:
                    self._encinst.terminate(mon["encses"])
                    mon["encses"]=None                                                
            self._monitors=None

    def _screen_encode_result(self, sz, pdata):
        try:
            if self.is_destroy():
                return
            if self._multiview is not None:
                sdata = bytearray(pdata[0:sz])
                tp = self._struct_h.unpack(sdata[0:2])[0]
                if tp==common.TOKEN_FRAME:
                    if self._multiview["type2"]==True: 
                        self._multiview["type2"]=False
                        if sz>3:
                            arxy = self._struct_hh.unpack(sdata[3:7])
                            nx=arxy[0]+self._multiview["ox"]
                            ny=arxy[1]+self._multiview["oy"]
                            sdata[3:7]=bytearray(self._struct_hh.pack(nx,ny))
                    if sdata[2]!=0:
                        self._multiview["type2"]=True
                with self._write_lock:
                    self._stream.write_bytes(sdata)
            else:
                with self._write_lock:
                    self._stream.write_bytes(pdata[0:sz])            
        except:
            ex = utils.get_exception()
            if not self.is_destroy():
                self.destroy()
                print("_screen_encode_result: err" + str(ex))
                
                