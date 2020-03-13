/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/
#if defined OS_WINDOWS

#include "windowsscreencapture.h"

ScreenCaptureNative::ScreenCaptureNative(DWDebugger* dbg){
	debugger=dbg;
	m_osVerInfo.dwOSVersionInfoSize = sizeof(OSVERSIONINFO);
    if (!GetVersionEx((OSVERSIONINFO*)&m_osVerInfo)) {
		m_osVerInfo.dwOSVersionInfoSize = 0;
    }
	runAsElevated=false;
	firstmonitorscheck=true;

	monitorsCounter.reset();
	cpuCounter.reset();
}

ScreenCaptureNative::~ScreenCaptureNative() {

}

bool ScreenCaptureNative::isWin8OrLater(){
	if (m_osVerInfo.dwOSVersionInfoSize == 0) {
		return false;
	}
	return ((m_osVerInfo.dwMajorVersion > 6) || ((m_osVerInfo.dwMajorVersion == 6) && (m_osVerInfo.dwMinorVersion >= 2)));
}

void ScreenCaptureNative::setAsElevated(bool b){

}

ULONGLONG ScreenCaptureNative::subtractTime(const FILETIME &a, const FILETIME &b){
    LARGE_INTEGER la, lb;
    la.LowPart = a.dwLowDateTime;
    la.HighPart = a.dwHighDateTime;
    lb.LowPart = b.dwLowDateTime;
    lb.HighPart = b.dwHighDateTime;
 
    return la.QuadPart - lb.QuadPart;
}

float ScreenCaptureNative::getCpuUsage(){
	FILETIME sysIdle, sysKernel, sysUser;
    FILETIME procCreation, procExit, procKernel, procUser;    
 
    if (!GetSystemTimes(&sysIdle, &sysKernel, &sysUser) ||
        !GetProcessTimes(GetCurrentProcess(), &procCreation, &procExit, &procKernel, &procUser)) {
        return -1;
    }

    if ((lastCpu>=0) && (cpuCounter.getCounter()<1000)){
    	return lastCpu;
    }

    if (lastCpu>=0){
    	ULONGLONG sysKernelDiff = subtractTime(sysKernel, prevSysKernel);
		ULONGLONG sysUserDiff = subtractTime(sysUser, prevSysUser);

		ULONGLONG procKernelDiff = subtractTime(procKernel, prevProcKernel);
		ULONGLONG procUserDiff = subtractTime(procUser, prevProcUser);

		ULONGLONG sysTotal = sysKernelDiff + sysUserDiff;
		ULONGLONG procTotal = procKernelDiff + procUserDiff;
		lastCpu=(float)((100.0 * procTotal)/sysTotal);
    }else{
    	lastCpu=0;
    }

    prevSysKernel.dwLowDateTime = sysKernel.dwLowDateTime;
	prevSysKernel.dwHighDateTime = sysKernel.dwHighDateTime;

	prevSysUser.dwLowDateTime = sysUser.dwLowDateTime;
	prevSysUser.dwHighDateTime = sysUser.dwHighDateTime;

	prevProcKernel.dwLowDateTime = procKernel.dwLowDateTime;
	prevProcKernel.dwHighDateTime = procKernel.dwHighDateTime;

	prevProcUser.dwLowDateTime = procUser.dwLowDateTime;
	prevProcUser.dwHighDateTime = procUser.dwHighDateTime;
	cpuCounter.reset();

	//printf("CPU: %f\n",lastCpu);

    return lastCpu;
}

/*int ScreenCaptureNative::detectMirrorDriver(vector<DISPLAY_DEVICE>& devices,map<int,DEVMODE>& settings){
	DISPLAY_DEVICE dd;
	ZeroMemory(&dd, sizeof(dd));
	dd.cb = sizeof(dd);
	int n = 0;
	while(EnumDisplayDevices(NULL, n, &dd, EDD_GET_DEVICE_INTERFACE_NAME))
	{
		n++;
		devices.push_back(dd);
	}
	for(int i=0;i<(int)devices.size();i++)
	{
		DEVMODE dm;
		ZeroMemory(&dm, sizeof(DEVMODE));
		dm.dmSize = sizeof(DEVMODE);
		dm.dmDriverExtra = 0;
		if(EnumDisplaySettingsEx(devices[i].DeviceName,ENUM_CURRENT_SETTINGS,&dm,EDS_ROTATEDMODE))
		{
			settings.insert(map<int,DEVMODE>::value_type(i,dm));
		}
	}
	for(int i=0;i<(int)devices.size();i++){
		string apps(devices[i].DeviceString);
		if (apps=="RDP Encoder Mirror Driver"){
			return i;
		}
	}
	return -1;
} */

BOOL CALLBACK ScreenCaptureNativeMonitorEnumProc(HMONITOR hMonitor,HDC hdcMonitor,LPRECT lprcMonitor,LPARAM dwData){
	ScreenCaptureNative *pThis = reinterpret_cast<ScreenCaptureNative * > (dwData);
	return pThis->monitorEnumProc(hMonitor,hdcMonitor,lprcMonitor,dwData);
}

BOOL CALLBACK ScreenCaptureNative::monitorEnumProc(HMONITOR hMonitor,HDC hdcMonitor,LPRECT lprcMonitor,LPARAM dwData){
	MonitorInfo mi;
	mi.hMonitor=hMonitor;
	mi.hdcMonitor=hdcMonitor;
	mi.x=lprcMonitor->left;
	mi.y=lprcMonitor->top;
	mi.w=lprcMonitor->right-lprcMonitor->left;
	mi.h=lprcMonitor->bottom-lprcMonitor->top;

	//FIX RISOLUZIONI SIMILE A 1366x768
	if (((float)mi.w/(float)8)!=(mi.w/8)){
		mi.w=(int)((int)((float)mi.w/(float)8)+(float)1) * 8;
	}
	//if (((float)mi.h/(float)8)!=(mi.h/8)){
	//   mi.h=(int)((int)((float)mi.h/(float)8)+(float)1) * 8;
	//}

	monitorsInfo.push_back(mi);
	return TRUE;
}

int ScreenCaptureNative::getMonitorCount(){
	int elapsed=monitorsCounter.getCounter();
	if ((firstmonitorscheck) || (elapsed>=MONITORS_INTERVAL)){
		firstmonitorscheck=false;
		monitorsInfo.clear();
		MonitorInfo mi;
		
		mi.x=GetSystemMetrics(SM_XVIRTUALSCREEN);
		mi.y=GetSystemMetrics(SM_YVIRTUALSCREEN);
		mi.w=GetSystemMetrics(SM_CXVIRTUALSCREEN);
		mi.h=GetSystemMetrics(SM_CYVIRTUALSCREEN);

		//FIX RISOLUZIONI SIMILE A 1366x768
		if (((float)mi.w/(float)8)!=(mi.w/8)){
			mi.w=(int)((int)((float)mi.w/(float)8)+(float)1) * 8;
		}
		//if (((float)mi.h/(float)8)!=(mi.h/8)){
		//   mi.h=(int)((int)((float)mi.h/(float)8)+(float)1) * 8;
		//}

		monitorsInfo.push_back(mi);
		HDC hdc = GetDC(NULL);
		EnumDisplayMonitors(hdc, 0, ScreenCaptureNativeMonitorEnumProc, (LPARAM)this);
		ReleaseDC(NULL,hdc);
		//Sistema imagesInfo
		for(vector<MonitorInfo>::size_type i = 0; i < monitorsInfo.size(); i++) {
			if (i>=screenShotInfo.size()){
				ScreenShotInfo ii;
				newScreenShotInfo(&ii, monitorsInfo[i].w, monitorsInfo[i].h);
				screenShotInfo.push_back(ii);
			}else{
				if ((monitorsInfo[i].w!=screenShotInfo[i].w) || (monitorsInfo[i].h!=screenShotInfo[i].h)){
					termScreenShotInfo(&screenShotInfo[i]);
					newScreenShotInfo(&screenShotInfo[i], monitorsInfo[i].w, monitorsInfo[i].h);
				}
			}
		}
		for(vector<ScreenShotInfo>::size_type i = monitorsInfo.size(); i < screenShotInfo.size(); i++) {
			termScreenShotInfo(&screenShotInfo[i]);
			screenShotInfo.erase(screenShotInfo.begin() + i);
			i--;
		}
		monitorsCounter.reset();
	}
	if (monitorsInfo.size()==1){ //Non trovato nessun monitor
		return 1;
	}else{
		return monitorsInfo.size()-1;
	}
}

ScreenCaptureNative::MonitorInfo* ScreenCaptureNative::getMonitorInfo(int idx){
	if ((monitorsInfo.size()==1) && ((idx==0) || (idx==1))){ //Non trovato nessun monitor
		return &monitorsInfo[0];
	}else if ((idx>=0) && (idx<=(int)monitorsInfo.size()-1)){
		return &monitorsInfo[idx];
	}else{
		return NULL;
	}
}

ScreenCaptureNative::ScreenShotInfo* ScreenCaptureNative::getScreenShotInfo(int idx){
	if ((idx==1) && (screenShotInfo.size()==1)){ //Non trovato nessun monitor
		return &screenShotInfo[0];
	}else if (idx <= (int)screenShotInfo.size() - 1){
		return &screenShotInfo[idx];
	}else{
		return NULL;
	}
}

LRESULT CALLBACK ScreenCaptureNative::ScreenCaptureNativeWindowProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam){
	ScreenCaptureNative *pThis = NULL;
	if (msg == WM_NCCREATE){
        CREATESTRUCT* pCreate = (CREATESTRUCT*)lParam;
        pThis = (ScreenCaptureNative*)pCreate->lpCreateParams;
        SetWindowLongPtr(hwnd, GWLP_USERDATA, (LONG_PTR)pThis);
	}else{
		pThis = (ScreenCaptureNative*)GetWindowLongPtr(hwnd, GWLP_USERDATA);
    }
	return pThis->windowProc(hwnd, msg, wParam,lParam);	
}

LRESULT CALLBACK ScreenCaptureNative::windowProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam){
	switch(msg){
		case  WM_CREATE:
			debugger->print((char *)"WM_CREATE");
			//disableVisualEffect
		break;
		case  WM_QUERYENDSESSION:
			debugger->print((char *)"WM_QUERYENDSESSION");
			//restoreVisualEffect
		break;
		case  WM_ENDSESSION:
			debugger->print((char *)"WM_ENDSESSION");
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
					debugger->print((char *)"WTS_CONSOLE_CONNECT");
				break;
				case 0x2:	//#define WTS_CONSOLE_DISCONNECT
					debugger->print((char *)"WTS_CONSOLE_DISCONNECT");
				break;
				case 0x3:	//#define WTS_REMOTE_CONNECT
					debugger->print((char *)"WTS_REMOTE_CONNECT");
				break;
				case 0x4:	//#define WTS_REMOTE_DISCONNECT
					debugger->print((char *)"WTS_REMOTE_DISCONNECT");
					/////restoreVisualEffect
				break;
				case 0x5:	//#define WTS_SESSION_LOGON
					debugger->print((char *)"WTS_SESSION_LOGON");
					//disableVisualEffect
				break;
				case 0x6:	//#define WTS_SESSION_LOGOFF
					debugger->print((char *)"WTS_SESSION_LOGOFF");
					//restoreVisualEffect
				break;
				case 0x7:	//#define WTS_SESSION_LOCK
					debugger->print((char *)"WTS_SESSION_LOCK");
				break;
				case 0x8:	//#define WTS_SESSION_UNLOCK
					debugger->print((char *)"WTS_SESSION_UNLOCK");
				break;
				case 0x9:	//#define WTS_SESSION_REMOTE_CONTROL
					debugger->print((char *)"WTS_SESSION_REMOTE_CONTROL");
				break;
			}
		break;
		case WM_DESTROY:
			debugger->print((char *)"WM_DESTROY");
			//restoreVisualEffect
			if (loadLib.WTSUnRegisterSessionNotificationFunc()) {
				loadLib.WTSUnRegisterSessionNotificationFunc()(hwnd);
			}
			PostQuitMessage(0);
		break;
    }
    return DefWindowProc(hwnd, msg, wParam, lParam);
}

DWORD WINAPI ScreenCaptureNativeCreateWindowThreadProc( LPVOID lpParam ){
    ScreenCaptureNative *pThis = reinterpret_cast<ScreenCaptureNative * > (lpParam);
	pThis->createWindow();
	return 1;
}

void ScreenCaptureNative::createWindow() {
	//CREA FINESTRA
	WNDCLASSEX wc;    
	HINSTANCE hInstance = GetModuleHandle(NULL);
	wc.cbSize        = sizeof(WNDCLASSEX);
	wc.style         = 0;
	wc.lpfnWndProc   = ScreenCaptureNativeWindowProc;
	wc.cbClsExtra    = 0;
	wc.cbWndExtra    = 0;
	wc.hInstance     = hInstance;
	wc.hIcon         = NULL;
	wc.hCursor       = NULL;
	wc.hbrBackground = (HBRUSH)(COLOR_WINDOW+1);
	wc.lpszMenuName  = NULL;
	wc.lpszClassName = "dwascreencapture";
	wc.hIconSm       = NULL;
	
	if(RegisterClassEx(&wc)){
		hwndwts=CreateWindowEx(0, "dwascreencapture",  "dwascreencapture", WS_EX_PALETTEWINDOW, CW_USEDEFAULT, CW_USEDEFAULT, 100, 100, NULL, NULL, hInstance, this);
		if (hwndwts!=NULL){
			if (loadLib.WTSRegisterSessionNotificationFunc()) {
				loadLib.WTSRegisterSessionNotificationFunc()(hwndwts,0);
			}
			UpdateWindow(hwndwts);
		}else{
			debugger->print((char *)"CreateWindowEx Failed");
		}
	}else{
		debugger->print((char *)"RegisterClassEx Failed");
	}
	if (hwndwts!=NULL){
		MSG messages;
		while (GetMessage (&messages, NULL, 0, 0)){
			TranslateMessage(&messages);
			DispatchMessage(&messages);
		}
	}
}

bool ScreenCaptureNative::initialize() {
	
	cursorHandle=NULL;
	cursorX=0;
	cursorY=0;
	cursoroffsetX=0;
	cursoroffsetY=0;
	cursorW=0;
	cursorH=0;
	cursorID=0;

	activeWinHandle=NULL;
	activeWinID=0;
	activeWinX=0;
	activeWinY=0;
	activeWinW=0;
	activeWinH=0;

	mousebtn1Down=false;
	mousebtn2Down=false;
	mousebtn3Down=false;
	ctrlDown=false;
	altDown=false;
	shiftDown=false;
	wcsncpy(prevDesktopName,L"",0);


	//GESTIONE DPI Legge in modo corretto le impostazioni dello schermo (risoluzione ecc..)
	if ((loadLib.isAvailableShCore()) && (loadLib.SetProcessDpiAwarenessFunc())){
		loadLib.SetProcessDpiAwarenessFunc()(2); //PROCESS_PER_MONITOR_DPI_AWARE 
	}else if ((loadLib.isAvailableUser32()) && (loadLib.SetProcessDPIAwareFunc())){
		loadLib.SetProcessDPIAwareFunc()();
	}

	if (loadLib.WTSRegisterSessionNotificationFunc()) {
		CreateThread(0, 0, ScreenCaptureNativeCreateWindowThreadProc, this, 0, NULL);
		Sleep(1000); //Attende che lo schermo diventi nero
    }	

		
	//VERIFICA IL MirrorDriver
	/*resMirror=-1;
	vector<DISPLAY_DEVICE> devices;
	map<int,DEVMODE> settings;
	resMirror = detectMirrorDriver(devices,settings);
	if (resMirror>=0){
		deviceDisplay = devices[resMirror];
		deviceMode = settings[resMirror];
	}*/
	
	/*if (resMirror>=0){
		hsrcDC = GetDC(GetDesktopWindow());
	}else{*/
		//hsrcDC = GetDC(NULL);
	//}
	
	//INIZIALIZZA I MONITOR
	getMonitorCount();

	return true;
}

void ScreenCaptureNative::terminate() {
	for(vector<ScreenShotInfo>::size_type i = 0; i < screenShotInfo.size(); i++) {
		termScreenShotInfo(&screenShotInfo[i]);
	}
	screenShotInfo.clear();
	monitorsInfo.clear();
	/*if (resMirror>=0){
		DeleteDC(hsrcDC);
		deviceMode.dmPelsWidth = 0;
		deviceMode.dmPelsHeight = 0;
		//deviceMode.dmBitsPerPel = 0;
		deviceMode.dmDeviceName[resMirror] = 0;
		deviceMode.dmFields = DM_PELSWIDTH |
                    DM_PELSHEIGHT | DM_POSITION;
		if(ChangeDisplaySettingsEx(deviceDisplay.DeviceName, &deviceMode, 0, CDS_UPDATEREGISTRY, 0)>=0){
			ChangeDisplaySettingsEx(deviceDisplay.DeviceName, &deviceMode, 0, 0, 0);
		}
		//if(ChangeDisplaySettingsEx(deviceDisplay.DeviceName, NULL, 0, CDS_UPDATEREGISTRY, 0)>=0){
		//	ChangeDisplaySettingsEx(deviceDisplay.DeviceName, NULL, 0, 0, 0);
		//}
	}else{*/
		//ReleaseDC(NULL,hsrcDC);
	//}
	cursorHandle = NULL;
	////restoreVisualEffect
	if (hwndwts){
		SendMessage(hwndwts, WM_DESTROY, 0, 0);
		hwndwts=NULL;
	}	
}

void ScreenCaptureNative::newScreenShotInfo(ScreenShotInfo* ii, int w, int h) {
	ii->w = w;
	ii->h = h;
	ii->data = NULL;
	ii->shotID=-1;
	ii->intervallCounter.reset();
}

void ScreenCaptureNative::initScreenShotInfo(ScreenShotInfo* ii) {
	termScreenShotInfo(ii);
	/*if (resMirror>=0){
		WORD drvExtraSaved = deviceMode.dmDriverExtra;
		deviceMode.dmDriverExtra = drvExtraSaved;
		deviceMode.dmPelsWidth = w;
		deviceMode.dmPelsHeight = h;
		deviceMode.dmBitsPerPel = 0;
		deviceMode.dmPosition.x = 0;
		deviceMode.dmPosition.y = 0;
		deviceMode.dmDeviceName[0] = '\0';
		deviceMode.dmFields = DM_BITSPERPEL | DM_PELSWIDTH |
                      DM_PELSHEIGHT | DM_POSITION;
		if(ChangeDisplaySettingsEx(deviceDisplay.DeviceName, &deviceMode, 0, CDS_UPDATEREGISTRY, 0)>=0){
			ChangeDisplaySettingsEx(deviceDisplay.DeviceName, &deviceMode, 0, 0, 0);
		}
	}*/
	ZeroMemory(&ii->bitmapInfo, sizeof(BITMAPINFO));
	ii->bitmapInfo.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
	ii->bitmapInfo.bmiHeader.biBitCount = 24;
	ii->bitmapInfo.bmiHeader.biCompression = BI_RGB;
	ii->bitmapInfo.bmiHeader.biPlanes = 1;
	ii->bitmapInfo.bmiHeader.biWidth = ii->w;
	ii->bitmapInfo.bmiHeader.biHeight = -ii->h;
	ii->hsrcDC = GetDC(NULL);
	ii->hdestDC = CreateCompatibleDC(NULL);
	void *buffer;
	ii->hbmDIB = CreateDIBSection(ii->hdestDC, (BITMAPINFO*)&ii->bitmapInfo, DIB_RGB_COLORS, &buffer, NULL, 0);
	ii->hbmDIBOLD = (HBITMAP)SelectObject(ii->hdestDC, ii->hbmDIB);
	ii->data = (unsigned char*)buffer;

	/*ii->hbitmap = CreateCompatibleBitmap(ii->hsrcDC, ii->w,ii->h);
	ii->hbitmapOLD = (HBITMAP)SelectObject(ii->hdestDC, ii->hbitmap);*/
	/*if (resMirror>=0){
		//ReleaseDC(GetDesktopWindow(),hsrcDC);
		ReleaseDC(NULL,hsrcDC);
		hsrcDC=CreateDC(deviceDisplay.DeviceName, 0, 0, 0);
	}*/
	ii->shotID=0;
}

void ScreenCaptureNative::termScreenShotInfo(ScreenShotInfo* ii) {
	if (ii->shotID>=0){
		SelectObject(ii->hdestDC,ii->hbmDIBOLD);
		DeleteObject(ii->hbmDIB);
		DeleteDC(ii->hdestDC);
		ReleaseDC(NULL,ii->hsrcDC);
		ii->data = NULL;
		//resetScreenshotData(ii);
		ii->shotID=-1;
	}
}

BOOL CALLBACK checkLayered(HWND hWnd, LPARAM lParam) {
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


/*
bool ScreenCaptureNative::captureCursor(int monitor, int* info, long& id, unsigned char** rgbdata) {
	int cursorVis=1;
	CURSORINFO appCursorInfo;
	appCursorInfo.cbSize = sizeof(CURSORINFO);
	if (GetCursorInfo(&appCursorInfo)){
		if (appCursorInfo.flags!=0){
			cursorVis=1;
			cursorX=appCursorInfo.ptScreenPos.x;
			cursorY=appCursorInfo.ptScreenPos.y;
			if ((appCursorInfo.hCursor!=cursorHandle) || (id==-1)){
				cursorHandle=appCursorInfo.hCursor;
				ICONINFO info;
				if (GetIconInfo(cursorHandle, &info)){
					BITMAP bmMask;
					GetObject(info.hbmMask, sizeof(BITMAP), (LPVOID)&bmMask);
					if (bmMask.bmPlanes != 1 || bmMask.bmBitsPixel != 1) {
						DeleteObject(info.hbmMask);
					}else{
						bool bok = false;
						//unsigned char* dataNorm = NULL;
						//unsigned char* dataMask = NULL;
						bool isColorShape = (info.hbmColor != NULL);
						int w = bmMask.bmWidth;
						int h = isColorShape ? bmMask.bmHeight : bmMask.bmHeight/2;
						//int nbit = bmMask.bmWidthBytes;

						//IMAGE
						HDC hdstImage = CreateCompatibleDC(NULL);
						BITMAPINFO biImage;
						ZeroMemory(&biImage, sizeof(BITMAPINFO));
						biImage.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
						biImage.bmiHeader.biBitCount = 32;
						biImage.bmiHeader.biCompression = BI_RGB;
						biImage.bmiHeader.biPlanes = 1;
						biImage.bmiHeader.biWidth = w;
						biImage.bmiHeader.biHeight = -h;
						biImage.bmiHeader.biSizeImage = 0;
						biImage.bmiHeader.biXPelsPerMeter = 0;
						biImage.bmiHeader.biYPelsPerMeter = 0;
						biImage.bmiHeader.biClrUsed = 0;
						biImage.bmiHeader.biClrImportant = 0;
						void *bufferImage;
						HANDLE hbmDIBImage = CreateDIBSection(hdstImage, (BITMAPINFO*)&biImage, DIB_RGB_COLORS, &bufferImage, NULL, 0);
						HANDLE hbmDIBOLDImage = (HBITMAP)SelectObject(hdstImage, hbmDIBImage);
						unsigned char* appDataImage = (unsigned char*)bufferImage;

						//MASK
						HDC hdstMask = CreateCompatibleDC(NULL);
						BITMAPINFO biMask;
						ZeroMemory(&biMask, sizeof(BITMAPINFO));
						biMask.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
						biMask.bmiHeader.biBitCount = 32;
						biMask.bmiHeader.biCompression = BI_RGB;
						biMask.bmiHeader.biPlanes = 1;
						biMask.bmiHeader.biWidth = w;
						biMask.bmiHeader.biHeight = -h;
						biMask.bmiHeader.biSizeImage = 0;
						biMask.bmiHeader.biXPelsPerMeter = 0;
						biMask.bmiHeader.biYPelsPerMeter = 0;
						biMask.bmiHeader.biClrUsed = 0;
						biMask.bmiHeader.biClrImportant = 0;
						void *bufferMask;
						HANDLE hbmDIBMask = CreateDIBSection(hdstMask, (BITMAPINFO*)&biMask, DIB_RGB_COLORS, &bufferMask, NULL, 0);
						HANDLE hbmDIBOLDMask = (HBITMAP)SelectObject(hdstMask, hbmDIBMask);
						unsigned char* appDataMask = (unsigned char*)bufferMask;


						//NORMAL
						HDC hdstNormal = CreateCompatibleDC(NULL);
						BITMAPINFO biNormal;
						ZeroMemory(&biNormal, sizeof(BITMAPINFO));
						biNormal.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
						biNormal.bmiHeader.biBitCount = 32;
						biNormal.bmiHeader.biCompression = BI_RGB;
						biNormal.bmiHeader.biPlanes = 1;
						biNormal.bmiHeader.biWidth = w;
						biNormal.bmiHeader.biHeight = -h;
						biNormal.bmiHeader.biSizeImage = 0;
						biNormal.bmiHeader.biXPelsPerMeter = 0;
						biNormal.bmiHeader.biYPelsPerMeter = 0;
						biNormal.bmiHeader.biClrUsed = 0;
						biNormal.bmiHeader.biClrImportant = 0;
						void *bufferNormal;
						HANDLE hbmDIBNormal = CreateDIBSection(hdstNormal, (BITMAPINFO*)&biNormal, DIB_RGB_COLORS, &bufferNormal, NULL, 0);
						HANDLE hbmDIBOLDNormal = (HBITMAP)SelectObject(hdstNormal, hbmDIBNormal);
						unsigned char* appDataNormal = (unsigned char*)bufferNormal;



						DrawIconEx(hdstImage, 0, 0, (HICON)cursorHandle, 0, 0, 0, NULL, DI_IMAGE);
						DrawIconEx(hdstMask, 0, 0, (HICON)cursorHandle, 0, 0, 0, NULL, DI_MASK);
						DrawIconEx(hdstNormal, 0, 0, (HICON)cursorHandle, 0, 0, 0, NULL, DI_NORMAL);


						bool cursorCheckMask=true;
						int isck = 0;
						for (int y=0; y<h; y++) {
							for (int x=0; x<w; x++) {
								if ((appDataImage[isck + 3])>0) {
									cursorCheckMask = false;
									break;
								}
								isck += 4;
							}
						}


						unsigned char* cursorData = NULL;
						cursorData = (unsigned char*)malloc(((w*3) * (h*3)) * 4);

						int is = 0;
						int id = 0;
						for (int y=0; y<h; y++) {
							int appis=is;
							for (int x=0; x<w; x++) {
								unsigned char r;
								unsigned char g;
								unsigned char b;
								unsigned char a;

								if (cursorCheckMask){
									r = appDataImage[is + 2];
									g = appDataImage[is + 1];
									b = appDataImage[is];
									if ((appDataMask[is + 2]==0) && (appDataMask[is + 1]==0) && (appDataMask[is]==0)){
										a = 255;
									}else{
										if ((appDataMask[is + 2]==appDataImage[is + 2]) && (appDataMask[is + 1]==appDataImage[is + 1]) && (appDataMask[is]==appDataImage[is])){
											r = 128;
											g = 128;
											b = 128;
											a = 255;
										}else{
											a = 0;
										}
									}
								}else{
									r = appDataImage[is + 2];
									g = appDataImage[is + 1];
									b = appDataImage[is];
									a = appDataImage[is + 3];
								}
								cursorData[id] = r;
								cursorData[id + 1] = g;
								cursorData[id + 2] = b;
								cursorData[id + 3] = a;
								id += 4;
								is += 4;
							}

							is=appis;
							for (int x=0; x<w; x++) {
								cursorData[id] = appDataMask[is + 3];
								cursorData[id + 1] = appDataMask[is + 3];
								cursorData[id + 2] = appDataMask[is + 3];
								cursorData[id + 3] = 0;
								id += 4;
								is += 4;
							}

							is=appis;
							for (int x=0; x<w; x++) {
								cursorData[id] = appDataNormal[is + 3];
								cursorData[id + 1] = appDataNormal[is + 3];
								cursorData[id + 2] = appDataNormal[is + 3];
								cursorData[id + 3] = 0;
								id += 4;
								is += 4;
							}

						}

						//NO TRANSPARENT
						is = 0;
						for (int y=0; y<h; y++) {
							int appis=is;
							for (int x=0; x<w; x++) {
								unsigned char r;
								unsigned char g;
								unsigned char b;
								unsigned char a;

								r = appDataImage[is + 2];
								g = appDataImage[is + 1];
								b = appDataImage[is];
								a = 255;
								cursorData[id] = r;
								cursorData[id + 1] = g;
								cursorData[id + 2] = b;
								cursorData[id + 3] = a;
								id += 4;
								is += 4;
							}

							is=appis;
							for (int x=0; x<w; x++) {
								unsigned char r;
								unsigned char g;
								unsigned char b;
								unsigned char a;

								r = appDataMask[is + 2];
								g = appDataMask[is + 1];
								b = appDataMask[is];
								a = 255;
								cursorData[id] = r;
								cursorData[id + 1] = g;
								cursorData[id + 2] = b;
								cursorData[id + 3] = a;
								id += 4;
								is += 4;
							}

							is=appis;
							for (int x=0; x<w; x++) {
								unsigned char r;
								unsigned char g;
								unsigned char b;
								unsigned char a;

								r = appDataNormal[is + 2];
								g = appDataNormal[is + 1];
								b = appDataNormal[is];
								a = 255;
								cursorData[id] = r;
								cursorData[id + 1] = g;
								cursorData[id + 2] = b;
								cursorData[id + 3] = a;
								id += 4;
								is += 4;
							}

						}

						//TRANSPARENT
						is = 0;
						for (int y=0; y<h; y++) {
							int appis=is;
							for (int x=0; x<w; x++) {
								unsigned char r;
								unsigned char g;
								unsigned char b;
								unsigned char a;

								r = appDataImage[is + 2];
								g = appDataImage[is + 1];
								b = appDataImage[is];
								a = appDataImage[is + 3];
								cursorData[id] = r;
								cursorData[id + 1] = g;
								cursorData[id + 2] = b;
								cursorData[id + 3] = a;
								id += 4;
								is += 4;
							}

							is=appis;
							for (int x=0; x<w; x++) {
								unsigned char r;
								unsigned char g;
								unsigned char b;
								unsigned char a;

								r = appDataMask[is + 2];
								g = appDataMask[is + 1];
								b = appDataMask[is];
								a = appDataMask[is + 3];
								cursorData[id] = r;
								cursorData[id + 1] = g;
								cursorData[id + 2] = b;
								cursorData[id + 3] = a;
								id += 4;
								is += 4;
							}

							is=appis;
							for (int x=0; x<w; x++) {
								unsigned char r;
								unsigned char g;
								unsigned char b;
								unsigned char a;

								r = appDataNormal[is + 2];
								g = appDataNormal[is + 1];
								b = appDataNormal[is];
								a = appDataNormal[is + 3];
								cursorData[id] = r;
								cursorData[id + 1] = g;
								cursorData[id + 2] = b;
								cursorData[id + 3] = a;
								id += 4;
								is += 4;
							}

						}



						bok = true;


						if (bok){
							cursorW=w*3;
							cursorH=h*3;
							int offsetX = 0;
							int offsetY = 0;
							if (info.fIcon==FALSE){
								offsetX = info.xHotspot;
								offsetY = info.yHotspot;
							}else{
								offsetX = w/2;
								offsetY = h/2;
							}
							cursoroffsetX=offsetX;
							cursoroffsetY=offsetY;
							*rgbdata = cursorData;
							cursorID++;
						}

						SelectObject(hdstImage, hbmDIBOLDImage);
						DeleteObject(hbmDIBImage);
						DeleteDC(hdstImage);

						SelectObject(hdstMask, hbmDIBOLDMask);
						DeleteObject(hbmDIBMask);
						DeleteDC(hdstMask);

						SelectObject(hdstNormal, hbmDIBOLDNormal);
						DeleteObject(hbmDIBNormal);
						DeleteDC(hdstNormal);

					}
				}
			}
		}else{
			//Cursore nascosto
			cursorVis=0;
			cursorW=0;
			cursorH=0;
			cursoroffsetX=0;
			cursoroffsetY=0;
			if (cursorHandle!=NULL){
				cursorHandle=NULL;
				cursorID++;
			}
		}
	}else{
		return false;
	}
	info[0]=cursorVis;
	MonitorInfo* mi = getMonitorInfo(monitor);
	if (mi!=NULL){
		info[1]=cursorX-mi->x;
		info[2]=cursorY-mi->y;
	}else{
		info[1]=cursorX;
		info[2]=cursorY;
	}
	info[3]=cursorW;
	info[4]=cursorH;
	info[5]=cursoroffsetX;
	info[6]=cursoroffsetY;
	id=cursorID;
	return true;
}*/


bool ScreenCaptureNative::captureCursor(int monitor, int* info, long& id, unsigned char** rgbdata) {
	int cursorVis=1; 
	CURSORINFO appCursorInfo;
	appCursorInfo.cbSize = sizeof(CURSORINFO);
	if (GetCursorInfo(&appCursorInfo)){
		cursorX=appCursorInfo.ptScreenPos.x;
		cursorY=appCursorInfo.ptScreenPos.y;
		if (appCursorInfo.flags!=0){
			cursorVis=1;
			if ((appCursorInfo.hCursor!=cursorHandle) || (id==-1)){
				bool bok = false;
				cursorHandle=appCursorInfo.hCursor;
				ICONINFO info;
				if (GetIconInfo(cursorHandle, &info)){
					BITMAP bmMask;
					GetObject(info.hbmMask, sizeof(BITMAP), (LPVOID)&bmMask);					
					if (bmMask.bmPlanes != 1 || bmMask.bmBitsPixel != 1) {
						DeleteObject(info.hbmMask);
					}else{
						//unsigned char* dataNorm = NULL;
						//unsigned char* dataMask = NULL;
						bool isColorShape = (info.hbmColor != NULL);
						int w = bmMask.bmWidth;
						int h = isColorShape ? bmMask.bmHeight : bmMask.bmHeight/2;
						//int nbit = bmMask.bmWidthBytes;

						//IMAGE
						HDC hdstImage = CreateCompatibleDC(NULL);
						BITMAPINFO biImage;
						ZeroMemory(&biImage, sizeof(BITMAPINFO));
						biImage.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
						biImage.bmiHeader.biBitCount = 32;
						biImage.bmiHeader.biCompression = BI_RGB;
						biImage.bmiHeader.biPlanes = 1;
						biImage.bmiHeader.biWidth = w;
						biImage.bmiHeader.biHeight = -h;
						biImage.bmiHeader.biSizeImage = 0;
						biImage.bmiHeader.biXPelsPerMeter = 0;
						biImage.bmiHeader.biYPelsPerMeter = 0;
						biImage.bmiHeader.biClrUsed = 0;
						biImage.bmiHeader.biClrImportant = 0;
						void *bufferImage;
						HANDLE hbmDIBImage = CreateDIBSection(hdstImage, (BITMAPINFO*)&biImage, DIB_RGB_COLORS, &bufferImage, NULL, 0);
						HANDLE hbmDIBOLDImage = (HBITMAP)SelectObject(hdstImage, hbmDIBImage);
						unsigned char* appDataImage = (unsigned char*)bufferImage;

						//MASK
						HDC hdstMask = CreateCompatibleDC(NULL);
						BITMAPINFO biMask;
						ZeroMemory(&biMask, sizeof(BITMAPINFO));
						biMask.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
						biMask.bmiHeader.biBitCount = 32;
						biMask.bmiHeader.biCompression = BI_RGB;
						biMask.bmiHeader.biPlanes = 1;
						biMask.bmiHeader.biWidth = w;
						biMask.bmiHeader.biHeight = -h;
						biMask.bmiHeader.biSizeImage = 0;
						biMask.bmiHeader.biXPelsPerMeter = 0;
						biMask.bmiHeader.biYPelsPerMeter = 0;
						biMask.bmiHeader.biClrUsed = 0;
						biMask.bmiHeader.biClrImportant = 0;
						void *bufferMask;
						HANDLE hbmDIBMask = CreateDIBSection(hdstMask, (BITMAPINFO*)&biMask, DIB_RGB_COLORS, &bufferMask, NULL, 0);
						HANDLE hbmDIBOLDMask = (HBITMAP)SelectObject(hdstMask, hbmDIBMask);
						unsigned char* appDataMask = (unsigned char*)bufferMask;
						
						bool cursorCheckMask=true;
						unsigned char* cursorData = NULL;
						if (DrawIconEx(hdstImage, 0, 0, (HICON)cursorHandle, 0, 0, 0, NULL, DI_IMAGE)) {
							int isck = 0;
							for (int y=0; y<h; y++) {
								for (int x=0; x<w; x++) {
									if ((appDataImage[isck + 3])>0) {
										cursorCheckMask = false;
										break;
									}
									isck += 4;
								}
							}
							if (DrawIconEx(hdstMask, 0, 0, (HICON)cursorHandle, 0, 0, 0, NULL, DI_MASK)) {
								cursorData = (unsigned char*)malloc((w * h) * 4);
								int is = 0;
								int id = 0;
								for (int y=0; y<h; y++) {
									for (int x=0; x<w; x++) {
										unsigned char r;
										unsigned char g;
										unsigned char b;
										unsigned char a;
										if (cursorCheckMask){
											r = appDataImage[is + 2];
											g = appDataImage[is + 1];
											b = appDataImage[is];
											if ((appDataMask[is + 2]==0) && (appDataMask[is + 1]==0) && (appDataMask[is]==0)){
												a = 255;
											}else{
												if ((appDataMask[is + 2]==appDataImage[is + 2]) && (appDataMask[is + 1]==appDataImage[is + 1]) && (appDataMask[is]==appDataImage[is])){
													r = 128;
													g = 128;
													b = 128;
													a = 255;
												}else{
													a = 0;
												}
											}
										}else{
											r = appDataImage[is + 2];
											g = appDataImage[is + 1];
											b = appDataImage[is];
											a = appDataImage[is + 3];
										}
										cursorData[id] = r;
										cursorData[id + 1] = g;
										cursorData[id + 2] = b;
										cursorData[id + 3] = a;
										id += 4;
										is += 4;
									}
								}
								bok = true;
							}
						}
						if (bok){
							cursorW=w;
							cursorH=h;
							int offsetX = 0;
							int offsetY = 0;
							if (info.fIcon==FALSE){
								offsetX = info.xHotspot;
								offsetY = info.yHotspot;
							}else{
								offsetX = w/2;
								offsetY = h/2;
							}
							cursoroffsetX=offsetX;
							cursoroffsetY=offsetY;							
							*rgbdata = cursorData;
							cursorID++;						
						}

						SelectObject(hdstImage, hbmDIBOLDImage);
						DeleteObject(hbmDIBImage);
						DeleteDC(hdstImage);

						SelectObject(hdstMask, hbmDIBOLDMask);
						DeleteObject(hbmDIBMask);
						DeleteDC(hdstMask);
					}
				}
				if (!bok){
					getCursorImage(CURSOR_TYPE_ARROW_18_18,&cursorW,&cursorH,&cursoroffsetX,&cursoroffsetY,rgbdata);
					cursorID++;
				}
			}
		}else{ //Cursore nascosto
			cursorVis=1;
			cursorW=0;
			cursorH=0;
			cursoroffsetX=0;
			cursoroffsetY=0;
			if ((cursorHandle!=NULL) || (id==-1)){
				cursorHandle=NULL;
				getCursorImage(CURSOR_TYPE_ARROW_18_18,&cursorW,&cursorH,&cursoroffsetX,&cursoroffsetY,rgbdata);
				cursorID++;
			}
		}
	}else{
		POINT point;
		if (GetCursorPos(&point)) {
			cursorVis=1;
			cursorX=point.x;
			cursorY=point.y;
			if (id==-1){
				cursorHandle=NULL;
				getCursorImage(CURSOR_TYPE_ARROW_18_18,&cursorW,&cursorH,&cursoroffsetX,&cursoroffsetY,rgbdata);
				cursorID++;
			}
		}else{
			return false;
		}
	}
	info[0]=cursorVis;
	MonitorInfo* mi = getMonitorInfo(monitor);
	if (mi!=NULL){
		info[1]=cursorX-mi->x;
		info[2]=cursorY-mi->y;		
	}else{
		info[1]=cursorX;
		info[2]=cursorY;
	}
	info[3]=cursorW;
	info[4]=cursorH;
	info[5]=cursoroffsetX;
	info[6]=cursoroffsetY;
	id=cursorID;
	return true;
}



HDESK ScreenCaptureNative::getInputDesktop() {
	HDESK hInputDesktop = OpenInputDesktop(0, FALSE,
			DESKTOP_CREATEMENU | DESKTOP_CREATEWINDOW | DESKTOP_ENUMERATE
					| DESKTOP_HOOKCONTROL | DESKTOP_READOBJECTS
					| DESKTOP_SWITCHDESKTOP | DESKTOP_JOURNALPLAYBACK
					| DESKTOP_JOURNALRECORD | DESKTOP_WRITEOBJECTS
					| GENERIC_WRITE);
	return hInputDesktop;
}

HDESK ScreenCaptureNative::getDesktop(char* name) {
	HDESK desktop = OpenDesktop(name, 0, FALSE,
			DESKTOP_CREATEMENU | DESKTOP_CREATEWINDOW | DESKTOP_ENUMERATE
					| DESKTOP_HOOKCONTROL | DESKTOP_READOBJECTS
					| DESKTOP_SWITCHDESKTOP | DESKTOP_JOURNALPLAYBACK
					| DESKTOP_JOURNALRECORD | DESKTOP_WRITEOBJECTS
					| GENERIC_WRITE);
	return desktop;
}

int ScreenCaptureNative::setCurrentThreadDesktop() { //0 NON CAMBIATO //1 CAMBIATO //2 UAC
	/*if (resMirror>=0){
		return false;
	}*/
	
	int iret=0;
	if (m_osVerInfo.dwPlatformId == VER_PLATFORM_WIN32_NT){ //isWinNTFamily
		HDESK desktop = getInputDesktop();
		bool checkuac=true;
		if (desktop){
			wchar_t  curDesktopName[1024];
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

bool ScreenCaptureNative::selectDesktop(char* name) {
	HDESK desktop = NULL;
	desktop = getDesktop(name);
	bool bret=false;
	if (SetThreadDesktop(desktop)==TRUE){
		bret=true;
	}
	CloseDesktop(desktop);
	return bret;
}

/*bool ScreenCaptureNative::getActiveWinPos(long* id, int* info){
	if (activeWinHandle!=NULL){
		*id=activeWinID;
		info[0]=activeWinX;
		info[1]=activeWinY;
		info[2]=activeWinW;
		info[3]=activeWinH;
		return true;
	}else{
		return false;
	}
}*/


long ScreenCaptureNative::captureScreen(int monitor, int distanceFrameMs, CAPTURE_IMAGE* capimage){
	capimage->width = 0;
	capimage->height = 0;
	
	int x = 0;
	int y = 0;
	int w = 0;
	int h = 0;
	
	MonitorInfo* mi = getMonitorInfo(monitor);
	if (mi==NULL){
		return -2; //Identifica Monitor non trovato
	}
	x=mi->x;
	y=mi->y;
	w=mi->w;
	h=mi->h;
	ScreenShotInfo* ii = getScreenShotInfo(monitor);	
	if (ii==NULL) {
		return -3; //ScreenShotInfo non found
	}

	int itd=setCurrentThreadDesktop();
	if (itd==2){
		return -1; //UAC Need
	}

	if (itd==1 || ii->shotID==-1){
		initScreenShotInfo(ii);
	}
	if ((ii->shotID==0) || (ii->intervallCounter.getCounter()>=distanceFrameMs)) {
		ii->intervallCounter.reset();
		//CHECK WINDOWS LAYERED
		DWORD flgcpt = SRCCOPY;
		BOOL captureBlt = false;
		EnumWindows(checkLayered, reinterpret_cast<LPARAM>(&captureBlt));
		if (captureBlt) {
			flgcpt = SRCCOPY | CAPTUREBLT;
		}
		//SCREEN CAPTURE
		if (!BitBlt(ii->hdestDC, 0, 0, w, h, ii->hsrcDC, x, y, flgcpt)) {
			char msgerr[500];
			sprintf(msgerr,"BitBlt error code: %ld",GetLastError());
			debugger->print(msgerr);
			return -2; //bitblt error
		}
		ii->shotID+=1;
	}

	capimage->data = ii->data;
	capimage->bpp=24;
	capimage->bpc=3;
	capimage->width = w;
	capimage->height = h;
	return ii->shotID;
}

void ScreenCaptureNative::sendInputs(INPUT (&inputs)[20],int max){
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


bool ScreenCaptureNative::isExtendedKey(int key){
	return key == VK_RMENU || key == VK_RCONTROL || key == VK_NUMLOCK || key == VK_INSERT || key == VK_DELETE
		|| key == VK_HOME || key == VK_END || key == VK_PRIOR || key == VK_NEXT
		|| key == VK_UP || key == VK_DOWN || key == VK_LEFT || key == VK_RIGHT ||key == VK_APPS
        || key == VK_RWIN || key == VK_LWIN || key == VK_MENU || key == VK_CONTROL || key == VK_CANCEL|| key == VK_DIVIDE
		|| key == VK_NUMPAD0 || key == VK_NUMPAD1 || key == VK_NUMPAD2 || key == VK_NUMPAD3 || key == VK_NUMPAD4 || key == VK_NUMPAD5
		|| key == VK_NUMPAD6 || key == VK_NUMPAD7 || key == VK_NUMPAD8 || key == VK_NUMPAD9;

}

int ScreenCaptureNative::getKeyCode(const char* key){
	if (strcmp(key,"CONTROL")==0){
		return VK_CONTROL;
	}else if (strcmp(key,"ALT")==0){
		return VK_MENU;
	}else if (strcmp(key,"SHIFT")==0){
		return VK_SHIFT;
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

void ScreenCaptureNative::addCtrlAltShift(INPUT (&inputs)[20],int &p,bool ctrl, bool alt, bool shift){
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

void ScreenCaptureNative::inputKeyboard(const char* type,const char* key, bool ctrl, bool alt, bool shift, bool command){
	INPUT inputs[20];
	int p=0;
	if (strcmp(type,"CHAR")==0){
		bool sendunicode=true;
		SHORT vkKeyScanResult = 0;
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
				threadId = GetWindowThreadProcessId(hwnd, 0);
				hklCurrent = GetKeyboardLayout(threadId);
				vkKeyScanResult = VkKeyScanExW(atoi(key), hklCurrent);
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

	}else if (strcmp(type,"CTRLALTCANC")==0){
		debugger->print((char *)"inputKeyboard CTRLALTCANC");
		if (selectDesktop((char *)"Winlogon")) {
			HWND hwndCtrlAltDel = FindWindow("SAS window class", "SAS window");
			if (hwndCtrlAltDel == NULL) {
				hwndCtrlAltDel = HWND_BROADCAST;
			}
			PostMessage(hwndCtrlAltDel, WM_HOTKEY, 0, MAKELONG(MOD_ALT | MOD_CONTROL, VK_DELETE));
			wcsncpy(prevDesktopName,L"",0); //Alla prossima cattura si posizione sul desktop corretto
		}
	}

	sendInputs(inputs,p);
}

void ScreenCaptureNative::addInputMouse(INPUT (&inputs)[20],int &p,int x, int y,DWORD dwFlags,int mouseData,int tm){
	inputs[p].type= INPUT_MOUSE;
	inputs[p].mi.dx = x;
	inputs[p].mi.dy = y;
	inputs[p].mi.dwFlags = dwFlags;
	inputs[p].mi.time = tm;
	inputs[p].mi.dwExtraInfo = 0;
	inputs[p].mi.mouseData = mouseData;
	p++;
}

void ScreenCaptureNative::inputMouse(int monitor, int x, int y, int button, int wheel, bool ctrl, bool alt, bool shift, bool command){
	INPUT inputs[20];
	int p=0;
	addCtrlAltShift(inputs,p,ctrl,alt,shift);

	int appx = 0;
	int appy = 0;
	int mouseData=0;
	DWORD dwFlags = 0;
    if ((x!=-1) && (y!=-1)) {
		int mx=x;
		int my=y;
		MonitorInfo* mi = getMonitorInfo(monitor);
		if (mi!=NULL){
			mx=mx+mi->x;
			my=my+mi->y;
		}
        dwFlags = MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_MOVE | MOUSEEVENTF_VIRTUALDESK;
		UINT16 desktopWidth =  GetSystemMetrics(SM_CXVIRTUALSCREEN);
		UINT16 desktopHeight = GetSystemMetrics(SM_CYVIRTUALSCREEN);

		int desktopOffsetX = GetSystemMetrics(SM_XVIRTUALSCREEN);
		int desktopOffsetY = GetSystemMetrics(SM_YVIRTUALSCREEN);
		appx = (int)((mx - desktopOffsetX) * 65535 / (desktopWidth));
		appy = (int)((my - desktopOffsetY) * 65535 / (desktopHeight));
    }
	if (button==64) { //CLICK
		addInputMouse(inputs,p,appx,appy,dwFlags | MOUSEEVENTF_LEFTDOWN,mouseData,5);
		addInputMouse(inputs,p,appx,appy,dwFlags | MOUSEEVENTF_LEFTUP,mouseData,0);
	}else if (button==128) { //DBLCLICK
		addInputMouse(inputs,p,appx,appy,dwFlags | MOUSEEVENTF_LEFTDOWN,mouseData,5);
		addInputMouse(inputs,p,appx,appy,dwFlags | MOUSEEVENTF_LEFTUP,mouseData,100);
		addInputMouse(inputs,p,appx,appy,dwFlags | MOUSEEVENTF_LEFTDOWN,mouseData,5);
		addInputMouse(inputs,p,appx,appy,dwFlags | MOUSEEVENTF_LEFTUP,mouseData,0);
	}else{
		if (button!=-1) {
			if ((button & 1) && (!mousebtn1Down)){
				dwFlags |=  MOUSEEVENTF_LEFTDOWN;
				mousebtn1Down=true;
			}else if (mousebtn1Down){
				dwFlags |=  MOUSEEVENTF_LEFTUP;
				mousebtn1Down=false;
			}

			if ((button & 2) && (!mousebtn2Down)){
				dwFlags |=  MOUSEEVENTF_RIGHTDOWN;
				mousebtn2Down=true;
			}else if (mousebtn2Down){
				dwFlags |=  MOUSEEVENTF_RIGHTUP;
				mousebtn2Down=false;
			}

			if ((button & 4) && (!mousebtn3Down)){
				dwFlags |=  MOUSEEVENTF_MIDDLEDOWN;
				mousebtn3Down=true;
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

void ScreenCaptureNative::copy(){
	inputKeyboard("KEY","C",true,false,false,false);
}

void ScreenCaptureNative::paste(){
	inputKeyboard("KEY","V",true,false,false,false);
}

wchar_t* ScreenCaptureNative::getClipboardText(){
	Sleep(100);
	wchar_t* wText=NULL;
	if (OpenClipboard(NULL)){
		HANDLE hData = GetClipboardData(CF_UNICODETEXT); 
		if (hData != NULL){
			  size_t sz=GlobalSize(hData);
			  if (sz>0){
				  wchar_t* wGlobal = (wchar_t*)GlobalLock(hData);
				  wText = new wchar_t[sz];
				  wcscpy(wText,wGlobal);
			  }
			  GlobalUnlock(hData);
		}
		CloseClipboard();
	}
	return wText;
}

void ScreenCaptureNative::setClipboardText(wchar_t* wText){
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
