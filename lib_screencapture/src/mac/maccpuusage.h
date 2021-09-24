/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/
#if defined OS_MAC

#include "../common/timecounter.h"
#include <mach/mach_host.h>

#ifndef MACCPUUSAGE_H_
#define MACCPUUSAGE_H_

class MacCPUUsage{

public:
	MacCPUUsage(void );
    ~MacCPUUsage( void );
    float getValue();

private:
    float calculateCPULoad(unsigned long long idleTicks, unsigned long long totalTicks);

    unsigned long long previousTotalTicks;
    unsigned long long previousIdleTicks;
    double percentCpu;
    TimeCounter cpuCounter;

};

#endif /* MACCPUUSAGE_H_ */

#endif
