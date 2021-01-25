# -*- coding: utf-8 -*-

'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''

import gdi
import images
_NOTIFY_ICON={"visible":False, "obj":None}

def _test_notify(e):
    if _NOTIFY_ICON["visible"]:
        #_NOTIFY_ICON["obj"].update(images.get_image("monitor_red.bmp"),u"MSG LOGO")
        _NOTIFY_ICON["obj"].destroy()
        _NOTIFY_ICON["visible"]=False
        _NOTIFY_ICON["obj"]=None        
    else:         
        _NOTIFY_ICON["obj"] = gdi.NotifyIcon(images.get_image("monitor_green.bmp"),u"MSG LOGO")
        _NOTIFY_ICON["obj"].set_object("window",e["window"])
        _NOTIFY_ICON["obj"].set_action(_test_notify_action)
        _NOTIFY_ICON["visible"]=True
        

def _test_notify_action(e):
    if e["action"]==u"ACTIVATE":
        e["source"].get_object("window").show()
        e["source"].get_object("window").to_front()
    elif e["action"]==u"CONTEXTMENU":
        pp=gdi.PopupMenu()
        pp.add_item("show","show")
        pp.add_item("disable","disable")
        pp.add_item("configure","configure")        
        pp.set_action(_test_other_window);        
        pp.show()
    

def _test_other_window(e):
    prnt=None
    if "window" in e:
        prnt=e["window"]
    wwn = gdi.DialogMessage(gdi.DIALOGMESSAGE_ACTIONS_YESNO,gdi.DIALOGMESSAGE_LEVEL_WARN,prnt) 
    wwn.set_title("Title MsgBox")
    wwn.set_message(u"Test Message.\nThis is a test message. How are you?. " + str(e["action"]))
    wwn.show()

def _test_close_window(e):
    wnd=None
    if "window" in e:
        if _NOTIFY_ICON["visible"]:
            _NOTIFY_ICON["obj"].destroy()
            _NOTIFY_ICON["visible"]=False
            _NOTIFY_ICON["obj"]=None
        wnd=e["window"]
        wnd.destroy()
        

def _test_window_action(e):
    wnd=e["window"]
    if e["action"]==u"ONCLOSE":
        if _NOTIFY_ICON["visible"]:
            e["source"].hide()
            e["cancel"]=True
            
        
if __name__ == "__main__":
    ww = gdi.Window()
    ww.set_title(u"Title test")
    ww.set_action(_test_window_action);
    #ww.set_position(100, 100)
    ww.set_size(800, 500)
    ww.set_show_position(gdi.WINDOW_POSITION_CENTER_SCREEN)
   
    l = gdi.Label()
    l.set_position(250, 50)
    l.set_width(100)
    l.set_text("Host")
    ww.add_component(l)
    
    t = gdi.TextBox()
    t.set_position(350, 50)
    ww.add_component(t)    
    
    l = gdi.Label()
    l.set_position(250, 90)
    l.set_width(100)
    l.set_text("Port")
    ww.add_component(l)
    
    t = gdi.TextBox()
    t.set_position(350, 90)
    ww.add_component(t)    
    
    l = gdi.Label()
    l.set_position(250, 130)
    l.set_width(100)
    l.set_text("User")
    ww.add_component(l)
    
    t = gdi.TextBox()
    t.set_position(350, 130)
    ww.add_component(t)       

    
    rr = gdi.RadioButton()
    rr.set_text("Yes")
    rr.set_group("GRP1");
    rr.set_position(250, 170)
    ww.add_component(rr)
    
    rr = gdi.RadioButton()
    rr.set_text("No")
    rr.set_group("GRP1");
    rr.set_position(250, 210)
    rr.set_selected(True)
    ww.add_component(rr)
    
    pbr = gdi.ProgressBar()
    pbr.set_position(250, 250)
    pbr.set_percent(0.4)
    ww.add_component(pbr)
    
    pl = gdi.Panel();
    pl.set_position(0, 0)
    pl.set_size(90,ww.get_height())
    pl.set_background_gradient("83e5ff", "FFFFFF", gdi.GRADIENT_DIRECTION_LEFTRIGHT)
    ww.add_component(pl)
    
    imp = gdi.ImagePanel()
    imp.set_position(200, 280)
    imp.set_filename(images.get_image("logo32x32.bmp"))
    ww.add_component(imp)    
   
    pb = gdi.Panel();
    pb.set_position(0, ww.get_height()-55)
    pb.set_size(ww.get_width(),55)
    ww.add_component(pb)
    
    b1 = gdi.Button();
    b1.set_text("Message")
    b1.set_position(10, 10)
    b1.set_action(_test_other_window)
    pb.add_component(b1)   
    
    b2 = gdi.Button();
    b2.set_text("Close")
    b2.set_position(10+b1.get_width()+10, 10)
    b2.set_action(_test_close_window)
    pb.add_component(b2)    
    
    b3 = gdi.Button();
    b3.set_text("Notify")
    b3.set_position(10+b1.get_width()+10+b2.get_width()+10, 10)
    b3.set_action(_test_notify)
    pb.add_component(b3)

    ww.show()
    gdi.loop()
    

            


