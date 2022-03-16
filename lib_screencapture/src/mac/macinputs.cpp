/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/
#if defined OS_QUARZDISPLAY

#include "macinputs.h"


MacInputs::MacInputs(){
	mousex=0;
	mousey=0;
	mousebtn1Down=false;
	mousebtn2Down=false;
	mousebtn3Down=false;
	commandDown=false;
	ctrlDown=false;
	altDown=false;
	shiftDown=false;
}

MacInputs::~MacInputs(){

}

void MacInputs::keyboard(const char* type,const char* key, bool ctrl, bool alt, bool shift, bool command){
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

void MacInputs::mouse(MONITORS_INFO_ITEM* moninfoitem, int x, int y, int factx, int facty, int button, int wheel, bool ctrl, bool alt, bool shift, bool command){
	//ctrlaltshift(ctrl,alt,shift,command);
	if ((x!=-1) && (y!=-1)){
		mousex=x;
		mousey=y;
	}

	/*MonitorInfo* mi = &monitorsInfo[0];
	if (mi==NULL){
		return;
	}*/

	CGPoint cmp = CGPointMake((int)((float)mousex/factx), (int)((float)mousey/facty));


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


void MacInputs::copy(){
	keyboard("KEY","C",false,false,false,true);
}

void MacInputs::paste(){
	keyboard("KEY","V",false,false,false,true);
}

//TODO NOT SECURE
/*wstring exec(const char* cmd){
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

int MacInputs::getClipboardText(wchar_t** wText){
	//TODO NOT SECURE
	/*wstring str=exec("pbpaste");
	return (wchar_t*)str.c_str();*/
	return 0;
}

void MacInputs::setClipboardText(wchar_t* wText){
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

CGKeyCode MacInputs::keyCodeForCharWithLayout(const char c, const UCKeyboardLayout *uchrHeader){
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

CGKeyCode MacInputs::keyCodeForChar(const char c){
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

CGKeyCode MacInputs::getCGKeyCode(const char* key){
	if (strcmp(key,"CONTROL")==0){
		return 0x3B;
	}else if (strcmp(key,"LCONTROL")==0){
		return 0x3B;
	}else if (strcmp(key,"RCONTROL")==0){
		return 0x3E;
	}else if (strcmp(key,"ALT")==0){
		return 0x3A;
	}else if (strcmp(key,"LALT")==0){
		return 0x3A;
	}else if (strcmp(key,"RALT")==0){
		return 0x3D;
	}else if (strcmp(key,"SHIFT")==0){
		return 0x38;
	}else if (strcmp(key,"LSHIFT")==0){
		return 0x38;
	}else if (strcmp(key,"RSHIFT")==0){
		return 0x3C;
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

void MacInputs::ctrlaltshift(bool ctrl, bool alt, bool shift, bool command){
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


int MacInputs::getModifiers(bool ctrl, bool alt, bool shift, bool command){
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


#endif
