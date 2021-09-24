/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/
#if defined OS_WINDOWS

#define _CRT_SECURE_NO_WARNINGS

#include "main.h"

OSVERSIONINFOEX m_osVerInfo = { 0 };

int taskKill(int pid) {
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

int isTaskRunning(int pid) {
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

void setFilePermissionEveryone(LPCTSTR FileName){
    PSID pEveryoneSID = NULL;
    PACL pACL = NULL;
    EXPLICIT_ACCESS ea[1];
    SID_IDENTIFIER_AUTHORITY SIDAuthWorld = SECURITY_WORLD_SID_AUTHORITY;

    AllocateAndInitializeSid(&SIDAuthWorld, 1,
                     SECURITY_WORLD_RID,
                     0, 0, 0, 0, 0, 0, 0,
                     &pEveryoneSID);

    ZeroMemory(&ea, 1 * sizeof(EXPLICIT_ACCESS));
    ea[0].grfAccessPermissions = 0xFFFFFFFF;
    ea[0].grfAccessMode = GRANT_ACCESS;
    ea[0].grfInheritance= NO_INHERITANCE;
    ea[0].Trustee.TrusteeForm = TRUSTEE_IS_SID;
    ea[0].Trustee.TrusteeType = TRUSTEE_IS_WELL_KNOWN_GROUP;
    ea[0].Trustee.ptstrName  = (LPTSTR) pEveryoneSID;
	SetEntriesInAcl(1, ea, NULL, &pACL);
	PSECURITY_DESCRIPTOR pSD = (PSECURITY_DESCRIPTOR) LocalAlloc(LPTR,
                                SECURITY_DESCRIPTOR_MIN_LENGTH);

    InitializeSecurityDescriptor(pSD,SECURITY_DESCRIPTOR_REVISION);

    SetSecurityDescriptorDacl(pSD,
            TRUE,
            pACL,
            FALSE);


    SetFileSecurity(FileName, DACL_SECURITY_INFORMATION, pSD);

    if (pEveryoneSID)
        FreeSid(pEveryoneSID);
    if (pACL)
        LocalFree(pACL);
    if (pSD)
        LocalFree(pSD);
}

void initOSVersionInfo(){
  if (m_osVerInfo.dwOSVersionInfoSize == 0) {
    m_osVerInfo.dwOSVersionInfoSize = sizeof(OSVERSIONINFO);

    if (!GetVersionEx((OSVERSIONINFO*)&m_osVerInfo)) {
      m_osVerInfo.dwOSVersionInfoSize = 0;
    }
  }
}

int isWinNTFamily(){
  initOSVersionInfo();
  if (m_osVerInfo.dwPlatformId == VER_PLATFORM_WIN32_NT){
	  return 1;
  }
  return 0;
}

int isWin2008Server(){
  initOSVersionInfo();
  if ((m_osVerInfo.dwMajorVersion == 6) && ((m_osVerInfo.dwMinorVersion == 0) || (m_osVerInfo.dwMinorVersion == 1)) && m_osVerInfo.wProductType != VER_NT_WORKSTATION){
	  return 1;
  }
  return 0;
}

int isVistaOrLater(){
  initOSVersionInfo();
  if (m_osVerInfo.dwMajorVersion >= 6){
	  return 1;
  }
  return 0;
}

int isWinXP(){
  initOSVersionInfo();
  if ((m_osVerInfo.dwMajorVersion == 5) && (m_osVerInfo.dwMinorVersion == 1) && isWinNTFamily()){
	  return 1;
  }
  return 0;
}

int isWin2003Server(){
  initOSVersionInfo();
  if ((m_osVerInfo.dwMajorVersion == 5) && (m_osVerInfo.dwMinorVersion == 2) && isWinNTFamily()){
	  return 1;
  }
  return 0;
}

int isUserInAdminGroup(){
	BOOL fInAdminGroup = FALSE;
	DWORD dwError = ERROR_SUCCESS;
	HANDLE hToken = NULL;
	HANDLE hTokenToCheck = NULL;
	try{
		DWORD cbSize = 0;
		OSVERSIONINFO osver = { sizeof(osver) };

		if (!OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY | TOKEN_DUPLICATE,
			&hToken)){
			dwError = GetLastError();
			goto Cleanup;
		}

		if (!GetVersionEx(&osver)){
			dwError = GetLastError();
			goto Cleanup;
		}

		if (osver.dwMajorVersion >= 6){
			TOKEN_ELEVATION_TYPE elevType;
			if (!GetTokenInformation(hToken, TokenElevationType, &elevType,
				sizeof(elevType), &cbSize))
			{
				dwError = GetLastError();
				goto Cleanup;
			}

			if (TokenElevationTypeLimited == elevType){
				if (!GetTokenInformation(hToken, TokenLinkedToken, &hTokenToCheck,
					sizeof(hTokenToCheck), &cbSize))
				{
					dwError = GetLastError();
					goto Cleanup;
				}
			}
		}

		if (!hTokenToCheck){
			if (!DuplicateToken(hToken, SecurityIdentification, &hTokenToCheck))
			{
				dwError = GetLastError();
				goto Cleanup;
			}
		}

		BYTE adminSID[SECURITY_MAX_SID_SIZE];
		cbSize = sizeof(adminSID);
		if (!CreateWellKnownSid(WinBuiltinAdministratorsSid, NULL, &adminSID,
			&cbSize))
		{
			dwError = GetLastError();
			goto Cleanup;
		}
		if (!CheckTokenMembership(hTokenToCheck, &adminSID, &fInAdminGroup)) {
			dwError = GetLastError();
			goto Cleanup;
		}
	}catch(...){
		fInAdminGroup = FALSE;
	}
Cleanup:
    if (hToken){
        CloseHandle(hToken);
        hToken = NULL;
    }
    if (hTokenToCheck){
        CloseHandle(hTokenToCheck);
        hTokenToCheck = NULL;
    }

    if (ERROR_SUCCESS != dwError){
    	return 0;
    }

    if (fInAdminGroup==TRUE){
		return 1;
	}
	return 0;
}


int isRunAsAdmin(){
    BOOL fIsRunAsAdmin = FALSE;
    DWORD dwError = ERROR_SUCCESS;
	PSID pAdministratorsGroup = NULL;
    try{
		SID_IDENTIFIER_AUTHORITY NtAuthority = SECURITY_NT_AUTHORITY;
		if (!AllocateAndInitializeSid(
			&NtAuthority,
			2,
			SECURITY_BUILTIN_DOMAIN_RID,
			DOMAIN_ALIAS_RID_ADMINS,
			0, 0, 0, 0, 0, 0,
			&pAdministratorsGroup))
		{
			dwError = GetLastError();
			goto Cleanup;
		}

		if (!CheckTokenMembership(NULL, pAdministratorsGroup, &fIsRunAsAdmin)){
			dwError = GetLastError();
			goto Cleanup;
		}
	}catch(...){
		fIsRunAsAdmin = FALSE;
	}
Cleanup:
    if (pAdministratorsGroup){
        FreeSid(pAdministratorsGroup);
        pAdministratorsGroup = NULL;
    }
    if (ERROR_SUCCESS != dwError){
    	return 0;
    }
    if (fIsRunAsAdmin==TRUE){
		return 1;
	}
	return 0;
}


int DWAScreenCaptureIsProcessElevated(){
    BOOL fIsElevated = FALSE;
    DWORD dwError = ERROR_SUCCESS;
	HANDLE hToken = NULL;
    try{
		if (!OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &hToken)){
			dwError = GetLastError();
			goto Cleanup;
		}
		TOKEN_ELEVATION elevation;
		DWORD dwSize;
		if (!GetTokenInformation(hToken, TokenElevation, &elevation,
			sizeof(elevation), &dwSize)){
			dwError = GetLastError();
			if (dwError==ERROR_INVALID_PARAMETER){
				fIsElevated = TRUE;
			}
			goto Cleanup;
		}
		fIsElevated = elevation.TokenIsElevated;
	}catch(...){
		fIsElevated = TRUE;
	}
Cleanup:
    if (hToken){
        CloseHandle(hToken);
        hToken = NULL;
    }
    if (fIsElevated==TRUE){
		return 1;
	}
    if (ERROR_SUCCESS != dwError){
    	return 0;
	}
	return 0;
}

long getActiveConsoleId(){
	return WTSGetActiveConsoleSessionId();
}

int startProcess(wchar_t* scmd, wchar_t* pythonHome) {
	STARTUPINFOW siStartupInfo;
	PROCESS_INFORMATION piProcessInfo;
	DWORD dwCreationFlags;
	dwCreationFlags = HIGH_PRIORITY_CLASS | CREATE_NO_WINDOW;
	ZeroMemory(&siStartupInfo, sizeof(STARTUPINFO));
	siStartupInfo.cb= sizeof(STARTUPINFO);
	siStartupInfo.lpReserved=NULL;
	siStartupInfo.lpTitle=(wchar_t*)L"DWAgentLib";
	siStartupInfo.dwX=0;
	siStartupInfo.dwY=0;
	siStartupInfo.dwXSize=0;
	siStartupInfo.dwYSize=0;
	siStartupInfo.dwXCountChars=0;
	siStartupInfo.dwYCountChars=0;
	siStartupInfo.dwFillAttribute=0;

	//siStartupInfo.wShowWindow = SW_HIDE;
	//siStartupInfo.dwFlags = STARTF_USESHOWWINDOW;
	siStartupInfo.dwFlags |= STARTF_USESTDHANDLES;
	//siStartupInfo.hStdInput = GetStdHandle(STD_INPUT_HANDLE);
	//siStartupInfo.hStdOutput = GetStdHandle(STD_OUTPUT_HANDLE);
	//siStartupInfo.hStdError = GetStdHandle(STD_ERROR_HANDLE);

	ZeroMemory(&piProcessInfo, sizeof(piProcessInfo));

	if (wcscmp(pythonHome, L"") != 0) {
		SetEnvironmentVariableW(TEXT(L"PYTHONHOME"),pythonHome);
	}

	int ppid=-1;
	if (CreateProcessW(NULL, // Application name
				scmd, // Application arguments
				NULL,
				NULL,
				FALSE,
				dwCreationFlags,
				NULL,
				NULL, // Working directory
				&siStartupInfo,
				&piProcessInfo) == TRUE) {
		ppid=piProcessInfo.dwProcessId;
	}
	return ppid;
}

int startProcessInActiveConsole(wchar_t* scmd, wchar_t* pythonHome) {
	STARTUPINFOW siStartupInfo;
	PROCESS_INFORMATION piProcessInfo;

	BOOL bRunAsUser=FALSE;
	HANDLE hUserTokenDup;
	DWORD dwCreationFlags;
	LPVOID pEnv =NULL;

	dwCreationFlags = HIGH_PRIORITY_CLASS | CREATE_NO_WINDOW;
	ZeroMemory(&siStartupInfo, sizeof(STARTUPINFO));
	siStartupInfo.cb= sizeof(STARTUPINFO);
	siStartupInfo.lpReserved=NULL;
	siStartupInfo.lpDesktop = (wchar_t*)L"winsta0\\default";
	siStartupInfo.lpTitle=(wchar_t*)L"DWAgentLib";
	siStartupInfo.dwX=0;
	siStartupInfo.dwY=0;
	siStartupInfo.dwXSize=0;
	siStartupInfo.dwYSize=0;
	siStartupInfo.dwXCountChars=0;
	siStartupInfo.dwYCountChars=0;
	siStartupInfo.dwFillAttribute=0;

	//siStartupInfo.wShowWindow = SW_HIDE;
	//siStartupInfo.dwFlags = STARTF_USESHOWWINDOW;
	siStartupInfo.dwFlags |= STARTF_USESTDHANDLES;
	//siStartupInfo.hStdInput = GetStdHandle(STD_INPUT_HANDLE);
	//siStartupInfo.hStdOutput = GetStdHandle(STD_OUTPUT_HANDLE);
	//siStartupInfo.hStdError = GetStdHandle(STD_ERROR_HANDLE);

	ZeroMemory(&piProcessInfo, sizeof(piProcessInfo));

	if (wcscmp(pythonHome, L"") != 0) {
		SetEnvironmentVariableW(TEXT(L"PYTHONHOME"),pythonHome);
	}

	HANDLE procHandle = GetCurrentProcess();
	DWORD dwSessionId = WTSGetActiveConsoleSessionId();
	if (dwSessionId) {
		HANDLE hPToken;
		if (!OpenProcessToken(procHandle, TOKEN_DUPLICATE, &hPToken) == 0) {
			if (DuplicateTokenEx(hPToken,MAXIMUM_ALLOWED,0,SecurityImpersonation,TokenPrimary,&hUserTokenDup) != 0) {
				if (SetTokenInformation(hUserTokenDup,(TOKEN_INFORMATION_CLASS) TokenSessionId,&dwSessionId,sizeof (dwSessionId)) != 0) {
					if(CreateEnvironmentBlock(&pEnv,hUserTokenDup,TRUE)){
						dwCreationFlags|=CREATE_UNICODE_ENVIRONMENT;
					}else{
						pEnv=NULL;
					}
					bRunAsUser=TRUE;
				}
			}
		}
	}

	int ppid=-1;
	if (bRunAsUser){
		if (CreateProcessAsUserW(
			hUserTokenDup,            // client's access token
			NULL,              // file to execute
			scmd,     // command line
			NULL,              // pointer to process SECURITY_ATTRIBUTES
			NULL,              // pointer to thread SECURITY_ATTRIBUTES
			FALSE,            // handles are not inheritable
			dwCreationFlags,  // creation flags
			pEnv,              // pointer to new environment block
			NULL,              // name of current directory
			&siStartupInfo,               // pointer to STARTUPINFO structure
			&piProcessInfo                // receives information about new process
			)){
			ppid = piProcessInfo.dwProcessId;
		}
	}else{
		if (CreateProcessW(NULL, // Application name
						scmd, // Application arguments
						NULL,
						NULL,
						FALSE,
						dwCreationFlags,
						NULL,
						NULL, // Working directory
						&siStartupInfo,
						&piProcessInfo) == TRUE) {
			ppid = piProcessInfo.dwProcessId;
		}
	}
	return ppid;
}

void DWAScreenCaptureWinStationConnect(){
	HINSTANCE winstadll = LoadLibrary("winsta.dll");
	if (winstadll){
		IWinStationConnectW winStationConnectWFunc = (IWinStationConnectW)GetProcAddress(winstadll, "WinStationConnectW");
		WCHAR password[1];
		memset(password, 0, sizeof(password));
		winStationConnectWFunc(NULL, 0, WTSGetActiveConsoleSessionId(), password, 0);
	}
}

void closeHandle(HANDLE hdl){
	CloseHandle(hdl);
}

#endif
