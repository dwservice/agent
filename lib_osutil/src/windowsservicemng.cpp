
/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/
#if defined OS_WINDOWS

#include "servicemng.h"

ServiceMng::ServiceMng(){

}

wchar_t* ServiceMng::getServiceList() {
	JSONWriter jsonw;
	jsonw.beginArray();

    SC_HANDLE hHandle = OpenSCManager(NULL, NULL, SC_MANAGER_ALL_ACCESS);
    if (NULL != hHandle) {
		ENUM_SERVICE_STATUS service;
		DWORD dwBytesNeeded = 0;
		DWORD dwServicesReturned = 0;
		DWORD dwResumedHandle = 0;
		DWORD dwServiceType = SERVICE_WIN32 | SERVICE_DRIVER;
		BOOL retVal = EnumServicesStatus(hHandle, dwServiceType, SERVICE_STATE_ALL,
			&service, sizeof(ENUM_SERVICE_STATUS), &dwBytesNeeded, &dwServicesReturned,
			&dwResumedHandle);
		if (!retVal) {
			if (ERROR_MORE_DATA == GetLastError()) {
				DWORD dwBytes = sizeof(ENUM_SERVICE_STATUS) + dwBytesNeeded;
				ENUM_SERVICE_STATUS* pServices = NULL;
				pServices = new ENUM_SERVICE_STATUS [dwBytes];
				EnumServicesStatus(hHandle, SERVICE_WIN32 | SERVICE_DRIVER, SERVICE_STATE_ALL,
					pServices, dwBytes, &dwBytesNeeded, &dwServicesReturned, &dwResumedHandle);
				for (unsigned iIndex = 0; iIndex < dwServicesReturned; iIndex++) {

					if ((pServices + iIndex)->ServiceStatus.dwServiceType>=10){
						jsonw.beginObject();
						jsonw.addString(L"Name", towstring((pServices + iIndex)->lpServiceName));
						jsonw.addString(L"Label", towstring((pServices + iIndex)->lpDisplayName));
						jsonw.addNumber(L"Status", (pServices + iIndex)->ServiceStatus.dwCurrentState);
						jsonw.endObject();
					}
				}
				delete [] pServices;
				pServices = NULL;
			}
		}
		CloseServiceHandle(hHandle);
	}

    jsonw.endArray();
	return towcharp(jsonw.getString());
}

bool ServiceMng::checkStateService(SC_HANDLE schService,DWORD state){
	SERVICE_STATUS_PROCESS ssp;
    DWORD dwBytesNeeded;
    BOOL bok = QueryServiceStatusEx(
            schService,
            SC_STATUS_PROCESS_INFO,
            (LPBYTE) & ssp,
            sizeof (SERVICE_STATUS_PROCESS),
            &dwBytesNeeded);
    if (bok) {
        if (ssp.dwCurrentState == state) {
            return true;
        }
    }
    return false;
}


bool ServiceMng::waitStateService(SC_HANDLE schService,DWORD state){
	int cnt = 0;
    while (cnt <= 30) {
        Sleep(2000);
        SERVICE_STATUS_PROCESS ssp;
        DWORD dwBytesNeeded;
        BOOL bok = QueryServiceStatusEx(
                schService,
                SC_STATUS_PROCESS_INFO,
                (LPBYTE) & ssp,
                sizeof (SERVICE_STATUS_PROCESS),
                &dwBytesNeeded);
        if (bok) {
            if (ssp.dwCurrentState == state) {
                return true;
            }
        } else {
            return false;
        }
        cnt++;
    }
    return false;
}

int ServiceMng::startService(wchar_t* serviceName) {
	bool bret=false;
    SC_HANDLE schSCManager = OpenSCManager(NULL, NULL, SC_MANAGER_CONNECT);
	SC_HANDLE schService = OpenServiceW(schSCManager, serviceName, SERVICE_START | SERVICE_QUERY_STATUS |  SERVICE_ENUMERATE_DEPENDENTS);
	if (checkStateService(schService, SERVICE_STOPPED)){
		BOOL bok = StartService(schService, 0, NULL);
		if (bok) {
			bret = waitStateService(schService, SERVICE_RUNNING);
		}
	}
    CloseServiceHandle(schService);
    CloseServiceHandle(schSCManager);
	if (bret){
		return 1;
	}
	return 0;
}

int ServiceMng::stopService(wchar_t* serviceName) {
	bool bret=false;
    SC_HANDLE schSCManager = OpenSCManager(NULL, NULL, SC_MANAGER_CONNECT);
    SC_HANDLE schService = OpenServiceW(schSCManager, serviceName, SERVICE_STOP | SERVICE_QUERY_STATUS |  SERVICE_ENUMERATE_DEPENDENTS);
    if (checkStateService(schService, SERVICE_RUNNING)){
		SERVICE_STATUS ssStatus;
		BOOL bok = ControlService(schService, SERVICE_CONTROL_STOP, &ssStatus);
		if (bok) {
			bret = waitStateService(schService, SERVICE_STOPPED);
		}
	}
	CloseServiceHandle(schService);
    CloseServiceHandle(schSCManager);
    if (bret){
		return 1;
	}
	return 0;
}

int ServiceMng::statusService(wchar_t* serviceName) {
    SC_HANDLE schSCManager = OpenSCManager(NULL, NULL, SC_MANAGER_ALL_ACCESS);
    SC_HANDLE schService = OpenServiceW(schSCManager, serviceName, SC_MANAGER_ALL_ACCESS);
    SERVICE_STATUS_PROCESS ssp;
    DWORD dwBytesNeeded;
    BOOL bok = QueryServiceStatusEx(
            schService,
            SC_STATUS_PROCESS_INFO,
            (LPBYTE) & ssp,
            sizeof (SERVICE_STATUS_PROCESS),
            &dwBytesNeeded);
    CloseServiceHandle(schService);
    CloseServiceHandle(schSCManager);
    if (bok) {
        if (ssp.dwCurrentState == SERVICE_STOPPED) {
            return 1;
		} else if (ssp.dwCurrentState == SERVICE_START_PENDING) {
			return 2;
		} else if (ssp.dwCurrentState == SERVICE_STOP_PENDING) {
			return 3;
		} else if (ssp.dwCurrentState == SERVICE_RUNNING) {
			return 4;
		} else if (ssp.dwCurrentState == SERVICE_CONTINUE_PENDING) {
			return 5;
		} else if (ssp.dwCurrentState == SERVICE_PAUSE_PENDING) {
			return 6;
		} else if (ssp.dwCurrentState == SERVICE_PAUSED) {
			return 7;
		} else {
            return -1;
        }
    } else {
        return -1;
    }
}

#endif
