/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/

#include "diskmng.h"
#include "performancemng.h"
#include "taskmng.h"
#include "servicemng.h"
#include "systemmng.h"

#ifndef MAIN_H_
#define MAIN_H_

extern "C"{
  
#if defined OS_WINDOWS
void freeMemory(LPVOID lb);
#endif

int taskKill(int pid);
int isTaskRunning(int pid);
wchar_t* getTaskList();

wchar_t* getServiceList();
int startService(wchar_t* serviceName);
int stopService(wchar_t* serviceName);

wchar_t* getSystemInfo();
wchar_t* getPerformanceInfo();

wchar_t* getDiskInfo();
int isFileJunction(wchar_t* path);
}


#endif /* MAIN_H_ */

