/* 
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
 */

#if defined OS_XORG

#ifndef SCREENCAPTURENATIVE_H_
#define SCREENCAPTURENATIVE_H_

using namespace std;
#include <X11/Xlib.h>
#include <X11/extensions/XShm.h>
#include <X11/extensions/Xdamage.h>
#include <sys/shm.h>
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <sys/ioctl.h>
#include <algorithm>
#include "dirent.h"
#include "../linux/Xrandr.h"
#include "../linux/linuxcpuusage.h"
#include "../linux/linuxinputsxorg.h"
#include "../common/dwdebugger.h"
#include "../common/util.h"

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
	void DWAScreenCaptureCopy();
	void DWAScreenCapturePaste();
	int DWAScreenCaptureGetCpuUsage();
}
  

struct ScreenCaptureInfo{
	int status; //0:NOT INIT; 1:INIT; 2:READY
	int monitor;
	int x;
	int y;
	int w;
	int h;
	RGB_IMAGE* rgbimage;
	XImage *image;
	XShmSegmentInfo m_shmseginfo;
	int redlshift;
	int greenlshift;
	int redrshift;
	int greenrshift;
	int bluershift;
};

XRRScreenResources* (*callXRRGetScreenResourcesCurrent)(Display *dpy, Window window);
XRRCrtcInfo* (*callXRRGetCrtcInfo)(Display *dpy, XRRScreenResources *resources, RRCrtc crtc);
void (*callXRRFreeScreenResources) (XRRScreenResources *resources);
void (*callXRRFreeCrtcInfo) (XRRCrtcInfo *crtcInfo);


Display *xdpy;
Window root;
Visual *visual;
int depth;
Screen *screen;
void *handleXrandr;
bool damageok;
Damage damage;
int damageevent;
bool damageareachanged;
int damageareax;
int damageareay;
int damageareaw;
int damageareah;
bool xfixesok;
bool xfixeschanged;
int xfixesevent;

LinuxCPUUsage* cpuUsage;
LinuxInputs* linuxInputs;


#endif /* SCREENCAPTURENATIVE_H_ */

#endif
