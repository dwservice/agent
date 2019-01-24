/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/

#include "../../../agent/lib_gdi/src/main.h"
#include <string>
#include <time.h>
#include <algorithm>
#include <fstream>

#include "7zip/7z.h"
#include "7zip/7zAlloc.h"
#include "7zip/7zBuf.h"
#include "7zip/7zCrc.h"
#include "7zip/7zFile.h"
#include "7zip/7zVersion.h"

#define BUFFERSIZE 64*1024

const char ckeckstartcompressfile[] = " @STARTZIPINSTALLER@!"; //il ! all'inizio lo ricerco dopo cosi non trova la stringa nell'exe

ISzAlloc g_AllocTmp = { SzAlloc, SzFree };

int winid=-1;
int winw=200;
int winh=12;

int percent=0;

bool silent=false;
int margc=0;
wchar_t **margv;


typedef BOOL (WINAPI *LPFN_ISWOW64PROCESS) (HANDLE, PBOOL);
LPFN_ISWOW64PROCESS fnIsWow64Process;

using namespace std;

wstring tmpPath;
bool bRunAsAdmin=false;
wstring runtimeExe=L"dwagent.exe";

wstring getExePath(){
	wchar_t strPathName[MAX_PATH];
	GetModuleFileNameW(NULL, strPathName, MAX_PATH);
	wstring newPath(strPathName);
	return newPath;
}

wstring getExeName(){
	wchar_t strPathName[MAX_PATH];
	GetModuleFileNameW(NULL, strPathName, MAX_PATH);
	wstring newExe(strPathName);
	int fpos = newExe.find_last_of('\\');
	if (fpos != -1)
		newExe = newExe.substr(fpos+1);
	fpos = newExe.find_last_of('.');
	if (fpos != -1)
		newExe = newExe.substr(0,(fpos));
	return newExe;
}

wstring getBasePath(){
	wchar_t strPathName[MAX_PATH];
	GetModuleFileNameW(NULL, strPathName, MAX_PATH);
	wstring newPath(strPathName);
	int fpos = newPath.find_last_of('\\');
	if (fpos != -1)
		newPath = newPath.substr(0,(fpos));
	return newPath;
}

bool argIsAsAdmin(int i) {
	if (i==1){
		wstring app;
		app.append(margv[i]);
		if(app.find(L"-asadmin=") == 0){
			return true;
		}
	}
	return false;
}

bool loadTmpPathByArgs(){
	if ((margc>=2) && argIsAsAdmin(1)){
		wstring app;
		app.append(margv[1]);
		tmpPath.append(app.substr(9));
		return true;
	}
	return false;
}


int Buf_EnsureSize(CBuf *dest, size_t size)
{
  if (dest->size >= size)
    return 1;
  Buf_Free(dest, &g_AllocTmp);
  return Buf_Create(dest, size, &g_AllocTmp);
}

SRes Utf16_To_Char(CBuf *buf, const UInt16 *s
    #ifndef _USE_UTF8
    , UINT codePage
    #endif
    )
{
  unsigned len = 0;
  for (len = 0; s[len] != 0; len++);

  {
    unsigned size = len * 3 + 100;
    if (!Buf_EnsureSize(buf, size))
      return SZ_ERROR_MEM;
    {
      buf->data[0] = 0;
      if (len != 0)
      {
        char defaultChar = '_';
        BOOL defUsed;
        unsigned numChars = 0;
        numChars = WideCharToMultiByte(codePage, 0, (LPCWSTR)s, len, (char *)buf->data, size, &defaultChar, &defUsed);
        if (numChars == 0 || numChars >= size)
          return SZ_ERROR_FAIL;
        buf->data[numChars] = 0;
      }
      return SZ_OK;
    }
  }

}

WRes MyCreateDir(const UInt16 *name){
  return CreateDirectoryW((LPCWSTR)name, NULL) ? 0 : GetLastError();
}

WRes OutFile_OpenUtf16(CSzFile *p, const UInt16 *name){
  return OutFile_OpenW(p, (LPCWSTR)name);
}

bool decompressFile(wstring pathcmp){

	bool bret=true;
	CFileInStream archiveStream;
	CLookToRead lookStream;
	CSzArEx db;
	SRes res;
	ISzAlloc allocImp;
	ISzAlloc allocTempImp;
	UInt16 *temp = NULL;
	size_t tempSize = 0;

	if (InFile_OpenW(&archiveStream.file, pathcmp.c_str())) {
		return false;
	}

	allocImp.Alloc = SzAlloc;
	allocImp.Free = SzFree;

	allocTempImp.Alloc = SzAllocTemp;
	allocTempImp.Free = SzFreeTemp;

	FileInStream_CreateVTable(&archiveStream);
	LookToRead_CreateVTable(&lookStream, False);

	lookStream.realStream = &archiveStream.s;
	LookToRead_Init(&lookStream);

	CrcGenerateTable();

	SzArEx_Init(&db);

	res = SzArEx_Open(&db, &lookStream.s, &allocImp, &allocTempImp);

	if (res == SZ_OK){
		UInt32 i;
		UInt32 blockIndex = 0xFFFFFFFF;
		Byte *outBuffer = 0;
		size_t outBufferSize = 0;

		for (i = 0; i < db.NumFiles; i++){
			int newperc=(int)(((float)(i+1)/(float)db.NumFiles)*100);
			if (percent!=newperc){
				percent=newperc;
				if (!silent){
					repaint(winid, 0, 0, winw, winh);
				}
			}
			size_t offset = 0;
			size_t outSizeProcessed = 0;
			size_t len;
			unsigned isDir = SzArEx_IsDir(&db, i);
			len = SzArEx_GetFileNameUtf16(&db, i, NULL);

			if (len > tempSize){
			  SzFree(NULL, temp);
			  tempSize = len;
			  temp = (UInt16 *)SzAlloc(NULL, tempSize * sizeof(temp[0]));
			  if (!temp){
				res = SZ_ERROR_MEM;
				bret=false;
				break;
			  }
			}

			SzArEx_GetFileNameUtf16(&db, i, temp);

			if (!isDir){
			  res = SzArEx_Extract(&db, &lookStream.s, i,
				  &blockIndex, &outBuffer, &outBufferSize,
				  &offset, &outSizeProcessed,
				  &allocImp, &allocTempImp);
			  if (res != SZ_OK){
				bret=false;
				break;
			  }
			}


			CSzFile outFile;
			size_t processedSize;
			size_t j;
			UInt16 *name = (UInt16 *)temp;
			const UInt16 *destPath = (const UInt16 *)name;

			for (j = 0; name[j] != 0; j++){
				if (name[j] == '/'){
					name[j] = 0;
					MyCreateDir(name);
					name[j] = CHAR_PATH_SEPARATOR;
				}
			}

			if (isDir){
				MyCreateDir(destPath);
				continue;
			}else if (OutFile_OpenUtf16(&outFile, destPath)){
				bret=false;
				res = SZ_ERROR_FAIL;
				break;
			}

			processedSize = outSizeProcessed;

			if (File_Write(&outFile, outBuffer + offset, &processedSize) != 0 || processedSize != outSizeProcessed){
				bret=false;
				res = SZ_ERROR_FAIL;
				break;
			}

			if (File_Close(&outFile)){
				bret=false;
				res = SZ_ERROR_FAIL;
				break;
			}

			if (SzBitWithVals_Check(&db.Attribs, i)){
				SetFileAttributesW((LPCWSTR)destPath, db.Attribs.Vals[i]);
			}

		}
		IAlloc_Free(&allocImp, outBuffer);
	}else{
		bret=false;
	}
	SzArEx_Free(&db, &allocImp);
	SzFree(NULL, temp);
	File_Close(&archiveStream.file);
	return bret;
}


bool splitFile(wstring pathcmp){
	bool bret=true;

	//Path del file exe
	wstring pathexe = getExePath();

	//Estrae il file compresso
	HANDLE hFileRead = CreateFileW(pathexe.c_str(),
            GENERIC_READ,
            FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
            NULL,
            OPEN_EXISTING,
            FILE_ATTRIBUTE_NORMAL,
            NULL);

	if (hFileRead != INVALID_HANDLE_VALUE){
		HANDLE hFileWrite = CreateFileW(pathcmp.c_str(),
            GENERIC_WRITE,
            0,
            NULL,
            CREATE_NEW,
            FILE_ATTRIBUTE_NORMAL,
            NULL);

		if (hFileWrite != INVALID_HANDLE_VALUE){
			DWORD dwBytesReaded = 0;
			char ReadBuffer[BUFFERSIZE] = {0};
			DWORD dwBytesWritten = 0;
			DWORD dwBytesToWrite = 0;
			char WriteBuffer[BUFFERSIZE] = {0};
			int psearch=0;
			int lnsearch=strlen(ckeckstartcompressfile);
			bool iscompressfile=false;
			while (true){
				dwBytesToWrite=0;
				if(ReadFile(hFileRead, ReadBuffer, BUFFERSIZE, &dwBytesReaded, NULL) ){
					if (dwBytesReaded==0){
						break;
					}
					for (int i=0;i<=(int)dwBytesReaded-1;i++){
						if (iscompressfile){
							WriteBuffer[dwBytesToWrite]=ReadBuffer[i];
							dwBytesToWrite++;
						}else{
							bool bok=false;
							if (psearch==0){
								if (ReadBuffer[i]=='!'){ //il ! non messo nella string cosi non trova la stringa nell'exe
									bok=true;
								}
							}else if (ReadBuffer[i]==ckeckstartcompressfile[psearch]){
								bok=true;
							}
							if (bok){
								psearch++;
								if (psearch==lnsearch){
									iscompressfile=true;
								}
							}else{
								psearch=0;
							}
						}
					}
					//Scrive file
					if (dwBytesToWrite>0){
						if(!WriteFile(hFileWrite, WriteBuffer, dwBytesToWrite, &dwBytesWritten, NULL)){
							bret=false;
							break;
						}else if (dwBytesWritten != dwBytesToWrite){
							bret=false;
							break;
						}
					}
				}else{
					bret=false;
					break;
				}
			}
			if(bret){
				bret=iscompressfile;
			}
			CloseHandle(hFileWrite);
		}else{
			bret=false;
		}
		CloseHandle(hFileRead);
	}else{
		bret=false;
	}
	return bret;
}

BOOL isWow64(){
    BOOL bIsWow64 = FALSE;

    //IsWow64Process is not available on all supported versions of Windows.
    //Use GetModuleHandle to get a handle to the DLL that contains the function
    //and GetProcAddress to get a pointer to the function if available.

    fnIsWow64Process = (LPFN_ISWOW64PROCESS) GetProcAddress(
        GetModuleHandle(TEXT("kernel32")),"IsWow64Process");

    if(NULL != fnIsWow64Process)  {
        if (!fnIsWow64Process(GetCurrentProcess(),&bIsWow64)) {
            //handle error
        }
    }
    return bIsWow64;
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
        if (wcscmp(FindFileData.cFileName, L".") != 0 && wcscmp(FindFileData.cFileName, L"..") != 0){
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

wchar_t* towchar_t(wstring& str) {
    wchar_t* apps = new wchar_t[str.size() + 1];
	wcscpy(apps, str.c_str());
    return apps;
}

int getRunType(){
	wstring path(L"runasadmin.install");
	if (existsFile(path)){
		return 0; //Install
	}
	wstring path1(L"runasadmin.run");
	if (existsFile(path1)){
		return 1; //Run
	}
	return -1;
}

bool removeRunTypeFile() {
    wstring pathi(L"runasadmin.install");
    DeleteFileW(towchar_t(pathi));
	wstring pathr(L"runasadmin.run");
    DeleteFileW(towchar_t(pathr));
	return true;
}

HANDLE runAsAdmin(){
	SHELLEXECUTEINFOW ShExecInfo = {0};
	ShExecInfo.cbSize = sizeof(SHELLEXECUTEINFOW);
	ShExecInfo.fMask = SEE_MASK_NOCLOSEPROCESS;
	ShExecInfo.hwnd = NULL;
	ShExecInfo.lpVerb  = L"runas";
	wchar_t szPath[MAX_PATH];
	if (GetModuleFileNameW(NULL, szPath, ARRAYSIZE(szPath))){
		ShExecInfo.lpFile = szPath;
		wstring params(L" \"-asadmin=");
		params.append(tmpPath.c_str());
		params.append(L"\\\"");
		for(int i=0; i<=margc-1; i++){
			if ((i>0) && (!argIsAsAdmin(i))){
				params.append(L" \"");
				params.append(margv[i]);
				params.append(L"\"");
			}
		}
		ShExecInfo.lpParameters = params.c_str();
		ShExecInfo.lpDirectory = getBasePath().c_str();
		ShExecInfo.nShow = SW_HIDE;
		ShExecInfo.hInstApp = NULL;
		if (ShellExecuteExW(&ShExecInfo)){
			return ShExecInfo.hProcess;
		}
	}
	return NULL;
}

HANDLE runProcess(int runType){
	SetEnvironmentVariableW(L"PYTHONHOME",L"runtime");

	SHELLEXECUTEINFOW ShExecInfo = {0};
	ShExecInfo.cbSize = sizeof(SHELLEXECUTEINFOW);
	ShExecInfo.fMask = SEE_MASK_NOCLOSEPROCESS;
	ShExecInfo.hwnd = NULL;
	wstring appfile;
	appfile.append(L"runtime");
	appfile.append(L"\\");
	appfile.append(runtimeExe);
	ShExecInfo.lpFile = appfile.c_str();
	wstring params(L" -S -m installer");
	if (runType==0){ //Install
		params.append(L" ");
		params.append(L"gotoopt=install");
	}else if (runType==1){ //Run
		params.append(L" ");
		params.append(L"gotoopt=run");
	}
	for(int i=0; i<=margc-1; i++){
		if ((i>0) && (!argIsAsAdmin(i))){
			params.append(L" \"");
			params.append(margv[i]);
			params.append(L"\"");
		}
	}
	ShExecInfo.lpParameters = params.c_str();
	ShExecInfo.lpDirectory = tmpPath.c_str();
	ShExecInfo.nShow = SW_SHOW;
	ShExecInfo.hInstApp = NULL;
	if (ShellExecuteExW(&ShExecInfo)){
		return ShExecInfo.hProcess;
	}
	return NULL;
}

bool runInstaller(){
	int runType=getRunType(); //0=Install; 1=Run
	while (true){
		removeRunTypeFile();
		HANDLE hProcess=runProcess(runType);
		if (hProcess!=NULL) {
			if (!silent){
				hide(winid);
			}
			WaitForSingleObject(hProcess,INFINITE);
			if (silent){
				return true;
			}
			runType=getRunType();
			if ((!bRunAsAdmin) && (runType!=-1)){
				if (!silent){
					show(winid,0);
					toFront(winid);
					hide(winid);
				}
				bRunAsAdmin=true;
				hProcess=runAsAdmin();
				if (hProcess!=NULL) {
					return true;
				}else{
					bRunAsAdmin=false;
					if (runType==0){ //Install
						runType=-1;
					}
				}
			}else{
				bRunAsAdmin=false;
				return true;
			}
		}else{
			bRunAsAdmin=false;
			return false;
		}
	}
}

void showMessage(LPCWSTR msg){
	if (!silent){
		MessageBoxW(getWindowHWNDByID(winid), msg,  L"", MB_OK|MB_ICONEXCLAMATION);
	}
}

void readInstallConfig(){
	if (existsFile(L"install.json")){
		HANDLE hFile = CreateFileW(L"install.json", GENERIC_READ, 0, NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
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
			int pel = apps.find(L"name");
			if (pel>0){
				int p1 = apps.find(L"\"",pel+5);
				if (p1>0){
					int p2 = apps.find(L"\"",p1+1);
					wstring sname=apps.substr(p1+1, p2-(p1+1));
					transform(sname.begin(), sname.end(), sname.begin(), ::tolower);
					runtimeExe.clear();
					runtimeExe.append(sname);
					runtimeExe.append(L".exe");
				}
			}
		}
	}
}


DWORD WINAPI thread_func(LPVOID lpParameter){
	if (loadTmpPathByArgs()==true){
		bRunAsAdmin=true;
	}else{
		DWORD dwRetVal = 0;
		wchar_t lpTempPathBuffer[MAX_PATH];
		dwRetVal = GetTempPathW(MAX_PATH,lpTempPathBuffer);
		if (dwRetVal > MAX_PATH || (dwRetVal == 0)){
			showMessage(L"Error detect temp directory.");
			if (!silent){
				destroyWindow(winid);
			}
			return 0;
		}
		wchar_t time_buf[21];
		time_t now;
		time(&now);
		wcsftime(time_buf, 21, L"%Y%m%d%H%M%S", gmtime(&now));
		tmpPath.append(lpTempPathBuffer);
		tmpPath.append(getExeName());
		tmpPath.append(time_buf);
		tmpPath.append(L"\\");
	}
	if (bRunAsAdmin){
		SetCurrentDirectoryW(tmpPath.c_str());
		readInstallConfig();
		if (!runInstaller()){
			bRunAsAdmin=false;
			showMessage(L"Error run installer.");
		}
	}else if (CreateDirectoryW(tmpPath.c_str(),NULL)){
		SetCurrentDirectoryW(tmpPath.c_str());
		//Path del file compresso
		wstring pathcmp(L"win.7z");
		if (splitFile(pathcmp)){
			if (decompressFile(pathcmp)){
				if (isWow64()){
					MoveFileExW(L"runtime\\bit64",L"runtime64",1);
					MoveFileExW(L"runtime\\Lib",L"runtime64\\Lib",1);
					deleteDir(L"runtime");
					MoveFileExW(L"runtime64",L"runtime",1);
					MoveFileExW(L"native_win_x86_64",L"native",1);
					deleteDir(L"native_win_x86_32");
				}else{
					deleteDir(L"runtime\\bit64");
					MoveFileExW(L"native_win_x86_32",L"native",1);
					deleteDir(L"native_win_x86_64");
				}
				CopyFileW(L"runtime\\Microsoft.VC90.CRT.manifest",L"runtime\\DLLs\\Microsoft.VC90.CRT.manifest",FALSE);
				CopyFileW(L"runtime\\msvcm90.dll",L"runtime\\DLLs\\msvcm90.dll",FALSE);
				CopyFileW(L"runtime\\msvcp90.dll",L"runtime\\DLLs\\msvcp90.dll",FALSE);
				CopyFileW(L"runtime\\msvcr90.dll",L"runtime\\DLLs\\msvcr90.dll",FALSE);

				readInstallConfig();
				if (runtimeExe.compare(L"dwagent.exe")!=0){
					wstring apps;
					apps.append(L"runtime\\");
					apps.append(runtimeExe);
					MoveFileExW(L"runtime\\dwagent.exe",apps.c_str(),1);
				}
				if (!runInstaller()){
					bRunAsAdmin=false;
					showMessage(L"Error run installer.");
				}
			}else{
				bRunAsAdmin=false;
				showMessage(L"Error decompress file.");
			}
		}else{
			bRunAsAdmin=false;
			showMessage(L"Error split file.");
		}
	}else{
		showMessage(L"Error create temp directory.");
	}
	if (!bRunAsAdmin){
		SetCurrentDirectoryW(getBasePath().c_str());
		deleteDir(tmpPath.c_str());
	}
	if (!silent){
		destroyWindow(winid);
	}


	return 0;
}

void callbackTypeRepaintInstaller(int id, int x,int y,int w, int h){
	//clear background
	penColor(id,255,255,255);
	fillRectangle(id,0,0,winw,winh);

	//draw external rectangle
	int rx=0;
	int rw=winw-1;
	int ry=0;
	int rh=winh-1;
	penColor(id,127,127,127);
	drawLine(id, rx, ry, rx+rw, ry);
	drawLine(id, rx, ry+rh, rx+rw, ry+rh);
	drawLine(id, rx, ry, rx, ry+rh);
	drawLine(id, rx+rw, ry, rx+rw, ry+rh);

	//draw progress
	int pw=(int)((float)(w*percent)/(float)100);
	if (pw>0){
		rw=rx+pw;
		penColor(id,114,159,207);
		fillRectangle(id, rx+1, ry+1, rw-1, rh-1);
	}
}

int wmain(int argc, wchar_t **argv) {
	margc=argc;
	margv=argv;

	for (int i=0; i<argc; i++){
		if (wcscmp(margv[i],L"-silent") == 0){
			silent=true;
			break;
		}
	}
	if (!silent){
		int size[2];
		getScreenSize(size);
		int winx = (size[0] - winw)/2;
		int winy = (size[1] - winh)/2;
		winid = newWindow(WINDOW_TYPE_POPUP, winx, winy, winw, winh, NULL);
		setCallbackRepaint(*callbackTypeRepaintInstaller);
		show(winid,0);
		CreateThread(NULL, 0, thread_func, NULL , 0, 0);
		loop();
	}else{
		HANDLE ht = CreateThread(NULL, 0, thread_func, NULL , 0, 0);
		WaitForSingleObject(ht, INFINITE);
	}
	return 0;
}
