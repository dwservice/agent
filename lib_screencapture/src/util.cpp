/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/

#include "util.h"
#include <stdlib.h>



int CURSOR_TYPE_ARROW_18_18=0;

CURSOR_TYPE cursors[1];
bool binitcursor=false;


char* cursor_data_arrow_18_18 = (char*)
"ww                "
"wbw               "
"wbbw              "
"wbbbw             "
"wbbbbw            "
"wbbbbbw           "
"wbbbbbbw          "
"wbbbbbbbw         "
"wbbbbbbbbw        "
"wbbbbbwwww        "
"wbbwbbw           "
"wbw wbbw          "
"ww  wbbw          "
"     wbbw         "
"     wbbw         "
"      ww          "
"                  "
"                  ";

int countSetBits(unsigned int num) {
	unsigned int count = 0;
	while (num) {
		count += num & 1;
		num >>= 1;
	}
	return count;
}

void getRGB(CAPTURE_IMAGE &capimage, unsigned long &i, CAPTURE_RGB &rgb){
	if (capimage.bpp>24){
		rgb.red = capimage.data[i+2];
		rgb.green = capimage.data[i+1];
		rgb.blue = capimage.data[i];
	}else if (capimage.bpp>16){
		rgb.red = capimage.data[i+2];
		rgb.green = capimage.data[i+1];
		rgb.blue = capimage.data[i];
	}else if (capimage.bpp>8){
		unsigned int pixel=(capimage.data[i+1] << 8) | (capimage.data[i]);
		rgb.red = (pixel & capimage.redmask) >> capimage.redlshift;
		rgb.green = (pixel & capimage.greenmask) >> capimage.greenlshift;
		rgb.blue = (pixel & capimage.bluemask) << capimage.bluershift;
	}else{
		unsigned int pixel=(capimage.data[i]);
		rgb.red = (pixel & capimage.redmask) >> capimage.redlshift;
		rgb.green = (pixel & capimage.greenmask) >> capimage.greenlshift;
		rgb.blue = (pixel & capimage.bluemask) << capimage.bluershift;
	}
}

short getPaletteColorIndexfromRGB(CAPTURE_RGB &rgb, PALETTE& palinfo) {
	return (short)(((rgb.red >> palinfo.redsf) << (palinfo.greencnt + palinfo.bluecnt)) + ((rgb.green >> palinfo.greensf) << palinfo.bluecnt) + (rgb.blue >> palinfo.bluesf));
}

void initCursor(){
	if (!binitcursor){
		binitcursor=true;
		cursors[0].w=18;
		cursors[0].h=18;
		cursors[0].offx=0;
		cursors[0].offy=0;
		cursors[0].data=cursor_data_arrow_18_18;
	}
}

void getCursorImage(int tp,int* w,int* h,int* offx,int* offy,unsigned char** rgbdata){
	initCursor();
	*w=cursors[tp].w;
	*h=cursors[tp].h;
	*offx=0;
	*offy=0;
	int i=0;
	int sz=(cursors[tp].w * cursors[tp].h);
	unsigned char* cursorData = (unsigned char*)malloc(sz * 4);
	char* dt = cursors[0].data;
	for (int p=0;p<sz;p++){
		char c = dt[p];
		if (c=='w'){
			cursorData[i]=255;
			cursorData[i+1]=255;
			cursorData[i+2]=255;
			cursorData[i+3]=255;
		}else if (c=='b'){
			cursorData[i]=0;
			cursorData[i+1]=0;
			cursorData[i+2]=0;
			cursorData[i+3]=255;
		}else{
			cursorData[i]=0;
			cursorData[i+1]=0;
			cursorData[i+2]=0;
			cursorData[i+3]=0;
		}
		i+=4;
	}
	*rgbdata = cursorData;
}

DistanceFrameMsCalculator::DistanceFrameMsCalculator(){
	//fastCounter.reset();
	distanceFrameMsCounter.reset();
	distanceFrameMs=10;
}

DistanceFrameMsCalculator::~DistanceFrameMsCalculator() {

}

int DistanceFrameMsCalculator::calculate(float fcpu){
	//int dFMs = 0;
	if (distanceFrameMsCounter.getCounter()>=1000){
		distanceFrameMsCounter.reset();
		float max=CPU_MAX;
		/*if (fastCounter.getCounter()<=1000) {
			max=CPU_MAX_FAST;
		}*/
		if (fcpu<0){
			distanceFrameMs=500;
		}else if (fcpu>max){
			if (distanceFrameMs<500){
				distanceFrameMs+=10;
			}
		}else if (distanceFrameMs>10){
			distanceFrameMs-=10;
		}
		//dFMs=distanceFrameMs;
	//}else{
		//dFMs=distanceFrameMs;
	}
	return distanceFrameMs;
}

void DistanceFrameMsCalculator::fast(){
	//fastCounter.reset();
}
