/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/

#include "main.h"

#if defined OS_LINUX

sem_t *semaphoreCreate(const char *__name, unsigned int value){
    return sem_open(__name, O_CREAT | O_EXCL, 0664, value);
}

sem_t *semaphoreOpen(const char *__name){
    return sem_open(__name, 0);
}

int semaphoreClose(sem_t *__sem){
	return sem_close(__sem);
}

int semaphoreUnlink (const char *__name){
	return sem_unlink(__name);
}

#endif
