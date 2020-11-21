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
import traceback
import struct
import sys
import os
import stat
import subprocess
import sharedmem
import logging
import base64
import utils
import ctypes
import native

VK_SHIFT          = 0x10
VK_CONTROL        = 0x11
VK_ALT            = 0x12

_libmap={}
_struct_h=struct.Struct("!h")
_struct_i=struct.Struct("!i")
_struct_I=struct.Struct("!I")

#GESTIONE CALLBACK DEBUG PRINT
#cb_debug_print_f={"func":None}
DBGFUNC = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_char_p)
DIFFUNC = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_char))
        
@DBGFUNC  
def cb_debug_print(str):
    cp = _libmap["captureprocess"]
    if cp is not None:
        cp.cb_debug_print(str)

@DIFFUNC
def cb_difference(sz, pdata):
    cp = _libmap["captureprocess"]
    if cp is not None:
        threading.current_thread().cb_difference(sz, pdata)


class Desktop():

    def __init__(self, agent_main):
        self._agent_main=agent_main
        self._capture_process = None
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
        #Attende chiusura
        cnt=0
        while cnt<10:
            time.sleep(1)
            cnt+=1
            bexit=True
            for k in lstcopy.keys():
                dm = lstcopy[k]
                if dm.is_alive():
                    bexit=False
                    break
            if bexit:
                break
        return True
            
        if not self._capture_process is None:
            self._capture_process.destroy()
            self._capture_process=None
        
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
                except Exception as e:
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
                    if self._capture_process is None:
                        self._capture_process = CaptureProcessClient(self._agent_main)
                        self._capture_process.start()                        
                    itm = Session(self, cinfo, key, wsock)
                    self._list[key]=itm
                    break
        finally:
            self._list_semaphore.release()
        itm.start()
        return itm
    
    def _rem_desktop_manager(self, sid):
        self._list_semaphore.acquire()
        try:
            if sid in self._list:
                del self._list[sid]
                if len(self._list)==0 and not self._capture_process is None:
                    self._capture_process.destroy()
                    self._capture_process=None
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
    
    def req_websocket(self, cinfo, wsock):
        self._add_desktop_manager(cinfo, wsock)        
        
class Session(threading.Thread):
        
    def __init__(self, dskmain, cinfo, sid,  wsock):
        threading.Thread.__init__(self,  name="DesktopSession" + str(sid))
        self._dskmain=dskmain
        self._cinfo=cinfo
        prms = cinfo.get_permissions()
        if prms["fullAccess"]:
            self._allow_inputs=True
            self._allow_audio=True
        else:
            pret=self._dskmain._agent_main.get_app_permission(cinfo,"desktop")
            if pret["fullAccess"]:
                    self._allow_inputs=True
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
        self._semaphore = threading.Condition()
        
        self._quality=-1
        self._supported_frame=None
        self._frame_type=-1 # 0=DATA_PALETTE_COMPRESS_V1; 100=DATA_TJPEG"
        self._audio_type=-1
        self._send_frame_type=False
        self._send_audio_type=False
        self._send_buffer_size = -1
        self._send_buffer_size_counter = utils.Counter()
        self._keepalive_counter = None
        self._keepalive_send = False
        
        self._websocket.accept(10,{"on_close": self._on_websocket_close,"on_data":self._on_websocket_data})
        self._cursor_visible = True
        self._slow_mode = False
        self._audio_enable = True
        self._monitor = -1 
        
        self._capture_process_recovery=False
        self._capture_process_id=None
        self._capture_process_data=[]
        
        self._last_copy_text=None        
        
            
    def get_id(self):
        return self._id
    
    def get_idses(self):
        return self._idses
    
    def _set_monitor(self):
        if self._monitor!=-1:
            self._dskmain._capture_process.set_monitor(self, self._monitor)
    
    def _set_frame_type(self):
        if self._frame_type!=-1:
            self._dskmain._capture_process.set_frame_type(self, self._frame_type)
    
    def _init_audio(self):
        if self._audio_type!=-1:
            self._dskmain._capture_process.init_audio(self, self._audio_type)
    
    def _set_quality(self):
        self._dskmain._capture_process.set_quality(self, self._quality)
    
    def _set_buffer_size(self):
        if self._send_buffer_size==-1 or self._send_buffer_size_counter.is_elapsed(1):
            appsbsz = self._websocket.get_send_buffer_size()
            if self._send_buffer_size!=appsbsz:
                try:
                    self._dskmain._capture_process.set_send_buffer_size(self, appsbsz)
                    self._send_buffer_size=appsbsz
                except:
                    None                        
            self._send_buffer_size_counter.reset()
    
    def _set_slow_mode(self):
        self._dskmain._capture_process.set_slow_mode(self, self._slow_mode)
    
    def _set_audio_enable(self):
        self._dskmain._capture_process.set_audio_enable(self, self._audio_enable)
    
    def _on_websocket_data(self,websocket,tpdata,data):
        if not self._bdestroy:
            try:
                if self._keepalive_counter is not None:
                    self._keepalive_counter.reset()                
                prprequest = json.loads(data.to_str("utf8"))
                if prprequest is not None and "frametime" in prprequest:
                    #print "frame received. Time: " + prprequest["frametime"]                    
                    if self._capture_process_recovery==True:
                        self._capture_process_recovery=False
                        self._set_frame_type()
                        self._set_monitor()
                        self._set_quality()
                        self._set_slow_mode()
                        self._init_audio()
                        self._set_audio_enable()
                    else:
                        tm = float(prprequest["frametime"])
                        self._dskmain._capture_process.received_frame(self, tm)
                        self._set_buffer_size()                                            
                if prprequest is not None and "inputs" in prprequest:
                    if not self._allow_inputs:
                        raise Exception("Permission denied (inputs).")
                    self._dskmain._capture_process.inputs(self, prprequest["inputs"])                                            
                if prprequest is not None and "cursor" in prprequest:
                    if prprequest["cursor"]=="true":
                        self._cursor_visible=True
                    elif prprequest["cursor"]=="false":
                        self._cursor_visible=False
                if prprequest is not None and "monitor" in prprequest:
                    self._monitor = int(prprequest["monitor"])
                    self._set_monitor()                    
                    if prprequest is not None and "acceptFrameType" in prprequest:
                        arft = prprequest["acceptFrameType"].split(";")
                        if self._supported_frame is not None:
                            for f in range (len(self._supported_frame)):
                                tf=self._supported_frame[f]                            
                                for i in range(len(arft)):
                                    if int(arft[i])==tf:
                                        self._frame_type=tf
                                        self._send_frame_type=True
                                        self._set_frame_type()
                                        break
                                if self._send_frame_type==True:
                                    break
                    if prprequest is not None and "acceptAudioType" in prprequest:
                        if not self._allow_audio:
                            raise Exception("Permission denied (audio).")
                        arft = prprequest["acceptAudioType"].split(";")
                        for i in range(len(arft)):
                            v = int(arft[i])
                            if v==0:
                                self._audio_type=v
                                self._send_audio_type=True
                                self._init_audio()                                
                                break
                            
                if prprequest is not None and "slow" in prprequest:
                    self._slow_mode=prprequest["slow"]=="true"
                    self._set_slow_mode()                    
                if prprequest is not None and "quality" in prprequest:
                    self._quality=int(prprequest["quality"])
                    self._set_quality()
                if prprequest is not None and "keepalive" in prprequest:
                    if self._keepalive_counter is None:
                        self._keepalive_counter = utils.Counter()
                    self._keepalive_send = True                
                if prprequest is not None and "audioEnable" in prprequest:
                    self._audio_enable=prprequest["audioEnable"]=="true"
                    self._set_audio_enable()                    
            except Exception as ex:
                self._dskmain._agent_main.write_err("AppDesktop:: on_websoket_data error. ID: " + self._id + " - Error:" + utils.exception_to_string(ex))            
            
   
    def _on_websocket_close(self):
        self.destroy();
       
    def _on_process_data(self,sdata):
        try:
            lst=[]
            if self._send_frame_type==True:
                self._send_frame_type=False
                lst.append(utils.Bytes(struct.pack("!hh",801,self._frame_type)))
            
            if self._send_audio_type==True:
                self._send_audio_type=False
                lst.append(utils.Bytes(struct.pack("!hh",809,0))) #0=opus            
            
            tp = _struct_h.unpack(sdata[0:2])[0]
            if tp==10: #MONITOR
                if self._capture_process_recovery==True:
                    #FORCE RESPONSE FROM CLIENT
                    lst.append(utils.Bytes(struct.pack("!h",800)+str(time.time())))
                    lst.append(utils.Bytes(struct.pack("!hB",2,1)))
                else:
                    lst.append(sdata)
            elif tp==11: #SUPPORTED FRAME
                if self._capture_process_recovery==False:
                    p=2
                    cnt = _struct_h.unpack(sdata[p:p+2])[0]
                    self._supported_frame=[]
                    for i in range(cnt):
                        p+=2
                        self._supported_frame.append(_struct_h.unpack(sdata[p:p+2])[0])                    
            elif tp==2: #TOKEN FRAME
                if sdata[2]==1:
                    tm = time.time()
                    lst.append(utils.Bytes(struct.pack("!h",800)+str(tm)))
                    #print "frame sent. Time: " + str(tm)
                                        
                lst.append(sdata)                
            elif tp==805: #COPY
                self._last_copy_text=unicode(base64.b64decode(sdata.new_buffer(2).to_str("utf8")).decode("utf8"))
                lst.append(sdata)
            elif tp==810: #AUDIO DATA
                #print "AUDIO: " + str(len(sdata))
                lst.append(sdata)
            elif tp==990: #CAPTURE ERROR
                self.destroy()
            elif tp==998: #DEBUG
                #self._dskmain._agent_main.write_debug(sdata.new_buffer(2).to_str("utf8"))
                self._dskmain._agent_main.write_info(sdata.new_buffer(2).to_str("utf8"))
            else:
                lst.append(sdata)
            self._semaphore.acquire()
            try:
                self._capture_process_data.extend(lst)
                if len(self._capture_process_data)>0:
                    self._semaphore.notify_all()
            finally:
                self._semaphore.release()
        except Exception as e:
            if not self.is_destroy():
                self._dskmain._agent_main.write_except(e,"AppDesktop:: capture error id:" + self._id +". (on_process_data)\n")
                    
    def _on_process_destroy(self):
        None        
    
    def _on_process_close(self):
        self._send_buffer_size = -1                       
        
    def run(self):
        process_status_counter=utils.Counter()    
        bfirst=True
        err_msg=None
        try:
            lst = []
            #SEND ID        
            sdataid=struct.pack("!h",900)+self._id;
            lst.append(utils.Bytes(sdataid))
            #START KEEP ALIVE MANAGET
            lst.append(utils.Bytes(struct.pack("!h",901)))            
            self._websocket.send_list_bytes(lst)
            
            while not self.is_destroy() and not self._dskmain._capture_process.is_destroy():
                lst = None                
                if self._dskmain._capture_process.get_status()=="started":
                    if not self._dskmain._capture_process.exists(self):
                        try:                            
                            self._capture_process_recovery=not bfirst
                            self._dskmain._capture_process.add(self)
                            bfirst=False
                        except:
                            None
                    process_status_counter.reset()
                elif process_status_counter.is_elapsed(15):
                    raise Exception("Process not started.")
                                                    
                self._semaphore.acquire()
                try:
                    if len(self._capture_process_data)==0 and not self._keepalive_send:
                        self._semaphore.wait(1)
                    if len(self._capture_process_data)>0:
                        lst=self._capture_process_data
                        self._capture_process_data=[]
                finally:
                    self._semaphore.release()
                
                
                if self._keepalive_counter is not None and self._keepalive_counter.is_elapsed(10.0):
                    self.destroy()
                else:
                    if self._keepalive_send:
                        self._keepalive_send=False
                        bts=utils.Bytes(struct.pack("!h",901))
                        if lst is None:
                            lst=[]
                        lst.append(bts)
                    if lst is not None:
                        self._websocket.send_list_bytes(lst)
                
                
        except Exception as e:
            if not self.is_destroy():
                appmsg = self._dskmain._capture_process.get_last_error()
                if appmsg is None:
                    appmsg = utils.exception_to_string(e)
                self._dskmain._agent_main.write_err("AppDesktop:: capture process id: " + self._id + " error: "  + appmsg)
                
        
        if not self.is_destroy():
            if err_msg is None:
                appmsg = self._dskmain._capture_process.get_last_error()
                if appmsg is None:
                    appmsg="Process not started."
                err_msg=appmsg
            try:
                self._websocket.send_bytes(utils.Bytes(struct.pack("!h",999) + err_msg))
            except:
                None
            self.destroy()
    
    def copy_text(self):
        if not self._allow_inputs:
            raise Exception("Permission denied (inputs).")
        self._last_copy_text = None
        self._dskmain._capture_process.copy_text(self);
        cnt = utils.Counter()
        while self._last_copy_text is None:
            time.sleep(0.5)
            if self.is_destroy() or cnt.is_elapsed(10):
                return ""
        return self._last_copy_text
         
    
    def paste_text(self,s):
        if not self._allow_inputs:
            raise Exception("Permission denied (inputs).")
        return self._dskmain._capture_process.paste_text(self,s);
    
    def destroy(self):
        bok=False
        self._semaphore.acquire()
        try:
            if not self._bdestroy:
                bok=True
            self._bdestroy=True
            self._semaphore.notify_all()
        finally:
            self._semaphore.release()
        if bok:
            if self._id is not None:
                if self._websocket is not None:
                    self._websocket.close()
                    self._websocket=None
                try:
                    self._dskmain._capture_process.remove(self)
                except Exception as e:
                    self._dskmain._agent_main.write_except(e,"AppDesktop:: captureprocess remove error " + self._id + ":")
                if self._id is not None:
                    self._dskmain._rem_desktop_manager(self._id)
                self._id=None
    
    def is_destroy(self):
        return self._bdestroy
               
class CaptureProcessClientDestroy(threading.Thread):
    
    def __init__(self, agent_main, ppid, pprc):
        threading.Thread.__init__(self,  name="DesktopCaptureProcessDestroy")
        self._agent_main=agent_main
        self._ppid=ppid
        self._process=pprc
        
    
    def _is_process_running(self):
        if self._process!=None:
            if self._process.poll() == None:
                return True
        elif self._ppid!=None:
            if self._agent_main.get_osmodule().is_task_running(self._ppid):
                return True
        return False
    
    def run(self):
        try:
            #Attende chiusura processo
            bok=False
            if self._process is not None or self._ppid is not None:
                r=20
                for i in range(r):
                    if not self._is_process_running():
                        bok=True
                        break
                    time.sleep(0.5)
            if not bok:
                if self._process!=None:
                    self._process.kill()
                elif self._ppid!=None:
                    self._agent_main.get_osmodule().task_kill(self._ppid)
        except Exception as e:
            self._agent_main.write_except(e)
    
class CaptureProcessClient(threading.Thread):
    
    def __init__(self, agent_main):
        threading.Thread.__init__(self,  name="DesktopCaptureProcessClient")
        self._lastid=0
        self._bdestroy=False
        self._agent_main=agent_main
        self._screen_module=None
        self._screen_listlibs=None
        self._sound_module=None
        self._sound_listlibs=None
        self._semaphore = threading.Condition()
        self._sharedmem=None
        self._sharedmem_bw=None
        self._sharedmem_br=None
        self._process=None
        self._process_init=False
        self._process_status="stopped"
        self._process_last_error=None
        self._ppid=None
        self._currentconsole=None
        self._currentconsolecounter=utils.Counter()
        self._listdm={}
        self._debug_inprocess=False
        try:
            self._debug_inprocess=self._agent_main.get_config("desktop.debug_inprocess",False)
        except:
            None
        
    def is_destroy(self):
        return self._bdestroy
    
    def destroy(self):
        self._bdestroy=True
    
    def get_last_error(self):
        return self._process_last_error;
        
    def _get_screen_module(self):
        if self._screen_module is None:
            self._screen_module = self._agent_main.load_lib("screencapture")
            #DOWNLOAD AUDIO LIB
            try:
                soundenable = False
                try:
                    soundenable = self._agent_main.get_config("desktop.sound_enable", True);
                except:
                    None
                if soundenable:
                    self._get_sound_module()
            except Exception as e:
                self._agent_main.write_err("Sound library load error: " + utils.exception_to_string(e))             
        return self._screen_module
    
    def _get_sound_module(self):
        if not (agent.is_windows() and (self._get_screen_module().isWinXP()==1 or self._get_screen_module().isWin2003Server()==1)):
            if self._sound_module is None:
                self._sound_module = self._agent_main.load_lib("soundcapture")
        return self._sound_module
    
    def _set_process_status_updating(self,checkv):
        appldm={}
        self._semaphore.acquire()
        self._process_init=True
        bdry=False
        try:
            while self._process_status=="updating":
                self._semaphore.wait(0.5)
                if self._bdestroy:
                    break
            bdry=self._bdestroy
            if self._process_status==checkv:
                return False
            self._process_status="updating"
            if checkv=="stopped":
                #self._write_list=[]
                appldm=self._listdm
                self._listdm={}                                
        finally:
            self._semaphore.release()
        if checkv=="stopped":
            for sid in appldm:
                dm = appldm[sid]
                try:
                    if bdry:
                        dm._on_process_destroy()
                    else:
                        dm._on_process_close()
                except Exception as e:
                    self._agent_main.write_except(e,"AppDesktop:: Stop capture process error:\n")            
            return True
        else:
            return not bdry
    
    def get_status(self):
        return self._process_status
    
    def _get_process_status(self):
        self._semaphore.acquire()
        try:
            while self._process_init==False or self._process_status=="updating":
                self._semaphore.wait(0.5)
                if self._bdestroy:
                    raise Exception("Process destroyed.")
            return self._process_status
        finally:
            self._semaphore.release()
    
    def _set_process_status(self,v):
        self._semaphore.acquire()
        try:
            self._process_status=v
        finally:
            self._semaphore.release()        
    
    def _is_process_running(self):
        if self._process!=None:
            if self._process.poll() == None:
                return True
        elif self._ppid!=None:
            if self._agent_main.get_osmodule().is_task_running(self._ppid):
                return True
        return False
    
    def _get_linux_envirionment(self,uid,tty):
        bwaylanderr=False
        lstret={} 
        if uid!=-1:
            lst = native.get_instance().get_process_ids()
            try:
                bok=False
                cnt = utils.Counter()
                while not bok and cnt.get_value()<=2:
                    for pid in lst:
                        if native.get_instance().get_process_uid(pid)==uid:
                            lstret={}
                            arenv = native.get_instance().get_process_environ(pid)
                            for apps in arenv:                        
                                if apps=="XAUTHORITY" or apps=="DISPLAY" or apps.startswith("WAYLAND_") or apps.startswith("XDG_") or apps.startswith("LC_"):
                                    lstret[apps]=arenv[apps]
                            if ("DISPLAY" in lstret and "XAUTHORITY" in lstret):
                                bok=True
                                break
                            lstret={}
                    time.sleep(0.5)
            except:
                lstret={}
        
        #check cmdline
        try:
            if tty is not None:
                st = os.stat("/dev/" + tty)
            lst = native.get_instance().get_process_ids()
            for pid in lst:
                sst = native.get_instance().get_process_stat(pid)
                if (tty is None or sst["tty"]==st.st_rdev) and (uid==-1 or native.get_instance().get_process_uid(pid)==uid):
                    lret = native.get_instance().get_process_cmdline(pid)
                    bok=False
                    sxauth=None
                    sdsp=None
                    for i in range(len(lret)):
                        if i==0:
                            scmd = lret[i]
                            arcmd = scmd.split("/")
                            if len(arcmd)>0:
                                scmd=arcmd[len(arcmd)-1]
                                if scmd.upper()=="X" or scmd.upper()=="XORG": 
                                    bok=True
                                elif scmd.upper()=="XWAYLAND":
                                    bwaylanderr=True
                        if bok:
                            sitm = lret[i]
                            if i>0 and lret[i-1]=="-auth":
                                sxauth=sitm
                            elif len(sitm)==2:
                                if sitm[0]==":" and sitm[1].isdigit():
                                    sdsp=sitm
                            elif len(sitm)==4:
                                if sitm[0]==":" and sitm[1].isdigit() and sitm[2]=="." and sitm[3].isdigit():
                                    sdsp=sitm
                    if sxauth is not None:
                        lstret["XAUTHORITY"] = sxauth
                    if sdsp is not None:
                        lstret["DISPLAY"] = sdsp
                    if bok:
                        bwaylanderr=False
                        break
            
        except:
            None
        
        if bwaylanderr:
            self._process_last_error="XWayland is not supported."
            self.destroy()
            raise Exception(self._process_last_error)
        
        if "DISPLAY" not in lstret:
            lstret["DISPLAY"]=":0"
            
        if "XAUTHORITY" in lstret:
            sxauth = lstret["XAUTHORITY"]
            if not os.path.exists(sxauth):
                try:
                    p = sxauth.rindex("/")
                    if p>=0:
                        sxauthdir = sxauth[0:p]
                        os.makedirs(sxauthdir, 0700)
                        fd = os.open(sxauth,os.O_RDWR|os.O_CREAT, 0600)
                        os.close(fd)                                                        
                except:
                    None
        '''
        if "DISPLAY" in lstret:
            self._agent_main.write_info("DISPLAY: " + lstret["DISPLAY"])
        if "XAUTHORITY" in lstret:
            self._agent_main.write_info("XAUTHORITY: " + lstret["XAUTHORITY"])
        '''
        return lstret        
    
    def _load_linux_console_info(self,appconsole):
        if appconsole is not None:
            stty=appconsole["id"]
            #self._agent_main.write_info("\n\n")
            #self._agent_main.write_info("TTY: " + stty)
            pwinfo=None            
            try:
                import pwd
                if os.getuid()==0:
                    data = subprocess.Popen(["who"], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
                    so, se = data.communicate()
                    if so is not None and len(so)>0:
                        ar = so.split("\n")
                        for s in ar:
                            if " " + stty + " " in s:
                                try:
                                    pwinfo=pwd.getpwnam(s.split(" ")[0].rstrip(" "))
                                    if pwinfo is not None:
                                        break
                                except:
                                    None
                    if pwinfo is None:
                        st = os.stat("/dev/" + stty)
                        pwinfo=pwd.getpwuid(st.st_uid)
                else:
                    pwinfo=pwd.getpwuid(os.getuid())
            except:
                None
            
            appuid=-1
            libenv={}
            if pwinfo is not None:                
                #self._agent_main.write_info("USER: " + pwinfo.pw_name)                
                appconsole["user"] = pwinfo.pw_name
                appconsole["uid"] = pwinfo.pw_uid
                appconsole["gid"] = pwinfo.pw_gid
                appconsole["home"] = pwinfo.pw_dir
                appuid=pwinfo.pw_uid
            else:
                libenv = os.environ
            
            lstret = self._get_linux_envirionment(appuid, self._appconsole["id"])
            for k in lstret:
                libenv[k]=lstret[k]
            if pwinfo is not None:
                libenv['HOME'] = appconsole["home"]
                libenv['LOGNAME'] = appconsole["user"]
                libenv['USER'] = appconsole["user"]
            appconsole["env"]=libenv
            
    
    def _get_console(self):
        if agent.is_windows():
            return {"id": self._get_screen_module().consoleSessionId()}
        elif agent.is_mac():
            return {"id": self._get_screen_module().consoleUserId()}
        elif agent.is_linux():
            try:
                stty=native.get_instance().get_tty_active()
                if stty is not None:
                    return {"id": stty}                    
            except:
                None 
            
        return None
    
    def _is_change_console(self):
        if self._currentconsole is not None and self._currentconsolecounter.is_elapsed(1):
            self._currentconsolecounter.reset()
            appc=self._get_console()
            appcid=appc["id"]
            if agent.is_windows():
                if (self._get_screen_module().isWinXP()==1 or self._get_screen_module().isWin2003Server()==1) and appcid>0:
                    self._get_screen_module().winStationConnectW()
                    time.sleep(1)
                    self._destroy_process()
                    return True
                elif appcid!=self._currentconsole["id"]:
                    self._destroy_process()
                    return True
            elif agent.is_mac():
                if appcid!=self._currentconsole["id"]:
                    self._destroy_process()
                    time.sleep(1)
                    return True
            elif agent.is_linux():
                if appcid!=self._currentconsole["id"]:
                    self._destroy_process()
                    return True
        return False
    
    def _sharedmem_read_timeout(self):
        if self._is_change_console():
            return True
        return self.is_destroy() 
    
    def _init_sharedmem(self):
        self._sharedmem=sharedmem.Stream()        
        self._sharedmem_bw=self._sharedmem.get_buffer_writer()
        self._sharedmem_bw.set_autoflush_time(0)        
        self._sharedmem_br=self._sharedmem.get_buffer_reader()
        self._sharedmem_br.set_timeout_function(self._sharedmem_read_timeout)
    
    def _init_process_demote(self,user_uid, user_gid):
        def set_ids():
            os.setgid(user_gid)
            os.setuid(user_uid)
        return set_ids
    
    
    def _init_process(self):
        if self._sharedmem is not None and self._sharedmem.is_closed():
            self._destroy_process()
        else:
            self._is_change_console()
        if not self._set_process_status_updating("started"):
            return
        
        ### DEBUG PURPOSE        
        if self._debug_inprocess:
            if self._sharedmem==None:
                self._appconsole=self._get_console()
                self._init_sharedmem()
                def fix_perm(fn):
                    if agent.is_mac() and self._appconsole!=None:
                        utils.path_change_owner(fn, self._appconsole["id"], -1)
                        utils.path_change_permissions(fn, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP)
                    elif agent.is_linux() and self._appconsole!=None and "uid" in self._appconsole:
                        utils.path_change_owner(fn, self._appconsole["uid"], self._appconsole["gid"])
                        utils.path_change_permissions(fn, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP)                    
                fname = self._sharedmem.create(fixperm=fix_perm)
                
                self._cpdebug = CaptureProcessDebug(fname)
                self._cpdebug.start()
                self._set_process_status("started")
            return
        ###############################
        
        while True:
            try:
                self._appconsole=self._get_console()
                self._currentconsole=None
                if self._sharedmem==None:
                    
                    if agent.is_linux():
                        self._load_linux_console_info(self._appconsole)
                    
                    self._init_sharedmem()
                    def fix_perm(fn):
                        if agent.is_mac() and self._appconsole!=None:
                            utils.path_change_owner(fn, self._appconsole["id"], -1)
                            utils.path_change_permissions(fn, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP)
                        elif agent.is_linux() and self._appconsole!=None and "uid" in self._appconsole:
                            utils.path_change_owner(fn, self._appconsole["uid"], self._appconsole["gid"])
                            utils.path_change_permissions(fn, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP)
                    fname = self._sharedmem.create(fixperm=fix_perm)
                    #RUN PROCESS
                    #if utils.path_exists("apps" + utils.path_sep + "desktop.py"): ##MI SERVE IN SVILUPPO
                    #    import compileall
                    #    compileall.compile_file("apps" + utils.path_sep + "desktop.py")
                    if agent.is_windows():
                        runaselevatore=u"False"
                        if self._get_screen_module().isUserInAdminGroup()==1:
                            if self._get_screen_module().isRunAsAdmin()==1:
                                if self._get_screen_module().isProcessElevated()==1:
                                    runaselevatore=u"True"
                        #Gestito cosi perche' sys.executable creave problemi con percorsi unicode
                        exep=sys.executable
                        pyhome=u""
                        appth="native\\service.properties"
                        if (utils.path_exists(appth)):
                            f = utils.file_open(appth, 'r', encoding='utf-8')
                            sprop = f.read()
                            f.close()
                            lns = sprop.splitlines()
                            for line in lns:
                                if line.startswith("pythonPath="):
                                    exep=line[11:]
                                elif line.startswith("pythonHome="):
                                    pyhome=line[11:]
                          
                        appcmd=u"\"" + exep + u"\" -S -m agent app=desktop " + unicode(fname) + u" " + unicode(str(self._agent_main._agent_debug_mode)) + u" windows " + runaselevatore
                        #appcmd=u"\"" + exep + u"\" -S -m agent app=desktop " + unicode(fname) + u" " + unicode(str(False)) + u" windows " + runaselevatore
                        self._ppid = self._get_screen_module().startProcessAsUser(appcmd,pyhome)
                        self._currentconsole=self._appconsole                        
                    elif agent.is_linux():
                        #GESTIRE IL RENICE
                        agfn=u'agent.pyc'
                        if self._agent_main._agent_debug_mode and utils.path_exists("agent.py"):
                            agfn=u'agent.py'                        
                        if self._appconsole!=None and "env" in self._appconsole:
                            libenv=self._appconsole["env"]
                            if utils.path_exists("runtime"):
                                libenv["LD_LIBRARY_PATH"]=utils.path_absname("runtime/lib")
                            elif "LD_LIBRARY_PATH" in os.environ:
                                libenv["LD_LIBRARY_PATH"]=os.environ["LD_LIBRARY_PATH"]
                            
                            self._process=subprocess.Popen([sys.executable, agfn, u'app=desktop', fname, str(self._agent_main._agent_debug_mode),u'linux'], env=libenv, preexec_fn=self._init_process_demote(self._appconsole["uid"], self._appconsole["gid"]))
                        else:
                            libenv = os.environ
                            lstret = self._get_linux_envirionment(-1, None)
                            for k in lstret:
                                libenv[k]=lstret[k]
                            if utils.path_exists("runtime"):
                                libenv["LD_LIBRARY_PATH"]=utils.path_absname("runtime/lib")
                            elif "LD_LIBRARY_PATH" in os.environ:
                                libenv["LD_LIBRARY_PATH"]=os.environ["LD_LIBRARY_PATH"]
                            self._process=subprocess.Popen([sys.executable, agfn , u'app=desktop', fname, str(self._agent_main._agent_debug_mode),u'linux'], env=libenv)
                        self._currentconsole=self._appconsole
                    elif agent.is_mac():
                        self._ppid = self._agent_main.get_osmodule().exec_guilnc(self._appconsole["id"],"desktop",[fname, str(self._agent_main._agent_debug_mode),u'mac'])
                        if self._ppid is not None:
                            self._currentconsole=self._appconsole
                            self._process = None
                        else:
                            self._currentconsole=None
                            libenv = os.environ
                            if utils.path_exists("runtime"):
                                libenv["DYLD_LIBRARY_PATH"]=utils.path_absname("runtime/lib")
                            #self._process=subprocess.Popen([sys.executable, u'agent.pyc', u'app=desktop', fname, str(self._agent_main._agent_debug_mode),u'mac'], env=libenv)
                            self._process=subprocess.Popen([sys.executable, u'-S', u'-m', u'agent' , u'app=desktop', unicode(fname), unicode(str(self._agent_main._agent_debug_mode)),u'mac'], env=libenv)
                            #GESTIRE IL RENICE
                    self._appconsole=None
                    #Attende che il processo si attiva
                    bok=False                    
                    if self._process is not None or self._ppid is not None:
                        cnt = utils.Counter()
                        while not cnt.is_elapsed(5):
                            time.sleep(0.5)
                            if self._is_process_running():
                                bok=True
                                break
                    if bok:
                        self._process_last_error=None
                        self._set_process_status("started")
                        break
                    else:
                        raise Exception("Process not started.")
                else:
                    break
             
            except Exception as e:
                time.sleep(2)
                self._destroy_process_internal()
                if self.is_destroy():
                    self._process_last_error=str(e)
                    self._set_process_status("stopped")
                    raise e
    
    def _destroy_process_internal(self):
        try:
            if self._sharedmem!=None:
                self._sharedmem.close()
        except Exception as e:            
            self._agent_main.write_except(e)
        
        cpd = CaptureProcessClientDestroy(self._agent_main,self._ppid,self._process)
        cpd.start()
        self._sharedmem=None
        self._process=None
        self._ppid=None
        self._currentconsole=None
        self._listdm={}        
    
    def _destroy_process(self):
        if not self._set_process_status_updating("stopped"):
            return
        self._destroy_process_internal()        
        self._set_process_status("stopped")
    
    
    def _write_data(self,s):
        st = self.get_status()
        if st=="started":
            self._sharedmem_bw.add_str(s)
        else:
            raise Exception("Process not started.")
    
    def _fire_on_process_data(self,sid,bts):
        try:
            self._listdm[sid]._on_process_data(bts)
        except:
            None
        
    def run(self):
        try:
            while not self.is_destroy():
                self._init_process()                
                try:
                    sid,bts = self._sharedmem_br.get_pack(["int","bytes"])
                    self._fire_on_process_data(str(sid),bts)                    
                except Exception as e:
                    if not self.is_destroy():
                        self._destroy_process()
                        time.sleep(1)                
        except Exception as e:
            try:
                self._process_last_error=str(e)
            except:
                self._process_last_error="Process not started."
        self.destroy()
        self._destroy_process()
        #UNLOAD DLL        
        if self._screen_module is not None:
            self._agent_main.unload_lib("screencapture")
            self._screen_module=None;
        if self._sound_module is not None:
            self._agent_main.unload_lib("soundcapture")
            self._sound_module=None;
        
    def exists(self, dm):
        self._semaphore.acquire()
        try:
            appid=dm._capture_process_id
            return appid is not None and appid in self._listdm
        finally:
            self._semaphore.release()
            
    def add(self, dm):
        appid=None
        self._semaphore.acquire()
        try:
            if self._bdestroy:
                raise Exception("Process destroyed.")            
            appid=dm._capture_process_id
            if appid is None:
                self._lastid+=1;
                appid=str(self._lastid)
                dm._capture_process_id=appid
            self._listdm[appid]=dm
            self._dm=dm
            if appid is not None:
                self._write_data(u"INITIALIZE:"+appid)                
        finally:
            self._semaphore.release()                    
        
    def remove(self, dm):
        appid=None
        self._semaphore.acquire()
        try:
            appid=dm._capture_process_id
            if appid is not None and appid in self._listdm:
                del self._listdm[appid]                
            else:
                appid=None 
            if appid is not None:
                self._write_data(u"TERMINATE:"+appid)
        finally:
            self._semaphore.release()        
    
    def get_id(self,dm):
        return dm._capture_process_id
    
    def set_send_buffer_size(self, dm, sz):
        sid=self.get_id(dm)
        apps=u"SET_SEND_BUFFER_SIZE:"+unicode(sid)+u";"+unicode(sz)
        self._write_data(apps)
    
    def received_frame(self, dm, tm):
        sid=self.get_id(dm)
        apps=u"RECEIVED_FRAME:"+unicode(sid)+u";"+unicode(tm)
        self._write_data(apps)        
    
    def init_audio(self, dm, v):
        sid=self.get_id(dm)
        apps=u"INIT_AUDIO:"+unicode(sid)+u";"+unicode(v)
        self._write_data(apps)
    
    def set_quality(self, dm, q):
        sid=self.get_id(dm)
        apps=u"SET_QUALITY:"+unicode(sid)+u";"+unicode(q)
        self._write_data(apps)
    
    def set_monitor(self, dm, m):
        sid=self.get_id(dm)
        apps=u"SET_MONITOR:"+unicode(sid)+u";"+unicode(m)
        self._write_data(apps)
    
    def set_frame_type(self, dm, tp):
        sid=self.get_id(dm)
        apps=u"SET_FRAME_TYPE:"+unicode(sid)+u";"+unicode(tp)
        self._write_data(apps)
    
    def set_slow_mode(self, dm, b):
        sid=self.get_id(dm)
        apps=u"SET_SLOW_MODE:"+unicode(sid)+u";"+unicode(b)
        self._write_data(apps)
    
    def set_audio_enable(self, dm, b):
        sid=self.get_id(dm)
        apps=u"SET_AUDIO_ENABLE:"+unicode(sid)+u";"+unicode(b)
        self._write_data(apps)
    
    def inputs(self, dm, sinps):
        bok = True;
        if agent.is_windows() and "CTRLALTCANC" in sinps:
            if self._get_screen_module().sas():
                bok = False
        if bok: 
            sid=self.get_id(dm)
            apps=u"INPUTS:"+unicode(sid)+";"+unicode(sinps)
            self._write_data(apps)
    
    def copy_text(self, dm) :
        sid=self.get_id(dm)
        self._write_data(u"COPY_TEXT:"+str(sid))
    
    def paste_text(self, dm, s) :
        sid=self.get_id(dm)
        if s is not None:
            self._write_data(u"PASTE_TEXT:"+str(sid)+u";"+base64.b64encode(s.encode("utf8")))


class CaptureProcessStdRedirect(object):
    
    def __init__(self,lg,lv):
        self._logger = lg;
        self._level = lv;
        
    def write(self, data):
        for line in data.rstrip().splitlines():
            self._logger.log(self._level, line.rstrip())


class CaptureProcessSessionSpeedCalculator():
    
    def __init__(self, prt):
        self._parent=prt        
        self._to_reset=False
        self._quality_inc_dec=0
        self._quality = 9
        self._quality_request = -1
        self._quality_counter = utils.Counter()
        self._fps_counter = utils.Counter()
        self._fps = 0
        self._min_wait_counter = utils.Counter()
        self._min_distance = 0
        self._min_wait_1 = 0.1
        self._min_wait_2 = None        
        self._frame_count=0
            
    def _calc_fps(self):
        if self._fps_counter.is_elapsed(1):            
            self._fps=int(float(self._frame_count)/self._fps_counter.get_value())
            self._min_distance=self._fps
            if self._min_distance<5:
                self._min_distance=5            
            if self._fps>5:
                self._min_wait_1=1.0/(float(self._fps)+5.0)
            else:
                self._min_wait_1=0.1            
            self._frame_count=0
            self._fps_counter.reset()
    
    def get_fps(self):
        self._calc_fps()
        return self._fps

    def get_min_distance(self):
        self._calc_fps()
        return self._min_distance        
    
    def get_min_wait(self):
        self._calc_fps()
        if self._min_wait_2 is not None:
            return self._min_wait_2
        else:
            return self._min_wait_1
    
    def set_quality_request(self, q):
        self._quality_request=q
        self.reset()
    
    def get_quality(self):
        if self._quality_request==-1:
            return self._quality
        else:
            return self._quality_request
    
    def reset(self):
        self._to_reset=True
        self._min_wait_2=None
    
    def received_frame(self,tm):
        self._frame_count+=1
        if not self._to_reset:
            if self._min_wait_counter.is_elapsed(1):
                self._min_wait_counter.reset()
                if self._fps<5:
                    self._min_wait_2=1.0/(float(self._fps)+2.0)                
                    #self._parent._send_debug("self._min_wait_2: " + str(self._min_wait_2))
            
            elp = (time.time()-tm)-self._parent._ping
            if elp>0.3:
                if self._quality_inc_dec==0:
                    self._quality_inc_dec=-1
                elif self._quality_inc_dec==1:
                    self._to_reset=True                    
            elif elp<0.2 and elp>0.0:
                if self._quality_inc_dec==0:
                    self._quality_inc_dec=+1   
                elif self._quality_inc_dec==-1:
                    self._to_reset=True                    
            if self._quality_counter.is_elapsed(2):
                if self._quality_request==-1:
                    if self._quality_inc_dec<0 and self._quality>0:
                        self._quality-=1
                    elif self._quality_inc_dec>0 and self._quality<9:
                        self._quality+=1  
                #self._parent._send_debug("self._quality: " + str(self._quality))
                self._to_reset=True
                
                        
        if self._to_reset:
            self._quality_counter.reset()
            self._min_wait_counter.reset()            
            self._quality_inc_dec=0           
            self._to_reset=False
        
class CaptureProcessSession(threading.Thread):
        
    def __init__(self, cprc, sid):
        threading.Thread.__init__(self,  name="CaptureProcessSession")
        self._capture_process = cprc
        self._scrinv = self._capture_process._screen_thread
        self._difference_inprogress = False        
        self._id=sid
        self._monitor=-1
        self._frame_type=-1
        self._frame_intervall_time=10.0/1000.0
        self._frame_intervall_time_counter=utils.Counter()
        self._frame_distance_lock=threading.Lock()
        self._frame_distance=0
        self._frame_size=0l
        self._audio_enable=True
        self._slow_mode=False
        self._slow_mode_counter=utils.Counter()
        self._ping=-1
        self._ping_counter=None
        self._speed_calculator=CaptureProcessSessionSpeedCalculator(self)
        self._sound_counter=utils.Counter()
        self._sound_init=False
        self._bdestroy = False
        
    def _send_debug(self, s):
        bts = utils.Bytes(struct.pack("!h",998))
        bts.append_str(s, "utf8")
        self._capture_process.write_data(self._id, bts);
    
    def cb_difference(self, sz, pdata):
        if sz>0:
            sdata = utils.Bytes(pdata[0:sz])
            tp = _struct_h.unpack(sdata[0:2])[0]
            if tp==1: #TOKEN DISTANCE FRAME
                self._frame_intervall_time_counter.reset()
                self._frame_intervall_time=float(_struct_i.unpack(sdata[2:6])[0])/1000.0                                
            elif tp==2: #TOKEN FRAME
                #CALCULATE PING
                if self._ping_counter is None:
                    self._ping_counter = utils.Counter()
                    self._capture_process.write_data(self._id, utils.Bytes(struct.pack("!hb",2,1)))
                
                self._frame_size+=long(len(sdata))
                if sdata[2]==1:
                    if self._frame_size==3:
                        self._speed_calculator.reset()
                        self._frame_size=0
                        return                        
                    with self._frame_distance_lock:
                        self._frame_distance+=1
                    self._frame_size=0
                self._capture_process.write_data(self._id, sdata)                    
            else:
                self._capture_process.write_data(self._id, sdata)
    
    def received_frame(self,tm): 
        #CALCULATE PING
        if self._ping==-1:
            self._ping=self._ping_counter.get_value()
            self._speed_calculator.reset()
            return
        with self._frame_distance_lock:
            self._frame_distance-=1        
        self._speed_calculator.received_frame(tm)        
    
    def set_send_buffer_size(self,sz):
        if self._capture_process._scr_libver>=2:
            self._scrinv.add(self, self._scrinv.setBufferSendSize, [sz])                
    
    def copy_text(self):
        self._scrinv.add(self, self._scrinv.copyText, [self._id])
    
    def paste_text(self, s):
        self._scrinv.add(self, self._scrinv.pasteText, [self._id, s])
    
    def set_frame_type(self,t):
        self._frame_type=t        
    
    def init_audio(self,v):
        if self._capture_process.get_sound_enable():            
            self.init_sound()
        else:
            bts = utils.Bytes(struct.pack("!h",811))
            bts.append_str(self._capture_process.get_sound_error_message(), "utf8")
            self._capture_process.write_data(self._id, bts);
    
    def set_slow_mode(self,b):
        self._slow_mode=b
        
    def set_audio_enable(self,b):
        self._audio_enable=b        
            
    def set_quality(self,q):
        self._speed_calculator.set_quality_request(q)       
    
    def set_monitor(self,m):
        if self._monitor!=m:
            self._monitor=m
            self._scrinv.add(self, self._scrinv.monitor, [self._id, m])
    
    def add_inputs(self,ips):
        for i in range(len(ips)):
            if i>=1:
                try:
                    prms=ips[i].split(",")
                    if prms[0]==u"MOUSE":
                        bcommand=False
                        if len(prms)==9:
                            bcommand=(prms[8]=="true")
                        self._scrinv.add(self, self._scrinv.inputMouse, [self._id, int(prms[1]), int(prms[2]), int(prms[3]), int(prms[4]), prms[5]=="true", prms[6]=="true", prms[7]=="true", bcommand])
                    elif prms[0]==u"KEYBOARD":                    
                        bcommand=False
                        if len(prms)==7:
                            bcommand=(prms[6]=="true")
                        self._scrinv.add(self, self._scrinv.inputKeyboard, [self._id, str(prms[1]), str(prms[2]), prms[3]=="true", prms[4]=="true", prms[5]=="true", bcommand])
                except Exception as ex:
                    self._capture_process._debug_print(utils.exception_to_string(ex) + "\n" + traceback.format_exc())
    
    def set_difference_inprogress(self, b):
        self._difference_inprogress=b
    
    def wait_difference_inprogress(self):
        while self._difference_inprogress:
            time.sleep(0.005)
            self.send_sound()
    
    def wait_time(self,tm):
        time.sleep(tm)
        self.send_sound()
                        
    def run(self):
        self._scrinv.add(self, self._scrinv.init,[self._id])
        try:
            appcnt=utils.Counter() 
            while not self._bdestroy:
                mdis=self._speed_calculator.get_min_distance()
                mwait=self._speed_calculator.get_min_wait()                
                if self._frame_distance<=mdis and (self._slow_mode==False or self._slow_mode_counter.is_elapsed(4)):
                    self._frame_intervall_time_counter.reset()
                    self._scrinv.add(self, self._scrinv.difference, [self._id,self._frame_type,self._speed_calculator.get_quality(),cb_difference])                    
                    while self._frame_type==-1:
                        self.wait_time(0.1)
                        if self._bdestroy:
                            return
                    
                    df = self._frame_intervall_time
                    w=mwait
                    if w>df:
                        df=w                                                
                    if not self._frame_intervall_time_counter.is_elapsed(df):
                        appwait=df-self._frame_intervall_time_counter.get_value()
                        appcnt.reset()
                        #self._send_debug("APPWAIT " + str(appwait) + "  df:" + str(df) + "  self._frame_intervall_time:" + str(self._frame_intervall_time))                        
                        while not appcnt.is_elapsed(appwait):
                            self.wait_time(0.005)                    
                    self.wait_difference_inprogress()                        
                    self._slow_mode_counter.reset()
                else:
                    if self._slow_mode:
                        self.wait_time(0.25)
                        self._speed_calculator.reset()
                    else:
                        self.wait_time(0.005)
                
        except Exception as ex:
            try:
                self._capture_process.write_data(self._id, utils.Bytes(struct.pack("!h",990)))
            except:
                None            
            self._capture_process._debug_print(utils.exception_to_string(ex) + "\n" + traceback.format_exc())            
        self._scrinv.add(self, self._scrinv.term,[self._id])

    def init_sound(self):
        if self._sound_init==False:
            try:
                self._sndmdl = self._capture_process._get_sound_module()
                self._sndmdl.DWASoundCaptureInit(self._id,0,9);
                self._sound_init=True
            except Exception as ex:
                try:
                    bts = utils.Bytes(struct.pack("!h",811))
                    bts.append_str(str(ex), "utf8")
                    self._capture_process.write_data(self._id, bts);
                except:
                    None
    
    def term_sound(self):
        if self._sound_init==True:
            self._sound_init=False
            try:
                self._sndmdl.DWASoundCaptureTerm(self._id);                
            except Exception as ex:
                self._capture_process._debug_print(utils.exception_to_string(ex) + "\n" + traceback.format_exc())
            

    def send_sound(self):
        if self._sound_init and self._sound_counter.is_elapsed(0.02):
            self._sound_counter.reset()
            try:
                pdatasound = ctypes.POINTER(ctypes.c_char)()
                szsound = self._sndmdl.DWASoundCaptureGetData(self._id, ctypes.byref(pdatasound));
                if szsound>0 and self._audio_enable and not self._slow_mode:
                    self._capture_process.write_data(self._id, utils.Bytes(struct.pack("!h",810)+pdatasound[0:szsound]))
            except Exception as ex:
                self._term_sound()
                try:
                    bts = utils.Bytes(struct.pack("!h",811))
                    bts.append_str(str(ex), "utf8")
                    self._capture_process.write_data(self._id, bts);
                except:
                    None                
    
    def destroy(self,bwait=False):
        self._bdestroy=True
        self.term_sound()
        if bwait:
            self.join(2)        
    
class CaptureProcessScreen(threading.Thread):
        
    def __init__(self, cprc):
        threading.Thread.__init__(self,  name="CaptureProcessScreen")
        self._capture_process = cprc
        self._scrmdl = self._capture_process._get_screen_module()
        self._list = []
        self._currentscr=None
    
    def init(self, args):
        self._scrmdl.init(args[0])
    
    def term(self, args):
        self._scrmdl.term(args[0])
    
    def cb_difference(self, sz, pdata):
        self._currentscr.cb_difference(sz, pdata)
    
    def difference(self, args):
        self._currentscr.set_difference_inprogress(True)
        self._scrmdl.difference(args[0],args[1],args[2],args[3])
        self._currentscr.set_difference_inprogress(False)
    
    def monitor(self, args):
        self._scrmdl.monitor(args[0],args[1])
    
    def inputMouse(self, args):
        self._scrmdl.inputMouse(args[0],args[1],args[2],args[3],args[4],args[5],args[6],args[7],args[8])
    
    def inputKeyboard(self, args):
        self._scrmdl.inputKeyboard(args[0],args[1],args[2],args[3],args[4],args[5],args[6])
    
    def pasteText(self, args):
        self._scrmdl.pasteText(args[0],ctypes.c_wchar_p(unicode(args[1])))
    
    def copyText(self, args):        
        apps=None
        pi=None
        try:
            pi=self._scrmdl.copyText(args[0])
            if pi:
                apps = ctypes.wstring_at(pi)
        finally:
            if pi: # and ln>0:
                self._scrmdl.freeMemory(pi)
        if apps is None:
            apps = ""
        bts = utils.Bytes(struct.pack("!h",805))
        bts.append_str(base64.b64encode(apps.encode("utf8")), "utf8")
        self._capture_process.write_data(args[0], bts)
    
    def setBufferSendSize(self, args):
        self._scrmdl.setBufferSendSize(args[0]);
       
    def add(self, scr, fnc, args):
        self._list.append([scr, fnc, args])
        
    def run(self):
        while not self._capture_process.is_destroy():
            while len(self._list)>0:
                ar = self._list.pop(0)
                self._currentscr=ar[0]
                ar[1](ar[2])
                self._currentscr=None                
            time.sleep(0.005)

class CaptureProcessSound(threading.Thread):
        
    def __init__(self, cprc):
        threading.Thread.__init__(self,  name="CaptureProcessSound")
        self._capture_process = cprc
        self._sndmdl = self._capture_process._get_sound_module()
        self._counter=utils.Counter();
        self._enable=None
        self._error_message=""
    
    def get_enable(self):
        return self._enable

    def get_error_message(self):
        return self._error_message
    
    def run(self):
        try:
            self._sndmdl.DWASoundCaptureStart()
            if agent.is_mac():
                bf = ctypes.create_string_buffer(2048)
                l = self._sndmdl.DWASoundCaptureGetDetectOutputName(bf,2048);
                if l>0:
                    sodn=bf.value[0:l]
                else:
                    sodn=""
                if "SOUNDFLOWER" not in sodn.upper():
                    raise Exception("Soundflower not found. Please install it and set it as your primary output device.")
            self._enable=True            
            self._counter.reset()
            while not self._capture_process.is_destroy():
                if self._counter.is_elapsed(3):
                    self._counter.reset()                    
                    #self._sndmdl.DWASoundCaptureDetectOutput() #TO CHECK                     
                time.sleep(0.5)
            self._sndmdl.DWASoundCaptureStop()
        except Exception as ex:
            self._enable=False
            self._error_message=str(ex)
            self._capture_process._debug_print("Sound error: " + str(ex))
            self._sndmdl.DWASoundCaptureStop()

class CaptureProcessDebug(threading.Thread):
        
    def __init__(self, nm):
        threading.Thread.__init__(self,  name="CaptureProcessDebug")
        self._name=nm
        self._capture_process = CaptureProcess()

    def run(self):
        self._capture_process.listen(self._name,"True")        
        self._capture_process.destroy()
        
    def write(self, sdata):
        self._capture_process._on_request(sdata)

class CaptureProcess():
    
    def __init__(self):
        _libmap["captureprocess"]=self
        self._bdestroy=False
        self._screen_thread=None
        self._screen_module=None
        self._screen_listlibs=None
        self._sound_module=None
        self._sound_thread=None        
        self._sound_listlibs=None
        self._sharedmem=None
        self._sharedmem_bw=None
        self._sharedmem_br=None        
        self._listids={}        
        self._scr_libver = 0        
        self._last_copy_text=""
        self._debug_logprocess=False
        self._sound_enable=True
        self._sound_error_message=""
        try:
            c = agent.read_config_file()
            if "desktop.debug_logprocess" in c:
                self._debug_logprocess=c["desktop.debug_logprocess"]
            if "desktop.sound_enable" in c:
                self._sound_enable=c["desktop.sound_enable"]
        except:
            None
    
    def is_destroy(self):
        return self._bdestroy        
    
    def destroy(self):
        self._bdestroy=True
    
    def _get_screen_module(self):        
        if self._screen_module is None:
            self._screen_listlibs = native.load_libraries_with_deps("screencapture")
            self._screen_module = self._screen_listlibs[0] 
        return self._screen_module
    
    def _get_sound_module(self):
        if self._sound_module is None:
            self._sound_listlibs = native.load_libraries_with_deps("soundcapture")
            self._sound_module = self._sound_listlibs[0]
        return self._sound_module    
    
    def get_sound_enable(self):
        if self._sound_thread is None:
            return False
        return self._sound_thread.get_enable()
    
    def get_sound_error_message(self):
        smsg=self._sound_error_message
        if self._sound_thread is not None:
            smsg=self._sound_thread.get_error_message()
        return smsg
    
    def write_data(self, sid, bts):
        self._sharedmem_bw.add_pack(["int","bytes"],[sid,bts])        
                  
    def _enable_debug(self):
        self._get_screen_module().setCallbackDebug(cb_debug_print)
    
    def _debug_print(self,s):
        if self._dbgenable:
            print(s)
                
    def cb_debug_print(self, s):
        self._debug_print("DESKTOPNATIVE@" + s)

    def _on_request(self, srequest):
        #self._debug_print("Richiesta: " + srequest)
        ar = srequest.split(":")
        try:
            if len(ar)==1 or len(ar)==2:
                if len(ar)==2:
                    prms=ar[1].split(";")
                if ar[0]==u"INITIALIZE":
                    appid=int(prms[0]);
                    if appid in self._listids:
                        apparid = self._listids[appid]                                
                        apparid["screenThread"].destroy()
                    self._listids[appid]={"id": appid, "monitor": -1, "sound": "none"}
                    self._listids[appid]["screenThread"]=CaptureProcessSession(self, appid)
                    self._listids[appid]["screenThread"].start()                        
                if ar[0]==u"TERMINATE":
                    appid=int(prms[0]);
                    if appid in self._listids:
                        apparid = self._listids[appid]
                        if "screenThread" in apparid:                                
                            apparid["screenThread"].destroy()
                        del self._listids[appid]  
                elif ar[0]==u"RECEIVED_FRAME":
                    appid=int(prms[0]);
                    tm=float(prms[1])
                    if appid in self._listids:
                        self._listids[appid]["screenThread"].received_frame(tm)
                elif ar[0]==u"INIT_AUDIO":
                    appid=int(prms[0]);
                    v=float(prms[1])
                    if appid in self._listids:
                        self._listids[appid]["screenThread"].init_audio(v)
                elif ar[0]==u"SET_SEND_BUFFER_SIZE":
                    appid=int(prms[0]);
                    sz=int(prms[1])
                    if appid in self._listids:
                        self._listids[appid]["screenThread"].set_send_buffer_size(sz)
                elif ar[0]==u"SET_MONITOR":
                    appid=int(prms[0]);
                    monidx=int(prms[1])
                    if appid in self._listids:
                        self._listids[appid]["screenThread"].set_monitor(monidx)
                elif ar[0]==u"SET_FRAME_TYPE":
                    appid=int(prms[0]);
                    frmtp=int(prms[1])
                    if appid in self._listids:
                        self._listids[appid]["screenThread"].set_frame_type(frmtp)
                elif ar[0]==u"SET_QUALITY":
                    appid=int(prms[0]);
                    qa=int(prms[1])
                    if appid in self._listids:
                        self._listids[appid]["screenThread"].set_quality(qa)
                elif ar[0]==u"SET_SLOW_MODE":
                    appid=int(prms[0]);
                    b=prms[1]=="True"
                    if appid in self._listids:
                        self._listids[appid]["screenThread"].set_slow_mode(b)
                elif ar[0]==u"SET_AUDIO_ENABLE":
                    appid=int(prms[0]);
                    b=prms[1]=="True"
                    if appid in self._listids:
                        self._listids[appid]["screenThread"].set_audio_enable(b)
                elif ar[0]==u"COPY_TEXT":
                    appid=int(prms[0]);
                    if appid in self._listids:
                        self._listids[appid]["screenThread"].copy_text()                                                            
                elif ar[0]==u"PASTE_TEXT":
                    appid=int(prms[0]);
                    s=base64.b64decode(prms[1]).decode("utf8")
                    if appid in self._listids:
                        self._listids[appid]["screenThread"].paste_text(s)
                elif ar[0]==u"INPUTS":
                    appid=int(prms[0]);
                    if appid in self._listids:
                        self._listids[appid]["screenThread"].add_inputs(prms)                
            else:
                raise Exception(u"Request '" + srequest + u"' is not valid.")
        except Exception as ex:
            self._debug_print(traceback.format_exc())

    def _sharedmem_read_timeout(self):
        return self.is_destroy() 
    
    def listen(self,fname,dbgenable):
        try:
            self._dbgenable=(dbgenable.upper()=="TRUE")
            if self._dbgenable==True:
                if self._debug_logprocess:
                    self._logger = logging.getLogger()
                    hdlr = logging.handlers.RotatingFileHandler(u'captureprocess.log', 'a', 10000000, 3, None, True)
                    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
                    hdlr.setFormatter(formatter)
                    self._logger.addHandler(hdlr) 
                    self._logger.setLevel(logging.DEBUG)
                    sys.stdout=CaptureProcessStdRedirect(self._logger,logging.DEBUG);
                    sys.stderr=CaptureProcessStdRedirect(self._logger,logging.ERROR);
                    self._enable_debug()        
        except Exception as ex:
            self._debug_print(str(ex) + "\n" + traceback.format_exc());
            return        
        try:
            self._scr_libver = self._get_screen_module().version()
        except:
            None            
        self._debug_print("Init capture process. (" + fname + ")")        
        try:
            
            self._sharedmem=sharedmem.Stream()
            self._sharedmem.connect(fname)            
            self._sharedmem_bw=self._sharedmem.get_buffer_writer()
            self._sharedmem_bw.set_autoflush_time(0.02)
            #self._sharedmem_bw.set_autoflush_size(56*1024)            
            self._sharedmem_br=self._sharedmem.get_buffer_reader()
            self._sharedmem_br.set_timeout_function(self._sharedmem_read_timeout)
            
            self._screen_thread = CaptureProcessScreen(self)
            self._screen_thread.start()
            
            try:                
                if not (agent.is_windows() and (self._get_screen_module().isWinXP()==1 or self._get_screen_module().isWin2003Server()==1)):
                    if self._sound_enable:
                        fnsndcrash=None
                        if agent.is_linux():
                            fnsndcrash = utils.path_expanduser("~") + utils.path_sep + u".dwagent"
                            if not utils.path_exists(fnsndcrash):
                                utils.path_makedirs(fnsndcrash)
                            fnsndcrash = fnsndcrash + utils.path_sep + u"app_desktop.soundcrash"
                        if fnsndcrash is None or not utils.path_exists(fnsndcrash):
                            if fnsndcrash is not None:                                                                
                                fsndcrash=utils.file_open(fnsndcrash, 'wb')
                                fsndcrash.close()
                            try:
                                self._get_sound_module().DWASoundCaptureVersion() #CHECK TO LOAD LIB
                                self._sound_thread = CaptureProcessSound(self)
                                self._sound_thread.start()
                                while self._sound_thread.get_enable() is None and not self._sharedmem.is_closed():
                                    time.sleep(0.25)
                            finally:
                                if fnsndcrash is not None:
                                    if utils.path_exists(fnsndcrash):
                                        os.remove(fnsndcrash)
                        else:
                            self._sound_error_message="Crash soundlib."
                    else:
                        self._sound_error_message="Not enabled."
                else:
                    self._sound_error_message="Not supported."
            except Exception as ex:
                self._sound_thread=None
                self._sound_error_message=str(ex)                 
                self._debug_print("Sound load error. " + str(ex));            
            
            self._debug_print("Ready to accept requests")            
            while not self._sharedmem.is_closed():
                srequest = self._sharedmem_br.get_str()
                if srequest==None:
                    #self._debug_print("########## Richiesta: NONE")
                    break
                self._on_request(srequest)
        except Exception as ex:
            if not self.is_destroy():
                self._debug_print(traceback.format_exc());
        self._bdestroy=True
        if self._sharedmem is not None:
            self._sharedmem.close()
        for appid in self._listids.keys():
            apparid = self._listids[appid]
            if "screenThread" in apparid:
                apparid["screenThread"].destroy(True)                
        if self._sound_thread is not None:
            self._sound_thread.join(2)
        #UNLOAD DLL
        if self._screen_module is not None:
            native.unload_libraries(self._screen_listlibs)
            self._screen_module=None;
        if self._sound_module is not None:
            native.unload_libraries(self._sound_listlibs)
            self._sound_module=None;
        self._debug_print("Term capture process.")


