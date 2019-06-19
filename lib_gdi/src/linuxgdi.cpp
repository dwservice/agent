/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/
#if defined OS_LINUX

#include "main.h"

#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <X11/Xlib.h>
#include <X11/Xatom.h>
#include <X11/Xutil.h>
#include <X11/xpm.h>
#include <X11/XKBlib.h>
#include <X11/keysym.h>
#include <wchar.h>
#include <locale.h>
#include <sys/timeb.h>
#include <vector>


bool exitloop=false;
bool binit=false;
Display * display;
int screenid;
Screen* screen;
Window root;
XIM im;
XIMStyle best_style;
XFontSet fontset;
int fontascent=0;
int fontheight=0;
Atom wm_protocols;
Atom wm_delete_window;

Colormap colormap;

struct DWAWindow {
	int id;
	Window win;
	XIC ic;
	GC gc;
	XColor curcol;
	int x;
	int y;
};

std::vector<DWAWindow*> windowList;
int windowListCnt=0;

DWAWindow* addWindow(Window win,GC gc,XIC ic){
	windowListCnt++;
	DWAWindow* ww = new DWAWindow();
	ww->id=windowListCnt;
	ww->ic=ic;
	ww->win=win;
	ww->gc=gc;
	ww->x=0;
	ww->y=0;
	windowList.push_back(ww);
	return ww;
}

void removeWindowByHandle(Window win){
	for (unsigned int i=0;i<windowList.size();i++){
		if (windowList.at(i)->win==win){
			DWAWindow* dwa = windowList.at(i);
			windowList.erase(windowList.begin()+i);
			delete dwa;
			break;
		}
	}
}

DWAWindow* getWindowByHandle(Window win){
	if (windowList.size()==0){
		return NULL;
	}
	for (unsigned int i=0;i<windowList.size();i++){
		if (windowList.at(i)->win==win){
			return windowList.at(i);
		}
	}
	return NULL;
}

DWAWindow* getWindowByID(int id){
	if (windowList.size()==0){
		return NULL;
	}
	for (unsigned int i=0;i<windowList.size();i++){
		if (windowList.at(i)->id==id){
			return windowList.at(i);
		}
	}
	return NULL;
}



//PER TIMER
int x11_fd;
fd_set in_fds;
struct timeval tv;

CallbackTypeRepaint g_callbackRepaint;
CallbackTypeKeyboard g_callbackKeyboard;
CallbackTypeMouse g_callbackMouse;
CallbackTypeWindow g_callbackWindow;
CallbackTypeTimer g_callbackTimer;


void setCallbackRepaint(CallbackTypeRepaint callback){
	g_callbackRepaint = callback;
}

void setCallbackKeyboard(CallbackTypeKeyboard callback){
	g_callbackKeyboard = callback;
}

void setCallbackMouse(CallbackTypeMouse callback){
	g_callbackMouse=callback;
}

void setCallbackWindow(CallbackTypeWindow callback){
	g_callbackWindow=callback;
}

void setCallbackTimer(CallbackTypeTimer callback){
	g_callbackTimer=callback;
}

void fireCallBackRepaint(int id, int x,int y,int w, int h){
	if(g_callbackRepaint)
		g_callbackRepaint(id, x, y, w, h);
}

void fireCallBackKeyboard(int id, wchar_t* type, wchar_t* c,XKeyEvent xkey){
	if(g_callbackKeyboard)
		g_callbackKeyboard(id, type, c,
				xkey.state & ShiftMask ? true : false,
				xkey.state & ControlMask ? true : false,
				false,false);
}

void fireCallBackMouse(int id, wchar_t* type, int x, int y, int button){
	if(g_callbackMouse)
		g_callbackMouse(id, type, x, y, button);
}

bool fireCallBackWindow(int id, wchar_t* type){
	if(g_callbackWindow)
		return g_callbackWindow(id,type);
	return true;
}

void fireCallBackTimer(){
	if(g_callbackTimer)
		g_callbackTimer();
}

long getMillisecons(){
	struct timeb tmb;
	ftime(&tmb);
	return (tmb.time * 1000) + tmb.millitm;
}


XIMStyle ChooseBetterStyle(XIMStyle style1,XIMStyle style2){
    XIMStyle s,t;
    XIMStyle preedit = XIMPreeditArea | XIMPreeditCallbacks |
        XIMPreeditPosition | XIMPreeditNothing | XIMPreeditNone;
    XIMStyle status = XIMStatusArea | XIMStatusCallbacks |
        XIMStatusNothing | XIMStatusNone;
    if (style1 == 0) return style2;
    if (style2 == 0) return style1;
    if ((style1 & (preedit | status)) == (style2 & (preedit | status)))
        return style1;
    s = style1 & preedit;
    t = style2 & preedit;
    if (s != t) {
        if (s | t | XIMPreeditCallbacks)
            return (s == XIMPreeditCallbacks)?style1:style2;
        else if (s | t | XIMPreeditPosition)
            return (s == XIMPreeditPosition)?style1:style2;
        else if (s | t | XIMPreeditArea)
            return (s == XIMPreeditArea)?style1:style2;
        else if (s | t | XIMPreeditNothing)
            return (s == XIMPreeditNothing)?style1:style2;
    }
    else { /* if preedit flags are the same, compare status flags */
        s = style1 & status;
        t = style2 & status;
        if (s | t | XIMStatusCallbacks)
            return (s == XIMStatusCallbacks)?style1:style2;
        else if (s | t | XIMStatusArea)
            return (s == XIMStatusArea)?style1:style2;
        else if (s | t | XIMStatusNothing)
            return (s == XIMStatusNothing)?style1:style2;
    }
}

int init(){
	if (!binit){
		binit=true;
		setlocale(LC_ALL, getenv("LANG"));
		display = XOpenDisplay(NULL);
		if (! display) {
			fprintf (stderr, "Could not open display.\n");
		}

		wm_protocols = XInternAtom(display, "WM_PROTOCOLS", False);
		wm_delete_window = XInternAtom(display, "WM_DELETE_WINDOW", False);

		XSetLocaleModifiers("");
		screenid = DefaultScreen(display);
		root = RootWindow(display, screenid);
		screen = XScreenOfDisplay(display, screenid);

		if ((im = XOpenIM(display, NULL, NULL, NULL)) == NULL) {
			fprintf(stderr, "Couldn't open input method");
		}
		XIMStyles *im_supported_styles;
		XIMStyle app_supported_styles;
		app_supported_styles = XIMPreeditNone | XIMPreeditNothing | XIMPreeditArea;
		app_supported_styles |= XIMStatusNone | XIMStatusNothing | XIMStatusArea;
		XGetIMValues(im, XNQueryInputStyle, &im_supported_styles, NULL);
		XIMStyle style;
		best_style = 0;
		for(int i=0; i < im_supported_styles->count_styles; i++) {
			style = im_supported_styles->supported_styles[i];
			if ((style & app_supported_styles) == style) /* if we can handle it */
				best_style = ChooseBetterStyle(style, best_style);
		}
		XFree(im_supported_styles);


		//IMPOSTA FONT
		int nmissing;
		char **missing;
		char *def_string;
		//fontset = XCreateFontSet(display, "-*-*-*-r-normal--14-*-*-*-P-*-*-*", &missing, &nmissing, &def_string);
		//fontset = XCreateFontSet(display, "-*-*-*-r-normal--*-120-100-100-*-*", &missing, &nmissing, &def_string);
		//fontset = XCreateFontSet(display, "fixed", &missing, &nmissing, &def_string);
		//fontset = XCreateFontSet(display, "-*-*-medium-r-normal--13-*-*-*-p-*-*-*", &missing, &nmissing, &def_string);
		fontset = XCreateFontSet(display, "-*-*-medium-*-*--13-*-*-*-*-*-*-*", &missing, &nmissing, &def_string);
		if (!fontset){
			fontset = XCreateFontSet(display, "-*-*-medium-*-*--12-*-*-*-*-*-*-*", &missing, &nmissing, &def_string);
		}
		if (!fontset){
			fontset = XCreateFontSet(display, "-*-*-*-*-*--13-*-*-*-*-*-*-*", &missing, &nmissing, &def_string);
		}
		if (!fontset){
			fontset = XCreateFontSet(display, "-*-*-*-*-*--12-*-*-*-*-*-*-*", &missing, &nmissing, &def_string);
		}
		if (!fontset){
			fontset = XCreateFontSet(display, "-*-*-medium-*-*--14-*-*-*-*-*-*-*", &missing, &nmissing, &def_string);
		}
		if (!fontset){
			fontset = XCreateFontSet(display, "-*-*-*-*-*--14-*-*-*-*-*-*-*", &missing, &nmissing, &def_string);
		}
		if (!fontset){
			fontset = XCreateFontSet(display, "-*-*-*-*-*--*-*-*-*-*-*-*-*", &missing, &nmissing, &def_string);
		}
		if (nmissing > 0) {
			/*for(int i=0; i < nmissing; i++){
				fprintf(stderr, "%s: %s\n", "program_name", missing[i]);
				fprintf(stderr, "%s: The string %s will be used in place\n","program_name", def_string);
			}*/
			XFreeStringList(missing);
		}
		//CALCOLA DIMENSIONI FONT
		XFontStruct **fonts;
		char **font_names;
		int nfonts;
		int j;
		fontascent = 0;
		fontheight = 0;
		nfonts = XFontsOfFontSet(fontset, &fonts, &font_names);
		for(j = 0; j < nfonts; j += 1){
			//fprintf(stderr, "%s: %s\n", "font name", font_names[j]);
			if (fontascent < fonts[j]->ascent) fontascent = fonts[j]->ascent;
			if (fontheight < fonts[j]->ascent+fonts[j]->descent) fontheight = fonts[j]->ascent+fonts[j]->descent;
		}

		//CARICA COLOR MAP
		colormap = DefaultColormap(display, screenid);
	}
	return 0;
}

void term(){
	if (binit){
		binit=false;
		XFreeColormap (display, colormap);
		XCloseDisplay(display);
	}
}



void keyBoardEvent(DWAWindow* dwa,XEvent* e){
	int len;
	int buf_len = 10;
	wchar_t *buffer = (wchar_t *)malloc(buf_len * sizeof(wchar_t));
	KeySym ks;
	Status status;
	len = XwcLookupString(dwa->ic, &e->xkey, buffer, buf_len,
									  &ks, &status);
	/*
	 * Workaround:  the Xsi implementation of XwcLookupString
	 * returns a length that is 4 times too big.  If this bug
	 * does not exist in your version of Xlib, remove the
	 * following line, and the similar line below.
	 */
	if (len>=4){
		len = len / 4;
	}
	if (status == XBufferOverflow) {
		buf_len = len;
		buffer = (wchar_t *)realloc((char *)buffer,
									buf_len * sizeof(wchar_t));
		len = XwcLookupString(dwa->ic, &e->xkey, buffer, buf_len,
							  &ks, &status);
		/* Workaround */
		if (len>=4){
			len = len / 4;
		}
	}
	switch (status) {
	case XLookupNone:
		break;
	case XLookupKeySym:
	case XLookupBoth:
		/* Handle backspacing, and <Return> to exit */
		if (ks==XK_Escape){
			fireCallBackKeyboard(dwa->id,L"KEY",L"ESCAPE",e->xkey);
			break;
		}else if ((ks==XK_F1)|| (ks==XK_KP_F1)){
			fireCallBackKeyboard(dwa->id,L"KEY",L"F1",e->xkey);
			break;
		}else if ((ks==XK_F2)|| (ks==XK_KP_F2)){
			fireCallBackKeyboard(dwa->id,L"KEY",L"F2",e->xkey);
			break;
		}else if ((ks==XK_F3)|| (ks==XK_KP_F3)){
			fireCallBackKeyboard(dwa->id,L"KEY",L"F3",e->xkey);
			break;
		}else if ((ks==XK_F4)|| (ks==XK_KP_F4)){
			fireCallBackKeyboard(dwa->id,L"KEY",L"F4",e->xkey);
			break;
		}else if ((ks==XK_F5)){
			fireCallBackKeyboard(dwa->id,L"KEY",L"F5",e->xkey);
			break;
		}else if ((ks==XK_F6)){
			fireCallBackKeyboard(dwa->id,L"KEY",L"F6",e->xkey);
			break;
		}else if ((ks==XK_F7)){
			fireCallBackKeyboard(dwa->id,L"KEY",L"F7",e->xkey);
			break;
		}else if ((ks==XK_F8)){
			fireCallBackKeyboard(dwa->id,L"KEY",L"F8",e->xkey);
			break;
		}else if ((ks==XK_F9)){
			fireCallBackKeyboard(dwa->id,L"KEY",L"F9",e->xkey);
			break;
		}else if ((ks==XK_F10)){
			fireCallBackKeyboard(dwa->id,L"KEY",L"F10",e->xkey);
			break;
		}else if ((ks==XK_F11)){
			fireCallBackKeyboard(dwa->id,L"KEY",L"F11",e->xkey);
			break;
		}else if ((ks==XK_F12)){
			fireCallBackKeyboard(dwa->id,L"KEY",L"F12",e->xkey);
			break;
		}else if (ks==XK_Print){
			fireCallBackKeyboard(dwa->id,L"KEY",L"PRINT",e->xkey);
			break;
		}else if (ks==XK_Scroll_Lock){
			fireCallBackKeyboard(dwa->id,L"KEY",L"SCROLLOCK",e->xkey);
			break;
		}else if (ks==XK_Pause){
			fireCallBackKeyboard(dwa->id,L"KEY",L"PAUSE",e->xkey);
			break;
		}else if (ks==XK_Break){
			fireCallBackKeyboard(dwa->id,L"KEY",L"BREAK",e->xkey);
			break;
//*********************************************************************************
		}else if (ks==XK_BackSpace){
			fireCallBackKeyboard(dwa->id,L"KEY",L"BACKSPACE",e->xkey);
			break;
		}else if ((ks==XK_Tab) || (ks==XK_KP_Tab) || ks==XK_ISO_Left_Tab){
			fireCallBackKeyboard(dwa->id,L"KEY",L"TAB",e->xkey);
			break;
		}else if ((ks==XK_Return) || (ks==XK_KP_Enter)){
			fireCallBackKeyboard(dwa->id,L"KEY",L"RETURN",e->xkey);
			break;
		}else if (ks==XK_Caps_Lock){
			fireCallBackKeyboard(dwa->id,L"KEY",L"CAPSLOCK",e->xkey);
			break;
		}else if (ks==XK_Shift_Lock){
			fireCallBackKeyboard(dwa->id,L"KEY",L"SHIFTLOCK",e->xkey);
			break;
		}else if ((ks==XK_Delete)|| (ks==XK_KP_Delete)){
			fireCallBackKeyboard(dwa->id,L"KEY",L"DELETE",e->xkey);
			break;
		}else if ((ks==XK_Left)|| (ks==XK_KP_Left)){
			fireCallBackKeyboard(dwa->id,L"KEY",L"LEFT",e->xkey);
			break;
		}else if ((ks==XK_Right)|| (ks==XK_KP_Right)){
			fireCallBackKeyboard(dwa->id,L"KEY",L"RIGHT",e->xkey);
			break;
		}else if ((ks==XK_Up)|| (ks==XK_KP_Up)){
			fireCallBackKeyboard(dwa->id,L"KEY",L"UP",e->xkey);
			break;
		}else if ((ks==XK_Down)|| (ks==XK_KP_Down)){
			fireCallBackKeyboard(dwa->id,L"KEY",L"DOWN",e->xkey);
			break;
		}else if ((ks==XK_Home) || (ks==XK_KP_Home)){
			fireCallBackKeyboard(dwa->id,L"KEY",L"HOME",e->xkey);
			break;
		}else if ((ks==XK_End) || (ks==XK_KP_End)){
			fireCallBackKeyboard(dwa->id,L"KEY",L"END",e->xkey);
			break;
		}
		if (status == XLookupKeySym) break;
	case XLookupChars:
		if (len>0){
			wchar_t appstr[len+1];
			int applen = 0;
			for(int i=0; i < len; i++){
				appstr[applen++] = buffer[i];
			}
			appstr[applen++]=L'\0';
			fireCallBackKeyboard(dwa->id,L"CHAR",appstr, e->xkey);
		}
		break;
	}
	free(buffer);
}

int addImageToBuffer(wchar_t* file,unsigned long* &bf){
	int iret=0;
	XImage *p;
	XImage *pmask;
	XpmAttributes xattributes;
	xattributes.valuemask = 0;
	int sz=wcstombs(NULL,file,0);
	char cfilename[sz];
	wcstombs(cfilename,file,1024*4);
	int rtn = XpmReadFileToImage(display,cfilename,&p,&pmask,&xattributes);
	if (rtn==0){
		iret=(2+(p->width*p->height));
		bf = (unsigned long*)malloc(iret*sizeof(unsigned long));
		int i=0;
		bf[i]=p->width;
		i++;
		bf[i]=p->height;
		i++;
		for (int y=0;y<p->height;y++){
			for (int x=0;x<p->width;x++){
				unsigned long c = XGetPixel(p,x,y);
				unsigned long cmask = XGetPixel(p,x,y);
				if (cmask!=0){
					c=c+0xff000000;
				}
				bf[i]=c;
				i++;
			}
		}
		XDestroyImage(p);
	}
	return iret;

}

int newWindow(int tp,int x, int y, int w, int h, wchar_t* iconPath){
	Window appwin;
	GC appgc;
	XIC appic;

	init();
	XSetWindowAttributes attributes;
	attributes.background_pixel = XWhitePixel(display,screenid);
	Visual *visual = DefaultVisual(display,screenid);
	int depth  = DefaultDepth(display,screenid);


	appwin = XCreateWindow(display,root,
		                            x, y, w, h, 0, depth,  InputOutput,
		                            visual ,CWBackPixel, &attributes);


	//Previene chiusura browser da bottone
    XSetWMProtocols(display, appwin, &wm_delete_window, 1);

	appgc = XCreateGC(display, appwin, 0, 0);

	if (tp==WINDOW_TYPE_TOOL){
		Atom key = XInternAtom(display, "_NET_WM_WINDOW_TYPE", True);
		Atom val= XInternAtom(display, "_NET_WM_WINDOW_TYPE_MENU", True);
		XChangeProperty(display, appwin, key, XA_ATOM, 32, PropModeReplace, (unsigned char*)&val,  1);
	}else if (tp==WINDOW_TYPE_DIALOG){
		Atom key = XInternAtom(display, "_NET_WM_WINDOW_TYPE", True);
		Atom val= XInternAtom(display, "_NET_WM_WINDOW_TYPE_DIALOG", True);
		XChangeProperty(display, appwin, key, XA_ATOM, 32, PropModeReplace, (unsigned char*)&val,  1);

		/*Atom key1 = XInternAtom(display, "_NET_WM_STATE", True);
		Atom val1 = XInternAtom(display, "_NET_WM_STATE_DEMANDS_ATTENTION", True);
		XChangeProperty(display, appwin, key1, XA_ATOM, 32, PropModeReplace, (unsigned char*)&val1,  1);*/
   	}

	if ((tp==WINDOW_TYPE_NORMAL_NOT_RESIZABLE) || (tp==WINDOW_TYPE_DIALOG) || (tp==WINDOW_TYPE_TOOL)){
		XSizeHints *sh = XAllocSizeHints();
		sh->flags = PMinSize | PMaxSize;
		sh->min_width = sh->max_width = w;
		sh->min_height = sh->max_height = h;
		XSetWMNormalHints(display, appwin, sh);
		XFree(sh);
	}

	//CARICA ICONA
	if (iconPath != NULL){
		int length = 0;
		int sz=1024*16;
		//int szBuff=sz;
		unsigned long *buffer = NULL;
		wchar_t wcs[wcslen(iconPath)];
		wcpcpy(wcs,iconPath);
		wchar_t *state;
		wchar_t *token = wcstok(wcs, L"\n", &state);
		while (token != NULL){
			unsigned long* appbf = NULL;
			int appln = addImageToBuffer(token,appbf);
			if (appln>0){
				if (length==0){
					buffer = (unsigned long*)malloc(appln*sizeof(unsigned long));
				}else{
					buffer = (unsigned long*)realloc(buffer,(length+appln)*sizeof(unsigned long));
				}
				memcpy(buffer+length, appbf, appln*sizeof(unsigned long));
				free(appbf);
				length+=appln;
			}
			token = wcstok(NULL, L"\n", &state);
		}
		if (length>0){
			Atom net_wm_icon = XInternAtom(display, "_NET_WM_ICON", False);
			Atom cardinal = XInternAtom(display, "CARDINAL", False);
			XChangeProperty(display, appwin, net_wm_icon, cardinal, 32, PropModeReplace, (const unsigned char*)buffer, length);
			free(buffer);
		}
	}

   	XVaNestedList list = XVaCreateNestedList(0,XNFontSet,fontset,NULL);
   	appic = XCreateIC(im,
				   XNInputStyle, best_style,
				   XNClientWindow, appwin,
				   XNPreeditAttributes, list,
				   XNStatusAttributes, list,
				   NULL);
	XFree(list);
	long im_event_mask=0;
	if (appic != NULL) {
		XGetICValues(appic, XNFilterEvents, &im_event_mask, NULL);
		XSetICFocus(appic);
	}
	XSelectInput (display, appwin, ExposureMask | PointerMotionMask
				| ButtonPressMask | ButtonReleaseMask | KeyPressMask | KeyReleaseMask
				| FocusChangeMask | im_event_mask);
	DWAWindow* dwa = addWindow(appwin,appgc,appic);
	dwa->x=x;
	dwa->y=y;


	return dwa->id;
}

void destroyWindow(int id){
	DWAWindow* dwa = getWindowByID(id);
	if (dwa!=NULL){
		XIC xic=dwa->ic;
		Window ww=dwa->win;
		removeWindowByHandle(dwa->win);
		XDestroyIC(xic);
		XDestroyWindow(display,ww);
		if (windowList.size()==0){
			exitloop=true;
		}
	}
}

void setTitle(int id, wchar_t* title){
	DWAWindow* dwa = getWindowByID(id);
	if (dwa!=NULL){
		XTextProperty prop;
		XwcTextListToTextProperty(display, &title, 1, XUTF8StringStyle, &prop);
		XSetWMName(display, dwa->win, &prop);
	}
}

void getScreenSize(int* size){
	init();
	size[0]=screen->width;
	size[1]=screen->height;
}

void show(int id,int mode){
	DWAWindow* dwa = getWindowByID(id);
	if (dwa!=NULL){
		XMapWindow(display, dwa->win);
		XMoveWindow(display,dwa->win,dwa->x, dwa->y);
	}
}

void hide(int id){
	DWAWindow* dwa = getWindowByID(id);
	if (dwa!=NULL){
		XUnmapWindow(display, dwa->win);
	}
}

void toFront(int id){
	DWAWindow* dwa = getWindowByID(id);
	if (dwa!=NULL){
		XRaiseWindow(display, dwa->win);
	}
}

void penColor(int id, int r, int g, int b){
	DWAWindow* dwa = getWindowByID(id);
	if (dwa!=NULL){
		char hexcol[16];
		snprintf(hexcol, sizeof hexcol, "#%02x%02x%02x", r, g, b);
		XParseColor(display, colormap, hexcol, &dwa->curcol);
		XAllocColor(display, colormap, &dwa->curcol);
	}
}

void penWidth(int id, int w){

}

void drawLine(int id, int x1,int y1,int x2,int y2){
	DWAWindow* dwa = getWindowByID(id);
	if (dwa!=NULL){
		XSetForeground(display,  dwa->gc, dwa->curcol.pixel);
		XDrawLine(display, dwa->win, dwa->gc, x1, y1, x2, y2);
	}
}

void drawEllipse(int id, int x, int y, int w,int h){
	DWAWindow* dwa = getWindowByID(id);
	if (dwa!=NULL){
		XSetForeground(display,  dwa->gc, dwa->curcol.pixel);
		XDrawArc(display, dwa->win, dwa->gc, x, y, w, h, 0, 360*64);
	}
}

void fillEllipse(int id, int x, int y, int w,int h){
	DWAWindow* dwa = getWindowByID(id);
	if (dwa!=NULL){
		XSetForeground(display,  dwa->gc, dwa->curcol.pixel);
		XFillArc(display, dwa->win, dwa->gc, x, y, w, h, 0, 360*64);
	}
}


int getFontAscent(int id){
	return fontascent;
}

int getTextHeight(int id){
	return fontheight;
}

int getTextWidth(int id,wchar_t* str){
	return XwcTextEscapement(fontset,str,wcslen(str));
}

void drawText(int id, wchar_t* str, int x, int y){
	DWAWindow* dwa = getWindowByID(id);
	if (dwa!=NULL){
		XSetForeground(display,  dwa->gc, dwa->curcol.pixel);
		XwcDrawString(display,dwa->win,fontset,dwa->gc,x,y+getFontAscent(0),str,wcslen(str));
	}
}

void fillRectangle(int id, int x, int y, int w,int h){
	DWAWindow* dwa = getWindowByID(id);
	if (dwa!=NULL){
		XSetForeground(display,  dwa->gc, dwa->curcol.pixel);
		XFillRectangle(display, dwa->win, dwa->gc, x, y, w, h);
	}
}

void repaint(int id, int x, int y, int w, int h){
	/*XEvent exppp;
	memset(&exppp, 0, sizeof(exppp));
	exppp.type = Expose;
	exppp.xexpose.window = mainwin;
	exppp.xexpose.x=x;
	exppp.xexpose.y=y;
	exppp.xexpose.width=w;
	exppp.xexpose.height=h;
	XSendEvent(display,mainwin,False,ExposureMask,&exppp);*/
	DWAWindow* dwa = getWindowByID(id);
	if (dwa!=NULL){
		fireCallBackRepaint(dwa->id,x,y,w,h);
	}
}

void clipRectangle(int id, int x, int y, int w, int h){
	DWAWindow* dwa = getWindowByID(id);
	if (dwa!=NULL){
		XRectangle curcliprect;
		curcliprect.x=x;
		curcliprect.y=y;
		curcliprect.width=w;
		curcliprect.height=h;
		XSetClipRectangles(display, dwa->gc, 0, 0, &curcliprect, 1, YXSorted);
	}
}

void clearClipRectangle(int id){
	DWAWindow* dwa = getWindowByID(id);
	if (dwa!=NULL){
		XSetClipMask(display, dwa->gc, None);
	}
}

//http://sourcecodebrowser.com/docker/1.4/net_8c.html#ad855b003908d95ec1117e45359d785a5
void createNotifyIcon(int id,wchar_t* iconPath,wchar_t* toolTip){
}

void setClipboardText(wchar_t* str){

}

wchar_t* getClipboardText(){
	return NULL;
}

void updateNotifyIcon(int id,wchar_t* iconPath,wchar_t* toolTip){
}

void destroyNotifyIcon(int id){
}

void getMousePosition(int* pos){
}

void loop(){

	long start, end;
	start=getMillisecons();
	x11_fd = ConnectionNumber(display);
	exitloop=false;
	while (!exitloop) {
		FD_ZERO(&in_fds);
		FD_SET(x11_fd, &in_fds);
		tv.tv_usec = 100000;
		tv.tv_sec = 0;
		select(x11_fd+1, &in_fds, 0, 0, &tv);

		end=getMillisecons();
		long elapsed=end-start;
		if (elapsed>100){
			fireCallBackTimer();
			start=getMillisecons();
		}else if (elapsed<0){ //ORA PC MODIFICATO
			start=getMillisecons();
		}

		if(XPending(display)){
			XEvent e;
			XNextEvent (display, &e);
			if (e.type == Expose) {
				DWAWindow* dwa = getWindowByHandle(e.xany.window);
				if (dwa!=NULL){
					fireCallBackRepaint(dwa->id,e.xexpose.x,e.xexpose.y,e.xexpose.width,e.xexpose.height);
				}
			}else if (e.type == KeyPress){
				DWAWindow* dwa = getWindowByHandle(e.xany.window);
				if (dwa!=NULL){
					keyBoardEvent(dwa,&e);
				}
			}else if (e.type == MappingNotify) {
			   XRefreshKeyboardMapping(&e.xmapping);
			}else if (e.type == MotionNotify){
				DWAWindow* dwa = getWindowByHandle(e.xany.window);
				if (dwa!=NULL){
					fireCallBackMouse(dwa->id,L"MOVE",e.xmotion.x,e.xmotion.y,0);
				}
			}else if (e.type == ButtonPress) {
				DWAWindow* dwa = getWindowByHandle(e.xany.window);
				if (dwa!=NULL){
					int btn=0;
					if (e.xbutton.button == Button1) {
						btn=1;
					}else if (e.xbutton.button == Button3) {
						btn=2;
					}
					fireCallBackMouse(dwa->id,L"BUTTON_DOWN",e.xbutton.x,e.xbutton.y,btn);
				}
			}else if (e.type == ButtonRelease) {
				DWAWindow* dwa = getWindowByHandle(e.xany.window);
				if (dwa!=NULL){
					int btn=0;
					if (e.xbutton.button == Button1) {
						btn=1;
					}else if (e.xbutton.button == Button3) {
						btn=2;
					}
					fireCallBackMouse(dwa->id,L"BUTTON_UP",e.xbutton.x,e.xbutton.y,btn);
				}
			}else if (e.type == FocusIn) {
				DWAWindow* dwa = getWindowByHandle(e.xany.window);
				if (dwa!=NULL){
					fireCallBackWindow(dwa->id,L"ACTIVE");
				}
			}else if (e.type == FocusOut) {
				DWAWindow* dwa = getWindowByHandle(e.xany.window);
				if (dwa!=NULL){
					fireCallBackWindow(dwa->id,L"INACTIVE");
				}
			}else if (e.type == ClientMessage) {
				DWAWindow* dwa = getWindowByHandle(e.xany.window);
				if (dwa!=NULL){
					if (e.xclient.message_type == wm_protocols &&
						e.xclient.data.l[0] == wm_delete_window)  {
						if (fireCallBackWindow(dwa->id,L"ONCLOSE")){
							destroyWindow(dwa->id);
						}
					}
				}
			}
		}
	}
	term();
}

#endif
