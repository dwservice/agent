/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/

#ifndef UTIL_H_
#define UTIL_H_

#include "timecounter.h"

typedef struct {
	unsigned char red;
	unsigned char green;
	unsigned char blue;
} CAPTURE_RGB;

typedef struct {
	int width;
	int height;
	unsigned char* data;
	int bpp;
	int bpc;
	int redmask;
	int greenmask;
	int bluemask;
	int redlshift;
	int greenlshift;
	int bluershift;
} CAPTURE_IMAGE;

typedef struct {
	int x;
	int y;
	int width;
	int height;
} CAPTURE_CHANGE_AREA;

typedef struct {
	int x;
	int y;
	int width;
	int height;
	int xdest;
	int ydest;
} CAPTURE_MOVE_AREA;

typedef struct{
	int redsize;
	int greensize;
	int bluesize;
	int redsf;
	int greensf;
	int bluesf;
	int redcnt;
	int greencnt;
	int bluecnt;
} PALETTE;

typedef struct{
	int w;
	int h;
	int offx;
	int offy;
	char* data;
} CURSOR_TYPE;


int countSetBits(unsigned int num);
short getPaletteColorIndexfromRGB(CAPTURE_RGB &rgb, PALETTE& palinfo);
void getRGB(CAPTURE_IMAGE &capimage, unsigned long &i, CAPTURE_RGB &rgb);
void getCursorImage(int tp,int* w,int* h,int* offx,int* offy,unsigned char** rgbdata);
extern int CURSOR_TYPE_ARROW_18_18;

class DistanceFrameMsCalculator{

public:
	DistanceFrameMsCalculator();
	~DistanceFrameMsCalculator(void);

	int calculate(float fcpu);
	void fast();

private:
	#define CPU_MAX 5.0
	#define CPU_MAX_FAST 25.0

	TimeCounter fastCounter; //Mi serve per attivate la cattura veloce se c'e' stato un input (esempio dopo un input catturo per 1 secondo in modalita' veloce)
	TimeCounter distanceFrameMsCounter;
	int distanceFrameMs;
	int distanceFrameMsFast;
};


#endif /* UTIL_H_ */

