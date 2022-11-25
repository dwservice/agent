/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/
#if defined OS_BITBLT

#include "screencapturenativebitblt.h"


int DWAScreenCaptureVersion(){
	return 2;
}

void DWAScreenCaptureFreeMemory(void* pnt){
	free(pnt);
}

int DWAScreenCaptureGetCpuUsage(){
	return (int)cpuUsage->getValue();
}

int DWAScreenCaptureIsChanged(){
	return winDesktop->setCurrentThread();
}

void addMonitorsInfo(MONITORS_INFO* moninfo, int x, int y, int w, int h,HMONITOR hMonitor){
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
		mi->hMonitor=hMonitor;
		moninfo->monitor[p].changed=1;
		moninfo->changed=1;
	}else{
		if ((mi->hMonitor!=hMonitor) || (moninfo->monitor[p].x!=x) || (moninfo->monitor[p].y!=y) || (moninfo->monitor[p].width!=w) || (moninfo->monitor[p].height!=h)){
			moninfo->monitor[p].index=p;
			moninfo->monitor[p].x=x;
			moninfo->monitor[p].y=y;
			moninfo->monitor[p].width=w;
			moninfo->monitor[p].height=h;
			mi->hMonitor=hMonitor;
			moninfo->monitor[p].changed=1;
			moninfo->changed=1;
		}else{
			moninfo->monitor[p].changed=0;
		}
	}
}

int clearMonitorsInfo(MONITORS_INFO* moninfo){
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

BOOL CALLBACK monitorEnumProc(HMONITOR hMonitor,HDC hdcMonitor,LPRECT lprcMonitor,LPARAM dwData){
	MONITORS_INFO* moninfo = reinterpret_cast<MONITORS_INFO*>(dwData);
	int x=lprcMonitor->left;
	int y=lprcMonitor->top;
	int w=lprcMonitor->right-lprcMonitor->left;
	int h=lprcMonitor->bottom-lprcMonitor->top;
	addMonitorsInfo(moninfo,x,y,w,h,hMonitor);
	return TRUE;
}

int DWAScreenCaptureGetMonitorsInfo(MONITORS_INFO* moninfo){
	winDesktop->monitorON();
	int oldmc=clearMonitorsInfo(moninfo);
	if (oldmc<0){
		return oldmc;
	}
	HDC hdc = GetDC(NULL);
	EnumDisplayMonitors(hdc, 0, monitorEnumProc, reinterpret_cast<LPARAM>(moninfo));
	ReleaseDC(NULL,hdc);
	if (moninfo->count==0){
		int x=GetSystemMetrics(SM_XVIRTUALSCREEN);
		int y=GetSystemMetrics(SM_YVIRTUALSCREEN);
		int w=GetSystemMetrics(SM_CXVIRTUALSCREEN);
		int h=GetSystemMetrics(SM_CYVIRTUALSCREEN);
		addMonitorsInfo(moninfo,x,y,w,h,NULL);
	}
	if (oldmc!=moninfo->count){
		moninfo->changed=1;
	}
	return 0;
}

bool DWAScreenCaptureLoad() {
	//checkBlockInputsWin=NULL;
	winDesktop=new WindowsDesktop();
	winInputs=new WindowsInputs();
	cpuUsage=new WindowsCPUUsage();
	winDesktop->monitorON();
	Sleep(500);
	return true;
}

void DWAScreenCaptureUnload() {
	//cursorHandle = NULL;
	////restoreVisualEffect
	delete winDesktop;
	delete winInputs;
	delete cpuUsage;
}

int DWAScreenCaptureCursor(CURSOR_IMAGE* curimage) {
	CursorInternalInfo* cursorInternalInfo = NULL;
	if (curimage->internal==NULL){
		cursorInternalInfo = new CursorInternalInfo();
		curimage->internal=cursorInternalInfo;
	}else{
		cursorInternalInfo=(CursorInternalInfo*)curimage->internal;
	}
	curimage->changed=0;
	CURSORINFO appCursorInfo;
	appCursorInfo.cbSize = sizeof(CURSORINFO);
	if (GetCursorInfo(&appCursorInfo)){
		curimage->x=appCursorInfo.ptScreenPos.x;
		curimage->y=appCursorInfo.ptScreenPos.y;
		if (appCursorInfo.flags!=0){
			curimage->visible=1;
			if ((curimage->data==NULL) || (appCursorInfo.hCursor!=cursorInternalInfo->hCursor)){
				bool bok = false;
				cursorInternalInfo->hCursor=appCursorInfo.hCursor;
				ICONINFO info;
				if (GetIconInfo(appCursorInfo.hCursor, &info)){
					BITMAP bmMask;
					GetObject(info.hbmMask, sizeof(BITMAP), (LPVOID)&bmMask);
					if (bmMask.bmPlanes != 1 || bmMask.bmBitsPixel != 1) {
						DeleteObject(info.hbmMask);
					}else{
						//unsigned char* dataNorm = NULL;
						//unsigned char* dataMask = NULL;
						bool isColorShape = (info.hbmColor != NULL);
						int w = bmMask.bmWidth;
						int h = isColorShape ? bmMask.bmHeight : bmMask.bmHeight/2;
						//int nbit = bmMask.bmWidthBytes;

						//IMAGE
						HDC hdstImage = CreateCompatibleDC(NULL);
						BITMAPINFO biImage;
						ZeroMemory(&biImage, sizeof(BITMAPINFO));
						biImage.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
						biImage.bmiHeader.biBitCount = 32;
						biImage.bmiHeader.biCompression = BI_RGB;
						biImage.bmiHeader.biPlanes = 1;
						biImage.bmiHeader.biWidth = w;
						biImage.bmiHeader.biHeight = -h;
						biImage.bmiHeader.biSizeImage = 0;
						biImage.bmiHeader.biXPelsPerMeter = 0;
						biImage.bmiHeader.biYPelsPerMeter = 0;
						biImage.bmiHeader.biClrUsed = 0;
						biImage.bmiHeader.biClrImportant = 0;
						void *bufferImage;
						HANDLE hbmDIBImage = CreateDIBSection(hdstImage, (BITMAPINFO*)&biImage, DIB_RGB_COLORS, &bufferImage, NULL, 0);
						HANDLE hbmDIBOLDImage = (HBITMAP)SelectObject(hdstImage, hbmDIBImage);
						unsigned char* appDataImage = (unsigned char*)bufferImage;

						//MASK
						HDC hdstMask = CreateCompatibleDC(NULL);
						BITMAPINFO biMask;
						ZeroMemory(&biMask, sizeof(BITMAPINFO));
						biMask.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
						biMask.bmiHeader.biBitCount = 32;
						biMask.bmiHeader.biCompression = BI_RGB;
						biMask.bmiHeader.biPlanes = 1;
						biMask.bmiHeader.biWidth = w;
						biMask.bmiHeader.biHeight = -h;
						biMask.bmiHeader.biSizeImage = 0;
						biMask.bmiHeader.biXPelsPerMeter = 0;
						biMask.bmiHeader.biYPelsPerMeter = 0;
						biMask.bmiHeader.biClrUsed = 0;
						biMask.bmiHeader.biClrImportant = 0;
						void *bufferMask;
						HANDLE hbmDIBMask = CreateDIBSection(hdstMask, (BITMAPINFO*)&biMask, DIB_RGB_COLORS, &bufferMask, NULL, 0);
						HANDLE hbmDIBOLDMask = (HBITMAP)SelectObject(hdstMask, hbmDIBMask);
						unsigned char* appDataMask = (unsigned char*)bufferMask;

						bool cursorCheckMask=true;
						unsigned char* cursorData = NULL;
						if (DrawIconEx(hdstImage, 0, 0, (HICON)appCursorInfo.hCursor, 0, 0, 0, NULL, DI_IMAGE)) {
							int isck = 0;
							for (int y=0; y<h; y++) {
								for (int x=0; x<w; x++) {
									if ((appDataImage[isck + 3])>0) {
										cursorCheckMask = false;
										break;
									}
									isck += 4;
								}
							}
							if (DrawIconEx(hdstMask, 0, 0, (HICON)appCursorInfo.hCursor, 0, 0, 0, NULL, DI_MASK)) {
								cursorData = (unsigned char*)malloc((w * h) * 4);
								int is = 0;
								int id = 0;
								for (int y=0; y<h; y++) {
									for (int x=0; x<w; x++) {
										unsigned char r;
										unsigned char g;
										unsigned char b;
										unsigned char a;
										if (cursorCheckMask){
											r = appDataImage[is + 2];
											g = appDataImage[is + 1];
											b = appDataImage[is];
											if ((appDataMask[is + 2]==0) && (appDataMask[is + 1]==0) && (appDataMask[is]==0)){
												a = 255;
											}else{
												if ((appDataMask[is + 2]==appDataImage[is + 2]) && (appDataMask[is + 1]==appDataImage[is + 1]) && (appDataMask[is]==appDataImage[is])){
													r = 128;
													g = 128;
													b = 128;
													a = 255;
												}else{
													a = 0;
												}
											}
										}else{
											r = appDataImage[is + 2];
											g = appDataImage[is + 1];
											b = appDataImage[is];
											a = appDataImage[is + 3];
										}
										cursorData[id] = r;
										cursorData[id + 1] = g;
										cursorData[id + 2] = b;
										cursorData[id + 3] = a;
										id += 4;
										is += 4;
									}
								}
								bok = true;
							}
						}
						if (bok){
							curimage->width=w;
							curimage->height=h;
							if (info.fIcon==FALSE){
								curimage->offx = info.xHotspot;
								curimage->offy = info.yHotspot;
							}else{
								curimage->offx = w/2;
								curimage->offy = h/2;
							}
							curimage->changed=1;
							if (curimage->data!=NULL){
								free(curimage->data);
							}
							curimage->data = cursorData;
							curimage->sizedata = curimage->width*curimage->height*4;
						}

						SelectObject(hdstImage, hbmDIBOLDImage);
						DeleteObject(hbmDIBImage);
						DeleteDC(hdstImage);

						SelectObject(hdstMask, hbmDIBOLDMask);
						DeleteObject(hbmDIBMask);
						DeleteDC(hdstMask);
					}
				}
				if (!bok){
					if (curimage->data==NULL){
						curimage->changed=1;
						setCursorImage(CURSOR_TYPE_ARROW_18_18,curimage);
					}
				}
			}
		}else{ //Cursore nascosto
			curimage->visible=1;
			if (curimage->data==NULL){
				curimage->changed=1;
				setCursorImage(CURSOR_TYPE_ARROW_18_18,curimage);
			}
		}
	}else{
		POINT point;
		if (GetCursorPos(&point)) {
			curimage->visible=1;
			curimage->x=point.x;
			curimage->y=point.y;
			if (curimage->data==NULL){
				curimage->changed=1;
				setCursorImage(CURSOR_TYPE_ARROW_18_18,curimage);
			}
		}else{
			return -1;
		}
	}
	return 0;
}

int DWAScreenCaptureInitMonitor(MONITORS_INFO_ITEM* moninfoitem, RGB_IMAGE* capimage, void** capses){
	ScreenCaptureInfo* sci = new ScreenCaptureInfo();
	sci->monitor=moninfoitem->index;
	sci->x=moninfoitem->x;
	sci->y=moninfoitem->y;
	sci->w=moninfoitem->width;
	sci->h=moninfoitem->height;
	sci->rgbimage=capimage;
	sci->rgbimage->width=moninfoitem->width;
	sci->rgbimage->height=moninfoitem->height;
	sci->bpp = 24;
	sci->bpc = 3;
	sci->bpr = ((((moninfoitem->width * sci->bpp) + 31) & ~31) >> 3);
	sci->rgbimage->sizedata=sci->rgbimage->width*sci->rgbimage->height*3;
	sci->rgbimage->sizechangearea=0;
	sci->rgbimage->sizemovearea=0;
	sci->rgbimage->data=(unsigned char*)malloc(sci->rgbimage->sizedata * sizeof(unsigned char));
	ZeroMemory(&sci->bitmapInfo, sizeof(BITMAPINFO));
	sci->bitmapInfo.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
	sci->bitmapInfo.bmiHeader.biBitCount = sci->bpp;
	sci->bitmapInfo.bmiHeader.biCompression = BI_RGB;
	sci->bitmapInfo.bmiHeader.biPlanes = 1;
	sci->bitmapInfo.bmiHeader.biWidth = sci->w;
	sci->bitmapInfo.bmiHeader.biHeight = -sci->h;
	sci->hsrcDC = GetDC(NULL);
	sci->hdestDC = CreateCompatibleDC(NULL);
	void *buffer;
	sci->hbmDIB = CreateDIBSection(sci->hdestDC, (BITMAPINFO*)&sci->bitmapInfo, DIB_RGB_COLORS, &buffer, NULL, 0);
	sci->hbmDIBOLD = (HBITMAP)SelectObject(sci->hdestDC, sci->hbmDIB);
	sci->data = (unsigned char*)buffer;
	/*sci->hbitmap = CreateCompatibleBitmap(sci->hsrcDC, moninfoitem->width,moninfoitem->height);
	sci->hbitmapOLD = (HBITMAP)SelectObject(sci->hdestDC, sci->hbitmap);*/
	sci->status=1;
	*capses=sci;
	return 0;
}

void DWAScreenCaptureTermMonitor(void* capses){
	ScreenCaptureInfo* sci = (ScreenCaptureInfo*)capses;
	if (sci->status==0){
		return;
	}
	SelectObject(sci->hdestDC,sci->hbmDIBOLD);
	DeleteObject(sci->hbmDIB);
	DeleteDC(sci->hdestDC);
	ReleaseDC(NULL,sci->hsrcDC);
	sci->data = NULL;
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
	//CHECK WINDOWS LAYERED
	DWORD flgcpt = SRCCOPY;
	if (winDesktop->checkWindowsLayered()){
		flgcpt = SRCCOPY | CAPTUREBLT;
	}
	//SCREEN CAPTURE
	if (!BitBlt(sci->hdestDC, 0, 0, sci->w, sci->h, sci->hsrcDC, sci->x, sci->y, flgcpt)) {
		char msgerr[500];
		sprintf(msgerr,"BitBlt error code: %ld",GetLastError());
		return -3; //bitblt error
	}

	RGB_IMAGE* rgbimage=sci->rgbimage;
	rgbimage->sizechangearea=0;
	rgbimage->sizemovearea=0;


	//CONVERT IN RGB
	int offsetSrc = 0;
	int offsetDst = 0;
	int rowOffset = sci->bpr % sci->w;
	for (int row = 0; row < sci->h; ++row){
		for (int col = 0; col < sci->w; ++col){
			if ((rgbimage->sizechangearea==0) and ((sci->status==1) or ((rgbimage->data[offsetDst] != sci->data[offsetSrc+2]) or (rgbimage->data[offsetDst+1] != sci->data[offsetSrc+1]) or (rgbimage->data[offsetDst+2] != sci->data[offsetSrc])))){
				rgbimage->sizechangearea=1;
				rgbimage->changearea[0].x=0;
				rgbimage->changearea[0].y=0;
				rgbimage->changearea[0].width=sci->w;
				rgbimage->changearea[0].height=sci->h;
			}
			rgbimage->data[offsetDst] = sci->data[offsetSrc+2];
			rgbimage->data[offsetDst+1] = sci->data[offsetSrc+1];
			rgbimage->data[offsetDst+2] = sci->data[offsetSrc];
			offsetSrc += 3;
			offsetDst += 3;
		}
		offsetSrc += rowOffset;
	}
	sci->status=2;
	return 0;
}


void DWAScreenCaptureInputKeyboard(const char* type,const char* key, bool ctrl, bool alt, bool shift, bool command){
	winInputs->keyboard(type, key, ctrl, alt, shift, command);
	if (strcmp(type,"CTRLALTCANC")==0){
		winDesktop->ctrlaltcanc();
	}
}

void DWAScreenCaptureInputMouse(MONITORS_INFO_ITEM* moninfoitem, int x, int y, int button, int wheel, bool ctrl, bool alt, bool shift, bool command){
	winInputs->mouse(moninfoitem, x, y, button, wheel, ctrl, alt, shift, command);
	/*if ((p==1) && (button==-1) && (mouseData==0) && (mx!=-1) && (my!=1)){ //INPUT BLOCKED BY FOREGROUND WINDOWS
		HWND h = GetForegroundWindow();
		if (h!=checkBlockInputsWin){
			POINT pnt;
			SetCursorPos(mx,my);
			if (GetCursorPos(&pnt)==TRUE){
				if ((mx!=pnt.x) || (my!=pnt.y)){
					SetForegroundWindow(hwndwts);
				}
			}else{
				sendInputs(inputs,p);
			}
		}else{
			sendInputs(inputs,p);
		}
		checkBlockInputsWin=h;
	}else{
		sendInputs(inputs,p);
	}*/
}

void DWAScreenCaptureCopy(){
	winDesktop->clearClipboardXP();
	winInputs->copy();
}

void DWAScreenCapturePaste(){
	winInputs->paste();
}

void DWAScreenCaptureGetClipboardChanges(CLIPBOARD_DATA* clipboardData){
	winDesktop->getClipboardChanges(clipboardData);
}

void DWAScreenCaptureSetClipboard(CLIPBOARD_DATA* clipboardData){
	winDesktop->setClipboard(clipboardData);
}


int wmain(int argc, wchar_t **argv) {
	DWAScreenCaptureLoad();
	MONITORS_INFO moninfo;
	DWAScreenCaptureGetMonitorsInfo(&moninfo);
	DWAScreenCaptureUnload();
	return 0;
}

//TMP PRIVACY MODE
void DWAScreenCaptureSetPrivacyMode(bool b){
	return WindowsLoadLibSetPrivacyMode(b);
}

#endif
