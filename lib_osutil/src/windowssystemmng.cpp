/*
 This Source Code Form is subject to the terms of the Mozilla
 Public License, v. 2.0. If a copy of the MPL was not distributed
 with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
 */
#if defined OS_WINDOWS

#include "systemmng.h"

SystemMng::SystemMng() {
	m_osVerInfo = OSVERSIONINFOEX();
	m_osVerInfo.dwOSVersionInfoSize = sizeof(OSVERSIONINFO);
	if (!GetVersionEx((OSVERSIONINFO*)&m_osVerInfo)) {
		m_osVerInfo.dwOSVersionInfoSize = 0;
	}
}

bool SystemMng::isWinNTFamily() {
	return m_osVerInfo.dwPlatformId == VER_PLATFORM_WIN32_NT;
}

bool SystemMng::isWinXP() {
	return ((m_osVerInfo.dwMajorVersion == 5) && (m_osVerInfo.dwMinorVersion == 1) && isWinNTFamily());
}

bool SystemMng::isWin2003Server() {
	return ((m_osVerInfo.dwMajorVersion == 5) && (m_osVerInfo.dwMinorVersion == 2) && isWinNTFamily());
}

bool SystemMng::isWin2008Server() {
	return ((m_osVerInfo.dwMajorVersion == 6) && ((m_osVerInfo.dwMinorVersion == 0) || (m_osVerInfo.dwMinorVersion == 1)) && m_osVerInfo.wProductType != VER_NT_WORKSTATION);
}

bool SystemMng::isVistaOrLater() {
	return m_osVerInfo.dwMajorVersion >= 6;
}

void SystemMng::appendCpuName(JSONWriter* jsonw) {
	int CPUInfo[4] = {-1};
	__cpuid(CPUInfo, 0x80000000);
	unsigned int nExIds = CPUInfo[0];

	char CPUBrandString[0x40] = {0};
	for( unsigned int i=0x80000000; i<=nExIds; ++i) {
		__cpuid(CPUInfo, i);

		if (i == 0x80000002)
		{
			memcpy( CPUBrandString,
					CPUInfo,
					sizeof(CPUInfo));
		}
		else if( i == 0x80000003 )
		{
			memcpy( CPUBrandString + 16,
					CPUInfo,
					sizeof(CPUInfo));
		}
		else if( i == 0x80000004 )
		{
			memcpy(CPUBrandString + 32, CPUInfo, sizeof(CPUInfo));
		}
	}
	jsonw->addString(L"cpuName",towstring(CPUBrandString));
}

wchar_t* SystemMng::getInfo() {
	JSONWriter jsonw;
	jsonw.beginObject();

	OSVERSIONINFOEX osvi;
	SYSTEM_INFO si;
	PGNSI pGNSI;
	PGPI pGPI;
	BOOL bOsVersionInfoEx;
	DWORD dwType;

	ZeroMemory(&si, sizeof(SYSTEM_INFO));
	ZeroMemory(&osvi, sizeof(OSVERSIONINFOEX));

	osvi.dwOSVersionInfoSize = sizeof(OSVERSIONINFOEX);
	bOsVersionInfoEx = GetVersionEx((OSVERSIONINFO*) &osvi);

	if(bOsVersionInfoEx == FALSE ) {
		jsonw.endObject();
		return towcharp(jsonw.getString());
	}

	pGNSI = (PGNSI) GetProcAddress(GetModuleHandle(TEXT("kernel32.dll")),"GetNativeSystemInfo");
	if(NULL != pGNSI) {
		pGNSI(&si);
	} else {
		GetSystemInfo(&si);
	}

	LONG iMajorVersion=osvi.dwMajorVersion;
	LONG iMinorVersion=osvi.dwMinorVersion;
	if ( VER_PLATFORM_WIN32_NT==osvi.dwPlatformId && iMajorVersion > 4 ) {

		//FIX WIN 10 DETECTION
		typedef LONG (WINAPI* tRtlGetVersion)(RTL_OSVERSIONINFOEXW*);
		HMODULE h_NtDll = GetModuleHandleW(L"ntdll.dll");
		tRtlGetVersion f_RtlGetVersion = (tRtlGetVersion)GetProcAddress(h_NtDll, "RtlGetVersion");
		if (f_RtlGetVersion) {
			RTL_OSVERSIONINFOEXW pk_OsVer;
			ZeroMemory(&pk_OsVer, sizeof(RTL_OSVERSIONINFOEXW));
			pk_OsVer.dwOSVersionInfoSize = sizeof(RTL_OSVERSIONINFOEXW);
			LONG Status = f_RtlGetVersion(&pk_OsVer);
			if (Status == 0) {
				iMajorVersion=pk_OsVer.dwMajorVersion;
				iMinorVersion=pk_OsVer.dwMinorVersion;
			}
		}

		wstring sret;
		sret.append(L"Microsoft ");

		//WINDOWS SERVER 2016 - 10
		if ( iMajorVersion == 10 ) {
			if ( iMinorVersion == 0 ) {
				if( osvi.wProductType == VER_NT_WORKSTATION ) {
					sret.append(L"Windows 10 ");
				} else {
					sret.append(L"Windows Server 2016 ");
				}
			}
		} else if ( iMajorVersion == 6 ) { //WINDOWS SERVER 2008 - SERVER 2012 - 7 - 8
			if ( iMinorVersion == 3 ) {
				if( osvi.wProductType == VER_NT_WORKSTATION ) {
					sret.append(L"Windows 8.1 ");
				} else {
					sret.append(L"Windows Server 2012 R2 ");
				}
			} else if ( iMinorVersion == 2 ) {
				if( osvi.wProductType == VER_NT_WORKSTATION ) {
					sret.append(L"Windows 8 ");
				} else {
					sret.append(L"Windows Server 2012 ");
				}
			} else if ( iMinorVersion == 1 ) {
				if( osvi.wProductType == VER_NT_WORKSTATION ) {
					sret.append(L"Windows 7 ");
				} else {
					sret.append(L"Windows Server 2008 R2 ");
				}
			} else if( iMinorVersion == 0 ) {
				if( osvi.wProductType == VER_NT_WORKSTATION ) {
					sret.append(L"Windows Vista ");
				} else {
					sret.append(L"Windows Server 2008 ");
				}
			}
		}
		if (( iMajorVersion == 6 ) || ( iMajorVersion == 10 )) {
			pGPI = (PGPI) GetProcAddress(GetModuleHandle(TEXT("kernel32.dll")),"GetProductInfo");
			pGPI(iMajorVersion, iMinorVersion, 0, 0, &dwType);
			switch( dwType ) {
				case PRODUCT_ULTIMATE:
				sret.append(L"Ultimate");
				break;
				case PRODUCT_PROFESSIONAL:
				sret.append(L"Professional" );
				break;
				case PRODUCT_HOME_PREMIUM:
				sret.append(L"Home Premium");
				break;
				case PRODUCT_HOME_BASIC:
				sret.append(L"Home Basic");
				break;
				case PRODUCT_ENTERPRISE:
				sret.append(L"Enterprise");
				break;
				case PRODUCT_BUSINESS:
				sret.append(L"Business");
				break;
				case PRODUCT_STARTER:
				sret.append(L"Starter");
				break;
				case PRODUCT_CLUSTER_SERVER:
				sret.append(L"Cluster Server");
				break;
				case PRODUCT_DATACENTER_SERVER:
				sret.append(L"Datacenter");
				break;
				case PRODUCT_DATACENTER_SERVER_CORE:
				sret.append(L"Datacenter (core installation)");
				break;
				case PRODUCT_ENTERPRISE_SERVER:
				sret.append(L"Enterprise");
				break;
				case PRODUCT_ENTERPRISE_SERVER_CORE:
				sret.append(L"Enterprise (core installation)");
				break;
				case PRODUCT_ENTERPRISE_SERVER_IA64:
				sret.append(L"Enterprise for Itanium-based Systems");
				break;
				case PRODUCT_SMALLBUSINESS_SERVER:
				sret.append(L"Small Business Server");
				break;
				case PRODUCT_SMALLBUSINESS_SERVER_PREMIUM:
				sret.append(L"Small Business Server Premium");
				break;
				case PRODUCT_STANDARD_SERVER:
				sret.append(L"Standard");
				break;
				case PRODUCT_STANDARD_SERVER_CORE:
				sret.append(L"Standard (core installation)");
				break;
				case PRODUCT_WEB_SERVER:
				sret.append(L"Web Server");
				break;
				case PRODUCT_CORE:
				sret.append(L"Home");
				break;
			}
		} else if ( iMajorVersion == 5 && iMinorVersion == 2 ) { //WINDOWS SERVER 2003 - HOME SERVER - AND XP 64
			if( GetSystemMetrics(SM_SERVERR2) ) {
				sret.append( L"Windows Server 2003 R2, ");
			} else if ( osvi.wSuiteMask & VER_SUITE_STORAGE_SERVER ) {
				sret.append( L"Windows Storage Server 2003");
			} else if ( osvi.wSuiteMask & VER_SUITE_WH_SERVER ) {
				sret.append( L"Windows Home Server");
			} else if( osvi.wProductType == VER_NT_WORKSTATION &&
					si.wProcessorArchitecture==PROCESSOR_ARCHITECTURE_AMD64) {
				sret.append( L"Windows XP Professional x64");
			} else {
				sret.append(L"Windows Server 2003, ");
			}
			if ( osvi.wProductType != VER_NT_WORKSTATION ) {
				if ( si.wProcessorArchitecture==PROCESSOR_ARCHITECTURE_IA64 ) {
					if( osvi.wSuiteMask & VER_SUITE_DATACENTER )
					sret.append( L"Datacenter for Itanium-based Systems");
					else if( osvi.wSuiteMask & VER_SUITE_ENTERPRISE )
					sret.append( L"Enterprise for Itanium-based Systems");
				} else if ( si.wProcessorArchitecture==PROCESSOR_ARCHITECTURE_AMD64 ) {
					if( osvi.wSuiteMask & VER_SUITE_DATACENTER )
					sret.append( L"Datacenter x64");
					else if( osvi.wSuiteMask & VER_SUITE_ENTERPRISE )
					sret.append( L"Enterprise x64");
					else sret.append( L"Standard x64");
				} else {
					if ( osvi.wSuiteMask & VER_SUITE_COMPUTE_SERVER )
					sret.append( L"Compute Cluster");
					else if( osvi.wSuiteMask & VER_SUITE_DATACENTER )
					sret.append( L"Datacenter");
					else if( osvi.wSuiteMask & VER_SUITE_ENTERPRISE )
					sret.append( L"Enterprise");
					else if ( osvi.wSuiteMask & VER_SUITE_BLADE )
					sret.append( L"Web");
					else sret.append( L"Standard");
				}
			}
		} else if ( iMajorVersion == 5 && iMinorVersion == 1 ) { //WINDOWS XP
			sret.append(L"Windows XP ");
			if( osvi.wSuiteMask & VER_SUITE_PERSONAL ) {
				sret.append( L"Home");
			} else {
				sret.append( L"Professional");
			}
		} else if ( iMajorVersion == 5 && iMinorVersion == 0 ) { //WINDOWS 2000
			sret.append(L"Windows 2000 ");
			if ( osvi.wProductType == VER_NT_WORKSTATION ) {
				sret.append( L"Professional");
			} else {
				if( osvi.wSuiteMask & VER_SUITE_DATACENTER )
				sret.append( L"Datacenter Server");
				else if( osvi.wSuiteMask & VER_SUITE_ENTERPRISE )
				sret.append( L"Advanced Server");
				else sret.append( L"Server");
			}
		}
		jsonw.addString(L"osName",sret);

		// Include service pack (if any) and build number.
		sret.clear();
		if( _tcslen(osvi.szCSDVersion) > 0 ) {
			sret.append(towstring(osvi.szCSDVersion));
		}
		jsonw.addString(L"osUpdate",sret);
		jsonw.addNumber(L"osBuild",osvi.dwBuildNumber);

		//PCNAME
		sret.clear();
		char hname[255];
		DWORD szhname = sizeof ( hname );
		if (GetComputerName(hname, &szhname )) {
			sret.append(towstring(hname));
		}
		jsonw.addString(L"pcName",sret);

		//CPU
		appendCpuName(&jsonw);


		//architecture
		sret.clear();
		if ( si.wProcessorArchitecture==0) {
			sret.append( L"x86");
		} else if ( si.wProcessorArchitecture==1) {
			sret.append(L"MIPS");
		} else if ( si.wProcessorArchitecture==2) {
			sret.append(L"Alpha");
		} else if ( si.wProcessorArchitecture==3) {
			sret.append(L"PowerPC");
		} else if ( si.wProcessorArchitecture==6) {
			sret.append(L"Intel Itanium-based");
		} else if ( si.wProcessorArchitecture==9) {
			sret.append(L"x64");
		} else {
			sret.append(L"Unknown");
		}
		jsonw.addString(L"cpuArchitecture",sret);

	}

	jsonw.endObject();
	return towcharp(jsonw.getString());

}

#endif
