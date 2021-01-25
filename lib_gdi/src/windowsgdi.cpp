/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/
#if defined OS_WINDOWS

#include "main.h"

CallbackEventMessage g_callEventMessage;
bool bclose=false;
JSONWriter jonextevent;

#define TRAYICONID	1
#define SWM_TRAYMSG	WM_APP

const char* className = "DWAWindowClass";
const char* classNameNotify = "DWAWindowNotifyClass";

struct DWAWindow { 
	int id;
	HWND hwnd;
	HDC hdc;
	COLORREF penColor;
	int penWidth;
	bool onCloseEvent;
};
std::vector<DWAWindow*> windowList;

struct DWANotifyIcon {
	int id;
	HWND hwnd;
	NOTIFYICONDATAW data;
};
std::vector<DWANotifyIcon*> notifyIconList;

struct DWAFont {
	int id;
	HFONT hFont;
};
std::vector<DWAFont*> fontList;

struct DWAImage {
	int id;
	ImageReader imageReader;
};
std::vector<DWAImage*> imageList;

DWAWindow* addWindow(int id,HWND hwnd){
	DWAWindow* ww = new DWAWindow();
	ww->id=id;
	ww->hwnd=hwnd;
	ww->penColor=RGB(0, 0, 0);
	ww->penWidth=1;
	ww->onCloseEvent=true;
	windowList.push_back(ww);
	return ww;
}

void removeWindowByHandle(HWND hwnd){
	for (unsigned int i=0;i<=windowList.size()-1;i++){
		if (windowList.at(i)->hwnd==hwnd){
			DWAWindow* dwa = windowList.at(i);
			windowList.erase(windowList.begin()+i);
			delete dwa;
			break;
		}
	}
}

DWAWindow* getWindowByHandle(HWND hwnd){
	if (windowList.size()==0){
		return NULL;
	}
	for (unsigned int i=0;i<=windowList.size()-1;i++){
		if (windowList.at(i)->hwnd==hwnd){
			return windowList.at(i);
		}
	}
	return NULL;
}

DWAWindow* getWindowByID(int id){
	if (windowList.size()==0){
		return NULL;
	}
	for (unsigned int i=0;i<=windowList.size()-1;i++){
		if (windowList.at(i)->id==id){
			return windowList.at(i);
		}
	}
	return NULL;
}

HWND getWindowHWNDByID(int id){
	DWAWindow* dwawin=getWindowByID(id);
	if (dwawin!=NULL){
		return dwawin->hwnd;
	}
	return NULL;
}

DWANotifyIcon* addNotifyIcon(int id){
	DWANotifyIcon* ww = new DWANotifyIcon();
	ww->id=id;
	notifyIconList.push_back(ww);
	return ww;
}

DWANotifyIcon* getNotifyIconByID(int id){
	if (notifyIconList.size()==0){
		return NULL;
	}
	for (unsigned int i=0;i<=notifyIconList.size()-1;i++){
		if (notifyIconList.at(i)->id==id){
			return notifyIconList.at(i);
		}
	}
	return NULL;
}

DWANotifyIcon* getNotifyIconByHandle(HWND hwnd){
	if (notifyIconList.size()==0){
		return NULL;
	}
	for (unsigned int i=0;i<=notifyIconList.size()-1;i++){
		if (notifyIconList.at(i)->hwnd==hwnd){
			return notifyIconList.at(i);
		}
	}
	return NULL;
}

DWAFont* addFont(int id){
	DWAFont* ft = new DWAFont();
	ft->id=id;
	fontList.push_back(ft);
	return ft;
}

DWAFont* getFontByID(int id){
	if (fontList.size()==0){
		return NULL;
	}
	for (unsigned int i=0;i<fontList.size();i++){
		if (fontList.at(i)->id==id){
			return fontList.at(i);
		}
	}
	return NULL;
}

DWAImage* addImage(int id){
	DWAImage* im = new DWAImage();
	im->id=id;
	imageList.push_back(im);
	return im;
}

DWAImage* getImageByID(int id){
	if (imageList.size()==0){
		return NULL;
	}
	for (unsigned int i=0;i<imageList.size();i++){
		if (imageList.at(i)->id==id){
			return imageList.at(i);
		}
	}
	return NULL;
}

ULONGLONG getDllVersion(LPCTSTR lpszDllName)
{
    ULONGLONG ullVersion = 0;
	HINSTANCE hinstDll;
    hinstDll = LoadLibrary(lpszDllName);
    if(hinstDll)
    {
        DLLGETVERSIONPROC pDllGetVersion;
        pDllGetVersion = (DLLGETVERSIONPROC)GetProcAddress(hinstDll, "DllGetVersion");
        if(pDllGetVersion)
        {
            DLLVERSIONINFO dvi;
            HRESULT hr;
            ZeroMemory(&dvi, sizeof(dvi));
            dvi.cbSize = sizeof(dvi);
            hr = (*pDllGetVersion)(&dvi);
            if(SUCCEEDED(hr))
				ullVersion = MAKEDLLVERULL(dvi.dwMajorVersion, dvi.dwMinorVersion,0,0);
        }
        FreeLibrary(hinstDll);
    }
    return ullVersion;
}

void destroyWindowInt(int id){
	DWAWindow* dwawin=getWindowByID(id);
	if (dwawin!=NULL){
		wchar_t cn[64] = L"";
		wsprintfW(cn, L"%s%d",className, dwawin->id);
		HWND hh=dwawin->hwnd;
		removeWindowByHandle(hh);
		DestroyWindow(hh);
		UnregisterClassW(cn,GetModuleHandle(NULL));
	}
}

LRESULT CALLBACK WndProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam){
	DWAWindow* dwawin=NULL;
	DWANotifyIcon* dwanfi=NULL;
	int iret = 0;
	int xPos = 0;
	int yPos = 0;
	int button=0;
	switch(msg){
		case WM_CREATE:
			break;
		case SWM_TRAYMSG:
			dwanfi=getNotifyIconByHandle(hwnd);
			if (dwanfi==NULL){
				break;
			}
			switch(lParam){
				case WM_LBUTTONUP:
					jonextevent.clear();
					jonextevent.beginObject();
					jonextevent.addString(L"name", L"NOTIFY");
					jonextevent.addString(L"action", L"ACTIVATE");
					jonextevent.addNumber(L"id", dwanfi->id);
					jonextevent.endObject();
					g_callEventMessage(jonextevent.getString().c_str());
					break;
				case WM_LBUTTONDBLCLK:
					jonextevent.clear();
					jonextevent.beginObject();
					jonextevent.addString(L"name", L"NOTIFY");
					jonextevent.addString(L"action", L"ACTIVATE");
					jonextevent.addNumber(L"id", dwanfi->id);
					jonextevent.endObject();
					g_callEventMessage(jonextevent.getString().c_str());
					break;
				case WM_RBUTTONDOWN:
				case WM_CONTEXTMENU:
					jonextevent.clear();
					jonextevent.beginObject();
					jonextevent.addString(L"name", L"NOTIFY");
					jonextevent.addString(L"action", L"CONTEXTMENU");
					jonextevent.addNumber(L"id", dwanfi->id);
					jonextevent.endObject();
					g_callEventMessage(jonextevent.getString().c_str());
					break;
				}
			iret = 1;
			break;
        case WM_CLOSE:
        	dwawin=getWindowByHandle(hwnd);
			if (dwawin==NULL){
				break;
			}
			if (dwawin->onCloseEvent){
				jonextevent.clear();
				jonextevent.beginObject();
				jonextevent.addString(L"name", L"WINDOW");
				jonextevent.addString(L"action", L"ONCLOSE");
				jonextevent.addNumber(L"id", dwawin->id);
				jonextevent.endObject();
				g_callEventMessage(jonextevent.getString().c_str());
			}else{
				destroyWindowInt(dwawin->id);
			}
        break;
		case WM_PAINT:
			dwawin=getWindowByHandle(hwnd);
			if (dwawin==NULL){
				break;
			}
			PAINTSTRUCT ps;
			dwawin->hdc = BeginPaint(dwawin->hwnd, &ps);
			SetBkMode(dwawin->hdc, TRANSPARENT);
			jonextevent.clear();
			jonextevent.beginObject();
			jonextevent.addString(L"name", L"REPAINT");
			jonextevent.addNumber(L"id", dwawin->id);
			jonextevent.addNumber(L"x", ps.rcPaint.left);
			jonextevent.addNumber(L"y", ps.rcPaint.top);
			jonextevent.addNumber(L"width", ps.rcPaint.right-ps.rcPaint.left);
			jonextevent.addNumber(L"height", ps.rcPaint.bottom-ps.rcPaint.top);
			jonextevent.endObject();
			g_callEventMessage(jonextevent.getString().c_str());
			EndPaint(dwawin->hwnd, &ps);
			dwawin->hdc=NULL;
	    break;
	    case WM_TIMER:
	    	g_callEventMessage(NULL);
		break;
	    case WM_ACTIVATE:
	    	dwawin=getWindowByHandle(hwnd);
			if (dwawin==NULL){
				break;
			}
			if ((wParam==WA_ACTIVE) || (wParam==WA_CLICKACTIVE)){
				jonextevent.clear();
				jonextevent.beginObject();
				jonextevent.addString(L"name", L"WINDOW");
				jonextevent.addString(L"action", L"ACTIVE");
				jonextevent.addNumber(L"id", dwawin->id);
				jonextevent.endObject();
				g_callEventMessage(jonextevent.getString().c_str());
			}else if (wParam==WA_INACTIVE){
				jonextevent.clear();
				jonextevent.beginObject();
				jonextevent.addString(L"name", L"WINDOW");
				jonextevent.addString(L"action", L"INACTIVE");
				jonextevent.addNumber(L"id", dwawin->id);
				jonextevent.endObject();
				g_callEventMessage(jonextevent.getString().c_str());
			}
		break;
		case WM_ACTIVATEAPP:
			dwawin=getWindowByHandle(hwnd);
			if (dwawin==NULL){
				break;
			}
			if (wParam==TRUE){
				jonextevent.clear();
				jonextevent.beginObject();
				jonextevent.addString(L"name", L"WINDOW");
				jonextevent.addString(L"action", L"ACTIVE");
				jonextevent.addNumber(L"id", dwawin->id);
				jonextevent.endObject();
				g_callEventMessage(jonextevent.getString().c_str());
			}else{
				jonextevent.clear();
				jonextevent.beginObject();
				jonextevent.addString(L"name", L"WINDOW");
				jonextevent.addString(L"action", L"INACTIVE");
				jonextevent.addNumber(L"id", dwawin->id);
				jonextevent.endObject();
				g_callEventMessage(jonextevent.getString().c_str());
			}
		break;
		case WM_KEYDOWN:
			dwawin=getWindowByHandle(hwnd);
			if (dwawin==NULL){
				break;
			}
			jonextevent.clear();
			jonextevent.beginObject();
			jonextevent.addString(L"name", L"KEYBOARD");
			jonextevent.addNumber(L"id", dwawin->id);
			if (wParam==VK_DELETE){
				jonextevent.addString(L"type", L"KEY");
				jonextevent.addString(L"value", L"DELETE");
			}else if (wParam==VK_LEFT){
				jonextevent.addString(L"type", L"KEY");
				jonextevent.addString(L"value", L"LEFT");
			}else if (wParam==VK_RIGHT){
				jonextevent.addString(L"type", L"KEY");
				jonextevent.addString(L"value", L"RIGHT");
			}else if (wParam==VK_HOME){
				jonextevent.addString(L"type", L"KEY");
				jonextevent.addString(L"value", L"HOME");
			}else if (wParam==VK_END){
				jonextevent.addString(L"type", L"KEY");
				jonextevent.addString(L"value", L"END");
			}else if (wParam==VK_TAB){
				jonextevent.addString(L"type", L"KEY");
				jonextevent.addString(L"value", L"TAB");
			}else{
				jonextevent.clear();
			}
			if (jonextevent.length()>0){
				jonextevent.addBoolean(L"shift", (BOOL)(GetKeyState(VK_SHIFT) & 0x8000) ? true : false);
				jonextevent.addBoolean(L"ctrl", (BOOL)(GetKeyState(VK_CONTROL) & 0x8000) ? true : false);
				jonextevent.addBoolean(L"alt", false);
				jonextevent.addBoolean(L"command", false);
				jonextevent.endObject();
				g_callEventMessage(jonextevent.getString().c_str());
			}
		break;
		case WM_SYSCHAR:
			dwawin=getWindowByHandle(hwnd);
			if (dwawin==NULL){
				break;
			}
			jonextevent.clear();
			jonextevent.beginObject();
			jonextevent.addString(L"name", L"KEYBOARD");
			jonextevent.addNumber(L"id", dwawin->id);
			jonextevent.addString(L"type", L"CHAR");
			jonextevent.addString(L"value", (wchar_t*)&wParam);
			jonextevent.addBoolean(L"shift", (BOOL)(GetKeyState(VK_SHIFT) & 0x8000) ? true : false);
			jonextevent.addBoolean(L"ctrl", (BOOL)(GetKeyState(VK_CONTROL) & 0x8000) ? true : false);
			jonextevent.addBoolean(L"alt", false);
			jonextevent.addBoolean(L"command", false);
			jonextevent.endObject();
			g_callEventMessage(jonextevent.getString().c_str());
		break;
		case WM_CHAR:
			dwawin=getWindowByHandle(hwnd);
			if (dwawin==NULL){
				break;
			}
			jonextevent.clear();
			jonextevent.beginObject();
			jonextevent.addString(L"name", L"KEYBOARD");
			jonextevent.addNumber(L"id", dwawin->id);
			if (wParam==VK_ESCAPE){
				jonextevent.addString(L"type", L"KEY");
				jonextevent.addString(L"value", L"ESCAPE");
			}else if (wParam==VK_RETURN){
				jonextevent.addString(L"type", L"KEY");
				jonextevent.addString(L"value", L"RETURN");
			}else if (wParam==VK_BACK){
				jonextevent.addString(L"type", L"KEY");
				jonextevent.addString(L"value", L"BACKSPACE");
			}else  if (wParam==24){ //CUT
				jonextevent.addString(L"type", L"COMMAND");
				jonextevent.addString(L"value", L"CUT");
			}else  if (wParam==3){ //COPY
				jonextevent.addString(L"type", L"COMMAND");
				jonextevent.addString(L"value", L"COPY");
			}else  if (wParam==22){ //PASTE
				jonextevent.addString(L"type", L"COMMAND");
				jonextevent.addString(L"value", L"PASTE");
			}else  if (wParam>=32){
				jonextevent.addString(L"type", L"CHAR");
				jonextevent.addString(L"value", (wchar_t*)&wParam);
			}else{
				jonextevent.clear();
			}
			if (jonextevent.length()>0){
				jonextevent.addBoolean(L"shift", (BOOL)(GetKeyState(VK_SHIFT) & 0x8000) ? true : false);
				jonextevent.addBoolean(L"ctrl", (BOOL)(GetKeyState(VK_CONTROL) & 0x8000) ? true : false);
				jonextevent.addBoolean(L"alt", false);
				jonextevent.addBoolean(L"command", false);
				jonextevent.endObject();
				g_callEventMessage(jonextevent.getString().c_str());
			}
		break;
		case WM_MOUSEMOVE:
			dwawin=getWindowByHandle(hwnd);
			if (dwawin==NULL){
				break;
			}
			xPos = GET_X_LPARAM(lParam);
			yPos = GET_Y_LPARAM(lParam);
			if (wParam & MK_LBUTTON){
				button=1;
			}else if (wParam & MK_RBUTTON){
				button=2;
			}
			jonextevent.clear();
			jonextevent.beginObject();
			jonextevent.addString(L"name", L"MOUSE");
			jonextevent.addString(L"action", L"MOVE");
			jonextevent.addNumber(L"id", dwawin->id);
			jonextevent.addNumber(L"x", xPos);
			jonextevent.addNumber(L"y", yPos);
			jonextevent.addNumber(L"button", button);
			jonextevent.endObject();
			g_callEventMessage(jonextevent.getString().c_str());
		break;
		case WM_LBUTTONDOWN:
			dwawin=getWindowByHandle(hwnd);
			if (dwawin==NULL){
				break;
			}
			xPos = GET_X_LPARAM(lParam);
			yPos = GET_Y_LPARAM(lParam);
			jonextevent.clear();
			jonextevent.beginObject();
			jonextevent.addString(L"name", L"MOUSE");
			jonextevent.addString(L"action", L"BUTTON_DOWN");
			jonextevent.addNumber(L"id", dwawin->id);
			jonextevent.addNumber(L"x", xPos);
			jonextevent.addNumber(L"y", yPos);
			jonextevent.addNumber(L"button", 1);
			jonextevent.endObject();
			g_callEventMessage(jonextevent.getString().c_str());
		break;
		case WM_LBUTTONUP:
			dwawin=getWindowByHandle(hwnd);
			if (dwawin==NULL){
				break;
			}
			xPos = GET_X_LPARAM(lParam);
			yPos = GET_Y_LPARAM(lParam);
			jonextevent.clear();
			jonextevent.beginObject();
			jonextevent.addString(L"name", L"MOUSE");
			jonextevent.addString(L"action", L"BUTTON_UP");
			jonextevent.addNumber(L"id", dwawin->id);
			jonextevent.addNumber(L"x", xPos);
			jonextevent.addNumber(L"y", yPos);
			jonextevent.addNumber(L"button", 1);
			jonextevent.endObject();
			g_callEventMessage(jonextevent.getString().c_str());
		break;
		case WM_RBUTTONDOWN:
			dwawin=getWindowByHandle(hwnd);
			if (dwawin==NULL){
				break;
			}
			xPos = GET_X_LPARAM(lParam);
			yPos = GET_Y_LPARAM(lParam);
			jonextevent.clear();
			jonextevent.beginObject();
			jonextevent.addString(L"name", L"MOUSE");
			jonextevent.addString(L"action", L"BUTTON_DOWN");
			jonextevent.addNumber(L"id", dwawin->id);
			jonextevent.addNumber(L"x", xPos);
			jonextevent.addNumber(L"y", yPos);
			jonextevent.addNumber(L"button", 2);
			jonextevent.endObject();
			g_callEventMessage(jonextevent.getString().c_str());
		break;
        case WM_RBUTTONUP:
        	dwawin=getWindowByHandle(hwnd);
			if (dwawin==NULL){
				break;
			}
			xPos = GET_X_LPARAM(lParam);
			yPos = GET_Y_LPARAM(lParam);
			jonextevent.clear();
			jonextevent.beginObject();
			jonextevent.addString(L"name", L"MOUSE");
			jonextevent.addString(L"action", L"BUTTON_UP");
			jonextevent.addNumber(L"id", dwawin->id);
			jonextevent.addNumber(L"x", xPos);
			jonextevent.addNumber(L"y", yPos);
			jonextevent.addNumber(L"button", 2);
			jonextevent.endObject();
			g_callEventMessage(jonextevent.getString().c_str());
		break;
        default:
			if(IsWindowUnicode(hwnd))
				iret = DefWindowProcW(hwnd, msg, wParam, lParam);
			else
				iret = DefWindowProcA(hwnd, msg, wParam, lParam);
    }
	return iret;
}

HICON CreateIconFromImage(wchar_t* iconPath){
	ImageReader imgr;
	imgr.load(iconPath);
	if (!imgr.isLoaded()){
		return NULL;
	}
	HDC hMemDC;
	DWORD dwWidth, dwHeight;
	BITMAPV5HEADER bi;
	HBITMAP hBitmap, hOldBitmap;
	void *lpBits;
	HICON hIcon = NULL;
	dwWidth = imgr.getWidth();
	dwHeight = imgr.getHeight();
	ZeroMemory(&bi, sizeof(BITMAPV5HEADER));
	bi.bV5Size = sizeof(BITMAPV5HEADER);
	bi.bV5Width = dwWidth;
	bi.bV5Height = dwHeight;
	bi.bV5Planes = 1;
	bi.bV5BitCount = 32;
	bi.bV5Compression = BI_BITFIELDS;
	bi.bV5RedMask = 0x00FF0000;
	bi.bV5GreenMask = 0x0000FF00;
	bi.bV5BlueMask = 0x000000FF;
	bi.bV5AlphaMask = 0xFF000000;
	HDC hdc;
	hdc = GetDC(NULL);
	hBitmap = CreateDIBSection(hdc, (BITMAPINFO *)&bi, DIB_RGB_COLORS,(void **)&lpBits, NULL, (DWORD)0);
	hMemDC = CreateCompatibleDC(hdc);
	ReleaseDC(NULL, hdc);
	hOldBitmap = (HBITMAP)SelectObject(hMemDC, hBitmap);
	PatBlt(hMemDC, 0, 0, dwWidth, dwHeight, WHITENESS);
	SetTextColor(hMemDC, RGB(0, 0, 0));
	SetBkMode(hMemDC, TRANSPARENT);
	DWORD *lpdwPixel;
	lpdwPixel = (DWORD *)lpBits;
	for (int cy=imgr.getHeight()-1;cy>=0;cy--){
		for (int cx=0;cx<=imgr.getWidth()-1;cx++){
			unsigned char r;
			unsigned char g;
			unsigned char b;
			unsigned char a;
			imgr.getPixel(cx, cy, &r, &g, &b, &a);
			*lpdwPixel = a << 24 | r << 16 | g << 8 | b << 0;
			lpdwPixel++;
		}
	}

	SelectObject(hMemDC, hOldBitmap);
	DeleteDC(hMemDC);
	HBITMAP hMonoBitmap = CreateBitmap(dwWidth, dwHeight, 1, 1, NULL);
	ICONINFO ii;
	ii.fIcon = TRUE;
	ii.xHotspot = 0;
	ii.yHotspot = 0;
	ii.hbmMask = hMonoBitmap;
	ii.hbmColor = hBitmap;
	hIcon = CreateIconIndirect(&ii);
	DeleteObject(hBitmap);
	DeleteObject(hMonoBitmap);
	return hIcon;
}

void DWAGDIDestroyNotifyIcon(int id){
	for (unsigned int i=0;i<=notifyIconList.size()-1;i++){
		if (notifyIconList.at(i)->id==id){
			DWANotifyIcon* dwanfi = notifyIconList.at(i);
			dwanfi->data.uFlags = 0;
			Shell_NotifyIconW(NIM_DELETE,&dwanfi->data);
			wchar_t cn[64] = L"";
			wsprintfW(cn, L"%s%d",classNameNotify,id);
			HWND hh=dwanfi->hwnd;
			DestroyWindow(hh);
			UnregisterClassW(cn,GetModuleHandle(NULL));
			notifyIconList.erase(notifyIconList.begin()+i);
			delete dwanfi;
			break;
		}
	}
}

void DWAGDIUpdateNotifyIcon(int id, wchar_t* iconPath,wchar_t* toolTip){
	DWANotifyIcon* dwanfi=getNotifyIconByID(id);
	if (dwanfi!=NULL){
		dwanfi->data.hIcon = CreateIconFromImage(iconPath);
		wcscpy(dwanfi->data.szTip,toolTip);
		Shell_NotifyIconW(NIM_MODIFY,&dwanfi->data);
		if(dwanfi->data.hIcon && DestroyIcon(dwanfi->data.hIcon)){
			dwanfi->data.hIcon = NULL;
		}
	}
}

void DWAGDICreateNotifyIcon(int id, wchar_t* iconPath,wchar_t* toolTip){
	WNDCLASSEXW wc;
	HINSTANCE hInstance = GetModuleHandle(NULL);
	wchar_t cn[64] = L"";
	wsprintfW(cn, L"%s%d",classNameNotify,id);
	wc.cbSize        = sizeof(WNDCLASSEX);
	wc.style         = 0;
	wc.lpfnWndProc   = WndProc;
	wc.cbClsExtra    = 0;
	wc.cbWndExtra    = 0;
	wc.hInstance     = hInstance;
	wc.hIcon         = NULL;
	wc.hCursor       = NULL;
	wc.hbrBackground = NULL;
	wc.lpszMenuName  = NULL;
	wc.lpszClassName = cn;
	wc.hIconSm       = NULL;

	if (RegisterClassExW(&wc)){
		HWND hwnd = CreateWindowExW(0, cn, NULL, WS_POPUPWINDOW, 0, 0, 0, 0, NULL, NULL, hInstance, NULL);
		if (hwnd!=NULL){
			DWANotifyIcon* dwanfi=addNotifyIcon(id);
			dwanfi->hwnd = hwnd;
			ZeroMemory(&dwanfi->data,sizeof(NOTIFYICONDATA));
			ULONGLONG ullVersion = getDllVersion("Shell32.dll");
			if(ullVersion >= MAKEDLLVERULL(6,0,6,0))
				dwanfi->data.cbSize = sizeof(NOTIFYICONDATA);
			else if(ullVersion >= MAKEDLLVERULL(6,0,0,0))
				dwanfi->data.cbSize = 504; //NOTIFYICONDATA_V3_SIZE;
			else if(ullVersion >= MAKEDLLVERULL(5,0,0,0))
				dwanfi->data.cbSize = NOTIFYICONDATA_V2_SIZE;
			else
				dwanfi->data.cbSize = NOTIFYICONDATA_V1_SIZE;
			dwanfi->data.uID = TRAYICONID;
			dwanfi->data.uFlags = NIF_ICON | NIF_MESSAGE | NIF_TIP;
			dwanfi->data.hWnd = hwnd;
			dwanfi->data.uCallbackMessage = SWM_TRAYMSG;
			DWAGDIUpdateNotifyIcon(id,iconPath,toolTip);
			dwanfi->data.hIcon = CreateIconFromImage(iconPath);
			wcscpy(dwanfi->data.szTip,toolTip);
			Shell_NotifyIconW(NIM_ADD,&dwanfi->data);
			if(dwanfi->data.hIcon && DestroyIcon(dwanfi->data.hIcon)){
				dwanfi->data.hIcon = NULL;
			}
		}else{
			UnregisterClassW(cn,hInstance);
		}
	}
}

void DWAGDINewWindow(int id, int tp, int x, int y, int w, int h, wchar_t* iconPath){
	WNDCLASSEXW wc;    
	HINSTANCE hInstance = GetModuleHandle(NULL);
	HICON hIcon = NULL;
	if (iconPath!=NULL){
		hIcon=CreateIconFromImage(iconPath);
	}

	wchar_t cn[64] = L""; 
	wsprintfW(cn, L"%s%d",className, id);
	
	wc.cbSize        = sizeof(WNDCLASSEX);
    wc.style         = 0;
    wc.lpfnWndProc   = WndProc;
    wc.cbClsExtra    = 0;
    wc.cbWndExtra    = 0;
    wc.hInstance     = hInstance;
    wc.hIcon         = hIcon;
    wc.hCursor       = LoadCursor(NULL, IDC_ARROW);
    wc.hbrBackground = (HBRUSH)(COLOR_WINDOW+1);
    wc.lpszMenuName  = NULL;
    wc.lpszClassName = cn;
    wc.hIconSm       = hIcon;
	
	if(!RegisterClassExW(&wc)){
        return;
    }
	
	int dwStyle=WS_OVERLAPPEDWINDOW;
	int dwStyleEx=0;
	if (tp==WINDOW_TYPE_NORMAL_NOT_RESIZABLE){
		dwStyle=WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX;
	}else if (tp==WINDOW_TYPE_DIALOG){
		dwStyle=WS_CAPTION|WS_POPUPWINDOW;
	}else if (tp==WINDOW_TYPE_TOOL){
		dwStyle=WS_CAPTION|WS_POPUPWINDOW;
		dwStyleEx=WS_EX_TOOLWINDOW;
	}else if (tp==WINDOW_TYPE_POPUP){
		dwStyle=WS_POPUP;
		dwStyleEx=WS_EX_TOPMOST|WS_EX_TOOLWINDOW;
	}	

	HWND hwnd;
	hwnd = CreateWindowExW(dwStyleEx, cn, NULL, dwStyle,x, y, w, h, NULL, NULL, hInstance, NULL);

	if(hwnd == NULL) {
		UnregisterClassW(cn,hInstance);
        return;
    }

	RECT winRC,clientRC;
    GetWindowRect(hwnd,&winRC); 
    GetClientRect(hwnd,&clientRC);
    int dx = w-(clientRC.right-clientRC.left); 
    int dy = h-(clientRC.bottom-clientRC.top); 
	int nx=x;
	int nw=w;
	if (dx>0){
		nw+=dx;
		nx+=(dx/2);
	}
	int ny=y;
	int nh=h;
	if (dy>0){
		nh+=dy;
		ny+=(dy/2);
	}
	SetWindowPos(hwnd, NULL, nx, ny, nw, nh, SWP_NOZORDER | SWP_NOMOVE | SWP_NOACTIVATE) ;
	addWindow(id, hwnd);
}

void DWAGDIDestroyWindow(int id){
	DWAWindow* dwawin=getWindowByID(id);
	if (dwawin!=NULL){
		dwawin->onCloseEvent=false;
		PostMessageW(dwawin->hwnd,WM_CLOSE,NULL,NULL);
	}
}

void DWAGDISetClipboardText(wchar_t* str){
    if (OpenClipboard(NULL)){
        EmptyClipboard();
        HGLOBAL hClipboardData;
		size_t size = (wcslen(str)+1) * sizeof(wchar_t);
        hClipboardData = GlobalAlloc(NULL, size);
        wchar_t* pchData = (wchar_t*)GlobalLock(hClipboardData);
		memcpy(pchData, str, size);
        SetClipboardData(CF_UNICODETEXT, hClipboardData);
        GlobalUnlock(hClipboardData);
        CloseClipboard();
    }
}

wchar_t* DWAGDIGetClipboardText(){
	if (OpenClipboard(NULL)){
		HANDLE clip = GetClipboardData(CF_UNICODETEXT);
		wchar_t * c;
		c = (wchar_t*)clip;
		CloseClipboard();
		return (wchar_t*)c;
	}
	return L"";
}

void DWAGDIGetScreenSize(int* size){
	size[0] = GetSystemMetrics(SM_CXSCREEN);
	size[1] = GetSystemMetrics(SM_CYSCREEN);
}

void DWAGDIGetImageSize(wchar_t* fname, int* size){
	ImageReader imageReader;
	imageReader.load(fname);
	size[0]=imageReader.getWidth();
	size[1]=imageReader.getHeight();
}

void DWAGDIGetMousePosition(int* pos){
	POINT pt;
	GetCursorPos(&pt);
	pos[0]=pt.x;
	pos[1]=pt.y;
}

void DWAGDIClipRectangle(int id, int x, int y, int w, int h){
	DWAWindow* dwawin=getWindowByID(id);
	if (dwawin!=NULL){
		SelectClipRgn(dwawin->hdc, NULL); 
		HRGN hrgn = CreateRectRgn(x,y,x+w,y+h);
		SelectClipRgn(dwawin->hdc, hrgn); 
		DeleteObject(hrgn);
	}
}

void DWAGDIClearClipRectangle(int id){
	DWAWindow* dwawin=getWindowByID(id);
	if (dwawin!=NULL){
		SelectClipRgn(dwawin->hdc, NULL); 
	}
}

void DWAGDIPenColor(int id, int r, int g, int b){
	DWAWindow* dwawin=getWindowByID(id);
	if (dwawin!=NULL){
		dwawin->penColor = RGB(r, g, b);
	}
}

void DWAGDIPenWidth(int id, int w){
	DWAWindow* dwawin=getWindowByID(id);
	if (dwawin!=NULL){
		dwawin->penWidth=w;
	}
}

void DWAGDIDrawLine(int id, int x1, int y1, int x2,int y2){
	DWAWindow* dwawin=getWindowByID(id);
	if (dwawin!=NULL){
		HPEN hPenOld;
		HPEN hLinePen;
		hLinePen = CreatePen(PS_SOLID, dwawin->penWidth, dwawin->penColor);
		hPenOld = (HPEN)SelectObject(dwawin->hdc, hLinePen);

		if (x2>x1){
			x2++;
		}else if (x1>x2){
			x2--;
		}
		if (y2>y1){
			y2++;
		}else if (y1>y2){
			y2--;
		}

		MoveToEx(dwawin->hdc, x1, y1, NULL);
		LineTo(dwawin->hdc, x2, y2);

		SelectObject(dwawin->hdc, hPenOld);
		DeleteObject(hLinePen);
	}
}

void DWAGDIDrawEllipse(int id, int x, int y, int w,int h){
	DWAWindow* dwawin=getWindowByID(id);
	if (dwawin!=NULL){
		HPEN hLinePen = CreatePen(PS_SOLID, dwawin->penWidth, dwawin->penColor);
		HPEN hPenOld = (HPEN)SelectObject(dwawin->hdc, hLinePen);
		SetDCBrushColor(dwawin->hdc, dwawin->penColor);
		HGDIOBJ hbr = GetStockObject(NULL_BRUSH);
		HBRUSH hbrOld = (HBRUSH)SelectObject(dwawin->hdc, hbr);
		Ellipse(dwawin->hdc,x, y, x+w, y+h);
		SelectObject(dwawin->hdc, hbrOld);
		SelectObject(dwawin->hdc, hPenOld);
		DeleteObject(hbr);
		DeleteObject(hLinePen);
	}
}

void DWAGDIFillEllipse(int id, int x, int y, int w,int h){
	DWAWindow* dwawin=getWindowByID(id);
	if (dwawin!=NULL){
		HPEN hLinePen = CreatePen(PS_SOLID, dwawin->penWidth, dwawin->penColor);
		HPEN hPenOld = (HPEN)SelectObject(dwawin->hdc, hLinePen);
		SetDCBrushColor(dwawin->hdc, dwawin->penColor);
		HGDIOBJ hbr = GetStockObject(DC_BRUSH);
		HBRUSH hbrOld = (HBRUSH)SelectObject(dwawin->hdc, hbr);
		Ellipse(dwawin->hdc,x, y, x+w, y+h);
		SelectObject(dwawin->hdc, hbrOld);
		SelectObject(dwawin->hdc, hPenOld);
		DeleteObject(hbr);
		DeleteObject(hLinePen);
	}
}

void DWAGDIFillRectangle(int id, int x, int y, int w, int h){
	DWAWindow* dwawin=getWindowByID(id);
	if (dwawin!=NULL){
		HBRUSH hbrBkgnd = CreateSolidBrush(dwawin->penColor);
		RECT rec;
		rec.left=x;
		rec.top=y;
		rec.right=x+w;
		rec.bottom=y+h;
		FillRect(dwawin->hdc,&rec,hbrBkgnd);
		DeleteObject(hbrBkgnd);
	}
}


void DWAGDIDrawText(int id, int fntid, wchar_t* str, int x, int y){
	DWAFont* dwf = getFontByID(fntid);
	DWAWindow* dwawin=getWindowByID(id);
	if ((dwawin!=NULL) && (dwf!=NULL)){
		SetTextColor(dwawin->hdc,dwawin->penColor);
		SelectObject(dwawin->hdc,dwf->hFont);
		RECT rec;
		rec.left=x;
		rec.top=y;
		rec.right=0;
		rec.bottom=0;	
		DrawTextExW(dwawin->hdc,str,-1,&rec,DT_LEFT | DT_NOCLIP,NULL);
	}
}

int DWAGDIGetTextHeight(int id, int fntid){
	DWAFont* dwf = getFontByID(fntid);
	DWAWindow* dwawin=getWindowByID(id);
	if ((dwawin!=NULL) && (dwf!=NULL)){
		HWND hwnd=dwawin->hwnd;
		TEXTMETRIC lptm;
		HDC dc=NULL;
		if (dwawin->hdc==NULL){
			dc=GetDC(hwnd);
		}else{
			dc=dwawin->hdc;
		}
		SelectObject(dc,dwf->hFont);
		GetTextMetrics(dc,&lptm);
		return lptm.tmHeight;
	}
	return 0;
}

int DWAGDIGetTextWidth(int id, int fntid, wchar_t* str){
	DWAFont* dwf = getFontByID(fntid);
	DWAWindow* dwawin=getWindowByID(id);
	if ((dwawin!=NULL) && (dwf!=NULL)){
		HWND hwnd=dwawin->hwnd;
		RECT rec;
		rec.left=0;
		rec.top=0;
		rec.right=100000;
		rec.bottom=100000;
		HDC dc=NULL;
		if (dwawin->hdc==NULL){
			dc=GetDC(hwnd);
		}else{
			dc=dwawin->hdc;
		}
		SelectObject(dc,dwf->hFont);
		if (DrawTextExW(dc,str,-1,&rec,DT_LEFT | DT_NOCLIP | DT_CALCRECT,NULL)!=0){
			return rec.right-rec.left;
		}
	}
	return 0;
}

void DWAGDIRepaint(int id, int x, int y, int w,int h){
	DWAWindow* dwawin=getWindowByID(id);
	if (dwawin!=NULL){
		RECT rec;
		rec.left=x;
		rec.top=y;
		rec.right=x+w;
		rec.bottom=y+h;
		HWND hwnd=dwawin->hwnd;
		InvalidateRect(hwnd,&rec,FALSE);
	}
}

void DWAGDIShow(int id,int md){
	DWAWindow* dwawin=getWindowByID(id);
	if (dwawin!=NULL){
		ShowWindow(dwawin->hwnd,SW_SHOW);
		UpdateWindow(dwawin->hwnd);
	}
}

void DWAGDIToFront(int id){
	DWAWindow* dwawin=getWindowByID(id);
	if (dwawin!=NULL){
		ShowWindow(dwawin->hwnd, SW_RESTORE);
		SetForegroundWindow(dwawin->hwnd);
		UpdateWindow(dwawin->hwnd);
	}
}

void DWAGDIHide(int id){
	DWAWindow* dwawin=getWindowByID(id);
	if (dwawin!=NULL){
		ShowWindow(dwawin->hwnd,SW_HIDE);
		UpdateWindow(dwawin->hwnd);
	}
}

void DWAGDISetTitle(int id, wchar_t* title){
	DWAWindow* dwawin=getWindowByID(id);
	if (dwawin!=NULL){
		SetWindowTextW(dwawin->hwnd, title);
	}
}

void DWAGDILoadFont(int id,wchar_t* name){
	DWAFont* dwf = addFont(id);
	//ww->hFont=CreateFont(0,0,0,0,FW_NORMAL,FALSE,FALSE,FALSE,DEFAULT_CHARSET,OUT_OUTLINE_PRECIS,CLIP_DEFAULT_PRECIS,CLEARTYPE_QUALITY, VARIABLE_PITCH,TEXT("Arial"));
	//ww->hFont = CreateFont(-MulDiv(12, GetDeviceCaps(dwawin->hdc, LOGPIXELSY), 72),0,0,0,FW_NORMAL,FALSE,FALSE,FALSE,DEFAULT_CHARSET,OUT_OUTLINE_PRECIS,CLIP_DEFAULT_PRECIS,CLEARTYPE_QUALITY, VARIABLE_PITCH,TEXT("Arial"));
	dwf->hFont = CreateFont(-14,0,0,0,FW_NORMAL,FALSE,FALSE,FALSE,DEFAULT_CHARSET,OUT_OUTLINE_PRECIS,CLIP_DEFAULT_PRECIS,CLEARTYPE_QUALITY, VARIABLE_PITCH,TEXT("Arial"));
	//ww->hFont = CreateFont(16,0,0,0,FW_NORMAL,FALSE,FALSE,FALSE,DEFAULT_CHARSET,OUT_OUTLINE_PRECIS,CLIP_DEFAULT_PRECIS,CLEARTYPE_QUALITY, VARIABLE_PITCH,TEXT("Arial"));
}

void DWAGDIUnloadFont(int id){
	for (unsigned int i=0;i<fontList.size();i++){
		DWAFont* dwf = fontList.at(i);
		if (dwf->id==id){
			DeleteObject(dwf->hFont);
			fontList.erase(fontList.begin()+i);
			delete dwf;
			break;
		}
	}

}

void DWAGDILoadImage(int id, wchar_t* fname, int* size){
	DWAImage* dwaim = addImage(id);
	dwaim->imageReader.load(fname);
	size[0]=dwaim->imageReader.getWidth();
	size[1]=dwaim->imageReader.getHeight();
}

void DWAGDIUnloadImage(int id){
	for (unsigned int i=0;i<imageList.size();i++){
		DWAImage* dwaim = imageList.at(i);
		if (dwaim->id==id){
			dwaim->imageReader.destroy();
			imageList.erase(imageList.begin()+i);
			delete dwaim;
			break;
		}
	}
}

void DWAGDIDrawImage(int id, int imgid, int x, int y){
	DWAWindow* dwawin = getWindowByID(id);
	DWAImage* dwaim = getImageByID(imgid);
	if ((dwawin!=NULL) && (dwaim!=NULL)){
		for (int cx=0;cx<=dwaim->imageReader.getWidth()-1;cx++){
			for (int cy=0;cy<=dwaim->imageReader.getHeight()-1;cy++){
				unsigned char r;
				unsigned char g;
				unsigned char b;
				unsigned char a;
				dwaim->imageReader.getPixel(cx, cy, &r, &g, &b, &a);
				COLORREF  c = b << 16 | g << 8 | r << 0;
				if (a>128){
					SetPixel(dwawin->hdc,x+cx, y+cy,c);
				}
			}
		}
	}
}

void DWAGDILoop(CallbackEventMessage callback){
	bclose=false;
	g_callEventMessage = callback;
	g_callEventMessage(NULL);
	MSG Msg;
	while(!bclose){
		if (PeekMessageW(&Msg, NULL, 0, 0, PM_REMOVE)==TRUE){
			TranslateMessage(&Msg);
			DispatchMessageW(&Msg);
		}else{
			g_callEventMessage(NULL);
			Sleep(10);
		}
	}
}

void DWAGDIEndLoop(){
	if (!bclose){
		PostQuitMessage(0);
	}
	bclose=true;
}

int isUserInAdminGroup(){
	BOOL fInAdminGroup = FALSE;
	DWORD dwError = ERROR_SUCCESS;
	HANDLE hToken = NULL;
	HANDLE hTokenToCheck = NULL;
	try{
		DWORD cbSize = 0;
		OSVERSIONINFO osver = { sizeof(osver) };

		if (!OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY | TOKEN_DUPLICATE,
			&hToken)){
			dwError = GetLastError();
			goto Cleanup;
		}

		if (!GetVersionEx(&osver)){
			dwError = GetLastError();
			goto Cleanup;
		}

		if (osver.dwMajorVersion >= 6){
			TOKEN_ELEVATION_TYPE elevType;
			if (!GetTokenInformation(hToken, TokenElevationType, &elevType,
				sizeof(elevType), &cbSize))
			{
				dwError = GetLastError();
				goto Cleanup;
			}

			if (TokenElevationTypeLimited == elevType){
				if (!GetTokenInformation(hToken, TokenLinkedToken, &hTokenToCheck,
					sizeof(hTokenToCheck), &cbSize))
				{
					dwError = GetLastError();
					goto Cleanup;
				}
			}
		}

		if (!hTokenToCheck){
			if (!DuplicateToken(hToken, SecurityIdentification, &hTokenToCheck))
			{
				dwError = GetLastError();
				goto Cleanup;
			}
		}

		BYTE adminSID[SECURITY_MAX_SID_SIZE];
		cbSize = sizeof(adminSID);
		if (!CreateWellKnownSid(WinBuiltinAdministratorsSid, NULL, &adminSID,
			&cbSize))
		{
			dwError = GetLastError();
			goto Cleanup;
		}
		if (!CheckTokenMembership(hTokenToCheck, &adminSID, &fInAdminGroup)) {
			dwError = GetLastError();
			goto Cleanup;
		}
	}catch(...){
		fInAdminGroup = FALSE;
	}
Cleanup:
    if (hToken){
        CloseHandle(hToken);
        hToken = NULL;
    }
    if (hTokenToCheck){
        CloseHandle(hTokenToCheck);
        hTokenToCheck = NULL;
    }

    if (ERROR_SUCCESS != dwError){
    	return 0;
    }

    if (fInAdminGroup==TRUE){
		return 1;
	}
	return 0;
}


int isRunAsAdmin(){
    BOOL fIsRunAsAdmin = FALSE;
    DWORD dwError = ERROR_SUCCESS;
	PSID pAdministratorsGroup = NULL;
    try{
		SID_IDENTIFIER_AUTHORITY NtAuthority = SECURITY_NT_AUTHORITY;
		if (!AllocateAndInitializeSid(
			&NtAuthority,
			2,
			SECURITY_BUILTIN_DOMAIN_RID,
			DOMAIN_ALIAS_RID_ADMINS,
			0, 0, 0, 0, 0, 0,
			&pAdministratorsGroup))
		{
			dwError = GetLastError();
			goto Cleanup;
		}

		if (!CheckTokenMembership(NULL, pAdministratorsGroup, &fIsRunAsAdmin)){
			dwError = GetLastError();
			goto Cleanup;
		}
	}catch(...){
		fIsRunAsAdmin = FALSE;
	}
Cleanup:
    if (pAdministratorsGroup){
        FreeSid(pAdministratorsGroup);
        pAdministratorsGroup = NULL;
    }
    if (ERROR_SUCCESS != dwError){
    	return 0;
    }
    if (fIsRunAsAdmin==TRUE){
		return 1;
	}
	return 0;
}


int isProcessElevated(){
    BOOL fIsElevated = FALSE;
    DWORD dwError = ERROR_SUCCESS;
	HANDLE hToken = NULL;
    try{
		if (!OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &hToken)){
			dwError = GetLastError();
			goto Cleanup;
		}
		TOKEN_ELEVATION elevation;
		DWORD dwSize;
		if (!GetTokenInformation(hToken, TokenElevation, &elevation,
			sizeof(elevation), &dwSize)){
			dwError = GetLastError();
			if (dwError==ERROR_INVALID_PARAMETER){
				fIsElevated = TRUE;
			}
			goto Cleanup;
		}
		fIsElevated = elevation.TokenIsElevated;
	}catch(...){
		fIsElevated = TRUE;
	}
Cleanup:
    if (hToken){
        CloseHandle(hToken);
        hToken = NULL;
    }
    if (fIsElevated==TRUE){
		return 1;
	}
    if (ERROR_SUCCESS != dwError){
    	return 0;
	}
	return 0;
}

int isTaskRunning(int pid) {
	DWORD dwDesiredAccess = SYNCHRONIZE;
    BOOL  bInheritHandle  = FALSE;
	HANDLE hProcess = OpenProcess(dwDesiredAccess, bInheritHandle, pid);
    if (hProcess == NULL){
        return FALSE;
    }
	DWORD ret = WaitForSingleObject(hProcess, 0);
	CloseHandle(hProcess);
	if (ret == WAIT_TIMEOUT){
		return 1;
	}
	return 0;
}
#endif
