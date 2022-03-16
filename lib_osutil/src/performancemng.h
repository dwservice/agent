/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/

#define TOTALBYTES    100*1024
#define BYTEINCREMENT 10*1024
#include "util.h"
#include "jsonwriter.h"

#if defined OS_WINDOWS
#include <windows.h>
#include <tchar.h>
#include <pdh.h>
#include <stdio.h>
#endif

class PerformanceMng{
public:
	PerformanceMng();
	int getInfo(wchar_t** sret);
private:

#if defined OS_WINDOWS
	//bool m_bFirstTime;
	OSVERSIONINFOEX m_osVerInfo;
	unsigned long long previousTotalTicks;
	unsigned long long previousIdleTicks;

	int getCpuUsage();
	float calculateCPULoad(unsigned long long idleTicks, unsigned long long totalTicks);
	unsigned long long fileTimeToInt64(const FILETIME & ft);
#endif

};
