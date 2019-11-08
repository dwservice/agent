/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/

#include "main.h"
#if defined OS_MAC
#else
void callbackTypeRepaintTest(int id, int x,int y,int w, int h){
	penColor(id,0,0,0);
	drawText(id, (wchar_t*)L"Test", 100, 50);
}

#if defined OS_WINDOWS
int wmain(int argc, wchar_t **argv) {
#else
	int main(int argc, char **argv) {
#endif

	int id = newWindow(WINDOW_TYPE_NORMAL_NOT_RESIZABLE,0,0,400,300, (wchar_t*)L"");

	setTitle(id,(wchar_t*)L"Test");
	setCallbackRepaint(*callbackTypeRepaintTest);
	//createNotifyIcon(id,L"",L"Tooltip");
	show(id,0);
	loop();
	return 1;
}
#endif
