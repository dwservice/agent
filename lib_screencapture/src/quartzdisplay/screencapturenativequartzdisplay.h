/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/
#if defined OS_QUARZDISPLAY

#include <sys/shm.h>
#include <stdio.h>
#include <string.h>
#include <sstream>
#include <stdlib.h>
#include <map>
#include <vector>
#include "../common/timecounter.h"
#include "../common/logger.h"
#include "../common/util.h"
#include "../mac/maccpuusage.h"
#include "../mac/macinputs.h"
#include "../mac/macobjc.h"
#include <ApplicationServices/ApplicationServices.h>
#include <Carbon/Carbon.h>
#include <IOKit/IOKitLib.h>
#include <IOKit/pwr_mgt/IOPMLib.h>
#include <mach/mach_init.h>
#include <mach/mach_error.h>

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

	int DWAScreenCaptureGetClipboardText(wchar_t** wText);
	void DWAScreenCaptureSetClipboardText(wchar_t* wText);

	//// TO DO 30/09/22 REMOVE ClipboardText
	void DWAScreenCaptureGetClipboardChanges(CLIPBOARD_DATA* clipboardData);
	void DWAScreenCaptureSetClipboard(CLIPBOARD_DATA* clipboardData);
	//////////////////////////////////////////

	void DWAScreenCaptureCopy();
	void DWAScreenCapturePaste();
	int DWAScreenCaptureGetCpuUsage();
}

#define MONITORS_MAX 32

struct MonitorInternalInfo{
	int displayID;
};

struct ScreenCaptureInfo{
	int status; //0:NOT INIT; 1:INIT; 2:READY
	int monitor;
	int x;
	int y;
	int w;
	int h;
	RGB_IMAGE* rgbimage;
	int displayID;
};

MacCPUUsage* cpuUsage;
MacInputs* macInputs;

int mainDisplayID;
int factx;
int facty;

IOPMAssertionID assertionIDIOPM1;
IOReturn successIOPM1;
IOPMAssertionID assertionIDIOPM2;
IOReturn successIOPM2;


#endif
