/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/
#if defined OS_WINDOWS

#include "windowsloadlib.h"

int WindowsLoadLib::countinstance = 0;

//WTS LIB
HINSTANCE WindowsLoadLib::wtsdll=NULL;
IWTSQueryUserToken WindowsLoadLib::wtsQueryUserTokenFunc=NULL;
IWTSRegisterSessionNotification WindowsLoadLib::wtsRegisterSessionNotificationFunc=NULL;
IWTSUnRegisterSessionNotification WindowsLoadLib::wtsUnRegisterSessionNotificationFunc=NULL;

//SHCORE LIB
HINSTANCE WindowsLoadLib::shcoredll=NULL;
ISetProcessDpiAwareness WindowsLoadLib::setProcessDpiAwarenessFunc=NULL;

//USER32 LIB
HINSTANCE WindowsLoadLib::user32dll=NULL;
ISetProcessDPIAware WindowsLoadLib::setProcessDPIAwareFunc=NULL;

//SAS LIB
HINSTANCE WindowsLoadLib::sasdll;
ISendSas WindowsLoadLib::sendSasFunc=NULL;

//WINSTA LIB
HINSTANCE WindowsLoadLib::winstadll=NULL;
IWinStationConnectW WindowsLoadLib::winStationConnectWFunc=NULL;


WindowsLoadLib::WindowsLoadLib(){
	if (WindowsLoadLib::countinstance==0){
		
		//WTS LIB
		WindowsLoadLib::wtsdll=LoadLibrary("Wtsapi32.dll");
		if (WindowsLoadLib::wtsdll){
			WindowsLoadLib::wtsQueryUserTokenFunc = (IWTSQueryUserToken)GetProcAddress(wtsdll, "WTSQueryUserToken");
			WindowsLoadLib::wtsRegisterSessionNotificationFunc = (IWTSRegisterSessionNotification)GetProcAddress(wtsdll, "WTSRegisterSessionNotification");
			WindowsLoadLib::wtsUnRegisterSessionNotificationFunc = (IWTSUnRegisterSessionNotification)GetProcAddress(wtsdll, "WTSUnRegisterSessionNotification");
		}

		//SHCORE LIB
		WindowsLoadLib::shcoredll = LoadLibrary("Shcore.dll");
		if (WindowsLoadLib::shcoredll) {
			WindowsLoadLib::setProcessDpiAwarenessFunc = (ISetProcessDpiAwareness)GetProcAddress(shcoredll, "SetProcessDpiAwareness");
		}

		//USER32 LIB
		WindowsLoadLib::user32dll = LoadLibrary("User32.dll");
		if (WindowsLoadLib::user32dll){
			WindowsLoadLib::setProcessDPIAwareFunc = (ISetProcessDPIAware)GetProcAddress(user32dll, "SetProcessDPIAware");
		}

		//SAS LIB
		WindowsLoadLib::sasdll = LoadLibrary("sas.dll");
		if (WindowsLoadLib::sasdll){
			WindowsLoadLib::sendSasFunc = (ISendSas)GetProcAddress(sasdll, "SendSAS");
		}else{
			WindowsLoadLib::sasdll = LoadLibrary("native\\sas.dll");
			if (WindowsLoadLib::sasdll){
				WindowsLoadLib::sendSasFunc = (ISendSas)GetProcAddress(sasdll, "SendSAS");
			}
		}
				
		//WINSTA LIB
		WindowsLoadLib::winstadll = LoadLibrary("winsta.dll");
		if (WindowsLoadLib::winstadll){
			WindowsLoadLib::winStationConnectWFunc = (IWinStationConnectW)GetProcAddress(winstadll, "WinStationConnectW");
		}

		/*dmwdll = LoadLibrary("dwmapi.dll"); 
		if (dmwdll){
			dwmIsCompositionEnabled = (IDwmIsCompositionEnabled)GetProcAddress(dmwdll, "DwmIsCompositionEnabled");
			dwmGetColorizationParameters = (IDwmGetColorizationParameters)GetProcAddress(dmwdll, (LPCSTR)127);
			dwmSetColorizationParameters = (IDwmSetColorizationParameters)GetProcAddress(dmwdll, (LPCSTR)131);
		}*/

	}
	WindowsLoadLib::countinstance++;
}

WindowsLoadLib::~WindowsLoadLib(){
	WindowsLoadLib::countinstance--;
	if (WindowsLoadLib::countinstance==0){
		if (WindowsLoadLib::wtsdll){
			FreeLibrary(WindowsLoadLib::wtsdll);
			WindowsLoadLib::wtsdll=NULL;
		}

		if (WindowsLoadLib::shcoredll){
			FreeLibrary(WindowsLoadLib::shcoredll);
			WindowsLoadLib::shcoredll=NULL;
		}

		if (WindowsLoadLib::user32dll){
			FreeLibrary(WindowsLoadLib::user32dll);
			WindowsLoadLib::user32dll=NULL;
		}

		if (WindowsLoadLib::sasdll){
			FreeLibrary(WindowsLoadLib::sasdll);
			WindowsLoadLib::sasdll=NULL;
		}

		if (WindowsLoadLib::winstadll){
			FreeLibrary(WindowsLoadLib::winstadll);
			WindowsLoadLib::winstadll=NULL;
		}

		/*if (dmwdll){
			FreeLibrary(dmwdll);
			dmwdll=NULL;
		}*/
	}
}

//WTS LIB
bool WindowsLoadLib::isAvailableWTS(){
	return WindowsLoadLib::wtsdll!=NULL;
}

IWTSQueryUserToken WindowsLoadLib::WTSQueryUserTokenFunc(){
	return WindowsLoadLib::wtsQueryUserTokenFunc;
}

IWTSRegisterSessionNotification WindowsLoadLib::WTSRegisterSessionNotificationFunc(){
	return WindowsLoadLib::wtsRegisterSessionNotificationFunc;
}

IWTSUnRegisterSessionNotification WindowsLoadLib::WTSUnRegisterSessionNotificationFunc(){
	return WindowsLoadLib::wtsUnRegisterSessionNotificationFunc;
}

//SHCORE LIB
bool WindowsLoadLib::isAvailableShCore(){
	return WindowsLoadLib::shcoredll!=NULL;
}
	
ISetProcessDpiAwareness WindowsLoadLib::SetProcessDpiAwarenessFunc(){
	return WindowsLoadLib::setProcessDpiAwarenessFunc;
}

//USER32 LIB
bool WindowsLoadLib::isAvailableUser32(){
	return WindowsLoadLib::user32dll!=NULL;
}

ISetProcessDPIAware WindowsLoadLib::SetProcessDPIAwareFunc(){
	return WindowsLoadLib::setProcessDPIAwareFunc;
}

//SAS LIB
bool WindowsLoadLib::isAvailableSas(){
	return WindowsLoadLib::sasdll!=NULL;
}

ISendSas WindowsLoadLib::SendSasFunc(){
	return WindowsLoadLib::sendSasFunc;
}

//WINSTA LIB
bool WindowsLoadLib::isAvailableWinStation(){
	return WindowsLoadLib::winstadll!=NULL;
}

IWinStationConnectW WindowsLoadLib::WinStationConnectWFunc(){
	return WindowsLoadLib::winStationConnectWFunc;
}

#endif
