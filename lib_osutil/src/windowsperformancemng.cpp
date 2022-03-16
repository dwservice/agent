
/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/

#if defined OS_WINDOWS

#include "performancemng.h"

PerformanceMng::PerformanceMng(){
	previousTotalTicks = 0;
	previousIdleTicks = 0;
	m_osVerInfo = OSVERSIONINFOEX();
	m_osVerInfo.dwOSVersionInfoSize = sizeof(OSVERSIONINFO);
    if (!GetVersionEx((OSVERSIONINFO*)&m_osVerInfo)) {
		m_osVerInfo.dwOSVersionInfoSize = 0;
	}
}

int PerformanceMng::getInfo(wchar_t** sret){
	JSONWriter jsonw;

	jsonw.beginObject();

	jsonw.addNumber(L"cpuUsagePerc",getCpuUsage());

	MEMORYSTATUSEX statex;
	statex.dwLength = sizeof (statex);
	GlobalMemoryStatusEx (&statex);

	jsonw.addNumber(L"memoryPhysicalTotal", statex.ullTotalPhys);
	jsonw.addNumber(L"memoryPhysicalAvailable", statex.ullAvailPhys);
	jsonw.addNumber(L"memoryVirtualTotal", statex.ullTotalVirtual);
	jsonw.addNumber(L"memoryVirtualAvailable", statex.ullAvailVirtual);
	jsonw.addNumber(L"memoryTotal", statex.ullTotalPhys);
	jsonw.addNumber(L"memoryAvailable", statex.ullAvailPhys);
	/*jsonw.addNumber(L"memoryTotal", statex.ullTotalPageFile);
	jsonw.addNumber(L"memoryAvailable", statex.ullAvailPageFile);*/

	jsonw.endObject();
	wstring str=jsonw.getString();
	*sret=towcharp(str);
	return str.length();
}

float PerformanceMng::calculateCPULoad(unsigned long long idleTicks, unsigned long long totalTicks){
	unsigned long long totalTicksSinceLastTime = totalTicks-previousTotalTicks;
	unsigned long long idleTicksSinceLastTime  = idleTicks-previousIdleTicks;
	float ret = 1.0f-((totalTicksSinceLastTime > 0) ? ((float)idleTicksSinceLastTime)/totalTicksSinceLastTime : 0);
	previousTotalTicks = totalTicks;
	previousIdleTicks  = idleTicks;
	return ret;
}

unsigned long long PerformanceMng::fileTimeToInt64(const FILETIME & ft) {
	return (((unsigned long long)(ft.dwHighDateTime))<<32)|((unsigned long long)ft.dwLowDateTime);
}

int PerformanceMng::getCpuUsage() {
	FILETIME idleTime, kernelTime, userTime;
	float f = GetSystemTimes(&idleTime, &kernelTime, &userTime) ? calculateCPULoad(fileTimeToInt64(idleTime), fileTimeToInt64(kernelTime)+fileTimeToInt64(userTime)) : -1.0f;
	return (int)(f * (float)100);
}

#endif
