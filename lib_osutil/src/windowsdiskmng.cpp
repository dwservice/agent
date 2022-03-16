/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/
#if defined OS_WINDOWS

#include "diskmng.h"


DiskMng::DiskMng(){

}

 int DiskMng::getInfo(wchar_t** sret) {
	JSONWriter jsonw;
	jsonw.beginArray();

	TCHAR szDrive[] = _T(" A:");
	DWORD uDriveMask = GetLogicalDrives();
	if(uDriveMask != 0){
		while(uDriveMask){
			if(uDriveMask & 1){
				jsonw.beginObject();

				wstring wsd = towstring(szDrive);
				trimAll(wsd);
				jsonw.addString(L"Name", wsd);
				ULARGE_INTEGER freeBytesAvailable, totalNumberOfBytes,totalNumberOfFreeBytes;
				BOOL bResult = GetDiskFreeSpaceExW(wsd.c_str(),(PULARGE_INTEGER)&freeBytesAvailable,(PULARGE_INTEGER)&totalNumberOfBytes,(PULARGE_INTEGER) &totalNumberOfFreeBytes);
				if(bResult){
					//jsonw.addNumber(L"", freeBytesAvailable.QuadPart);
					jsonw.addNumber(L"Size", totalNumberOfBytes.QuadPart);
					jsonw.addNumber(L"Free", totalNumberOfFreeBytes.QuadPart);
				}else{
					//jsonw.addNumber(L"", 0);
					jsonw.addNumber(L"Size", 0);
					jsonw.addNumber(L"Free", 0);
				}

				jsonw.endObject();
			}
			//printf("%S ", (const char *)szDrive);
			++szDrive[1];
			uDriveMask >>= 1;
		}
	}

	jsonw.endArray();
	wstring str=jsonw.getString();
	*sret=towcharp(str);
	return str.length();
}


int DiskMng::isFileJunction(wchar_t* path){
	BOOL result = FALSE;
	HANDLE fileHandle;
	fileHandle = CreateFileW(path, 0, FILE_SHARE_READ | FILE_SHARE_WRITE, NULL, OPEN_EXISTING, FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT, NULL);
	if (fileHandle != INVALID_HANDLE_VALUE)	{
		char Tmp[MAXIMUM_REPARSE_DATA_BUFFER_SIZE] = {0};
		REPARSE_DATA_BUFFER& reparseData = *(REPARSE_DATA_BUFFER*)Tmp;
		DWORD bytesRet;
		if (DeviceIoControl(fileHandle, FSCTL_GET_REPARSE_POINT, NULL, 0, &reparseData, sizeof(Tmp), &bytesRet, NULL)){
			result = reparseData.ReparseTag == IO_REPARSE_TAG_MOUNT_POINT;
		}
		CloseHandle(fileHandle);
	}
	if (result==TRUE){
		return 1;
	}
	return 0;
}

#endif
