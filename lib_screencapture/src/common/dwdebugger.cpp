/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/

#include "dwdebugger.h"

CallbackType g_callback_debug=NULL;

void DWAScreenCaptureSetCallbackDebug(CallbackType callback){
	g_callback_debug=callback;
}

void DWDebuggerPrint(const wchar_t *format, ...){
	if (g_callback_debug!=NULL){
		/*wchar_t buffer[4096];
		va_list arg;
		va_start(arg, format);
		vswprintf(buffer,format, arg);
		va_end(arg);
		g_callback_debug(buffer);*/
	}
}

