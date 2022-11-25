/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/
#if defined OS_WINDOWS
using namespace std;
#include "windowsloadlib.h"
#include <windows.h>
#include <string>
#include "../common/util.h"
#include "../common/logger.h"
#include "../common/timecounter.h"


#ifndef WINDOWSDESKTOP_H_
#define WINDOWSDESKTOP_H_

class WindowsDesktop{

public:
	WindowsDesktop(void );
    ~WindowsDesktop( void );
    LRESULT CALLBACK windowProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam);
    DWORD WINAPI createWindow();
    int setCurrentThread();
    bool checkWindowsLayered();
    void destroy();
    void ctrlaltcanc();
    void monitorON();
    void getClipboardChanges(CLIPBOARD_DATA* clipboardData);
    void setClipboard(CLIPBOARD_DATA* clipboardData);
    void clearClipboardXP();

private:
    WindowsLoadLib* loadLibWin;
    wchar_t prevDesktopName[1024];
    OSVERSIONINFOEX m_osVerInfo;
    bool runAsElevated;
    HWND hwndwts;
    BOOL CALLBACK checkLayered(HWND hWnd, LPARAM lParam);
    HDESK getInputDesktop();
    HDESK getDesktop(char* name);
    bool isWinNTFamily();
	bool isWinXP();
    bool selectDesktop(char* name);
    bool bclipboardchanged;
    TimeCounter tcclipboardxp;
    wchar_t* oldclipboardxp;
};

#endif /* WINDOWSDESKTOP_H_ */

#endif
