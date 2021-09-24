/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/

#include "timecounter.h"
#if defined OS_WINDOWS
#include <windows.h>
#endif

TimeCounter::TimeCounter(){
	reset();
}

TimeCounter::~TimeCounter(){

}


long TimeCounter::getMillisecons(){
#if defined OS_LINUX
	struct timeb tmb;
	ftime(&tmb);
	return (tmb.time * 1000) + tmb.millitm;
#elif defined OS_MAC
	struct timeb tmb;
	ftime(&tmb);
	return (tmb.time * 1000) + tmb.millitm;
#elif defined OS_WINDOWS
	return GetTickCount();
#else
	return 0;
#endif
}

void TimeCounter::reset(){
	current=getMillisecons();
}

long TimeCounter::getCounter(){
	long elapsed=getMillisecons()-current;
	if (elapsed<0){ //FORSE CAMBIATO ORARIO PC
		elapsed=0;
		reset();
	}
	return elapsed;
}

long TimeCounter::getCounterAndReset(){
	long c = getCounter();
	reset();
	return c;
}

void TimeCounter::printCounter(std::string msg){
	std::string app=msg+"%d\n";
	printf(app.c_str(),getCounter());
}

void TimeCounter::printCounterAndReset(std::string msg){
	std::string app=msg+"%d\n";
	printf(app.c_str(),getCounterAndReset());
}



