/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/

#include "main.h"

#if defined OS_MAC
#include <sys/mman.h>

sem_t *semaphoreCreate(const char *__name, int oflag, mode_t mode, unsigned int value){
    return sem_open(__name, oflag, mode, value);
}

sem_t *semaphoreOpen(const char *__name, int oflag){
    return sem_open(__name, oflag);
}

int semaphoreClose(sem_t *__sem){
	return sem_close(__sem);
}

int semaphoreUnlink (const char *__name){
	return sem_unlink(__name);
}

int sharedMemoryOpen(const char *name, int oflag, mode_t mode){
	return shm_open(name,oflag,mode);
}

int sharedMemoryUnlink(const char *name){
	return shm_unlink(name);
}

#endif
