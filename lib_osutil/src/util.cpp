/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/

#include "util.h"

wstring towstring(const char* chrs) {
	size_t requiredSize = mbstowcs(NULL, chrs, 0);
    wchar_t* dest = (wchar_t *)malloc( (requiredSize + 1) * sizeof( wchar_t ));
    mbstowcs(dest, chrs, requiredSize + 1);
	wstring str = wstring(dest);
	free(dest);
	return str;
}

wchar_t* towcharp(wstring str) {
	wchar_t*  wc = (wchar_t*)malloc((str.size() + 1) * sizeof(wchar_t));
	str.copy(wc,str.size());
	wc[str.size()]='\0';
	return wc;
}

void trim(wstring& str, wchar_t c) {
    string::size_type pos = str.find_last_not_of(c);
    if (pos != string::npos) {
        str.erase(pos + 1);
        pos = str.find_first_not_of(c);
        if (pos != string::npos) str.erase(0, pos);
    } else str.erase(str.begin(), str.end());
}

void trimAll(wstring& str) {
    trim(str, ' ');
    trim(str, '\r');
    trim(str, '\n');
    trim(str, '\t');
}
