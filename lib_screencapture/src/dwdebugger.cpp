/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/

#include "dwdebugger.h"


DWDebugger::DWDebugger(){
	g_callback_debug=NULL;
	btest=false;
}

void DWDebugger::setCallback(CallbackType callback){
	g_callback_debug=callback;
}

void DWDebugger::setTest(){
	btest=true;
}

void DWDebugger::print(const char *format, ...){
	if ((!btest) && (g_callback_debug!=NULL)){
		char buffer[4096];
		va_list arg;
		va_start(arg, format);
		vsprintf(buffer,format, arg);
		va_end(arg);
		g_callback_debug(buffer);
	}
}

