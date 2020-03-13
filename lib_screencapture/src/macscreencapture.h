/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/
#if defined OS_MAC

using namespace std;

#include <sys/shm.h>
#include <stdio.h>
#include <string.h>
#include <sstream>
#include <stdlib.h>
#include <map>
#include <vector>
#include "timecounter.h"
#include "dwdebugger.h"
#include "util.h"
#include <ApplicationServices/ApplicationServices.h>
#include <Carbon/Carbon.h>
#include <IOKit/IOKitLib.h>
#include <mach/mach_init.h>
#include <mach/mach_error.h>
#include <mach/mach_host.h>
#include <mach/vm_map.h>

class ScreenCaptureNative{

public:
	ScreenCaptureNative(DWDebugger* dbg);
    ~ScreenCaptureNative( void );

    int getMonitorCount();
    bool initialize();
	void terminate();
    void getResolution(int* size);
    long captureScreen(int monitor, int distanceFrameMs, CAPTURE_IMAGE* capimage);
    bool captureCursor(int monitor, int* info, long& id, unsigned char** data);
    bool getActiveWinPos(long* id, int* info);
    void getCursorPixel(int x, int y, unsigned char* rgba);
    void inputKeyboard(const char* type, const char* key, bool ctrl, bool alt, bool shift, bool command);
	void inputMouse(int monitor, int x, int y, int button, int wheel, bool ctrl, bool alt, bool shift, bool command);
	wchar_t* getClipboardText();
	void setClipboardText(wchar_t* wText);
	void copy();
	void paste();
	float getCpuUsage();

private:
	#define MONITORS_INTERVAL 3000
	#define MONITORS_MAX 32

	DWDebugger* dwdbg;
	struct MonitorInfo{
		CGDirectDisplayID id;
		int x;
		int y;
		int w;
		int h;
		int dispw;
		int disph;
		float factx;
		float facty;
		bool sleep;
	};

	struct ScreenShotInfo{
		int w;
		int h;
		int bpp;
		int bpc;
		int bpr;
		unsigned char* data;
		long shotID;
		TimeCounter intervallCounter; //Calcola il tempo di cattura da un shot ad un altra
	};

	vector<MonitorInfo> monitorsInfo;
	TimeCounter monitorsCounter;
	bool firstmonitorscheck;

	vector<ScreenShotInfo> screenShotInfo;

	long cursorID;
	int cursorX;
	int cursorY;
	int cursoroffsetX;
	int cursoroffsetY;
	int cursorW;
	int cursorH;

	int mousex;
	int mousey;
	bool mousebtn1Down;
	bool mousebtn2Down;
	bool mousebtn3Down;
	bool commandDown;
	bool ctrlDown;
	bool altDown;
	bool shiftDown;
	unsigned long long previousTotalTicks;
	unsigned long long previousIdleTicks;
	double percentCpu;
	TimeCounter cpuCounter;
	float calculateCPULoad(unsigned long long idleTicks, unsigned long long totalTicks);
	void wakeupMonitor();
	CGKeyCode getCGKeyCode(const char* key);
	void ctrlaltshift(bool ctrl, bool alt, bool shift, bool command);
	int getModifiers(bool ctrl, bool alt, bool shift, bool command);
	void newScreenShotInfo(ScreenShotInfo* ii, int w, int h);
	void termScreenShotInfo(ScreenShotInfo* ii);
	ScreenShotInfo* getScreenShotInfo(int idx);
	CGKeyCode keyCodeForChar(const char c);
	CGKeyCode keyCodeForCharWithLayout(const char c, const UCKeyboardLayout *uchrHeader);
	//TODO NOT SECURE
	//wstring exec(const char* cmd);
};

#endif
