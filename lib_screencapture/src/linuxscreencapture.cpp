/* 
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/
#if defined OS_LINUX

#include "linuxscreencapture.h"

ScreenCaptureNative::ScreenCaptureNative(DWDebugger* dbg) {
	dwdbg=dbg;
	xdpy = NULL;
	screen = NULL;
	visual = NULL;
	mousebtn1Down=false;
	mousebtn2Down=false;
	mousebtn3Down=false;
	ctrlDown=false;
	altDown=false;
	shiftDown=false;
	max_grp=4;
	cursorX=0;
	cursorY=0;
	cursoroffsetX=0;
	cursoroffsetY=0;
	cursorW=0;
	cursorH=0;
	cursorID=0;
	
	firstmonitorscheck=true;
	monitorsCounter.reset();

	firstGetCpu=true;
	cpuCounter.reset();
	//read process number
	FILE* file = fopen("/proc/cpuinfo", "r");
	char line[128];
    numProcessors = 0;
    while(fgets(line, 128, file) != NULL){
        if (strncmp(line, "processor", 9) == 0) numProcessors++;
    }
    fclose(file);

    loadXrandr("/usr/lib");
}


ScreenCaptureNative::~ScreenCaptureNative() {
	if (handleXrandr) {
		dlclose(handleXrandr);
		handleXrandr=NULL;
	}
}

bool ScreenCaptureNative::loadXrandrCheck(string s) {
	transform(s.begin(), s.end(), s.begin(),::tolower);
    return (s.substr(0,12)=="libxrandr.so");
}

bool ScreenCaptureNative::loadXrandr(string s){
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

float ScreenCaptureNative::getCpuUsage(){

	if ((!firstGetCpu) && (cpuCounter.getCounter()<1000)){
		return percentCpu;
	}

	struct tms timeSample;
    clock_t now;
	
    now = times(&timeSample);
	if (firstGetCpu){
		firstGetCpu=false;	
		percentCpu = 0.0;
	}else{
		if (now <= lastCPU || timeSample.tms_stime < lastSysCPU ||
			timeSample.tms_utime < lastUserCPU){
			percentCpu = 0.0;
		}else{
			percentCpu = (timeSample.tms_stime - lastSysCPU) +
				(timeSample.tms_utime - lastUserCPU);
			percentCpu /= (now - lastCPU);
			percentCpu /= numProcessors;
			percentCpu *=100;
		}
	}
	lastCPU = now;
	lastSysCPU = timeSample.tms_stime;
	lastUserCPU = timeSample.tms_utime;
	cpuCounter.reset();
	//printf("CPU: %f\n",percent);
    return percentCpu;
}

void ScreenCaptureNative::trimnl (char *s) {
  char *pnl = s + strlen(s);
  if (*s && *--pnl == '\n')
    *pnl = 0;
}

bool ScreenCaptureNative::initialize() {
	//INIT MONITOR
	activeTTY=0;
	envxauthority="";
	envxwayland="";
	envxdisplay="";
	getMonitorCount();
	return true;
}

void ScreenCaptureNative::terminate() {
	for(vector<ScreenShotInfo>::size_type i = 0; i < screenShotInfo.size(); i++) {
		termScreenShotInfo(&screenShotInfo[i]);
	}
	screenShotInfo.clear();
	monitorsInfo.clear();
	if (xdpy != NULL) {
		XCloseDisplay(xdpy);
		xdpy = NULL;
	}
	unloadKeyMap();

}

bool ScreenCaptureNative::makeDirs(std::string path){
    bool bSuccess = false;
    int nRC = ::mkdir( path.c_str(), 0700 );
    if( nRC == -1 )
    {
        switch(errno){
            case ENOENT:
                if(makeDirs(path.substr(0, path.find_last_of('/'))))
                    bSuccess = 0 == ::mkdir( path.c_str(), 0700 );
                else
                    bSuccess = false;
                break;
            case EEXIST:
                //Done!
                bSuccess = true;
                break;
            default:
                bSuccess = false;
                break;
        }
    }
    else
        bSuccess = true;
    return bSuccess;
}


bool ScreenCaptureNative::existsFile(std::string filename) {
	struct stat   buffer;
    if (stat (filename.c_str(), &buffer) == 0){
    	return true;
    }else{
    	return false;
    }
}

long ScreenCaptureNative::getActiveTTY(){
	long lret=0;
	string appstr="";
	FILE *fp;
	fp = fopen("/sys/class/tty/console/active" , "r");
	char apps[2048];
	if(fp != NULL) {
		int rd = fread(apps, 1, sizeof(apps), fp);
		apps[rd]=0;
		trimnl(apps);
		appstr.append(apps);
		fclose(fp);
	}
	appstr.insert(0,"/sys/class/tty/");
	appstr.append("/active");
	fp = fopen(appstr.c_str() , "r");
	if(fp != NULL) {
		int rd = fread(apps, 1, sizeof(apps), fp);
		apps[rd]=0;
		trimnl(apps);
		appstr.clear();
		appstr.append(apps);
		fclose(fp);
		struct stat buf;
		appstr.insert(0,"/dev/");
		if (stat(appstr.c_str(),&buf)==0){
			lret=buf.st_rdev;
			//printf("dev: %d\n", buf.st_rdev);
		}
	}
	return lret;
}

long ScreenCaptureNative::getProcessTTY(char* pid) {
	char P_state;
	int P_ppid, P_pgrp, P_session, P_tty_num, P_tpgid;
	unsigned long P_flags, P_min_flt, P_cmin_flt, P_maj_flt, P_cmaj_flt, P_utime, P_stime;
	long P_cutime, P_cstime, P_priority, P_nice, P_timeout, P_alarm;
	unsigned long P_start_time, P_vsize;
	long P_rss;
	unsigned long P_rss_rlim, P_start_code, P_end_code, P_start_stack, P_kstk_esp, P_kstk_eip;
	unsigned P_signal, P_blocked, P_sigignore, P_sigcatch;
	unsigned long P_wchan, P_nswap, P_cnswap;

    char buf[800];
    int num;
    int fd;
    char* tmp;
    struct stat sb;
    snprintf(buf, 32, "/proc/%s/stat", pid);
    if ( (fd = open(buf, O_RDONLY, 0) ) == -1 ) return 0;
    num = read(fd, buf, sizeof buf - 1);
    fstat(fd, &sb);
    close(fd);
    if(num<80) return 0;
    buf[num] = '\0';
    tmp = strrchr(buf, ')');
    *tmp = '\0';
    num = sscanf(tmp + 2,
       "%c "
       "%d %d %d %d %d "
       "%lu %lu %lu %lu %lu %lu %lu "
       "%ld %ld %ld %ld %ld %ld "
       "%lu %lu "
       "%ld "
       "%lu %lu %lu %lu %lu %lu "
       "%u %u %u %u "
       "%lu %lu %lu",
       &P_state,
       &P_ppid, &P_pgrp, &P_session, &P_tty_num, &P_tpgid,
       &P_flags, &P_min_flt, &P_cmin_flt, &P_maj_flt, &P_cmaj_flt, &P_utime, &P_stime,
       &P_cutime, &P_cstime, &P_priority, &P_nice, &P_timeout, &P_alarm,
       &P_start_time, &P_vsize,
       &P_rss,
       &P_rss_rlim, &P_start_code, &P_end_code, &P_start_stack, &P_kstk_esp, &P_kstk_eip,
       &P_signal, &P_blocked, &P_sigignore, &P_sigcatch,
       &P_wchan, &P_nswap, &P_cnswap
    );
    return P_tty_num;
}

bool ScreenCaptureNative::setXEnvirionment(long actty){
	bool bret=false;
	string appxauthority("");
	string appxwayland("");
	string appxdisplay("");
	string cmdxauthority("");
	string cmdxdisplay("");
	string detectedxdisplay(":0");
	DIR *d;
	struct dirent *dir;
	d = opendir("/proc");
	if (d) {
		while ((dir = readdir(d)) != NULL) {
			//Prende solo i pid
			bool bisNum=true;
			for (int i=0; i<=(int)strlen(dir->d_name)-1; i++) {
				if(!(isdigit(dir->d_name[i]))) {
					bisNum=false;
					break;
				}
			}
			if ((bisNum) && ((actty==0) || (actty==getProcessTTY(dir->d_name)))){
				//printf("%s\n", dir->d_name);

				string appstr;

				//LEGGE ENVIRIONMENT
				appstr.append("/proc/");
				appstr.append(dir->d_name);
				appstr.append("/");
				appstr.append("environ");
				char appline[64*1024];
				FILE *fp;
				fp = fopen(appstr.c_str() , "r");
				if(fp != NULL) {
					int rc=fread(appline, 1, sizeof(appline), fp);
					string item;
					for (int i=0; i<=rc-1; i++) {
						char c = appline[i];
						if (c=='\0'){
							if (item.compare(0,11,"XAUTHORITY=")==0){
								appxauthority = item.substr(11);
							}
							if (item.compare(0,16,"WAYLAND_DISPLAY=")==0){
								appxwayland = item.substr(16);
							}
							if (item.compare(0,8,"DISPLAY=")==0){
								appxdisplay = item.substr(8);
							}
							//printf("%s\n", item.c_str());
							item.clear();
						}else{
							item.push_back(c);
						}
					}
					fclose(fp);

					if (((appxauthority.compare("")!=0) && (appxdisplay.compare("")!=0)) ||
						((appxwayland.compare("")!=0) && (appxdisplay.compare("")!=0))){
						break;
					}else if (appxdisplay.compare("")!=0){
						detectedxdisplay=appxdisplay;
					}
					appxauthority="";
					appxwayland="";
					appxdisplay="";
				}

				//LEGGE COMMANDLINE
				if (cmdxauthority==""){
					appstr.clear();
					appstr.append("/proc/");
					appstr.append(dir->d_name);
					appstr.append("/");
					appstr.append("cmdline");
					fp = fopen(appstr.c_str() , "r");
					if(fp != NULL) {
						int rc=fread(appline, 1, sizeof(appline), fp);
						string item;
						for (int i=0; i<=rc-1; i++) {
							char c = appline[i];
							if (c=='\0'){
								if (cmdxauthority=="XAUTHORITY"){
									cmdxauthority=item;
								}else{
									if (item=="-auth"){
										cmdxauthority = "XAUTHORITY";
									}else if (((item.size()==2) && (item.compare(0,1,":")==0) && isdigit(item.c_str()[1]))){
										cmdxdisplay = item;
									}
								}
								//printf("%s\n", item.c_str());
								item.clear();
							}else{
								item.push_back(c);
							}
						}
						fclose(fp);
						if (cmdxauthority=="XAUTHORITY"){
							cmdxauthority="";
						}
						if ((cmdxauthority!="") && (cmdxdisplay=="")){
							cmdxdisplay=detectedxdisplay;
						}
					}
				}
			}
		}
		closedir(d);
	}

	/*
	printf("tty %d \n",actty);
	printf("appxauthority %s \n",appxauthority.c_str());
	printf("appxwayland %s \n",appxwayland.c_str());
	printf("appxdisplay %s \n",appxdisplay.c_str());
	printf("cmdxauthority %s \n",cmdxauthority.c_str());
	printf("cmdxdisplay %s \n",cmdxdisplay.c_str());
	printf("detectedxdisplay %s \n",detectedxdisplay.c_str());
	*/

	//Verifica Differenze
	if ((appxauthority!="") || (appxwayland!="")){
		if (envxauthority!=appxauthority){
			envxauthority=appxauthority;
			bret=true;
		}
		if (envxwayland!=appxwayland){
			envxwayland=appxwayland;
			bret=true;
		}
		if (envxdisplay!=appxdisplay){
			envxdisplay=appxdisplay;
			bret=true;
		}
	}else{
		if ((cmdxauthority!="") && (cmdxdisplay!="")){
			if ((envxauthority!=cmdxauthority) || (envxdisplay!=cmdxdisplay)){
				//Se non esiste il file xauthority lo crea
				if (!existsFile(cmdxauthority)){
					makeDirs(cmdxauthority.substr(0, cmdxauthority.find_last_of('/')));
					int fdauth = open(cmdxauthority.c_str(), O_RDWR|O_CREAT, 0600);
					if (fdauth != -1) {
						close(fdauth);
					}else{
						cmdxauthority="";
					}
				}
				envxauthority=cmdxauthority;
				envxdisplay=cmdxdisplay;
				bret=true;
			}
		}else if (envxdisplay!=detectedxdisplay){
			envxdisplay=detectedxdisplay;
			bret=true;
		}
	}

	if (bret){
		//Imposta le variabili di ambiente
		if (envxauthority!=""){
			setenv("XAUTHORITY",envxauthority.c_str(),1);
			//printf("XAUTHORITY %s \n",envxauthority.c_str());
		}else{
			unsetenv("XAUTHORITY");
			//printf("unset XAUTHORITY \n");
		}
		if (envxwayland!=""){
			setenv("WAYLAND_DISPLAY",envxwayland.c_str(),1);
			//printf("WAYLAND_DISPLAY %s \n",envxwayland.c_str());
		}else{
			unsetenv("WAYLAND_DISPLAY");
			//printf("unset WAYLAND_DISPLAY \n");
		}
		if (envxdisplay!=""){
			setenv("DISPLAY",envxdisplay.c_str(),1);
			//printf("DISPLAY %s \n",envxdisplay.c_str());
		}else{
			unsetenv("DISPLAY");
			//printf("unset DISPLAY \n");
		}
	}
	return bret;
}

int ScreenCaptureNative::getMonitorCount() {
	int elapsed=monitorsCounter.getCounter();
	if ((firstmonitorscheck) || (elapsed>=MONITORS_INTERVAL)){
		firstmonitorscheck=false;

		monitorsInfo.clear();

		bool changedactty=false;
		bool changedenvs=false;

		//Verifica se cambiato activetty
		long actty = getActiveTTY();
		if (activeTTY!=actty){
			activeTTY=actty;
			envxauthority.clear();
			envxwayland.clear();
			envxdisplay.clear();
			changedactty=true;
		}

		//Verifica se cambiate display e envs
		changedenvs=setXEnvirionment(activeTTY);

		if ((xdpy == NULL) || (changedactty) || (changedenvs)){
			for(vector<ScreenShotInfo>::size_type i = 0; i < screenShotInfo.size(); i++) {
				termScreenShotInfo(&screenShotInfo[i]);
			}
			screenShotInfo.clear();
			if (xdpy != NULL) {
				XCloseDisplay(xdpy);
				unloadKeyMap();
			}
			if ((xdpy = XOpenDisplay(NULL)) != NULL) {
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
				loadKeyMap();
			}else{
				activeTTY=0;
				monitorsCounter.reset();
				return 0;
			}
		}

		if (handleXrandr) {
			int maxw=0;
			int maxh=0;
			XRRScreenResources *res = (*callXRRGetScreenResourcesCurrent)(xdpy, root);
			for( int j = 0; j < res->ncrtc; j++ ) {
				XRRCrtcInfo *crtc_info = (*callXRRGetCrtcInfo)(xdpy, res, res->crtcs[j]);
				if (crtc_info->noutput){
					MonitorInfo mi;
					mi.x=crtc_info->x;
					mi.y=crtc_info->y;
					mi.w=crtc_info->width;
					mi.h=crtc_info->height;
					monitorsInfo.push_back(mi);
					int appw=crtc_info->x+crtc_info->width;
					if (appw>maxw){
						maxw=appw;
					}
					int apph=crtc_info->y+crtc_info->height;
					if (apph>maxh){
						maxh=apph;
					}
				}
				callXRRFreeCrtcInfo(crtc_info);
			}
			callXRRFreeScreenResources(res);


			if (monitorsInfo.size()>1){
				MonitorInfo mi;
				mi.x=0;
				mi.y=0;
				mi.w=maxw;
				mi.h=maxh;
				monitorsInfo.insert(monitorsInfo.begin(),mi);
			}
		}
		if (monitorsInfo.size()==0){
			MonitorInfo mi;
			mi.x=0;
			mi.y=0;
			mi.w=screen->width;
			mi.h=screen->height;
			monitorsInfo.push_back(mi);
		}
		for(vector<MonitorInfo>::size_type i = 0; i < monitorsInfo.size(); i++) {
			if (i>=screenShotInfo.size()){
				ScreenShotInfo ii;
				newScreenShotInfo(&ii, monitorsInfo[i].w, monitorsInfo[i].h);
				screenShotInfo.push_back(ii);
			}else{
				if ((monitorsInfo[i].w!=screenShotInfo[i].w) || (monitorsInfo[i].h!=screenShotInfo[i].h)){
					termScreenShotInfo(&screenShotInfo[i]);
					newScreenShotInfo(&screenShotInfo[i], monitorsInfo[i].w, monitorsInfo[i].h);
				}
			}
		}
		for(vector<ScreenShotInfo>::size_type i = monitorsInfo.size(); i < screenShotInfo.size(); i++) {
			termScreenShotInfo(&screenShotInfo[i]);
			screenShotInfo.erase(screenShotInfo.begin() + i);
			i--;
		}
		monitorsCounter.reset();
	}
	if (monitorsInfo.size()<=1){ //Non trovato nessun monitor solo un monitor
		return monitorsInfo.size();
	}else{
		return monitorsInfo.size()-1;
	}

}

ScreenCaptureNative::MonitorInfo* ScreenCaptureNative::getMonitorInfo(int idx){
	if ((monitorsInfo.size()==1) && ((idx==0) || (idx==1))){ //Non trovato nessun monitor
		return &monitorsInfo[0];
	}else if ((idx>=0) && (idx<=(int)monitorsInfo.size()-1)){
		return &monitorsInfo[idx];
	}else{
		return NULL;
	}
}

void ScreenCaptureNative::newScreenShotInfo(ScreenShotInfo* ii, int w, int h) {
	ii->w = w;
	ii->h = h;
	ii->image = NULL;
	//ii->data161616 = NULL;
	ii->shotID=-1;
	ii->intervallCounter.reset();
}

void ScreenCaptureNative::initScreenShotInfo(ScreenShotInfo* ii) {
	termScreenShotInfo(ii);

	int imageW=ii->w;
	int imageH=ii->h;
	ii->image = XShmCreateImage(xdpy, visual, depth, ZPixmap, NULL, &ii->m_shmseginfo, imageW, imageH);
	ii->m_shmseginfo.shmid = shmget(IPC_PRIVATE, ii->image->bytes_per_line * imageH, IPC_CREAT | 0777);
	ii->m_shmseginfo.shmaddr = reinterpret_cast<char*>(shmat(ii->m_shmseginfo.shmid, NULL, 0));
	ii->image->data = ii->m_shmseginfo.shmaddr;
	ii->m_shmseginfo.readOnly = False;
	XShmAttach(xdpy, &ii->m_shmseginfo);

	//char c[100];
	//sprintf(c,"############### rm:%d gm:%d bm:%d",image->red_mask,image->green_mask,image->blue_mask);
	//dwdbg->print(c);

	int redbits=countSetBits(ii->image->red_mask);
	int greenbits=countSetBits(ii->image->green_mask);
	int bluebits=countSetBits(ii->image->blue_mask);
	if (redbits<8){
		ii->redrshift=8-redbits;
	}else{
		ii->redrshift=0;
	}
	if (greenbits<8){
		ii->greenrshift=8-greenbits;
	}else{
		ii->greenrshift=0;
	}
	if (bluebits<8){
		ii->bluershift=8-bluebits;
	}else{
		ii->bluershift=0;
	}
	ii->redlshift=(bluebits+greenbits)-ii->redrshift;
	ii->greenlshift=bluebits-ii->greenrshift;
	ii->shotID=0;
}


void ScreenCaptureNative::termScreenShotInfo(ScreenShotInfo* ii) {
	if (ii->shotID>=0){
		if (ii->image != NULL) {
			XShmDetach(xdpy,&ii->m_shmseginfo);
			XDestroyImage(ii->image);
			shmdt(ii->m_shmseginfo.shmaddr);
			shmctl(ii->m_shmseginfo.shmid, IPC_RMID, 0);
			ii->image = NULL;
		}
		ii->shotID=-1;
	}
}

ScreenCaptureNative::ScreenShotInfo* ScreenCaptureNative::getScreenShotInfo(int idx){
	if ((idx==1) && (screenShotInfo.size()==1)){ //Non trovato nessun monitor
		return &screenShotInfo[0];
	}else if (idx <= (int)screenShotInfo.size() - 1){
		return &screenShotInfo[idx];
	}else{
		return NULL;
	}
}

long ScreenCaptureNative::captureScreen(int monitor, int distanceFrameMs, CAPTURE_IMAGE* capimage){
	capimage->width = 0;
	capimage->height = 0;

	int x = 0;
	int y = 0;
	int w = 0;
	int h = 0;

	MonitorInfo* mi = getMonitorInfo(monitor);
	if (mi==NULL){
		return -2; //Identifica Monitor non trovato
	}

	x=mi->x;
	y=mi->y;
	w=mi->w;
	h=mi->h;

	ScreenShotInfo* ii = getScreenShotInfo(monitor);
	if (ii==NULL) {
		return -3; //Identifica ScreenShotInfo non trovato
	}

	if (ii->shotID==-1){
		initScreenShotInfo(ii);
	}


	if ((ii->shotID==0) || (ii->intervallCounter.getCounter()>=distanceFrameMs)) {
		ii->intervallCounter.reset();
		XShmGetImage(xdpy, root, ii->image, x, y, AllPlanes);
		/*
		destroyImage();
		image = XGetImage(xdpy, root, x, y, w, h, AllPlanes, ZPixmap);*/
		ii->shotID+=1;
	}
	capimage->data = (unsigned char*)ii->image->data;
	capimage->bpp = ii->image->bits_per_pixel;
	capimage->redmask=ii->image->red_mask;
	capimage->greenmask=ii->image->green_mask;
	capimage->bluemask=ii->image->blue_mask;
	capimage->redlshift=ii->redlshift;
	capimage->greenlshift=ii->greenlshift;
	capimage->bluershift=ii->bluershift;
	if (capimage->bpp>24){
		capimage->bpc=4;
	}else if (capimage->bpp>16){
		capimage->bpc=3;
	}else if (capimage->bpp>8){
		capimage->bpc=2;
	}else{
		capimage->bpc=1;
	}
	capimage->width = w;
	capimage->height = h;
	return ii->shotID;
}

bool ScreenCaptureNative::captureCursor(int monitor, int* info, long& id, unsigned char** data) {
	unsigned int mask_return;
	Window window_returned;
	int win_x, win_y;
	if (XQueryPointer(xdpy,root,&window_returned,&window_returned,&cursorX,&cursorY,&win_x,&win_y,&mask_return)==True){
		if (id==-1){
			getCursorImage(CURSOR_TYPE_ARROW_18_18,&cursorW,&cursorH,&cursoroffsetX,&cursoroffsetY,data);
			cursorID++;
		}
		id=cursorID;
		info[0]=True;
		MonitorInfo* mi = getMonitorInfo(monitor);
		if (mi!=NULL){
			info[1]=cursorX-mi->x;
			info[2]=cursorY-mi->y;
		}else{
			info[1]=cursorX;
			info[2]=cursorY;
		}
		info[3]=cursorW;
		info[4]=cursorH;
		info[5]=cursoroffsetX;
		info[6]=cursoroffsetY;
		return true;
	}else{
		return false;
	}
}

bool ScreenCaptureNative::getActiveWinPos(long* id, int* info){
	return false;
}

void ScreenCaptureNative::loadKeyMap() {
	XkbDescPtr xkb = XkbGetMap(xdpy, XkbAllComponentsMask, XkbUseCoreKbd); //XkbAllClientInfoMask
	XkbClientMapPtr cm = xkb->map;
	for (int i=xkb->min_key_code;i<=xkb->max_key_code;i++){
		int oft=cm->key_sym_map[i].offset;
		if (cm->key_sym_map[i].group_info==0){
			KEYMAP* keyMap = new KEYMAP[4];
			for (int i=0;i<max_grp;i++){
				keyMap[i].unicode=0;
				keyMap[i].sym=NoSymbol;
				keyMap[i].code=i;
				keyMap[i].modifier=0;
			}
			arNewUnicodeMap.push_back(keyMap);
		}else{
			for (int g=0;g<=cm->key_sym_map[i].group_info-1;g++){
				if (g<max_grp){
					int ig=cm->key_sym_map[i].kt_index[g];
					//KEYSYM
					for (int l=0;l<=cm->types[ig].num_levels-1;l++){
						KeySym ks = xkb->map->syms[oft];
						if (ks!=NoSymbol){
							long uc = keysym2ucs(ks);
							if (uc!=-1){
								//Se non esiste le crea
								map<int,KEYMAP*>::iterator itmap = hmUnicodeMap.find(uc);
								KEYMAP* keyMap;
								if (itmap==hmUnicodeMap.end()){ //NON ESISTE
									keyMap = new KEYMAP[4];
									for (int g=0;g<max_grp;g++){
										keyMap[g].unicode=0;
										keyMap[g].sym=NoSymbol;
										keyMap[g].code=0;
										keyMap[g].modifier=0;
									}
									hmUnicodeMap[uc]=keyMap;
								}else{
									keyMap=itmap->second;
								}
								if (keyMap[g].code==0){//NON ASSEGNATO IN PRECEDENZA
									keyMap[g].unicode=uc;
									keyMap[g].sym=ks;
									keyMap[g].code=i;
									//TYPES
									for (int m=0;m<=cm->types[ig].map_count-1;m++){
										if (l==cm->types[ig].map[m].level){
											keyMap[g].modifier=cm->types[ig].map[m].mods.mask;
											break;
										}
									}
								}
							}

						}
						oft++;
					}
				}
			}
		}
	}
	XkbFreeClientMap(xkb, XkbAllComponentsMask, true);
}

void ScreenCaptureNative::unloadKeyMap() {
	for (std::map<int,KEYMAP*>::iterator it=hmUnicodeMap.begin(); it!=hmUnicodeMap.end(); ++it){
		delete [] it->second;
	}
	hmUnicodeMap.clear();
	for (std::vector<KEYMAP*>::iterator it = arNewUnicodeMap.begin() ; it != arNewUnicodeMap.end(); ++it){
		delete [] *it;
	}
	arNewUnicodeMap.clear();
}

KeySym ScreenCaptureNative::getKeySym(const char* key){
	if (strcmp(key,"CONTROL")==0){
		return XK_Control_L;
	}else if (strcmp(key,"ALT")==0){
		return XK_Alt_L;
	}else if (strcmp(key,"SHIFT")==0){
		return XK_Shift_L;
	}else if (strcmp(key,"TAB")==0){
		return XK_Tab;
	}else if (strcmp(key,"ENTER")==0){
		return XK_Return;
	}else if (strcmp(key,"BACKSPACE")==0){
		return XK_BackSpace;
	}else if (strcmp(key,"CLEAR")==0){
		return XK_Clear;
	}else if (strcmp(key,"PAUSE")==0){
		return XK_Pause;
	}else if (strcmp(key,"ESCAPE")==0){
		return XK_Escape;
	}else if (strcmp(key,"SPACE")==0){
		return XK_space;
	}else if (strcmp(key,"DELETE")==0){
		return XK_Delete;
	}else if (strcmp(key,"INSERT")==0){
		return XK_Insert;
	}else if (strcmp(key,"HELP")==0){
		return XK_Help;
	}else if (strcmp(key,"LEFT_WINDOW")==0){
		return 0;
	}else if (strcmp(key,"RIGHT_WINDOW")==0){
		return 0;
	}else if (strcmp(key,"SELECT")==0){
		return XK_Select;
	}else if (strcmp(key,"PAGE_UP")==0){
		return XK_Page_Up;
	}else if (strcmp(key,"PAGE_DOWN")==0){
		return XK_Page_Down;
	}else if (strcmp(key,"END")==0){
		return XK_End;
	}else if (strcmp(key,"HOME")==0){
		return XK_Home;
	}else if (strcmp(key,"LEFT_ARROW")==0){
		return XK_Left;
	}else if (strcmp(key,"UP_ARROW")==0){
		return XK_Up;
	}else if (strcmp(key,"DOWN_ARROW")==0){
		return XK_Down;
	}else if (strcmp(key,"RIGHT_ARROW")==0){
		return XK_Right;
	}else if (strcmp(key,"F1")==0){
		return XK_F1;
	}else if (strcmp(key,"F2")==0){
		return XK_F2;
	}else if (strcmp(key,"F3")==0){
		return XK_F3;
	}else if (strcmp(key,"F4")==0){
		return XK_F4;
	}else if (strcmp(key,"F5")==0){
		return XK_F5;
	}else if (strcmp(key,"F6")==0){
		return XK_F6;
	}else if (strcmp(key,"F7")==0){
		return XK_F7;
	}else if (strcmp(key,"F8")==0){
		return XK_F8;
	}else if (strcmp(key,"F9")==0){
		return XK_F9;
	}else if (strcmp(key,"F10")==0){
		return XK_F10;
	}else if (strcmp(key,"F11")==0){
		return XK_F11;
	}else if (strcmp(key,"F12")==0){
		return XK_F12;
	}else{
		return XStringToKeysym(key);
	}
	return 0;
}

KeyCode ScreenCaptureNative::addKeyUnicode(int uc) {
	XkbDescPtr xkb = XkbGetMap(xdpy, XkbAllComponentsMask, XkbUseCoreKbd);
	KeySym sym=ucs2keysym(uc);
	if (sym!=NoSymbol){
		KeyCode kc=247;
		int* ari=new int[1];
		ari[0]=0;
		XkbChangeTypesOfKey(xkb,kc,1,XkbGroup1Mask,ari,NULL);
		delete [] ari;
		KeySym* appks = XkbResizeKeySyms(xkb,kc,1);
		appks[0]=sym;
		xkb->device_spec=XkbUseCoreKbd;
		XkbMapChangesRec changes;
		changes.changed = XkbKeySymsMask;
		changes.first_key_sym = kc;
		changes.num_key_syms = 1;
		XkbChangeMap(xdpy, xkb, &changes);
		return kc;
	}
	return 0;
}

void ScreenCaptureNative::ctrlaltshift(bool ctrl, bool alt, bool shift){
	if ((ctrl) && (!ctrlDown)){
		ctrlDown=true;
		KeyCode kc = XKeysymToKeycode(xdpy, XK_Control_L);
		XTestFakeKeyEvent(xdpy, kc, True, CurrentTime);
	}else if ((!ctrl) && (ctrlDown)){
		ctrlDown=false;
		KeyCode kc = XKeysymToKeycode(xdpy, XK_Control_L);
		XTestFakeKeyEvent(xdpy, kc, False, CurrentTime);
	}

	if ((alt) && (!altDown)){
		altDown=true;
		KeyCode kc = XKeysymToKeycode(xdpy, XK_Alt_L);
		XTestFakeKeyEvent(xdpy, kc, True, CurrentTime);
	}else if ((!alt) && (altDown)){
		altDown=false;
		KeyCode kc = XKeysymToKeycode(xdpy, XK_Alt_L);
		XTestFakeKeyEvent(xdpy, kc, False, CurrentTime);
	}

	if ((shift) && (!shiftDown)){
		shiftDown=true;
		KeyCode kc = XKeysymToKeycode(xdpy, XK_Shift_L);
		XTestFakeKeyEvent(xdpy, kc, True, CurrentTime);
	}else if ((!shift) && (shiftDown)){
		shiftDown=false;
		KeyCode kc = XKeysymToKeycode(xdpy, XK_Shift_L);
		XTestFakeKeyEvent(xdpy, kc, False, CurrentTime);
	}
}


void ScreenCaptureNative::inputKeyboard(const char* type, const char* key, bool ctrl, bool alt, bool shift, bool command){
	if (xdpy != NULL) {
		if (strcmp(type,"CHAR")==0){
			int uc = atoi(key);
			//Legge lo stato della tastiera
			XkbStateRec kbstate;
			XkbGetState(xdpy, XkbUseCoreKbd, &kbstate);
			int curg=kbstate.group;
			KeyCode kc = 0;
			int md = 0;
			//Cerca il symbolo nella tastiera
			map<int,KEYMAP*>::iterator itmap = hmUnicodeMap.find(uc);
			KEYMAP* keyMap;
			if (itmap!=hmUnicodeMap.end()){ //NON ESISTE
				keyMap=itmap->second;
				//Verifica il keycode per il gruppo corrente
				kc=keyMap[curg].code;
				md=keyMap[curg].modifier;
				//Verifica il keycode per gli altri gruppi
				if (kc==0){
					for (int g=0;g<max_grp;g++){
						if (keyMap[g].code!=0){
							curg=g;
							kc = keyMap[curg].code;
							md = keyMap[curg].modifier;
							break;
						}
					}
				}
			}else{
				kc=addKeyUnicode(uc);
			}
			//Simula il tasto
			if (kc!=0){

				//Cambia tastiera se necessario
				if (curg!=kbstate.group){
					XkbLockGroup(xdpy, XkbUseCoreKbd, curg);
					//VERIFICARE SE NECESSARIO XkbLatchGroup
					//XkbLatchGroup(xdpy, XkbUseCoreKbd, curg);
				}

				//Imposta modifiers
				if (md!=kbstate.locked_mods){
					XkbLockModifiers(xdpy,XkbUseCoreKbd,255,md);
					//VERIFICARE SE NECESSARIO XkbLatchModifiers
					//XkbLatchModifiers(xdpy, XkbUseCoreKbd, 255, md);
				}

				XTestFakeKeyEvent(xdpy, kc, True, CurrentTime);
				XTestFakeKeyEvent(xdpy, kc, False, CurrentTime);

				//Ripristina modifiers
				if (md!=kbstate.locked_mods){
					XkbLockModifiers(xdpy,XkbUseCoreKbd,255,kbstate.locked_mods);
					//VERIFICARE SE NECESSARIO XkbLatchModifiers
					//XkbLatchModifiers(xdpy, XkbUseCoreKbd, 255, kbstate.locked_mods);
				}
				XFlush(xdpy);
			}
		}else if (strcmp(type,"KEY")==0){
			KeySym ks = getKeySym(key);
			if (ks!=0){
				KeyCode kc = XKeysymToKeycode(xdpy, ks);
				if (kc!=0){
					ctrlaltshift(ctrl,alt,shift);
					XTestFakeKeyEvent(xdpy, kc, True, CurrentTime);
					XTestFakeKeyEvent(xdpy, kc, False, CurrentTime);
					ctrlaltshift(false,false,false);
					XFlush(xdpy);
				}
			}
		}else if (strcmp(type,"CTRLALTCANC")==0){

		}
	}

	/*if (xdpy != NULL) {
		KeySym ks = getKeySym(key);
		if (ks!=0){
			KeyCode kc = XKeysymToKeycode(xdpy, ks);
			XTestFakeKeyEvent(xdpy, kc, True, CurrentTime);
			XTestFakeKeyEvent(xdpy, kc, False, CurrentTime);
			XFlush(xdpy);

			XSync(xdpy, False);
		}
	}
	//void ScreenCaptureNative::inputKeyboardChar(int uc) {
	char s[5];
	sprintf(s, "U%x", uc);
	KeySym sym  = XStringToKeysym(s);
	if (lastuc!=uc){
		int min, max, numcodes;
		KeySym *keysym;
		XDisplayKeycodes(xdpy,&min,&max);
		keysym = XGetKeyboardMapping(xdpy,min,max-min+1,&numcodes);
		keysym[(max-min-1)*numcodes]=sym;
		XChangeKeyboardMapping(xdpy,min,numcodes,keysym,(max-min));
		XFree(keysym);
		//XFlush(xdpy);
		lastuc=uc;
	}
	KeyCode kc = XKeysymToKeycode(xdpy,sym);
	XTestFakeKeyEvent(xdpy, kc, True, CurrentTime);
	XTestFakeKeyEvent(xdpy, kc, False, CurrentTime);
	XFlush(xdpy);

	XSync(xdpy, False);*/
}

void ScreenCaptureNative::mouseMove(int x,int y){
	//XTestFakeMotionEvent(xdpy, -1, x, y, CurrentTime);
	XWarpPointer(xdpy, None, root, 0, 0, 0, 0, x, y);
	XFlush(xdpy);
}

void ScreenCaptureNative::mouseButton(int button,bool press){
	XTestFakeButtonEvent(xdpy, button, press, CurrentTime);
	XFlush(xdpy);
	/*XEvent event;
    memset(&event, 0x00, sizeof(event));
    if (press){
    	event.type = ButtonPress;
    }else{
    	event.type = ButtonRelease;
    	event.xbutton.state = 0x100;
    }
    event.xbutton.button = button;
    event.xbutton.same_screen = True;
    XQueryPointer(xdpy, root, &event.xbutton.root, &event.xbutton.window, &event.xbutton.x_root, &event.xbutton.y_root, &event.xbutton.x, &event.xbutton.y, &event.xbutton.state);
    event.xbutton.subwindow = event.xbutton.window;
    while(event.xbutton.subwindow){
        event.xbutton.window = event.xbutton.subwindow;
        XQueryPointer(xdpy, event.xbutton.window, &event.xbutton.root, &event.xbutton.subwindow, &event.xbutton.x_root, &event.xbutton.y_root, &event.xbutton.x, &event.xbutton.y, &event.xbutton.state);
    }
    XSendEvent(xdpy, PointerWindow, True, 0xfff, &event);
	 */
}

void ScreenCaptureNative::inputMouse(int monitor, int x, int y, int button, int wheel, bool ctrl, bool alt, bool shift, bool command){
	if (xdpy != NULL) {
		ctrlaltshift(ctrl,alt,shift);
		if ((x!=-1) && (y!=-1)){
			int mx=x;
			int my=y;
			MonitorInfo* mi = getMonitorInfo(monitor);
			if (mi!=NULL){
				mx=mx+mi->x;
				my=my+mi->y;
			}
			mouseMove(mx,my);
		}
		if (button==64) { //CLICK
			mouseButton(Button1, true);
			mouseButton(Button1, false);
		}else if (button==128) { //DBLCLICK
			mouseButton(Button1, true);
			mouseButton(Button1, false);

			//microsleep
			double milliseconds=200;
			struct timespec sleepytime;
			sleepytime.tv_sec = milliseconds / 1000;
			sleepytime.tv_nsec = (milliseconds - (sleepytime.tv_sec * 1000)) * 1000000;
			nanosleep(&sleepytime, NULL);

			mouseButton(Button1, true);
			mouseButton(Button1, false);
		}else if (button!=-1) {
			int appbtn=-1;
			if ((button & 1) && (!mousebtn1Down)){
				appbtn=Button1;
				mousebtn1Down=true;
			}else if (mousebtn1Down){
				appbtn=Button1;
				mousebtn1Down=false;
			}
			if (appbtn!=-1){
				mouseButton(appbtn, mousebtn1Down);
			}
			appbtn=-1;
			if ((button & 2) && (!mousebtn2Down)){
				appbtn=Button3;
				mousebtn2Down=true;
			}else if (mousebtn2Down){
				appbtn=Button3;
				mousebtn2Down=false;
			}
			if (appbtn!=-1){
				mouseButton(appbtn, mousebtn2Down);
			}
			appbtn=-1;
			if ((button & 4) && (!mousebtn3Down)){
				appbtn=Button2;
				mousebtn3Down=true;
			}else if (mousebtn3Down){
				appbtn=Button2;
				mousebtn3Down=false;
			}
			if (appbtn!=-1){
				mouseButton(appbtn, mousebtn3Down);
			}
		}
		if (wheel>0){
			mouseButton(4, true);
			mouseButton(4, false);
		}else if (wheel<0){
			mouseButton(5, true);
			mouseButton(5, false);
		}
	}
}

void ScreenCaptureNative::copy(){

}

void ScreenCaptureNative::paste(){

}

wchar_t* ScreenCaptureNative::getClipboardText(){
	return NULL;
}

void ScreenCaptureNative::setClipboardText(wchar_t* wText){
}



#endif
