/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/

#if defined OS_LINUX

#include "linuxcpuusage.h"

LinuxCPUUsage::LinuxCPUUsage(){
	percentCpu = 0;
	lastCPU = 0;
	lastSysCPU = 0;
	lastUserCPU = 0;
	firstGetCpu=true;
	cpuCounter.reset();
	//read process number
	FILE* file = fopen("/proc/cpuinfo", "r");
	char line[128];
	numProcessors = 0;
	while(fgets(line, 128, file) != NULL){
		if (strncmp(line, "processor", 9) == 0) numProcessors++;
	}
	fclose(file);
}

LinuxCPUUsage::~LinuxCPUUsage(){

}

float LinuxCPUUsage::getValue(){
	if ((!firstGetCpu) && (cpuCounter.getCounter()<1000)){
		return percentCpu;
	}

	struct tms timeSample;
	clock_t now;

	now = times(&timeSample);
	if (firstGetCpu){
		firstGetCpu=false;
		percentCpu = 0.0;
	}else{
		if (now <= lastCPU || timeSample.tms_stime < lastSysCPU ||
			timeSample.tms_utime < lastUserCPU){
			percentCpu = 0.0;
		}else{
			percentCpu = (timeSample.tms_stime - lastSysCPU) +
				(timeSample.tms_utime - lastUserCPU);
			percentCpu /= (now - lastCPU);
			percentCpu /= numProcessors;
			percentCpu *=100;
		}
	}
	lastCPU = now;
	lastSysCPU = timeSample.tms_stime;
	lastUserCPU = timeSample.tms_utime;
	cpuCounter.reset();
	//printf("CPU: %f\n",percent);
	return percentCpu;
}

#endif
