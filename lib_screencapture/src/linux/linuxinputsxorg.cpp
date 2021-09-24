
/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/
#if defined OS_XORG

#include "linuxinputsxorg.h"


LinuxInputs::LinuxInputs(){
	xdpy=NULL;
	root=0;
	mousebtn1Down=false;
	mousebtn2Down=false;
	mousebtn3Down=false;
	ctrlDown=false;
	altDown=false;
	shiftDown=false;
	max_grp=4;
	kccustom=0;
	kccustominit=false;
	//std::thread td(&detectKeyboardChanged, this);
    //td.detach();
}

LinuxInputs::~LinuxInputs(){
	clearCustomKeyUnicode();
	unloadKeyMap();
}

void LinuxInputs::setDisplay(Display *d, Window r){
	unloadKeyMap();
	xdpy=d;
	root=r;
	loadKeyMap();
}

void LinuxInputs::keyboardChanged(){
	if (skipKeyboardChangedCounter.getCounter()>=1000){
		clearCustomKeyUnicode();
		unloadKeyMap();
		loadKeyMap();
	}
}

void LinuxInputs::keyboard(const char* type,const char* key, bool ctrl, bool alt, bool shift, bool command){
	if (xdpy != NULL) {
		if (strcmp(type,"CHAR")==0){
			int uc = atoi(key);
			//Legge lo stato della tastiera
			XkbStateRec kbstate;
			XkbGetState(xdpy, XkbUseCoreKbd, &kbstate);
			int curg=kbstate.group;
			KeyCode kc = 0;
			int md = 0;
			//Cerca il symbolo nella tastiera
			map<int,KEYMAP*>::iterator itmap = hmUnicodeMap.find(uc);
			KEYMAP* keyMap;
			if (itmap!=hmUnicodeMap.end()){ //NON ESISTE
				keyMap=itmap->second;
				//Verifica il keycode per il gruppo corrente
				kc=keyMap[curg].code;
				md=keyMap[curg].modifier;
				//Verifica il keycode per gli altri gruppi
				if (kc==0){
					for (int g=0;g<max_grp;g++){
						if (keyMap[g].code!=0){
							curg=g;
							kc = keyMap[curg].code;
							md = keyMap[curg].modifier;
							break;
						}
					}
				}
			}
			if (kc==0){
				kc=createCustomKeyUnicode(uc);
				md=0;
				curg=0;
			}
			//Simula il tasto
			if (kc!=0){
				//Cambia gruppo
				if (curg!=kbstate.group){
					XkbLockGroup(xdpy, XkbUseCoreKbd, curg);
				}

				//Imposta modifiers
				if (md!=kbstate.locked_mods){
					XkbLockModifiers(xdpy,XkbUseCoreKbd,255,md);
				}

				XTestFakeKeyEvent(xdpy, kc, True, CurrentTime);
				XTestFakeKeyEvent(xdpy, kc, False, CurrentTime);

				//Ripristina gruppo
				if (curg!=kbstate.group){
					XkbLockGroup(xdpy, XkbUseCoreKbd, kbstate.group);
				}

				//Ripristina modifiers
				if (md!=kbstate.locked_mods){
					XkbLockModifiers(xdpy,XkbUseCoreKbd,255,kbstate.locked_mods);
				}
				XFlush(xdpy);
			}
		}else if (strcmp(type,"KEY")==0){
			KeySym ks = getKeySym(key);
			if (ks!=0){
				KeyCode kc = XKeysymToKeycode(xdpy, ks);
				if (kc!=0){
					ctrlaltshift(ctrl,alt,shift);
					XTestFakeKeyEvent(xdpy, kc, True, CurrentTime);
					XTestFakeKeyEvent(xdpy, kc, False, CurrentTime);
					ctrlaltshift(false,false,false);
					XFlush(xdpy);
				}
			}
		}else if (strcmp(type,"CTRLALTCANC")==0){

		}
	}
}

void LinuxInputs::mouse(MONITORS_INFO_ITEM* moninfoitem, int x, int y, int button, int wheel, bool ctrl, bool alt, bool shift, bool command){
	if (xdpy != NULL) {
		ctrlaltshift(ctrl,alt,shift);
		if ((x!=-1) && (y!=-1)){
			int mx=x;
			int my=y;
			if (moninfoitem!=NULL){
				mx=mx+moninfoitem->x;
				my=my+moninfoitem->y;
			}
			mouseMove(mx,my);
		}
		if (button==64) { //CLICK
			mouseButton(Button1, true);
			mouseButton(Button1, false);
		}else if (button==128) { //DBLCLICK
			mouseButton(Button1, true);
			mouseButton(Button1, false);

			//microsleep
			double milliseconds=200;
			struct timespec sleepytime;
			sleepytime.tv_sec = milliseconds / 1000;
			sleepytime.tv_nsec = (milliseconds - (sleepytime.tv_sec * 1000)) * 1000000;
			nanosleep(&sleepytime, NULL);

			mouseButton(Button1, true);
			mouseButton(Button1, false);
		}else if (button!=-1) {
			int appbtn=-1;
			if ((button & 1) && (!mousebtn1Down)){
				appbtn=Button1;
				mousebtn1Down=true;
			}else if (mousebtn1Down){
				appbtn=Button1;
				mousebtn1Down=false;
			}
			if (appbtn!=-1){
				mouseButton(appbtn, mousebtn1Down);
			}
			appbtn=-1;
			if ((button & 2) && (!mousebtn2Down)){
				appbtn=Button3;
				mousebtn2Down=true;
			}else if (mousebtn2Down){
				appbtn=Button3;
				mousebtn2Down=false;
			}
			if (appbtn!=-1){
				mouseButton(appbtn, mousebtn2Down);
			}
			appbtn=-1;
			if ((button & 4) && (!mousebtn3Down)){
				appbtn=Button2;
				mousebtn3Down=true;
			}else if (mousebtn3Down){
				appbtn=Button2;
				mousebtn3Down=false;
			}
			if (appbtn!=-1){
				mouseButton(appbtn, mousebtn3Down);
			}
		}
		if (wheel>0){
			mouseButton(4, true);
			mouseButton(4, false);
		}else if (wheel<0){
			mouseButton(5, true);
			mouseButton(5, false);
		}
	}
}


void LinuxInputs::copy(){

}

void LinuxInputs::paste(){

}

int LinuxInputs::getClipboardText(wchar_t** wText){
	return 0;
}

void LinuxInputs::setClipboardText(wchar_t* wText){

}

void LinuxInputs::mouseMove(int x,int y){
	//XTestFakeMotionEvent(xdpy, -1, x, y, CurrentTime);
	XWarpPointer(xdpy, None, root, 0, 0, 0, 0, x, y);
	XFlush(xdpy);
}

void LinuxInputs::mouseButton(int button,bool press){
	XTestFakeButtonEvent(xdpy, button, press, CurrentTime);
	XFlush(xdpy);
	/*XEvent event;
    memset(&event, 0x00, sizeof(event));
    if (press){
    	event.type = ButtonPress;
    }else{
    	event.type = ButtonRelease;
    	event.xbutton.state = 0x100;
    }
    event.xbutton.button = button;
    event.xbutton.same_screen = True;
    XQueryPointer(xdpy, root, &event.xbutton.root, &event.xbutton.window, &event.xbutton.x_root, &event.xbutton.y_root, &event.xbutton.x, &event.xbutton.y, &event.xbutton.state);
    event.xbutton.subwindow = event.xbutton.window;
    while(event.xbutton.subwindow){
        event.xbutton.window = event.xbutton.subwindow;
        XQueryPointer(xdpy, event.xbutton.window, &event.xbutton.root, &event.xbutton.subwindow, &event.xbutton.x_root, &event.xbutton.y_root, &event.xbutton.x, &event.xbutton.y, &event.xbutton.state);
    }
    XSendEvent(xdpy, PointerWindow, True, 0xfff, &event);
	 */
}

void LinuxInputs::loadKeyMap() {
  	kccustom=0;
  	kccustominit=false;
	XkbDescPtr xkb = XkbGetMap(xdpy, XkbAllComponentsMask, XkbUseCoreKbd); //XkbAllClientInfoMask
	XkbClientMapPtr cm = xkb->map;
	//dwdbg->print("###################################################");
	//dwdbg->print("###################################################");
	//dwdbg->print("###################################################");
	for (int i=xkb->min_key_code;i<=xkb->max_key_code;i++){
		int oft=cm->key_sym_map[i].offset;
		if (cm->key_sym_map[i].group_info==0){
            //dwdbg->print("%d - Not defined1",i);
          	kccustom=i;
		}else{
			for (int g=0;g<=cm->key_sym_map[i].group_info-1;g++){
				if (g<max_grp){
					int ig=cm->key_sym_map[i].kt_index[g];
					//KEYSYM
					for (int l=0;l<=cm->types[ig].num_levels-1;l++){
						KeySym ks = xkb->map->syms[oft];
						if (ks!=NoSymbol){
							long uc = keysym2ucs(ks);
							if (uc!=-1){
                             	//dwdbg->print("%d - g: %d - l: %d - KeySym: %04x - Unicode: %04x",i,g,l,ks,uc);
								//Se non esiste le crea
								map<int,KEYMAP*>::iterator itmap = hmUnicodeMap.find(uc);
								KEYMAP* keyMap;
								if (itmap==hmUnicodeMap.end()){ //NON ESISTE
									keyMap = new KEYMAP[4];
									for (int g=0;g<max_grp;g++){
										keyMap[g].unicode=0;
										keyMap[g].sym=NoSymbol;
										keyMap[g].code=0;
										keyMap[g].modifier=0;
									}
									hmUnicodeMap[uc]=keyMap;
								}else{
									keyMap=itmap->second;
								}
								if (keyMap[g].code==0){//NON ASSEGNATO IN PRECEDENZA
									keyMap[g].unicode=uc;
									keyMap[g].sym=ks;
									keyMap[g].code=i;
									//TYPES
									for (int m=0;m<=cm->types[ig].map_count-1;m++){
										if (l==cm->types[ig].map[m].level){
											keyMap[g].modifier=cm->types[ig].map[m].mods.mask;
											break;
										}
									}
								}
							}else{
                            	//dwdbg->print("%d - g: %d - l: %d - KeySym: %04x",i,g,l,ks);
                            }
						}else{
                          	if ((cm->key_sym_map[i].group_info==1) && (cm->types[ig].num_levels==1)){
                            	//dwdbg->print("%d - Not defined2",i);
                              	kccustom=i;
                            }else{
                        		//dwdbg->print("%d - g: %d - l: %d - KeySym: NoSymbol",i,g,l);
                            }
                        }
						oft++;
					}
				}
			}
		}
	}
	//dwdbg->print("###################################################");
	//dwdbg->print("###################################################");
	//dwdbg->print("###################################################");
	XkbFreeClientMap(xkb, XkbAllComponentsMask, true);
}

void LinuxInputs::unloadKeyMap() {
	for (std::map<int,KEYMAP*>::iterator it=hmUnicodeMap.begin(); it!=hmUnicodeMap.end(); ++it){
		delete [] it->second;
	}
	hmUnicodeMap.clear();
	kccustom=0;
}

KeySym LinuxInputs::getKeySym(const char* key){
	if (strcmp(key,"CONTROL")==0){
		return XK_Control_L;
	}else if (strcmp(key,"ALT")==0){
		return XK_Alt_L;
	}else if (strcmp(key,"SHIFT")==0){
		return XK_Shift_L;
	}else if (strcmp(key,"TAB")==0){
		return XK_Tab;
	}else if (strcmp(key,"ENTER")==0){
		return XK_Return;
	}else if (strcmp(key,"BACKSPACE")==0){
		return XK_BackSpace;
	}else if (strcmp(key,"CLEAR")==0){
		return XK_Clear;
	}else if (strcmp(key,"PAUSE")==0){
		return XK_Pause;
	}else if (strcmp(key,"ESCAPE")==0){
		return XK_Escape;
	}else if (strcmp(key,"SPACE")==0){
		return XK_space;
	}else if (strcmp(key,"DELETE")==0){
		return XK_Delete;
	}else if (strcmp(key,"INSERT")==0){
		return XK_Insert;
	}else if (strcmp(key,"HELP")==0){
		return XK_Help;
	}else if (strcmp(key,"LEFT_WINDOW")==0){
		return 0;
	}else if (strcmp(key,"RIGHT_WINDOW")==0){
		return 0;
	}else if (strcmp(key,"SELECT")==0){
		return XK_Select;
	}else if (strcmp(key,"PAGE_UP")==0){
		return XK_Page_Up;
	}else if (strcmp(key,"PAGE_DOWN")==0){
		return XK_Page_Down;
	}else if (strcmp(key,"END")==0){
		return XK_End;
	}else if (strcmp(key,"HOME")==0){
		return XK_Home;
	}else if (strcmp(key,"LEFT_ARROW")==0){
		return XK_Left;
	}else if (strcmp(key,"UP_ARROW")==0){
		return XK_Up;
	}else if (strcmp(key,"DOWN_ARROW")==0){
		return XK_Down;
	}else if (strcmp(key,"RIGHT_ARROW")==0){
		return XK_Right;
	}else if (strcmp(key,"F1")==0){
		return XK_F1;
	}else if (strcmp(key,"F2")==0){
		return XK_F2;
	}else if (strcmp(key,"F3")==0){
		return XK_F3;
	}else if (strcmp(key,"F4")==0){
		return XK_F4;
	}else if (strcmp(key,"F5")==0){
		return XK_F5;
	}else if (strcmp(key,"F6")==0){
		return XK_F6;
	}else if (strcmp(key,"F7")==0){
		return XK_F7;
	}else if (strcmp(key,"F8")==0){
		return XK_F8;
	}else if (strcmp(key,"F9")==0){
		return XK_F9;
	}else if (strcmp(key,"F10")==0){
		return XK_F10;
	}else if (strcmp(key,"F11")==0){
		return XK_F11;
	}else if (strcmp(key,"F12")==0){
		return XK_F12;
	}else{
		return XStringToKeysym(key);
	}
	return 0;
}

void LinuxInputs::clearCustomKeyUnicode(){
  	if ((kccustom!=0) && (kccustominit==true)){
  		XkbDescPtr xkb = XkbGetMap(xdpy, XkbAllComponentsMask, XkbUseCoreKbd);
        KeySym* appks = XkbResizeKeySyms(xkb,kccustom,1);
        appks[0]=NoSymbol;
        xkb->device_spec=XkbUseCoreKbd;
        XkbMapChangesRec changes;
        changes.changed = XkbKeySymsMask;
        changes.first_key_sym = kccustom;
        changes.num_key_syms = 1;
        XkbChangeMap(xdpy, xkb, &changes);
        XkbFreeClientMap(xkb, XkbAllComponentsMask, true);
      	kccustominit=false;
      	skipKeyboardChangedCounter.reset();
    }
}

KeyCode LinuxInputs::createCustomKeyUnicode(int uc) {
  	if (kccustom!=0){
        KeySym sym=ucs2keysym(uc);
        if (sym!=NoSymbol){
            XkbDescPtr xkb = XkbGetMap(xdpy, XkbAllComponentsMask, XkbUseCoreKbd);
            int* ari=new int[1];
            ari[0]=0;
            XkbChangeTypesOfKey(xkb,kccustom,1,XkbGroup1Mask,ari,NULL);
            delete [] ari;
            KeySym* appks = XkbResizeKeySyms(xkb,kccustom,1);
            appks[0]=sym;
            xkb->device_spec=XkbUseCoreKbd;
            XkbMapChangesRec changes;
            changes.changed = XkbKeySymsMask;
            changes.first_key_sym = kccustom;
            changes.num_key_syms = 1;
            XkbChangeMap(xdpy, xkb, &changes);
            XkbFreeClientMap(xkb, XkbAllComponentsMask, true);
            kccustominit=true;
          	skipKeyboardChangedCounter.reset();
            return kccustom;
        }
    }
	return 0;
}

void LinuxInputs::ctrlaltshift(bool ctrl, bool alt, bool shift){
	if ((ctrl) && (!ctrlDown)){
		ctrlDown=true;
		KeyCode kc = XKeysymToKeycode(xdpy, XK_Control_L);
		XTestFakeKeyEvent(xdpy, kc, True, CurrentTime);
	}else if ((!ctrl) && (ctrlDown)){
		ctrlDown=false;
		KeyCode kc = XKeysymToKeycode(xdpy, XK_Control_L);
		XTestFakeKeyEvent(xdpy, kc, False, CurrentTime);
	}

	if ((alt) && (!altDown)){
		altDown=true;
		KeyCode kc = XKeysymToKeycode(xdpy, XK_Alt_L);
		XTestFakeKeyEvent(xdpy, kc, True, CurrentTime);
	}else if ((!alt) && (altDown)){
		altDown=false;
		KeyCode kc = XKeysymToKeycode(xdpy, XK_Alt_L);
		XTestFakeKeyEvent(xdpy, kc, False, CurrentTime);
	}

	if ((shift) && (!shiftDown)){
		shiftDown=true;
		KeyCode kc = XKeysymToKeycode(xdpy, XK_Shift_L);
		XTestFakeKeyEvent(xdpy, kc, True, CurrentTime);
	}else if ((!shift) && (shiftDown)){
		shiftDown=false;
		KeyCode kc = XKeysymToKeycode(xdpy, XK_Shift_L);
		XTestFakeKeyEvent(xdpy, kc, False, CurrentTime);
	}
}

#endif
