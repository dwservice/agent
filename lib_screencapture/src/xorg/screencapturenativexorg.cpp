
/* 
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/
#if defined OS_XORG

#include "screencapturenativexorg.h"


bool loadXrandrCheck(string s) {
	transform(s.begin(), s.end(), s.begin(),::tolower);
    return (s.substr(0,12)=="libxrandr.so");
}

bool loadXrandr(string s){
	bool bret=false;
	DIR *d;
	struct dirent *dir;
	d = opendir(s.c_str());
	if (d) {
		while ((dir = readdir(d)) != NULL) {
			string apps="";
			apps.append(dir->d_name);
			if (dir->d_type == DT_DIR){
				if ((apps!=".") && (apps!="..")){
					apps.clear();
					apps.append(s);
					apps.append("/");
					apps.append(dir->d_name);
					bret = loadXrandr(apps);
					if (bret){
						break;
					}
				}
			}else if (dir->d_type == DT_REG){
				if (loadXrandrCheck(apps)){
					apps.clear();
					apps.append(s);
					apps.append("/");
					apps.append(dir->d_name);
					handleXrandr = dlopen(apps.c_str(), RTLD_LAZY);
					if (handleXrandr) {
						callXRRGetScreenResourcesCurrent = (XRRScreenResources* (*)(Display *dpy, Window window))dlsym(handleXrandr, "XRRGetScreenResourcesCurrent");
						if (dlerror() != NULL)  {
							dlclose(handleXrandr);
							handleXrandr=NULL;
						}
					}
					if (handleXrandr) {
						callXRRGetCrtcInfo = (XRRCrtcInfo* (*)(Display *dpy, XRRScreenResources *resources, RRCrtc crtc))dlsym(handleXrandr, "XRRGetCrtcInfo");
						if (dlerror() != NULL)  {
							dlclose(handleXrandr);
							handleXrandr=NULL;
						}
					}
					if (handleXrandr) {
						callXRRFreeScreenResources = (void (*) (XRRScreenResources *resources))dlsym(handleXrandr, "XRRFreeScreenResources");
						if (dlerror() != NULL)  {
							dlclose(handleXrandr);
							handleXrandr=NULL;
						}
					}
					if (handleXrandr) {
						callXRRFreeCrtcInfo = (void (*) (XRRCrtcInfo *crtcInfo))dlsym(handleXrandr, "XRRFreeCrtcInfo");
						if (dlerror() != NULL)  {
							dlclose(handleXrandr);
							handleXrandr=NULL;
						}
					}
					if (handleXrandr) {
						bret=true;
						break;
					}
				}
			}
		}
		closedir(d);
	}
	return bret;
}

int DWAScreenCaptureGetCpuUsage(){
    return (int)cpuUsage->getValue();
}

int DWAScreenCaptureVersion(){
	return 2;
}

void DWAScreenCaptureFreeMemory(void* pnt){
	free(pnt);
}

void handleXEvents(){
	XEvent event;
	while (XPending(xdpy)){
		XNextEvent(xdpy, &event);
		/*if ((damageok) && (event.type == damageevent + XDamageNotify)){
			XDamageNotifyEvent *damageevt = (XDamageNotifyEvent*) (&event);
		}*/
		if (event.type == xfixesevent + XFixesCursorNotify) {
			xfixeschanged=true;
		}
		if (event.type == MappingNotify) {
			XMappingEvent *e = (XMappingEvent *) &event;
			if (e->request == MappingKeyboard) {
				linuxInputs->keyboardChanged();
			}
		}

		//EVENT CLIPBOARD CHANGE
		if (event.type == xfixesevent + XFixesSelectionNotify && ((XFixesSelectionNotifyEvent*)&event)->selection == atomClipboard){
			XConvertSelection(xdpy, atomClipboard, atomStrTp, atomXSelData, fakewindow, CurrentTime);
		}

		//GET CLIPBOARD
		if (event.type == SelectionNotify) {
			//printf("SelectionNotify\n");
			if ((event.xselection.selection==atomClipboard) && (event.xselection.property)) {
				int format;
				unsigned long N, size;
				char * data;
				Atom target;
				XGetWindowProperty(event.xselection.display, event.xselection.requestor,
					event.xselection.property, 0L,(~0L), 0, AnyPropertyType, &target,
					&format, &size, &N,(unsigned char**)&data);
				if (target == atomStrTp) {
					wchar_t* dest = (wchar_t*)malloc((size+1) * sizeof(wchar_t));
					mbstowcs(dest, (char*)data, size+1);
					copytxt.append(dest);
					free(dest);
					XFree(data);
					copyok=true;

					clipboardChanges=true;

				}
				XDeleteProperty(event.xselection.display, event.xselection.requestor, event.xselection.property);
			}
		}
		//SET CLIPBOARD
		if (event.type == SelectionRequest) {
			//printf("SelectionRequest\n");
			if ((event.xselectionrequest.selection == atomClipboard) && (pastetxt.length()>0)){
				XSelectionRequestEvent * xsr = &event.xselectionrequest;
				XSelectionEvent ev = {0};
				int ret = 0;
				ev.type = SelectionNotify, ev.display = xsr->display, ev.requestor = xsr->requestor,
				ev.selection = xsr->selection, ev.time = xsr->time, ev.target = xsr->target, ev.property = xsr->property;
				if (ev.target == atomTargets){
					ret = XChangeProperty (ev.display, ev.requestor, ev.property, 4, 32, PropModeReplace, (unsigned char*)&atomStrTp, 1);
				}else if (ev.target == 31 || ev.target == atomText){ //XA_STRING=31;
					wchar_t* chrs = (wchar_t*)pastetxt.c_str();
					size_t requiredSize = wcstombs(NULL, chrs, 0);
					char* dest = (char*)malloc((requiredSize+1) * sizeof(char));
					wcstombs(dest, chrs, requiredSize+1);
					ret = XChangeProperty(ev.display, ev.requestor, ev.property, 31, 8, PropModeReplace, (unsigned char*)dest, requiredSize);
					free(dest);
				}else if (ev.target == atomStrTp){
					wchar_t* chrs = (wchar_t*)pastetxt.c_str();
					size_t requiredSize = wcstombs(NULL, chrs, 0);
					char* dest = (char*)malloc(((requiredSize)+1) * sizeof(char));
					wcstombs(dest, chrs, requiredSize+1);
					ret = XChangeProperty(ev.display, ev.requestor, ev.property, atomStrTp, 8, PropModeReplace, (unsigned char*)dest, requiredSize);
					free(dest);
				}else{
					ev.property = None;
				}
				if ((ret & 2) == 0){
					XSendEvent(xdpy, ev.requestor, 0, 0, (XEvent *)&ev);
				}
			}
		}
		if (event.type == SelectionClear) {
			//printf("SelectionClear\n");
			pastetxt.clear();
		}
	}
}

int DWAScreenCaptureIsChanged(){
	if (xdpy!=NULL){
		handleXEvents();

		//DETECT DAMAGE
		if (damageok){
			damageareachanged=false;
			XDamageSubtract(xdpy, damage, None, damageregion);
			int rects_num = 0;
			XRectangle bounds;
			XRectangle* rects = XFixesFetchRegionAndBounds(xdpy,damageregion,&rects_num, &bounds);
			for (int i = 0; i < rects_num; ++i) {
				int appcx = rects[i].x;
				int appcy = rects[i].y;
				int appcw = rects[i].width;
				int appch = rects[i].height;
				if (damageareachanged==false){
					damageareax=appcx;
					damageareay=appcy;
					damageareaw=appcw;
					damageareah=appch;
				}else{
					if (appcx<damageareax){
						damageareax=appcx;
						damageareaw+=damageareax-appcx;
					}
					if (appcy<damageareay){
						damageareay=appcy;
						damageareah+=damageareay-appcy;
					}
					if (appcx+appcw>damageareax+damageareaw){
						damageareaw+=(appcx+appcw)-(damageareax+damageareaw);
					}
					if (appcy+appch>damageareay+damageareah){
						damageareah+=(appcy+appch)-(damageareay+damageareah);
					}
				}
				damageareachanged=true;
			}
			XFree(rects);
		}
	}
	return 0;
}

void calcColShiftBits(ScreenCaptureInfo* sci){
	if (sci->image->bits_per_pixel<=16){
		int redbits=countSetBits(sci->image->red_mask);
		int greenbits=countSetBits(sci->image->green_mask);
		int bluebits=countSetBits(sci->image->blue_mask);
		if (redbits<8){
			sci->redrshift=8-redbits;
		}else{
			sci->redrshift=0;
		}
		if (greenbits<8){
			sci->greenrshift=8-greenbits;
		}else{
			sci->greenrshift=0;
		}
		if (bluebits<8){
			sci->bluershift=8-bluebits;
		}else{
			sci->bluershift=0;
		}
		sci->redlshift=(bluebits+greenbits)-sci->redrshift;
		sci->greenlshift=bluebits-sci->greenrshift;
	}
}

int DWAScreenCaptureInitMonitor(MONITORS_INFO_ITEM* moninfoitem, RGB_IMAGE* capimage, void** capses){
	ScreenCaptureInfo* sci = new ScreenCaptureInfo();
	sci->monitor=moninfoitem->index;
	sci->x=moninfoitem->x;
	sci->y=moninfoitem->y;
	sci->w=moninfoitem->width;
	sci->h=moninfoitem->height;
	capimage->width=moninfoitem->width;
	capimage->height=moninfoitem->height;
	capimage->sizedata=capimage->width*capimage->height*3;
	capimage->sizechangearea=0;
	capimage->sizemovearea=0;
	capimage->data=(unsigned char*)malloc(capimage->sizedata * sizeof(unsigned char));
	sci->rgbimage=capimage;
	if (!damageok){
		sci->image = XShmCreateImage(xdpy, visual, depth, ZPixmap, NULL, &sci->m_shmseginfo, sci->w, sci->h);
		sci->m_shmseginfo.shmid = shmget(IPC_PRIVATE, sci->image->bytes_per_line * sci->h, IPC_CREAT | 0777);
		sci->m_shmseginfo.shmaddr = reinterpret_cast<char*>(shmat(sci->m_shmseginfo.shmid, NULL, 0));
		sci->image->data = sci->m_shmseginfo.shmaddr;
		sci->m_shmseginfo.readOnly = False;
		XShmAttach(xdpy, &sci->m_shmseginfo);
		calcColShiftBits(sci);
	}
	sci->status=1;
	*capses=sci;
	return 0;
}

void DWAScreenCaptureTermMonitor(void* capses){
	ScreenCaptureInfo* sci = (ScreenCaptureInfo*)capses;
	if (sci->status==0){
		return;
	}
	if (sci->image != NULL) {
		XShmDetach(xdpy,&sci->m_shmseginfo);
		XDestroyImage(sci->image);
		shmdt(sci->m_shmseginfo.shmaddr);
		shmctl(sci->m_shmseginfo.shmid, IPC_RMID, 0);
		sci->image = NULL;
	}
	RGB_IMAGE* rgbimage = sci->rgbimage;
	free(rgbimage->data);
	rgbimage->data=NULL;
	rgbimage->width=0;
	rgbimage->height=0;
	sci->status=0;
	delete sci;
}

int DWAScreenCaptureGetImage(void* capses){
	ScreenCaptureInfo* sci = (ScreenCaptureInfo*)capses;
	if (sci->status==0){
		return -1; //NOT INIT
	}
	RGB_IMAGE* rgbimage=sci->rgbimage;
	rgbimage->sizechangearea=0;
	rgbimage->sizemovearea=0;
	bool cok=False;
	int cx=0;
	int cy=0;
	int cw=0;
	int ch=0;

	if ((!damageok) || (sci->status==1)){
		cok=true;
		cx=sci->x;
		cy=sci->y;
		cw=sci->w;
		ch=sci->h;
	}else if (damageareachanged==true){
		int x1=sci->x;
		int y1=sci->y;
		int x2=sci->x+sci->w;
		int y2=sci->y+sci->h;

		int x3=damageareax;
		int y3=damageareay;
		int x4=damageareax+damageareaw;
		int y4=damageareay+damageareah;


		int x5 = max(x1, x3);
		int y5 = max(y1, y3);
		int x6 = min(x2, x4);
		int y6 = min(y2, y4);

		if (x5 >= x6 || y5 >= y6) { //no intersec
			cok=false;
		}else{
			cok=true;
			cx=x5;
			cy=y5;
			cw=x6-x5;
			ch=y6-y5;
		}
	}
	if (cok){
		if (damageok){
			sci->image = XGetImage(xdpy, root, cx, cy, cw, ch, AllPlanes, ZPixmap);
			if (sci->image==NULL){
				return -3;
			}
			calcColShiftBits(sci);
		}else{
			if (!XShmGetImage(xdpy, root, sci->image, sci->x, sci->y, AllPlanes)){
				return -3;
			}
		}
		//CONVERT IN RGB
		int offsetSrc = 0;
		int offsetDst = 0;
		int rowOffset = sci->image->bytes_per_line % cw;
		for (int row = sci->y; row < sci->y+sci->h; ++row){
			for (int col = sci->x; col < sci->x+sci->w; ++col){
				if (row>=cy and row<cy+ch and col>=cx and col<cx+cw){
					unsigned char r=0;
					unsigned char g=0;
					unsigned char b=0;
					if (sci->image->bits_per_pixel>24){
						r = sci->image->data[offsetSrc+2];
						g = sci->image->data[offsetSrc+1];
						b = sci->image->data[offsetSrc];
						offsetSrc += 4;
					}else if (sci->image->bits_per_pixel>16){
						r = sci->image->data[offsetSrc+2];
						g = sci->image->data[offsetSrc+1];
						b = sci->image->data[offsetSrc];
						offsetSrc += 3;
					}else if (sci->image->bits_per_pixel>8){
						unsigned int pixel=(((unsigned char)sci->image->data[offsetSrc+1]) << 8) | ((unsigned char)sci->image->data[offsetSrc]);
						r = (unsigned char)((pixel & sci->image->red_mask) >> (sci->redlshift));
						g = (unsigned char)((pixel & sci->image->green_mask) >> sci->greenlshift);
						b = (unsigned char)((pixel & sci->image->blue_mask) << sci->bluershift);
						offsetSrc += 2;
					}else{
						unsigned int pixel=((unsigned char)sci->image->data[offsetSrc]);
						r = (unsigned char)((pixel & sci->image->red_mask) >> sci->redlshift);
						g = (unsigned char)((pixel & sci->image->green_mask) >> sci->greenlshift);
						b = (unsigned char)((pixel & sci->image->blue_mask) << sci->bluershift);
						offsetSrc += 1;
					}
					if ((rgbimage->sizechangearea==0) and ((sci->status==1) or ((rgbimage->data[offsetDst] != r) or (rgbimage->data[offsetDst+1] != g) or (rgbimage->data[offsetDst+2] != b)))){
						rgbimage->sizechangearea=1;
						rgbimage->changearea[0].x=0;
						rgbimage->changearea[0].y=0;
						rgbimage->changearea[0].width=sci->w;
						rgbimage->changearea[0].height=sci->h;
					}
					rgbimage->data[offsetDst] = r;
					rgbimage->data[offsetDst+1] = g;
					rgbimage->data[offsetDst+2] = b;
				}
				offsetDst += 3;
			}
			if (row>=cy and row<cy+ch){
				offsetSrc += rowOffset;
			}
		}
		sci->status=2;
		if (damageok){
			XDestroyImage(sci->image);
			sci->image=NULL;
		}
	}
	return 0;
}

int DWAScreenCaptureCursor(CURSOR_IMAGE* curimage){
	curimage->changed=0;
	unsigned int mask_return;
	Window window_returned;
	int win_x, win_y, cursorX, cursorY;
	if (XQueryPointer(xdpy,root,&window_returned,&window_returned,&cursorX,&cursorY,&win_x,&win_y,&mask_return)==True){
		if (xfixesok){
			if (xfixeschanged){
				XFixesCursorImage *xcurimg = XFixesGetCursorImage(xdpy);
				if ((xcurimg) && (xcurimg->width>1) && (xcurimg->height>1)){
					curimage->offx=xcurimg->xhot;
					curimage->offy=xcurimg->yhot;
					curimage->width=xcurimg->width;
					curimage->height=xcurimg->height;
					curimage->sizedata=xcurimg->width*xcurimg->height*4;
					bool visible=false;
					unsigned char* cursorData = (unsigned char*)malloc(curimage->sizedata);
					long unsigned int* dt = xcurimg->pixels;
					int offsrc=0;
					int offdest=0;
					long unsigned int argb;
					long unsigned int rgba;
					for (int row = 0; row < xcurimg->height; ++row){
						for (int col = 0; col < xcurimg->width; ++col){
							argb = dt[offsrc] & 0xffffffff;
							if (argb!=0x00000000){
								visible=true;
							}
							rgba = (argb << 8) | (argb >> 24);
							cursorData[offdest] = (rgba >> 24)  & 0xff;
							cursorData[offdest+1] = (rgba >> 16) & 0xff;
							cursorData[offdest+2] = (rgba >> 8) & 0xff;
							cursorData[offdest+3] = rgba & 0xff;
							offsrc+=1;
							offdest+=4;
						}
					}
					if (visible){
						if (curimage->data!=NULL){
							free(curimage->data);
						}
						curimage->changed=1;
						curimage->data = cursorData;
					}else{
						free(cursorData);
					}
					XFree(xcurimg);
				}else if (curimage->data==NULL){
					curimage->changed=1;
					setCursorImage(CURSOR_TYPE_ARROW_18_18,curimage);
				}
				xfixeschanged=false;
			}
		}else{
			if (curimage->data==NULL){
				curimage->changed=1;
				setCursorImage(CURSOR_TYPE_ARROW_18_18,curimage);
			}
		}
		curimage->visible=1;
		curimage->x=cursorX;
		curimage->y=cursorY;
		return 0;
	}else{
		return -1;
	}
}


void DWAScreenCaptureInputKeyboard(const char* type, const char* key, bool ctrl, bool alt, bool shift, bool command){
	linuxInputs->keyboard(type, key, ctrl, alt, shift, command);
}


void DWAScreenCaptureInputMouse(MONITORS_INFO_ITEM* moninfoitem, int x, int y, int button, int wheel, bool ctrl, bool alt, bool shift, bool command){
	linuxInputs->mouse(moninfoitem, x, y, button, wheel, ctrl, alt, shift, command);
}

void DWAScreenCaptureCopy(){
	linuxInputs->copy();
}

void DWAScreenCapturePaste(){
	linuxInputs->paste();
}

void DWAScreenCaptureGetClipboardChanges(CLIPBOARD_DATA* clipboardData){
	clipboardData->type=0;
	if (clipboardChanges){
		clipboardChanges=false;
		clipboardData->type=1; //TEXT
		clipboardData->data=(unsigned char*)malloc(copytxt.length() * sizeof(wchar_t));
		copytxt.copy((wchar_t*)clipboardData->data,copytxt.length());
		clipboardData->sizedata=(copytxt.length() * sizeof(wchar_t));
		copytxt.clear();
	}
}

void DWAScreenCaptureSetClipboard(CLIPBOARD_DATA* clipboardData){
	if ((xdpy!=NULL) && (fakewindow)){
		XSetSelectionOwner(xdpy, atomClipboard, fakewindow, 0);
		if (XGetSelectionOwner (xdpy, atomClipboard) == fakewindow){
			pastetxt.clear();
			pastetxt.append((wchar_t*)clipboardData->data,(clipboardData->sizedata / sizeof(wchar_t)));
			handleXEvents();
		}
	}
}

bool DWAScreenCaptureLoad() {
	xdpy = NULL;
	root = 0;
	screen = NULL;
	visual = NULL;
	damageok=false;
	xfixesok=false;
	cpuUsage=new LinuxCPUUsage();
	linuxInputs=new LinuxInputs();
	loadXrandr("/usr/lib");
	return true;
}

void DWAScreenCaptureUnload() {
  	delete linuxInputs;
	delete cpuUsage;
	if (xdpy != NULL) {
		if (damageok){
			XDamageDestroy(xdpy, damage);
			XFixesDestroyRegion(xdpy, damageregion);
		}
		damageok=false;
		xfixesok=false;
		if (fakewindow){
			XDestroyWindow(xdpy,fakewindow);
		}
		XCloseDisplay(xdpy);
		xdpy = NULL;
	}
	if (handleXrandr) {
		dlclose(handleXrandr);
		handleXrandr=NULL;
	}
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

void addMonitorsInfo(MONITORS_INFO* moninfo, int x, int y, int w, int h){
	int p=moninfo->count;
	moninfo->count+=1;
	if (moninfo->monitor[p].changed==-1){
		moninfo->monitor[p].index=p;
		moninfo->monitor[p].x=x;
		moninfo->monitor[p].y=y;
		moninfo->monitor[p].width=w;
		moninfo->monitor[p].height=h;
		moninfo->monitor[p].changed=1;
		moninfo->changed=1;
	}else{
		if ((moninfo->monitor[p].x!=x) || (moninfo->monitor[p].y!=y) || (moninfo->monitor[p].width!=w) || (moninfo->monitor[p].height!=h)){
			moninfo->monitor[p].index=p;
			moninfo->monitor[p].x=x;
			moninfo->monitor[p].y=y;
			moninfo->monitor[p].width=w;
			moninfo->monitor[p].height=h;
			moninfo->monitor[p].changed=1;
			moninfo->changed=1;
		}else{
			moninfo->monitor[p].changed=0;
		}
	}
}

bool stringEndsWith(string const &str, string const &suffix) {
    if (str.length() < suffix.length()) {
        return false;
    }
    return str.compare(str.length() - suffix.length(), suffix.length(), suffix) == 0;
}

int DWAScreenCaptureGetMonitorsInfo(MONITORS_INFO* moninfo){
	//Detect monitor
	int iret=0;
	int oldmc=clearMonitorsInfo(moninfo);
	if (xdpy == NULL){
		clipboardChanges=false;

		//set locale
		setlocale(LC_ALL, getenv("LANG"));

		if ((xdpy = XOpenDisplay(NULL)) != NULL) {

			//for XNextEvent ???
			XKeysymToKeycode(xdpy, XK_F1);

			root = XDefaultRootWindow(xdpy);
			screen = XScreenOfDisplay(xdpy, 0);
			visual = XDefaultVisualOfScreen(screen);
			depth=24;
			int n;
			int* dps = XListDepths(xdpy,0,&n);
			if (dps!=NULL){
				if (n>0){
					depth=dps[0];
				}
				XFree(dps);
			}
			linuxInputs->setDisplay(xdpy,root);

			int xfixeserr;
			if (!XFixesQueryExtension(xdpy, &xfixesevent, &xfixeserr)) {
				xfixesok = false;
			}else{
				int major, minor;
				XFixesQueryVersion(xdpy, &major, &minor);
				xfixesok = (major >= 2);
				xfixeschanged = xfixesok;
			}
			XFixesSelectCursorInput(xdpy, root, XFixesDisplayCursorNotifyMask);

			//XDAMAGE
			int damageerr;
			if (!XDamageQueryExtension(xdpy, &damageevent, &damageerr)) {
				damageok=false;
			}else{
				damageok=true;
				damage = XDamageCreate(xdpy, root, XDamageReportNonEmpty);
				if (!damage){
					damageok=false;
				}else{
					damageregion = XFixesCreateRegion(xdpy, 0, 0);
					if (!damageregion) {
						damageok=false;
						XDamageDestroy(xdpy, damage);
					}
				}
			}
			damageareachanged=false;

			//CLIPBOARD
			int defscr = DefaultScreen(xdpy);
			fakewindow = XCreateSimpleWindow(xdpy, RootWindow(xdpy, defscr), 0, 0, 1, 1, 0, BlackPixel(xdpy, defscr), WhitePixel(xdpy, defscr));
			atomStrTp = XInternAtom(xdpy, "UTF8_STRING", 1);
			if(atomStrTp  == None){
				atomStrTp = 31; //XA_STRING
			}
			atomClipboard = XInternAtom(xdpy, "CLIPBOARD", 0);
			atomXSelData = XInternAtom(xdpy, "XSEL_DATA", 0);
			atomTargets = XInternAtom(xdpy, "TARGETS", 0);
			atomText = XInternAtom(xdpy, "TEXT", 0);

			 XFixesSelectSelectionInput(xdpy, DefaultRootWindow(xdpy), atomClipboard, XFixesSetSelectionOwnerNotifyMask);

		}else{
			damageok=false;
			xfixesok=false;
			iret=-1;
		}
	}
	if (handleXrandr) {
		XRRScreenResources *res = (*callXRRGetScreenResourcesCurrent)(xdpy, root);
		for( int j = 0; j < res->ncrtc; j++ ) {
			XRRCrtcInfo *crtc_info = (*callXRRGetCrtcInfo)(xdpy, res, res->crtcs[j]);
			if (crtc_info->noutput){
				int x=crtc_info->x;
				int y=crtc_info->y;
				int w=crtc_info->width;
				int h=crtc_info->height;
				addMonitorsInfo(moninfo,x,y,w,h);
			}
			callXRRFreeCrtcInfo(crtc_info);
		}
		callXRRFreeScreenResources(res);
	}
	if (moninfo->count==0){
		XWindowAttributes xwAttr;
		XGetWindowAttributes(xdpy, root, &xwAttr); //Status ret =
		int x=0;
		int y=0;
		int w=xwAttr.width;
		int h=xwAttr.height;
		addMonitorsInfo(moninfo,x,y,w,h);
	}
	if (oldmc!=moninfo->count){
		moninfo->changed=1;
	}
	return iret;
}

#endif
