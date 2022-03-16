/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/
#if defined OS_WINDOWS

#include "windowsinputs.h"


WindowsInputs::WindowsInputs(){
	mousebtn1Down=false;
	mousebtn2Down=false;
	mousebtn3Down=false;
	ctrlDown=false;
	altDown=false;
	shiftDown=false;
}

WindowsInputs::~WindowsInputs(){

}

void WindowsInputs::addCtrlAltShift(INPUT (&inputs)[20],int &p,bool ctrl, bool alt, bool shift){
	if ((ctrl) && (!ctrlDown)){
		ctrlDown=true;
		inputs[p].type= INPUT_KEYBOARD;
		inputs[p].ki.wVk = VK_LCONTROL;
		inputs[p].ki.wScan = MapVirtualKey(VK_LCONTROL & 0xFF, MAPVK_VK_TO_VSC);
		inputs[p].ki.time = 5;
		inputs[p].ki.dwExtraInfo = 0;
		inputs[p].ki.dwFlags = 0;
		p++;
	}else if ((!ctrl) && (ctrlDown)){
		ctrlDown=false;
		inputs[p].type= INPUT_KEYBOARD;
		inputs[p].ki.wVk = VK_LCONTROL;
		inputs[p].ki.wScan = MapVirtualKey(VK_LCONTROL & 0xFF, MAPVK_VK_TO_VSC);
		inputs[p].ki.time = 0;
		inputs[p].ki.dwExtraInfo = 0;
		inputs[p].ki.dwFlags = KEYEVENTF_KEYUP;
		p++;
	}
	if ((alt) && (!altDown)){
		altDown=true;
		inputs[p].type= INPUT_KEYBOARD;
		inputs[p].ki.wVk = VK_LMENU;
		inputs[p].ki.wScan = MapVirtualKey(VK_LMENU & 0xFF, MAPVK_VK_TO_VSC);
		inputs[p].ki.time = 5;
		inputs[p].ki.dwExtraInfo = 0;
		inputs[p].ki.dwFlags = 0;
		p++;
	}else if ((!alt) && (altDown)){
		altDown=false;
		inputs[p].type= INPUT_KEYBOARD;
		inputs[p].ki.wVk = VK_LMENU;
		inputs[p].ki.wScan = MapVirtualKey(VK_LMENU & 0xFF, MAPVK_VK_TO_VSC);
		inputs[p].ki.time = 0;
		inputs[p].ki.dwExtraInfo = 0;
		inputs[p].ki.dwFlags = KEYEVENTF_KEYUP;
		p++;
	}
	if ((shift) && (!shiftDown)){
		shiftDown=true;
		inputs[p].type= INPUT_KEYBOARD;
		inputs[p].ki.wVk = VK_LSHIFT;
		inputs[p].ki.wScan = MapVirtualKey(VK_LSHIFT & 0xFF, MAPVK_VK_TO_VSC);
		inputs[p].ki.time = 5;
		inputs[p].ki.dwExtraInfo = 0;
		inputs[p].ki.dwFlags = 0;
		p++;
	}else if ((!shift) && (shiftDown)){
		shiftDown=false;
		inputs[p].type= INPUT_KEYBOARD;
		inputs[p].ki.wVk = VK_LSHIFT;
		inputs[p].ki.wScan = MapVirtualKey(VK_LSHIFT & 0xFF, MAPVK_VK_TO_VSC);
		inputs[p].ki.time = 0;
		inputs[p].ki.dwExtraInfo = 0;
		inputs[p].ki.dwFlags = KEYEVENTF_KEYUP;
		p++;
	}
}

void WindowsInputs::sendInputs(INPUT (&inputs)[20],int max){
	if (max>0){
		INPUT sk[1];
		for (int i=0;i<=max-1;i++){
			sk[0]=inputs[i];
			int tm = 0;
			if (sk[0].type==INPUT_KEYBOARD){
				tm = sk[0].ki.time;
				sk[0].ki.time=0;
			}else if (sk[0].type==INPUT_MOUSE){
				tm = sk[0].mi.time;
				sk[0].mi.time=0;
			}
			SendInput(1, sk, sizeof(INPUT));
			if (tm>0){
				Sleep(tm);
			}
		}
	}
}

bool WindowsInputs::isExtendedKey(int key){
	return key == VK_RMENU || key == VK_RCONTROL || key == VK_NUMLOCK || key == VK_INSERT || key == VK_DELETE
		|| key == VK_HOME || key == VK_END || key == VK_PRIOR || key == VK_NEXT
		|| key == VK_UP || key == VK_DOWN || key == VK_LEFT || key == VK_RIGHT ||key == VK_APPS
        || key == VK_RWIN || key == VK_LWIN || key == VK_MENU || key == VK_CONTROL || key == VK_CANCEL|| key == VK_DIVIDE
		|| key == VK_NUMPAD0 || key == VK_NUMPAD1 || key == VK_NUMPAD2 || key == VK_NUMPAD3 || key == VK_NUMPAD4 || key == VK_NUMPAD5
		|| key == VK_NUMPAD6 || key == VK_NUMPAD7 || key == VK_NUMPAD8 || key == VK_NUMPAD9;

}

int WindowsInputs::getKeyCode(const char* key){
	if (strcmp(key,"CONTROL")==0){
		return VK_CONTROL;
	}else if (strcmp(key,"LCONTROL")==0){
		return VK_LCONTROL;
	}else if (strcmp(key,"RCONTROL")==0){
			return VK_RCONTROL;
	}else if (strcmp(key,"ALT")==0){
		return VK_MENU;
	}else if (strcmp(key,"LALT")==0){
		return VK_LMENU;
	}else if (strcmp(key,"RALT")==0){
		return VK_RMENU;
	}else if (strcmp(key,"SHIFT")==0){
		return VK_SHIFT;
	}else if (strcmp(key,"LSHIFT")==0){
		return VK_LSHIFT;
	}else if (strcmp(key,"RSHIFT")==0){
		return VK_RSHIFT;
	}else if (strcmp(key,"TAB")==0){
		return VK_TAB;
	}else if (strcmp(key,"ENTER")==0){
		return VK_RETURN;
	}else if (strcmp(key,"BACKSPACE")==0){
		return VK_BACK;
	}else if (strcmp(key,"CLEAR")==0){
		return VK_CLEAR;
	}else if (strcmp(key,"PAUSE")==0){
		return VK_PAUSE;
	}else if (strcmp(key,"ESCAPE")==0){
		return VK_ESCAPE;
	}else if (strcmp(key,"SPACE")==0){
		return VK_SPACE;
	}else if (strcmp(key,"DELETE")==0){
		return VK_DELETE;
	}else if (strcmp(key,"INSERT")==0){
		return VK_INSERT;
	}else if (strcmp(key,"HELP")==0){
		return VK_HELP;
	}else if (strcmp(key,"LEFT_WINDOW")==0){
		return VK_LWIN;
	}else if (strcmp(key,"RIGHT_WINDOW")==0){
		return VK_RWIN;
	}else if (strcmp(key,"SELECT")==0){
		return VK_SELECT;
	}else if (strcmp(key,"PAGE_UP")==0){
		return VK_PRIOR;
	}else if (strcmp(key,"PAGE_DOWN")==0){
		return VK_NEXT;
	}else if (strcmp(key,"END")==0){
		return VK_END;
	}else if (strcmp(key,"HOME")==0){
		return VK_HOME;
	}else if (strcmp(key,"LEFT_ARROW")==0){
		return VK_LEFT;
	}else if (strcmp(key,"UP_ARROW")==0){
		return VK_UP;
	}else if (strcmp(key,"DOWN_ARROW")==0){
		return VK_DOWN;
	}else if (strcmp(key,"RIGHT_ARROW")==0){
		return VK_RIGHT;
	}else if (strcmp(key,"F1")==0){
		return VK_F1;
	}else if (strcmp(key,"F2")==0){
		return VK_F2;
	}else if (strcmp(key,"F3")==0){
		return VK_F3;
	}else if (strcmp(key,"F4")==0){
		return VK_F4;
	}else if (strcmp(key,"F5")==0){
		return VK_F5;
	}else if (strcmp(key,"F6")==0){
		return VK_F6;
	}else if (strcmp(key,"F7")==0){
		return VK_F7;
	}else if (strcmp(key,"F8")==0){
		return VK_F8;
	}else if (strcmp(key,"F9")==0){
		return VK_F9;
	}else if (strcmp(key,"F10")==0){
		return VK_F10;
	}else if (strcmp(key,"F11")==0){
		return VK_F11;
	}else if (strcmp(key,"F12")==0){
		return VK_F12;
	}else{
		return VkKeyScan(key[0]);
	}
	return 0;
}

void WindowsInputs::addInputMouse(INPUT (&inputs)[20],int &p,int x, int y,DWORD dwFlags,int mouseData,int tm){
	inputs[p].type= INPUT_MOUSE;
	inputs[p].mi.dx = x;
	inputs[p].mi.dy = y;
	inputs[p].mi.dwFlags = dwFlags;
	inputs[p].mi.time = tm;
	inputs[p].mi.dwExtraInfo = 0;
	inputs[p].mi.mouseData = mouseData;
	p++;
}


void WindowsInputs::keyboard(const char* type,const char* key, bool ctrl, bool alt, bool shift, bool command){
	INPUT inputs[20];
	int p=0;
	if (strcmp(type,"CHAR")==0){
		bool sendunicode=true;
		SHORT vkKeyScanResult = 0;
		int vkey = 0;
		short btlo = 0;
		short bthi = 0;
		bool wShift = false;
		bool wCtrl  = false;
		bool wAlt   = false;
		bool wHankaku   = false;
		HKL hklCurrent = (HKL)0x04090409;
		DWORD threadId = 0;
		try {
			HWND hwnd = GetForegroundWindow();
			if (hwnd != 0) {
				int ikey=atoi(key);
				threadId = GetWindowThreadProcessId(hwnd, 0);
				hklCurrent = GetKeyboardLayout(threadId);
				vkKeyScanResult = VkKeyScanExW(ikey, hklCurrent);
				if (vkKeyScanResult != -1) {
					sendunicode=false;
					btlo = vkKeyScanResult & 0xff;
					bthi = (vkKeyScanResult>>8) & 0xff;
					wShift = (bthi >> 0 & 1) != 0;
					wCtrl  = (bthi >> 1 & 1) != 0;
					wAlt   = (bthi >> 2 & 1) != 0;
					wHankaku = (bthi >> 3 & 1) != 0;
					if ((wCtrl && wAlt) || wHankaku){ //VK_KANA ???
						sendunicode=true;
					}else if (strcmp(key,"46")==0){ //??? Putty issue 46=.
						sendunicode=true;
					}

					if (!sendunicode){
						vkey=MapVirtualKeyEx(btlo, MAPVK_VK_TO_VSC,hklCurrent);
						BYTE keyState[256] = {};
						if (GetKeyboardState(keyState)){
							keyState[VK_CAPITAL]=0x00;
							if (wShift){
								keyState[VK_SHIFT]=0xff;
							}else{
								keyState[VK_SHIFT]=0x00;
							}
							if (wCtrl){
								keyState[VK_CONTROL]=0xff;
							}else{
								keyState[VK_CONTROL]=0x00;
							}
							if (wAlt){
								keyState[VK_MENU]=0xff;
							}else{
								keyState[VK_MENU]=0x00;
							}
							WCHAR sbuff[5] = {};
							if (ToUnicodeEx(btlo,vkey,keyState,sbuff,4,0,hklCurrent)>0){
								int ikeyapp = (int)sbuff[0];
								if (ikey!=ikeyapp){
									sendunicode=true;
								}
							}
						}
					}

				}
				if (sendunicode){
					int ltit = GetWindowTextLengthW(hwnd);
					wchar_t* tit = new wchar_t[ltit + 1];
					GetWindowTextW(hwnd, tit, (ltit + 1));
					if ((wcsstr(tit, L"VirtualBox") != 0) || (wcsstr(tit, L"VMware") != 0)){ //??? VirtualBox/VMware don't accept KEYEVENTF_UNICODE*/
						sendunicode=false;
					}
					delete  tit;
				}
			}
		} catch (...) {

		}

		if (sendunicode){
			inputs[p].type= INPUT_KEYBOARD;
			inputs[p].ki.wVk = 0;
			inputs[p].ki.wScan = atoi(key);
			inputs[p].ki.time = 5;
			inputs[p].ki.dwFlags = KEYEVENTF_UNICODE;
			inputs[p].ki.dwExtraInfo = 0;
			p++;

			inputs[p].type= INPUT_KEYBOARD;
			inputs[p].ki.wVk = 0;
			inputs[p].ki.wScan = atoi(key);
			inputs[p].ki.time = 0;
			inputs[p].ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP;
			inputs[p].ki.dwExtraInfo = 0;
			p++;

		}else{

			//DISABLE VK_CAPITAL
			SHORT vkc = GetKeyState(VK_CAPITAL);
			if ((vkc & 0x0001)!=0){
				inputs[p].type= INPUT_KEYBOARD;
				inputs[p].ki.wVk = VK_CAPITAL;
				inputs[p].ki.wScan = 0;
				inputs[p].ki.time = 5;
				inputs[p].ki.dwExtraInfo = 0;
				inputs[p].ki.dwFlags =  KEYEVENTF_EXTENDEDKEY | 0;
				p++;
				inputs[p].type= INPUT_KEYBOARD;
				inputs[p].ki.wVk = VK_CAPITAL;
				inputs[p].ki.wScan = 0;
				inputs[p].ki.time = 5;
				inputs[p].ki.dwExtraInfo = 0;
				inputs[p].ki.dwFlags =   KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP;
				p++;
			}

			addCtrlAltShift(inputs,p,wCtrl,wAlt,wShift);

			inputs[p].type= INPUT_KEYBOARD;
			inputs[p].ki.wVk = btlo;
			inputs[p].ki.wScan = MapVirtualKey(btlo, MAPVK_VK_TO_VSC);
			inputs[p].ki.time = 5;
			inputs[p].ki.dwExtraInfo = 0;
			inputs[p].ki.dwFlags = 0;
			p++;

			inputs[p].type= INPUT_KEYBOARD;
			inputs[p].ki.wVk = btlo;
			inputs[p].ki.wScan = MapVirtualKey(btlo, MAPVK_VK_TO_VSC);
			inputs[p].ki.time = 0;
			inputs[p].ki.dwExtraInfo = 0;
			inputs[p].ki.dwFlags = KEYEVENTF_KEYUP;
			p++;

			addCtrlAltShift(inputs,p,false,false,false);

		}
	}else if (strcmp(type,"KEY")==0){
		addCtrlAltShift(inputs,p,ctrl,alt,shift);

		int kc = getKeyCode(key);
		short btlo = kc & 0xff;
		//short bthi = (kc>>8) & 0xff;

		bool extk=isExtendedKey(btlo);
		inputs[p].type= INPUT_KEYBOARD;
		inputs[p].ki.wVk = kc;
		inputs[p].ki.wScan = MapVirtualKey(btlo, MAPVK_VK_TO_VSC);
		inputs[p].ki.time = 0;
		inputs[p].ki.dwExtraInfo = 0;
		inputs[p].ki.dwFlags = 0;
		if (extk){
			inputs[p].ki.dwFlags |= KEYEVENTF_EXTENDEDKEY;
		}
		p++;

		inputs[p].type= INPUT_KEYBOARD;
		inputs[p].ki.wVk = kc;
		inputs[p].ki.wScan = MapVirtualKey(btlo, MAPVK_VK_TO_VSC);
		inputs[p].ki.time = 0;
		inputs[p].ki.dwExtraInfo = 0;
		inputs[p].ki.dwFlags = KEYEVENTF_KEYUP;
		if (extk){
			inputs[p].ki.dwFlags |= KEYEVENTF_EXTENDEDKEY;
		}
		p++;

		addCtrlAltShift(inputs,p,false,false,false);

	}
	sendInputs(inputs,p);
}

void WindowsInputs::mouse(MONITORS_INFO_ITEM* moninfoitem, int x, int y, int button, int wheel, bool ctrl, bool alt, bool shift, bool command){
	INPUT inputs[20];
	int p=0;
	addCtrlAltShift(inputs,p,ctrl,alt,shift);

	int mx=-1;
	int my=-1;
	int appx = 0;
	int appy = 0;
	int mouseData=0;
	DWORD dwFlags = 0;
	if ((x>=0) && (y>=0)){
		mx=x;
		my=y;
		if (moninfoitem!=NULL){
			mx+=moninfoitem->x;
			my+=moninfoitem->y;
		}
		dwFlags = MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_MOVE | MOUSEEVENTF_VIRTUALDESK;
		UINT16 desktopWidth =  GetSystemMetrics(SM_CXVIRTUALSCREEN);
		UINT16 desktopHeight = GetSystemMetrics(SM_CYVIRTUALSCREEN);

		int desktopOffsetX = GetSystemMetrics(SM_XVIRTUALSCREEN);
		int desktopOffsetY = GetSystemMetrics(SM_YVIRTUALSCREEN);
		appx = (int)((mx - desktopOffsetX) * 65535 / (desktopWidth));
		appy = (int)((my - desktopOffsetY) * 65535 / (desktopHeight));
	}
	if (button==64){ //CLICK
		addInputMouse(inputs,p,appx,appy,dwFlags | MOUSEEVENTF_LEFTDOWN,mouseData,5);
		addInputMouse(inputs,p,appx,appy,dwFlags | MOUSEEVENTF_LEFTUP,mouseData,0);
	}else if (button==128){ //DBLCLICK
		addInputMouse(inputs,p,appx,appy,dwFlags | MOUSEEVENTF_LEFTDOWN,mouseData,5);
		addInputMouse(inputs,p,appx,appy,dwFlags | MOUSEEVENTF_LEFTUP,mouseData,100);
		addInputMouse(inputs,p,appx,appy,dwFlags | MOUSEEVENTF_LEFTDOWN,mouseData,5);
		addInputMouse(inputs,p,appx,appy,dwFlags | MOUSEEVENTF_LEFTUP,mouseData,0);
	}else{
		if (button!=-1){
			if (button & 1){
				if (!mousebtn1Down){
					dwFlags |=  MOUSEEVENTF_LEFTDOWN;
					mousebtn1Down=true;
				}
			}else if (mousebtn1Down){
				dwFlags |=  MOUSEEVENTF_LEFTUP;
				mousebtn1Down=false;
			}

			if (button & 2){
				if (!mousebtn2Down){
					dwFlags |=  MOUSEEVENTF_RIGHTDOWN;
					mousebtn2Down=true;
				}
			}else if (mousebtn2Down){
				dwFlags |=  MOUSEEVENTF_RIGHTUP;
				mousebtn2Down=false;
			}

			if (button & 4){
				if (!mousebtn3Down){
					dwFlags |=  MOUSEEVENTF_MIDDLEDOWN;
					mousebtn3Down=true;
				}
			}else if (mousebtn3Down){
				dwFlags |=  MOUSEEVENTF_MIDDLEUP;
				mousebtn3Down=false;
			}
		}
		if (wheel!=0) {
			dwFlags |= MOUSEEVENTF_WHEEL;
			mouseData = wheel*120;
		}
		addInputMouse(inputs,p,appx,appy,dwFlags,mouseData,0);
	}
	sendInputs(inputs,p);
}


void WindowsInputs::copy(){
	keyboard("KEY","C",true,false,false,false);
}

void WindowsInputs::paste(){
	keyboard("KEY","V",true,false,false,false);
}

int WindowsInputs::getClipboardText(wchar_t** wText){
	Sleep(100);
	int iret=0;
	if (OpenClipboard(NULL)){
		HANDLE hData = GetClipboardData(CF_UNICODETEXT);
		if (hData != NULL){
			  size_t sz=GlobalSize(hData);
			  if (sz>0){
				  wchar_t* wGlobal = (wchar_t*)GlobalLock(hData);
				  iret=wcslen(wGlobal);
				  wchar_t* tret = (wchar_t*)malloc(iret*sizeof(wchar_t));
				  wcscpy(tret,wGlobal);
				  *wText=tret;
			  }
			  GlobalUnlock(hData);
		}
		CloseClipboard();
	}
	return iret;
}

void WindowsInputs::setClipboardText(wchar_t* wText){
	HGLOBAL hdst;
    LPWSTR dst;
	if (wText!=NULL){
		size_t len = wcslen(wText);
		hdst = GlobalAlloc(GMEM_MOVEABLE | GMEM_DDESHARE, (len + 1) * sizeof(wchar_t));
		dst = (LPWSTR)GlobalLock(hdst);
		memcpy(dst, wText, len * sizeof(wchar_t));
		dst[len] = 0;
		GlobalUnlock(hdst);
	}
	if (OpenClipboard(NULL)){
		EmptyClipboard();
		if (wText!=NULL){
			SetClipboardData(CF_UNICODETEXT, hdst);
		}
		CloseClipboard();
	}
	Sleep(100);
}

#endif
