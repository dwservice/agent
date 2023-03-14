/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/

#if defined OS_MAC

#include "maccpuusage.h"


MacCPUUsage::MacCPUUsage(){
	percentCpu = 0;
	firstGetCpu=true;
	cpuCounter.reset(); 	
    size_t size = sizeof(cpuFrequency);
    sysctlbyname("hw.cpufrequency", &cpuFrequency, &size, nullptr, 0);
}

MacCPUUsage::~MacCPUUsage(){

}

float MacCPUUsage::getValue(){
	if ((percentCpu>=0) && (cpuCounter.getCounter()<1000)){
		return percentCpu;
	}
  	if (firstGetCpu){
  		prevTime=mach_absolute_time();
      	percentCpu=0;
    }else{
      	uint64_t curTime = mach_absolute_time();
        uint64_t elapsedTime = curTime - prevTime;
        mach_timebase_info_data_t timebase;
        mach_timebase_info(&timebase);
        uint64_t elapsedTimeNs = elapsedTime * timebase.numer / timebase.denom;
        percentCpu = 100.0 * elapsedTimeNs / cpuFrequency;
        prevTime = curTime;
    }
  	firstGetCpu=false;
 	cpuCounter.reset();
	return percentCpu;
}

#endif