/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/

#if defined OS_WINDOWS

#include "windowsdesktop.h"

DWORD WINAPI WindowsDesktopCreateWindow(LPVOID lpParam){
	WindowsDesktop* wd = (WindowsDesktop*)lpParam;
	return wd->createWindow();
}

LRESULT CALLBACK WindowsDesktopWindowProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam){
	WindowsDesktop *pThis;
	/*if (msg == WM_NCCREATE){
		pThis = static_cast<WindowsDesktop*>(reinterpret_cast<CREATESTRUCT*>(lParam)->lpCreateParams);
		SetLastError(0);
		if (!SetWindowLongPtr(hwnd, GWLP_USERDATA, reinterpret_cast<LONG_PTR>(pThis))){
			if (GetLastError() != 0) {
				return FALSE;
			}
		}
	}else{*/
	pThis = reinterpret_cast<WindowsDesktop*>(GetWindowLongPtr(hwnd, GWLP_USERDATA));
	//}
	if (pThis){
		pThis->windowProc(hwnd, msg, wParam, lParam);
	}
	return DefWindowProc(hwnd, msg, wParam, lParam);
}

BOOL CALLBACK WindowsDesktopCheckLayered(HWND hWnd, LPARAM lParam){
	BOOL& cBlt = *(reinterpret_cast<BOOL*>(lParam));
	if (IsWindowVisible(hWnd)==FALSE || IsIconic(hWnd)==TRUE) {
		return TRUE;
	}
	char title[5];
	GetWindowText(hWnd, title, 6);
	if (strcmp(title,"Start")!=0){ //Start e' sempre layered ma la cattura comunque???
		WINDOWINFO WNDI;
		GetWindowInfo(hWnd, &WNDI);
		if (WNDI.dwExStyle & WS_EX_LAYERED) {
			cBlt = true;
			return FALSE;
		}
	}
	return TRUE;
}


WindowsDesktop::WindowsDesktop(){
	m_osVerInfo.dwOSVersionInfoSize = sizeof(OSVERSIONINFO);
	if (!GetVersionEx((OSVERSIONINFO*)&m_osVerInfo)){
		m_osVerInfo.dwOSVersionInfoSize = 0;
	}
	if (isWinXP()){
		tcclipboardxp = TimeCounter();
		oldclipboardxp = NULL;
	}
	runAsElevated=false;
	bclipboardchanged=false;
	wcsncpy(prevDesktopName,L"",0);
	hwndwts=NULL;
	loadLibWin = new WindowsLoadLib();
	//GESTIONE DPI Legge in modo corretto le impostazioni dello schermo (risoluzione ecc..)
	if ((loadLibWin->isAvailableShCore()) && (loadLibWin->SetProcessDpiAwarenessFunc())){
		loadLibWin->SetProcessDpiAwarenessFunc()(2); //PROCESS_PER_MONITOR_DPI_AWARE
	}else if ((loadLibWin->isAvailableUser32()) && (loadLibWin->SetProcessDPIAwareFunc())){
		loadLibWin->SetProcessDPIAwareFunc()();
	}
	if (loadLibWin->WTSRegisterSessionNotificationFunc()){
		CreateThread(0, 0, WindowsDesktopCreateWindow, this, 0, NULL);
		Sleep(1000);
	}
}

WindowsDesktop::~WindowsDesktop(){
	clearClipboardXP();
	if (hwndwts){
		SendMessage(hwndwts, WM_DESTROY, 0, 0);
		hwndwts=NULL;
	}
	delete loadLibWin;
}

bool WindowsDesktop::isWinNTFamily() {
	return m_osVerInfo.dwPlatformId == VER_PLATFORM_WIN32_NT;
}

bool WindowsDesktop::isWinXP() {
	return ((m_osVerInfo.dwMajorVersion == 5) && (m_osVerInfo.dwMinorVersion == 1) && isWinNTFamily());
}

void WindowsDesktop::clearClipboardXP(){
	if (isWinXP()){
		if (oldclipboardxp!=NULL){
			free(oldclipboardxp);
			oldclipboardxp=NULL;
		}
	}
}

LRESULT CALLBACK WindowsDesktop::windowProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam){
	switch(msg){
		case  WM_CREATE:
			//DWALoggerWriteDebug(L"WM_CREATE");
			//disableVisualEffect
		break;
		case  WM_QUERYENDSESSION:
			//DWALoggerWriteDebug(L"WM_QUERYENDSESSION");
			//restoreVisualEffect
		break;
		case  WM_ENDSESSION:
			//DWALoggerWriteDebug(L"WM_ENDSESSION");
			//restoreVisualEffect
		break;
		case  WM_WTSSESSION_CHANGE:
			/*
				WTS_CONSOLE_CONNECT		= 0x1
				WTS_CONSOLE_DISCONNECT		= 0x2
				WTS_REMOTE_CONNECT		= 0x3
				WTS_REMOTE_DISCONNECT		= 0x4
				WTS_SESSION_LOGON		= 0x5
				WTS_SESSION_LOGOFF		= 0x6
				WTS_SESSION_LOCK		= 0x7
				WTS_SESSION_UNLOCK		= 0x8
				WTS_SESSION_REMOTE_CONTROL	= 0x9
			*/
			switch(wParam){
				case 0x1:	//#define WTS_CONSOLE_CONNECT
					//DWALoggerWriteDebug(L"WTS_CONSOLE_CONNECT");
				break;
				case 0x2:	//#define WTS_CONSOLE_DISCONNECT
					//DWALoggerWriteDebug(L"WTS_CONSOLE_DISCONNECT");
				break;
				case 0x3:	//#define WTS_REMOTE_CONNECT
					//DWALoggerWriteDebug(L"WTS_REMOTE_CONNECT");
				break;
				case 0x4:	//#define WTS_REMOTE_DISCONNECT
					//DWALoggerWriteDebug(L"WTS_REMOTE_DISCONNECT");
					/////restoreVisualEffect
				break;
				case 0x5:	//#define WTS_SESSION_LOGON
					//DWALoggerWriteDebug(L"WTS_SESSION_LOGON");
					//disableVisualEffect
				break;
				case 0x6:	//#define WTS_SESSION_LOGOFF
					//DWALoggerWriteDebug(L"WTS_SESSION_LOGOFF");
					//restoreVisualEffect
				break;
				case 0x7:	//#define WTS_SESSION_LOCK
					//DWALoggerWriteDebug(L"WTS_SESSION_LOCK");
				break;
				case 0x8:	//#define WTS_SESSION_UNLOCK
					//DWALoggerWriteDebug(L"WTS_SESSION_UNLOCK");
				break;
				case 0x9:	//#define WTS_SESSION_REMOTE_CONTROL
					//DWALoggerWriteDebug(L"WTS_SESSION_REMOTE_CONTROL");
				break;
			}
		break;
		case WM_CLIPBOARDUPDATE:
			//DWALoggerWriteDebug(L"WM_CLIPBOARDUPDATE");
			bclipboardchanged=true;
		break;
		case WM_DESTROY:
			//DWALoggerWriteDebug(L"WM_DESTROY");
			//restoreVisualEffect
			if (loadLibWin->WTSUnRegisterSessionNotificationFunc()) {
				loadLibWin->WTSUnRegisterSessionNotificationFunc()(hwnd);
			}
			PostQuitMessage(0);
		break;
	}
	return DefWindowProc(hwnd, msg, wParam, lParam);
}

DWORD WINAPI WindowsDesktop::createWindow(){
	//CREATE WINDOWS
	WNDCLASSEX wc;
	HINSTANCE hInstance = GetModuleHandle(NULL);
	wc.cbSize        = sizeof(WNDCLASSEX);
	wc.style         = 0;
	wc.lpfnWndProc   = WindowsDesktopWindowProc;
	wc.cbClsExtra    = 0;
	wc.cbWndExtra    = 0;
	wc.hInstance     = hInstance;
	wc.hIcon         = NULL;
	wc.hCursor       = NULL;
	wc.hbrBackground = (HBRUSH)(COLOR_WINDOW+1);
	wc.lpszMenuName  = NULL;
	wc.lpszClassName = "dwascreencapture";
	wc.hIconSm       = NULL;

	RegisterClassEx(&wc);

	hwndwts=CreateWindowEx(0, "dwascreencapture",  "dwascreencapture", WS_EX_PALETTEWINDOW, CW_USEDEFAULT, CW_USEDEFAULT, 100, 100, NULL, NULL, hInstance, NULL);
	if (hwndwts!=NULL){
		SetWindowLongPtr(hwndwts, GWLP_USERDATA, reinterpret_cast<LONG_PTR>(this));
		if (loadLibWin->WTSRegisterSessionNotificationFunc()) {
			loadLibWin->WTSRegisterSessionNotificationFunc()(hwndwts,0);
		}

		if (!isWinXP()){
			if (loadLibWin->AddClipboardFormatListenerFunc()) {
				loadLibWin->AddClipboardFormatListenerFunc()(hwndwts);
			}
		}

		UpdateWindow(hwndwts);
		//ShowWindow(hwndwts, SW_SHOW);
	}else{
		//DWALoggerWriteDebug(L"CreateWindowEx Failed");
	}
	if (hwndwts!=NULL){
		MSG messages;
		while (GetMessage(&messages, NULL, 0, 0)){
			TranslateMessage(&messages);
			DispatchMessage(&messages);
		}
	}
	return 1;
}

void WindowsDesktop::monitorON(){
	INPUT inputs[1];
	inputs[0].type= INPUT_MOUSE;
	inputs[0].mi.dx = 0;
	inputs[0].mi.dy = 0;
	inputs[0].mi.dwFlags = MOUSEEVENTF_MOVE;
	inputs[0].mi.time = 0;
	inputs[0].mi.dwExtraInfo = 0;
	inputs[0].mi.mouseData = 0;
	SendInput(1, inputs, sizeof(INPUT));
}

int WindowsDesktop::setCurrentThread(){ //0 NOT CHANGED //1 CHANGED //2 UAC
	int iret=0;
	if (isWinNTFamily()){
		HDESK desktop = getInputDesktop();
		bool checkuac=true;
		if (desktop){
			wchar_t curDesktopName[1024];
			DWORD nameLength = 0;
			if (GetUserObjectInformationW(desktop, UOI_NAME, &curDesktopName, 1024, &nameLength)) {
				if (wcscmp(prevDesktopName,curDesktopName)!=0){
					if (SetThreadDesktop(desktop)){
						checkuac=false;
						wcsncpy(prevDesktopName,curDesktopName,nameLength);
						iret=1;
					}
				}else{
					checkuac=false;
				}
			}
		}
		if (checkuac){
			if (!runAsElevated){
				iret=2; //UAC
			}
		}
		CloseDesktop(desktop);
	}
	return iret;
}


bool WindowsDesktop::checkWindowsLayered(){
	BOOL captureBlt = false;
	EnumWindows(WindowsDesktopCheckLayered, reinterpret_cast<LPARAM>(&captureBlt));
	if (captureBlt) {
		return true;
	}
	return false;
}

HDESK WindowsDesktop::getInputDesktop(){
	HDESK hInputDesktop = OpenInputDesktop(0, FALSE,
			DESKTOP_CREATEMENU | DESKTOP_CREATEWINDOW | DESKTOP_ENUMERATE
					| DESKTOP_HOOKCONTROL | DESKTOP_READOBJECTS
					| DESKTOP_SWITCHDESKTOP | DESKTOP_JOURNALPLAYBACK
					| DESKTOP_JOURNALRECORD | DESKTOP_WRITEOBJECTS
					| GENERIC_WRITE);
	return hInputDesktop;
}

HDESK WindowsDesktop::getDesktop(char* name){
	HDESK desktop = OpenDesktop(name, 0, FALSE,
			DESKTOP_CREATEMENU | DESKTOP_CREATEWINDOW | DESKTOP_ENUMERATE
					| DESKTOP_HOOKCONTROL | DESKTOP_READOBJECTS
					| DESKTOP_SWITCHDESKTOP | DESKTOP_JOURNALPLAYBACK
					| DESKTOP_JOURNALRECORD | DESKTOP_WRITEOBJECTS
					| GENERIC_WRITE);
	return desktop;
}

bool WindowsDesktop::selectDesktop(char* name){
	HDESK desktop = NULL;
	desktop = getDesktop(name);
	bool bret=false;
	if (SetThreadDesktop(desktop)==TRUE){
		bret=true;
	}
	CloseDesktop(desktop);
	return bret;
}

void WindowsDesktop::ctrlaltcanc(){
	//DWALoggerWriteDebug(L"DWAScreenCaptureInputKeyboard CTRLALTCANC");
	if (selectDesktop((char *)"Winlogon")){
		HWND hwndCtrlAltDel = FindWindow("SAS window class", "SAS window");
		if (hwndCtrlAltDel == NULL) {
			hwndCtrlAltDel = HWND_BROADCAST;
		}
		PostMessage(hwndCtrlAltDel, WM_HOTKEY, 0, MAKELONG(MOD_ALT | MOD_CONTROL, VK_DELETE));
		wcsncpy(prevDesktopName,L"",0); //Alla prossima cattura si posizione sul desktop corretto
	}
}

void WindowsDesktop::getClipboardChanges(CLIPBOARD_DATA* clipboardData){
	clipboardData->type=0;
	if (!isWinXP()){
		bool b = bclipboardchanged;
		bclipboardchanged=false;
		if (b){
			int iret=0;
			if (OpenClipboard(NULL)){
				HANDLE hData = GetClipboardData(CF_UNICODETEXT);
				if (hData != NULL){
					  size_t sz=GlobalSize(hData);
					  if (sz>0){
							wchar_t* wGlobal = (wchar_t*)GlobalLock(hData);
							iret=wcslen(wGlobal);
							if (iret>0){
								wchar_t* tret = (wchar_t*)malloc(iret*sizeof(wchar_t)+1);
								wcscpy(tret,wGlobal);
								clipboardData->type=1; //TEXT
								clipboardData->data=(unsigned char*)tret;
								clipboardData->sizedata=(iret*sizeof(wchar_t));
							}
					  }
					  GlobalUnlock(hData);
				}
				CloseClipboard();
			}
		}
	}else{ //XP DO NOT SUPPORT WM_CLIPBOARDUPDATE
		if (tcclipboardxp.getCounter()>2000){
			tcclipboardxp.reset();
			if (OpenClipboard(NULL)){
				HANDLE hData = GetClipboardData(CF_UNICODETEXT);
				if (hData != NULL){
					  size_t sz=GlobalSize(hData);
					  if (sz>0){
							wchar_t* wGlobal = (wchar_t*)GlobalLock(hData);
							int iret=wcslen(wGlobal);
							if (iret>0){
								bool bchange=((oldclipboardxp==NULL) || (wcscmp(wGlobal,oldclipboardxp)!=0));
								if (bchange){
									if (oldclipboardxp!=NULL){
										free(oldclipboardxp);
									}
									oldclipboardxp = (wchar_t*)malloc(iret*sizeof(wchar_t)+1);
									wchar_t* tret = (wchar_t*)malloc(iret*sizeof(wchar_t)+1);
									wcscpy(oldclipboardxp,wGlobal);
									wcscpy(tret,wGlobal);
									clipboardData->type=1; //TEXT
									clipboardData->data=(unsigned char*)tret;
									clipboardData->sizedata=(iret*sizeof(wchar_t));
								}
							}
					  }
					  GlobalUnlock(hData);
				}
				CloseClipboard();
			}

		}
	}
}

void WindowsDesktop::setClipboard(CLIPBOARD_DATA* clipboardData){
	if (clipboardData->type==1){ //TEXT
		HGLOBAL hdst;
		if (clipboardData->sizedata>0){
			LPWSTR dst;
			size_t len = clipboardData->sizedata / sizeof(wchar_t);
			hdst = GlobalAlloc(GMEM_MOVEABLE | GMEM_DDESHARE, (len + 1) * sizeof(wchar_t));
			dst = (LPWSTR)GlobalLock(hdst);
			memcpy(dst, clipboardData->data, len * sizeof(wchar_t));
			dst[len] = 0;
			GlobalUnlock(hdst);
			if (OpenClipboard(NULL)){
				EmptyClipboard();
				SetClipboardData(CF_UNICODETEXT, hdst);
				CloseClipboard();
			}
		}else if (OpenClipboard(NULL)){
			EmptyClipboard();
			CloseClipboard();
		}
	}
}

#endif
