
/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/
#if defined OS_WINDOWS

#include "taskmng.h"

TaskMng::TaskMng(){

}

void TaskMng::appendMemoryUsage(HANDLE hProcess_i, JSONWriter* jsonw){
	PPROCESS_MEMORY_COUNTERS pMemCountr = new PROCESS_MEMORY_COUNTERS;
	if( GetProcessMemoryInfo(hProcess_i,pMemCountr, sizeof(PROCESS_MEMORY_COUNTERS))){
		jsonw->addNumber(L"Memory", pMemCountr->WorkingSetSize);
	}else{
		jsonw->addNumber(L"Memory", 0);
	}
	delete pMemCountr;
}

void TaskMng::appendProcessOwner(HANDLE hProcess_i, JSONWriter* jsonw){
   wstring sown;
   HANDLE hProcessToken = NULL;
   if ( ::OpenProcessToken( hProcess_i, TOKEN_READ, &hProcessToken ) || !hProcessToken )  {
	   DWORD dwProcessTokenInfoAllocSize = 0;
	   ::GetTokenInformation(hProcessToken, TokenUser, NULL, 0, &dwProcessTokenInfoAllocSize);
	   if( ::GetLastError() == ERROR_INSUFFICIENT_BUFFER )
	   {
		  PTOKEN_USER pUserToken = reinterpret_cast<PTOKEN_USER>( new BYTE[dwProcessTokenInfoAllocSize] );
		  if (pUserToken != NULL)
		  {
			 if (::GetTokenInformation( hProcessToken, TokenUser, pUserToken, dwProcessTokenInfoAllocSize, &dwProcessTokenInfoAllocSize ))
			 {
				SID_NAME_USE   snuSIDNameUse;
				TCHAR          szUser[MAX_PATH] = { 0 };
				DWORD          dwUserNameLength = MAX_PATH;
				TCHAR          szDomain[MAX_PATH] = { 0 };
				DWORD          dwDomainNameLength = MAX_PATH;

				if ( ::LookupAccountSid( NULL,
										 pUserToken->User.Sid,
										 szUser,
										 &dwUserNameLength,
										 szDomain,
										 &dwDomainNameLength,
										 &snuSIDNameUse )){
				   // Prepare user name string
				   sown.append(towstring(szDomain));
				   sown.append(L"\\");
				   sown.append(towstring(szUser));
				}
			 }
			 delete [] pUserToken;
		  }
	   }
   }
   CloseHandle( hProcessToken );
   jsonw->addString(L"Owner", sown);
}

/*void EnableDebugPriv()
{
    HANDLE hToken;
    LUID luid;
    TOKEN_PRIVILEGES tkp;

    OpenProcessToken(GetCurrentProcess(), TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY, &hToken);

    LookupPrivilegeValue(NULL, SE_DEBUG_NAME, &luid);

    tkp.PrivilegeCount = 1;
    tkp.Privileges[0].Luid = luid;
    tkp.Privileges[0].Attributes = SE_PRIVILEGE_ENABLED;

    AdjustTokenPrivileges(hToken, false, &tkp, sizeof(tkp), NULL, NULL);

    CloseHandle(hToken);
}*/

wchar_t* TaskMng::getTaskList() {
	JSONWriter jsonw;
	jsonw.beginArray();
	//EnableDebugPriv();

    PROCESSENTRY32 entry;
    entry.dwSize = sizeof(PROCESSENTRY32);

    HANDLE snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);

    if (Process32First(snapshot, &entry) == TRUE){
        while (Process32Next(snapshot, &entry) == TRUE){
        	jsonw.beginObject();

        	jsonw.addString(L"Name", towstring(entry.szExeFile));
        	jsonw.addNumber(L"PID", entry.th32ProcessID);
			HANDLE hProcess = OpenProcess(PROCESS_ALL_ACCESS, FALSE, entry.th32ProcessID);
			appendMemoryUsage(hProcess, &jsonw);
			appendProcessOwner(hProcess, &jsonw);

			CloseHandle(hProcess);

			jsonw.endObject();
        }
    }

    CloseHandle(snapshot);

    jsonw.endArray();
	return towcharp(jsonw.getString());
}

int TaskMng::taskKill(int pid) {
	DWORD dwDesiredAccess = PROCESS_TERMINATE;
    BOOL  bInheritHandle  = FALSE;
    HANDLE hProcess = OpenProcess(dwDesiredAccess, bInheritHandle, pid);
    if (hProcess == NULL){
        return FALSE;
    }
	DWORD uExitCode = 0;
    GetExitCodeProcess(hProcess, &uExitCode);
    BOOL result = TerminateProcess(hProcess, uExitCode);

    CloseHandle(hProcess);
	if (result==TRUE){
		return 1;
	}
	return 0;
}

int TaskMng::isTaskRunning(int pid) {
	DWORD dwDesiredAccess = SYNCHRONIZE;
    BOOL  bInheritHandle  = FALSE;
	HANDLE hProcess = OpenProcess(dwDesiredAccess, bInheritHandle, pid);
    if (hProcess == NULL){
        return FALSE;
    }
	DWORD ret = WaitForSingleObject(hProcess, 0);
	CloseHandle(hProcess);
	if (ret == WAIT_TIMEOUT){
		return 1;
	}
	return 0;
}

#endif
