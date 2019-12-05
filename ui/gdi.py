# -*- coding: utf-8 -*-

'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''

import ctypes
import _ctypes
import utils
import platform
import sys
import time
import threading
import struct
import messages
import images
import subprocess

WINDOW_TYPE_NORMAL=0
WINDOW_TYPE_NORMAL_NOT_RESIZABLE=1
WINDOW_TYPE_DIALOG=100
WINDOW_TYPE_POPUP=200
WINDOW_TYPE_TOOL=300

WINDOW_POSITION_CENTER_SCREEN=0

TEXT_ALIGN_LEFTMIDDLE=0
TEXT_ALIGN_LEFTTOP=1
TEXT_ALIGN_CENTERMIDDLE=10


DIALOGMESSAGE_ACTIONS_OK=0
DIALOGMESSAGE_ACTIONS_YESNO=10

DIALOGMESSAGE_LEVEL_INFO=0
DIALOGMESSAGE_LEVEL_WARN=1
DIALOGMESSAGE_LEVEL_ERROR=2

POPUP_POSITION_BOTTONRIGHT=0
POPUP_POSITION_BOTTONLEFT=1
POPUP_POSITION_TOPRIGHT=10
POPUP_POSITION_TOPLEFT=11

GRADIENT_DIRECTION_LEFTRIGHT=0;
GRADIENT_DIRECTION_RIGHTLEFT=1;
GRADIENT_DIRECTION_TOPBOTTOM=2;
GRADIENT_DIRECTION_BOTTONTOP=3;

_STYLE_WINDOW_BACKGROUND_COLOR="ffffff"
_STYLE_WINDOW_FOREGROUND_COLOR="000000"
_STYLE_COMPONENT_BACKGROUND_COLOR="d9d9d9"
_STYLE_COMPONENT_FOREGROUND_COLOR="000000"
_STYLE_COMPONENT_BORDER_COLOR="a0a0a0"
_STYLE_EDITOR_BACKGROUND_COLOR="ffffff"
_STYLE_EDITOR_FOREGROUND_COLOR="000000"
_STYLE_EDITOR_SELECTION_COLOR="c0c0c0"

_gdimap={}
_gdimap["root_window"]=None
_gdimap["windows"]={}
_gdimap["thread"]=None


def is_windows():
    return (platform.system().lower().find("window") > -1)

def is_linux():
    return (platform.system().lower().find("linux") > -1)

def is_mac():
    return (platform.system().lower().find("darwin") > -1)

def is_os_32bit():
    return not sys.maxsize > 2**32

def is_os_64bit():
    return sys.maxsize > 2**32

def is_windows_user_in_admin_group():
    if is_windows():
        return gdw_lib().isUserInAdminGroup()==1
    else:
        raise Exception("invalid os.")

def is_windows_run_as_admin():
    if is_windows():
        return gdw_lib().isRunAsAdmin()==1
    else:
        raise Exception("invalid os.")

def is_windows_process_elevated():
    return gdw_lib().isProcessElevated()==1

def is_windows_task_running(pid):
    bret=gdw_lib().isTaskRunning(pid);
    return bret==1

def to_unicode(s):
    if s is None:
        return u""
    if not isinstance(s, unicode):
        return s.decode("utf8")
    return s    

#GESTIONE CALLBACK
if is_windows() and not is_os_32bit():
    #Gestito cosi in quanto i BOOL nel return dalla callback non funziona bene (SU WIN 32 BIT NON SI AVVIA) 
    import ctypes.wintypes
    CMPFUNCREPAINT = ctypes.WINFUNCTYPE(ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int)
    CMPFUNCKEYBOARD = ctypes.WINFUNCTYPE(ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.wintypes.BOOL, ctypes.wintypes.BOOL, ctypes.wintypes.BOOL, ctypes.wintypes.BOOL)
    CMPFUNCMOUSE = ctypes.WINFUNCTYPE(ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p, ctypes.c_int, ctypes.c_int, ctypes.c_int)
    CMPFUNCWINDOW = ctypes.WINFUNCTYPE(ctypes.wintypes.BOOL,ctypes.c_int, ctypes.c_wchar_p)
    CMPFUNCTIMER = ctypes.WINFUNCTYPE(ctypes.c_void_p)
else:
    CMPFUNCREPAINT = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int)
    CMPFUNCKEYBOARD = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_bool, ctypes.c_bool, ctypes.c_bool, ctypes.c_bool)
    CMPFUNCMOUSE = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p, ctypes.c_int, ctypes.c_int, ctypes.c_int)
    CMPFUNCWINDOW = ctypes.CFUNCTYPE(ctypes.c_bool,ctypes.c_int, ctypes.c_wchar_p)
    CMPFUNCTIMER = ctypes.CFUNCTYPE(ctypes.c_void_p)

@CMPFUNCREPAINT 
def cb_func_repaint(wid,x,y,w,h):
    if wid in _gdimap["windows"]:
        #print("CALLBACK REPAINT: " + str(x) + " " + str(y) + " " + str(w) + " " + str(h))
        _gdimap["windows"][wid].on_paint(x,y,w,h);
       

@CMPFUNCKEYBOARD 
def cb_func_keyboard(wid,tp,c,shift,ctrl,alt,meta):
    if wid in _gdimap["windows"]:
        #print("CALLBACK KEYBOARD: " + tp + " " + c)
        _gdimap["windows"][wid].on_keyboard(tp,c,shift,ctrl,alt,meta);

@CMPFUNCMOUSE 
def cb_func_mouse(wid,tp,x,y,b):
    if wid in _gdimap["windows"]:
        #print("CALLBACK MOUSE: " + tp + " " + str(x) + " " + str(y) + " " + str(b))
        _gdimap["windows"][wid].on_mouse(tp,x,y,b);

@CMPFUNCWINDOW 
def cb_func_window(wid,tp):
    if wid in _gdimap["windows"]:
        #print("CALLBACK WINDOW: " + tp)
        return _gdimap["windows"][wid].on_window(tp)
    return True

@CMPFUNCTIMER 
def cb_func_timer():
    #print("CALLBACK TIMER: " + str(time.time()))
    _gdimap["scheduler"].execute()
    

def gdw_lib():
    if "gdwlib" in _gdimap:
        return _gdimap["gdwlib"]
    else:
        gdwlib=None
        namelib=None
        namelibinst=None
        pathlib=None
        if is_windows():
            namelib="dwaggdi.dll"
            pathlib="win"
            #Installer Mode
            if is_os_32bit():
                namelibinst="dwaggdi_x86_32.dll"
            elif is_os_64bit():
                namelibinst="dwaggdi_x86_64.dll"
        elif is_linux():
            namelib="dwaggdi.so"
            pathlib="linux"
            #Installer Mode
            if is_os_32bit():
                namelibinst="dwaggdi_x86_32.so"
            elif is_os_64bit():
                namelibinst="dwaggdi_x86_64.so"
        elif is_mac():
            namelib="dwaggdi.so"
            pathlib="mac"
            #Installer Mode
            if is_os_32bit():
                namelibinst="dwaggdi_x86_32.so"
            elif is_os_64bit():
                namelibinst="dwaggdi_x86_64.so"
        if not utils.path_exists(".srcmode"):
            if utils.path_exists(namelibinst): #Installer Mode
                gdwlib = ctypes.CDLL("." + utils.path_sep + namelibinst)
            elif utils.path_exists("native" + utils.path_sep + namelib):
                gdwlib = ctypes.CDLL("native" + utils.path_sep + namelib)
        else:
            gdwlib = ctypes.CDLL(".." + utils.path_sep + "make" + utils.path_sep + "native" + utils.path_sep + namelib)
        if gdwlib==None:
            raise Exception("Missing gdi library.")
        
        gdwlib.getClipboardText.restype = ctypes.c_wchar_p
        _gdimap["gdwlib"]=gdwlib
        return gdwlib 


def getRGBColor(s):
    return struct.unpack('BBB',s.decode('hex'))

def getHexColor(r,g,b):
    return struct.pack('BBB',r,g,b).encode('hex')

def getImageSize(fn):
    sz_array = (ctypes.c_int * 2)()
    gdw_lib().getImageSize(fn,sz_array)
    return {"width":sz_array[0], "height":sz_array[1]}

def _repaint_later(sid,x,y,w,h):
    _init_scheduler()
    return _gdimap["scheduler"].repaint_later(sid,x,y,w,h)

def _init_scheduler():
    if not "scheduler" in _gdimap:
        sched = Scheduler()
        _gdimap["scheduler"]=sched;
        
def add_scheduler(w,func,*args, **kargs):
    _init_scheduler()
    return _gdimap["scheduler"].add(w,func,*args,**kargs)
    
def delete_scheduler(itm):
    _init_scheduler()
    if itm is not None:
        _gdimap["scheduler"].delete(itm)


def init_window(win):
    if win._id is None:
        logo=win._logo_path
        if logo is None:
            if is_windows():
                logo=images.get_image(u"logo.ico")
            elif is_linux():
                logo=images.get_image(u"logo16x16.xpm") + u"\n" + images.get_image(u"logo32x32.xpm")
        win._id=gdw_lib().newWindow(win._type,win._x,win._y,win._w,win._h,logo)
        gdw_lib().setTitle(win._id,win._title)
        _gdimap["windows"][win._id]=win;
        if win._notifyicon_enable:
            gdw_lib().createNotifyIcon(win._id,win._notifyicon_path,win._notifyicon_tooltip)

def loop(rwin,show):
    _init_scheduler()
    gdwlib=gdw_lib();
    _gdimap["root_window"]=rwin;
    _gdimap["thread"]=threading.current_thread()
    gdwlib.setCallbackRepaint(cb_func_repaint)
    gdwlib.setCallbackKeyboard(cb_func_keyboard)
    gdwlib.setCallbackMouse(cb_func_mouse)
    gdwlib.setCallbackWindow(cb_func_window)
    gdwlib.setCallbackTimer(cb_func_timer)
    init_window(rwin)
    if show:
        rwin.show()
    gdwlib.loop()
    _gdimap["scheduler"].destroy()
    del _gdimap["scheduler"]
    if is_windows():
        _ctypes.FreeLibrary(gdwlib._handle)
    else:
        _ctypes.dlclose(gdwlib._handle)
    del gdwlib    


def get_time():
    if is_windows():
        return time.clock()
    else:
        return time.time()


class Scheduler():
    
    def __init__(self):
        self._semaphore = threading.Condition()
        self.daemon=True
        self._destroy=False
        self._list=[]
        self._repaint_list=[]
    
    def execute(self):
        to_exec=[]
        self._semaphore.acquire()
        try:
            new_list=[]
            for itm in self._list:
                cur_time=long(get_time() * 1000)
                elapsed = (cur_time - itm["time"])
                if elapsed>itm["wait"]:
                    to_exec.append(itm)
                else:
                    if elapsed<0:
                        itm["time"]=cur_time
                    new_list.append(itm)
            
            self._list=new_list;
        finally:
            self._semaphore.release() 
        #EXECUTE
        for itm in to_exec:
            itm["func"](*itm["args"],**itm["kargs"])
        #REPAINT
        self._semaphore.acquire()
        try:
            for itm in self._repaint_list:
                gdw_lib().repaint(itm["id"],itm["x"],itm["y"],itm["w"],itm["h"])
            self._repaint_list=[]
        finally:
            self._semaphore.release()
    
    def add(self,wt,func,*args, **kargs):
        itm=None
        self._semaphore.acquire()
        try:
            if self._destroy:
                return
            itm={"time": long(get_time() * 1000),"wait":wt*1000, "func":func, "args":args ,"kargs":kargs}
            self._list.append(itm)
        finally:
            self._semaphore.release()
        return itm    
    
    def delete(self,itm):
        self._semaphore.acquire()
        try:
            if self._destroy:
                return
            if itm in self._list: 
                self._list.remove(itm)
        finally:
            self._semaphore.release()
    
    def repaint_later(self,sid,x,y,w,h):
        self._semaphore.acquire()
        try:
            if self._destroy:
                return
            #Verifica se è già presente un repaint che lo contiene
            badd=True
            for itm in self._repaint_list:
                if sid==itm["id"]:
                    if x>=itm["x"] and y>=itm["y"] and x+w<=itm["x"]+itm["w"] and y+h<=itm["y"]+itm["h"]:
                        badd=False
                        break
            if badd:
                #Elimina i rettangoli contenuti
                newlist=[]
                for itm in self._repaint_list:
                    if sid==itm["id"]:
                        if not (itm["x"]>=x and itm["y"]>=y and itm["x"]+itm["w"]<=x+w and itm["y"]+itm["h"]<=y+h):
                            newlist.append(itm)
                    else:
                        newlist.append(itm)
                newlist.append({"id":sid,"x":x,"y":y,"w":w,"h":h})
                self._repaint_list=newlist;
        finally:
            self._semaphore.release()
    
    def destroy(self):
        self._semaphore.acquire()
        try:
            self._destroy=True
            self._repaint_list=[]
        finally:
            self._semaphore.release()
       

class Paint:
    def __init__(self,win,offx,offy,clipx,clipy,clipw,cliph):
        self._window=win
        self._offx=offx;
        self._offy=offy;
        self._clipx=clipx;
        self._clipy=clipy;
        self._clipw=clipw;
        self._cliph=cliph;
    
    def pen_color(self, col):
        rgb=getRGBColor(col.upper());
        gdw_lib().penColor(self._window._id,rgb[0],rgb[1],rgb[2])

    def fill_rectangle(self,x,y,w,h):
        gdw_lib().fillRectangle(self._window._id,self._offx+x,self._offy+y,w,h)
        
    def fill_ellipse(self,x,y,w,h):
        gdw_lib().fillEllipse(self._window._id,self._offx+x,self._offy+y,w,h)

    def draw_image_fromfile(self,fn,x,y,w,h):
        gdw_lib().drawImageFromFile(self._window._id,fn,self._offx+x,self._offy+y,w,h)                  
        
    def draw_ellipse(self,x,y,w,h):
        gdw_lib().drawEllipse(self._window._id,self._offx+x,self._offy+y,w,h)
        
    def draw_line(self,x1,y1,x2,y2):
        gdw_lib().drawLine(self._window._id,self._offx+x1,self._offy+y1,self._offx+x2,self._offy+y2)
    
    def get_text_height(self):
        return gdw_lib().getTextHeight(self._window._id);
    
    def get_text_width(self,s):
        return gdw_lib().getTextWidth(self._window._id,s);
    
    def get_image_size(self,fn):
        return getImageSize(fn)
            
    def draw_text(self,s,x,y):
        gdw_lib().drawText(self._window._id,s,self._offx+x,self._offy+y);
        
    def clip_rectangle(self,x,y,w,h):
        appx=self._offx+x
        appy=self._offy+y
        if appx<self._clipx:
            appx=self._clipx
        if appy<self._clipy:
            appy=self._clipy
        if appx+w>self._clipx+self._clipw:
            w=(self._clipx+self._clipw)-appx
        if appy+h>self._clipy+self._cliph:
            h=(self._clipy+self._cliph)-appy
        gdw_lib().clipRectangle(self._window._id,appx,appy,w,h)
    
    def clear_clip_rectangle(self):
        gdw_lib().clipRectangle(self._window._id,self._clipx,self._clipy,self._clipw,self._cliph)
    

class Window:
    def __init__(self,tp=WINDOW_TYPE_NORMAL_NOT_RESIZABLE,parentwin=None,logopath=None):
        self._id=None;
        self._type=tp
        self._top_windows=[]
        self._title="";
        self._x=0;
        self._y=0;
        self._w=300;
        self._h=200;
        self._logo_path=logopath;
        self._background=_STYLE_WINDOW_BACKGROUND_COLOR
        self._foreground=_STYLE_WINDOW_FOREGROUND_COLOR
        self._components=[]
        self._show=False
        self._activate=False
        self._disable=False
        self._focus_sequence_index_lost=None
        self._focus_sequence_index=None
        self._focus_sequence=[]
        self._mouse_enter_component=None
        self._notifyicon_enable=False
        self._notifyicon_path=None
        self._notifyicon_tooltip=None
        self._action=None
        self._parent_window=parentwin
        if self._parent_window is not None:
            self._parent_window._top_windows.append(self)
            self.set_title(parentwin.get_title())
    
    
    def _fire_action(self,e):
        if self._action is not None:
            e["source"]=self
            self._action(e)
    
    def set_action(self,f):
        self._action=f
        
    def get_action(self):
        return self._action
    
    def get_x(self):
        return self._x;
    
    def get_y(self):
        return self._y;
    
    def get_width(self):
        return self._w;
    
    def get_height(self):
        return self._h;
    
    def get_logo_path(self):
        return self._logo_path;
    
    def set_foreground(self,c):
        self._foreground=c
    
    def get_foreground(self):
        return self._foreground
    
    def set_background(self,c):
        self._background=c
    
    def get_background(self):
        return self._background    
    
    def set_title(self,t):
        self._title=to_unicode(t)
    
    def get_title(self):
        return self._title

    def set_show_position(self,p):
        if p==WINDOW_POSITION_CENTER_SCREEN:
            sz_array = (ctypes.c_int * 2)()
            gdw_lib().getScreenSize(sz_array)
            self._x=(int)(sz_array[0]/2)-(self._w/2)
            self._y=(int)(sz_array[1]/2)-(self._h/2)

    def set_position(self,x,y):
        self._x=x;
        self._y=y;
    
    def set_size(self,w,h):
        self._w=w
        self._h=h
    
    def get_mouse_enter_component(self):
        return self._mouse_enter_component
    
    def get_focus_component(self):
        if self._focus_sequence_index is not None and self._focus_sequence_index<=len(self._focus_sequence)-1:
            return self._focus_sequence[self._focus_sequence_index]
        return  None
    
    def _add_focus_sequence(self, c):
        self._focus_sequence.append(c);
     
    def add_component(self, c):
        c._window=self;
        self._components.append(c)
        self._add_focus_sequence(c)
    
    def get_components(self):
        return self._components
    
    def remove_component(self, crem):
        for c in self._components:
            if c==crem:
                if c._container:
                    c.remove_all_components()
                c._destroy()
                bchangefocus=False
                if self.get_focus_component()==c:
                    self._set_focus_component_byindex(None)
                self._components.remove(c)
                self._focus_sequence.remove(c)
                if bchangefocus:
                    self.next_focus_component()
                _repaint_later(self._id,c._x,c._y,c._w,c._h)
                break
    
    def get_all_components(self):
        return self._focus_sequence
    
    def repaint(self):
        if self._id is not None:
            _repaint_later(self._id,self._x,self._y,self._w,self._h)
    
    def destroy(self):
        if self._id is not None:
            if self._parent_window is not None and self._parent_window._id is not None:
                self._parent_window._disable=False
                self._parent_window._top_windows.remove(self)
            for w in self._top_windows:
                w.hide();
            gdw_lib().destroyWindow(self._id)
            del _gdimap["windows"][self._id]
            if self._parent_window is not None and self._parent_window._id is not None:
                if self._parent_window.is_show():
                    self._parent_window.to_front()
    
    def show_notifyicon(self,path,tooltip):
        if not self._notifyicon_enable:
            self._notifyicon_enable=True
            self._notifyicon_path=path
            self._notifyicon_tooltip=tooltip
            if self._id is not None:
                gdw_lib().createNotifyIcon(self._id,self._notifyicon_path,self._notifyicon_tooltip)
    
    def hide_notifyicon(self):
        if self._notifyicon_enable:
            self._notifyicon_enable=False
            if self._id is not None:
                gdw_lib().destroyNotifyIcon(self._id)
    
    def update_notifyicon(self,path,tooltip):
        self._notifyicon_path=path
        self._notifyicon_tooltip=tooltip
        if self._id is not None:
            gdw_lib().updateNotifyIcon(self._id,self._notifyicon_path,self._notifyicon_tooltip)
    
    def _show_later(self):
        init_window(self)
        gdw_lib().show(self._id,0)
        gdw_lib().toFront(self._id)
        self.on_show()
    
    def _hide_later(self):
        init_window(self)
        self.on_hide()
        gdw_lib().hide(self._id)
    
    def _to_front_later(self):
        init_window(self)
        gdw_lib().toFront(self._id)
        
    def is_show(self):
        return self._show
    
    def show(self):
        if not self._show:
            self._show=True
            if self._parent_window is not None:
                self._parent_window._disable=True
            if _gdimap["thread"]==threading.current_thread():
                self._show_later()
            else:
                add_scheduler(0,self._show_later) #CREA LA FINESTRA NEL THREAD GRAFICO
    
    def hide(self):
        if self._show:
            self._show=False
            if _gdimap["thread"]==threading.current_thread():
                self._hide_later()
            else:
                add_scheduler(0,self._hide_later) 
    
    def to_front(self):
        if _gdimap["thread"]==threading.current_thread():
            self._to_front_later()
        else:
            add_scheduler(0,self._to_front_later)
        
    def on_show(self):
        self._set_activate()
    
    def on_hide(self):
        self._set_inactivate()
    
    def _set_activate(self):
        if not self._activate:
            self._activate=True
            self.next_focus_component()
    
    def _set_inactivate(self):
        if self._activate:
            self._activate=False    
            self._focus_sequence_index_lost=self._focus_sequence_index
            self._set_focus_component_byindex(None,{"mode":"KEYBOARD"})
            self._set_mouse_enter_component(None, "", 0, 0, False)
    
    def _set_focus_component(self,c,e):
        if c is not None and c in self._focus_sequence:
            self._set_focus_component_byindex(self._focus_sequence.index(c),e)
        
    def _set_focus_component_byindex(self,idx,e):
        if self._focus_sequence_index==idx:
            return
        oldc=self.get_focus_component();
        self._focus_sequence_index=idx
        if oldc is not None:
            oldc.on_focus_lost(e)
            oldc.repaint()
        if self._focus_sequence_index is not None:
            if self._activate:
                self.get_focus_component().on_focus_get(e)
                self.get_focus_component().repaint()
            else:
                self._focus_sequence_index_lost=self._focus_sequence_index
            
    def next_focus_component(self):
        if self._focus_sequence_index_lost is not None:
            self._set_focus_component_byindex(self._focus_sequence_index_lost,{"mode":"KEYBOARD"})
            self._focus_sequence_index_lost=None
            return
        if self._focus_sequence_index is None:
            if len(self._components)>0:
                for c in self._focus_sequence:
                    if c.is_focusable() and c.is_enable():
                        self._set_focus_component(c,{"mode":"KEYBOARD"})
                        break 
        else:
            i=self._focus_sequence_index+1;
            while i!=self._focus_sequence_index:
                if i>(len(self._focus_sequence)-1):
                    i=0
                c=self._focus_sequence[i]
                if c.is_focusable() and c.is_enable():
                    self._set_focus_component_byindex(i,{"mode":"KEYBOARD"})
                    break
                i+=1

    def previous_focus_component(self):
        if self._focus_sequence_index is None:
            if len(self._components)>0:
                for c in reversed(self._focus_sequence):
                    if c.is_focusable() and c.is_enable():
                        self._set_focus_component(c,{"mode":"KEYBOARD"})
                        break 
        else:
            i=self._focus_sequence_index-1;
            while i!=self._focus_sequence_index:
                if i<0:
                    i=len(self._focus_sequence)-1
                c=self._focus_sequence[i]
                if c.is_focusable() and c.is_enable():
                    self._set_focus_component_byindex(i,{"mode":"KEYBOARD"})
                    break
                i-=1
    
    def _set_mouse_enter_component(self,c,tp,x,y,b):
        if self._mouse_enter_component==c:
            return
        if self._mouse_enter_component is not None:
            self._mouse_enter_component.on_mouse_leave({})
        self._mouse_enter_component=c;
        if self._mouse_enter_component is not None:
            self._mouse_enter_component.on_mouse_enter({})
    
    def _is_intersect(self,r1,r2):
        if r1["x"] < r2["x"] + r2["w"] and r2["x"] < r1["x"] + r1["w"] and r1["y"] < r2["y"] + r2["h"]:
            return r2["y"] < r1["y"] + r1["h"]
        return False
        
    
    def on_paint(self,x,y,w,h):
        if self._id is not None:
            rgb=getRGBColor(self._background);
            gdw_lib().penColor(self._id,rgb[0],rgb[1],rgb[2])
            gdw_lib().fillRectangle(self._id,x,y,w,h)
            #print str("*******************************")
            for c in self._components:
                self._on_paint_component(c,x,y,w,h,0,0)
                if c._container:
                    self._on_paint_container(c,x,y,w,h,0,0)
    
    def _on_paint_component(self,c,x,y,w,h,offx,offy):
        r1={"x":c._x+offx, "y":c._y+offy, "w":c._w, "h":c._h}
        r2={"x":x, "y":y, "w":w, "h":h}
        if self._is_intersect(r1,r2) :
            clipx=c._x+offx
            if x>c._x+offx:
                clipx=x
            clipw=c._w-(clipx-(c._x+offx))
            if clipw>(x+w)-clipx:
                clipw=(x+w)-clipx
            clipy=c._y+offy
            if y>c._y+offy:
                clipy=y
            cliph=c._h-(clipy-(c._y+offy))
            if cliph>(y+h)-clipy:
                cliph=(y+h)-clipy
            
            gdw_lib().clipRectangle(self._id,clipx,clipy,clipw,cliph)
            pobj=Paint(self,c._x+offx,c._y+offy,clipx,clipy,clipw,cliph)
            c.on_paint(pobj) #DA FARE GESTIRE INTERSEZIONE DARE CORDINATE CORRETTE
            gdw_lib().clearClipRectangle(self._id)
            #print str(c) + " " + str(c._x+offx) + " " + str(c._y+offy) + " CLIP:" + str(clipx) + " " + str(clipy) + " " + str(clipw) + " " + str(cliph)            
        
    def _on_paint_container(self,cnt,x,y,w,h,offx,offy):
        for c in cnt._components:
            self._on_paint_component(c,x,y,w,h,offx+cnt._x,offy+cnt._y)
            if c._container:
                self._on_paint_container(c,x,y,w,h,offx+cnt._x,offy+cnt._y)
    
    
    def on_keyboard(self,tp,c,shift,ctrl,alt,meta):
        if self._disable:
            return
        if self.get_focus_component() is not None:
            self.get_focus_component().on_keyboard(tp,c,shift,ctrl,alt,meta)

    
    def _on_mouse_component(self,c,tp,x,y,b,offx,offy):
        if x>=c._x+offx and y>=c._y+offy and x<c._x+offx+c._w and y<c._y+offy+c._h:
            self._set_mouse_enter_component(c, tp, x, y, b)
            c.on_mouse(tp,x-(c._x+offx),y-(c._y+offy),b)
            return True
        return False
    
    def _on_mouse_container(self,cnt,tp,x,y,b,offx,offy):
        for c in reversed(cnt._components):
            if c._container:
                if self._on_mouse_container(c,tp,x,y,b,offx+cnt._x,offy+cnt._y):
                    return True
                else:
                    if self._on_mouse_component(c,tp,x,y,b,offx+cnt._x,offy+cnt._y):
                        return True
            else:
                if self._on_mouse_component(c,tp,x,y,b,offx+cnt._x,offy+cnt._y):
                    return True
        return False
        
    def on_mouse(self,tp,x,y,b):
        if self._disable:
            return
        #VERIFICA FOCUS
        if tp=="BUTTON_DOWN":
            for c in reversed(self._focus_sequence):
                if c.is_focusable() and c.is_enable():
                    xy = c._get_win_pos()
                    if x>=xy[0] and y>=xy[1] and x<xy[0]+c._w and y<xy[1]+c._h:
                        self._set_focus_component(c,{"mode":"MOUSE","x":x-xy[0],"y":y-xy[1]})
                        break
        benter=False
        for c in reversed(self._components):
            if c._container:
                if self._on_mouse_container(c,tp,x,y,b,0,0):
                    benter=True
                    break
                else:
                    if self._on_mouse_component(c,tp,x,y,b,0,0):
                        benter=True
                        break
            else:       
                if self._on_mouse_component(c,tp,x,y,b,0,0):
                    benter=True
                    break
        if not benter:
            self._set_mouse_enter_component(None, tp, x, y, b)
    
    def on_window(self,tp):
        if tp=="ACTIVE":
            if not self._disable:
                self._set_activate()
            for w in self._top_windows:
                if w.is_show():
                    w.to_front()
        elif tp=="INACTIVE":
            self._set_inactivate()
        elif tp=="NOTIFYICON_ACTIVATE":
            self._fire_action({"action":"NOTIFYICON_ACTIVATE"})
        elif tp=="NOTIFYICON_CONTEXTMENU":
            self._fire_action({"action":"NOTIFYICON_CONTEXTMENU"})
        elif tp=="ONCLOSE":
            if not self._disable:
                e={"action":"ONCLOSE"};
                self._fire_action(e)
                if "cancel" in e and e["cancel"] == True:
                    return False
            else:
                return False
        return True
 
class DialogMessage(Window):
    
    def __init__(self,act,lv,parentwin=None):
        if parentwin is None:
            Window.__init__(self,WINDOW_TYPE_DIALOG,parentwin)
        else:
            if parentwin.is_show():
                Window.__init__(self,WINDOW_TYPE_TOOL,parentwin)
            else:
                Window.__init__(self,WINDOW_TYPE_DIALOG,parentwin)
        self._actions=act
        self._level=lv
        self._message=u""
        self._action=None        
        
        
        
    def get_message(self):
        return self._message

    def set_message(self, value):
        self._message = to_unicode(value)

    def _fire_action(self,e):
        Window._fire_action(self, e)
        self.destroy()
        
    def _ok_action(self,e):
        self._fire_action({"action":"DIALOG_OK"})
    
    def _yes_action(self,e):
        self._fire_action({"action":"DIALOG_YES"})
    
    def _no_action(self,e):
        self._fire_action({"action":"DIALOG_NO"})
    
    def show(self):
        gapLabel=6
        pnlLeftW=50
        pnlBottomH=55   
        
        self.set_size(300, 180);
        self.set_show_position(WINDOW_POSITION_CENTER_SCREEN)
        
        pnlLeft = Panel();
        pnlLeft.set_position(0, 0)
        pnlLeft.set_size(pnlLeftW,self.get_height())
        col="064f7e"
        if self._level==DIALOGMESSAGE_LEVEL_ERROR:
            col="a61515"
        elif self._level==DIALOGMESSAGE_LEVEL_WARN:
            col="d2d90c"
        pnlLeft.set_background_gradient(col, "FFFFFF", GRADIENT_DIRECTION_LEFTRIGHT)
        self.add_component(pnlLeft)
        
             
        lb = Label()
        lb.set_position(gapLabel+pnlLeftW, gapLabel)
        lb.set_size(self.get_width()-pnlLeft.get_width()-(gapLabel*2), self.get_height()-55-(gapLabel*2))
        lb.set_wordwrap(True)
        lb.set_text(self._message)
        self.add_component(lb)
        
        pnl = Panel();
        pnl.set_position(0, self.get_height()-pnlBottomH)
        pnl.set_size(self.get_width(),pnlBottomH)
        self.add_component(pnl)
        
        if self._actions==DIALOGMESSAGE_ACTIONS_YESNO:
            bty = Button();
            bty.set_position(int((self._w/2)-((bty._w*2)/2))-5, 10)
            bty.set_text(messages.get_message('yes'))
            bty.set_action(self._yes_action)
            pnl.add_component(bty)
            
            btn = Button();
            btn.set_position(bty._x+bty._w+10, 10)
            btn.set_text(messages.get_message('no'))
            btn.set_action(self._no_action)
            pnl.add_component(btn)
        else:
            bt = Button();
            bt.set_position(int((self._w/2)-(bt._w/2)), 10)
            bt.set_text(messages.get_message('ok'))
            bt.set_action(self._ok_action)
            pnl.add_component(bt)
        
        Window.show(self)                 
                

    def on_window(self, tp):
        if tp=="ONCLOSE":
            return False
        return Window.on_window(self, tp)
        

class PopupMenu(Window):
    
    def __init__(self):
        Window.__init__(self,WINDOW_TYPE_POPUP)
        self._w=110;
        self._h=30;
        self._show_position=POPUP_POSITION_BOTTONRIGHT
        self._action=None
        self._list=[]        
    
    def set_show_position(self,p):
        self._show_position=p
        
    def get_show_position(self,p):
        return self._show_position

    def _do_actions(self,e):
        self.destroy()
        if self._action is not None:
            self._action({"source":self, "action":e["source"].get_name()});
        
    
    def set_action(self,f):
        self._action=f
        
    def get_action(self):
        return self._action
    
    def show(self):
        self._h=len(self._list)*30+4
        
        sz_array = (ctypes.c_int * 2)()
        gdw_lib().getMousePosition(sz_array)
        
        if self._show_position==POPUP_POSITION_TOPLEFT:
            self._x=(int)(sz_array[0])-self._w
            self._y=(int)(sz_array[1])-self._h
        elif self._show_position==POPUP_POSITION_TOPRIGHT:
            self._x=(int)(sz_array[0])
            self._y=(int)(sz_array[1])-self._h
        elif self._show_position==POPUP_POSITION_BOTTONRIGHT:
            self._x=(int)(sz_array[0])
            self._y=(int)(sz_array[1])
        elif self._show_position==POPUP_POSITION_BOTTONLEFT:
            self._x=(int)(sz_array[0])-self._w
            self._y=(int)(sz_array[1])
        
        pnl = Panel()
        pnl.set_background("ffffff")
        pnl.set_border(BorderLine())
        pnl.set_position(0, 0)
        pnl.set_size(self._w, self._h)
        self.add_component(pnl)
        
        y=2
        for itm in self._list:
            lbl = Label()
            lbl.set_name(itm["key"])
            lbl.set_text(itm["label"])
            lbl.set_highlight(True)
            lbl.set_position(2, y)
            lbl.set_width(self._w-4)
            lbl.set_action(self._do_actions)
            pnl.add_component(lbl)
            y+=30
        
        Window.show(self)
    
    def add_item(self,k,l):
        self._list.append({"key": k, "label": l})
        
    def on_window(self, tp):
        if tp=="INACTIVE":
            self.destroy()
            return True
        return Window.on_window(self, tp)
    
   
class BorderLine:
    
    def __init__(self):
        None
        self._color=_STYLE_COMPONENT_BORDER_COLOR
        self.size_l=1
        self.size_t=1
        self.size_b=1
        self.size_r=1
    
    def set_color(self,c):
        self._color=c
    
    def get_color(self):
        return self.color
            
    def on_paint(self,c,pobj):
        pobj.pen_color(self._color)
        x=0
        y=0
        w=c._w
        h=c._h
        pobj.draw_line(0,0,0,c._h-1) #LEFT
        pobj.draw_line(0,0,c._w-1,0) #TOP       
        pobj.draw_line(c._w-1,0,c._w-1,c._h-1) #RIGHT 
        pobj.draw_line(0,c._h-1,c._w-1,c._h-1) #BOTTOM
        

class Component:
    
    def __init__(self):
        self._window=None
        self._x=0;
        self._y=0;
        self._w=0;
        self._h=0;
        self._background=_STYLE_COMPONENT_BACKGROUND_COLOR
        self._foreground=_STYLE_COMPONENT_FOREGROUND_COLOR
        self._name=None
        self._border=None
        self._opaque=True
        self._focusable=False
        self._parent=None
        self._container=False
        self._enable=True
        self._components=[]
        self._gradient_background_start=None
        self._gradient_background_end=None
        self._gradient_direction=None
    
    def _destroy(self):
        self._window=None
        
    def add_component(self, c):
        if self._container:
            c._window=self._window;
            c._parent=self;
            self._components.append(c)
            self._window._add_focus_sequence(c)
            c.repaint()
    
    def remove_component(self, crem):
        if self._container:
            for c in self._components:
                if c==crem:
                    if c._container:
                        c.remove_all_components()
                    c._destroy()
                    bchangefocus=False
                    if self._window.get_focus_component()==c:
                        self._window._set_focus_component_byindex(None)
                    self._components.remove(c)
                    self._window._focus_sequence.remove(c)
                    if bchangefocus:
                        self._window.next_focus_component()
                    xy=self._get_win_pos()
                    _repaint_later(self._window._id,c._x+xy[0],c._y+xy[1],c._w,c._h)
                    break
    
    def get_components(self):
        return self._components
    
    def remove_all_components(self):
        if self._container:
            while len(self._components)>0:
                c=self._components[0]
                if c._container:
                    c.remove_all_components()
                c._destroy()
                bchangefocus=False
                if self._window.get_focus_component()==c:
                        self._window._set_focus_component_byindex(None)
                self._components.remove(c)
                self._window._focus_sequence.remove(c)
                if bchangefocus:
                        self._window.next_focus_component()
                xy=self._get_win_pos()
                _repaint_later(self._window._id,c._x+xy[0],c._y+xy[1],c._w,c._h)
    
    def focus(self):
        if self._window:
            self._window._set_focus_component(self,{"mode":"KEYBOARD"})
    
    def get_name(self):
        return self._name
    
    def set_name(self,value):
        self._name=value
    
    def set_position(self,x,y):
        self._x=x;
        self._y=y;
        self.repaint_parent()
    
    def set_size(self,w,h):
        self._w=w;
        self._h=h;
        self.repaint_parent()
    
    def set_x(self,x):
        self._x=x;
        self.repaint_parent()
    
    def get_x(self):
        return self._x;
    
    def set_y(self,y):
        self._y=y;
        self.repaint_parent()
    
    def get_y(self):
        return self._y;
    
    def set_width(self,w):
        self._w=w;
        self.repaint_parent()
    
    def get_width(self):
        return self._w;
    
    def set_height(self,h):
        self._h=h;
        self.repaint_parent()
    
    def get_height(self):
        return self._h;
        
    def set_foreground(self,c):
        self._foreground=c
    
    def get_foreground(self):
        return self._foreground
    
    def set_background(self,c):
        self._background=c
        self.clear_background_gradient();
    
    def get_background(self):
        return self._background
    
    def set_background_gradient(self,cstart,cend,direction): #DA GESTIRE direction al momento fisso sinistra verso destra
        self._gradient_background_start=cstart
        self._gradient_background_end=cend
        self._gradient_direction=direction
        self.repaint()
        
    def is_background_gradient(self):
        return (self._gradient_background_start is not None and self._gradient_background_end is not None and self._gradient_direction is not None)
        
    def clear_background_gradient(self):
        self._gradient_background_start=None
        self._gradient_background_end=None
        self._gradient_direction=None
    
    def set_border(self,b):
        self._border=b;
    
    def get_border(self):
        return self._border;
    
    def set_enable(self,b):
        self._enable=b;
        self.repaint()
    
    def is_enable(self):
        return self._enable
        
    def set_opaque(self,b):
        self._opaque=b;
    
    def is_opaque(self):
        return self._opaque;    
    
    def is_focusable(self):
        return self._focusable
    
    def has_focus(self):
        if self._window:            
            return self._window.get_focus_component()==self
        else:
            return False
    
    def on_focus_get(self,e):
        None
    
    def on_focus_lost(self,e):
        None
    
    def on_mouse_enter(self,e):
        None
    
    def on_mouse_leave(self,e):
        None
        
    def _get_win_pos(self):
        x=self._x;
        y=self._y;
        if self._parent is not None:
            xy=self._parent._get_win_pos();
            return (xy[0]+x,xy[1]+y)
        else:
            return (x,y)
        
    def repaint_parent(self):
        if self._parent is not None and self._window._id is not None:
            #print "repaint_parent"
            self._parent.repaint()
        elif self._window is not None and self._window._id is not None:
            #print "repaint_parent"
            self._window.repaint()
            
    def repaint(self):
        if self._window is not None and self._window._id is not None:
            #print "repaint"
            xy=self._get_win_pos()
            _repaint_later(self._window._id,xy[0],xy[1],self._w,self._h);
    
    def repaint_area(self,x,y,w,h):
        if self._window is not None and self._window._id is not None:
            #print "repaint_area"
            xy=self._get_win_pos()
            _repaint_later(self._window._id,xy[0]+x,xy[1]+y,w,h);
    
    def _draw_background_gradient(self,pobj,x,y,w,h):
        rgbstart = getRGBColor(self._gradient_background_start);
        rgbend = getRGBColor(self._gradient_background_end);
        rstart=rgbstart[0]
        gstart=rgbstart[1]
        bstart=rgbstart[2]
        rend=rgbend[0]
        gend=rgbend[1]
        bend=rgbend[2]        
        if rstart>rend:
            app=rend
            rend=rstart
            rstart=app
        
        if gstart>gend:
            app=gend
            gend=gstart
            gstart=app
            
        if bstart>bend:
            app=bend
            bend=bstart
            bstart=app        
        if self._gradient_direction==GRADIENT_DIRECTION_LEFTRIGHT:
            rstep = float(rend-rstart)/float(w)
            gstep = float(gend-gstart)/float(w)
            bstep = float(bend-bstart)/float(w)
            for i in range(w):
                hexc=getHexColor(int(rstart),int(gstart),int(bstart))
                pobj.pen_color(hexc)
                pobj.draw_line(i,0,i,h-1)
                rstart+=rstep
                gstart+=gstep
                bstart+=bstep
        elif self._gradient_direction==GRADIENT_DIRECTION_TOPBOTTOM:
            rstep = float(rend-rstart)/float(h)
            gstep = float(gend-gstart)/float(h)
            bstep = float(bend-bstart)/float(h)
            for i in range(h):
                hexc=getHexColor(int(rstart),int(gstart),int(bstart))
                pobj.pen_color(hexc)
                pobj.draw_line(0,i,w-1,i)
                rstart+=rstep
                gstart+=gstep
                bstart+=bstep
        elif self._gradient_direction==GRADIENT_DIRECTION_BOTTONTOP:
            rstep = float(rend-rstart)/float(h)
            gstep = float(gend-gstart)/float(h)
            bstep = float(bend-bstart)/float(h)
            for i in reversed(range(h)):
                hexc=getHexColor(int(rstart),int(gstart),int(bstart))
                pobj.pen_color(hexc)
                pobj.draw_line(0,i,w-1,i)
                rstart+=rstep
                gstart+=gstep
                bstart+=bstep
    
    def on_paint(self,pobj):
        if self._opaque:
            if self.is_background_gradient():
                self._draw_background_gradient(pobj,0,0,self._w,self._h)
            else:
                pobj.pen_color(self._background)
                pobj.fill_rectangle(0, 0,self._w,self._h)
        if self._border is not None:
            self._border.on_paint(self,pobj) 
        pobj.pen_color(self._foreground)
    
    def on_keyboard(self,tp,c,shift,ctrl,alt,meta):
        if tp=="KEY":
            if c=="TAB":
                if shift:
                    self._window.previous_focus_component()
                else:
                    self._window.next_focus_component()
    
    def on_mouse(self,tp,x,y,b):
        None    
        #print "tp: " + tp + " - x: " + str(x) + " - y: " + str(y) + " - b: " + str(b) + "  " + str(self)

class Panel(Component):
    def __init__(self):
        Component.__init__(self)
        self._border=None;
        self._w=300;
        self._h=200;
        self._focusable=False
        self._opaque=True
        self._container=True
        
class Label(Component):
    
    def __init__(self):
        Component.__init__(self)
        self._background=_STYLE_EDITOR_BACKGROUND_COLOR
        self._foreground=_STYLE_EDITOR_FOREGROUND_COLOR
        self._border=None;
        self._w=150;
        self._h=30;
        self._focusable=False
        self._opaque=False
        self._text=u""
        self._wordwrap=False
        self._text_align=TEXT_ALIGN_LEFTMIDDLE
        self._highlight=False
        self._action=None
    
    def get_text(self):
        return self._text

    def set_text(self, value):
        self._text = to_unicode(value)
        self.repaint()
    
    def get_text_align(self):
        return self._text_align

    def set_text_align(self, value):
        self._text_align = value
        self.repaint()
    
    def set_action(self,f):
        self._action=f
        
    def get_action(self):
        return self._action
    
    def set_wordwrap(self,b):
        self._wordwrap=b
        
    def is_wordwrap(self):
        return self._wordwrap 

    def set_highlight(self,b):
        self._highlight=b
    
    def is_highlight(self):
        return self._highlight

    def on_mouse_enter(self,e):
        if self._enable and self._highlight:
            self.repaint()
    
    def on_mouse_leave(self,e):
        if self._enable and self._highlight:
            self.repaint()
    
    def on_paint(self,pobj):
        if self._enable:
            if self._highlight and self._window.get_mouse_enter_component()==self:
                pobj.pen_color("e2e9ed")
                pobj.fill_rectangle(0,0,self._w,self._h)
                if self._border is not None:
                    self._border.on_paint(self,pobj)     
            else:
                Component.on_paint(self, pobj)
        else:
            Component.on_paint(self, pobj)
        pobj.clip_rectangle(2,2,self._w-4,self._h-4)
        gapw=2;
        s = self._text 
        if s!=u"":
            pobj.pen_color(self._foreground)
            ar=[]
            if not self._wordwrap:
                ar = s.split(u"\n");
            else:
                appar = s.split(u"\n");
                for appsr in appar:
                    if appsr=="":
                        ar.append("")
                    else:
                        wordar = appsr.split(" ");
                        curs=u""
                        for wsr in wordar:
                            news=None
                            if curs==u"":
                                news=wsr
                            else:
                                news=curs + u" " + wsr
                            if pobj.get_text_width(news)>self._w-(gapw*2):
                                ar.append(curs)
                                curs=wsr
                            else:
                                curs=news
                        if curs!=u"":
                            ar.append(curs)
            th=pobj.get_text_height()*len(ar);
            ty=2;
            if self._text_align==TEXT_ALIGN_LEFTMIDDLE or self._text_align==TEXT_ALIGN_CENTERMIDDLE:
                ty=(self._h/2)-(th/2)
            for sr in ar:
                tx=gapw
                if self._text_align==TEXT_ALIGN_CENTERMIDDLE:
                    tx=((self._w-(gapw*2))/2)-(pobj.get_text_width(sr)/2)
                    if tx<gapw:
                        tx=gapw
                pobj.draw_text(sr,tx,ty);
                ty+=pobj.get_text_height()
        pobj.clear_clip_rectangle()

    def on_mouse(self,tp,x,y,b):
        if self.is_enable():
            if tp=="BUTTON_UP":
                if self._enable and self._action is not None:
                    self._action({"window":self._window, "source":self, "action":"CLICK"});
                    

class Button(Component):
    def __init__(self):
        Component.__init__(self)
        self._w=100;
        self._h=36;
        self._focusable=True
        self._opaque=True
        self._text=u""
        self._border=BorderLine();
        self._action=None
        
    
    def get_text(self):
        return self._text

    def set_text(self, value):
        self._text = to_unicode(value)
        self.repaint() 
    
    def set_action(self,f):
        self._action=f
        
    def get_action(self):
        return self._action
    
    def on_mouse_enter(self,e):
        if self._enable:
            self.repaint()
    
    def on_mouse_leave(self,e):
        if self._enable:
            self.repaint()

    def on_paint(self,pobj):
        if self._enable:
            if self._window.get_mouse_enter_component()==self:
                pobj.pen_color("e2e9ed")
                pobj.fill_rectangle(0,0,self._w,self._h)
                if self._border is not None:
                    self._border.on_paint(self,pobj)     
            else:
                Component.on_paint(self, pobj)
        else:
            Component.on_paint(self, pobj)
        pobj.clip_rectangle(2,2,self._w-4,self._h-4)
        s = self._text 
        if s!=u"":
            if self._enable:
                pobj.pen_color(self._foreground)
            else:
                pobj.pen_color("a0a0a0")
            tx=(self._w/2)-(pobj.get_text_width(s)/2)
            ty=(self._h/2)-(pobj.get_text_height()/2)
            pobj.draw_text(s,tx,ty);
        pobj.clear_clip_rectangle()
    
    def on_mouse(self,tp,x,y,b):
        if self.is_enable():
            if tp=="BUTTON_DOWN":
                self.focus()
            elif tp=="BUTTON_UP":
                if self._enable and self._action is not None:
                    self._action({"window":self._window, "source":self, "action":"PERFORMED"});
            

class RadioButton(Component):
    def __init__(self):
        Component.__init__(self)
        self._w=150;
        self._h=30;
        self._focusable=True
        self._opaque=False
        self._text=""
        self._border=None;
        self._selected=False
        self._group=None
        self._action=None
    
    def set_action(self,f):
        self._action=f
        
    def get_action(self):
        return self._action
    
    def get_text(self):
        return self._text

    def set_text(self, value):
        self._text = to_unicode(value)
        self.repaint() 
    
    def get_selected(self):
        return self._selected

    def set_selected(self, value):
        self._selected= value
        self.repaint_area(0,0,22,self._h)
    
    def get_group(self):
        return self._group

    def set_group(self, value):
        self._group= value

    def _repaint_check(self):
        self.repaint_area(0,0,22,self._h)
    
    '''def on_mouse_enter(self,e):
        if self._enable:
            self.repaint_area(0,0,22,self._h)
    
    def on_mouse_leave(self,e):
        if self._enable:
            self.repaint_area(0,0,22,self._h)'''

    def on_paint(self,pobj):
        Component.on_paint(self, pobj)
        pobj.clip_rectangle(2,2,self._w-4,self._h-4)
        #if self._window.get_mouse_enter_component()==self:
        #    pobj.pen_color("f8fbfd")
        #else:            
        pobj.pen_color(_STYLE_EDITOR_BACKGROUND_COLOR)
        rsz=18
        ty=(self._h/2)-(rsz/2)
        pobj.fill_ellipse(2,ty,rsz,rsz)
        pobj.pen_color(_STYLE_COMPONENT_BORDER_COLOR)
        pobj.draw_ellipse(2,ty,rsz,rsz)
        
        if self._selected:
            gap=8
            pobj.pen_color(_STYLE_EDITOR_FOREGROUND_COLOR)
            ty=(self._h/2)-((rsz-gap)/2)
            pobj.fill_ellipse(2+(gap/2),ty,rsz-gap,rsz-gap)
        
        s = self._text 
        if s!=u"":
            pobj.pen_color(self._foreground)
            ty=(self._h/2)-(pobj.get_text_height()/2)
            pobj.draw_text(s,rsz+10,ty);
        pobj.clear_clip_rectangle()
            
    def on_mouse(self,tp,x,y,b):
        if self.is_enable():
            if tp=="BUTTON_DOWN":
                self.focus()
                if not self._selected:
                    old_selected=None
                    if self._group is not None:
                        for c in self._window.get_all_components():
                            if isinstance(c, RadioButton):
                                if c._group is not None:
                                    if self._group==c._group:
                                        if c._selected:
                                            old_selected=c
                                            old_selected._selected=False
                                            old_selected._repaint_check()
                    self._selected=True
                    self._repaint_check()
                    if self._enable and self._action is not None:
                        self._action({"window":self._window, "source":self, "old_selected":old_selected});


class ProgressBar(Component):
    
    def __init__(self):
        Component.__init__(self)
        self._foreground="86a7d4"
        self._border=BorderLine();
        self._w=250;
        self._h=24;
        self._focusable=False
        self._opaque=True
        self._percent=0
    
    def get_percent(self):
        return self._percent

    def set_percent(self, value):
        self._percent = value
        self.repaint() 

    def on_paint(self,pobj):
        Component.on_paint(self, pobj)
        p=self._percent
        if p<0.0:
            p=0.0;
        elif p>1.0:
            p=1.0;
        if self._percent>0.0:
            pobj.pen_color(self._foreground)
            pw=int((self._w-4)*p)
            pobj.fill_rectangle(2,2,pw,self._h-4);

class ImagePanel(Component):
    
    def __init__(self):
        Component.__init__(self)
        self._filename=None
        self._w=250;
        self._h=100;
        self._focusable=False
        self._opaque=False
        
    
    def get_filename(self):
        return self._filename

    def set_filename(self, fn):
        self._filename = fn;
        self.repaint() 

    def on_paint(self,pobj):
        Component.on_paint(self, pobj)
        if self._filename is not None:
            if utils.path_exists(self._filename):
                pobj.draw_image_fromfile(self._filename,0,0,self._w,self._h);
                
class TextBox(Component):
    
    def __init__(self):
        Component.__init__(self)
        self._background=_STYLE_EDITOR_BACKGROUND_COLOR
        self._foreground=_STYLE_EDITOR_FOREGROUND_COLOR
        self._border=BorderLine();
        self._focusable=True
        self._w=200;
        self._h=30;
        self._text=u""
        self._cursor_position=0
        self._selection_start=0
        self._selection_end=0
        self._blink=False
        self._blinkitm=None
        self._password_mask=False
        self._validate=None
        self._cursor_x=-1
        self._text_offx=0
    
    def _stop_blink(self):
        delete_scheduler(self._blinkitm);
        self._blinkitm = None
        self._blink=False
        self._repaint_cursor()
    
    def _start_blink(self):
        if self.has_focus():
            self._blink = not self._blink
            self._repaint_cursor()
            self._blinkitm = add_scheduler(0.5, self._start_blink);
        else:
            self._stop_blink()
    
    def set_password_mask(self,value):
        self._password_mask=value
    
    def is_password_mask(self):
        return self._password_mask
   
    def set_validate(self,value):
        self._validate=value
    
    def get_validate(self):
        return self._validate
   
    def get_text(self):
        return self._text

    def set_text(self, value):
        self._text = to_unicode(value)
        self._cursor_position=len(self._text)
        self._selection_start=self._cursor_position
        self._selection_end=self._cursor_position
        self.repaint()
              
    def on_focus_get(self,e):
        if e["mode"]=="KEYBOARD":
            self._selection_start=len(self._text)
            self._selection_end=len(self._text)
            self._cursor_position=self._selection_end
        delete_scheduler(self._blinkitm);
        self._blink=False
        self._start_blink()
    
    def on_focus_lost(self,e):
        if self._validate is not None:
            self._validate({"window":self._window, "source": self})
        self._cursor_position=0
        self._selection_start=0
        self._selection_end=0
        self._stop_blink()
    
    def _get_cursor_pos_by_x(self,x):
        x=x
        xi=2
        xf=2
        for i in range(len(self._text)):
            s=self._text[0:i]
            if len(s)!=0:
                xf = gdw_lib().getTextWidth(self._window._id,s)+2-self._text_offx
                if x>=xi and x<=xf:
                    return i-1
                xi=xf
        if len(self._text)!=0:
            xf = gdw_lib().getTextWidth(self._window._id,self._text)+2-self._text_offx
            if x>=xi and x<=xf:
                return len(self._text)-1
        return len(self._text)
    
    '''def on_mouse_enter(self,e):
        self.repaint()
    
    def on_mouse_leave(self,e):
        self.repaint()'''
    
    def _repaint_text_area(self):
        self.repaint_area(1, 1, self._w-1, self._h-1)
    
    def _repaint_cursor(self):
        if self._cursor_x!=-1:
            self.repaint_area(self._cursor_x-self._text_offx, 0, 1, self._h)
    
    def on_paint(self,pobj):
        #if self._window.get_mouse_enter_component()==self:
        #    pobj.pen_color("f8fbfd")
        #    pobj.fill_rectangle(x,y,w,h)
        #    if self._border is not None:
        #        self._border.on_paint(self,pobj)     
        #else:
        Component.on_paint(self, pobj)
        pobj.clip_rectangle(2,2,self._w-4,self._h-4)
        s = self._text
        if self._password_mask:
            s=u"*" * len(s)
        self._cursor_x = 2
        if s!=u"":
            wtx=pobj.get_text_width(s)
            #CALCOLA CURSORE
            self._cursor_x += pobj.get_text_width(s[0:self._cursor_position])
            if wtx>self._w-4:
                if self._cursor_x-self._text_offx>self._w-4:
                    self._text_offx=self._cursor_x-(self._w-4)+int(self._w/3)
                elif self._cursor_x-self._text_offx<2:
                    self._text_offx=self._cursor_x-int(self._w/3)
                if self._text_offx>(wtx+2)-(self._w-4):
                    self._text_offx=(wtx+2)-(self._w-4)
                if self._text_offx<0:
                    self._text_offx=0            
            else:
                self._text_offx=0
            #SELECTION
            if self._selection_end>self._selection_start:
                xstart=pobj.get_text_width(s[0:self._selection_start])
                xend=pobj.get_text_width(s[0:self._selection_end])
                pobj.pen_color(_STYLE_EDITOR_SELECTION_COLOR)
                pobj.fill_rectangle(2+xstart-self._text_offx,3,(xend-xstart),self._h-(2*3));
            #TESTO
            pobj.pen_color(self._foreground)
            ty=(self._h/2)-(pobj.get_text_height()/2)
            pobj.draw_text(s,2-self._text_offx,ty);
        else:
            self._text_offx=0
        if self._blink:
            pobj.pen_color(self._foreground)
            pobj.draw_line(self._cursor_x-self._text_offx,3,self._cursor_x-self._text_offx,self._h-3)
        pobj.clear_clip_rectangle();
        
    
    def _on_keyboard_char(self,c,shift,ctrl,alt,meta):
        if self._selection_start!=self._selection_end:
            self._text=self._text[0:self._selection_start] + self._text[self._selection_end:]
            self._cursor_position=self._selection_start
        self._text=self._text[0:self._cursor_position] + unicode(c) + self._text[self._cursor_position:]
        self._cursor_position+=len(unicode(c))
        self._selection_start=self._cursor_position
        self._selection_end=self._cursor_position
        self._blink=True
        self._repaint_text_area()
        
    def _on_keyboard_key(self,c,shift,ctrl,alt,meta):
        if c=="BACKSPACE":
            if self._selection_start==self._selection_end: 
                if self._cursor_position>0:
                    self._text=self._text[0:self._cursor_position-1] + self._text[self._cursor_position:]
                    self._cursor_position-=1
            else:
                self._text=self._text[0:self._selection_start] + self._text[self._selection_end:]
                self._cursor_position=self._selection_start
            self._selection_start=self._cursor_position
            self._selection_end=self._cursor_position
            self._blink=True
            self._repaint_text_area()
        elif c=="DELETE":
            if self._selection_start==self._selection_end:
                if self._cursor_position<len(self._text):
                    self._text=self._text[0:self._cursor_position] + self._text[self._cursor_position+1:]
            else:
                self._text=self._text[0:self._selection_start] + self._text[self._selection_end:]
                self._cursor_position=self._selection_start
            self._selection_start=self._cursor_position
            self._selection_end=self._cursor_position
            self._blink=True
            self._repaint_text_area()
        elif c=="LEFT":
            if self._cursor_position>0:
                if shift and self._cursor_position==self._selection_start:
                    self._cursor_position-=1
                    self._selection_start=self._cursor_position
                elif shift and self._cursor_position==self._selection_end:
                    self._cursor_position-=1
                    self._selection_end=self._cursor_position
                else:
                    self._cursor_position-=1
                    self._selection_start=self._cursor_position
                    self._selection_end=self._cursor_position
            elif not shift :
                self._selection_start=self._cursor_position
                self._selection_end=self._cursor_position
            self._blink=True
            self._repaint_text_area()
        elif c=="RIGHT":
            if self._cursor_position<len(self._text):
                if shift and self._cursor_position==self._selection_end:
                    self._cursor_position+=1
                    self._selection_end=self._cursor_position
                elif shift and self._cursor_position==self._selection_start:
                    self._cursor_position+=1
                    self._selection_start=self._cursor_position
                else:
                    self._cursor_position+=1
                    self._selection_start=self._cursor_position
                    self._selection_end=self._cursor_position
            elif not shift :
                self._selection_start=self._cursor_position
                self._selection_end=self._cursor_position
            self._blink=True
            self._repaint_text_area()
        elif c=="HOME":
            if self._cursor_position>0:
                if shift and self._cursor_position==self._selection_start:
                    self._cursor_position=0
                    self._selection_start=0
                elif shift and self._cursor_position==self._selection_end:
                    self._cursor_position=0
                    self._selection_end=self._selection_start
                    self._selection_start=0                        
                else:
                    self._cursor_position=0
                    self._selection_start=self._cursor_position
                    self._selection_end=self._cursor_position
            elif not shift :
                self._selection_start=self._cursor_position
                self._selection_end=self._cursor_position
            self._blink=True
            self._repaint_text_area()
        elif c=="END":
            if self._cursor_position<len(self._text):
                if shift and self._cursor_position==self._selection_end:
                    self._cursor_position=len(self._text)
                    self._selection_end=self._cursor_position
                elif shift and self._cursor_position==self._selection_start:
                    self._cursor_position=len(self._text)
                    self._selection_start=self._selection_end
                    self._selection_end=self._cursor_position
                else:
                    self._cursor_position=len(self._text)
                    self._selection_start=self._cursor_position
                    self._selection_end=self._cursor_position
            elif not shift :
                self._selection_start=self._cursor_position
                self._selection_end=self._cursor_position
            self._blink=True
            self._repaint_text_area()

    def _on_keyboard_command(self,c,shift,ctrl,alt,meta):
        if c=="COPY":
            s=self._text[self._selection_start:self._selection_end]
            if len(s)>0:
                gdw_lib().setClipboardText(s)  
        elif c=="CUT":
            s=self._text[self._selection_start:self._selection_end]
            if len(s)>0:
                gdw_lib().setClipboardText(s) 
            self._on_keyboard_key("DELETE",shift,ctrl,alt,meta)
        elif c=="PASTE":
            s=gdw_lib().getClipboardText()
            if len(s)>0:
                self._on_keyboard_char(s,shift,ctrl,alt,meta) 

    def on_keyboard(self,tp,c,shift,ctrl,alt,meta):
        Component.on_keyboard(self,tp,c,shift,ctrl,alt,meta)
        if tp=="CHAR":
            self._on_keyboard_char(c,shift,ctrl,alt,meta)
        elif tp=="KEY":
            self._on_keyboard_key(c,shift,ctrl,alt,meta)
        elif tp=="COMMAND":
            self._on_keyboard_command(c,shift,ctrl,alt,meta)
            
               
    def on_mouse(self,tp,x,y,b):
        if tp=="BUTTON_DOWN":
            self._cursor_position=self._get_cursor_pos_by_x(x)
            self._selection_start=self._cursor_position
            self._selection_end=self._cursor_position
            self.repaint()


