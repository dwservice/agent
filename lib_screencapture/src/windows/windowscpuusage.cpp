/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/

#if defined OS_WINDOWS

#include "windowscpuusage.h"


WindowsCPUUsage::WindowsCPUUsage(){
	cpuCounter.reset();
}

WindowsCPUUsage::~WindowsCPUUsage(){

}

ULONGLONG WindowsCPUUsage::subtractTime(const FILETIME &a, const FILETIME &b){
    LARGE_INTEGER la, lb;
    la.LowPart = a.dwLowDateTime;
    la.HighPart = a.dwHighDateTime;
    lb.LowPart = b.dwLowDateTime;
    lb.HighPart = b.dwHighDateTime;

    return la.QuadPart - lb.QuadPart;
}

float WindowsCPUUsage::getValue(){
	FILETIME sysIdle, sysKernel, sysUser;
	FILETIME procCreation, procExit, procKernel, procUser;

	if (!GetSystemTimes(&sysIdle, &sysKernel, &sysUser) ||
		!GetProcessTimes(GetCurrentProcess(), &procCreation, &procExit, &procKernel, &procUser)) {
		return -1;
	}

	if ((lastCpu>=0) && (cpuCounter.getCounter()<1000)){
		return lastCpu;
	}

	if (lastCpu>=0){
		ULONGLONG sysKernelDiff = subtractTime(sysKernel, prevSysKernel);
		ULONGLONG sysUserDiff = subtractTime(sysUser, prevSysUser);

		ULONGLONG procKernelDiff = subtractTime(procKernel, prevProcKernel);
		ULONGLONG procUserDiff = subtractTime(procUser, prevProcUser);

		ULONGLONG sysTotal = sysKernelDiff + sysUserDiff;
		ULONGLONG procTotal = procKernelDiff + procUserDiff;
		lastCpu=(float)((100.0 * procTotal)/sysTotal);
	}else{
		lastCpu=0;
	}

	prevSysKernel.dwLowDateTime = sysKernel.dwLowDateTime;
	prevSysKernel.dwHighDateTime = sysKernel.dwHighDateTime;

	prevSysUser.dwLowDateTime = sysUser.dwLowDateTime;
	prevSysUser.dwHighDateTime = sysUser.dwHighDateTime;

	prevProcKernel.dwLowDateTime = procKernel.dwLowDateTime;
	prevProcKernel.dwHighDateTime = procKernel.dwHighDateTime;

	prevProcUser.dwLowDateTime = procUser.dwLowDateTime;
	prevProcUser.dwHighDateTime = procUser.dwHighDateTime;
	cpuCounter.reset();

	//printf("CPU: %f\n",lastCpu);

	return lastCpu;
}

#endif
