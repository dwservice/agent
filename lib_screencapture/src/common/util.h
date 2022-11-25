/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/

#ifndef UTIL_H_
#define UTIL_H_

#include "timecounter.h"

const int RGB_IMAGE_DIFFSIZE=1000;
const int MONITORS_INFO_ITEM_MAX=1000;

typedef struct{
	int index;
	int x;
	int y;
	int width;
	int height;
	int changed;
	void* internal;
} MONITORS_INFO_ITEM;

typedef struct{
	int count;
	int changed;
	MONITORS_INFO_ITEM monitor[MONITORS_INFO_ITEM_MAX];
} MONITORS_INFO;


typedef struct{
	int x1;
	int y1;
	int x2;
	int y2;
} DIFF_RECT;

typedef struct {
	int x;
	int y;
	int width;
	int height;
} RGB_IMAGE_CHANGE_AREA;

typedef struct {
	int x;
	int y;
	int width;
	int height;
	int xdest;
	int ydest;
} RGB_IMAGE_MOVE_AREA;

typedef struct {
	int width;
	int height;
	long sizedata;
	unsigned char* data;
	int sizechangearea;
	RGB_IMAGE_CHANGE_AREA changearea[RGB_IMAGE_DIFFSIZE];
	int sizemovearea;
	RGB_IMAGE_MOVE_AREA movearea[RGB_IMAGE_DIFFSIZE];

} RGB_IMAGE;

typedef struct{
	int visible;
	int x;
	int y;
	int offx;
	int offy;
	int width;
	int height;
	int changed;
	long sizedata;
	unsigned char* data; //RGBA
	void* internal;
} CURSOR_IMAGE;

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

typedef struct {
	int type;
	long sizedata;
	unsigned char* data;
} CLIPBOARD_DATA;

int intToArray(unsigned char* buffer,int p,int i);
int byteArrayToInt(unsigned char* buffer,int p);
int shortToArray(unsigned char* buffer,int p,short s);
short byteArrayToShort(unsigned char* buffer,int p);

int countSetBits(unsigned int num);
void setCursorImage(int tp,CURSOR_IMAGE* curimage);
extern int CURSOR_TYPE_ARROW_18_18;


#endif /* UTIL_H_ */

