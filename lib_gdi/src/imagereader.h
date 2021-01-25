/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/

#ifndef IMAGEREADER_H_
#define IMAGEREADER_H_

#include <fstream>
#include <vector>
#include <iostream>

class ImageReader{
public:
	ImageReader();
	void load(const wchar_t* iconPath);
	int getWidth();
	int getHeight();
	void getPixel(unsigned int x, unsigned int y, unsigned char *r, unsigned char *g, unsigned char *b, unsigned char *a);
	bool isLoaded();
	void destroy();

private:
	void readBMP(const wchar_t* iconPath);
	std::vector<unsigned char> data;
	int width;
	int height;
	int bits;
	bool bloaded;
};

#endif /* IMAGEREADER_H_ */
