/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/
#include <stdio.h>
#include <string>
#include <sys/timeb.h>

#ifndef TIMECOUNTER_H_
#define TIMECOUNTER_H_

class TimeCounter{

public:
	TimeCounter(void );
    ~TimeCounter( void );
    void reset();
    long getCounter();
    long getCounterAndReset();
    void printCounter(std::string);
    void printCounterAndReset(std::string);

private:
    long getMillisecons();

    long current;
};

#endif /* TIMECOUNTER_H_ */

