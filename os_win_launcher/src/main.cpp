/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/

#include "main.h"

using namespace std;

wstring pythonPath = L"";

wstring getDWAgentPath(){
	wchar_t strPathName[_MAX_PATH];
	GetModuleFileNameW(NULL, strPathName, _MAX_PATH);
	wstring newPath(strPathName);
	int fpos = newPath.find_last_of('\\');
	if (fpos != -1)
		newPath = newPath.substr(0,(fpos));
	fpos = newPath.find_last_of('\\');
	if (fpos != -1)
		newPath = newPath.substr(0,(fpos));
	return newPath;
}

BOOL isRunAsAdmin(){
    BOOL fIsRunAsAdmin = FALSE;
    DWORD dwError = ERROR_SUCCESS;
    PSID pAdministratorsGroup = NULL;
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

Cleanup:
    if (pAdministratorsGroup){
        FreeSid(pAdministratorsGroup);
        pAdministratorsGroup = NULL;
    }
    if (ERROR_SUCCESS != dwError){
        throw dwError;
    }
    return fIsRunAsAdmin;
}

bool existsFile(wstring fileName) {
	return GetFileAttributesW(fileName.c_str())!=INVALID_FILE_ATTRIBUTES;
}


bool deleteDir(const wchar_t *path){
	bool bret=true;
    WIN32_FIND_DATAW FindFileData;
    HANDLE hFind;
    DWORD Attributes;
    wchar_t str[MAX_PATH];
	wcscpy(str,path);
	wcscat(str,L"\\*.*");
    hFind = FindFirstFileW(str, &FindFileData);
    do{
        if (wcscmp(FindFileData.cFileName, L".") != 0 && wcscmp(FindFileData.cFileName, L"..") != 0)
        {
            wcscpy(str, path);
            wcscat(str,L"\\");
            wcscat (str,FindFileData.cFileName);
            Attributes = GetFileAttributesW(str);
			if (Attributes & FILE_ATTRIBUTE_DIRECTORY){
                if (!deleteDir(str)){
					bret=false;
					break;
				}
            }else{
				if (!DeleteFileW(str)){
					bret=false;
					break;
				}
            }
        }
    }while(FindNextFileW(hFind, &FindFileData));
    FindClose(hFind);
    RemoveDirectoryW(path);
    return bret;
}

void startRemove(wstring dwPath){
	STARTUPINFOW siStartupInfo;
	PROCESS_INFORMATION piProcessInfo;
	BOOL bRunAsUser=FALSE;
	HANDLE hUserTokenDup;
	DWORD dwCreationFlags;
	LPVOID pEnv =NULL;

	wchar_t szTempPath[MAX_PATH];
	GetTempPathW(MAX_PATH,szTempPath);
	wchar_t szDestPath[MAX_PATH];
	wcscpy(szDestPath,szTempPath);
	wcscat(szDestPath, L"dwaglnc.exe");
	wchar_t szSrcPath[MAX_PATH];
	wcscpy(szSrcPath, dwPath.c_str());
	wcscat(szSrcPath, L"\\native\\dwaglnc.exe");
	DeleteFileW(szDestPath);
	CopyFileW(szSrcPath, szDestPath, false);
	wchar_t cmd[(MAX_PATH * 2)+100];
	wcscpy(cmd,szDestPath);
	wcscat(cmd, L" remove \"");
	wcscat(cmd, dwPath.c_str());
	wcscat(cmd, L"\"");


	dwCreationFlags = NORMAL_PRIORITY_CLASS|CREATE_NO_WINDOW;
	ZeroMemory(&siStartupInfo, sizeof(STARTUPINFO));
	siStartupInfo.cb= sizeof(STARTUPINFO);
	siStartupInfo.lpReserved=NULL;
	siStartupInfo.lpDesktop = L"winsta0\\default";
	siStartupInfo.lpTitle=L"DWAGRemover";
	siStartupInfo.dwX=0;
	siStartupInfo.dwY=0;
	siStartupInfo.dwXSize=0;
	siStartupInfo.dwYSize=0;
	siStartupInfo.dwXCountChars=0;
	siStartupInfo.dwYCountChars=0;
	siStartupInfo.dwFillAttribute=0;
	siStartupInfo.wShowWindow=0;

	ZeroMemory(&piProcessInfo, sizeof(piProcessInfo));
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
	if (bRunAsUser){
		CreateProcessAsUserW(
			hUserTokenDup,          
			NULL,              
			cmd,     
			NULL,              
			NULL,              
			FALSE,             
			dwCreationFlags,  
			pEnv,             
			szTempPath,       
			&siStartupInfo,   
			&piProcessInfo    
			);
	}else{
		CreateProcessW(NULL, 
						cmd, 
						NULL,
						NULL,
						FALSE,
						dwCreationFlags,
						NULL,
						szTempPath, // Working directory
						&siStartupInfo,
						&piProcessInfo);
	}
}

void trim(wstring& str, wchar_t c) {
    string::size_type pos = str.find_last_not_of(c);
    if (pos != string::npos) {
        str.erase(pos + 1);
        pos = str.find_first_not_of(c);
        if (pos != string::npos) str.erase(0, pos);
    } else str.erase(str.begin(), str.end());
}

void trimAll(wstring& str) {
    trim(str, ' ');
    trim(str, '\r');
    trim(str, '\n');
    trim(str, '\t');
}

void loadProperties(wstring dwPath) {
	wstring appfn = dwPath;
	appfn.append(L"\\native\\service.properties");

	HANDLE hFile = CreateFileW(appfn.c_str(), GENERIC_READ, 0, NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
	if (hFile!=INVALID_HANDLE_VALUE){
		DWORD  dwBytesRead;
		char buff[16*1024];
		ReadFile(hFile, buff, sizeof(buff), &dwBytesRead, NULL);
		CloseHandle(hFile);
		wstring apps;
		int numc = MultiByteToWideChar(CP_UTF8, 0, buff, dwBytesRead, NULL, 0);
		if (numc){
			wchar_t *wszTo = new wchar_t[numc + 1];
			wszTo[numc] = L'\0';
			MultiByteToWideChar(CP_UTF8, 0, buff, -1, wszTo, numc);
			apps = wszTo;
			delete[] wszTo;
		}
		int pel = 0;
		while(pel>=0){
			int prepel=pel;
			pel = apps.find(L"\n",prepel);
			wstring line;
			if (pel<0){
				line = apps.substr(prepel);
			}else{
				line = apps.substr(prepel, pel-prepel);
				pel++;
			}
			trimAll(line);

			//Legge le proprietà necessarie
			int endpart1 = line.find_first_of(L"=");
			wstring part1 = line.substr(0, endpart1);
			trimAll(part1);
			wstring part2 = line.substr(endpart1 + 1);
			trimAll(part2);
			if (part1.compare(L"pythonPath") == 0) {
				pythonPath = part2;
			}
		}
	}else{
		throw "ERROR: Read properties error.";
	}
}

int wmain(int argc, wchar_t **argv) {
		if(argc > 0){
		wstring scommand = wstring(argv[1]);
		if (scommand.compare(L"remove")==0){
			if (argc>=2){
				Sleep(2000);
				deleteDir(argv[2]);
			}
			return 0;
		}
		SetEnvironmentVariableW(TEXT(L"PYTHONHOME"),TEXT(L"runtime"));
		wstring dwPath = getDWAgentPath();
		loadProperties(dwPath);
		wstring cmd=L"";
		if (scommand.compare(L"monitor")==0){
			cmd=L"-S -m monitor window";
			ShellExecuteW(GetDesktopWindow(), L"open", pythonPath.c_str(), cmd.c_str(), dwPath.c_str() , SW_SHOW);
		}else if (scommand.compare(L"systray")==0){
			cmd=L"-S -m monitor systray";
			ShellExecuteW(GetDesktopWindow(), L"open", pythonPath.c_str(), cmd.c_str(), dwPath.c_str() , SW_SHOW);
		}else if (scommand.compare(L"configure")==0){
			cmd=L"-S -m configure";
			ShellExecuteW(GetDesktopWindow(), L"open", pythonPath.c_str(), cmd.c_str(), dwPath.c_str() , SW_SHOW);
		}else if (scommand.compare(L"uninstallAsAdimn")==0){
			SHELLEXECUTEINFOW ShExecInfo = {0};
			ShExecInfo.cbSize = sizeof(SHELLEXECUTEINFOW);
			ShExecInfo.fMask = SEE_MASK_NOCLOSEPROCESS;
			ShExecInfo.hwnd = NULL;
			ShExecInfo.lpVerb = NULL;
			ShExecInfo.lpFile = pythonPath.c_str();
			ShExecInfo.lpParameters = L"-S -m installer uninstall";
			ShExecInfo.lpDirectory = dwPath.c_str();
			ShExecInfo.nShow = SW_SHOW;
			ShExecInfo.hInstApp = NULL;
			ShellExecuteExW(&ShExecInfo);
			WaitForSingleObject(ShExecInfo.hProcess,INFINITE);
			//Elimina cartella lanciando l'applicazione da temp
			wstring fln = dwPath;
			fln.append(L"\\").append(L"agent.uninstall");
			if (existsFile(fln)){
				startRemove(dwPath);
			}
		}else if (scommand.compare(L"uninstall")==0){
			//Rilancia L'Applicazione come Amministratore
			SHELLEXECUTEINFOW ShExecInfo = {0};
			ShExecInfo.cbSize = sizeof(SHELLEXECUTEINFOW);
			ShExecInfo.fMask = SEE_MASK_NOCLOSEPROCESS;
			ShExecInfo.hwnd = NULL;
			if (isRunAsAdmin()){
				ShExecInfo.lpVerb  = NULL;
			}else{
				ShExecInfo.lpVerb  = L"runas";
			}
			ShExecInfo.lpFile = L"native\\dwaglnc.exe";
			ShExecInfo.lpParameters = L"uninstallAsAdimn";
			ShExecInfo.lpDirectory = dwPath.c_str();
			ShExecInfo.nShow = SW_SHOW;
			ShExecInfo.hInstApp = NULL;
			ShellExecuteExW(&ShExecInfo);
		}
	}
    return 0;
}

