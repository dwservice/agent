/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/
#ifndef MAIN_H_
#define MAIN_H_

#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <cstring>
#include <map>
#include "rtaudio_c.h"
#include "opus.h"

#if defined OS_WINDOWS
#include <windows.h>
#else
#include <pthread.h>
#endif


typedef struct{
	OpusEncoder *enc;
	int bufferSize;
	unsigned char* buffer;
	int ringBufferPos;
	int enctype;
	int quality;

} SESSION;

#if defined OS_WINDOWS
HANDLE mtx;
#else
pthread_mutex_t mtx;
#endif

bool bStarted=false;
bool bStreamAlive=false;
bool bStreamFirst=true;
unsigned int sampleRate = 48000;
unsigned int numChannels = 2;
unsigned int bufferFrames = 0;
unsigned int deviceCount = 0;
unsigned int deviceOut = 0;

rtaudio_t adc;
int ringBufferSize=0;
int ringBufferLimit=0;
float* ringBuffer;
float* ringBufferApp;
std::map<int,SESSION> hmSession;

void DWASoundCaptureLock();
void DWASoundCaptureUnlock();
void DWASoundCaptureCreateLock();
void DWASoundCaptureDestroyLock();
void DWASoundCaptureTermNoSync(int id);
void DWASoundCaptureDestroyStream();

extern "C" {
	int DWASoundCaptureVersion();
	unsigned int DWASoundCaptureGetSampleRate();
	unsigned int DWASoundCaptureGetNumChannels();
	unsigned int DWASoundCaptureGetBufferFrames();
	int DWASoundCaptureGetDetectOutputName(char* bf, int sz);
	void DWASoundCaptureStart();
	void DWASoundCaptureDetectOutput();
	void DWASoundCaptureStop();
	int DWASoundCaptureInit(int id, int enctype, int quality);
	int DWASoundCaptureGetData(int id, unsigned char** data);
	void DWASoundCaptureTerm(int id);
}


#endif /* MAIN_H_ */

