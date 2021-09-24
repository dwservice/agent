/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/
#if defined OS_DESKTOPDUPLICATION

using namespace std;
#include <windows.h>
#include <vector>
#include <map>
#include <string>
#include <fstream>
#include <sys/stat.h>
#include "../windows/windowscpuusage.h"
#include "../windows/windowsinputs.h"
#include "../windows/windowsdesktop.h"
#include "../windows/windowsloadlib.h"
#include "../common/dwdebugger.h"
#include "../common/timecounter.h"
#include "../common/util.h"

#include <shlobj.h>
#include <shellapi.h>
#include <dxgi1_2.h>
#include <d3d11.h>
#include <memory>
#include <algorithm>
#include <string>

extern "C" {
	int DWAScreenCaptureVersion();
	bool DWAScreenCaptureLoad();
	void DWAScreenCaptureFreeMemory(void* pnt);
	int DWAScreenCaptureIsChanged();
	int DWAScreenCaptureGetMonitorsInfo(MONITORS_INFO* moninfo);
	int DWAScreenCaptureInitMonitor(MONITORS_INFO_ITEM* moninfoitem, RGB_IMAGE* capimage, void** capses);
	int DWAScreenCaptureGetImage(void* capses);
	void DWAScreenCaptureTermMonitor(void* capses);
	void DWAScreenCaptureUnload();
	void DWAScreenCaptureInputKeyboard(const char* type, const char* key, bool ctrl, bool alt, bool shift, bool command);
	void DWAScreenCaptureInputMouse(MONITORS_INFO_ITEM* moninfoitem, int x, int y, int button, int wheel, bool ctrl, bool alt, bool shift, bool command);
	int DWAScreenCaptureCursor(CURSOR_IMAGE* curimage);
	int DWAScreenCaptureGetClipboardText(wchar_t** wText);
	void DWAScreenCaptureSetClipboardText(wchar_t* wText);
	void DWAScreenCaptureCopy();
	void DWAScreenCapturePaste();
	int DWAScreenCaptureGetCpuUsage();
	//TMP PRIVACY MODE
	void DWAScreenCaptureSetPrivacyMode(bool b);
}

D3D_DRIVER_TYPE gDriverTypes[] =
{
	D3D_DRIVER_TYPE_HARDWARE,
	D3D_DRIVER_TYPE_WARP,
	D3D_DRIVER_TYPE_REFERENCE
};
UINT gNumDriverTypes = ARRAYSIZE(gDriverTypes);
D3D_FEATURE_LEVEL gFeatureLevels[] =
{
	D3D_FEATURE_LEVEL_11_0,
	D3D_FEATURE_LEVEL_10_1,
	D3D_FEATURE_LEVEL_10_0,
	D3D_FEATURE_LEVEL_9_1
};

D3D_FEATURE_LEVEL minD3Dlevel = D3D_FEATURE_LEVEL_10_0;

UINT gNumFeatureLevels = ARRAYSIZE(gFeatureLevels);

struct MonitorInternalInfo{
	HMONITOR hMonitor;
};

struct CursorInternalInfo{
	//ULONG dataID;
	HCURSOR hCursor;
};

struct CursorCaptureInfo{
	int lastMonitorUpdate;
	LARGE_INTEGER lastTimeStamp;
	int x;
	int y;
	bool visible;
	ULONG dataID;
	UINT dataSize;
	unsigned char* data;
	DXGI_OUTDUPL_POINTER_SHAPE_INFO info;
};

struct ScreenCaptureInfo{
	int status; //0:NOT INIT; 1:INIT; 2:READY
	int monitor;
	int x;
	int y;
	int w;
	int h;
	RGB_IMAGE* rgbimage;
	unsigned char* data;
	D3D_FEATURE_LEVEL lFeatureLevel;
	ID3D11Device* lDeskDupDevice;
	ID3D11DeviceContext* lDeskDupImmediateContext;
	IDXGIOutputDuplication* desktopDupl;
	ID3D11Texture2D* destImage;
	DXGI_OUTPUT_DESC outputDesc;
	DXGI_OUTDUPL_DESC outputDuplDesc;
	D3D11_MAPPED_SUBRESOURCE resource;
	UINT subresource;
	BYTE* metaDataBuffer;
	UINT metaDataSize;
};

CursorCaptureInfo cursorCaptureInfo;

WindowsDesktop* winDesktop;
WindowsInputs* winInputs;
WindowsCPUUsage* cpuUsage;



#endif
