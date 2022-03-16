/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/


#include "util.h"
#include "jsonwriter.h"

#if defined OS_WINDOWS
#include <windows.h>
#include <string>
#include <tlhelp32.h>
#include <Psapi.h>
#endif
using namespace std;

class TaskMng{
public:
	TaskMng();
	int getTaskList(wchar_t** sret);
	int taskKill(int pid);
	int isTaskRunning(int pid);
private:
#if defined OS_WINDOWS
	void appendMemoryUsage(HANDLE hProcess_i, JSONWriter* jsonw);
	void appendProcessOwner(HANDLE hProcess_i, JSONWriter* jsonw);
#endif

};
