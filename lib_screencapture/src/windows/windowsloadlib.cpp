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
IGetWindowDisplayAffinity WindowsLoadLib::getWindowDisplayAffinityFunc=NULL;
ISetWindowDisplayAffinity WindowsLoadLib::setWindowDisplayAffinityFunc=NULL;
IAddClipboardFormatListener WindowsLoadLib::addClipboardFormatListenerFunc=NULL;

//SAS LIB
HINSTANCE WindowsLoadLib::sasdll;
ISendSas WindowsLoadLib::sendSasFunc=NULL;

//WINSTA LIB
HINSTANCE WindowsLoadLib::winstadll=NULL;
IWinStationConnectW WindowsLoadLib::winStationConnectWFunc=NULL;

//DXVA2 LIB
HINSTANCE WindowsLoadLib::dxva2dll=NULL;
IGetNumberOfPhysicalMonitorsFromHMONITOR WindowsLoadLib::getNumberOfPhysicalMonitorsFromHMONITORFunc=NULL;
IGetPhysicalMonitorsFromHMONITOR WindowsLoadLib::getPhysicalMonitorsFromHMONITORFunc=NULL;
ISetVCPFeature WindowsLoadLib::setVCPFeatureFunc=NULL;
IGetVCPFeatureAndVCPFeatureReply WindowsLoadLib::getVCPFeatureAndVCPFeatureReplyFunc=NULL;


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
			WindowsLoadLib::getWindowDisplayAffinityFunc = (IGetWindowDisplayAffinity)GetProcAddress(user32dll, "GetWindowDisplayAffinity");
			WindowsLoadLib::setWindowDisplayAffinityFunc = (ISetWindowDisplayAffinity)GetProcAddress(user32dll, "SetWindowDisplayAffinity");
			WindowsLoadLib::addClipboardFormatListenerFunc = (IAddClipboardFormatListener)GetProcAddress(user32dll, "AddClipboardFormatListener");
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

		//DXVA2 LIB
		WindowsLoadLib::dxva2dll = LoadLibrary("Dxva2.dll");
		if (WindowsLoadLib::dxva2dll){
			WindowsLoadLib::getNumberOfPhysicalMonitorsFromHMONITORFunc = (IGetNumberOfPhysicalMonitorsFromHMONITOR)GetProcAddress(dxva2dll, "GetNumberOfPhysicalMonitorsFromHMONITOR");
			WindowsLoadLib::getPhysicalMonitorsFromHMONITORFunc = (IGetPhysicalMonitorsFromHMONITOR)GetProcAddress(dxva2dll, "GetPhysicalMonitorsFromHMONITOR");
			WindowsLoadLib::setVCPFeatureFunc = (ISetVCPFeature)GetProcAddress(dxva2dll, "SetVCPFeature");
			WindowsLoadLib::getVCPFeatureAndVCPFeatureReplyFunc = (IGetVCPFeatureAndVCPFeatureReply)GetProcAddress(dxva2dll, "GetVCPFeatureAndVCPFeatureReply");

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

		if (WindowsLoadLib::dxva2dll){
			FreeLibrary(WindowsLoadLib::dxva2dll);
			WindowsLoadLib::dxva2dll=NULL;
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

IGetWindowDisplayAffinity WindowsLoadLib::GetWindowDisplayAffinityFunc(){
	return WindowsLoadLib::getWindowDisplayAffinityFunc;
}

ISetWindowDisplayAffinity WindowsLoadLib::SetWindowDisplayAffinityFunc(){
	return WindowsLoadLib::setWindowDisplayAffinityFunc;
}

IAddClipboardFormatListener WindowsLoadLib::AddClipboardFormatListenerFunc(){
	return WindowsLoadLib::addClipboardFormatListenerFunc;
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

//DXVA2 LIB
bool WindowsLoadLib::isAvailableDxva2(){
	return WindowsLoadLib::dxva2dll!=NULL;
}

IGetNumberOfPhysicalMonitorsFromHMONITOR WindowsLoadLib::GetNumberOfPhysicalMonitorsFromHMONITORFunc(){
	return WindowsLoadLib::getNumberOfPhysicalMonitorsFromHMONITORFunc;
}

IGetPhysicalMonitorsFromHMONITOR WindowsLoadLib::GetPhysicalMonitorsFromHMONITORFunc(){
	return WindowsLoadLib::getPhysicalMonitorsFromHMONITORFunc;
}

ISetVCPFeature WindowsLoadLib::SetVCPFeatureFunc(){
	return WindowsLoadLib::setVCPFeatureFunc;
}

IGetVCPFeatureAndVCPFeatureReply WindowsLoadLib::GetVCPFeatureAndVCPFeatureReplyFunc(){
	return WindowsLoadLib::getVCPFeatureAndVCPFeatureReplyFunc;
}


//TMP PRIVACY MODE (BEGIN)
#include <vector>
WindowsLoadLib privacyModeLoadLib;
const BYTE PowerMode = 0xD6;
const DWORD PowerOn = 0x01;
const DWORD PowerOff = 0x04;
struct PrivacyModeMonitorDesc{
    HANDLE hdl;
    RECT rc;
};
std::vector<PrivacyModeMonitorDesc> privacyModeMonitors;
bool privacyModeEnable=false;

BOOL CALLBACK PrivacyModeMonitorEnumProc(HMONITOR hMonitor, HDC hdcMonitor, LPRECT lprcMonitor, LPARAM dwData){
    std::vector<PrivacyModeMonitorDesc>* pMonitors = reinterpret_cast< std::vector<PrivacyModeMonitorDesc>* >(dwData);
    DWORD nMonitorCount;
    if(privacyModeLoadLib.GetNumberOfPhysicalMonitorsFromHMONITORFunc()(hMonitor, &nMonitorCount)){
        PHYSICAL_MONITOR* pMons = new PHYSICAL_MONITOR[nMonitorCount];
        if(privacyModeLoadLib.GetPhysicalMonitorsFromHMONITORFunc()(hMonitor, nMonitorCount, pMons)){
            for(DWORD i=0; i<nMonitorCount; i++){
                PrivacyModeMonitorDesc desc;
                desc.hdl = pMons[i].hPhysicalMonitor;
                desc.rc = *lprcMonitor;
                pMonitors->push_back(desc);
            }
        }
        delete[] pMons;
    }
    return TRUE;
}

DWORD WINAPI PrivacyModeThreadProc( LPVOID lpParam ){
	while(privacyModeEnable){
		for(auto& monitor : privacyModeMonitors){
			DWORD pdwCurrentValue;
			DWORD pdwMaximumValue;
			if (privacyModeLoadLib.GetVCPFeatureAndVCPFeatureReplyFunc()(monitor.hdl, PowerMode, NULL, &pdwCurrentValue, &pdwMaximumValue)){
				if (pdwCurrentValue==PowerOn){
					privacyModeLoadLib.SetVCPFeatureFunc()(monitor.hdl, PowerMode, PowerOff);
				}
			}
		}
		Sleep(500);
	}
	for(auto& monitor : privacyModeMonitors){
		privacyModeLoadLib.SetVCPFeatureFunc()(monitor.hdl, PowerMode, PowerOn);
	}
	return 1;
}

void WindowsLoadLibSetPrivacyMode(bool b){
	if (privacyModeEnable==false){
		privacyModeEnable=true;
		if (privacyModeLoadLib.isAvailableDxva2()){
			privacyModeMonitors.clear();
			EnumDisplayMonitors(NULL, NULL, &PrivacyModeMonitorEnumProc, reinterpret_cast<LPARAM>(&privacyModeMonitors));
			CreateThread(0, 0, PrivacyModeThreadProc, NULL, 0, NULL);
		}
	}else{
		privacyModeEnable=false;
	}

}
//TMP PRIVACY MODE (END)


#endif
