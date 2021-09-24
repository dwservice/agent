/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/

#ifndef DWDEBBUGGER_H_
#define DWDEBBUGGER_H_

#include <stdio.h>
#include <stdarg.h>

typedef void (*CallbackType)(wchar_t*);

extern "C" {
	void DWAScreenCaptureSetCallbackDebug(CallbackType callback);
}

void DWDebuggerPrint(const wchar_t *format, ...);


#endif /* DWDEBBUGGER_H_ */


