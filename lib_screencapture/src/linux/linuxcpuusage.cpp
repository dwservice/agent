/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/

#if defined OS_LINUX

#include "linuxcpuusage.h"

LinuxCPUUsage::LinuxCPUUsage(){
	percentCpu = 0;
	firstGetCpu=true;
	cpuCounter.reset();
	numCores = sysconf(_SC_NPROCESSORS_ONLN);
	if (numCores<=0){
		FILE* file = fopen("/proc/cpuinfo", "r");
		char line[128];
		numCores = 0;
		while(fgets(line, 128, file) != NULL){
			if (strncmp(line, "processor", 9) == 0) numCores++;
		}
		fclose(file);
	}
}

LinuxCPUUsage::~LinuxCPUUsage(){

}

float LinuxCPUUsage::getValue(){
	if ((!firstGetCpu) && (cpuCounter.getCounter()<1000)){
		return percentCpu;
	}
	if (firstGetCpu){
		clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &prevTime);
		percentCpu=0;
	}else{
		timespec curTime;
		clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &curTime);
		double elapsedTime = curTime.tv_sec - prevTime.tv_sec +
							  (curTime.tv_nsec - prevTime.tv_nsec) / 1e9;

		percentCpu = 100.0 * elapsedTime / numCores;
		prevTime = curTime;
	}
	firstGetCpu=false;
	cpuCounter.reset();
	return percentCpu;
}

#endif
