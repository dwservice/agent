/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/
#if defined OS_QUARZDISPLAY

#include "screencapturenativequartzdisplay.h"

int DWAScreenCaptureVersion(){
	return 1;
}

void DWAScreenCaptureFreeMemory(void* pnt){
	free(pnt);
}

int DWAScreenCaptureIsChanged(){
	return 0;
}

int DWAScreenCaptureInitMonitor(MONITORS_INFO_ITEM* moninfoitem, RGB_IMAGE* capimage, void** capses){
	ScreenCaptureInfo* sci = new ScreenCaptureInfo();
	sci->monitor=moninfoitem->index;
	sci->x=moninfoitem->x;
	sci->y=moninfoitem->y;
	sci->w=moninfoitem->width;
	sci->h=moninfoitem->height;
	capimage->width=moninfoitem->width;
	capimage->height=moninfoitem->height;
	capimage->sizedata=capimage->width*capimage->height*3;
	capimage->sizechangearea=0;
	capimage->sizemovearea=0;
	capimage->data=(unsigned char*)malloc(capimage->sizedata * sizeof(unsigned char));
	sci->rgbimage=capimage;

	sci->status=1;
	*capses=sci;
	return 0;
}

void DWAScreenCaptureTermMonitor(void* capses){
	ScreenCaptureInfo* sci = (ScreenCaptureInfo*)capses;
	if (sci->status==0){
		return;
	}
	/*if (sci->image != NULL){
		XShmDetach(xdpy,&sci->m_shmseginfo);
		XDestroyImage(sci->image);
		shmdt(sci->m_shmseginfo.shmaddr);
		shmctl(sci->m_shmseginfo.shmid, IPC_RMID, 0);
		sci->image = NULL;
	}*/
	RGB_IMAGE* rgbimage = sci->rgbimage;
	free(rgbimage->data);
	rgbimage->data=NULL;
	rgbimage->width=0;
	rgbimage->height=0;
	sci->status=0;
	delete sci;
}

int DWAScreenCaptureGetImage(void* capses){
	ScreenCaptureInfo* sci = (ScreenCaptureInfo*)capses;
	if (sci->status==0){
		return -1; //NOT INIT
	}
	RGB_IMAGE* rgbimage=sci->rgbimage;
	rgbimage->sizechangearea=0;
	rgbimage->sizemovearea=0;

	CGImageRef image_ref = CGDisplayCreateImage(mainDisplayID);
	if (image_ref==NULL){
		return -4; //Identifica CGDisplayCreateImage failed
	}
	CGDataProviderRef provider = CGImageGetDataProvider(image_ref);
	CFDataRef dataref = CGDataProviderCopyData(provider);
	int bpp = CGImageGetBitsPerPixel(image_ref);
	int bpr = CGImageGetBytesPerRow(image_ref);
	unsigned char* data = (unsigned char*)CFDataGetBytePtr(dataref);
	//CONVERT IN RGB
	int offsetSrc = 0;
	int offsetDst = 0;
	int rowOffset = bpr % sci->w;
	for (int row = 0; row < sci->h; ++row){
		for (int col = 0; col < sci->w; ++col){
			unsigned char r=0;
			unsigned char g=0;
			unsigned char b=0;
			if (bpp>24){
				r = data[offsetSrc+2];
				g = data[offsetSrc+1];
				b = data[offsetSrc];
				offsetSrc += 4;
			}else if (bpp>16){
				r = data[offsetSrc+2];
				g = data[offsetSrc+1];
				b = data[offsetSrc];
				offsetSrc += 3;
			/*}else if (bpp>8){
				unsigned int pixel=(data[offsetSrc+1] << 8) | (data[offsetSrc]);
				r = (pixel & sci->image->red_mask) >> sci->redlshift;
				g = (pixel & sci->image->green_mask) >> sci->greenlshift;
				b = (pixel & sci->image->blue_mask) << sci->bluershift;
				offsetSrc += 2;
			}else{
				unsigned int pixel=(data[offsetSrc]);
				r = (pixel & sci->image->red_mask) >> sci->redlshift;
				g = (pixel & sci->image->green_mask) >> sci->greenlshift;
				b = (pixel & sci->image->blue_mask) << sci->bluershift;
				offsetSrc += 1;*/
			}
			if ((rgbimage->sizechangearea==0) and ((sci->status==1) or ((rgbimage->data[offsetDst] != r) or (rgbimage->data[offsetDst+1] != g) or (rgbimage->data[offsetDst+2] != b)))){
				rgbimage->sizechangearea=1;
				rgbimage->changearea[0].x=0;
				rgbimage->changearea[0].y=0;
				rgbimage->changearea[0].width=sci->w;
				rgbimage->changearea[0].height=sci->h;
			}
			rgbimage->data[offsetDst] = r;
			rgbimage->data[offsetDst+1] = g;
			rgbimage->data[offsetDst+2] = b;
			offsetDst += 3;
		}
		offsetSrc += rowOffset;
	}
	CFRelease(dataref);
	CGImageRelease(image_ref);
	sci->status=2;
	return 0;
}

int DWAScreenCaptureCursor(CURSOR_IMAGE* curimage){
	if ((factx==-1) || (facty==-1)){
		return false;
	}
	curimage->changed=0;
	CGEventRef event = CGEventCreate(NULL);
	if (event!=NULL){
		if (curimage->data==NULL){
			curimage->changed=1;
			setCursorImage(CURSOR_TYPE_ARROW_18_18,curimage);
		}
		curimage->visible=1;
		CGPoint cursor = CGEventGetLocation(event);
		curimage->x=(int)cursor.x*factx;
		curimage->y=(int)cursor.y*facty;
		CFRelease(event);
		return 0;
	}
	return -1;
}

void DWAScreenCaptureInputKeyboard(const char* type, const char* key, bool ctrl, bool alt, bool shift, bool command){
	macInputs->keyboard(type, key, ctrl, alt, shift, command);
}

void DWAScreenCaptureInputMouse(MONITORS_INFO_ITEM* moninfoitem, int x, int y, int button, int wheel, bool ctrl, bool alt, bool shift, bool command){
	if ((factx!=-1) and (facty!=-1)){
		macInputs->mouse(moninfoitem, x, y, factx, facty, button, wheel, ctrl, alt, shift, command);
	}
}

void DWAScreenCaptureCopy(){
	macInputs->copy();
}

void DWAScreenCapturePaste(){
	macInputs->paste();
}

int DWAScreenCaptureGetClipboardText(wchar_t** wText){
	usleep(200000);
	return macobjcGetClipboardText(wText);
}

void DWAScreenCaptureSetClipboardText(wchar_t* wText){
	macobjcSetClipboardText(wText);
	usleep(200000);
}

int DWAScreenCaptureGetCpuUsage(){
	return (int)cpuUsage->getValue();
}

/*int clearMonitorsInfo(MONITORS_INFO* moninfo){
	moninfo->changed=0;
	for (int i=0;i<=MONITORS_INFO_ITEM_MAX-1;i++){
		moninfo->monitor[i].changed=-1;
	}
	for (int i=0;i<=moninfo->count-1;i++){
		moninfo->monitor[i].changed=0;
	}
	int oldmc=moninfo->count;
	moninfo->count=0;
	return oldmc;
}

void addMonitorsInfo(MONITORS_INFO* moninfo, int x, int y, int w, int h, int did){
	int p=moninfo->count;
	moninfo->count+=1;
	MonitorInternalInfo* mi = NULL;
	if (moninfo->monitor[p].internal==NULL){
		mi = new MonitorInternalInfo();
		moninfo->monitor[p].internal=mi;
	}else{
		mi = (MonitorInternalInfo*)moninfo->monitor[p].internal;
	}
	if (moninfo->monitor[p].changed==-1){
		moninfo->monitor[p].index=p;
		moninfo->monitor[p].x=x;
		moninfo->monitor[p].y=y;
		moninfo->monitor[p].width=w;
		moninfo->monitor[p].height=h;
		mi->displayID=did;
		moninfo->monitor[p].changed=1;
		moninfo->changed=1;
	}else{
		if ((mi->displayID!=did) || (moninfo->monitor[p].x!=x) || (moninfo->monitor[p].y!=y) || (moninfo->monitor[p].width!=w) || (moninfo->monitor[p].height!=h)){
			moninfo->monitor[p].index=p;
			moninfo->monitor[p].x=x;
			moninfo->monitor[p].y=y;
			moninfo->monitor[p].width=w;
			moninfo->monitor[p].height=h;
			mi->displayID=did;
			moninfo->monitor[p].changed=1;
			moninfo->changed=1;
		}else{
			moninfo->monitor[p].changed=0;
		}
	}
}
*/

int DWAScreenCaptureGetMonitorsInfo(MONITORS_INFO* moninfo){
	int iret=0;
	//int oldmc=clearMonitorsInfo(moninfo);
	/*CGDirectDisplayID display[MONITORS_MAX];
	CGDisplayCount numDisplays;
	CGDisplayErr err;
	err = CGGetActiveDisplayList(MONITORS_MAX, display, &numDisplays);
	if (err == CGDisplayNoErr){
		for (CGDisplayCount i = 0; i < numDisplays; ++i) {
			CGDirectDisplayID dspy = display[i];
			printf("CGDirectDisplayID %d\n",dspy);
		}
	}*/

	mainDisplayID = CGMainDisplayID();
	//wakeup monitor
	if (CGDisplayIsAsleep(mainDisplayID)){
#if (MAC_OS_X_VERSION_MAX_ALLOWED < 120000)
		#define kIOMainPortDefault kIOMasterPortDefault
#endif
		io_registry_entry_t reg = IORegistryEntryFromPath(kIOMainPortDefault, "IOService:/IOResources/IODisplayWrangler");
		if (reg){
			IORegistryEntrySetCFProperty(reg, CFSTR("IORequestIdle"), kCFBooleanFalse);
		}
		IOObjectRelease(reg);
	}
	moninfo->changed=0;
	CGDisplayModeRef dmd = CGDisplayCopyDisplayMode(mainDisplayID);
	int wm = CGDisplayModeGetWidth(dmd);
	int hm = CGDisplayModeGetHeight(dmd);
	int w = wm;
	int h = hm;
	CGImageRef image_ref = CGDisplayCreateImage(mainDisplayID);
	if (image_ref!=NULL){
		CGDataProviderRef provider = CGImageGetDataProvider(image_ref);
		CFDataRef dataref = CGDataProviderCopyData(provider);
		w = CGImageGetWidth(image_ref);
		h = CGImageGetHeight(image_ref);
		CFRelease(dataref);
		CGImageRelease(image_ref);
	}
	int p=0;
	if (moninfo->count==0){
		factx = (float)w/(float)wm;
		facty = (float)h/(float)hm;
		moninfo->monitor[p].index=p;
		moninfo->monitor[p].x=0;
		moninfo->monitor[p].y=0;
		moninfo->monitor[p].width=w;
		moninfo->monitor[p].height=h;
		moninfo->monitor[p].changed=1;
		moninfo->changed=1;
		moninfo->count=1;
		//addMonitorsInfo(moninfo,x,y,w,h,mainDisplay);
	}else if ((moninfo->monitor[p].width!=w) || (moninfo->monitor[p].height!=h)){
			factx = (float)w/(float)wm;
			facty = (float)h/(float)hm;
			moninfo->monitor[p].width=w;
			moninfo->monitor[p].height=h;
			moninfo->monitor[p].changed=1;
			moninfo->changed=1;
	}
	/*if (oldmc!=moninfo->count){
		moninfo->changed=1;
	}*/
	return iret;
}

bool DWAScreenCaptureLoad(){
	cpuUsage=new MacCPUUsage();
	macInputs=new MacInputs();
	mainDisplayID=-1;
	factx=-1;
	facty=-1;
	CFStringRef reasonForActivity=CFSTR("dwagent keep awake");
	successIOPM1 = kIOReturnError;
	successIOPM1 = IOPMAssertionCreateWithName(kIOPMAssertionTypeNoDisplaySleep, kIOPMAssertionLevelOn, reasonForActivity, &assertionIDIOPM1);
	successIOPM2 = kIOReturnError;
	successIOPM2 = IOPMAssertionCreateWithName(CFSTR("UserIsActive"), kIOPMAssertionLevelOn, reasonForActivity, &assertionIDIOPM2);
	return true;
}

void DWAScreenCaptureUnload(){
	delete cpuUsage;
	delete macInputs;
	if(successIOPM1 == kIOReturnSuccess) {
		IOPMAssertionRelease(assertionIDIOPM1);
		successIOPM1 = kIOReturnError;
	}
	if(successIOPM2 == kIOReturnSuccess) {
		IOPMAssertionRelease(assertionIDIOPM2);
		successIOPM2 = kIOReturnError;
	}
}


#endif
