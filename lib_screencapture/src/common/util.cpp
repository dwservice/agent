/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/

#include "util.h"
#include <stdlib.h>

#include <string>
#include <vector>

#if defined OS_WINDOWS
#include <windows.h>
#else
#include <fstream>
#endif

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
	int count=0;
	while(num!=0){
		if((num&1)!=0){
			count++;
		}
		num=num>>1;
	}
	return count;
}

int intToArray(unsigned char* buffer,int p,int i){
	buffer[p] = (i >> 24) & 0xFF;
	buffer[p+1] = (i >> 16) & 0xFF;
	buffer[p+2] = (i >> 8) & 0xFF;
	buffer[p+3] = i & 0xFF;
	return 4;
}

int byteArrayToInt(unsigned char* buffer,int p) {
    return ((buffer[p] << 24) + ((buffer[p+1] & 0xFF) << 16) + ((buffer[p+2] & 0xFF) << 8) + ((buffer[p+3] & 0xFF) << 0));
}

int shortToArray(unsigned char* buffer,int p,short s){
	buffer[p] = (s >> 8) & 0xFF;
	buffer[p+1] = s & 0xFF;
	return 2;
}

short byteArrayToShort(unsigned char* buffer,int p) {
    return (short) ((buffer[p] << 8) + (buffer[p+1] << 0));
}

void initCursors(){
	if (!binitcursor){
		binitcursor=true;
		cursors[0].w=18;
		cursors[0].h=18;
		cursors[0].offx=0;
		cursors[0].offy=0;
		cursors[0].data=cursor_data_arrow_18_18;
	}
}

void setCursorImage(int tp,CURSOR_IMAGE* curimage){
	initCursors();
	curimage->width=cursors[tp].w;
	curimage->height=cursors[tp].h;
	curimage->offx=0;
	curimage->offy=0;
	curimage->sizedata=curimage->width*curimage->height*4;
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
	curimage->data = cursorData;
}



