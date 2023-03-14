/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/
#if defined OS_DESKTOPDUPLICATION

#include "screencapturenativedesktopduplication.h"

int DWAScreenCaptureVersion(){
	return 2;
}

void DWAScreenCaptureFreeMemory(void* pnt){
	free(pnt);
}

int DWAScreenCaptureIsChanged(){
	int iret = winDesktop->setCurrentThread();
	if (iret!=0){
		Sleep(250); //DO NOT REMOVE IT FIX SWITCH SCREEN ISSUE
	}
	return iret;
}

void destroyCursorInfo(){
	if (cursorCaptureInfo.data){
		delete [] cursorCaptureInfo.data;
	}
	cursorCaptureInfo.data = NULL;
	cursorCaptureInfo.dataSize = 0;
}

int DWAScreenCaptureGetCpuUsage(){
    return (int)cpuUsage->getValue();
}

int clearMonitorsInfo(MONITORS_INFO* moninfo){
	moninfo->changed=0;
	for (int i=0;i<=MONITORS_INFO_ITEM_MAX-1;i++){
		moninfo->monitor[i].changed=-1;
	}
	for (int i=0;i<=moninfo->count-1;i++){
		moninfo->monitor[i].changed=0;
	}
	int oldmc=moninfo->count;
	moninfo->count=0;
	return oldmc;
}

void addMonitorsInfo(MONITORS_INFO* moninfo, int x, int y, int w, int h, int rotatedDegrees, HMONITOR hMonitor){
	int p=moninfo->count;
	moninfo->count+=1;
	MonitorInternalInfo* mi = NULL;
	if (moninfo->monitor[p].internal==NULL){
		mi = new MonitorInternalInfo();
		moninfo->monitor[p].internal=mi;
	}else{
		mi = (MonitorInternalInfo*)moninfo->monitor[p].internal;
	}
	if (moninfo->monitor[p].changed==-1){
		moninfo->monitor[p].index=p;
		moninfo->monitor[p].x=x;
		moninfo->monitor[p].y=y;
		moninfo->monitor[p].width=w;
		moninfo->monitor[p].height=h;
		mi->rotatedDegrees=rotatedDegrees;
		mi->hMonitor=hMonitor;
		moninfo->monitor[p].changed=1;
		moninfo->changed=1;
	}else{
		if ((mi->hMonitor!=hMonitor) || (moninfo->monitor[p].x!=x) || (moninfo->monitor[p].y!=y) || (moninfo->monitor[p].width!=w) || (moninfo->monitor[p].height!=h)){
			moninfo->monitor[p].index=p;
			moninfo->monitor[p].x=x;
			moninfo->monitor[p].y=y;
			moninfo->monitor[p].width=w;
			moninfo->monitor[p].height=h;
			mi->rotatedDegrees=rotatedDegrees;
			mi->hMonitor=hMonitor;
			moninfo->monitor[p].changed=1;
			moninfo->changed=1;
		}else{
			moninfo->monitor[p].changed=0;
		}
	}
}


int DWAScreenCaptureGetMonitorsInfo(MONITORS_INFO* moninfo){
	winDesktop->monitorON();
	int oldmc=clearMonitorsInfo(moninfo);
	if (oldmc<0){
		return oldmc;
	}
	IDXGIFactory1* ipDxgiFactory;
	HRESULT hr = CreateDXGIFactory1(__uuidof(IDXGIFactory1), (void**)(&ipDxgiFactory));
	if (FAILED(hr)){
		return -5;
	}
	IDXGIAdapter1* ipDxgiAdapter;
	IDXGIOutput* ipDxgiOutput;
	for(int j=0; ipDxgiFactory->EnumAdapters1(j, &ipDxgiAdapter) != DXGI_ERROR_NOT_FOUND; j++){
		for (UINT i = 0; ; i++){
			HRESULT hr = ipDxgiAdapter->EnumOutputs(i, &ipDxgiOutput);
			if (FAILED(hr)){
				break;
			}
			if ((nullptr != ipDxgiOutput) && (hr != DXGI_ERROR_NOT_FOUND)){
				DXGI_OUTPUT_DESC DesktopDesc;
				hr = ipDxgiOutput->GetDesc(&DesktopDesc);
				bool bok=true;
				if (FAILED(hr)){
					bok=false;
				}
				if ((bok) && (DesktopDesc.AttachedToDesktop==TRUE)){
					int rotatedDegrees=0;
					switch (DesktopDesc.Rotation){
						case DXGI_MODE_ROTATION_UNSPECIFIED:
						case DXGI_MODE_ROTATION_IDENTITY:
							rotatedDegrees = 0;
							break;
						case DXGI_MODE_ROTATION_ROTATE90:
							rotatedDegrees = 90;
							break;
						case DXGI_MODE_ROTATION_ROTATE180:
							rotatedDegrees = 180;
							break;
						case DXGI_MODE_ROTATION_ROTATE270:
							rotatedDegrees = 270;
							break;
					}
					int x=DesktopDesc.DesktopCoordinates.left;
					int y=DesktopDesc.DesktopCoordinates.top;
					int w=DesktopDesc.DesktopCoordinates.right - DesktopDesc.DesktopCoordinates.left;
					int h=DesktopDesc.DesktopCoordinates.bottom - DesktopDesc.DesktopCoordinates.top;
					addMonitorsInfo(moninfo,x,y,w,h,rotatedDegrees,DesktopDesc.Monitor);
				}
				ipDxgiOutput->Release();
			}
		}
		ipDxgiAdapter->Release();
	}
	ipDxgiOutput = nullptr;
	ipDxgiAdapter = nullptr;
	ipDxgiFactory->Release();
	ipDxgiFactory = nullptr;
	if (oldmc!=moninfo->count){
		moninfo->changed=1;
	}
	return 0;
}

bool DWAScreenCaptureLoad() {
	bool bok=false;
	D3D_FEATURE_LEVEL lFeatureLevel;
	ID3D11Device* lDeskDupDevice;
	ID3D11DeviceContext* lDeskDupImmediateContext;
	HRESULT hr(E_FAIL);
	for (UINT DriverTypeIndex = 0; DriverTypeIndex < gNumDriverTypes; ++DriverTypeIndex){
		hr = D3D11CreateDevice(
			nullptr,
			gDriverTypes[DriverTypeIndex],
			nullptr,
			0,
			gFeatureLevels,
			gNumFeatureLevels,
			D3D11_SDK_VERSION,
			&lDeskDupDevice,
			&lFeatureLevel,
			&lDeskDupImmediateContext);

		if (SUCCEEDED(hr)){
			break;
		}
		lDeskDupDevice->Release();
		lDeskDupImmediateContext->Release();
	}
	if (FAILED(hr)){
		bok=false;
	}else if (lDeskDupDevice == nullptr){
		bok=false;
	}else{
		if (lFeatureLevel>=minD3Dlevel){
			bok=true;
		}
		lDeskDupDevice->Release();
		lDeskDupImmediateContext->Release();
	}
	if (bok){
		cursorCaptureInfo.dataID=0;
		cursorCaptureInfo.lastMonitorUpdate=-1;
		cursorCaptureInfo.dataSize=0;
		winDesktop=new WindowsDesktop();
		winInputs=new WindowsInputs();
		cpuUsage=new WindowsCPUUsage();
		winDesktop->monitorON();
		Sleep(500);
	}
	return bok;
}

void DWAScreenCaptureUnload() {
	//restoreVisualEffect
	destroyCursorInfo();
	delete winDesktop;
	delete winInputs;
	delete cpuUsage;
}

int DWAScreenCaptureCursor(CURSOR_IMAGE* curimage) {
	/*if (cursorCaptureInfo.lastMonitorUpdate>=0){
		CursorInternalInfo* cursorInternalInfo = NULL;
		if (curimage->internal==NULL){
			cursorInternalInfo = new CursorInternalInfo();
			cursorInternalInfo->dataID=0;
			curimage->internal=cursorInternalInfo;

		}else{
			cursorInternalInfo=(CursorInternalInfo*)curimage->internal;
		}
		curimage->changed=0;
		curimage->x=cursorCaptureInfo.x;
		curimage->y=cursorCaptureInfo.y;
		if ((cursorCaptureInfo.visible) and (cursorCaptureInfo.dataID>0)){
			curimage->visible=1;
			if (cursorInternalInfo->dataID!=cursorCaptureInfo.dataID){
				int is = 0;
				int id = 0;
				unsigned char* cursorData = (unsigned char*)malloc((cursorCaptureInfo.info.Width * cursorCaptureInfo.info.Height) * 4);
				for (UINT y=0; y<cursorCaptureInfo.info.Height; y++){
					for (UINT x=0; x<cursorCaptureInfo.info.Width; x++){
						cursorData[id] = cursorCaptureInfo.data[is+1];
						cursorData[id + 1] = cursorCaptureInfo.data[is+2];
						cursorData[id + 2] = cursorCaptureInfo.data[is+3];
						if (cursorCaptureInfo.data[is]==0){
							cursorData[id + 3] = 0;//cursorCaptureInfo.data[is];
						}else{
							cursorData[id] = cursorCaptureInfo.data[is];
							cursorData[id + 1] = cursorCaptureInfo.data[is];
							cursorData[id + 2] = cursorCaptureInfo.data[is];
							cursorData[id + 3] = 255;
						}

						//if (cursorCaptureInfo.info.Type==DXGI_OUTDUPL_POINTER_SHAPE_TYPE_MONOCHROME){
						//}else if (cursorCaptureInfo.info.Type==DXGI_OUTDUPL_POINTER_SHAPE_TYPE_COLOR){
						//}else if (cursorCaptureInfo.info.Type==DXGI_OUTDUPL_POINTER_SHAPE_TYPE_MASKED_COLOR){
						//}

						id += 4;
						is += 4;
					}
				}
				curimage->width=cursorCaptureInfo.info.Width;
				curimage->height=cursorCaptureInfo.info.Height;
				curimage->offx=cursorCaptureInfo.info.HotSpot.x;
				curimage->offy=cursorCaptureInfo.info.HotSpot.y;
				if (curimage->data!=NULL){
					free(curimage->data);
				}
				curimage->data = cursorData;
				curimage->sizedata = curimage->width*curimage->height*4;
				curimage->changed=1;
				cursorInternalInfo->dataID=cursorCaptureInfo.dataID;
			}
		}else{
			curimage->visible=1;
			if (curimage->data==NULL){
				curimage->changed=1;
				setCursorImage(CURSOR_TYPE_ARROW_18_18,curimage);
			}
		}
	}else{
		POINT point;
		if (GetCursorPos(&point)) {
			curimage->visible=1;
			curimage->x=point.x;
			curimage->y=point.y;
			if (curimage->data==NULL){
				curimage->changed=1;
				setCursorImage(CURSOR_TYPE_ARROW_18_18,curimage);
			}
		}else{
			return -1;
		}
	}
	*/

	CursorInternalInfo* cursorInternalInfo = NULL;
	if (curimage->internal==NULL){
		cursorInternalInfo = new CursorInternalInfo();
		curimage->internal=cursorInternalInfo;
	}else{
		cursorInternalInfo=(CursorInternalInfo*)curimage->internal;
	}
	curimage->changed=0;
	CURSORINFO appCursorInfo;
	appCursorInfo.cbSize = sizeof(CURSORINFO);
	if (GetCursorInfo(&appCursorInfo)){
		curimage->x=appCursorInfo.ptScreenPos.x;
		curimage->y=appCursorInfo.ptScreenPos.y;
		if (appCursorInfo.flags!=0){
			curimage->visible=1;
			if ((curimage->data==NULL) || (appCursorInfo.hCursor!=cursorInternalInfo->hCursor)){
				bool bok = false;
				cursorInternalInfo->hCursor=appCursorInfo.hCursor;
				ICONINFO info;
				if (GetIconInfo(appCursorInfo.hCursor, &info)){
					BITMAP bmMask;
					GetObject(info.hbmMask, sizeof(BITMAP), (LPVOID)&bmMask);
					if (bmMask.bmPlanes != 1 || bmMask.bmBitsPixel != 1) {
						DeleteObject(info.hbmMask);
					}else{
						//unsigned char* dataNorm = NULL;
						//unsigned char* dataMask = NULL;
						bool isColorShape = (info.hbmColor != NULL);
						int w = bmMask.bmWidth;
						int h = isColorShape ? bmMask.bmHeight : bmMask.bmHeight/2;
						//int nbit = bmMask.bmWidthBytes;

						//IMAGE
						HDC hdstImage = CreateCompatibleDC(NULL);
						BITMAPINFO biImage;
						ZeroMemory(&biImage, sizeof(BITMAPINFO));
						biImage.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
						biImage.bmiHeader.biBitCount = 32;
						biImage.bmiHeader.biCompression = BI_RGB;
						biImage.bmiHeader.biPlanes = 1;
						biImage.bmiHeader.biWidth = w;
						biImage.bmiHeader.biHeight = -h;
						biImage.bmiHeader.biSizeImage = 0;
						biImage.bmiHeader.biXPelsPerMeter = 0;
						biImage.bmiHeader.biYPelsPerMeter = 0;
						biImage.bmiHeader.biClrUsed = 0;
						biImage.bmiHeader.biClrImportant = 0;
						void *bufferImage;
						HANDLE hbmDIBImage = CreateDIBSection(hdstImage, (BITMAPINFO*)&biImage, DIB_RGB_COLORS, &bufferImage, NULL, 0);
						HANDLE hbmDIBOLDImage = (HBITMAP)SelectObject(hdstImage, hbmDIBImage);
						unsigned char* appDataImage = (unsigned char*)bufferImage;

						//MASK
						HDC hdstMask = CreateCompatibleDC(NULL);
						BITMAPINFO biMask;
						ZeroMemory(&biMask, sizeof(BITMAPINFO));
						biMask.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
						biMask.bmiHeader.biBitCount = 32;
						biMask.bmiHeader.biCompression = BI_RGB;
						biMask.bmiHeader.biPlanes = 1;
						biMask.bmiHeader.biWidth = w;
						biMask.bmiHeader.biHeight = -h;
						biMask.bmiHeader.biSizeImage = 0;
						biMask.bmiHeader.biXPelsPerMeter = 0;
						biMask.bmiHeader.biYPelsPerMeter = 0;
						biMask.bmiHeader.biClrUsed = 0;
						biMask.bmiHeader.biClrImportant = 0;
						void *bufferMask;
						HANDLE hbmDIBMask = CreateDIBSection(hdstMask, (BITMAPINFO*)&biMask, DIB_RGB_COLORS, &bufferMask, NULL, 0);
						HANDLE hbmDIBOLDMask = (HBITMAP)SelectObject(hdstMask, hbmDIBMask);
						unsigned char* appDataMask = (unsigned char*)bufferMask;

						bool cursorCheckMask=true;
						unsigned char* cursorData = NULL;
						if (DrawIconEx(hdstImage, 0, 0, (HICON)appCursorInfo.hCursor, 0, 0, 0, NULL, DI_IMAGE)) {
							int isck = 0;
							for (int y=0; y<h; y++) {
								for (int x=0; x<w; x++) {
									if ((appDataImage[isck + 3])>0) {
										cursorCheckMask = false;
										break;
									}
									isck += 4;
								}
							}
							if (DrawIconEx(hdstMask, 0, 0, (HICON)appCursorInfo.hCursor, 0, 0, 0, NULL, DI_MASK)) {
								cursorData = (unsigned char*)malloc((w * h) * 4);
								int is = 0;
								int id = 0;
								for (int y=0; y<h; y++) {
									for (int x=0; x<w; x++) {
										unsigned char r;
										unsigned char g;
										unsigned char b;
										unsigned char a;
										if (cursorCheckMask){
											r = appDataImage[is + 2];
											g = appDataImage[is + 1];
											b = appDataImage[is];
											if ((appDataMask[is + 2]==0) && (appDataMask[is + 1]==0) && (appDataMask[is]==0)){
												a = 255;
											}else{
												if ((appDataMask[is + 2]==appDataImage[is + 2]) && (appDataMask[is + 1]==appDataImage[is + 1]) && (appDataMask[is]==appDataImage[is])){
													r = 128;
													g = 128;
													b = 128;
													a = 255;
												}else{
													a = 0;
												}
											}
										}else{
											r = appDataImage[is + 2];
											g = appDataImage[is + 1];
											b = appDataImage[is];
											a = appDataImage[is + 3];
										}
										cursorData[id] = r;
										cursorData[id + 1] = g;
										cursorData[id + 2] = b;
										cursorData[id + 3] = a;
										id += 4;
										is += 4;
										if ((r!=0) || (g!=0) || (b!=0) || (a!=0)){
											bok = true;
										}
									}
								}
								if (!bok){
									free(cursorData);
								}
							}
						}
						if (bok){
							curimage->width=w;
							curimage->height=h;
							if (info.fIcon==FALSE){
								curimage->offx = info.xHotspot;
								curimage->offy = info.yHotspot;
							}else{
								curimage->offx = w/2;
								curimage->offy = h/2;
							}
							curimage->changed=1;
							if (curimage->data!=NULL){
								free(curimage->data);
							}
							curimage->data = cursorData;
							curimage->sizedata = curimage->width*curimage->height*4;
						}

						SelectObject(hdstImage, hbmDIBOLDImage);
						DeleteObject(hbmDIBImage);
						DeleteDC(hdstImage);

						SelectObject(hdstMask, hbmDIBOLDMask);
						DeleteObject(hbmDIBMask);
						DeleteDC(hdstMask);
					}
				}
				if (!bok){
					if (curimage->data==NULL){
						curimage->changed=1;
						setCursorImage(CURSOR_TYPE_ARROW_18_18,curimage);
					}
				}
			}
		}else{ //Cursore nascosto
			curimage->visible=1;
			if (curimage->data==NULL){
				curimage->changed=1;
				setCursorImage(CURSOR_TYPE_ARROW_18_18,curimage);
			}
		}
	}else{
		POINT point;
		if (GetCursorPos(&point)) {
			curimage->visible=1;
			curimage->x=point.x;
			curimage->y=point.y;
			if (curimage->data==NULL){
				curimage->changed=1;
				setCursorImage(CURSOR_TYPE_ARROW_18_18,curimage);
			}
		}else{
			return -1;
		}
	}
	return 0;
}

void releaseScreenCaptureInfo(ScreenCaptureInfo* sci){
	if (sci->destImage!=nullptr){
		sci->destImage->Release();
		sci->destImage=nullptr;
	}
	if (sci->metaDataBuffer){
		delete [] sci->metaDataBuffer;
		sci->metaDataBuffer = NULL;
	}
	sci->metaDataSize = 0;
	if (sci->desktopDupl != nullptr){
		sci->desktopDupl->Release();
		sci->desktopDupl=nullptr;
	}
	if (sci->lDeskDupDevice != nullptr){
		sci->lDeskDupDevice->Release();
		sci->lDeskDupDevice=nullptr;
	}
	if (sci->lDeskDupImmediateContext != nullptr){
		sci->lDeskDupImmediateContext->Release();
		sci->lDeskDupImmediateContext=nullptr;
	}
	if (sci->rgbimage->data!=NULL){
		free(sci->rgbimage->data);
		sci->rgbimage->data=NULL;
	}
	sci->rgbimage->width=0;
	sci->rgbimage->height=0;
	sci->status=0;
	delete sci;
}

int DWAScreenCaptureInitMonitor(MONITORS_INFO_ITEM* moninfoitem, RGB_IMAGE* capimage, void** capses){
	ScreenCaptureInfo* sci = new ScreenCaptureInfo();
	sci->monitor=moninfoitem->index;
	sci->x=moninfoitem->x;
	sci->y=moninfoitem->y;
	sci->w=moninfoitem->width;
	sci->h=moninfoitem->height;
	sci->rgbimage=capimage;
	sci->rgbimage->width=moninfoitem->width;
	sci->rgbimage->height=moninfoitem->height;
	sci->rgbimage->sizedata=sci->rgbimage->width*sci->rgbimage->height*3;
	sci->rgbimage->sizechangearea=0;
	sci->rgbimage->sizemovearea=0;
	sci->lDeskDupDevice=nullptr;
	sci->lDeskDupImmediateContext=nullptr;
	HRESULT hr(E_FAIL);
	for (UINT DriverTypeIndex = 0; DriverTypeIndex < gNumDriverTypes; ++DriverTypeIndex){
		hr = D3D11CreateDevice(
			nullptr,
			gDriverTypes[DriverTypeIndex],
			nullptr,
			0,
			gFeatureLevels,
			gNumFeatureLevels,
			D3D11_SDK_VERSION,
			&sci->lDeskDupDevice,
			&sci->lFeatureLevel,
			&sci->lDeskDupImmediateContext);

		if (SUCCEEDED(hr)){
			break;
		}
		sci->lDeskDupDevice->Release();
		sci->lDeskDupImmediateContext->Release();
	}
	if (FAILED(hr)){
		releaseScreenCaptureInfo(sci);
		return -20;
	}
	Sleep(100);
	if (sci->lDeskDupDevice == nullptr){
		releaseScreenCaptureInfo(sci);
		return -21;
	}
	if (sci->lFeatureLevel<minD3Dlevel){
		releaseScreenCaptureInfo(sci);
		return -22;
	}

	IDXGIDevice* lDxgiDevice;
	hr = sci->lDeskDupDevice->QueryInterface(IID_PPV_ARGS(&lDxgiDevice));
	if (FAILED(hr)){
		releaseScreenCaptureInfo(sci);
		return -3;
	}
	IDXGIAdapter* lDxgiAdapter;
	hr = lDxgiDevice->GetParent(__uuidof(IDXGIAdapter),reinterpret_cast<void**>(&lDxgiAdapter));
	if (FAILED(hr)){
		releaseScreenCaptureInfo(sci);
		return -4;
	}
	lDxgiDevice->Release();

	IDXGIOutput* lDxgiOutput;
	hr = lDxgiAdapter->EnumOutputs(sci->monitor,&lDxgiOutput);
	if (FAILED(hr)){
		releaseScreenCaptureInfo(sci);
		return -5;
	}
	lDxgiAdapter->Release();

	hr = lDxgiOutput->GetDesc(&sci->outputDesc);
	if (FAILED(hr)){
		releaseScreenCaptureInfo(sci);
		return -6;
	}

	IDXGIOutput1* lDxgiOutput1;
	hr = lDxgiOutput->QueryInterface(IID_PPV_ARGS(&lDxgiOutput1));
	if (FAILED(hr)){
		releaseScreenCaptureInfo(sci);
		return -7;
	}
	lDxgiOutput->Release();

	hr = lDxgiOutput1->DuplicateOutput(sci->lDeskDupDevice,&sci->desktopDupl);
	if (FAILED(hr)){
		releaseScreenCaptureInfo(sci);
		return -8;
	}
	lDxgiOutput1->Release();

	sci->desktopDupl->GetDesc(&sci->outputDuplDesc);

	D3D11_TEXTURE2D_DESC desc;
	desc.Width = sci->outputDuplDesc.ModeDesc.Width;
	desc.Height = sci->outputDuplDesc.ModeDesc.Height;
	desc.Format = sci->outputDuplDesc.ModeDesc.Format;
	desc.ArraySize = 1;
	desc.BindFlags = 0;
	desc.MiscFlags = 0;
	desc.SampleDesc.Count = 1;
	desc.SampleDesc.Quality = 0;
	desc.MipLevels = 1;
	desc.CPUAccessFlags = D3D11_CPU_ACCESS_READ;
	desc.Usage = D3D11_USAGE_STAGING;
	hr = sci->lDeskDupDevice->CreateTexture2D(&desc, NULL, &sci->destImage);
	if (FAILED(hr)){
		releaseScreenCaptureInfo(sci);
		return -9;
	}
	if (sci->destImage == nullptr){
		releaseScreenCaptureInfo(sci);
		return -10;
	}
	sci->subresource = D3D11CalcSubresource(0, 0, 0);
	sci->rgbimage->data=(unsigned char*)malloc(sci->rgbimage->sizedata * sizeof(unsigned char));
	sci->status=1;
	*capses=sci;
	return 0;
}

void DWAScreenCaptureTermMonitor(void* capses){
	ScreenCaptureInfo* sci = (ScreenCaptureInfo*)capses;
	if (sci->status==0){
		return;
	}
	releaseScreenCaptureInfo(sci);
}


HRESULT updateCursorInfo(ScreenCaptureInfo* sci, _In_ DXGI_OUTDUPL_FRAME_INFO* FrameInfo){
	HRESULT hr = S_OK;
	if (FrameInfo->LastMouseUpdateTime.QuadPart == 0){
		return hr;
	}
	bool UpdatePosition = true;
	if (!FrameInfo->PointerPosition.Visible && (cursorCaptureInfo.lastMonitorUpdate != sci->monitor)){
		UpdatePosition = false;
	}
	if (FrameInfo->PointerPosition.Visible && cursorCaptureInfo.visible && (cursorCaptureInfo.lastMonitorUpdate != sci->monitor) && (cursorCaptureInfo.lastTimeStamp.QuadPart > FrameInfo->LastMouseUpdateTime.QuadPart)){
		UpdatePosition = false;
	}
	if (UpdatePosition){
		cursorCaptureInfo.x = FrameInfo->PointerPosition.Position.x + sci->x;
		cursorCaptureInfo.y = FrameInfo->PointerPosition.Position.y + sci->y;
		cursorCaptureInfo.lastMonitorUpdate = sci->monitor;
		cursorCaptureInfo.lastTimeStamp = FrameInfo->LastMouseUpdateTime;
		cursorCaptureInfo.visible = FrameInfo->PointerPosition.Visible != 0;
	}
	if (FrameInfo->PointerShapeBufferSize == 0){
		return hr;
	}
	if (FrameInfo->PointerShapeBufferSize > cursorCaptureInfo.dataSize){
		destroyCursorInfo();
		cursorCaptureInfo.data = new (std::nothrow) BYTE[FrameInfo->PointerShapeBufferSize];
		if (!cursorCaptureInfo.data){
			cursorCaptureInfo.dataSize = 0;
			return E_OUTOFMEMORY;
		}
		cursorCaptureInfo.dataSize = FrameInfo->PointerShapeBufferSize;
	}
	UINT BufferSizeRequired;
	hr = sci->desktopDupl->GetFramePointerShape(FrameInfo->PointerShapeBufferSize, reinterpret_cast<unsigned char*>(cursorCaptureInfo.data), &BufferSizeRequired, &cursorCaptureInfo.info);
	if (FAILED(hr))	{
		destroyCursorInfo();
		return hr;
	}else{
		cursorCaptureInfo.dataID++;
	}
	return hr;
}

int DWAScreenCaptureGetImage(void* capses){
	int iret=0;
	bool bok=true;
	bool brelaseframe=false;
		ScreenCaptureInfo* sci = (ScreenCaptureInfo*)capses;
	if (sci->status==0){
		return -1; //NOT INIT
	}
	RGB_IMAGE* rgbimage=sci->rgbimage;
	rgbimage->sizechangearea=0;
	rgbimage->sizemovearea=0;
	HRESULT hr(E_FAIL);
	DXGI_OUTDUPL_FRAME_INFO lFrameInfo;
	IDXGIResource* lDesktopResource;
	hr = sci->desktopDupl->AcquireNextFrame(0,&lFrameInfo,&lDesktopResource);
	if (FAILED(hr)){
		if (hr != DXGI_ERROR_WAIT_TIMEOUT){
			iret=-3;
		}
		bok=false;
	}
	if (hr == DXGI_ERROR_WAIT_TIMEOUT){
		bok=false;
	}
	if (bok){
		brelaseframe=true;
		//FRAME
		if (lFrameInfo.TotalMetadataBufferSize){
			if (lFrameInfo.TotalMetadataBufferSize > sci->metaDataSize){
				if (sci->metaDataBuffer){
					delete [] sci->metaDataBuffer;
					sci->metaDataBuffer = NULL;
				}
				sci->metaDataBuffer = new (std::nothrow) BYTE[lFrameInfo.TotalMetadataBufferSize];
				if (!sci->metaDataBuffer){
					sci->metaDataSize = 0;
					rgbimage->sizechangearea=0;
					rgbimage->sizemovearea=0;
					iret=-5; //OUTOFMEMORY
					bok=false;
				}
				sci->metaDataSize = lFrameInfo.TotalMetadataBufferSize;
			}
			UINT BufSize = lFrameInfo.TotalMetadataBufferSize;

			hr = sci->desktopDupl->GetFrameMoveRects(BufSize, reinterpret_cast<DXGI_OUTDUPL_MOVE_RECT*>(sci->metaDataBuffer), &BufSize);
			if (FAILED(hr)){
				if (hr != DXGI_ERROR_ACCESS_LOST){
					iret=-6;
				}
				rgbimage->sizechangearea=0;
				rgbimage->sizemovearea=0;
				bok=false;
				//return hr;
			}
			rgbimage->sizemovearea = BufSize / sizeof(DXGI_OUTDUPL_MOVE_RECT);
			if ((rgbimage->sizemovearea>0) and (rgbimage->sizemovearea<=RGB_IMAGE_DIFFSIZE)){
				DXGI_OUTDUPL_MOVE_RECT* rects = (DXGI_OUTDUPL_MOVE_RECT*)sci->metaDataBuffer;
				for (int i = 0; i < rgbimage->sizemovearea; i++){
					DXGI_OUTDUPL_MOVE_RECT rect = rects[i];
					RGB_IMAGE_MOVE_AREA* rgbmovearea = &rgbimage->movearea[i];
					rgbmovearea->x=rect.SourcePoint.x;
					rgbmovearea->y=rect.SourcePoint.y;
					rgbmovearea->width=rect.DestinationRect.right-rect.DestinationRect.left;
					rgbmovearea->height=rect.DestinationRect.bottom-rect.DestinationRect.top;
					rgbmovearea->xdest=rect.DestinationRect.left;
					rgbmovearea->ydest=rect.DestinationRect.top;
				}
			}

			BYTE* dirtyRects = sci->metaDataBuffer + BufSize;
			BufSize = lFrameInfo.TotalMetadataBufferSize - BufSize;
			hr = sci->desktopDupl->GetFrameDirtyRects(BufSize, reinterpret_cast<RECT*>(dirtyRects), &BufSize);
			if (FAILED(hr)){
				if (hr != DXGI_ERROR_ACCESS_LOST){
					iret=-7;
				}
				rgbimage->sizechangearea=0;
				rgbimage->sizemovearea=0;
				bok=false;
			}
			rgbimage->sizechangearea = BufSize / sizeof(RECT);
			if ((rgbimage->sizechangearea>0) and (rgbimage->sizechangearea<=RGB_IMAGE_DIFFSIZE)){
				RECT* rects = (RECT*)dirtyRects;
				for (int i = 0; i < rgbimage->sizechangearea; i++){
					RECT rect = rects[i];
					RGB_IMAGE_CHANGE_AREA* rgbchangearea = &rgbimage->changearea[i];
					rgbchangearea->x=rect.left;
					rgbchangearea->y=rect.top;
					rgbchangearea->width=rect.right-rect.left;
					rgbchangearea->height=rect.bottom-rect.top;
				}
			}

			if ((rgbimage->sizemovearea>RGB_IMAGE_DIFFSIZE) or (rgbimage->sizechangearea>RGB_IMAGE_DIFFSIZE)){
				rgbimage->sizemovearea = 0;
				rgbimage->sizechangearea = 1;
				RGB_IMAGE_CHANGE_AREA* rgbchangearea = &rgbimage->changearea[0];
				rgbchangearea->x=0;
				rgbchangearea->y=0;
				rgbchangearea->width=sci->w;
				rgbchangearea->height=sci->h;
			}

		}

		//CURSOR
		//updateCursorInfo(sci,&lFrameInfo);
	}
	if (bok){
		ID3D11Texture2D* desktopImage;
		hr = lDesktopResource->QueryInterface(__uuidof(ID3D11Texture2D), reinterpret_cast<void **>(&desktopImage));
		if (FAILED(hr)){
			lDesktopResource->Release();
			iret=-4;
			bok=false;
		}else{
			bool blackimg=true;
			sci->lDeskDupImmediateContext->CopyResource(sci->destImage, desktopImage);
			desktopImage->Release();
			lDesktopResource->Release();
			sci->lDeskDupImmediateContext->Map(sci->destImage, sci->subresource, D3D11_MAP_READ, 0, &sci->resource);
			//CONVERT TO RGB (PIXEL IS DXGI_FORMAT_B8G8R8A8_UNORM)
			unsigned char* sptr = reinterpret_cast<unsigned char*>(sci->resource.pData);
			int offsetSrc = 0;
			int offsetDst = 0;
			int rowOffset = sci->resource.RowPitch % sci->w;
			for (int row = 0; row < sci->h; ++row){
				for (int col = 0; col < sci->w; ++col){
					rgbimage->data[offsetDst] = sptr[offsetSrc+2];
					rgbimage->data[offsetDst+1] = sptr[offsetSrc+1];
					rgbimage->data[offsetDst+2] = sptr[offsetSrc];
					//pDest[offsetDst+4] = pSrc[offsetSrc+3];
					if ((sci->status==1) and (blackimg==true)){
						if ((sptr[offsetSrc]!=0) ||(sptr[offsetSrc+1]!=0) || (sptr[offsetSrc+2]!=0) || (sptr[offsetSrc+3]!=0)){
							blackimg=false;
						}
					}
					offsetSrc += 4;
					offsetDst += 3;
				}
				offsetSrc += rowOffset;
			}
			sci->lDeskDupImmediateContext->Unmap(sci->destImage, 0);
			if ((sci->status==1) && (blackimg==true)){
				iret=-8;
			}else{
				sci->status=2;
			}
		}
	}
	if (brelaseframe){
		hr = sci->desktopDupl->ReleaseFrame();
		if (FAILED(hr)){
			iret=-9;
			bok=false;
		}
	}
	return iret;
}

void DWAScreenCaptureInputKeyboard(const char* type,const char* key, bool ctrl, bool alt, bool shift, bool command){
	winInputs->keyboard(type, key, ctrl, alt, shift, command);
	if (strcmp(type,"CTRLALTCANC")==0){
		winDesktop->ctrlaltcanc();
	}
}

void DWAScreenCaptureInputMouse(MONITORS_INFO_ITEM* moninfoitem, int x, int y, int button, int wheel, bool ctrl, bool alt, bool shift, bool command){
	if (moninfoitem==NULL){
		winInputs->mouse(moninfoitem, x, y, button, wheel, ctrl, alt, shift, command);
	}else{
		MonitorInternalInfo* mi = (MonitorInternalInfo*)moninfoitem->internal;
		if ((mi->rotatedDegrees==0) || (mi->rotatedDegrees==90)){
			winInputs->mouse(moninfoitem, x, y, button, wheel, ctrl, alt, shift, command);
		}else{
			winInputs->mouse(moninfoitem, y, x, button, wheel, ctrl, alt, shift, command);
		}
	}

	/*if ((p==1) && (button==-1) && (mouseData==0) && (mx!=-1) && (my!=1)){ //INPUT BLOCKED BY FOREGROUND WINDOWS
		HWND h = GetForegroundWindow();
		if (h!=checkBlockInputsWin){
			POINT pnt;
			SetCursorPos(mx,my);
			if (GetCursorPos(&pnt)==TRUE){
				if ((mx!=pnt.x) || (my!=pnt.y)){
					SetForegroundWindow(hwndwts);
				}
			}else{
				sendInputs(inputs,p);
			}
		}else{
			sendInputs(inputs,p);
		}
		checkBlockInputsWin=h;
	}else{
		sendInputs(inputs,p);
	}*/
}

void DWAScreenCaptureCopy(){
	winDesktop->clearClipboardXP();
	winInputs->copy();
}

void DWAScreenCapturePaste(){
	winInputs->paste();
}

void DWAScreenCaptureGetClipboardChanges(CLIPBOARD_DATA* clipboardData){
	winDesktop->getClipboardChanges(clipboardData);
}

void DWAScreenCaptureSetClipboard(CLIPBOARD_DATA* clipboardData){
	winDesktop->setClipboard(clipboardData);
}

//TMP PRIVACY MODE
void DWAScreenCaptureSetPrivacyMode(bool b){
	return WindowsLoadLibSetPrivacyMode(b);
}

int wmain(int argc, wchar_t **argv) {
	/*DWAScreenCaptureLoad();
	MONITORS_INFO moninfo;
	DWAScreenCaptureGetMonitorsInfo(&moninfo);
	DWAScreenCaptureUnload();*/
	DWAScreenCaptureInputKeyboard("CHAR","76", false, false, false, false);
	return 0;
}

#endif
