/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <map>
#include <vector>
#include <iostream>
#include "timecounter.h"
#include "util.h"
#include <string>

#include "zutil.h"
#include "turbojpeg.h"
#include "linuxscreencapture.h"
#include "macscreencapture.h"
#include "windowsscreencapture.h"


typedef void (*CallbackDifference)(int, unsigned char*);

class ScreenCapture{

public:
	ScreenCapture(DWDebugger* dbg);
    ~ScreenCapture( void );

	void  initialize(int id);
	void terminate(int id);
	void monitor(int id, int index);
	void difference(int id, int typeFrame, int quality, CallbackDifference cbdiff);

	void inputKeyboard(int id, const char* type, const char* key, bool ctrl, bool alt, bool shift, bool command);
	void inputMouse(int id, int x, int y, int button, int wheel, bool ctrl, bool alt, bool shift, bool command);
	wchar_t* copyText(int id);
	void pasteText(int id,wchar_t* str);
	//float getCpuUsage();
	ScreenCaptureNative getNative();

	void areaChanged(CAPTURE_CHANGE_AREA* area);
	void areaMoved(CAPTURE_MOVE_AREA* area);


private:
	#define TYPE_FRAME_PALETTE_V1 0
	#define TYPE_FRAME_TJPEG_V1 100

	#define TJPEG_SPLIT_SIZE 1*1024*1024
	#define BUFFER_DIFF_SIZE 56*1024
	#define MOUSE_INTERVAL 50


	int diffBufferSize;
	unsigned char* diffBuffer;
	tjhandle tjInstance;

	typedef struct{
		int x1;
		int y1;
		int x2;
		int y2;
	} DIFFRECT;

	typedef struct{
		//short* data;
		unsigned char* data;
		long shotID;
		short shotw;
		short shoth;
		bool screenLocked;
		PALETTE palette;
		int jpegQuality;
		
		long cursorID;
		bool cursorVisible;
		int cursorx;
		int cursory;
		int cursorw;
		int cursorh;
		int cursoroffsetx;
		int cursoroffsety;
		TimeCounter cursorCounter;

		/*long activeWinID;
		int activeWinX;
		int activeWinY;
		int activeWinW;
		int activeWinH;*/
	   
		int monitorCount;
		int monitor;
		int quality;
		int typeFrame;

	} SESSION;


	DWDebugger* dwdbg;
	int lastSessionID;
	std::map<int,SESSION> hmSession;
	ScreenCaptureNative captureNative;
	
	DistanceFrameMsCalculator distanceFrameMsCalculator;

	void initSession(int id);
	void loadQuality(SESSION* ses);

	void resizeDiffBufferIfNeed(int needsz);
	//int prepareCopyArea(unsigned char* &bf,int p,int* cursz,SESSION &ses);
	void differenceFrameTJPEG(SESSION &ses, CAPTURE_IMAGE &capimage, CallbackDifference cbdiff);
	void differenceFrameTPALETTE(SESSION &ses, CAPTURE_IMAGE &capimage, CallbackDifference cbdiff);
	void differenceCursor(SESSION &ses, CAPTURE_IMAGE &capimage, CallbackDifference cbdiff);
	void inputsEvent();
	//char convertCharBase64(char c);
	//void debugPrint(char* str);
	int intToArray(unsigned char* buffer,int p,int i);
	int byteArrayToInt(unsigned char* buffer,int p);
	int shortToArray(unsigned char* buffer,int p,short s);
	short byteArrayToShort(unsigned char* buffer,int p);
	

};

