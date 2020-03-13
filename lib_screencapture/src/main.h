/* 
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
 */

#ifndef MAIN_H_
#define MAIN_H_

#include "screencapture.h"

#if defined OS_MAC
#include <SystemConfiguration/SystemConfiguration.h>
#endif

#if defined OS_WINDOWS
#include <Userenv.h>
#endif


extern "C" {

int version();
void freeMemory(void* pnt);
void init(int id);
void monitor(int id, int index);
void difference(int id, int typeFrame, int quality, CallbackDifference cbdiff);
void term(int id);
void inputMouse(int id, int x, int y, int button, int wheel, bool ctrl, bool alt, bool shift, bool command);
void inputKeyboard(int id, const char* type, const char* key, bool ctrl, bool alt, bool shift, bool command);
void setCallbackDebug(CallbackType callback);
wchar_t* copyText(int id);
void pasteText(int id, wchar_t* str);

#if defined OS_WINDOWS
int startProcessAsUser(wchar_t* scmd, wchar_t* pythonHome);
int isWinNTFamily();
int isWinXP();
int isWin2003Server();
int isWin2008Server();
int isVistaOrLater();
int sas();
long consoleSessionId();
void winStationConnectW();
int isUserInAdminGroup();
int isRunAsAdmin();
int isProcessElevated();
void setAsElevated(int i);
#endif

#if defined OS_MAC
int consoleUserId();
#endif

}

#endif /* MAIN_H_ */
