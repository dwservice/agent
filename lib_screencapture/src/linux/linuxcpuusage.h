/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/
#if defined OS_LINUX

#include "../common/timecounter.h"
#include <sys/times.h>
#include <string.h>

#ifndef LINUXCPUUSAGE_H_
#define LINUXCPUUSAGE_H_

class LinuxCPUUsage{

public:
	LinuxCPUUsage(void );
    ~LinuxCPUUsage( void );
    float getValue();

private:
    bool firstGetCpu;
    clock_t lastCPU;
    clock_t lastSysCPU;
    clock_t lastUserCPU;
    int numProcessors;
    double percentCpu;
    TimeCounter cpuCounter;
};

#endif /* LINUXCPUUSAGE_H_ */

#endif
