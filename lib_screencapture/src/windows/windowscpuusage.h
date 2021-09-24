/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/
#if defined OS_WINDOWS

#include "../common/timecounter.h"
#include <windows.h>

#ifndef WINDOWSCPUUSAGE_H_
#define WINDOWSCPUUSAGE_H_

class WindowsCPUUsage{

public:
	WindowsCPUUsage(void );
    ~WindowsCPUUsage( void );
    float getValue();

private:
    FILETIME prevSysKernel;
    FILETIME prevSysUser;
    FILETIME prevProcKernel;
    FILETIME prevProcUser;
    float lastCpu=-1;
    TimeCounter cpuCounter;

    ULONGLONG subtractTime(const FILETIME &a, const FILETIME &b);
};

#endif /* WINDOWSCPUUSAGE_H_ */

#endif
