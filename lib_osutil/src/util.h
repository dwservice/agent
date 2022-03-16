/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/

#ifndef UTIL_H_
#define UTIL_H_

#include <string>

using namespace std;

wstring towstring(const char* chrs);
wchar_t* towcharp(wstring str);
void trim(wstring& str, wchar_t c);
void trimAll(wstring& str);

#endif /* UTIL_H_ */


