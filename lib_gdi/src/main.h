/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/
#include "jsonwriter.h"
#include "imagereader.h"
#if defined OS_MAC
#else
#if defined OS_WINDOWS
#include <windows.h>
#include <windowsX.h>
#include <vector>
#include <Shellapi.h>
#include <Shlwapi.h>
#endif

#ifndef MAIN_H_
#define MAIN_H_

const int WINDOW_TYPE_NORMAL=0;
const int WINDOW_TYPE_NORMAL_NOT_RESIZABLE=1;
const int WINDOW_TYPE_DIALOG=100;
const int WINDOW_TYPE_POPUP=200;
const int WINDOW_TYPE_TOOL=300;

typedef void (*CallbackEventMessage)(const wchar_t* msg);

extern "C"{
	void DWAGDILoop(CallbackEventMessage callback);
	void DWAGDIEndLoop();
	void DWAGDILoadFont(int id,wchar_t* name);
	void DWAGDIUnloadFont(int id);
	int DWAGDIGetTextHeight(int id, int fntid);
	int DWAGDIGetTextWidth(int id, int fntid, wchar_t* str);
	void DWAGDIDrawText(int id, int fntid, wchar_t* str, int x, int y);
	void DWAGDINewWindow(int id,int tp,int x, int y, int w, int h, wchar_t* iconPath);
	void DWAGDIDestroyWindow(int id);
	void DWAGDIPosSizeWindow(int id,int x, int y, int w, int h);
	void DWAGDISetTitle(int id, wchar_t* title);
	void DWAGDIShow(int id,int mode);
	void DWAGDIHide(int id);
	void DWAGDIToFront(int id);
	void DWAGDIPenColor(int id, int r, int g, int b);
	void DWAGDIPenWidth(int id, int w);
	void DWAGDIDrawLine(int id, int x1, int y1, int x2, int y2);
	void DWAGDIDrawEllipse(int id, int x, int y, int w, int h);
	void DWAGDIFillEllipse(int id, int x, int y, int w, int h);
	void DWAGDIFillRectangle(int id, int x, int y, int w, int h);
	void DWAGDIGetScreenSize(int* size);
	void DWAGDIGetImageSize(wchar_t* fname, int* size);
	void DWAGDIRepaint(int id, int x, int y, int w, int h);
	void DWAGDIClipRectangle(int id, int x, int y, int w, int h);
	void DWAGDIClearClipRectangle(int id);
	void DWAGDISetClipboardText(wchar_t* str);
	wchar_t* DWAGDIGetClipboardText();
	void DWAGDICreateNotifyIcon(int id, wchar_t* iconPath, wchar_t* toolTip);
	void DWAGDIUpdateNotifyIcon(int id, wchar_t* iconPath, wchar_t* toolTip);
	void DWAGDIDestroyNotifyIcon(int id);
	void DWAGDIGetMousePosition(int* pos);
	void DWAGDILoadImage(int id, wchar_t* fname, int* size);
	void DWAGDIUnloadImage(int id);
	void DWAGDIDrawImage(int id, int imgid, int x, int y);

#if defined OS_WINDOWS
	HWND getWindowHWNDByID(int id);
	int isUserInAdminGroup();
	int isRunAsAdmin();
	int isProcessElevated();
	int isTaskRunning(int pid);
#endif

#if defined OS_MAC
	void DWAGDINSAppSetActivationPolicy(int v);
#endif
}

#endif /* MAIN_H_ */
#endif
