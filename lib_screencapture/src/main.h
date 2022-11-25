/* 
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
 */
#if defined OS_MAIN

#ifndef MAIN_H_
#define MAIN_H_

#define TJPEG_SPLIT_SIZE 1*1024*1024
#define RESULT_DIFF_SIZE 56*1024


typedef void (*CallbackEncodeResult)(unsigned int, unsigned char*);

#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <map>
#include <vector>
#include <iostream>
#include <string>
#include "common/timecounter.h"
#include "common/util.h"
#include "zutil.h"
#include "turbojpeg.h"

#if defined OS_WINDOWS
#include <Userenv.h>
#include "windows/windowsloadlib.h"
#endif


struct TJPEGEncoderSessionInfo{
	int resultBufferSize;
	unsigned char* resultBuffer;
	tjhandle tjInstance;
	unsigned char* jpegBuf;
	long jpegBufSize;
	unsigned char* data;
	int width;
	int height;
};

struct PaletteEncoderSessionInfo{
	int resultBufferSize;
	unsigned char* resultBuffer;
	unsigned char* data;
	int width;
	int height;
	PALETTE palette;
};

unsigned char* resultBufferCursor=(unsigned char*)malloc(RESULT_DIFF_SIZE*sizeof(unsigned char));
int resultBufferCursorSize=RESULT_DIFF_SIZE;

extern "C" {

int DWAScreenCaptureVersion();

//PALETTE
int DWAScreenCapturePaletteEncoderVersion();
int DWAScreenCapturePaletteEncoderInit(int ver, void** encses);
void DWAScreenCapturePaletteEncoderTerm(int ver, void* encses);
unsigned long DWAScreenCapturePaletteEncode(int ver, void* encses, int redsize, int greensize, int bluesize, RGB_IMAGE* rgbimage, CallbackEncodeResult cbresult);

//TURBOJPEG
int DWAScreenCaptureTJPEGEncoderVersion();
int DWAScreenCaptureTJPEGEncoderInit(int ver, void** encses);
void DWAScreenCaptureTJPEGEncoderTerm(int ver, void* encses);
unsigned long DWAScreenCaptureTJPEGEncode(int ver, void* encses, int jpegQuality, int bufferSendSize, RGB_IMAGE* rgbimage, CallbackEncodeResult cbresult);

//void DWAScreenCaptureRGBImageFree(RGB_IMAGE* rgbimage);


unsigned long DWAScreenCaptureCursorEncode(int ver, CURSOR_IMAGE* curimage, CallbackEncodeResult cbresult);

#if defined OS_WINDOWS
int DWAScreenCaptureSAS();
#endif

}

#endif /* MAIN_H_ */

#endif
