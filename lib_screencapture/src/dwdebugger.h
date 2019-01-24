/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/

#ifndef DWDEBBUGGER_H_
#define DWDEBBUGGER_H_

#include <stdio.h>
#include <stdarg.h>

typedef void (*CallbackType)(char*);

class DWDebugger{

public:
	DWDebugger();
	void print(const char *format, ...);
	void setCallback(CallbackType callback);
	void setTest();

private:
	CallbackType g_callback_debug;
	bool btest;
};

#endif /* DWDEBBUGGER_H_ */

