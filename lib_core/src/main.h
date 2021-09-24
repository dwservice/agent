/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/
#if defined OS_WINDOWS
#include <windows.h>
#include <Aclapi.h>
#include <shlobj.h>
#include <vector>
#include <Userenv.h>
typedef BOOL (WINAPI *IWinStationConnectW)(HANDLE server, ULONG connectSessionId,ULONG activeSessionId, PCWSTR password, ULONG unknown);
#endif
#if defined OS_LINUX
#include <iostream>
#include <fcntl.h>
#include <semaphore.h>
#include <sys/stat.h>
#include <sys/mman.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#endif
#if defined OS_MAC
#include <iostream>
#include <fcntl.h>
#include <semaphore.h>
#include <sys/stat.h>
#include <sys/mman.h>
#include <SystemConfiguration/SystemConfiguration.h>
#endif

#ifndef MAIN_H_
#define MAIN_H_



extern "C"{
#if defined OS_WINDOWS
	int taskKill(int pid);
	int isTaskRunning(int pid);
	void setFilePermissionEveryone(LPCTSTR FileName);
	int isWinXP();
	int isWin2003Server();
	int isUserInAdminGroup();
	int isRunAsAdmin();
	int isProcessElevated();
	long getActiveConsoleId();
	int startProcess(wchar_t* scmd, wchar_t* pythonHome);
	int startProcessInActiveConsole(wchar_t* scmd, wchar_t* pythonHome);
	void winStationConnect();
	void closeHandle(HANDLE hdl);
#else
	typedef struct{
		int create;
		int mode;
		int fd;
		int semvalue;
		sem_t* sem;
		char* name;
	} SEMAPHORE_DEF;

	typedef struct{
		int create;
		int mode;
		int fd;
		int size;
		char* name;
	} SHAREDMEMORY_DEF;


	//BEGIN TO REMOVE 16/08/2021
	sem_t *semaphoreCreate(const char *__name, int oflag, mode_t mode, unsigned int value);
	sem_t *semaphoreOpen(const char *__name, int oflag);
	int semaphoreClose(sem_t *__sem);
	int semaphoreUnlink(const char *__name);
	int sharedMemoryOpen(const char *name, int oflag, mode_t mode);
	int sharedMemoryUnlink(const char *name);
	//END TO REMOVE 16/08/2021

	int semaphoreInitialize(SEMAPHORE_DEF *semdef);
	int semaphoreDestroy(SEMAPHORE_DEF *semdef);
	int sharedMemoryInitialize(SHAREDMEMORY_DEF *shmdef);
	int sharedMemoryDestroy(SHAREDMEMORY_DEF *shmdef);
	int semUnlink(const char *name);
	int shmUnlink(const char *name);

#endif
#if defined OS_MAC
	int getConsoleUserId();
#endif
}

#endif /* MAIN_H_ */

