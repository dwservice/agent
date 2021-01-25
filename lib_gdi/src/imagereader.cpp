/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/

#include "imagereader.h"


ImageReader::ImageReader(){
	bloaded=false;
	width=0;
	height=0;
	bits=0;
}

void ImageReader::destroy() {
	bloaded=false;
	width=0;
	height=0;
	bits=0;
}

void ImageReader::load(const wchar_t* iconPath){
	readBMP(iconPath);
}

bool ImageReader::isLoaded(){
	return bloaded;
}

int ImageReader::getWidth(){
	return width;
}

int ImageReader::getHeight(){
	return height;
}

void ImageReader::getPixel(unsigned int x, unsigned int y, unsigned char *r, unsigned char *g, unsigned char *b, unsigned char *a){
	if (bloaded && x<(unsigned int)width && y<(unsigned int)height){
		y=(height-1)-y;
		unsigned int chl = bits/8;
		*b = data[chl*(y*width+x)+0];
		*g = data[chl*(y*width+x)+1];
		*r = data[chl*(y*width+x)+2];
		if (chl==4){
			*a = data[chl*(y*width+x)+3];
		}else{
			*a = 255;
		}
	}
}

void ImageReader::readBMP(const wchar_t* iconPath) {
	int sz=wcstombs(NULL,iconPath,0);
	char fname[sz];
	wcstombs(fname,iconPath,sz*sizeof(wchar_t));
	std::ifstream inp(fname, std::ios_base::binary);
	if (inp) {
		int posType=0;
		int posOffset=posType+2+4+2+2;
		int posWidthHeight=posOffset+4+4;
		int posBits=posWidthHeight+4+4+2;

		//READ TYPE
		unsigned short type;
		inp.read((char*)&type, 2);
		if(type == 0x4D42) {
			//READ OFFSET
			unsigned int offset;
			inp.seekg(posOffset, inp.beg);
			inp.read((char*)&offset, 4);

			//READ width/weight
			inp.seekg(posWidthHeight, inp.beg);
			inp.read((char*)&width, 4);
			inp.read((char*)&height, 4);

			//READ bits
			inp.seekg(posBits, inp.beg);
			inp.read((char*)&bits, 2);

			if ((width>0) && (height>0)){
				data.resize(width * height * bits / 8);
				inp.seekg(offset, inp.beg);
				if (width % 4 == 0) {
					inp.read((char*)data.data(), data.size());
				}else{
					unsigned int sizerow = width * (bits / 8);
					unsigned int sizeapp = sizerow;
					while (sizeapp % 4 != 0) {
						sizeapp++;
					}
					int skiprow = sizeapp-sizerow;
					for (int y = 0; y < height; ++y) {
						inp.read((char*)(data.data() + sizerow * y), sizerow);
						if (skiprow>0){
							inp.seekg(skiprow, inp.cur);
						}
					}
				}
				bloaded=true;
			}
		}
		inp.close();
	}
}
