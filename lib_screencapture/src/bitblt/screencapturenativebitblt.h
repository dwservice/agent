/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/
#if defined OS_BITBLT

using namespace std;
#include <windows.h>
#include <vector>
#include <map>
#include <string>
#include <fstream>
#include <sys/stat.h>
#include "../windows/windowscpuusage.h"
#include "../windows/windowsinputs.h"
#include "../windows/windowsdesktop.h"
#include "../windows/windowsloadlib.h"
#include "../common/timecounter.h"
#include "../common/util.h"
#include "../common/logger.h"

extern "C" {
	int DWAScreenCaptureVersion();
	bool DWAScreenCaptureLoad();
	void DWAScreenCaptureFreeMemory(void* pnt);
	int DWAScreenCaptureIsChanged();
	int DWAScreenCaptureGetMonitorsInfo(MONITORS_INFO* moninfo);
	int DWAScreenCaptureInitMonitor(MONITORS_INFO_ITEM* moninfoitem, RGB_IMAGE* capimage, void** capses);
	int DWAScreenCaptureGetImage(void* capses);
	void DWAScreenCaptureTermMonitor(void* capses);
	void DWAScreenCaptureUnload();
	void DWAScreenCaptureInputKeyboard(const char* type, const char* key, bool ctrl, bool alt, bool shift, bool command);
	void DWAScreenCaptureInputMouse(MONITORS_INFO_ITEM* moninfoitem, int x, int y, int button, int wheel, bool ctrl, bool alt, bool shift, bool command);
	int DWAScreenCaptureCursor(CURSOR_IMAGE* curimage);
	void DWAScreenCaptureGetClipboardChanges(CLIPBOARD_DATA* clipboardData);
	void DWAScreenCaptureSetClipboard(CLIPBOARD_DATA* clipboardData);
	void DWAScreenCaptureCopy();
	void DWAScreenCapturePaste();
	int DWAScreenCaptureGetCpuUsage();
	//TMP PRIVACY MODE
	void DWAScreenCaptureSetPrivacyMode(bool b);
}

struct MonitorInternalInfo{
	HMONITOR hMonitor;
};

struct CursorInternalInfo{
	HCURSOR hCursor;
};

struct ScreenCaptureInfo{
	int status; //0:NOT INIT; 1:INIT; 2:READY
	int monitor;
	int x;
	int y;
	int w;
	int h;
	int bpp;
	int bpc;
	int bpr;
	RGB_IMAGE* rgbimage;
	unsigned char* data;
	HDC hsrcDC;
	HDC hdestDC;
	BITMAPINFO bitmapInfo;
	HANDLE hbmDIB;
	HANDLE hbmDIBOLD;
};

WindowsDesktop* winDesktop;
WindowsInputs* winInputs;
WindowsCPUUsage* cpuUsage;

#endif
