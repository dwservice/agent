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
import communication
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

CAPTURE_INTERVALL_SLOW_MODE = 10 

_libmap={}

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
        cp.cb_difference(sz, pdata)


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
            dm.terminate()
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
                    dm.terminate()
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
                        self._capture_process = CaptureProcess(self._agent_main)
                    itm = Manager(self, cinfo, key, wsock)
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
        
class SpeedManager():
    
    def __init__(self, dskmain):
        self._dskmain=dskmain
        self._frame_sent=0l
        self._frame_sent_size=0l
        self._frame_received=0l
        self._frame_distance=0l
        self._fps_counter=None
        self._fps_frame=0l
        self._fps=-1
        self._qa_check_frame=None
        self._qa_check_frame_size_avg=None
        self._qa_check_frame_size=None
        self._qa_check_frame_time=None
        self._qa_time_wait=0.0
        self._qa_time_counter=None
        self._qa_time_bytes=0l
        self._qa_detect=9
        
        
    def get_frame_sent(self):
        return self._frame_sent
    
    def get_qa_detect(self):
        return self._qa_detect
    
    def update_frame_size(self,w,h):        
        self._qa_check_frame_size_avg=long(((float(w*h*3)*10.0)/100.0))        
    
    def sent(self,fsize):
        self._frame_sent+=1l
        self._frame_sent_size=fsize
        if self._frame_sent==1l:
            self._qa_time_counter=communication.Counter()            
            self._qa_check_frame=self._frame_sent        
            self._qa_check_frame_size=fsize
            self._qa_check_frame_time=time.time()
        self._qa_time_bytes+=fsize
        
            
    def received(self, frec):
        self._frame_received=frec
        
        #CALCULATE FPS
        if self._fps_counter is None:
            self._fps_counter=communication.Counter()
            self._fps_frame=self._frame_received
        elif self._fps_counter.is_elapsed(1000):
            nf = self._frame_received-self._fps_frame
            self._fps = int((float(nf) * 1000.0)/float(self._fps_counter.get_value()))
            self._fps_frame=self._frame_received
            self._fps_counter.reset()
        
        #CALCULATE QA    
        if self._qa_check_frame is not None and self._qa_check_frame==frec:
            newqa=None
            elp=time.time()-self._qa_check_frame_time
            elp=((elp*(float(self._qa_check_frame_size_avg)/2))/float(self._qa_check_frame_size))
            if elp>=0:
                if elp<0.2:
                    newqa=9
                elif elp<0.3:
                    newqa=8
                elif elp<0.4:
                    newqa=7
                elif elp<0.5:
                    newqa=6
                elif elp<0.6:
                    newqa=5
                elif elp<0.7:
                    newqa=4
                elif elp<0.8:
                    newqa=3
                elif elp<0.9:
                    newqa=2
                elif elp<1.0:
                    newqa=1
                else:
                    newqa=0
            if newqa is not None:
                self._qa_detect=newqa
                #self._dskmain._agent_main.write_info("INITQA: " + str(self._qa_detect) + " - ELAPSED: " + str(elp) + " - FRAMESIZE:" + str(self._qa_check_frame_size))
            self._qa_check_frame=None
            self._qa_check_frame_time=None
            self._qa_time_counter.reset()
            self._qa_time_bytes=0l            
            self._qa_time_wait=0.0
   
            
            
    
    def wait_time(self, semre):
        while True:
            self._frame_distance=self._frame_sent-self._frame_received                        
            #self._dskmain._agent_main.write_info("DISTANCE: " + str(self._frame_distance) + " - FPS: " + str(self._fps) + " - FRAME: " + str(self._frame_sent) + " - QA: " + str(self._qa_detect))
            if self._frame_sent==1:
                bok = self._frame_sent==self._frame_received
            else:
                appfps = self._fps
                if appfps==-1:
                    appfps=self._qa_detect+3
                bok = self._frame_distance<=appfps                            
            if bok:
                break
            else:
                tmw = time.time()
                semre.wait(0.25)
                elw = time.time()-tmw
                if self._frame_sent>1:                                         
                    if elw>0:
                        self._qa_time_wait+=elw
        #DETECT QA                      
        if self._frame_sent>1 and self._qa_time_counter.is_elapsed(1000):
            autoqawaitint=int(self._qa_time_wait*1000)
            autoqawaitperc=int((float(autoqawaitint)/float(self._qa_time_counter.get_value()))*100.0)            
            if autoqawaitperc>=50.0:
                if self._qa_detect>0:
                    self._qa_detect-=1
                    #self._dskmain._agent_main.write_info("NEWQA: " + str(self._qa_detect) + " - WAIT: " + str(autoqawaitint) + " - PERC: " + str(autoqawaitperc) + " - BYTES: " + str(self._qa_time_bytes))
            elif self._qa_time_bytes>long(self._qa_check_frame_size_avg*(float(self._qa_time_counter.get_value()) / 1000.0)) and autoqawaitperc<=5.0:
                if self._qa_detect<9:
                    self._qa_detect+=1
                    #self._dskmain._agent_main.write_info("NEWQA: " + str(self._qa_detect) + " - WAIT: " + str(autoqawaitint) + " - PERC: " + str(autoqawaitperc) + " - BYTES: " + str(self._qa_time_bytes))
            self._qa_time_counter.reset()
            self._qa_time_bytes=0l
            self._qa_time_wait=0.0

class Manager(threading.Thread):
        
    def __init__(self, dskmain, cinfo, sid,  wsock):
        threading.Thread.__init__(self,  name="DesktopManager")
        self._dskmain=dskmain
        self._cinfo=cinfo
        prms = cinfo.get_permissions()
        if prms["fullAccess"]:
            self._allow_inputs=True
        else:
            pret=self._dskmain._agent_main.get_app_permission(cinfo,"desktop")
            if pret["fullAccess"]:
                    self._allow_inputs=True
            else:
                if "allowScreenInput" in pret:
                    self._allow_inputs=pret["allowScreenInput"]
                else:
                    self._allow_inputs=False
        
        self._prop=wsock.get_properties()
        self._idses=cinfo.get_idsession()
        self._id=sid
        self._bclose=False
        self._websocket=wsock
        self._artosend=[]
        self._artosendsize=0
        self._semaphore = threading.Condition()
        self._quality=-1
        
        self._frame_sent_size=None
        self._speed_manager = SpeedManager(self._dskmain)
        
        self._supported_frame=None
        self._frame_type=0 # 0=DATA_PALETTE_COMPRESS_V1; 100=DATA_TJPEG"
        self._send_frame_type=False        
        
        
        self._distanceFrameMs=10.0/1000.0
        self._distanceFrameMsCounter=communication.Counter()
        
                        
        self._websocket.accept(10,{"on_close": self._on_close,"on_data":self._on_data})
        self._semaphore_inputs = threading.Condition()
        #self._input_click_state=None
        #self._input_counter=communication.Counter()
        self._inputs = []
        self._cursor_visible = True
        self._slow_mode = False
        #self._cursor_last_token = None
        self._monitor = -1 
        self._monitor_count = 0
    
    def get_id(self):
        return self._id
    
    def get_idses(self):
        return self._idses
    
    def _on_data(self,websocket,tpdata,data):
        if not self._bclose:
            try:
                prprequest = json.loads(data.to_str("utf8"))
                if prprequest is not None and "frametime" in prprequest:
                    #print "frametime: " + prprequest["frametime"]
                    self._semaphore.acquire()
                    try:
                        self._speed_manager.received(long(prprequest["frametime"]))
                        self._semaphore.notify_all();
                    finally:
                        self._semaphore.release()
                if prprequest is not None and "inputs" in prprequest:
                    if not self._allow_inputs:
                        raise Exception("Permission denied (inputs).")
                    applist = prprequest["inputs"].split(";")
                    if len(applist)>0:
                        self._semaphore_inputs.acquire()
                        try:
                            self._inputs.extend(applist)
                        finally:
                            self._semaphore_inputs.release()
                        #print("_inputevents " +  self._id + ": " + str(long(time.time() * 1000)-apptm));                        
                if prprequest is not None and "cursor" in prprequest:
                    self._semaphore.acquire()
                    try:
                        if prprequest["cursor"]=="true":
                            self._cursor_visible=True
                        elif prprequest["cursor"]=="false":
                            self._cursor_visible=False
                    finally:
                        self._semaphore.release()
                if prprequest is not None and "monitor" in prprequest:
                    self._semaphore.acquire()
                    try:
                        self._monitor = int(prprequest["monitor"])
                        if prprequest is not None and "acceptFrameType" in prprequest:
                            arft = prprequest["acceptFrameType"].split(";")
                            if self._supported_frame is not None:
                                for f in range (len(self._supported_frame)):
                                    tf=self._supported_frame[f]                            
                                    for i in range(len(arft)):
                                        if int(arft[i])==tf:
                                            self._frame_type=tf
                                            self._send_frame_type=True
                                            break
                                    if self._send_frame_type==True:
                                        break
                            
                    finally:
                        self._semaphore.release()                        
                if prprequest is not None and "slow" in prprequest:
                    self._semaphore.acquire()
                    try:
                        if prprequest["slow"]=="true":
                            self._slow_mode=True
                        elif prprequest["slow"]=="false":
                            self._slow_mode=False
                        self._semaphore.notify_all();
                    finally:
                        self._semaphore.release()
                if prprequest is not None and "quality" in prprequest:
                    self._semaphore.acquire()
                    try:
                        self._quality=int(prprequest["quality"])
                    finally:
                        self._semaphore.release()
            except Exception as ex:
                self._bclose=True
                self._dskmain._agent_main.write_except(ex,"AppDesktop:: capture error" + self._id + " error:" + str(ex))
        
   
   
       
    def _on_token(self,sdata):
        if self._send_frame_type==True:
            self._send_frame_type=False
            self._websocket.send_bytes(utils.Bytes(struct.pack("!hh",801,self._frame_type)))
        
        tp = struct.unpack("!h",sdata[0:2])[0]
        self._semaphore.acquire()
        try:
            if tp==0: #Resolution
                arsz = struct.unpack("!hh",sdata[2:6])
                self._speed_manager.update_frame_size(arsz[0],arsz[1])
            elif tp==10: #TOKEN MONITOR AND SUPPORTED FRAME
                self._monitor_count = struct.unpack("!h",sdata[2:4])[0]
            elif tp==11: #SUPPORTED FRAME
                p=2
                cnt = struct.unpack("!h",sdata[p:p+2])[0]
                self._supported_frame=[]
                for i in range(cnt):
                    p+=2
                    self._supported_frame.append(struct.unpack("!h",sdata[p:p+2])[0])
            elif tp==1: #TOKEN DISTANCE FRAME
                self._distanceFrameMsCounter.reset()
                self._distanceFrameMs=struct.unpack("!i",sdata[2:6])[0]
                sdata=None
            elif tp==2: #TOKEN FRAME                
                if self._frame_sent_size==None:
                    self._frame_sent_size=len(sdata)
                    #print "inizio TOKEN #########################################"
                else:
                    self._frame_sent_size+=len(sdata)
                
                #if len(sdata)>=7:
                #    ar = struct.unpack("!bbbhh", sdata[0:7])
                #    print "LEN: " + str(len(sdata)) + " " + str(ar[3]) + " " + str(ar[4]) 
                        
                if sdata[2]==1:                    
                    #if self._frame_first_token==False:
                    #   print "#"
                    #   print "#"
                    self._speed_manager.sent(self._frame_sent_size)
                    self._websocket.send_bytes(utils.Bytes(struct.pack("!h",800)+str(self._speed_manager.get_frame_sent())))
                    self._frame_sent_size=None
                        
        finally:
            self._semaphore.release()
        if sdata is not None:
            self._websocket.send_bytes(sdata)
        
                        
                        
    def run(self):
        #last_diff_time=long(time.time() * 1000)
        cnt_retry=0 ##I tentativi servono quando l'utente si disconnette (Es. in windows)
        #INVIA ID
        sdataid=struct.pack("!h",900)+self._id;
        self._websocket.send_bytes(utils.Bytes(sdataid))
        lclose=self.is_close()
        curmon=-1
        max_retry=3
        frame_type=0
        quality_detect=self._speed_manager.get_qa_detect()
        quality_request=-1
        while not lclose:
            try:
                #print("_send_token_image WAIT time=" + str(long(time.time() * 1000)-apptmwait));
                self._inputevents()
                #last_diff_time=communication.get_time()                
                self._distanceFrameMsCounter.reset()
                appqa=quality_detect
                if quality_request>=0 and quality_request<=9:                    
                    appqa=quality_request                   
                self._dskmain._capture_process.difference(self, frame_type, appqa,curmon,self._on_token)
                max_retry=5;
                #print("_send_token_image _capture_process time=" + str(communication.get_time()-last_diff_time));
                
                self._semaphore.acquire()
                try:
                    if self._bclose:
                        lclose=True
                        break                    
                    self._speed_manager.wait_time(self._semaphore)                    
                    appwait=0
                    if self._slow_mode:
                        appwait=CAPTURE_INTERVALL_SLOW_MODE
                    else:
                        if not self._distanceFrameMsCounter.is_elapsed(self._distanceFrameMs):
                            appwait=float(self._distanceFrameMs-self._distanceFrameMsCounter.get_value()) / 1000.0                                                                    
                    if appwait>0.0:
                        #print("WAIT: " + str(appwait))
                        self._semaphore.wait(appwait)                                 
                    if self._monitor_count>0:                               
                        curmon=self._monitor
                    else:
                        curmon=-1
                    quality_request=self._quality
                    frame_type=self._frame_type
                    quality_detect = self._speed_manager.get_qa_detect()
                finally:
                    self._semaphore.release()
                cnt_retry=0
            except Exception as e:
                if not self.is_close():
                    if cnt_retry>=max_retry: #NUMERO TENTATITVI
                        try:
                            self._websocket.send_bytes(utils.Bytes(struct.pack("!h",999) + str(e)))
                            #TOKEN MONITOR = 0 NOT DETECTED
                            #self._websocket.send_bytes(struct.pack("!hh",10,0))
                        except Exception as ex:
                            None
                        self.terminate()
                        lclose=True
                        self._dskmain._agent_main.write_except(e,"Desktop capture error id:" + self._id)
                    else:
                        #token_empty=True
                        cnt_retry+=1
                        time.sleep(1)
                        self._dskmain._agent_main.write_err("Desktop capture retry " + str(cnt_retry) + " id:" + self._id + " error:" + str(e))
                        self._dskmain._agent_main.write_debug(str(e) + "\n" + traceback.format_exc());
                else:
                    lclose=True        
        if not self.is_close():
            self.terminate()
        self._destroy();
    
    '''   
    def _inputevents_is_valid_click_state(self,ar):
        if self._input_click_state is not None:
            x = int(ar[1]);
            y = int(ar[2]);
            time = long(ar[8])
            arstate=self._input_click_state["args"]
            xstate = int(arstate[1])
            ystate = int(arstate[2])
            timestate = int(arstate[8])
            elapsed=time-timestate
            return (x==xstate) and (y==ystate) and (elapsed>=0) and (elapsed<=200) 
        
        return False
    
    def _inputevents_fire_click_state_if_need(self):
        if self._input_click_state is not None:
            elapsed = long(time.time() * 1000)-self._input_click_state["time"]
            if (elapsed<0) or (elapsed>200):
                self._inputevents_fire_click_state()
    
    def _inputevents_fire_click_state(self):
        if self._input_click_state is not None:
            ar=self._input_click_state["args"]
            x = int(ar[1]);
            y = int(ar[2]);
            btn = int(ar[3])
            whl = int(ar[4])
            sctrl = ar[5]
            salt = ar[6]
            sshift = ar[7]
            self._dskmain._capture_process.mouse(self, x, y, btn, whl, sctrl=="true",salt=="true",sshift=="true")
            if ar[3]=="64":
                if self._input_click_state["state"]=="DOWN":
                    self._dskmain._capture_process.mouse(self, x, y, 1, whl, sctrl=="true",salt=="true",sshift=="true")
            self._input_click_state=None
    
    '''
    
    def _inputevents(self):
        bret=True
        try:
            applist = []
            self._semaphore_inputs.acquire()
            try:
                if len(self._inputs)>0:
                    applist=self._inputs
                    self._inputs=[]
            finally:
                self._semaphore_inputs.release()
                        
            bret=len(applist)>0
            
            '''
            if len(applist)>0:
                print("**********************************************")
                appl=long(time.time() * 1000)
                for i in range(len(applist)):
                    s = applist[i]
                    ar = s.split(",")
                    print("_inputevents " +  ar[0] + ": " + str(appl - long(ar[len(ar)-1])));
                print("**********************************************")
            applist=[]
            '''
            
            
            #INVIA EVENTI
            '''
            if len(applist)==0:
                bret=False
                self._inputevents_fire_click_state_if_need()
            '''
            for i in range(len(applist)):
                s = applist[i]
                ar = s.split(",")
                if ar[0]=='MOUSE':
                    x = int(ar[1]);
                    y = int(ar[2]);
                    btn = int(ar[3])
                    whl = int(ar[4])
                    sctrl = ar[5]
                    salt = ar[6]
                    sshift = ar[7]
                    scommand = "false"
                    if len(ar)==9:
                        scommand = ar[8]
                    
                    '''
                    #GESTIONE DOPPIO CLICK
                    bfireev=True
                    if (self._input_click_state==None):
                        if (btn==1):
                            self._input_click_state={}
                            self._input_click_state["state"]="DOWN"
                            self._input_click_state["args"]=ar
                            self._input_click_state["time"]=long(time.time() * 1000)
                            bfireev=False
                    else:
                        if self._input_click_state["state"]=='DOWN' and (btn==0) and self._inputevents_is_valid_click_state(ar):
                            if self._input_click_state["args"][3]=="1":
                                self._input_click_state["state"]="UP"
                                self._input_click_state["args"][3]="64"; #CLICK
                                self._input_click_state["args"][8]=ar[8]
                                self._input_click_state["time"]=long(time.time() * 1000)
                                bfireev=False
                            elif self._input_click_state["args"][3]=="64":
                                self._input_click_state["state"]="UP"
                                self._input_click_state["args"][3]="128"; #DBLCLICK
                                self._input_click_state["args"][8]=ar[8]
                                self._input_click_state["time"]=long(time.time() * 1000)
                                self._inputevents_fire_click_state();
                                bfireev=False
                            else:
                                self._inputevents_fire_click_state();
                        elif self._input_click_state["state"]=='UP' and (btn==1) and self._inputevents_is_valid_click_state(ar):
                            if self._input_click_state["args"][3]=="64":
                                self._input_click_state["state"]="DOWN"
                                self._input_click_state["args"][8]=ar[8]
                                self._input_click_state["time"]=long(time.time() * 1000)
                                bfireev=False
                            else:
                                self._inputevents_fire_click_state();
                        else:
                            self._inputevents_fire_click_state();
                    '''
                    
                    #print("_inputevents " + str(btn) + "  " + str(long(time.time() * 1000) - long(ar[len(ar)-1])))
                    
                    #if bfireev:
                    self._dskmain._capture_process.mouse(self, x, y, btn, whl, sctrl=="true",salt=="true",sshift=="true",scommand=="true")
                       
                     
                elif ar[0]=='KEYBOARD':
                    #self._inputevents_fire_click_state();
                    tp = ar[1]
                    code = ar[2]
                    sctrl = ar[3]
                    salt = ar[4]
                    sshift = ar[5]
                    scommand = "false"
                    if len(ar)==7:
                        scommand = ar[6]
                    self._dskmain._capture_process.keyboard(self, tp, code, sctrl=="true",salt=="true",sshift=="true",scommand=="true")
        except Exception as e:
            self._dskmain._agent_main.write_except(e,"AppDesktop:: inputevents error " + self._id + ":")
        return bret
                
    def _on_close(self):
        self.terminate();
    
    def copy_text(self):
        if not self._allow_inputs:
            raise Exception("Permission denied (inputs).")
        return self._dskmain._capture_process.copy_text(self);
    
    def paste_text(self,s):
        if not self._allow_inputs:
            raise Exception("Permission denied (inputs).")
        return self._dskmain._capture_process.paste_text(self,s);
    
    def terminate(self):
        self._semaphore.acquire()
        try:
            self._bclose=True
            self._semaphore.notify_all()
        finally:
            self._semaphore.release()
    
    def _destroy(self):
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
    
    def is_close(self):
        ret = True
        self._semaphore.acquire()
        try:
            ret=self._bclose
        finally:
            self._semaphore.release()
        return ret
               
       
class CaptureProcessStdRedirect(object):
    
    def __init__(self,lg,lv):
        self._logger = lg;
        self._level = lv;
        
    def write(self, data):
        for line in data.rstrip().splitlines():
            self._logger.log(self._level, line.rstrip())



class CaptureProcess():
    
    def __init__(self,agent_main):
        _libmap["captureprocess"]=self
        self._lastid=0
        self._bdestroy=False
        self._agent_main=agent_main
        self._osmodule=None
        self._listlibs=None
        self._semaphore = threading.Condition()
        self._sharedmem=None
        self._process=None
        self._ppid=None
        self._currentconsoleid=None
        self._listdm={}
        self._last_copy_text=""
    
    def destroy(self):
        self._semaphore.acquire()
        try:
            self._bdestroy=True
            if self._sharedmem!=None:
                self._destroy_internal()
        finally:
            self._semaphore.release() 
        #UNLOAD DLL
        if self._osmodule is not None:
            if self._agent_main is not None:
                self._agent_main.unload_lib("screencapture")
            else:
                native.unload_libraries(self._listlibs)
            self._osmodule=None;
    
    def _get_osmodule(self):
        if self._osmodule is None:
            if self._agent_main is not None:
                self._osmodule = self._agent_main.load_lib("screencapture")
            else:
                self._listlibs = native.load_libraries_with_deps("screencapture")
                self._osmodule = self._listlibs[0] 
        return self._osmodule
    
    def _init_process_demote(self,user_uid, user_gid):
        def set_ids():
            os.setgid(user_gid)
            os.setuid(user_uid)    
        return set_ids
    
    def _init_process(self):
        if self._bdestroy:
            raise Exception("Process destroyed.")
        iretry=0;
        while True:
            try:
                self._appconsoleid=None
                iretry+=1
                if agent.is_windows():
                    self._appconsoleid=self._get_osmodule().consoleSessionId();
                    if (self._get_osmodule().isWinXP()==1 or self._get_osmodule().isWin2003Server()==1) and self._appconsoleid>0:
                        self._get_osmodule().winStationConnectW()
                        time.sleep(1)
                        self._destroy_internal()
                    elif self._currentconsoleid!=None and self._appconsoleid!=self._currentconsoleid:
                        self._destroy_internal()
                elif agent.is_mac():
                    self._appconsoleid=self._get_osmodule().consoleUserId();
                    if self._currentconsoleid!=None and self._appconsoleid!=self._currentconsoleid:
                        self._destroy_internal()
                        time.sleep(1)
                
                if self._sharedmem==None:
                    self._sharedmem=sharedmem.Stream()
                    def fix_perm(fn):
                        if agent.is_mac() and self._appconsoleid!=None:
                            utils.path_change_owner(fn, self._appconsoleid, -1)
                            utils.path_change_permissions(fn, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP)
                    fname = self._sharedmem.create(fixperm=fix_perm)
                    #RUN PROCESS
                    #if utils.path_exists("apps" + utils.path_sep + "desktop.py"): ##MI SERVE IN SVILUPPO
                    #    import compileall
                    #    compileall.compile_file("apps" + utils.path_sep + "desktop.py")
                    if agent.is_windows():
                        runaselevatore=u"False"
                        if self._get_osmodule().isUserInAdminGroup()==1:
                            if self._get_osmodule().isRunAsAdmin()==1:
                                if self._get_osmodule().isProcessElevated()==1:
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
                        self._ppid = self._get_osmodule().startProcessAsUser(appcmd,pyhome)
                        self._currentconsoleid=self._get_osmodule().consoleSessionId();                        
                    elif agent.is_linux():
                        libenv = os.environ
                        if utils.path_exists("runtime"):
                            libenv["LD_LIBRARY_PATH"]=utils.path_absname("runtime/lib")
                        #for some distro linux command below don't works because missing runpy
                        #self._process=subprocess.Popen([sys.executable, u'-S', u'-m', u'agent' , u'app=desktop', unicode(fname), unicode(str(self._agent_main._agent_debug_mode)),u'linux'], env=libenv)
                        self._process=subprocess.Popen([sys.executable, u'agent.pyc', u'app=desktop', fname, str(self._agent_main._agent_debug_mode),u'linux'], env=libenv)
                        '''
                        stat -c%U /dev/tty2                        
                        if my_args is None: my_args = sys.argv[1:]
                        user_name, cwd = my_args[:2]
                        args = my_args[2:]
                        pw_record = pwd.getpwnam(user_name)
                        user_name      = pw_record.pw_name
                        user_home_dir  = pw_record.pw_dir
                        user_uid       = pw_record.pw_uid
                        user_gid       = pw_record.pw_gid
                        env = os.environ.copy()
                        env[ 'HOME'     ]  = user_home_dir
                        env[ 'LOGNAME'  ]  = user_name
                        env[ 'PWD'      ]  = cwd
                        env[ 'USER'     ]  = user_name
                        self._process=subprocess.Popen([sys.executable, u'agent.pyc', u'app=desktop', fname, str(self._agent_main._agent_debug_mode),u'linux'], env=libenv, preexec_fn=self._init_process_demote(1000, 1000))
                        '''
                        #GESTIRE IL RENICE
                    elif agent.is_mac():
                        self._ppid = self._agent_main.get_osmodule().exec_guilnc(self._appconsoleid,"desktop",[fname, str(self._agent_main._agent_debug_mode),u'mac'])
                        if self._ppid is not None:
                            self._currentconsoleid=self._appconsoleid
                            self._process = None
                        else:
                            self._currentconsoleid=None
                            libenv = os.environ
                            if utils.path_exists("runtime"):
                                libenv["DYLD_LIBRARY_PATH"]=utils.path_absname("runtime/lib")
                            #self._process=subprocess.Popen([sys.executable, u'agent.pyc', u'app=desktop', fname, str(self._agent_main._agent_debug_mode),u'mac'], env=libenv)
                            self._process=subprocess.Popen([sys.executable, u'-S', u'-m', u'agent' , u'app=desktop', unicode(fname), unicode(str(self._agent_main._agent_debug_mode)),u'mac'], env=libenv)
                            #GESTIRE IL RENICE
                    self._appconsoleid=None
                       
                    #Attende che il processo si attiva
                    bok=False
                    for i in range(10):
                        time.sleep(0.5)
                        if self._process!=None:
                            if self._process.poll() == None:
                                bok=True
                                break
                        elif self._ppid!=None:
                            if self._agent_main.get_osmodule().is_task_running(self._ppid):
                                bok=True
                                break
                        else:
                            break
                    if bok:
                        break
                    else:
                        raise Exception("Process not started.")
                else:
                    break
             
            except Exception as e:
                time.sleep(1)
                self._destroy_internal()
                if iretry>=3:
                    raise e
    
    def _destroy_internal(self):
        try:
            if self._sharedmem!=None:
                self._sharedmem.close()
        except Exception as e:
            self._agent_main.write_except(e)
        try:
            #Attende chiusura processo
            bok=False
            for i in range(6):
                if self._process!=None:
                    if not self._process.poll() == None:
                        bok=True
                        break
                elif self._ppid!=None:
                    if not self._agent_main.get_osmodule().is_task_running(self._ppid):
                        bok=True
                        break                
                else:
                    break
                time.sleep(0.5)
            if not bok:
                if self._process!=None:
                    self._process.kill()
                elif self._ppid!=None:
                    self._agent_main.get_osmodule().task_kill(self._ppid)
        except Exception as e:
            self._agent_main.write_except(e)
        self._sharedmem=None
        self._process=None
        self._ppid=None
        self._currentconsoleid=None
        self._listdm={}
        
    
    '''def _request(self,req,bdestroy=False):
        self._semaphore.acquire()
        try:
            try:
                self._init_process()
                self._sharedmem.write_token(req)
                resp = self._sharedmem.read_token()
                if resp==None:
                    raise Exception("Capture process closed.")
            except Exception as e:
                self._destroy_internal()
                raise e
            if bdestroy:
                self._destroy_internal()
            if resp=="K":
                return None
            if resp[0]=="K":
                return resp[1:]
            else:
                raise Exception(resp[1:])
        finally:
            self._semaphore.release() 
    '''
        
    def write_token(self,s):
        bts=utils.Bytes();
        bts.append_str(s, "utf8")
        self._sharedmem.write_token(bts)
        #self._sharedmem.write_token(s)
        
    def read_token(self):        
        return self._sharedmem.read_token()        
    
    def _request_async(self,req,bdestroy=False):
        self._semaphore.acquire()
        try:
            try:
                self._init_process()
                self.write_token(req)
                if bdestroy:
                    self._destroy_internal()
            except Exception as e:
                self._destroy_internal()
                raise e
        finally:
            self._semaphore.release()
     
    def _request(self,req,ontoken,bdestroy=False):
        self._semaphore.acquire()
        try:
            try:
                self._init_process()
                self.write_token(req)
                while True:
                    resp = self.read_token()
                    if self._bdestroy:
                        raise Exception("Process destroyed.")
                    if resp==None:
                        raise Exception("Capture process closed.")
                    if bdestroy:
                        self._destroy_internal()
                    if resp[0]==ord("K") or resp[0]==ord("T"):
                        apps = resp.new_buffer(1)
                        if len(apps)>0:
                            ontoken(apps)
                        if resp[0]==ord("T"):
                            break
                    else:
                        raise Exception(resp.new_buffer(1).to_str("utf8"))
            except Exception as e:
                self._destroy_internal()
                raise e
        finally:
            self._semaphore.release()
        
    def remove(self, dm):
        if dm in self._listdm:
            sid=self._listdm[dm]
            del self._listdm[dm] 
            self._request_async(u"TERMINATE:"+sid,len(self._listdm)==0)
    
    def get_id(self,dm):
        if dm not in self._listdm:
            self._lastid+=1;
            appid=str(self._lastid)
            #self._request("INITIALIZE:" + appid)
            self._listdm[dm]=appid
            #self._listdm[dm]=str(self._get_osmodule().initialize())
        return self._listdm[dm]
    
    def difference(self, dm, tp, qa, monitor, ontoken):
        sid=self.get_id(dm)
        sreq=[]
        sreq.append(u"DIFFERENCE:")
        sreq.append(sid)
        sreq.append(u";")
        sreq.append(str(tp))
        sreq.append(u";")
        sreq.append(str(qa))
        sreq.append(u";")
        sreq.append(str(monitor))
        self._request(u"".join(sreq),ontoken)
        '''
        sret = self._request("DIFFERENCE:" + sid + ";" + str(bps) + ";" + str(monitor))
        if sret==None:
            sret=""
        return sret
        '''
    
    def keyboard(self, dm, tp, code, ctrl, alt, shift, cmdkey) :
        sid=self.get_id(dm)
        bok = True;
        if agent.is_windows() and tp=="CTRLALTCANC":
            if self._get_osmodule().sas():
                bok = False
        if bok:
            apps=u"KEYBOARD:"+unicode(sid)+u";"+ unicode(tp) +u";"+unicode(code)+u";"+unicode(ctrl)+u";"+unicode(alt)+u";"+unicode(shift)+u";"+unicode(cmdkey)
            #print(apps)
            self._request_async(apps)
        
    
    def mouse(self, dm, x, y , btn, whl, ctrl, alt, shift, cmdkey) :
        sid=self.get_id(dm)
        apps=u"MOUSE:"+unicode(sid)+u";"+unicode(x)+u";"+unicode(y)+u";"+unicode(btn)+u";"+unicode(whl)+u";"+unicode(ctrl)+u";"+unicode(alt)+u";"+unicode(shift)+u";"+unicode(cmdkey)
        #print(apps)
        self._request_async(apps)
    
    
    def _on_token_copy_text(self,sdata):
        self._last_copy_text=unicode(base64.b64decode(sdata.to_str("utf8")).decode("utf8"))
        
    def copy_text(self, dm) :
        sid=self.get_id(dm)
        self._last_copy_text=""
        self._request(u"COPYTEXT:"+str(sid),self._on_token_copy_text)
        return self._last_copy_text
    
    def paste_text(self, dm, s) :
        sid=self.get_id(dm)
        if s is not None:
            self._request_async(u"PASTETEXT:"+str(sid)+u";"+base64.b64encode(s.encode("utf8")))
        
    
    def _enable_debug(self):
        self._get_osmodule().setCallbackDebug(cb_debug_print)
    
    def _debug_print(self,s):
        if self._dbgenable:
            print(s)
    
    '''
    def _difference(self, sid, bps):
        s=None
        pi=None
        ln=0
        try:
            pi=ctypes.POINTER(ctypes.c_char)()
            ln = self._get_osmodule().difference(sid,bps,ctypes.byref(pi))
            if ln>0:
                s=pi[0:ln];
            elif ln<0:
                raise Exception("Capture difference error.")
        finally:
            if pi: # and ln>0:
                self._get_osmodule().freeMemory(pi)
        return s        
    '''
            
    def _copy_text(self, sid):
        s=None
        pi=None
        try:
            pi=self._get_osmodule().copyText(sid)
            if pi:
                s = ctypes.wstring_at(pi)
        finally:
            if pi: # and ln>0:
                self._get_osmodule().freeMemory(pi)
        return s

    def _paste_text(self, sid,s):
        self._get_osmodule().pasteText(sid,ctypes.c_wchar_p(unicode(s)))

    def write_res_token(self, t, bts):
        if bts is not None:
            bts.insert_byte(0,ord(t))
        else:
            bts=utils.Bytes()
            bts.append_byte(ord(t))        
        self._sharedmem.write_token(bts)                

    def cb_debug_print(self, str):
        self._debug_print("DESKTOPNATIVE@" + str)

    def cb_difference(self, sz, pdata):
        if sz>0:
            self.write_res_token("K", utils.Bytes(pdata[0:sz]))
    
    def listen(self,fname,dbgenable):
        try:
            self._dbgenable=(dbgenable.upper()=="TRUE")
            if self._dbgenable==True:
                self._logger = logging.getLogger()
                hdlr = logging.handlers.RotatingFileHandler(u'captureprocess.log', 'a', 10000000, 3)
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
        
        libver = 0
        try:
            libver = self._get_osmodule().version()
        except:
            None            
        self._debug_print("Init capture process. (" + fname + ")")
        listids={}
        try:
            self._sharedmem=sharedmem.Stream()
            self._sharedmem.connect(fname)
            self._debug_print("Pronto ad accettare richieste")
            while not self._sharedmem.is_closed():
                bts = self.read_token()
                if bts==None:
                    #self._debug_print("########## Richiesta: NONE")
                    break
                srequest=bts.to_str('utf8')
                self._debug_print("Richiesta: " + srequest)
                ar = srequest.split(":")
                try:
                    if len(ar)==1 or len(ar)==2:
                        if len(ar)==2:
                            prms=ar[1].split(";")
                        if ar[0]==u"TERMINATE":
                            appid=int(prms[0]);
                            if appid in listids:
                                del listids[appid]
                                self._get_osmodule().term(appid)
                        elif ar[0]==u"DIFFERENCE":
                            appid=int(prms[0]);
                            tp=int(prms[1]);
                            qa=int(prms[2]);
                            monidx=int(prms[3]);
                            if appid not in listids:
                                self._get_osmodule().init(appid);
                                listids[appid]={"monitor": monidx};
                                self._get_osmodule().monitor(appid,monidx)
                            elif listids[appid]["monitor"]!=monidx:
                                self._get_osmodule().monitor(appid,monidx)
                            
                            self._get_osmodule().difference(appid,tp,qa,cb_difference)
                            self.write_res_token("T", None)
                        elif ar[0]==u"COPYTEXT":
                            apps = self._copy_text(int(prms[0]))
                            if apps is None:
                                self.write_res_token("T", None)
                            else:
                                bts = utils.Bytes()
                                bts.append_str(base64.b64encode(apps.encode("utf8")), "utf8")
                                self.write_res_token("T", bts)
                        elif ar[0]==u"PASTETEXT":
                            self._paste_text(int(prms[0]),base64.b64decode(prms[1]).decode("utf8"))
                        elif ar[0]==u"MOUSE":
                            if libver==0:
                                self._get_osmodule().inputMouse(int(prms[0]),int(prms[1]), int(prms[2]), int(prms[3]), int(prms[4]), prms[5]=="True", prms[6]=="True",prms[7]=="True")
                            else:
                                bcommand=False
                                if len(prms)==9:
                                    bcommand=(prms[8]=="True")
                                self._get_osmodule().inputMouse(int(prms[0]),int(prms[1]), int(prms[2]), int(prms[3]), int(prms[4]), prms[5]=="True", prms[6]=="True",prms[7]=="True",bcommand)
                        elif ar[0]==u"KEYBOARD":
                            if libver==0:
                                self._get_osmodule().inputKeyboard(int(prms[0]), str(prms[1]), str(prms[2]), prms[3]=="True", prms[4]=="True",prms[5]=="True")
                            else:
                                bcommand=False
                                if len(prms)==7:
                                    bcommand=(prms[6]=="True")
                                self._get_osmodule().inputKeyboard(int(prms[0]), str(prms[1]), str(prms[2]), prms[3]=="True", prms[4]=="True",prms[5]=="True",bcommand)
                        else:
                            bts = utils.Bytes()
                            bts.append_str(u"Request '" + srequest + u"' not found.", "utf8")
                            self.write_res_token("E", bts)
                    else:
                        raise Exception(u"Request '" + srequest + u"' is not valid.")
                except Exception as ex:
                    self._debug_print(traceback.format_exc());
                    bts = utils.Bytes()
                    bts.append_str(unicode(ex), "utf8")
                    self.write_res_token("E", bts )
        except Exception as ex:
            self._debug_print(traceback.format_exc());
        
        if self._sharedmem is not None:
            self._sharedmem.close()
        for appid in listids.keys():
            self._get_osmodule().term(appid)
        self._debug_print("Term capture process.")


