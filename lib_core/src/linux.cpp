/*
 This Source Code Form is subject to the terms of the Mozilla
 Public License, v. 2.0. If a copy of the MPL was not distributed
 with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
 */
#if defined OS_LINUX

#include "main.h"


//TO REMOVE 16/08/2021
sem_t *semaphoreCreate(const char *__name, int oflag, mode_t mode, unsigned int value) {
	return sem_open(__name, oflag, mode, value);
}

//TO REMOVE 16/08/2021
sem_t *semaphoreOpen(const char *__name, int oflag) {
	return sem_open(__name, oflag);
}

//TO REMOVE 16/08/2021
int semaphoreClose(sem_t *__sem) {
	return sem_close(__sem);
}

//TO REMOVE 16/08/2021
int semaphoreUnlink(const char *__name) {
	return sem_unlink(__name);
}

//TO REMOVE 16/08/2021
int sharedMemoryOpen(const char *name, int oflag, mode_t mode) {
	return shm_open(name, oflag, mode);
}

//TO REMOVE 16/08/2021
int sharedMemoryUnlink(const char *name) {
	return shm_unlink(name);
}


int semaphoreInitialize(SEMAPHORE_DEF *semdef) {
	if (semdef->create==1){
		semdef->fd = shm_open(semdef->name, O_CREAT | O_EXCL | O_RDWR, S_IRUSR | S_IWUSR);
		if (semdef->fd == -1) {
			semdef->name=NULL;
			semdef->fd=-1;
			semdef->sem=NULL;
			return -1;
		}
		if (ftruncate(semdef->fd, sizeof(sem_t*)) == -1) {
			close(semdef->fd);
			semdef->name=NULL;
			semdef->fd=-1;
			semdef->sem=NULL;
			return -2;
		}
		if (semdef->mode!=-1){
			fchmod(semdef->fd,semdef->mode);
		}
		semdef->sem = (sem_t*)mmap(NULL, sizeof(sem_t*), PROT_READ | PROT_WRITE, MAP_SHARED, semdef->fd, 0);
		if (semdef->sem==MAP_FAILED){
			close(semdef->fd);
			shm_unlink(semdef->name);
			semdef->name=NULL;
			semdef->fd=-1;
			semdef->sem=NULL;
			return -3;
		}
		if (sem_init(semdef->sem, 1, semdef->semvalue) == -1){
			close(semdef->fd);
			shm_unlink(semdef->name);
			semdef->name=NULL;
			semdef->fd=-1;
			semdef->sem=NULL;
			return -4;
		}
	}else{
		semdef->fd = shm_open(semdef->name, O_RDWR, 0);
		if (semdef->fd == -1) {
			semdef->name=NULL;
			semdef->fd=-1;
			semdef->sem=NULL;
			return -1;
		}
		semdef->sem = (sem_t*)mmap(NULL, sizeof(sem_t*), PROT_READ | PROT_WRITE, MAP_SHARED, semdef->fd, 0);
		if (semdef->sem==MAP_FAILED){
			close(semdef->fd);
			semdef->name=NULL;
			semdef->fd=-1;
			semdef->sem=NULL;
			return -3;
		}
	}
	return 0;
}

int semaphoreDestroy(SEMAPHORE_DEF *semdef) {
	int iret=0;
	if (semdef->create==1){
		if (semdef->sem!=NULL){
			iret-=sem_destroy(semdef->sem);
		}
		if (semdef->fd!=-1){
			iret-=close(semdef->fd);
		}
		if (semdef->name!=NULL){
			iret-=shm_unlink(semdef->name);
		}
	}else{
		if (semdef->fd!=-1){
			iret-=close(semdef->fd);
		}
	}
	semdef->name=NULL;
	semdef->fd=-1;
	semdef->sem=NULL;
	return iret;
}

int sharedMemoryInitialize(SHAREDMEMORY_DEF *shmdef) {
	int iret=0;
	if (shmdef->create==1){
		shmdef->fd = shm_open(shmdef->name, O_CREAT | O_EXCL | O_RDWR, S_IRUSR | S_IWUSR);
		if (shmdef->fd == -1) {
			return -1;
		}
		if (ftruncate(shmdef->fd, shmdef->size) == -1) {
			close(shmdef->fd);
			return -2;
		}
		if (shmdef->mode!=-1){
			fchmod(shmdef->fd,shmdef->mode);
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
	return shm_unlink(name);
}

int shmUnlink(const char *name) {
	return shm_unlink(name);
}


#endif
