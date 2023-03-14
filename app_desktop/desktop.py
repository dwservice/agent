# -*- coding: utf-8 -*-

'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''

import agent
import threading
import json
import time
import struct
import os
import stat
import utils
import ctypes
import native
import subprocess
import ipc
from . import common

class Desktop():

    def __init__(self, agent_main):
        self._agent_main=agent_main
        self._process = None
        self._list = {}
        self._list_semaphore = threading.Condition()        
                    
    def destroy(self, bforce):
        lstcopy=None
        self._list_semaphore.acquire()
        try:
            if not bforce and len(self._list)>0:
                return False
            lstcopy=self._list.copy()
        finally:
            self._list_semaphore.release()
        for k in lstcopy.keys():
            dm = lstcopy[k]
            dm.destroy()
        if not self._process is None:
            self._process.destroy()
            self._process=None            
        return True
        
    def on_conn_close(self, idses):
        lstcopy=None
        self._list_semaphore.acquire()
        try:
            lstcopy=self._list.copy()
        finally:
            self._list_semaphore.release()
        
        for k in lstcopy.keys():
            dm = lstcopy[k]
            if dm.get_idses()==idses:
                try:
                    dm.destroy()
                except:
                    e = utils.get_exception()
                    self._agent_main.write_except(e,"AppDesktop:: on_conn_close error:")
            
    def has_permission(self,cinfo):
        return self._agent_main.has_app_permission(cinfo,"desktop");
    
    def _add_desktop_manager(self, cinfo, wsock):
        itm = None
        key = None
        self._list_semaphore.acquire()
        try:
            while True:
                key = agent.generate_key(10) 
                if key not in self._list:
                    if self._process is None:
                        self._process = DesktopProcessCapture(self._agent_main)
                        self._process.start()
                    itm = DesktopSession(self, cinfo, key, wsock)
                    self._list[key]=itm                    
                    break
        except Exception as e:
            if self._process is not None:
                if len(self._list)==0 and not self._process is None:
                    self._process.destroy()
                    self._process=None
            raise e
        finally:
            self._list_semaphore.release()        
        itm.start()
        return itm
    
    def _rem_desktop_manager(self, sid):
        self._list_semaphore.acquire()
        try:
            if sid in self._list:
                del self._list[sid]
                if len(self._list)==0 and not self._process is None:
                    self._process.destroy()
                    self._process=None
                
        finally:
            self._list_semaphore.release()
    
    def _get_desktop_manager(self, sid):
        self._list_semaphore.acquire()
        try:
            if sid in self._list:
                return self._list[sid]
        finally:
            self._list_semaphore.release()
        return None
    
    def _get_desktop_manager_check_permissions(self,cinfo,sid):
        dm=self._get_desktop_manager(sid)
        if dm is not None and cinfo.get_idsession()==dm.get_idses():
            return dm;
        else:
            raise Exception("Permission denied. Invalid id.")
        
    def req_copy_text(self,cinfo,params):
        sid = agent.get_prop(params,"id", "")
        dm=self._get_desktop_manager_check_permissions(cinfo,sid)
        sret={}
        sret["text"]=dm.copy_text();
        return json.dumps(sret)
    
    def req_paste_text(self,cinfo,params):
        sret=""
        sid = agent.get_prop(params,"id", "")
        s = agent.get_prop(params,"text", "")
        dm=self._get_desktop_manager_check_permissions(cinfo,sid)
        dm.paste_text(s);
        return sret
    
    def req_set_clipboard(self,cinfo,params):
        sret=""
        sid = agent.get_prop(params,"id", "")
        t = agent.get_prop(params,"type", "")
        d = agent.get_prop(params,"data", "")
        dm=self._get_desktop_manager_check_permissions(cinfo,sid)
        dm.set_clipboard(t, d);
        return sret
    
    def req_websocket(self, cinfo, wsock):
        self._add_desktop_manager(cinfo, wsock)        


class DesktopProcessCapture(threading.Thread):
    
    def __init__(self, agent_main):
        threading.Thread.__init__(self,  name="DesktopProcessCapture")
        self._struct_Q=struct.Struct("!Q")
        self._bdestroy=False
        self._agent_main=agent_main
        self._screen_module=None
        self._sound_module=None
        self._sound_status=None
        self._supported_frame=None
        self._semaphore = threading.Condition()
        self._strm=None
        self._process=None
        self._process_init=False
        self._process_status="stopped"
        self._process_last_error=None
        self._last_clipboard={"id":0,"type":0}
        self._last_clipboard_cnt=0
        self._last_clipboard_partial=None
        self._id=0        
        self._monitors=None 
        self._monitorsid=0       
        #self._cpdebug=None
        self._debug_forcesubprocess=False
        try:
            self._debug_forcesubprocess=self._agent_main.get_config("desktop.debug_forcesubprocess",False)
        except:
            None        
        
    def is_destroy(self):
        return self._bdestroy
    
    def destroy(self):
        self._bdestroy=True
        
    def get_supported_frame(self):
        self._semaphore.acquire()
        try:
            if self._supported_frame is None:
                self._supported_frame=[]
                v = self._screen_module.DWAScreenCaptureTJPEGEncoderVersion()
                if v>=2:
                    self._supported_frame.append(common.TYPE_FRAME_TJPEG_V2)
                if v>=1:
                    self._supported_frame.append(common.TYPE_FRAME_TJPEG_V1)
                v = self._screen_module.DWAScreenCapturePaletteEncoderVersion()
                if v>=1:
                    self._supported_frame.append(common.TYPE_FRAME_PALETTE_V1)
            return self._supported_frame
        finally:
            self._semaphore.release()
    
    def get_sound_status(self):
        self._semaphore.acquire()
        try:
            return self._sound_status
        finally:
            self._semaphore.release()    
    
    def get_monitors(self):
        self._semaphore.acquire()
        try:
            return self._monitors
        finally:
            self._semaphore.release()
    
    def get_last_error(self):
        return self._process_last_error;
    
    def get_last_clipboard(self):
        return self._last_clipboard
    
    def _init_screen_module(self):
        if self._screen_module is None:
            self._screen_module = self._agent_main.load_lib("screencapture")                         
        return self._screen_module

    def _term_screen_module(self):
        if self._screen_module is not None:
            self._agent_main.unload_lib("screencapture")
            self._screen_module=None;
    
    def _is_old_windows(self):
        return (utils.is_windows() and (native.get_instance().is_win_xp()==1 or native.get_instance().is_win_2003_server()==1))
            
    def _init_sound_module(self):
        if not self._is_old_windows():
            if self._sound_module is None:
                try:
                    soundenable = False
                    try:
                        soundenable = self._agent_main.get_config("desktop.sound_enable", True);
                    except:
                        None
                    if soundenable:
                        self._sound_module = self._agent_main.load_lib("soundcapture")
                except:
                    e = utils.get_exception()
                    self._agent_main.write_err("Sound library load error: " + utils.exception_to_string(e))
        return self._sound_module
    
    def _term_sound_module(self):
        if self._sound_module is not None:
            self._agent_main.unload_lib("soundcapture")
            self._sound_module=None;
    
    def get_id(self):
        return self._id
    
    def get_status(self):
        return self._process_status
    
    def _destroy_sound_nosync(self):
        if self._sound_status is not None:
            try:
                if "memmap" in self._sound_status:
                    memmap=self._sound_status["memmap"]
                    memmap.seek(0)
                    memmap.write(b"C")
                    memmap.close()
            except:
                None
            self._sound_status=None        
        
    def _destroy_monitors_nosync(self):
        if self._monitors is not None:
            try:
                if "memmap" in self._monitors:
                    memmap=self._monitors["memmap"]
                    memmap.seek(0)
                    memmap.write(b"C")
                    memmap.close()
            except:
                None
            self._monitors=None
            
    def _destroy_process(self):
        self._semaphore.acquire()
        try:
            self._destroy_sound_nosync()
            self._destroy_monitors_nosync()
        finally:
            self._semaphore.release()            
        try:
            if self._strm!=None:
                self._strm.close()                
        except:
            e = utils.get_exception()            
            self._agent_main.write_except(e)        
        self._strm=None
        if self._process is not None: 
            self._process.close()
        self._process_status="stopped"
    
    def _write_obj(self, obj):
        st = self.get_status()
        if st=="started":
            self._strm.write_obj(obj)
        else:
            raise Exception("Process not started.")
    
    def _must_destory_process(self):
        return ((self._process is not None and (not self._process.is_running() or self._process.is_change_console())) 
                or (self._strm is not None and self._strm.is_closed())) 
    
    def _strm_read_timeout(self, strm):
        if self._must_destory_process():
            return True
        return self.is_destroy()
    
    def run(self):
        #DOWNLOAD SCREEN LIB
        self._init_screen_module()
        #DOWNLOAD AUDIO LIB
        self._init_sound_module()        
        try:
            while not self.is_destroy():
                try:
                    if self._must_destory_process():
                        self._destroy_process()                    
                    if self._process_status=="stopped":
                        if self._process is None or not self._process.is_running():
                            prcargs=[]         
                            if hasattr(self._agent_main, "_app_desktop_capture_fallback_lib") and self._agent_main._app_desktop_capture_fallback_lib is not None:
                                prcargs.append("capture_fallback_lib=" + self._agent_main._app_desktop_capture_fallback_lib)
                            self._process=ipc.ProcessInActiveConsole("app_desktop.capture", "ProcessCapture", prcargs, forcesubprocess=self._debug_forcesubprocess)                            
                            self._strm=self._process.start()
                            self._strm.set_read_timeout_function(self._strm_read_timeout)
                            self._process_last_error=None
                            self._process_status="started"
                    if self._process_status=="started":
                        jo = self._strm.read_obj()
                        if jo==None:
                            raise Exception("Stream closed")
                        sreq = jo["request"]
                        if sreq==u"MONITORS_CHANGED":
                            bwrite=False
                            self._semaphore.acquire()
                            try:
                                self._destroy_monitors_nosync()
                                if "error_code" in jo:
                                    self._monitors={"list": jo["monitors"], "error_code": jo["error_code"]}                                    
                                else:
                                    self._monitors={"list": jo["monitors"]}
                                    self._monitorsid+=1
                                    self._monitors["id"]=self._monitorsid
                                    szmmap=1 
                                    
                                    #MONITORS DATA
                                    for i in range(len(self._monitors["list"])):
                                        mon = self._monitors["list"][i]
                                        mon["pos"]=szmmap
                                        l=1+8+ctypes.sizeof(common.RGB_IMAGE)+(mon["width"]*mon["height"]*3)                                
                                        szmmap+=l
                                    
                                    #CURSOR DATA
                                    l=ctypes.sizeof(common.CURSOR_IMAGE)+8+common.MAX_CURSOR_IMAGE_SIZE
                                    self._monitors["curpos"]=szmmap
                                    szmmap+=l
                                    
                                    #FPS
                                    self._monitors["fpspos"]=szmmap
                                    szmmap+=1                                                                
                                    memmap = ipc.MemMap(szmmap, fixperm=self._process.get_fixperm())
                                    memmap.seek(0)
                                    memmap.write(b"O")
                                    
                                    memmap.write(self._struct_Q.pack(0))                                                                
                                    self._monitors["memmap"]=memmap
                                    self._monitors["cond"]=ipc.Condition(fixperm=self._process.get_fixperm())
                                    bwrite=True
                            finally:
                                self._semaphore.release()
                            if bwrite:
                                self._write_obj({u"request":u"INIT_SCREEN_CAPTURE",u"monitors":self._monitors})                                
                        elif sreq==u"SOUND_STATUS":
                            bwrite=False
                            self._semaphore.acquire()
                            try:
                                self._destroy_sound_nosync()
                                self._sound_status=jo
                                if self._sound_status["status"]==u"OK":
                                    szmmap=1+8+8+jo["memmap_size"]
                                    self._sound_status["memmap_size"] = jo["memmap_size"]
                                    self._sound_status["memmap"] = ipc.MemMap(szmmap, fixperm=self._process.get_fixperm())
                                    self._sound_status["memmap"].seek(0)
                                    self._sound_status["memmap"].write(b"O")
                                    self._sound_status["memmap"].write(self._struct_Q.pack(0))                                    
                                    self._sound_status["cond"]=ipc.Condition(fixperm=self._process.get_fixperm())
                                    bwrite=True
                            finally:
                                self._semaphore.release()
                            if bwrite:
                                self._write_obj({u"request":u"INIT_SOUND_CAPTURE",u"cond":self._sound_status["cond"],u"memmap":self._sound_status["memmap"]})
                        elif sreq==u"CLIPBOARD_CHANGED":
                            if jo["tokenpos"]==0:
                                self._last_clipboard_partial={"type":jo["type"], "size":jo["size"], "tokens":[]}
                            self._last_clipboard_partial["tokens"].append(jo["tokendata"])
                            if jo["tokenlast"]:
                                self._last_clipboard_cnt+=1
                                self._last_clipboard_partial["id"]=self._last_clipboard_cnt
                                self._last_clipboard=self._last_clipboard_partial
                                self._last_clipboard_partial=None                            
                        elif sreq==u"RAISE_ERROR":
                            if "capture_fallback_lib" in jo:
                                self._agent_main._app_desktop_capture_fallback_lib=jo["capture_fallback_lib"]
                                if "message" in jo:
                                    self._agent_main.write_err("AppDesktop:: Process capture error: " + jo["message"]) 
                                self._agent_main.write_err("AppDesktop:: Process capture fallback library: " + self._agent_main._app_desktop_capture_fallback_lib)                               
                            else:
                                self._agent_main._app_desktop_capture_fallback_lib=None
                                self.destroy()
                            self._process_last_error=jo["message"]
                            self._destroy_process()
                        elif sreq==u"WRITE_LOG":
                            if jo["level"]=="INFO":
                                self._agent_main.write_info(jo["text"])
                            elif jo["level"]=="ERR":
                                self._agent_main.write_err(jo["text"])
                            else:
                                self._agent_main.write_debug(jo["text"])                        
                    else:
                        time.sleep(1)
                except:
                    e = utils.get_exception()
                    strmsg=utils.exception_to_string(e)                    
                    self._process_last_error=strmsg
                    if strmsg=="XWayland is not supported.":
                        self.destroy()                    
                    self._destroy_process()
                    if not self.is_destroy():
                        self._agent_main.write_err("AppDesktop:: Process capture error: " + self._process_last_error)
                    time.sleep(1)
        except:
            try:
                e = utils.get_exception()
                self._process_last_error=utils.exception_to_string(e)
            except:
                self._process_last_error="Process not started."
        self.destroy()
        self._destroy_process()
        if self._process is not None:
            self._process.join(2)
            self._process=None
        #UNLOAD DLL
        self._term_screen_module()
        self._term_sound_module()        
        
    def inputs(self, mon, sinps):
        bok = True
        if utils.is_windows() and "CTRLALTCANC" in sinps:
            if self._screen_module.DWAScreenCaptureSAS():
                bok = False            
        if bok: 
            self._write_obj({u"request":u"INPUTS",u"monitor":mon,u"inputs":sinps})
    
    def copy_text(self, mon):
        self._write_obj({u"request":u"COPY_TEXT",u"monitor":mon})
            
    def paste_text(self, mon, stxt):
        self._write_obj({u"request":u"PASTE_TEXT",u"monitor":mon, u"text": stxt})
            
    def set_clipboard(self, mon, stp, sdt):
        self._write_obj({u"request":u"SET_CLIPBOARD",u"monitor":mon, u"type": stp, u"data": sdt})


class DesktopSessionStatsCalculator():
    
    def __init__(self, chk, rsl):
        self._check_time=chk
        self._resolution_time=rsl
        self._counter=utils.Counter()
        self._ttime=0
        self._times=[]
        self._keys={}
    
    def reset(self):
        self._ttime=0
        self._times=[]
        appkeys=self._keys
        self._keys={}
        for k in appkeys:
            self.add_key(k)
    
    def add_key(self,k):
        itm={"increment":0,"value":0,"values":[]}
        self._keys[k]=itm
    
    def inc(self,k,v):
        self._keys[k]["increment"]+=v                
    
    def check(self,rsl=None):
        if rsl is not None:
            self._resolution_time=rsl
        if self._counter.is_elapsed(self._check_time):
            if len(self._keys)>0:
                elp=self._counter.get_value()
                self._ttime+=elp
                self._times.append(elp)
                for k in self._keys:
                    itm=self._keys[k]
                    itm["values"].append(itm["increment"])
                    itm["increment"]=0
                
                while self._ttime>self._resolution_time and len(self._times)>1:
                    elp=self._times.pop(0)
                    self._ttime-=elp
                    for k in self._keys:
                        itm=self._keys[k]
                        itm["values"].pop(0)
                
                oret={}
                for k in self._keys:
                    itm=self._keys[k]
                    v=sum(itm["values"])/sum(self._times)
                    itm["value"]=v
                    oret[k]=v                
                self._counter.reset()                
                return oret            
        return None
    
class DesktopSession(threading.Thread):
    
    def __init__(self, dskmain, cinfo, sid,  wsock):
        threading.Thread.__init__(self,  name="DesktopSession" + sid)
        self._struct_h=struct.Struct("!h")
        self._struct_hh=struct.Struct("!hh")
        self._struct_hb=struct.Struct("!hb")
        self._struct_Q=struct.Struct("!Q")
        self._struct_cpltkc=struct.Struct("!hhqi")
        self._dskmain=dskmain
        self._process=self._dskmain._process
        self._cinfo=cinfo
        prms = cinfo.get_permissions()
        if prms["fullAccess"]:
            self._allow_inputs=True
            self._allow_audio=True
        else:
            pret=self._dskmain._agent_main.get_app_permission(cinfo,"desktop")
            if pret["fullAccess"]:
                self._allow_inputs=True
                self._allow_audio=True
            else:
                if "allowScreenInput" in pret:
                    self._allow_inputs=pret["allowScreenInput"]
                else:
                    self._allow_inputs=False
                if "allowAudio" in pret:
                    self._allow_audio=pret["allowAudio"]
                else:
                    self._allow_audio=True
        
        self._prop=wsock.get_properties()
        self._idses=cinfo.get_idsession()
        self._id=sid
        self._bdestroy=False
        self._websocket=wsock
        self._keepalive_counter = None
        self._keepalive_send = False        
        self._websocket.accept(10,{"on_close": self._on_websocket_close,"on_data":self._on_websocket_data})
        self._websocket_send_lock = threading.RLock()
        self._cursor_visible = True
        self._supported_frame=None
        self._process_id=-1        
        self._monitor=-1
        self._monitor_count=-1
        self._monitor_encoder=-1
        self._frame_type=-1 # 0=DATA_PALETTE_COMPRESS_V1; 100=DATA_TJPEG_v1"; 101=DATA_TJPEG_v2"
        self._frame_type_to_send=False        
        self._send_stats_thread = None            
        self._frame_distance=0
        self._audio_type=-1
        self._audio_type_to_send=False
        self._audio_enable=True
        self._clipboard_auto=False
        self._slow_mode=False
        self._slow_mode_counter=utils.Counter()
        self._ping=0
        self._ping_check=False
        self._ping_counter=None
        self._stats_calc=DesktopSessionStatsCalculator(0.25,1.0)
        self._stats_calc.add_key("fps")
        self._stats_calc.add_key("capfps")
        self._stats_calc.add_key("bps")        
        self._stats_capture_fps=0
        self._stats_cur_frame_size=0
        self._stats_fps=0        
        self._stats_bps=0
        self._stats_frame_sent_time=0
        self._stats_frame_received_time=0
        self._stats_frame_pending=0
        self._semaphore_st=threading.Condition()        
        self._quality=9
        self._quality_request=-1
        self._quality_detect_value=9        
        self._quality_detect_fps_min=8
        self._quality_detect_down_count=0
        self._quality_detect_up_check=utils.Counter()        
        self._frame_intervall_fps=0
        self._frame_intervall_stats_calc=DesktopSessionStatsCalculator(0.2,1.0)
        self._frame_intervall_stats_calc.add_key("fps")
        self._frame_intervall_fps_min=1
        self._frame_intervall_fps_inc=4
        self._frame_intervall_event=threading.Event()
        self._frame_intervall_time_counter=utils.Counter()
        self._process_encoder=None
        self._process_encoder_stream=None
        self._process_encoder_alive=False
        self._process_encoder_event=None
        self._process_encoder_read_thread=None
        self._process_encoder_monitorsid=-1
        self._process_encoder_init=False
        self._init_session_to_send=True
        self._init_counter=utils.Counter()
        self._init_err_msg=None
        self._debug_forcesubprocess=False
        self._process_clipboard_thread=None
        self._last_clipboard_id=-1
        try:
            self._debug_forcesubprocess=self._dskmain._agent_main.get_config("desktop.debug_forcesubprocess",False)
        except:
            None
            
    def get_id(self):
        return self._id
    
    def get_idses(self):
        return self._idses
    
    def _on_websocket_data(self,websocket,tpdata,data):
        if not self._bdestroy:
            try:
                if self._keepalive_counter is not None:
                    self._keepalive_counter.reset()
                if tpdata == ord('s'):
                    prprequest = json.loads(data)
                else: #OLD TO REMOVE 19/12/2022
                    prprequest = json.loads(self._decode_data(data))
                if prprequest is not None and "frametime" in prprequest:
                    tm = float(prprequest["frametime"])
                    if "framepending" in prprequest:
                        pf = int(prprequest["framepending"])
                    else:
                        pf = 0
                    self._received_frame(tm,pf)
                if prprequest is not None and "inputs" in prprequest:
                    if not self._allow_inputs:
                        raise Exception("Permission denied (inputs).")                    
                    self._process.inputs(self._monitor,prprequest["inputs"])                                                                
                if prprequest is not None and "cursor" in prprequest:
                    if prprequest["cursor"]=="true":
                        self._cursor_visible=True
                    elif prprequest["cursor"]=="false":
                        self._cursor_visible=False
                if prprequest is not None and "monitor" in prprequest:                    
                    self._monitor = int(prprequest["monitor"])                        
                    if prprequest is not None and "acceptFrameType" in prprequest:
                        arft = prprequest["acceptFrameType"].split(";")
                        if self._supported_frame is not None:
                            for f in range (len(self._supported_frame)):
                                tf=self._supported_frame[f]                            
                                for i in range(len(arft)):
                                    if int(arft[i])==tf:
                                        self._frame_type=tf
                                        self._frame_type_to_send=True
                                        break
                                if self._frame_type_to_send==True:
                                    break
                    
                    if prprequest is not None and "acceptAudioType" in prprequest:
                        if not self._allow_audio:
                            raise Exception("Permission denied (audio).")
                        arft = prprequest["acceptAudioType"].split(";")
                        for i in range(len(arft)):
                            v = int(arft[i])
                            if v==0:
                                self._audio_type=v
                                self._audio_type_to_send=True                                                                
                                break
                    try:
                        if self._process_encoder_event is not None:
                            self._process_encoder_event.set()                            
                    except:
                        None
                            
                if prprequest is not None and "slow" in prprequest:
                    self._slow_mode=prprequest["slow"]=="true"
                if prprequest is not None and "quality" in prprequest:
                    self._quality_request=int(prprequest["quality"])
                if prprequest is not None and "keepalive" in prprequest:
                    if self._keepalive_counter is None:
                        self._keepalive_counter = utils.Counter()
                    self._keepalive_send = True
                if prprequest is not None and "audioEnable" in prprequest:
                    self._audio_enable=prprequest["audioEnable"]=="true"
                if prprequest is not None and "sendStats" in prprequest:
                    b=prprequest["sendStats"]=="true"
                    if b and self._send_stats_thread is None:
                        self._send_stats_thread=threading.Thread(target=self._send_stats_run, name="DesktopSessionSendStats" + utils.str_new(self._id))
                        self._send_stats_thread.start()                    
                    elif not b and self._send_stats_thread is not None:
                        self._send_stats_thread=None
                if prprequest is not None and "clipboardAuto" in prprequest:
                    self._clipboard_auto=prprequest["clipboardAuto"]=="true"
            except:
                ex = utils.get_exception()
                if self._process.get_status()=="started":
                    self._dskmain._agent_main.write_err("AppDesktop:: on_websoket_data error. ID: " + self._id + " - Error:" + utils.exception_to_string(ex))            
            
   
    def _on_websocket_close(self):
        self.destroy();
    
    def _decode_data(self,data):
        return data.decode("utf8")        
    
    def _send_bytes(self, bts):
        with self._websocket_send_lock:
            self._websocket.send_bytes(bts)
    
    def check_destroy(self):
        if self._init_counter is not None and self._init_counter.is_elapsed(15):
            if self._process.get_status()=="started":
                self._init_err_msg = "Session not started."
            else:
                appmsg = self._process.get_last_error()
                if appmsg is None:
                    appmsg="Process not started."
                self._init_err_msg = appmsg 
            raise Exception(self._init_err_msg)
        if self._keepalive_counter is not None and self._keepalive_counter.is_elapsed(10.0):
            self._init_err_msg = None
            self.destroy()
            return False
        else:
            if self._keepalive_send:
                self._keepalive_send=False
                bts=self._struct_h.pack(common.TOKEN_SESSION_ALIVE)
                self._send_bytes(bts)
        if self._process_encoder is not None and not self._process_encoder.is_running():
            return False
        return not self.is_destroy() and not self._process.is_destroy()

    def _strm_read_timeout(self, strm):
        return not self.check_destroy()
        
    def _received_frame(self,tm,fp): 
        self._semaphore_st.acquire()
        try:
            #CALCULATE PING
            if self._ping_check:
                self._ping=self._ping_counter.get_value()
                self._ping_counter.reset()
                self._ping_check=False
                return            
            if tm>=self._stats_frame_sent_time:
                self._stats_frame_sent_time=0
                self._stats_frame_received_time=0
            else:
                self._stats_frame_received_time=tm
            self._stats_frame_pending=fp            
            self._received_frame_nosync()
            self._semaphore_st.notify_all()
        finally:
            self._semaphore_st.release()
    
    def _received_frame_nosync(self):
        self._frame_distance-=1
        self._stats_calc.inc("fps", 1)
        self._frame_intervall_stats_calc.inc("fps", 1)                    
            
    def send_init_session(self):
        #SEND ID        
        sdataid=self._struct_h.pack(common.TOKEN_SESSION_ID)+utils.str_to_bytes(self._id)
        self._send_bytes(sdataid)
    
        #START KEEP ALIVE MANAGER
        self._send_bytes(self._struct_h.pack(common.TOKEN_SESSION_ALIVE))
        
        #TYPE=11 DATA=CNT-S1-S2-... -> SUPPORTED FRAME            
        self._supported_frame=self._process.get_supported_frame()
        spar = []
        spar.append(self._struct_hh.pack(common.TOKEN_SUPPORTED_FRAME,3))
        for sf in self._supported_frame:
            spar.append(self._struct_h.pack(sf))
        self._send_bytes(utils.bytes_join(spar))
        
    def _send_stats_run(self):
        while self._send_stats_thread is not None:
            try:
                jostats = {}
                jostats["fps"]=int(self._stats_fps) 
                jostats["fpscap"]=int(self._stats_capture_fps)
                jostats["bps"]=self._stats_bps
                if self._stats_fps>0:
                    jostats["tdiff"]=int(self._frame_distance*(1000.0/self._stats_fps))
                else:
                    jostats["tdiff"]=0
                jostats["fdiff"]=self._frame_distance
                jostats["ping"]=int(self._ping*1000)                        
                jostats["qa"]=self._quality
                apps=json.dumps(jostats)                    
                ba=bytearray(apps,"utf8")
                ba[0:0]=self._struct_h.pack(common.TOKEN_SESSION_STATS)
                self._send_bytes(ba)
            except:
                print(utils.get_exception()) 
                self._send_stats_thread=None
            time.sleep(1.0)
    
    def _strm_process_encoder_read_timeout(self, strm):
        return self.is_destroy()
    
    def _destroy_process_encoder(self, bforce=False):
        if self._process_encoder_init==True or bforce==True:
            if self._process_encoder_stream is not None:
                self._process_encoder_stream.close()
                self._process_encoder_stream=None        
            try:
                if self._process_encoder_event is not None:
                    self._process_encoder_event.set()
            except:
                None
            if self._process_encoder is not None:
                self._process_encoder.close()
                self._process_encoder.join(1)
                self._process_encoder=None
            self._process_encoder_init=False        
        self._process_encoder_monitorsid=-1        
    
    def _process_encoder_read(self,cpid):
        while True:
            sdata = None
            try: 
                sdata = self._process_encoder_stream.read_bytes()                
            except:
                None
            if sdata==None:
                break
            self._init_counter=None
            if len(sdata)>0:
                tp = self._struct_h.unpack(sdata[0:2])[0]                
                if tp==common.TOKEN_FRAME:
                    #SEND PING
                    if self._ping_counter is None or (self._ping_counter.is_elapsed(5) and self._stats_frame_sent_time==self._stats_frame_received_time):
                        if self._ping_counter is None:
                            self._ping_counter = utils.Counter()
                        else:
                            self._ping_counter.reset()
                        self._ping_check=True
                        self._send_bytes(self._struct_h.pack(common.TOKEN_FRAME_TIME)+utils.str_to_bytes(utils.str_new(time.time())))
                        self._send_bytes(self._struct_hb.pack(2,1))
                        
                    bsend=True
                    self._semaphore_st.acquire()
                    try:
                        self._stats_cur_frame_size+=int(len(sdata))
                        if utils.bytes_get(sdata,2)==1:
                            self._frame_distance+=1
                            self._stats_calc.inc("bps",self._stats_cur_frame_size)
                            if self._stats_cur_frame_size==3:                           
                                self._received_frame_nosync()
                                bsend=False
                            else:
                                tm=time.time() 
                                if tm>self._stats_frame_sent_time:
                                    self._stats_frame_sent_time=tm
                                else: 
                                    self._stats_frame_received_time=0
                            self._stats_cur_frame_size=0
                    finally:
                        self._semaphore_st.release()
                        
                    if bsend:
                        if utils.bytes_get(sdata,2)==1:                            
                            self._send_bytes(self._struct_h.pack(common.TOKEN_FRAME_TIME)+utils.str_to_bytes(utils.str_new(self._stats_frame_sent_time)))
                        self._send_bytes(sdata)                        
                        
                elif tp==common.TOKEN_CURSOR:
                    if self._cursor_visible==True:
                        self._send_bytes(sdata)
                elif tp==common.TOKEN_AUDIO_DATA: #TOKEN AUDIO
                    if self._audio_type_to_send==False:
                        self._send_bytes(sdata)
                elif tp==common.TOKEN_FRAME_NEXT:
                    #NEXT FRAME
                    fiw=0
                    self._semaphore_st.acquire()                
                    try:
                        arToken = self._struct_Q.unpack(sdata[2:2+self._struct_Q.size])
                        self._stats_calc.inc("capfps", arToken[0])
                        
                        if self._slow_mode:
                            self._slow_mode_counter.reset()
                            while self._slow_mode and not self._slow_mode_counter.is_elapsed(4):
                                self._semaphore_st.wait(0.2)
                            self._quality_detect_down_count=0
                            self._quality_detect_up_check.reset()                                                
                        else:
                            bdwait=False
                            while self._process_id==cpid and not (self._stats_frame_pending==0 and ((self._stats_frame_received_time==0) or self._stats_frame_sent_time-self._stats_frame_received_time<1+self._ping)):
                                bdwait=True
                                self._semaphore_st.wait(0.5)
                            if self._calc_stats():
                                self._qa_detect()
                            if self._quality_request!=-1:
                                self._quality=self._quality_request
                            else:
                                self._quality=self._quality_detect_value
                            if self._stats_frame_sent_time==0 and self._stats_frame_received_time==0:
                                fiw=0
                            else:
                                arstats=self._frame_intervall_stats_calc.check(1.0+self._ping)
                                if arstats is not None:
                                    self._frame_intervall_fps = int(arstats["fps"])
                                    #print(str(self._frame_intervall_fps))
                                if bdwait:
                                    ifps=self._frame_intervall_fps
                                    if ifps==0:
                                        ifps=self._frame_intervall_fps_min
                                else:
                                    ifps=self._frame_intervall_fps+self._frame_intervall_fps_inc
                                fiw=1.0/ifps                            
                    finally:
                        self._semaphore_st.release()
                    w = fiw-self._frame_intervall_time_counter.get_value()
                    if w>0:
                        self._frame_intervall_event.wait(w)
                    self._frame_intervall_time_counter.reset()
                    self._frame_intervall_event.set()                                        
                else:
                    self._send_bytes(sdata)

                    
    def _calc_stats(self):
        arstats=self._stats_calc.check(1.0+self._ping)
        if arstats is not None:
            self._stats_fps=int(arstats["fps"])
            self._stats_bps=int(arstats["bps"])
            self._stats_capture_fps=int(arstats["capfps"])
            return True
        return False
    
    def _qa_detect(self):
        if self._quality_request==-1:
            #DETECT DOWN
            if self._quality_detect_value>0 and self._stats_capture_fps>0 and self._stats_capture_fps>self._stats_fps and self._stats_fps<=self._quality_detect_fps_min:
                self._quality_detect_down_count+=1
                if self._quality_detect_down_count>=8: #2 SEC
                    self._quality_detect_value-=1
                    #print("DOWN quality_detect_value: " + str(self._quality_detect_value) + " capture_fps:" + str(self._stats_capture_fps) + " stats_fps:" + str(self._stats_fps))
                    self._quality_detect_down_count=0
                    self._quality_detect_up_check.reset()
            else:
                self._quality_detect_down_count=0
            #DETECT UP
            if self._quality_detect_value<9:
                if self._stats_fps>=self._quality_detect_fps_min:
                    if self._quality_detect_up_check.is_elapsed(4):
                        self._quality_detect_value+=1
                        self._quality_detect_up_check.reset()
                        #print("UP quality_detect_value: " + str(self._quality_detect_value) + " capture_fps:" + str(self._stats_capture_fps) + " stats_fps:" + str(self._stats_fps))
                else:
                    self._quality_detect_up_check.reset()
            else:
                self._quality_detect_up_check.reset()        
    
    def _process_clipboard_handler(self):
        while self._last_clipboard_id>=0:
            last_clipboard=self._process.get_last_clipboard()
            if last_clipboard["id"]!=self._last_clipboard_id:
                self._last_clipboard_id=last_clipboard["id"]
                
                tks=last_clipboard["tokens"]
                for i in range(len(tks)):
                    self._send_bytes(self._struct_cpltkc.pack(common.TOKEN_CLIPBOARD,last_clipboard["type"],last_clipboard["size"],i) + tks[i])
            else:
                time.sleep(0.25)
    
    def _destroy_clipboard_handler(self):
        if self._process_clipboard_thread!=None:
            self._last_clipboard_id=-1
            self._process_clipboard_thread.join(2)
            self._process_clipboard_thread=None             
      
    def run(self):
        baudioenable=None
        bframelocked=False
        try:
            self._cinfo.inc_activities_value("screenCapture")
        except:
            None        
        try:
            while self.check_destroy():
                
                if self._process.get_status()=="started":                    
                    if self._process.get_id()!=self._process_id:
                        self._destroy_process_encoder()
                        self._process_id=self._process.get_id()
                else:
                    self._destroy_process_encoder()
                
                if self._process.get_status()=="started":
                    
                    if self._process_encoder==None:
                        self._process_encoder = ipc.Process("app_desktop.encoder", "ProcessEncoder", forcesubprocess=self._debug_forcesubprocess)
                        self._process_encoder_stream = self._process_encoder.start()
                        self._process_encoder_stream.set_read_timeout_function(self._strm_process_encoder_read_timeout)
                        self._process_encoder_read_thread=threading.Thread(target=self._process_encoder_read, args=(self._process_id,), name="DesktopSessionProcessRead" + utils.str_new(self._id))
                        self._process_encoder_read_thread.start()
                    
                    if self._clipboard_auto==True:
                        if self._process_clipboard_thread==None:
                            self._last_clipboard_id=self._process.get_last_clipboard()["id"]
                            self._process_clipboard_thread=threading.Thread(target=self._process_clipboard_handler, name="DesktopSessionClipboardHandler" + utils.str_new(self._id))
                            self._process_clipboard_thread.start() 
                    else:
                        self._destroy_clipboard_handler()
                    
                    monitors=self._process.get_monitors()
                    if monitors is None:
                        time.sleep(0.25)
                    else:
                        if self._init_session_to_send==True:
                            self._init_session_to_send=False
                            self.send_init_session()
                        if self._monitor_count!=len(monitors["list"]):
                            #TYPE=10 DATA=SZ -> MONITOR COUNT
                            self._monitor_count=len(monitors["list"])
                            if self._monitor_count==0 and "error_code" in monitors:
                                if bframelocked==False:
                                    bframelocked=True
                                    self._send_bytes(self._struct_h.pack(common.TOKEN_FRAME_LOCKED))
                            else:
                                if bframelocked==True:
                                    bframelocked=False
                                    self._send_bytes(self._struct_h.pack(common.TOKEN_FRAME_UNLOCKED))
                                self._send_bytes(self._struct_hh.pack(common.TOKEN_MONITOR,self._monitor_count))
                        
                        if self._frame_type!=-1 and self._monitor!=-1 and self._monitor_count>0:
                            try:
                                if self._process_encoder_init==False:
                                    self._process_encoder_event = ipc.Event()
                                    self._process_encoder_stream.write_obj({u"request":u"INIT",u"event":self._process_encoder_event,u"image_type":self._frame_type})
                                    self._process_encoder_init=True
                                    self._frame_intervall_event.set()
                                                                                
                                if self._process_encoder_monitorsid!=monitors["id"]:
                                    self._process_encoder_stream.write_obj({u"request":u"SET_MONITORS",u"monitors":monitors})
                                    self._process_encoder_monitorsid=monitors["id"]
                                    
                                soundstatus=self._process.get_sound_status()
                                if soundstatus is not None:
                                    if self._audio_type_to_send==True:
                                        self._audio_type_to_send=False
                                        if soundstatus["status"]==u"OK":
                                            self._send_bytes(self._struct_hh.pack(common.TOKEN_AUDIO_TYPE,0)) #0=opus
                                            self._process_encoder_stream.write_obj({u"request":u"START_SOUND", u"status":soundstatus})
                                            baudioenable=True
                                        else:
                                            err_msg="Unknown error."
                                            if "message" in soundstatus:
                                                err_msg=soundstatus["message"]
                                            ba=bytearray(err_msg,"utf8")
                                            ba[0:0]=self._struct_h.pack(common.TOKEN_AUDIO_ERROR)                                            
                                            self._send_bytes(ba)
                                    if baudioenable is not None and self._audio_enable!=baudioenable:
                                        baudioenable=not baudioenable
                                        self._process_encoder_stream.write_obj({u"request":u"SET_SOUND_ENABLE", u"value":baudioenable})                                    
                                
                                
                                if self._frame_type_to_send==True:
                                    self._frame_type_to_send=False
                                    self._send_bytes(self._struct_hh.pack(common.TOKEN_FRAME_TYPE,self._frame_type))                                                    
                                
                                if self._frame_type!=-1 and self._monitor!=-1:
                                    self._frame_intervall_event.wait(0.25)
                                    if self._frame_intervall_event.is_set():
                                        self._frame_intervall_event.clear()                                        
                                        self._process_encoder_stream.write_obj({u"request":u"ENCODE", u"monitor":self._monitor, u"quality":self._quality,u"send_buffer_size":self._websocket.get_send_buffer_size()})
                                else:
                                    time.sleep(0.25)
                            except Exception:
                                self._destroy_process_encoder()
                        else:        
                            time.sleep(0.25)
                else:
                    time.sleep(0.25)
                
        except:
            e = utils.get_exception()
            if not self.is_destroy():
                if self._dskmain._agent_main._agent_debug_mode:
                    self._dskmain._agent_main.write_err(utils.get_stacktrace_string())                
                appmsg = self._process.get_last_error()
                if appmsg is None:
                    appmsg = utils.exception_to_string(e)
                self._dskmain._agent_main.write_err("AppDesktop:: session id: " + self._id + " error: "  + appmsg)                
        
        try:
            self._cinfo.dec_activities_value("screenCapture")
        except:
            None
        
        try:
            self._destroy_clipboard_handler()
        except:
            self._dskmain._agent_main.write_err("AppDesktop:: session id: " + self._id + " error: destroy_clipboard_handler")        
        
        bsndmsg = not (self._process_encoder is not None and not self._process_encoder.is_running())
        self._destroy_process_encoder(True)
        if not self.is_destroy():
            if bsndmsg:            
                if self._init_err_msg is None:
                    appmsg = self._process.get_last_error()
                    if appmsg is None:
                        appmsg="Process not started."
                    self._init_err_msg=appmsg
                try:
                    self._send_bytes(self._struct_h.pack(common.TOKEN_SESSION_ERROR) + self._init_err_msg.encode("ascii", errors='replace'))
                except:
                    None
            self.destroy()
        if self._websocket is not None:
            self._websocket.close()
            self._websocket=None
        
        self._dskmain._rem_desktop_manager(self._id)
        self._id=None        
        
    def copy_text(self):
        if not self._allow_inputs:
            raise Exception("Permission denied (inputs).")
        if self._clipboard_auto:
            raise Exception("Auto clipboard enabled.")
            
        lid = self._process.get_last_clipboard()["id"];
        self._process.copy_text(self._monitor)
        cnt = utils.Counter()
        while True:
            apps = self._process.get_last_clipboard()
            if lid!=apps["id"]:
                bts = utils.bytes_join(apps["tokens"])
                return utils.bytes_to_str(bts,"utf8")
            time.sleep(0.5)
            if self.is_destroy() or cnt.is_elapsed(5):
                return ""
    
    def paste_text(self,s):
        if not self._allow_inputs:
            raise Exception("Permission denied (inputs).")
        if s is not None:
            self._process.paste_text(self._monitor,s)
            
    def set_clipboard(self,t,d):
        if not self._allow_inputs:
            raise Exception("Permission denied (inputs).")
        if t is not None and d is not None:
            self._process.set_clipboard(self._monitor,t,d)
    
    def destroy(self):
        self._send_stats_thread=None
        self._bdestroy=True             
    
    def is_destroy(self):
        return self._bdestroy    
 
     
