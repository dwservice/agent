/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/
#if defined OS_MAC

#include "macscreencapture.h"

ScreenCaptureNative::ScreenCaptureNative(DWDebugger* dbg) {
	dwdbg=dbg;
	mousebtn1Down=false;
	mousebtn2Down=false;
	mousebtn3Down=false;
	mousex=0;
	mousey=0;
	commandDown=false;
	ctrlDown=false;
	altDown=false;
	shiftDown=false;
	cursorX=0;
	cursorY=0;
	cursoroffsetX=0;
	cursoroffsetY=0;
	cursorW=0;
	cursorH=0;
	cursorID=0;
	monitorsCounter.reset();
	firstmonitorscheck=true;
	percentCpu=-1.0f;
	monitorsCounter.reset();
	previousTotalTicks=0;
	previousIdleTicks=0;
}

ScreenCaptureNative::~ScreenCaptureNative() {

}

float ScreenCaptureNative::calculateCPULoad(unsigned long long idleTicks, unsigned long long totalTicks){
	unsigned long long totalTicksSinceLastTime = totalTicks-previousTotalTicks;
	unsigned long long idleTicksSinceLastTime  = idleTicks-previousIdleTicks;
	float ret = 1.0f-((totalTicksSinceLastTime > 0) ? ((float)idleTicksSinceLastTime)/totalTicksSinceLastTime : 0);
	previousTotalTicks = totalTicks;
	previousIdleTicks  = idleTicks;
	return ret*100.0;
}

float ScreenCaptureNative::getCpuUsage(){
	if ((percentCpu>=0) && (cpuCounter.getCounter()<1000)){
		return percentCpu;
	}
	host_cpu_load_info_data_t cpuinfo;
	mach_msg_type_number_t count = HOST_CPU_LOAD_INFO_COUNT;
	if (host_statistics(mach_host_self(), HOST_CPU_LOAD_INFO, (host_info_t)&cpuinfo, &count) == KERN_SUCCESS){
		unsigned long long totalTicks = 0;
		for(int i=0; i<CPU_STATE_MAX; i++) totalTicks += cpuinfo.cpu_ticks[i];
		percentCpu=calculateCPULoad(cpuinfo.cpu_ticks[CPU_STATE_IDLE], totalTicks);
	}else{
		percentCpu=-1.0f;
	}
	cpuCounter.reset();
	return percentCpu;
}

bool ScreenCaptureNative::initialize() {

	//INIZIALIZZA MONITOR
	getMonitorCount();

	return true;
}

void ScreenCaptureNative::terminate() {
	for(vector<ScreenShotInfo>::size_type i = 0; i < screenShotInfo.size(); i++) {
		termScreenShotInfo(&screenShotInfo[i]);
	}
	screenShotInfo.clear();
	monitorsInfo.clear();
}


int ScreenCaptureNative::getMonitorCount(){
	/*int elapsed=monitorsCounter.getCounter();
	if ((firstmonitorscheck) || (elapsed>=MONITORS_INTERVAL)){
		firstmonitorscheck=false;
		CGDirectDisplayID display[MONITORS_MAX];
		CGDisplayCount numDisplays;
		CGDisplayErr err;
		err = CGGetActiveDisplayList(MONITORS_MAX, display, &numDisplays);
		if (err != CGDisplayNoErr)
			return 0;
		for (CGDisplayCount i = 0; i < numDisplays; ++i) {
			CGDirectDisplayID dspy = display[i];
			if (i>=monitorsInfo.size()){
				MonitorInfo ii;
				clearMonitorInfo(&ii);
				ii.id=dspy;
				monitorsInfo.push_back(ii);
			}else{
				if (monitorsInfo[i].id!=dspy){
					MonitorInfo ii;
					clearMonitorInfo(&ii);
					ii.id=dspy;
				}
			}
		}
		for(std::vector<MonitorInfo>::size_type i = numDisplays; i < monitorsInfo.size(); i++) {
			clearMonitorInfo(&monitorsInfo[i]);
			monitorsInfo.erase(monitorsInfo.begin() + i);
			i--;
		}

		monitorsCounter.reset();
	}
	return monitorsInfo.size();*/

	//TODO MULTIMONITOR
	/*if (firstmonitorscheck){
		CGDirectDisplayID display[MONITORS_MAX];
		CGDisplayCount numDisplays;
		CGDisplayErr err;
		err = CGGetActiveDisplayList(MONITORS_MAX, display, &numDisplays);
		if (err != CGDisplayNoErr)
			return 0;
		for (CGDisplayCount i = 0; i < numDisplays; ++i) {
			CGDirectDisplayID dspy = display[i];
			printf("CGDirectDisplayID %d\n",dspy);
		}
	}*/

	int elapsed=monitorsCounter.getCounter();
		if ((firstmonitorscheck) || (elapsed>=MONITORS_INTERVAL)){
		int did = CGMainDisplayID();

		CGDisplayModeRef dmd = CGDisplayCopyDisplayMode(did);
		int w = CGDisplayModeGetWidth(dmd);
		int h = CGDisplayModeGetHeight(dmd);
		//FIX RISOLUZIONI SIMILE A 1366x768
		if (((float)w/(float)8)!=(w/8)){
			w=(int)((int)((float)w/(float)8)+(float)1) * 8;
		}
		//if (((float)h/(float)8)!=(h/8)){
		//  h=(int)((int)((float)h/(float)8)+(float)1) * 8;
		//}
		if (firstmonitorscheck){
			MonitorInfo mi;
			mi.id=did;
			mi.factx=-1;
			mi.facty=-1;
			mi.dispw=w;
			mi.disph=h;
			mi.sleep=CGDisplayIsAsleep(did);
			monitorsInfo.push_back(mi);
			ScreenShotInfo ii;
			newScreenShotInfo(&ii, -1, -1);
			screenShotInfo.push_back(ii);
		}else{
			MonitorInfo* mi=&monitorsInfo[0];
			mi->id=did;
			if ((mi->dispw!=w) || (mi->disph!=h)){
				mi->factx=-1;
				mi->facty=-1;
			}
			mi->dispw=w;
			mi->disph=h;
			mi->sleep=CGDisplayIsAsleep(did);
		}
		firstmonitorscheck=false;
		monitorsCounter.reset();
	}
	return 1;
}

void ScreenCaptureNative::newScreenShotInfo(ScreenShotInfo* ii, int w, int h) {
	ii->bpp = -1;
	ii->bpc = -1;
	ii->bpr = -1;
	ii->w = w;
	ii->h = h;
	ii->data = NULL;
	ii->intervallCounter.reset();
	ii->shotID=0;
}



void ScreenCaptureNative::termScreenShotInfo(ScreenShotInfo* ii) {
	if (ii->shotID>=0){
		if (ii->data!=NULL){
			free(ii->data);
			ii->data=NULL;
		}
		ii->shotID=-1;
	}
}

ScreenCaptureNative::ScreenShotInfo* ScreenCaptureNative::getScreenShotInfo(int idx){
	if ((idx==1) && (screenShotInfo.size()==1)){ //Non trovato nessun monitor
		return &screenShotInfo[0];
	}else if (idx <= screenShotInfo.size() - 1){
		return &screenShotInfo[idx];
	}else{
		return NULL;
	}
}

long ScreenCaptureNative::captureScreen(int monitor, int distanceFrameMs, CAPTURE_IMAGE* capimage){
	capimage->width = 0;
	capimage->height = 0;


	//MonitorInfo* mi = getMonitorInfo(monitor);
	MonitorInfo* mi = &monitorsInfo[0];
	if (mi==NULL){
		return -2; //Identifica Monitor non trovato
	}

	int w = mi->w;
	int h = mi->h;

	ScreenShotInfo* ii = getScreenShotInfo(0);
	if (ii==NULL) {
		return -3; //Identifica ScreenShotInfo non trovato
	}

	/*if (ii->shotID==-1){
		initScreenShotInfo(ii);
	}*/

	if ((ii->shotID==0) || (ii->intervallCounter.getCounter()>=distanceFrameMs)) {
		ii->intervallCounter.reset();
		//CGDisplayCapture(displayid);
		CGImageRef image_ref = CGDisplayCreateImage(mi->id);
		//CGImageRef image_ref = CGWindowListCreateImage(CGRectNull, kCGWindowListOptionOnScreenOnly,0, kCGWindowImageBoundsIgnoreFraming);
		//CGRect captureRect = CGRectMake(0,0,w,h);
		//CGImageRef image_ref = CGWindowListCreateImage(captureRect, kCGWindowListOptionOnScreenOnly, kCGNullWindowID, kCGWindowImageBoundsIgnoreFraming);
		if (image_ref==NULL){
			return -4; //Identifica CGDisplayCreateImage failed
		}
		CGDataProviderRef provider = CGImageGetDataProvider(image_ref);
		CFDataRef dataref = CGDataProviderCopyData(provider);
		w = CGImageGetWidth(image_ref);
		h = CGImageGetHeight(image_ref);
		if ((mi->w!=w) || (mi->h!=h)){
			mi->factx=-1;
			mi->facty=-1;
		}
		if ((mi->factx==-1) || (mi->facty==-1)){
			mi->factx = (float)w/(float)mi->dispw;
			mi->facty = (float)h/(float)mi->disph;
		}
		mi->w=w;
		mi->h=h;
		int bpp = CGImageGetBitsPerPixel(image_ref);
		int bpc = (bpp + 7) / 8;
		int bpr = CGImageGetBytesPerRow(image_ref);
		if ((w!=ii->w) || (h!=ii->h) || (bpp!=ii->bpp) || (bpr!=ii->bpr)){
			termScreenShotInfo(ii);
			newScreenShotInfo(ii, w, h);
			ii->bpp=bpp;
			ii->bpc=bpc;
			ii->bpr=bpr;
			ii->data = (unsigned char*)malloc(h * bpr);
		}
		memcpy(ii->data, CFDataGetBytePtr(dataref), h * bpr);
		CFRelease(dataref);
		CGImageRelease(image_ref);
		ii->shotID+=1;
	}

	capimage->data = (unsigned char*)ii->data;
	capimage->bpp = ii->bpp;
	capimage->bpc = ii->bpc;
	capimage->width = w;
	capimage->height = h;
	return ii->shotID;
}

bool ScreenCaptureNative::captureCursor(int monitor, int* info, long& id, unsigned char** data){
	MonitorInfo* mi = &monitorsInfo[0];
	if ((mi==NULL) || (mi->factx==-1) || (mi->facty==-1)){
		return false;
	}
	CGEventRef event = CGEventCreate(NULL);
	if (event!=NULL){
		CGPoint cursor = CGEventGetLocation(event);
		cursorX=(int)cursor.x*mi->factx;
		cursorY=(int)cursor.y*mi->facty;
		CFRelease(event);
		if (id==-1){
			getCursorImage(CURSOR_TYPE_ARROW_18_18,&cursorW,&cursorH,&cursoroffsetX,&cursoroffsetY,data);
			cursorID++;
		}
		id=cursorID;
		info[0]=true;
		info[1]=cursorX;
		info[2]=cursorY;
		info[3]=cursorW;
		info[4]=cursorH;
		info[5]=cursoroffsetX;
		info[6]=cursoroffsetY;
		return true;
	}
	return false;
}

bool ScreenCaptureNative::getActiveWinPos(long* id, int* info){
	return false;
}

CGKeyCode ScreenCaptureNative::keyCodeForChar(const char c){
    CFDataRef currentLayoutData;
    TISInputSourceRef currentKeyboard = TISCopyCurrentKeyboardInputSource();

    if (currentKeyboard == NULL) {
        return UINT16_MAX;
    }

    currentLayoutData = (CFDataRef)TISGetInputSourceProperty(currentKeyboard, kTISPropertyUnicodeKeyLayoutData);
    CFRelease(currentKeyboard);
    if (currentLayoutData == NULL) {
        return UINT16_MAX;
    }

    return keyCodeForCharWithLayout(c, (const UCKeyboardLayout *)CFDataGetBytePtr(currentLayoutData));
}

CGKeyCode ScreenCaptureNative::keyCodeForCharWithLayout(const char c, const UCKeyboardLayout *uchrHeader){
    uint8_t *uchrData = (uint8_t *)uchrHeader;
    const UCKeyboardTypeHeader *uchrKeyboardList = uchrHeader->keyboardTypeList;
    ItemCount i, j;
    for (i = 0; i < uchrHeader->keyboardTypeCount; ++i) {
        UCKeyToCharTableIndex *uchrKeyIX = (UCKeyToCharTableIndex *)
        (uchrData + (uchrKeyboardList[i].keyToCharTableIndexOffset));

        UCKeyStateRecordsIndex *stateRecordsIndex;
        if (uchrKeyboardList[i].keyStateRecordsIndexOffset != 0) {
            stateRecordsIndex = (UCKeyStateRecordsIndex *)
                (uchrData + (uchrKeyboardList[i].keyStateRecordsIndexOffset));

            if ((stateRecordsIndex->keyStateRecordsIndexFormat) != kUCKeyStateRecordsIndexFormat) {
                stateRecordsIndex = NULL;
            }
        } else {
            stateRecordsIndex = NULL;
        }
        if ((uchrKeyIX->keyToCharTableIndexFormat) != kUCKeyToCharTableIndexFormat) {
            continue;
        }
        for (j = 0; j < uchrKeyIX->keyToCharTableCount; ++j) {
            UCKeyOutput *keyToCharData =
                (UCKeyOutput *)(uchrData + (uchrKeyIX->keyToCharTableOffsets[j]));

            UInt16 k;
            for (k = 0; k < uchrKeyIX->keyToCharTableSize; ++k) {
                if ((keyToCharData[k] & kUCKeyOutputTestForIndexMask) ==
                    kUCKeyOutputStateIndexMask) {
                    long keyIndex = (keyToCharData[k] & kUCKeyOutputGetIndexMask);
                    if (stateRecordsIndex != NULL &&
                        keyIndex <= (stateRecordsIndex->keyStateRecordCount)) {
                        UCKeyStateRecord *stateRecord = (UCKeyStateRecord *)(uchrData + (stateRecordsIndex->keyStateRecordOffsets[keyIndex]));
                        if ((stateRecord->stateZeroCharData) == c) {
                            return (CGKeyCode)k;
                        }
                    } else if (keyToCharData[k] == c) {
                        return (CGKeyCode)k;
                    }
                } else if (((keyToCharData[k] & kUCKeyOutputTestForIndexMask)
                            != kUCKeyOutputSequenceIndexMask) &&
                           keyToCharData[k] != 0xFFFE &&
                           keyToCharData[k] != 0xFFFF &&
                           keyToCharData[k] == c) {
                    return (CGKeyCode)k;
                }
            }
        }
    }
    return UINT16_MAX;
}

CGKeyCode ScreenCaptureNative::getCGKeyCode(const char* key){
	if (strcmp(key,"CONTROL")==0){
		return 0x3B;
	}else if (strcmp(key,"ALT")==0){
		return 0x3A;
	}else if (strcmp(key,"SHIFT")==0){
		return 0x38;
	}else if (strcmp(key,"TAB")==0){
		return 0x30;
	}else if (strcmp(key,"ENTER")==0){
		return 0x24;
	}else if (strcmp(key,"BACKSPACE")==0){
		return 0x33;
	}else if (strcmp(key,"CLEAR")==0){

	}else if (strcmp(key,"PAUSE")==0){

	}else if (strcmp(key,"ESCAPE")==0){
		return 0x35;
	}else if (strcmp(key,"SPACE")==0){
		return 0x31;
	}else if (strcmp(key,"DELETE")==0){
		return 0x75;
	}else if (strcmp(key,"INSERT")==0){

	}else if (strcmp(key,"HELP")==0){
		return 0x72;
	}else if (strcmp(key,"LEFT_WINDOW")==0){
		return 0x37;
	}else if (strcmp(key,"RIGHT_WINDOW")==0){
		return 0x37;
	}else if (strcmp(key,"SELECT")==0){

	}else if (strcmp(key,"PAGE_UP")==0){
		return 0x74;
	}else if (strcmp(key,"PAGE_DOWN")==0){
		return 0x79;
	}else if (strcmp(key,"END")==0){
		return 0x77;
	}else if (strcmp(key,"HOME")==0){
		return 0x73;
	}else if (strcmp(key,"LEFT_ARROW")==0){
		return 0x7B;
	}else if (strcmp(key,"UP_ARROW")==0){
		return 0x7E;
	}else if (strcmp(key,"DOWN_ARROW")==0){
		return 0x7D;
	}else if (strcmp(key,"RIGHT_ARROW")==0){
		return 0x7C;
	}else if (strcmp(key,"F1")==0){
		return 0x7A;
	}else if (strcmp(key,"F2")==0){
		return 0x78;
	}else if (strcmp(key,"F3")==0){
		return 0x63;
	}else if (strcmp(key,"F4")==0){
		return 0x76;
	}else if (strcmp(key,"F5")==0){
		return 0x60;
	}else if (strcmp(key,"F6")==0){
		return 0x61;
	}else if (strcmp(key,"F7")==0){
		return 0x62;
	}else if (strcmp(key,"F8")==0){
		return 0x64;
	}else if (strcmp(key,"F9")==0){
		return 0x65;
	}else if (strcmp(key,"F10")==0){
		return 0x6D;
	}else if (strcmp(key,"F11")==0){
		return 0x67;
	}else if (strcmp(key,"F12")==0){
		return 0x6F;
	}else{
		return keyCodeForChar(key[0]);
	}
	return UINT16_MAX;
}

void ScreenCaptureNative::ctrlaltshift(bool ctrl, bool alt, bool shift, bool command){
	if ((ctrl) && (!commandDown)){
		commandDown=true;
		CGEventRef kdown = CGEventCreateKeyboardEvent(NULL, (CGKeyCode)0x37, true); //(CGKeyCode)0x37 = COMMAND
		CGEventPost(kCGHIDEventTap, kdown);
		CFRelease(kdown);
	}else if ((!ctrl) && (commandDown)){
		commandDown=false;
		CGEventRef kup = CGEventCreateKeyboardEvent(NULL, (CGKeyCode)0x37, false); //(CGKeyCode)0x37 = COMMAND
		CGEventPost(kCGHIDEventTap, kup);
		CFRelease(kup);
	}

	if ((ctrl) && (!ctrlDown)){
		ctrlDown=true;
		CGEventRef kdown = CGEventCreateKeyboardEvent(NULL, (CGKeyCode)0x3B, true); //(CGKeyCode)0x3B = CTRL
		CGEventPost(kCGHIDEventTap, kdown);
		CFRelease(kdown);
	}else if ((!ctrl) && (ctrlDown)){
		ctrlDown=false;
		CGEventRef kup = CGEventCreateKeyboardEvent(NULL, (CGKeyCode)0x3B, false); //(CGKeyCode)0x3B = CTRL
		CGEventPost(kCGHIDEventTap, kup);
		CFRelease(kup);
	}

	if ((alt) && (!altDown)){
		altDown=true;
		CGEventRef kdown = CGEventCreateKeyboardEvent(NULL, (CGKeyCode)0x3A, true);
		CGEventPost(kCGHIDEventTap, kdown);
		CFRelease(kdown);
	}else if ((!alt) && (altDown)){
		altDown=false;
		CGEventRef kup = CGEventCreateKeyboardEvent(NULL, (CGKeyCode)0x3A, false);
		CGEventPost(kCGHIDEventTap, kup);
		CFRelease(kup);
	}

	if ((shift) && (!shiftDown)){
		shiftDown=true;
		CGEventRef kdown = CGEventCreateKeyboardEvent(NULL, (CGKeyCode)0x38, true);
		CGEventPost(kCGHIDEventTap, kdown);
		CFRelease(kdown);
	}else if ((!shift) && (shiftDown)){
		shiftDown=false;
		CGEventRef kup = CGEventCreateKeyboardEvent(NULL, (CGKeyCode)0x38, false);
		CGEventPost(kCGHIDEventTap, kup);
		CFRelease(kup);
	}
}

void ScreenCaptureNative::wakeupMonitor(){
	MonitorInfo* ii = &monitorsInfo[0];
	//GESTIONE SLEEP
	if (ii->sleep){
		io_registry_entry_t reg = IORegistryEntryFromPath(kIOMasterPortDefault, "IOService:/IOResources/IODisplayWrangler");
		if (reg)
			IORegistryEntrySetCFProperty(reg, CFSTR("IORequestIdle"), kCFBooleanFalse);
			IOObjectRelease(reg);
		ii->sleep=false;
	}
}

int ScreenCaptureNative::getModifiers(bool ctrl, bool alt, bool shift, bool command){
	int modifiers=0;
	if (command){
		 modifiers = modifiers | kCGEventFlagMaskCommand;
	}
	if (ctrl){
		 modifiers = modifiers | kCGEventFlagMaskControl;
	}
	if (alt){
		 modifiers = modifiers | kCGEventFlagMaskAlternate;
	}
	if (shift){
		 modifiers = modifiers | kCGEventFlagMaskShift;
	}
	return modifiers;
}

void ScreenCaptureNative::inputKeyboard(const char* type, const char* key, bool ctrl, bool alt, bool shift, bool command){
	wakeupMonitor();

	if (strcmp(type,"CHAR")==0){
		int uc = atoi(key);
		UniChar c = uc;
		CGEventRef kdown = CGEventCreateKeyboardEvent(NULL, 0, true);
		CGEventKeyboardSetUnicodeString(kdown,1,&c);
		CGEventPost(kCGHIDEventTap, kdown);
		CFRelease(kdown);
		CGEventRef kup = CGEventCreateKeyboardEvent(NULL, 0, false);
		CGEventKeyboardSetUnicodeString(kup, 1, &c);
		CGEventPost(kCGHIDEventTap, kup);
		CFRelease(kup);
	}else if (strcmp(type,"KEY")==0){
		CGKeyCode c = getCGKeyCode(key);
		if (c!=UINT16_MAX){
			//ctrlaltshift(ctrl,alt,shift,command);
			CGEventRef kdown = CGEventCreateKeyboardEvent(NULL, c, true);
			CGEventSetFlags(kdown, (CGEventFlags)getModifiers(ctrl,alt,shift,command));
			CGEventPost(kCGHIDEventTap, kdown);
			CFRelease(kdown);
			CGEventRef kup = CGEventCreateKeyboardEvent(NULL, c, false);
			CGEventSetFlags(kup, (CGEventFlags)getModifiers(ctrl,alt,shift,command));
			CGEventPost(kCGHIDEventTap, kup);
			CFRelease(kup);
			//ctrlaltshift(false,false,false,false);
		}
	}else if (strcmp(type,"CTRLALTCANC")==0){
	}
}

void ScreenCaptureNative::inputMouse(int monitor, int x, int y, int button, int wheel, bool ctrl, bool alt, bool shift, bool command){
	wakeupMonitor();

	//ctrlaltshift(ctrl,alt,shift,command);
	if ((x!=-1) && (y!=-1)){
		mousex=x;
		mousey=y;
	}


	MonitorInfo* mi = &monitorsInfo[0];
	if (mi==NULL){
		return;
	}
	CGPoint cmp = CGPointMake((int)((float)mousex/mi->factx), (int)((float)mousey/mi->facty));

	if (button==64) { //CLICK

		CGEventRef theEvent = CGEventCreateMouseEvent(NULL, kCGEventLeftMouseDown, cmp, kCGMouseButtonLeft);
		CGEventSetFlags(theEvent, (CGEventFlags)getModifiers(ctrl,alt,shift,command));
		CGEventPost(kCGHIDEventTap, theEvent);
		CGEventSetType(theEvent, kCGEventLeftMouseUp);
		CGEventPost(kCGHIDEventTap, theEvent);
		CFRelease(theEvent);
	}else if (button==128) { //DBLCLICK
		CGEventRef theEvent = CGEventCreateMouseEvent(NULL, kCGEventLeftMouseDown, cmp, kCGMouseButtonLeft);
		CGEventPost(kCGHIDEventTap, theEvent);
		CGEventSetType(theEvent, kCGEventLeftMouseUp);
		CGEventSetFlags(theEvent, (CGEventFlags)getModifiers(ctrl,alt,shift,command));
		CGEventPost(kCGHIDEventTap, theEvent);

		CGEventSetIntegerValueField(theEvent, kCGMouseEventClickState, 2);

		CGEventSetType(theEvent, kCGEventLeftMouseDown);
		CGEventSetFlags(theEvent, (CGEventFlags)getModifiers(ctrl,alt,shift,command));
		CGEventPost(kCGHIDEventTap, theEvent);
		CGEventSetType(theEvent, kCGEventLeftMouseUp);
		CGEventPost(kCGHIDEventTap, theEvent);

		CFRelease(theEvent);
	}else{
		bool moveonly=true;
		if (button!=-1) {
			int appbtn=-1;
			if ((button & 1) && (!mousebtn1Down)){
				appbtn=kCGEventLeftMouseDown;
				mousebtn1Down=true;
			}else if (mousebtn1Down){
				appbtn=kCGEventLeftMouseUp;
				mousebtn1Down=false;
			}
			if (appbtn!=-1){
				moveonly=false;
				CGEventRef theEvent = CGEventCreateMouseEvent(NULL,appbtn,cmp,kCGMouseButtonLeft);
				CGEventSetFlags(theEvent, (CGEventFlags)getModifiers(ctrl,alt,shift,command));
				CGEventPost(kCGHIDEventTap, theEvent);
				CFRelease(theEvent);
			}
			appbtn=-1;
			if ((button & 2) && (!mousebtn2Down)){
				appbtn=kCGEventRightMouseDown;
				mousebtn2Down=true;
			}else if (mousebtn2Down){
				appbtn=kCGEventRightMouseUp;
				mousebtn2Down=false;
			}
			if (appbtn!=-1){
				moveonly=false;
				CGEventRef theEvent = CGEventCreateMouseEvent(NULL,appbtn,cmp,kCGMouseButtonRight);
				CGEventSetFlags(theEvent, (CGEventFlags)getModifiers(ctrl,alt,shift,command));
				CGEventPost(kCGHIDEventTap, theEvent);
				CFRelease(theEvent);
			}
			/*appbtn=-1;
			if ((button & 4) && (!mousebtn3Down)){
				appbtn=Button2;
				mousebtn3Down=true;
			}else if (mousebtn3Down){
				appbtn=Button2;
				mousebtn3Down=false;
			}
			if (appbtn!=-1){
				mouseButton(appbtn, mousebtn3Down);
			}*/
		}
		if (moveonly){
			CGEventRef theEvent = NULL;
			if (mousebtn1Down){
				theEvent = CGEventCreateMouseEvent(NULL,kCGEventLeftMouseDragged,cmp,kCGMouseButtonLeft);
			}else{
				theEvent = CGEventCreateMouseEvent(NULL,kCGEventMouseMoved,cmp,kCGMouseButtonLeft);
			}
			CGEventSetFlags(theEvent, (CGEventFlags)getModifiers(ctrl,alt,shift,command));
			CGEventPost(kCGHIDEventTap, theEvent);
			CFRelease(theEvent);
		}
	}
	if (wheel!=0) {
		CGEventRef scroll = CGEventCreateScrollWheelEvent(NULL, kCGScrollEventUnitLine, 1, wheel);
		CGEventSetFlags(scroll, (CGEventFlags)getModifiers(ctrl,alt,shift,command));
		CGEventPost(kCGHIDEventTap, scroll);
		CFRelease(scroll);
	}


}

void ScreenCaptureNative::copy(){
	inputKeyboard("KEY","C",false,false,false,true);
}

void ScreenCaptureNative::paste(){
	inputKeyboard("KEY","V",false,false,false,true);
}

//TODO NOT SECURE
/*wstring ScreenCaptureNative::exec(const char* cmd){
	FILE* pipe = popen(cmd, "r");
	if (!pipe) return L"";
	wchar_t buffer[128];
	std::wstring result = L"";
	while (!feof(pipe)){
		if (fgetws(buffer, 128, pipe) != NULL){
			result += buffer;
		}
	}
	pclose(pipe);
	return result;
}*/

wchar_t* ScreenCaptureNative::getClipboardText(){
	//TODO NOT SECURE
	/*wstring str=exec("pbpaste");
	return (wchar_t*)str.c_str();*/
	return NULL;
}

void ScreenCaptureNative::setClipboardText(wchar_t* wText){
	//TODO NOT SECURE
	/*
	wstring wapp = L"";
	wapp.append(L"echo \"");
	if (wText!=NULL){
		wapp.append(wText);
	}
	wapp.append(L"\" | pbcopy");
	char app[4096];
	wcstombs(app, wText, sizeof(app));
	exec(app);
	*/
}


#endif
