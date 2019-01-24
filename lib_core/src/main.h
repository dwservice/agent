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
#else
#include <iostream>
#include <fcntl.h>
#include <semaphore.h>
#endif

#ifndef MAIN_H_
#define MAIN_H_


extern "C"{
#if defined OS_WINDOWS
	int taskKill(int pid);
	int isTaskRunning(int pid);
	void setFilePermissionEveryone(LPCTSTR FileName);
#else
	sem_t *semaphoreCreate(const char *__name, unsigned int value);
	sem_t *semaphoreOpen(const char *__name);
	int semaphoreClose(sem_t *__sem);
	int semaphoreUnlink(const char *__name);
#endif

}

#endif /* MAIN_H_ */

