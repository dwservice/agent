/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/

#include "logger.h"

CallbackType dwalogger_callback=NULL;

void DWALoggerSetCallback(CallbackType callback){
	dwalogger_callback=callback;
}

void DWALoggerWrite(int lev, const wchar_t *format, ...){
	if (dwalogger_callback!=NULL){
		wchar_t buffer[4096];
		va_list arg;
		va_start(arg, format);
#if defined OS_WINDOWS
		vswprintf(buffer,format, arg);
#else
		vswprintf(buffer,4096,format, arg);
#endif
		va_end(arg);
		dwalogger_callback(lev, buffer);
	}
}

void DWALoggerWriteInfo(const wchar_t *format, ...){
	if (dwalogger_callback!=NULL){
		wchar_t buffer[4096];
		va_list arg;
		va_start(arg, format);
#if defined OS_WINDOWS
		vswprintf(buffer,format, arg);
#else
		vswprintf(buffer,4096,format, arg);
#endif
		va_end(arg);
		dwalogger_callback(0, buffer);
	}
}

void DWALoggerWriteErr(const wchar_t *format, ...){
	if (dwalogger_callback!=NULL){
		wchar_t buffer[4096];
		va_list arg;
		va_start(arg, format);
#if defined OS_WINDOWS
		vswprintf(buffer,format, arg);
#else
		vswprintf(buffer,4096,format, arg);
#endif
		va_end(arg);
		dwalogger_callback(1, buffer);
	}
}

void DWALoggerWriteDebug(const wchar_t *format, ...){
	if (dwalogger_callback!=NULL){
		wchar_t buffer[4096];
		va_list arg;
		va_start(arg, format);
#if defined OS_WINDOWS
		vswprintf(buffer,format, arg);
#else
		vswprintf(buffer,4096,format, arg);
#endif
		va_end(arg);
		dwalogger_callback(9, buffer);
	}
}

