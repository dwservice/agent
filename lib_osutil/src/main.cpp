/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/

#include "main.h"

DiskMng diskmng = DiskMng();
TaskMng taskmng = TaskMng();
PerformanceMng performancemng = PerformanceMng();
ServiceMng servicemng = ServiceMng();
SystemMng systemmng = SystemMng();


#if defined OS_WINDOWS
void freeMemory(LPVOID lp) {
    free(lp);
}
#endif


int taskKill(int pid){
	return taskmng.taskKill(pid);
}
int isTaskRunning(int pid){
	return taskmng.isTaskRunning(pid);
}

 int DWAOSUtilGetTaskList(wchar_t** sret){
	return taskmng.getTaskList(sret);
}

int DWAOSUtilGetServiceList(wchar_t** sret){
	return servicemng.getServiceList(sret);
}

int startService(wchar_t* serviceName){
	return servicemng.startService(serviceName);
}

int stopService(wchar_t* serviceName){
	return servicemng.stopService(serviceName);
}

int DWAOSUtilGetSystemInfo(wchar_t** sret){
	return systemmng.getInfo(sret);
}

int DWAOSUtilGetPerformanceInfo(wchar_t** sret){
	return performancemng.getInfo(sret);
}

int DWAOSUtilGetDiskInfo(wchar_t** sret){
	return diskmng.getInfo(sret);
}

int isFileJunction(wchar_t* path){
	return diskmng.isFileJunction(path);
}

int wmain(int argc, wchar_t **argv) {
	return 0;
}
