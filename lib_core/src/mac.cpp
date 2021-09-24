/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/

#if defined OS_MAC
#include "main.h"


//TO REMOVE 16/08/2021
sem_t *semaphoreCreate(const char *__name, int oflag, mode_t mode, unsigned int value){
    return sem_open(__name, oflag, mode, value);
}

//TO REMOVE 16/08/2021
sem_t *semaphoreOpen(const char *__name, int oflag){
    return sem_open(__name, oflag);
}

//TO REMOVE 16/08/2021
int semaphoreClose(sem_t *__sem){
	return sem_close(__sem);
}

//TO REMOVE 16/08/2021
int semaphoreUnlink (const char *__name){
	return sem_unlink(__name);
}

//TO REMOVE 16/08/2021
int sharedMemoryOpen(const char *name, int oflag, mode_t mode){
	return shm_open(name,oflag,mode);
}

//TO REMOVE 16/08/2021
int sharedMemoryUnlink(const char *name){
	return shm_unlink(name);
}


int semaphoreInitialize(SEMAPHORE_DEF *semdef) {
	if (semdef->create==1){
		int imd=S_IRUSR | S_IWUSR;
		if (semdef->mode!=-1){
			imd=semdef->mode;
		}
		semdef->sem=sem_open(semdef->name,  O_CREAT | O_EXCL, imd, semdef->semvalue);
		if (semdef->sem ==  SEM_FAILED){
			sem_unlink(semdef->name);
			semdef->name=NULL;
			semdef->sem=NULL;
			return -1;
		}
	}else{
		semdef->sem=sem_open(semdef->name,  0);
		if (semdef->sem==MAP_FAILED){
			semdef->name=NULL;
			semdef->sem=NULL;
			return -1;
		}
	}
	return 0;
}

int semaphoreDestroy(SEMAPHORE_DEF *semdef) {
	int iret=0;
	if (semdef->create==1){
		if (semdef->sem!=NULL){
			iret-=sem_close(semdef->sem);
		}
		if (semdef->name!=NULL){
			iret-=sem_unlink(semdef->name);
		}
	}else{
		if (semdef->sem!=NULL){
			iret-=sem_close(semdef->sem);
		}
	}
	semdef->name=NULL;
	semdef->sem=NULL;
	return iret;
}

int sharedMemoryInitialize(SHAREDMEMORY_DEF *shmdef) {
	int iret=0;
	struct stat st;
	if (shmdef->create==1){
		int imd=S_IRUSR | S_IWUSR;
		if (shmdef->mode!=-1){
			imd=shmdef->mode;
		}
		shmdef->fd = shm_open(shmdef->name, O_CREAT | O_EXCL | O_RDWR, imd);
		if (shmdef->fd == -1) {
			return -1;
		}
		if (ftruncate(shmdef->fd, shmdef->size) == -1) {
			close(shmdef->fd);
			return -2;
		}
	}else{
		shmdef->fd = shm_open(shmdef->name, O_RDWR, 0);
		if (shmdef->fd == -1) {
			return -1;
		}
	}
	return iret;
}

int sharedMemoryDestroy(SHAREDMEMORY_DEF *shmdef) {
	int iret=0;
	if (shmdef->create==1){
		if (shmdef->fd!=-1){
			iret-=close(shmdef->fd);
			iret-=shm_unlink(shmdef->name);
		}
	}else{
		if (shmdef->fd!=-1){
			iret-=close(shmdef->fd);
		}
	}
	shmdef->name=NULL;
	shmdef->fd=-1;
	shmdef->size=0;
	return iret;
}

int semUnlink(const char *name) {
	return sem_unlink(name);
}

int shmUnlink(const char *name) {
	return shm_unlink(name);
}


int getConsoleUserId(){
	uid_t uid=0;
	SCDynamicStoreRef store = SCDynamicStoreCreate(NULL, CFSTR("GetConsoleUser"), NULL, NULL);
	if(store != NULL){
		SCDynamicStoreCopyConsoleUser(store, &uid, NULL);
		CFRelease(store);
	}
	return uid;
}

#endif
