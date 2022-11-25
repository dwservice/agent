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
#include "common/logger.h"

#define RESULT_DIFF_SIZE 56*1024

typedef void (*CallbackRecord)(unsigned int, unsigned char*);
typedef void (*CallbackEncodeResult)(unsigned int, unsigned char*);

typedef struct{
	unsigned int sampleRate;
	unsigned int numChannels;
	unsigned int bufferFrames;
} AUDIO_CONFIG;

unsigned int deviceCount = 0;
unsigned int deviceOut = 0;

struct AudioCaptureSessionInfo{
	rtaudio_t adc;
	bool bStreamAlive;
	AUDIO_CONFIG* conf;
	CallbackRecord callbackRecord;
};

struct OPUSEncoderSessionInfo{
	int resultBufferSize;
	unsigned char* resultBuffer;
	OpusEncoder* enc;
	AUDIO_CONFIG* conf;
};

extern "C" {
	int DWASoundCaptureVersion();
	int DWASoundCaptureStart(AUDIO_CONFIG* audioconf,CallbackRecord cbrec,void** capses);
	void DWASoundCaptureStop(void* capses);
	int DWASoundCaptureGetDetectOutputName(void* capses,char* bf, int sz);
	int DWASoundCaptureOPUSEncoderInit(AUDIO_CONFIG* audioconf,void** encses);
	void DWASoundCaptureOPUSEncoderTerm(void* encses);
	int DWASoundCaptureOPUSEncode(void* encses, unsigned char* rawinput, int sizeinput, CallbackEncodeResult cbresult);
}


#endif /* MAIN_H_ */

