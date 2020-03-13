/* 
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
 */
#include "main.h"
#include "timecounter.h"

//using namespace std;

#if defined OS_WINDOWS

#define _CRT_SECURE_NO_WARNINGS
#define _WIN32_DCOM
#define WIDTHBYTES(bits)    (((bits) + 31) / 32 * 4)
//#pragma comment(lib,"UserEnv.lib")
//#pragma warning(disable : 4995)

WindowsLoadLib loadLib;
OSVERSIONINFOEX m_osVerInfo = { 0 };
//bool binit=false;
//EXTERN_C IMAGE_DOS_HEADER __ImageBase;

#endif

DWDebugger debugger = DWDebugger();
ScreenCapture screenCapture = ScreenCapture(&debugger);


#if defined OS_WINDOWS

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

long consoleSessionId(){
	return WTSGetActiveConsoleSessionId();
}

void winStationConnectW(){
	if (loadLib.WinStationConnectWFunc()){
		WCHAR password[1];
		memset(password, 0, sizeof(password));
		loadLib.WinStationConnectWFunc()(NULL, 0, WTSGetActiveConsoleSessionId(), password, 0);
	}
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


int isProcessElevated(){
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

int startProcessAsUser(wchar_t* scmd, wchar_t* pythonHome) {
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

void setAsElevated(int i){
	screenCapture.getNative().setAsElevated(i==1);
}

int sas(){
	BOOL bret=FALSE;
	if (isVistaOrLater() && loadLib.SendSasFunc()) {
		HKEY regkey;
		LSTATUS st = RegOpenKeyEx(HKEY_LOCAL_MACHINE,"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System", 0, KEY_ALL_ACCESS, &regkey);
		if (st==ERROR_SUCCESS){
			DWORD oldvalue=0;
			DWORD size=sizeof(DWORD);
			DWORD dwType=REG_DWORD;
			st = RegQueryValueEx(regkey, "SoftwareSASGeneration", 0, &dwType, (BYTE*)&oldvalue, &size);
			boolean brem=true;
			if (st==ERROR_SUCCESS){
				brem=false;
			}
			if ((brem) || (oldvalue!=1)){
				DWORD value=1;
				st = RegSetValueEx(regkey, "SoftwareSASGeneration",0, REG_DWORD, (const BYTE*)&value, sizeof(value));
				if (st==ERROR_SUCCESS){
					loadLib.SendSasFunc()(FALSE);
					bret=TRUE;
					if (!brem){
						st = RegSetValueEx(regkey, "SoftwareSASGeneration",0, REG_DWORD, (const BYTE*)&oldvalue, sizeof(oldvalue));
					}else{
						RegDeleteValue(regkey,"SoftwareSASGeneration");
					}
				}else{
					loadLib.SendSasFunc()(FALSE);
					bret=TRUE;
				}
			}else{
				loadLib.SendSasFunc()(FALSE);
				bret=TRUE;
			}
			RegCloseKey(regkey);
		}
	}
	if (bret==TRUE){
		return 1;
	}else{
		return 0;
	}
}
#endif


int version(){
	return 1;
}

void freeMemory(void* pnt){
	free(pnt);
}

void init(int id){
	screenCapture.initialize(id);
}

void monitor(int id, int index){
	screenCapture.monitor(id, index);
}

void difference(int id, int typeFrame, int quality, CallbackDifference cbdiff) {
	screenCapture.difference(id, typeFrame, quality, cbdiff);
}

void term(int id) {
	screenCapture.terminate(id);
}

void inputMouse(int id, int x, int y, int button, int wheel, bool ctrl, bool alt, bool shift, bool command){
	screenCapture.inputMouse(id,x,y,button,wheel,ctrl,alt,shift,command);
}

void inputKeyboard(int id, const char* type, const char* key, bool ctrl, bool alt, bool shift, bool command){
	screenCapture.inputKeyboard(id,type,key,ctrl,alt,shift,command);
}

wchar_t* copyText(int id){
	return screenCapture.copyText(id);
}

void pasteText(int id,wchar_t* str){
	screenCapture.pasteText(id,str);
}

void setCallbackDebug(CallbackType callback){
	debugger.setCallback(callback);
}

#if defined OS_MAC
int consoleUserId(){
	uid_t uid=0;
	SCDynamicStoreRef store = SCDynamicStoreCreate(NULL, CFSTR("GetConsoleUser"), NULL, NULL);
	if(store != NULL){
		SCDynamicStoreCopyConsoleUser(store, &uid, NULL);
		CFRelease(store);
	}
	return uid;
}
#endif


void callbackDifference(int sz, unsigned char* data){
	//printf("LN:%d\n",sz);
}

#if defined OS_WINDOWS
int wmain(int argc, wchar_t **argv) {
#else
	int main(int argc, char **argv) {
#endif


	/*Sleep(4000);
	HWND hwnd = GetForegroundWindow();
	if (hwnd != 0) {

		printf("hwnd %d\n", hwnd);


		int id = 0;
		init(id);
		inputKeyboard(id, "CHAR", "46", false, false, false); //.
		//inputKeyboard(id, "CHAR", "64", false, false, false); //@
		//inputKeyboard(id, "CHAR", "35", false, false, false);
		term(id);

		printf("FINE\n");

	}*/


	int id = 0;
	init(id);
	TimeCounter tc;

	int i=0;
	monitor(id,0);
	while (true){
		tc.reset();
		unsigned char* bf = NULL;
		difference(id,0,100,*callbackDifference);
		printf("DIFF %d TM:%lu\n",i,tc.getCounter());
		i++;
		if (i>=1){
			break;
		}
		free(bf);

		int milliseconds=10;
#if defined OS_WINDOWS
		Sleep(milliseconds);
#else
		struct timespec ts;
		ts.tv_sec = milliseconds / 1000;
		ts.tv_nsec = (milliseconds % 1000) * 1000000;
		nanosleep(&ts, NULL);
#endif

	}

	term(id);

	return 0;
}

#if defined OS_MAC

int MACTest1main(int argc, char **argv){
	unsigned int displayid = CGMainDisplayID();
	//CGImageRef image_ref = CGDisplayCreateImage(displayid);
	//CGImageRef image_ref = CGWindowListCreateImage(CGRectNull, kCGWindowListOptionOnScreenOnly,0, kCGWindowImageBoundsIgnoreFraming);
	CGRect captureRect = CGDisplayBounds(displayid);
	CGImageRef image_ref = CGWindowListCreateImage(captureRect, kCGWindowListOptionOnScreenOnly, kCGNullWindowID, kCGWindowImageDefault);

	if (image_ref!=NULL){
		CGDataProviderRef provider = CGImageGetDataProvider(image_ref);
		CFDataRef dataref = CGDataProviderCopyData(provider);
		int imageW = CGImageGetWidth(image_ref);
		int imageH = CGImageGetHeight(image_ref);
		int bpp = CGImageGetBitsPerPixel(image_ref) / 8;
		unsigned char* pixels = (unsigned char*)malloc(imageW * imageH * bpp);
		memcpy(pixels, CFDataGetBytePtr(dataref), imageW * imageH * bpp);

		CFRelease(dataref);
		CGImageRelease(image_ref);

		free(pixels);
	}
	return 0;
}

#endif
