/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/

#if defined OS_MAC

#include "maccpuusage.h"

MacCPUUsage::MacCPUUsage(){
	percentCpu=-1.0f;
	previousTotalTicks=0;
	previousIdleTicks=0;
}

MacCPUUsage::~MacCPUUsage(){

}

float MacCPUUsage::calculateCPULoad(unsigned long long idleTicks, unsigned long long totalTicks){
	unsigned long long totalTicksSinceLastTime = totalTicks-previousTotalTicks;
	unsigned long long idleTicksSinceLastTime  = idleTicks-previousIdleTicks;
	float ret = 1.0f-((totalTicksSinceLastTime > 0) ? ((float)idleTicksSinceLastTime)/totalTicksSinceLastTime : 0);
	previousTotalTicks = totalTicks;
	previousIdleTicks  = idleTicks;
	return ret*100.0;
}

float MacCPUUsage::getValue(){
	if ((percentCpu>=0) && (cpuCounter.getCounter()<1000)){
		return percentCpu;
	}
	host_cpu_load_info_data_t cpuinfo;
	mach_msg_type_number_t count = HOST_CPU_LOAD_INFO_COUNT;
	if (host_statistics(mach_host_self(), HOST_CPU_LOAD_INFO, (host_info_t)&cpuinfo, &count) == KERN_SUCCESS){
		unsigned long long totalTicks = 0;
		for(int i=0; i<CPU_STATE_MAX; i++) totalTicks += cpuinfo.cpu_ticks[i];
		percentCpu=calculateCPULoad(cpuinfo.cpu_ticks[CPU_STATE_IDLE], totalTicks);
	}else{
		percentCpu=-1.0f;
	}
	cpuCounter.reset();
	return percentCpu;
}

#endif
