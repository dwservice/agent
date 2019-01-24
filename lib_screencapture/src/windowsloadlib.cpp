/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/
#if defined OS_WINDOWS

#include "windowsloadlib.h"

int LoadLib::countinstance = 0;

//WTS LIB
HINSTANCE LoadLib::wtsdll=NULL;
IWTSQueryUserToken LoadLib::wtsQueryUserTokenFunc=NULL;
IWTSRegisterSessionNotification LoadLib::wtsRegisterSessionNotificationFunc=NULL;
IWTSUnRegisterSessionNotification LoadLib::wtsUnRegisterSessionNotificationFunc=NULL;

//SHCORE LIB
HINSTANCE LoadLib::shcoredll=NULL;
ISetProcessDpiAwareness LoadLib::setProcessDpiAwarenessFunc=NULL;

//USER32 LIB
HINSTANCE LoadLib::user32dll=NULL;
ISetProcessDPIAware LoadLib::setProcessDPIAwareFunc=NULL;

//SAS LIB
HINSTANCE LoadLib::sasdll;	
ISendSas LoadLib::sendSasFunc=NULL;

//WINSTA LIB
HINSTANCE LoadLib::winstadll=NULL;
IWinStationConnectW LoadLib::winStationConnectWFunc=NULL;


LoadLib::LoadLib(){
	if (LoadLib::countinstance==0){
		
		//WTS LIB
		LoadLib::wtsdll=LoadLibrary("Wtsapi32.dll");
		if (LoadLib::wtsdll){
			LoadLib::wtsQueryUserTokenFunc = (IWTSQueryUserToken)GetProcAddress(wtsdll, "WTSQueryUserToken");
			LoadLib::wtsRegisterSessionNotificationFunc = (IWTSRegisterSessionNotification)GetProcAddress(wtsdll, "WTSRegisterSessionNotification");
			LoadLib::wtsUnRegisterSessionNotificationFunc = (IWTSUnRegisterSessionNotification)GetProcAddress(wtsdll, "WTSUnRegisterSessionNotification");
		}

		//SHCORE LIB
		LoadLib::shcoredll = LoadLibrary("Shcore.dll");
		if (LoadLib::shcoredll) {
			LoadLib::setProcessDpiAwarenessFunc = (ISetProcessDpiAwareness)GetProcAddress(shcoredll, "SetProcessDpiAwareness");
		}

		//USER32 LIB
		LoadLib::user32dll = LoadLibrary("User32.dll");
		if (LoadLib::user32dll){
			LoadLib::setProcessDPIAwareFunc = (ISetProcessDPIAware)GetProcAddress(user32dll, "SetProcessDPIAware");
		}

		//SAS LIB
		LoadLib::sasdll = LoadLibrary("sas.dll");
		if (LoadLib::sasdll){
			LoadLib::sendSasFunc = (ISendSas)GetProcAddress(sasdll, "SendSAS");
		}else{
			LoadLib::sasdll = LoadLibrary("native\\sas.dll");
			if (LoadLib::sasdll){
				LoadLib::sendSasFunc = (ISendSas)GetProcAddress(sasdll, "SendSAS");
			}
		}
				
		//WINSTA LIB
		LoadLib::winstadll = LoadLibrary("winsta.dll");
		if (LoadLib::winstadll){
			LoadLib::winStationConnectWFunc = (IWinStationConnectW)GetProcAddress(winstadll, "WinStationConnectW");
		}

		/*dmwdll = LoadLibrary("dwmapi.dll"); 
		if (dmwdll){
			dwmIsCompositionEnabled = (IDwmIsCompositionEnabled)GetProcAddress(dmwdll, "DwmIsCompositionEnabled");
			dwmGetColorizationParameters = (IDwmGetColorizationParameters)GetProcAddress(dmwdll, (LPCSTR)127);
			dwmSetColorizationParameters = (IDwmSetColorizationParameters)GetProcAddress(dmwdll, (LPCSTR)131);
		}*/

	}
	LoadLib::countinstance++;
}

LoadLib::~LoadLib(){
	LoadLib::countinstance--;
	if (LoadLib::countinstance==0){
		if (LoadLib::wtsdll){
			FreeLibrary(LoadLib::wtsdll);
			LoadLib::wtsdll=NULL;
		}

		if (LoadLib::shcoredll){
			FreeLibrary(LoadLib::shcoredll);
			LoadLib::shcoredll=NULL;
		}

		if (LoadLib::user32dll){
			FreeLibrary(LoadLib::user32dll);
			LoadLib::user32dll=NULL;
		}

		if (LoadLib::sasdll){
			FreeLibrary(LoadLib::sasdll);
			LoadLib::sasdll=NULL;
		}

		if (LoadLib::winstadll){
			FreeLibrary(LoadLib::winstadll);
			LoadLib::winstadll=NULL;
		}

		/*if (dmwdll){
			FreeLibrary(dmwdll);
			dmwdll=NULL;
		}*/
	}
}

//WTS LIB
bool LoadLib::isAvailableWTS(){
	return LoadLib::wtsdll!=NULL;
}

IWTSQueryUserToken LoadLib::WTSQueryUserTokenFunc(){
	return LoadLib::wtsQueryUserTokenFunc;
}

IWTSRegisterSessionNotification LoadLib::WTSRegisterSessionNotificationFunc(){
	return LoadLib::wtsRegisterSessionNotificationFunc;
}

IWTSUnRegisterSessionNotification LoadLib::WTSUnRegisterSessionNotificationFunc(){
	return LoadLib::wtsUnRegisterSessionNotificationFunc;
}

//SHCORE LIB
bool LoadLib::isAvailableShCore(){
	return LoadLib::shcoredll!=NULL;
}
	
ISetProcessDpiAwareness LoadLib::SetProcessDpiAwarenessFunc(){
	return LoadLib::setProcessDpiAwarenessFunc;
}

//USER32 LIB
bool LoadLib::isAvailableUser32(){
	return LoadLib::user32dll!=NULL;
}

ISetProcessDPIAware LoadLib::SetProcessDPIAwareFunc(){
	return LoadLib::setProcessDPIAwareFunc;
}

//SAS LIB
bool LoadLib::isAvailableSas(){
	return LoadLib::sasdll!=NULL;
}

ISendSas LoadLib::SendSasFunc(){
	return LoadLib::sendSasFunc;
}

//WINSTA LIB
bool LoadLib::isAvailableWinStation(){
	return LoadLib::winstadll!=NULL;
}

IWinStationConnectW LoadLib::WinStationConnectWFunc(){
	return LoadLib::winStationConnectWFunc;
}

#endif
