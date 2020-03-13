/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/
#if defined OS_WINDOWS

using namespace std;
#include <windows.h>
#include <vector>
#include <map>
#include <string>
#include <fstream>
#include <sys/stat.h>
#include "windowsloadlib.h"
#include "dwdebugger.h"
#include "timecounter.h"
#include "util.h"

class ScreenCaptureNative{
	

public:
	ScreenCaptureNative(DWDebugger* dbg);
    ~ScreenCaptureNative( void );
	
	BOOL CALLBACK monitorEnumProc(HMONITOR hMonitor,HDC hdcMonitor,LPRECT lprcMonitor,LPARAM dwData);

	static LRESULT CALLBACK ScreenCaptureNativeWindowProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam);
	LRESULT CALLBACK windowProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam);
	void createWindow();

	int getMonitorCount();
    bool initialize();
	void terminate();
	long captureScreen(int monitor, int distanceFrameMs, CAPTURE_IMAGE* capimage);
	bool captureCursor(int monitor, int* info, long& id, unsigned char** rgbdata);
	//bool getActiveWinPos(long* id, int* info);
	void inputKeyboard(const char* type,const char* key, bool ctrl, bool alt, bool shift, bool command);
	void inputMouse(int monitor, int x, int y, int button, int wheel, bool ctrl, bool alt, bool shift, bool command);
	wchar_t* getClipboardText();
	void setClipboardText(wchar_t* wText);
	void copy();
	void paste();
	float getCpuUsage();
	void setAsElevated(bool b);
	
private:
	#define MONITORS_INTERVAL 3000

	DWDebugger* debugger;
	WindowsLoadLib loadLib;

	struct MonitorInfo{
		HMONITOR hMonitor;
		HDC hdcMonitor;
		int x;
		int y;
		int w;
		int h;
	};

	struct ScreenShotInfo{
		HDC hsrcDC;
		HDC hdestDC;
		BITMAPINFO bitmapInfo;
		HANDLE hbmDIB;
		HANDLE hbmDIBOLD;
		int w;
		int h;
		unsigned char* data;
		long shotID;
		TimeCounter intervallCounter; //Calcola il tempo di cattura da un shot ad un altra 
	};

	vector<MonitorInfo> monitorsInfo;
	TimeCounter monitorsCounter;
	bool firstmonitorscheck;

	//CURSORE
	HCURSOR cursorHandle;
	long cursorID;
	int cursorX;
	int cursorY;
	int cursoroffsetX;
	int cursoroffsetY;
	int cursorW;
	int cursorH;
	
	//SPOSTAMENTO FINESTRA ATTIVA
	HWND activeWinHandle;
	long activeWinID;
	int activeWinX;
	int activeWinY;
	int activeWinW;
	int activeWinH;

	//INPUT
	bool mousebtn1Down;
	bool mousebtn2Down;
	bool mousebtn3Down;
	bool ctrlDown;
	bool altDown;
	bool shiftDown;
	/*int resMirror;
	DEVMODE deviceMode;
	DISPLAY_DEVICE deviceDisplay;*/
	
	
	vector<ScreenShotInfo> screenShotInfo;

	wchar_t prevDesktopName[1024];

	FILETIME prevSysKernel;
	FILETIME prevSysUser; 
	FILETIME prevProcKernel; 
	FILETIME prevProcUser;
	float lastCpu=-1;
	TimeCounter cpuCounter;

	//int detectMirrorDriver(vector<DISPLAY_DEVICE>& devices,map<int,DEVMODE>& settings);
	OSVERSIONINFOEX m_osVerInfo;
	bool runAsElevated; 
	bool isWin8OrLater();
	bool isExtendedKey(int key);
	int getKeyCode(const char* key);
	void sendInputs(INPUT (&inputs)[20],int max);
	void addCtrlAltShift(INPUT (&inputs)[20],int &p,bool ctrl, bool alt, bool shift);
	void addInputMouse(INPUT (&inputs)[20],int &p,int x, int y,DWORD dwFlags,int mouseData,int tm);
	void newScreenShotInfo(ScreenShotInfo* ii, int w, int h);
	void initScreenShotInfo(ScreenShotInfo* ii);
	void termScreenShotInfo(ScreenShotInfo* ii);
	void resetScreenshotData(ScreenShotInfo* ii);
	bool selectDesktop(char* name);
    HDESK getDesktop(char* name);
    HDESK getInputDesktop();
	int setCurrentThreadDesktop();
	MonitorInfo* getMonitorInfo(int idx);
	ScreenShotInfo* getScreenShotInfo(int idx);
	ULONGLONG subtractTime(const FILETIME &a, const FILETIME &b);	
	HWND hwndwts;
};

#endif
