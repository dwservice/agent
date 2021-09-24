/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/
#if defined OS_WINDOWS

using namespace std;
/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/

#include <windows.h>

#ifndef WINDOWSLOADLIB_H_
#define WINDOWSLOADLIB_H_

//WTS LIB
typedef BOOL (WINAPI *IWTSQueryUserToken)(ULONG SessionId, PHANDLE phToken); 
typedef BOOL (WINAPI *IWTSRegisterSessionNotification)(HWND, DWORD);
typedef BOOL (WINAPI *IWTSUnRegisterSessionNotification)(HWND);

//SHCORE LIB
typedef VOID (WINAPI *ISetProcessDpiAwareness )(int v);

//USER32 LIB
typedef VOID (WINAPI *ISetProcessDPIAware)();
typedef BOOL (WINAPI *IGetWindowDisplayAffinity)(HWND, DWORD*);
typedef BOOL (WINAPI *ISetWindowDisplayAffinity)(HWND, DWORD);

//USER32 LIB
typedef VOID (WINAPI *ISendSas)(BOOL asUser); 

//WINSTA LIB
typedef BOOL (WINAPI *IWinStationConnectW)(HANDLE server, ULONG connectSessionId,ULONG activeSessionId, PCWSTR password, ULONG unknown);

//DXVA2 LIB LIB
static const int PHYSICAL_MONITOR_DESCRIPTION_SIZE = 128;
typedef struct _PHYSICAL_MONITOR {
  HANDLE hPhysicalMonitor;
  WCHAR  szPhysicalMonitorDescription[PHYSICAL_MONITOR_DESCRIPTION_SIZE];
} PHYSICAL_MONITOR, *LPPHYSICAL_MONITOR;
typedef enum _MC_VCP_CODE_TYPE {
  MC_MOMENTARY,
  MC_SET_PARAMETER
} MC_VCP_CODE_TYPE, *LPMC_VCP_CODE_TYPE;
typedef BOOL (WINAPI *IGetNumberOfPhysicalMonitorsFromHMONITOR)(HMONITOR hMonitor,LPDWORD  pdwNumberOfPhysicalMonitors);
typedef BOOL (WINAPI *IGetPhysicalMonitorsFromHMONITOR)(HMONITOR hMonitor, DWORD dwPhysicalMonitorArraySize, LPPHYSICAL_MONITOR pPhysicalMonitorArray);
typedef BOOL (WINAPI *ISetVCPFeature)(HANDLE hMonitor, BYTE bVCPCode, DWORD dwNewValue);
typedef BOOL (WINAPI *IGetVCPFeatureAndVCPFeatureReply)(HANDLE hMonitor, BYTE bVCPCode, LPMC_VCP_CODE_TYPE pvct, LPDWORD pdwCurrentValue, LPDWORD pdwMaximumValue);

class WindowsLoadLib{

public:
	WindowsLoadLib();
    ~WindowsLoadLib( void );

	//WTS LIB
	bool isAvailableWTS();
	IWTSQueryUserToken WTSQueryUserTokenFunc();
	IWTSRegisterSessionNotification WTSRegisterSessionNotificationFunc();
	IWTSUnRegisterSessionNotification WTSUnRegisterSessionNotificationFunc();
	
	//SHCORE LIB
	bool isAvailableShCore();
	ISetProcessDpiAwareness SetProcessDpiAwarenessFunc();

	//USER32 LIB
	bool isAvailableUser32();
	ISetProcessDPIAware SetProcessDPIAwareFunc();
	IGetWindowDisplayAffinity GetWindowDisplayAffinityFunc();
	ISetWindowDisplayAffinity SetWindowDisplayAffinityFunc();

	//SAS LIB
	bool isAvailableSas();
	ISendSas SendSasFunc();

	//WINSTA LIB
	bool isAvailableWinStation();
	IWinStationConnectW WinStationConnectWFunc();

	//DXVA2 LIB
	bool isAvailableDxva2();
	IGetNumberOfPhysicalMonitorsFromHMONITOR GetNumberOfPhysicalMonitorsFromHMONITORFunc();
	IGetPhysicalMonitorsFromHMONITOR GetPhysicalMonitorsFromHMONITORFunc();
	ISetVCPFeature SetVCPFeatureFunc();
	IGetVCPFeatureAndVCPFeatureReply GetVCPFeatureAndVCPFeatureReplyFunc();

private:
	static int countinstance;

	//WTS LIB
	static HINSTANCE wtsdll; 
	static IWTSQueryUserToken wtsQueryUserTokenFunc;
	static IWTSRegisterSessionNotification wtsRegisterSessionNotificationFunc;
	static IWTSUnRegisterSessionNotification wtsUnRegisterSessionNotificationFunc;

	//SHCORE LIB
	static HINSTANCE shcoredll;
	static ISetProcessDpiAwareness setProcessDpiAwarenessFunc;

	//USER32 LIB
	static HINSTANCE user32dll;
	static ISetProcessDPIAware setProcessDPIAwareFunc;
	static IGetWindowDisplayAffinity getWindowDisplayAffinityFunc;
	static ISetWindowDisplayAffinity setWindowDisplayAffinityFunc;

	//SAS LIB
	static HINSTANCE sasdll;	
	static ISendSas sendSasFunc;

	//WINSTA LIB
	static HINSTANCE winstadll;
	static IWinStationConnectW winStationConnectWFunc;

	//DXVA2 LIB
	static HINSTANCE dxva2dll;
	static IGetNumberOfPhysicalMonitorsFromHMONITOR getNumberOfPhysicalMonitorsFromHMONITORFunc;
	static IGetPhysicalMonitorsFromHMONITOR getPhysicalMonitorsFromHMONITORFunc;
	static ISetVCPFeature setVCPFeatureFunc;
	static IGetVCPFeatureAndVCPFeatureReply getVCPFeatureAndVCPFeatureReplyFunc;

	//EXTERNAL
	
	/*typedef struct DWMCOLORIZATIONPARAMS{
		COLORREF         clrColor;   
		COLORREF         clrAftGlow;
		UINT             nIntensity;
		UINT             clrAftGlowBal;
		UINT		 clrBlurBal;       
		UINT		 clrGlassReflInt;  
		BOOL             fOpaque;
	}DWMColor;

	HINSTANCE dmwdll;
	typedef HRESULT (WINAPI *IDwmIsCompositionEnabled)(BOOL *pfEnabled);
	IDwmIsCompositionEnabled dwmIsCompositionEnabled;
	typedef HRESULT (WINAPI *IDwmGetColorizationParameters)(DWMCOLORIZATIONPARAMS *colorparam);
	IDwmGetColorizationParameters dwmGetColorizationParameters;
	typedef HRESULT (WINAPI *IDwmSetColorizationParameters)(DWMCOLORIZATIONPARAMS *colorparam, UINT unknown);
	IDwmSetColorizationParameters dwmSetColorizationParameters;*/

};

//TMP PRIVACY MODE
void WindowsLoadLibSetPrivacyMode(bool b);

#endif /* WINDOWSLOADLIB_H_ */


#endif
