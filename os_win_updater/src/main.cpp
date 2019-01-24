/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/

#include "main.h"

using namespace std;

wstring workPath = L"";

CallbackType g_callback_wlog = NULL;

wchar_t* towchar_t(wstring& str) {
    wchar_t* apps = new wchar_t[str.size() + 1];
	wcscpy(apps, str.c_str());
    return apps;
}

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

void WriteToLog(const wchar_t* str) {
	if (g_callback_wlog!=NULL){
		g_callback_wlog(str);
	}
}

bool compareFile(wchar_t* fn1,wchar_t* fn2) {
	int BUFFERSIZE=1024*16;
	HANDLE hFile1;
	DWORD  dwBytesRead1 = 0;
	char ReadBuffer1[1024*16];
	HANDLE hFile2;
	DWORD  dwBytesRead2 = 0;
	char ReadBuffer2[1024*16];

	hFile1 = CreateFileW(fn1,
					   GENERIC_READ,
					   FILE_SHARE_READ,
					   NULL,
					   OPEN_EXISTING,
					   FILE_ATTRIBUTE_NORMAL,
					   NULL);
	if (hFile1 == INVALID_HANDLE_VALUE) {
		return false;
	}
	hFile2 = CreateFileW(fn2,
						   GENERIC_READ,
						   FILE_SHARE_READ,
						   NULL,
						   OPEN_EXISTING,
						   FILE_ATTRIBUTE_NORMAL,
						   NULL);
	if (hFile2 == INVALID_HANDLE_VALUE) {
		CloseHandle(hFile1);
		return false;
	}
	bool bret = true;
	while(true){
		if(ReadFile(hFile1, ReadBuffer1, BUFFERSIZE, &dwBytesRead1, NULL)==FALSE){
			bret = false;
			break;
		}
		if(ReadFile(hFile2, ReadBuffer2, BUFFERSIZE, &dwBytesRead2, NULL)==FALSE){
			bret = false;
			break;
		}
		if ((dwBytesRead1 == 0) && (dwBytesRead2 == 0)){
			bret = true;
			break;
		}
		if ((dwBytesRead1 != dwBytesRead2) || dwBytesRead1==0 || dwBytesRead2==0){
			bret = false;
			break;
		}else{
			for (int i=0;i<dwBytesRead1;i++){
				if (strcmp(&ReadBuffer1[i],&ReadBuffer2[i])!=0){
					bret = false;
					break;
				}
			}
		}
	}
	CloseHandle(hFile1);
	CloseHandle(hFile2);
	return bret;
}

bool existsFile(wstring fileName) {
	return GetFileAttributesW(fileName.c_str())!=INVALID_FILE_ATTRIBUTES;
}


BOOL existsDir(wstring file){
	DWORD returnvalue;
	returnvalue = GetFileAttributesW(file.c_str());
	if(returnvalue == ((DWORD)-1)){
		return false;
	}
	else{
		return true;
	}
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

bool updateFiles(wstring dsub){
	bool bret=true;
	wstring dwkr=workPath;
	wstring dupd=workPath;
	dupd.append(L"\\update");
	WIN32_FIND_DATAW FindFileData;
    HANDLE hFind;
    DWORD Attributes;
    wchar_t strupd[MAX_PATH];
	wchar_t strwkr[MAX_PATH];
	wcscpy(strupd,dupd.c_str());
	if (wcscmp(dsub.c_str(),L"")!=0){;
		wcscat(strupd,L"\\");
		wcscat(strupd,dsub.c_str());
	}
    wcscat(strupd,L"\\*.*");
    hFind = FindFirstFileW(strupd, &FindFileData);
    do{
        if (wcscmp(FindFileData.cFileName, L".") != 0 && wcscmp(FindFileData.cFileName, L"..") != 0){
			wcscpy(strwkr, dwkr.c_str());
			if (wcscmp(dsub.c_str(),L"")!=0){
				wcscat(strwkr,L"\\");
				wcscat(strwkr,dsub.c_str());
			}
            wcscat(strwkr,L"\\");
            wcscat(strwkr,FindFileData.cFileName);

            wcscpy(strupd, dupd.c_str());
			if (wcscmp(dsub.c_str(),L"")!=0){
				wcscat(strupd,L"\\");
				wcscat(strupd,dsub.c_str());
			}
            wcscat(strupd,L"\\");
            wcscat(strupd,FindFileData.cFileName);

	        Attributes = GetFileAttributesW(strupd);
			if ((Attributes & FILE_ATTRIBUTE_DIRECTORY)){
				if (!existsDir(strwkr)){
					CreateDirectoryW(strwkr,NULL);
				}
				wstring dsubapp;
				if (wcscmp(dsub.c_str(),L"")!=0){;
					dsubapp.append(dsub);
					dsubapp.append(L"\\");
				}
				dsubapp.append(FindFileData.cFileName);
				if (!updateFiles(dsubapp)){
					bret=false;
				}
            }else{
				if (existsFile(strwkr)){
					if (!DeleteFileW(strwkr)){
						wchar_t strmsg[1000];
						wcscpy(strmsg, L"ERROR:Coping file ");
						wcscat(strmsg, strupd);
						wcscat(strmsg, L" .");
						WriteToLog(strmsg);
						bret=false;
					}
				}
				if (!existsFile(strwkr)){
					if ((CopyFileW(strupd,strwkr,TRUE)!=0) && (compareFile(strupd,strwkr))){
						wchar_t strmsg[1000];
						wcscpy(strmsg, L"Copied file ");
						wcscat(strmsg, strupd);
						wcscat(strmsg, L" .");
						WriteToLog(strmsg);
						DeleteFileW(strupd);
					}else{
						wchar_t strmsg[1000];
						wcscpy(strmsg, L"ERROR:Coping file ");
						wcscat(strmsg, strupd);
						wcscat(strmsg, L" .");
						WriteToLog(strmsg);
						bret=false;
					}
				}
			}
        }
    }while(FindNextFileW(hFind, &FindFileData));
    FindClose(hFind);
    return bret;
}

void setCallbackWriteLog(CallbackType callback){
	g_callback_wlog=callback;
}

bool checkUpdate(){
	workPath=getDWAgentPath();
	wstring dupd=workPath;
	dupd.append(L"\\update");
	if(existsDir(dupd)){
		if (updateFiles(L"")){
			return deleteDir(dupd.c_str());
		}else{
			return false;
		}
    }
	return true;
}

int main(int argc, char** argv ){
	return 0;
}
