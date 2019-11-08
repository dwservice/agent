/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/
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

typedef void (*CallbackTypeRepaint)(int id, int x,int y,int w, int h);
typedef void (*CallbackTypeKeyboard)(int id, wchar_t* type,wchar_t* c,bool shift,bool ctrl,bool alt,bool meta);
typedef void (*CallbackTypeMouse)(int id, wchar_t* type, int x, int y, int button);
typedef bool (*CallbackTypeWindow)(int id, wchar_t* type);
typedef void (*CallbackTypeTimer)();

extern "C"{
	void setCallbackRepaint(CallbackTypeRepaint callback);
	void setCallbackKeyboard(CallbackTypeKeyboard callback);
	void setCallbackMouse(CallbackTypeMouse callback);
	void setCallbackWindow(CallbackTypeWindow callback);
	void setCallbackTimer(CallbackTypeTimer callback);
	void loop();
	int newWindow(int tp,int x, int y, int w, int h, wchar_t* iconPath);
	void destroyWindow(int id);
	void setTitle(int id, wchar_t* title);
	void show(int id,int mode);
	void hide(int id);
	void toFront(int id);
	void penColor(int id, int r, int g, int b);
	void penWidth(int id, int w);
	void drawLine(int id, int x1,int y1,int x2,int y2);
	void drawEllipse(int id, int x, int y, int w,int h);
	void fillEllipse(int id, int x, int y, int w,int h);
	void drawText(int id, wchar_t* str, int x, int y);
	void fillRectangle(int id, int x, int y, int w,int h);
	void drawImageFromFile(int id, wchar_t* fname, int x, int y, int w, int h);
	void getImageSize(wchar_t* fname, int* sz);

	void getScreenSize(int* size);

	int getTextHeight(int id);
	int getTextWidth(int id,wchar_t* str);
	void repaint(int id, int x, int y, int w,int h);
	void clipRectangle(int id, int x, int y, int w, int h);
	void clearClipRectangle(int id);

	void setClipboardText(wchar_t* str);
	wchar_t* getClipboardText();

	void createNotifyIcon(int id,wchar_t* iconPath,wchar_t* toolTip);
	void updateNotifyIcon(int id,wchar_t* iconPath,wchar_t* toolTip);
	void destroyNotifyIcon(int id);
	void getMousePosition(int* pos);

#if defined OS_WINDOWS
	HWND getWindowHWNDByID(int id);
	int isUserInAdminGroup();
	int isRunAsAdmin();
	int isProcessElevated();
	int isTaskRunning(int pid);
#endif

}

#endif /* MAIN_H_ */
#endif
