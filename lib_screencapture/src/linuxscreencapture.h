/* 
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
 */

#if defined OS_LINUX
 
using namespace std;

#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <X11/keysym.h>
#include <X11/XKBlib.h>
#include <X11/extensions/XTest.h>
#include <X11/extensions/XShm.h>
#include <sys/shm.h>
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>
#include <sstream>
#include <stdlib.h>
#include <sys/times.h>
#include <sys/vtimes.h>
#include <sys/ioctl.h>
#include <sys/types.h>
#include <unistd.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <algorithm>
#include <map>
#include <vector>
#include "dirent.h"
#include "linuxkeysym2ucs.h"
#include "linuxXrandr.h"
#include <errno.h>
#include "dwdebugger.h"
#include "timecounter.h"
#include "util.h"



typedef short (*FPalIdx)(unsigned char* rgb);

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
    void inputKeyboard(const char* type, const char* key, bool ctrl, bool alt, bool shift, bool command);
	void inputMouse(int monitor, int x, int y, int button, int wheel, bool ctrl, bool alt, bool shift, bool command);
	wchar_t* getClipboardText();
	void setClipboardText(wchar_t* wText);
	void copy();
	void paste();
	float getCpuUsage();
	
private:
	DWDebugger* dwdbg;

	#define MONITORS_INTERVAL 3000

	struct MonitorInfo{
		int x;
		int y;
		int w;
		int h;
	};

	struct ScreenShotInfo{
		XImage *image;
		int w;
		int h;
		int redlshift;
		int greenlshift;
		int redrshift;
		int greenrshift;
		int bluershift;
		long shotID;
		TimeCounter intervallCounter;
		XShmSegmentInfo m_shmseginfo;
	};

	vector<ScreenShotInfo> screenShotInfo;

	vector<MonitorInfo> monitorsInfo;
	TimeCounter monitorsCounter;
	bool firstmonitorscheck;

	long activeTTY;



	XRRScreenResources* (*callXRRGetScreenResourcesCurrent)(Display *dpy, Window window);
	XRRCrtcInfo* (*callXRRGetCrtcInfo)(Display *dpy, XRRScreenResources *resources, RRCrtc crtc);
	void (*callXRRFreeScreenResources) (XRRScreenResources *resources);
	void (*callXRRFreeCrtcInfo) (XRRCrtcInfo *crtcInfo);

	bool loadXrandr(string s);
	bool loadXrandrCheck(string s);
	//void loadXrandr();


	Display *xdpy;
	Window root;
	Visual *visual;
	int depth;
	Screen *screen;

	void *handleXrandr;

	long cursorID;
	int cursorX;
	int cursorY;
	int cursoroffsetX;
	int cursoroffsetY;
	int cursorW;
	int cursorH;

	bool mousebtn1Down;
	bool mousebtn2Down;
	bool mousebtn3Down;
	bool ctrlDown;
	bool altDown;
	bool shiftDown;
	bool firstGetCpu;
	clock_t lastCPU;
	clock_t lastSysCPU;
	clock_t lastUserCPU;
	int numProcessors;
	double percentCpu;
	TimeCounter cpuCounter;

	/*bool setXEnvirionment();
	bool setXEnvirionmentCmd(char* cmd);
	bool setXEnvirionmentProcess();*/

	string envxauthority;
	string envxwayland;
	string envxdisplay;
	long getActiveTTY();
	long getProcessTTY(char* pid);
	bool setXEnvirionment(long actty);
	bool existsFile(std::string filename);
	bool makeDirs(std::string path);
	//void setXDPY(Display *app,Screen *appscreen);


	void trimnl(char *s);
	KeySym getKeySym(const char* key);
	void mouseMove(int x,int y);
	void mouseButton(int button,bool press);
	void ctrlaltshift(bool ctrl, bool alt, bool shift);

	MonitorInfo* getMonitorInfo(int idx);

	void newScreenShotInfo(ScreenShotInfo* ii, int w, int h);
	ScreenShotInfo* getScreenShotInfo(int idx);
	void initScreenShotInfo(ScreenShotInfo* ii);
	void termScreenShotInfo(ScreenShotInfo* ii);

	int max_grp;
	typedef struct{
		int unicode;
		KeySym sym;
		KeyCode code;
		int modifier;
	} KEYMAP;
	map<int,KEYMAP*> hmUnicodeMap;
	vector<KEYMAP*> arNewUnicodeMap;

	void loadKeyMap();
	void unloadKeyMap();
	KeyCode addKeyUnicode(int uc);

};

#endif
