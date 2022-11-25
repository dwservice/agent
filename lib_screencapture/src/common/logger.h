/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/

#ifndef LOGGER_H_
#define LOGGER_H_

#include <stdio.h>
#include <stdarg.h>
#if defined OS_WINDOWS
#else
#include <wchar.h>
#endif


typedef void (*CallbackType)(int, wchar_t*);

extern "C" {
	void DWALoggerSetCallback(CallbackType callback);
}

void DWALoggerWriteInfo(const wchar_t *format, ...);
void DWALoggerWriteErr(const wchar_t *format, ...);
void DWALoggerWriteDebug(const wchar_t *format, ...);


#endif /* LOGGER_H_ */


