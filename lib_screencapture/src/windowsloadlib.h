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

//USER32 LIB
typedef VOID (WINAPI *ISendSas)(BOOL asUser); 

//WINSTA LIB
typedef BOOL (WINAPI *IWinStationConnectW)(HANDLE server, ULONG connectSessionId,
										   ULONG activeSessionId, PCWSTR password,
										   ULONG unknown); 

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

	//SAS LIB
	bool isAvailableSas();
	ISendSas SendSasFunc();

	//WINSTA LIB
	bool isAvailableWinStation();
	IWinStationConnectW WinStationConnectWFunc();

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

	//SAS LIB
	static HINSTANCE sasdll;	
	static ISendSas sendSasFunc;

	//WINSTA LIB
	static HINSTANCE winstadll;
	static IWinStationConnectW winStationConnectWFunc;


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

#endif /* WINDOWSLOADLIB_H_ */


#endif
