# -*- coding: utf-8 -*-

'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''

import gdi


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
        wnd=e["window"]
        wnd.destroy()
        

def _test_window_action(e):
    if e["action"]==u"NOTIFYICON_ACTIVATE":
        e["source"].show()
        e["source"].to_front()
    elif e["action"]==u"NOTIFYICON_CONTEXTMENU":
        pp=gdi.PopupMenu()
        pp.set_show_position(gdi.POPUP_POSITION_TOPLEFT)
        pp.add_item("show","show")
        pp.add_item("disable","disable")
        pp.add_item("configure","configure")
        
        pp.set_action(_test_other_window);
        
        pp.show()
    elif e["action"]==u"ONCLOSE":
        #e["source"].hide()
        #e["cancel"]=True
        None    
        
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
    
    '''
    imp = ImagePanel()
    imp.set_position(250, 280)
    imp.set_filename(u"test.bmp")
    ww.add_component(imp)
    '''
    
    pl = gdi.Panel();
    pl.set_position(0, 0)
    pl.set_size(90,ww.get_height())
    pl.set_background_gradient("83e5ff", "FFFFFF", gdi.GRADIENT_DIRECTION_LEFTRIGHT)
    ww.add_component(pl)
   
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
   
    #ww.show_notifyicon(u"logo.ico",u"MSG LOGO")
   
    gdi.loop(ww,True)
    

            


