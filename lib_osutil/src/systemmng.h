/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/

#define BUFSIZE 256

#include "util.h"
#include "jsonwriter.h"


#if defined OS_WINDOWS
#include <windows.h>
#include <tchar.h>
#include <intrin.h>
#endif

using namespace std;

class SystemMng{
public:
	SystemMng();
	int getInfo(wchar_t** sret);

#if defined OS_WINDOWS
	bool isWinNTFamily();
	bool isWinXP();
	bool isWin2003Server();
	bool isWin2008Server();
	bool isVistaOrLater();
#endif

private:

#if defined OS_WINDOWS
	OSVERSIONINFOEX m_osVerInfo;
	typedef void (WINAPI *PGNSI)(LPSYSTEM_INFO);
	typedef BOOL (WINAPI *PGPI)(DWORD, DWORD, DWORD, DWORD, PDWORD);
	void appendCpuName(JSONWriter* jsonw);
#endif
};
