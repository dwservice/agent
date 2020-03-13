/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/

//PROTOCOL DIFFERENCE: TYPE-DATA
// TYPE=0 DATA=W-H -> CHANGED RESOLUTION
// TYPE=1 DATA=L-V -> TOKEN DISTANCE FRAME MS
// TYPE=2 DATA=L-X-Y-W-H-IMG -> TOKEN FRAME
// TYPE=3 DATA=V-X-Y-W-H-OFFX-OFFY-IMG -> TOKEN CURSOR
//		V=Visible -> 1:YES 0:NO
// TYPE=4 DATA=SX-SY-SW-SH-DX-DY -> COPY AREA
// TYPE=10 DATA=SZ -> MONITOR COUNT
// TYPE=11 DATA=CNT-S1-S2-... -> SUPPORTED FRAME
// TYPE=701 -> CAPTURE LOCKED
// TYPE=702 -> CAPTURE UNLOCKED


#include "screencapture.h"

using namespace std;

ScreenCapture::ScreenCapture(DWDebugger* dbg)
		:captureNative(dbg){
	dwdbg=dbg;	
	lastSessionID=0;
	diffBufferSize = BUFFER_DIFF_SIZE;
	diffBuffer = (unsigned char*)calloc(diffBufferSize,sizeof(unsigned char));
	tjInstance = tjInitCompress();
}


ScreenCapture::~ScreenCapture(){
	if (tjInstance != NULL){
		tjDestroy(tjInstance);
	}
	tjInstance=NULL;
	free(diffBuffer);
	captureNative.terminate();
}

ScreenCaptureNative ScreenCapture::getNative(){
	return captureNative;
}

void ScreenCapture::inputsEvent(){
	distanceFrameMsCalculator.fast();
}

void ScreenCapture::loadQuality(SESSION* ses) {
	int quality=ses->quality;
	short rsz=0;
	short gsz=0;
	short bsz=0;
	if (quality<0 || quality>9){
		quality=9;
	}
	switch (quality){
		case 0:
			rsz=4;
			gsz=4;
			bsz=4;
			ses->jpegQuality=30;
		break;
		case 1:
			rsz=8;
			gsz=4;
			bsz=4;
			ses->jpegQuality=40;
		break;
		case 2:
			rsz=8;
			gsz=8;
			bsz=4;
			ses->jpegQuality=45;
		break;
		case 3:
			rsz=8;
			gsz=8;
			bsz=8;
			ses->jpegQuality=50;
		break;
		case 4:
			rsz=16;
			gsz=8;
			bsz=8;
			ses->jpegQuality=55;
		break;
		case 5:
			rsz=16;
			gsz=16;
			bsz=8;
			ses->jpegQuality=60;
		break;
		case 6:
			rsz=16;
			gsz=16;
			bsz=16;
			ses->jpegQuality=65;
		break;
		case 7:
			rsz=32;
			gsz=16;
			bsz=16;
			ses->jpegQuality=75;
		break;
		case 8:
			rsz=32;
			gsz=32;
			bsz=16;
			ses->jpegQuality=80;
		break;
		case 9:
			rsz=32;
			gsz=32;
			bsz=32;
			ses->jpegQuality=90;
		break;
	}
	//PALETTE
	ses->palette.redsize=rsz;
	ses->palette.greensize=gsz;
	ses->palette.bluesize=bsz;

	ses->palette.redcnt=countSetBits(rsz-1);
	ses->palette.greencnt=countSetBits(gsz-1);
	ses->palette.bluecnt=countSetBits(bsz-1);

	ses->palette.redsf=countSetBits((int)(255-(rsz-1)));
	ses->palette.greensf=countSetBits((int)(255-(gsz-1)));
	ses->palette.bluesf=countSetBits((int)(255-(bsz-1)));

}

int ScreenCapture::intToArray(unsigned char* buffer,int p,int i){
	buffer[p] = (i >> 24) & 0xFF;
	buffer[p+1] = (i >> 16) & 0xFF;
	buffer[p+2] = (i >> 8) & 0xFF;
	buffer[p+3] = i & 0xFF;
	return 4;
}

int ScreenCapture::byteArrayToInt(unsigned char* buffer,int p) {
    return ((buffer[p] << 24) + ((buffer[p+1] & 0xFF) << 16) + ((buffer[p+2] & 0xFF) << 8) + ((buffer[p+3] & 0xFF) << 0));
}

int ScreenCapture::shortToArray(unsigned char* buffer,int p,short s){
	buffer[p] = (s >> 8) & 0xFF;
	buffer[p+1] = s & 0xFF;
	return 2;
}

short ScreenCapture::byteArrayToShort(unsigned char* buffer,int p) {
    return (short) ((buffer[p] << 8) + (buffer[p+1] << 0));
}

void ScreenCapture::differenceCursor(SESSION &ses, CAPTURE_IMAGE &capimage,CallbackDifference cbdiff){
	dwdbg->print("ScreenCapture::prepareCursor#START");
	// TYPE=3 DATA=V-X-Y-W-H-OFFX-OFFY-IMG -> TOKEN CURSOR
	//		V=Visible -> 1:YES 0:NO
	bool bstore=false;
	int pbf=2;
	int elapsed=ses.cursorCounter.getCounter();
	if (elapsed>=MOUSE_INTERVAL){
		//CAPTURE CURSOR
		long cursorID=0;
		if (ses.cursorID==-1){
			cursorID=-1; //FORCE
		}
		int curInfo[7];
		unsigned char* rgbdata=NULL;
		dwdbg->print("ScreenCapture::prepareCursor#CAPTURE");
		if (captureNative.captureCursor(ses.monitor,curInfo,cursorID,&rgbdata)){
			bool cursorVisible=(curInfo[0]==1);
			int cursorx=curInfo[1];
			int cursory=curInfo[2];
			int cursorw=curInfo[3];
			int cursorh=curInfo[4];
			int cursoroffsetx=curInfo[5];
			int cursoroffsety=curInfo[6];
		
			if ((cursorVisible!=ses.cursorVisible) || (cursorx!=ses.cursorx) || (cursory!=ses.cursory) || (cursorID!=ses.cursorID)) {
				if (!cursorVisible){
					dwdbg->print("ScreenCapture::prepareCursor#INVISIBLE");
					bstore=true;
					diffBuffer[pbf]=0;
					pbf++;
				}else{
					if ((cursorID!=ses.cursorID) && (rgbdata!=NULL)){
						dwdbg->print("ScreenCapture::prepareCursor#VISIBLE_NEW_ID");
						bstore=true;
						diffBuffer[pbf]=1;
						pbf++;
						pbf+=shortToArray(diffBuffer,pbf,cursorx);
						pbf+=shortToArray(diffBuffer,pbf,cursory);
						pbf+=shortToArray(diffBuffer,pbf,cursorw);
						pbf+=shortToArray(diffBuffer,pbf,cursorh);
						pbf+=shortToArray(diffBuffer,pbf,cursoroffsetx);
						pbf+=shortToArray(diffBuffer,pbf,cursoroffsety);


						//Append cursor data
						int oldpbf=pbf;
						pbf+=shortToArray(diffBuffer,pbf,0);
						pbf+=shortToArray(diffBuffer,pbf,0);
						pbf+=shortToArray(diffBuffer,pbf,cursorw);
						pbf+=shortToArray(diffBuffer,pbf,cursorh);
						int appcrsz=cursorw*cursorh;
						unsigned char indata[(appcrsz*4)];
						int szb=0;
						int i=0;
						for (int ip=0;ip<appcrsz;ip++){
							unsigned char r=rgbdata[i];
							unsigned char g=rgbdata[i+1];
							unsigned char b=rgbdata[i+2];
							unsigned char a=rgbdata[i+3];
							indata[szb]=r;
							szb++;
							indata[szb]=g;
							szb++;
							indata[szb]=b;
							szb++;
							indata[szb]=a;
							szb++;
							i+=4;
						}
						//COMPRIME
						int zerr;
						int CHUNK=16384;
						unsigned char outdata[CHUNK];
						z_stream strm;
						strm.zalloc = Z_NULL;
						strm.zfree  = Z_NULL;
						strm.opaque = Z_NULL;
						//zerr=deflateInit(&strm, Z_DEFAULT_COMPRESSION);
						zerr=deflateInit(&strm, Z_BEST_SPEED);
						if (zerr == Z_OK){
							strm.next_in = (unsigned char *)indata;
							strm.avail_in = szb;
							do {
								strm.avail_out = CHUNK;
								strm.next_out = outdata;
								zerr=deflate(&strm, Z_FINISH);
								if (zerr == Z_STREAM_ERROR) {
									break;
								}
								int appsz = CHUNK-strm.avail_out;
								if (appsz>0){
									resizeDiffBufferIfNeed(appsz+pbf);
									memcpy(diffBuffer+pbf,outdata,appsz);
									pbf+=appsz;
								}
							}while (strm.avail_out == 0);
							deflateEnd(&strm);
							if (zerr == Z_STREAM_ERROR) {
								pbf=oldpbf;
							}
						}

					}else if ((cursorx!=ses.cursorx) || (cursory!=ses.cursory)){
						dwdbg->print("ScreenCapture::prepareCursor#VISIBLE_NEW_XY");
						bstore=true;
						diffBuffer[pbf]=1;
						pbf++;
						pbf+=shortToArray(diffBuffer,pbf,cursorx);
						pbf+=shortToArray(diffBuffer,pbf,cursory);
					}
				}
				//Inserisce SIZE Token
				shortToArray(diffBuffer,0,3);
				cbdiff(pbf,diffBuffer);
			}
			if (bstore){
				dwdbg->print("ScreenCapture::prepareCursor#STORE");
				ses.cursorVisible=cursorVisible;
				ses.cursorx=cursorx;
				ses.cursory=cursory;
				ses.cursorw=cursorw;
				ses.cursorh=cursorh;
				ses.cursoroffsetx=cursoroffsetx;
				ses.cursoroffsety=cursoroffsety;
				ses.cursorID=cursorID;
			}
		}
		if (rgbdata!=NULL){
			free(rgbdata);
		}
		ses.cursorCounter.reset();
	}
	dwdbg->print("ScreenCapture::prepareCursor#END");
}

/*
int ScreenCapture::prepareCopyArea(unsigned char* &bf,int p,int* cursz,SESSION &ses){
	int pbf=p;
	long activeWinID;
	int activeWinInfo[4];
	if (captureNative.getActiveWinPos(&activeWinID,activeWinInfo)){
		if (ses.activeWinID==activeWinID){
			if (((ses.activeWinX!=activeWinInfo[0]) || (ses.activeWinY!=activeWinInfo[1])) && 
				((ses.activeWinW==activeWinInfo[2] && ses.activeWinH==activeWinInfo[3]))){ //Non sto ridimenzionando
				int sx=ses.activeWinX;
				int sy=ses.activeWinY;
				int sw=ses.activeWinW;
				int sh=ses.activeWinH;
				int dx=activeWinInfo[0];
				int dy=activeWinInfo[1];
				if (dx<0){
					sw=sw+dx;
					sx=sx-dx;
					dx=0;
				}
				if (sx<0){
					sx=0;
				}
				if ((sx+sw)>ses.shotw){
					sw=sw-((sx+sw)-ses.shotw);
				}
				if ((dx+sw)>ses.shotw){
					sw=sw-((dx+sw)-ses.shotw);
				}
				if (dy<0){
					sh=sh+dy;
					sy=sy-dy;
					dy=0;
				}
				if (sy<0){
					sy=0;
				}
				if ((sy+sh)>ses.shoth){
					sh=sh-((sy+sh)-ses.shoth);
				}
				if ((dy+sh)>ses.shoth){
					sh=sh-((dy+sh)-ses.shoth);
				}
				if ((sw>0) && (sh>0)){
					//Copia l'area dalla vecchia immagine
					short* bfcopy = (short*)malloc((sw*sh)*sizeof(short)); 
					int j=0;
					int i=(sy*ses.shotw)+sx;
					int iskip=(ses.shotw-sw);
					int szbt=sizeof(short);
					for (int y=sy;y<sy+sh;y++){
						memcpy(bfcopy+j,ses.data+i,sw*szbt);
						j+=sw;
						i+=sw+iskip;
					}
					j=0;
					i=(dy*ses.shotw)+dx;
					for (int y=dy;y<dy+sh;y++){
						memcpy(ses.data+i,bfcopy+j,sw*szbt);
						j+=sw;
						i+=sw+iskip;
					}
					free(bfcopy);

					//Prepara la risposta
					// TYPE=4 DATA=SX-SY-SW-SH-DX-DY -> COPY AREA
					resizeBufferIfNeed(bf,cursz,pbf+100);
					pbf+=intToArray(bf,pbf,14);
					pbf+=shortToArray(bf,pbf,4);
					pbf+=shortToArray(bf,pbf,sx);
					pbf+=shortToArray(bf,pbf,sy);
					pbf+=shortToArray(bf,pbf,sw);
					pbf+=shortToArray(bf,pbf,sh);
					pbf+=shortToArray(bf,pbf,dx);
					pbf+=shortToArray(bf,pbf,dy);
					//printf("TYPE=4 %d %d %d %d %d %d\n",sx,sy,sw,sh,dx,dy);
				}				
			}
		}
		ses.activeWinID=activeWinID;
		ses.activeWinX=activeWinInfo[0];
		ses.activeWinY=activeWinInfo[1];
		ses.activeWinW=activeWinInfo[2];
		ses.activeWinH=activeWinInfo[3];
	}
	return pbf-p;
}*/

void ScreenCapture::areaChanged(CAPTURE_CHANGE_AREA* area) {

}

void ScreenCapture::areaMoved(CAPTURE_MOVE_AREA* area) {

}

void ScreenCapture::differenceFrameTJPEG(SESSION &ses, CAPTURE_IMAGE &capimage,CallbackDifference cbdiff){
	int gapmin=50;
	unsigned long sz = (ses.shotw*ses.shoth);
	bool firstdata = false;
	CAPTURE_RGB rgb;
	if (ses.data == NULL) {
		ses.data = (unsigned char*)malloc((sz*3) * sizeof(unsigned char));
		firstdata = true;
	}
	//detect changes and make blocks
	vector<DIFFRECT>ardiff;
	//vector<DIFFRECT>arhorizgap;
	DIFFRECT drcur = DIFFRECT();
	drcur.x1=-1;
	drcur.y1=-1;
	drcur.x2=-1;
	drcur.y2=-1;
	unsigned long inew=0;
	unsigned long ip=0;
	unsigned long cntsz=0;
	for (int y=0;y<ses.shoth;y++){
		if ((drcur.y2!=-1) && ((y-drcur.y2>=gapmin) || (cntsz>=TJPEG_SPLIT_SIZE))){
			ardiff.push_back(drcur);
			drcur = DIFFRECT();
			drcur.x1=-1;
			drcur.y1=-1;
			drcur.x2=-1;
			drcur.y2=-1;
		}
		for (int x=0;x<ses.shotw;x++){
			getRGB(capimage, inew, rgb);
			if ((firstdata==true) || (rgb.red!=ses.data[ip]) || (rgb.green!=ses.data[ip+1]) || (rgb.blue!=ses.data[ip+2])){
				ses.data[ip]=rgb.red;
				ses.data[ip+1]=rgb.green;
				ses.data[ip+2]=rgb.blue;
				if (drcur.x1==-1){
					drcur.x1=drcur.x2=x;
					drcur.y1=drcur.y2=y;
					cntsz=0;
				}else{
					if (x<drcur.x1){
						drcur.x1=x;
					}
					if (x>drcur.x2){
						drcur.x2=x;
					}
					if (y<drcur.y1){
						drcur.y1=y;
					}
					if (y>drcur.y2){
						drcur.y2=y;
					}
					cntsz+=3;
				}
			}
			inew+=capimage.bpc;
			ip+=3;
		}
	}
	//Close block
	if (drcur.y2!=-1){
		ardiff.push_back(drcur);
	}
	//drcurhorizgap=NULL;
	if (ardiff.size()>0){
		while (!ardiff.empty()){
			drcur = ardiff[0];
			int cw=(drcur.x2-drcur.x1)+1;
			int ch=(drcur.y2-drcur.y1)+1;
			int tot=2+1;
			unsigned long jpegSize = 0;
			unsigned char* jpegBuf = NULL;
			int tjcret = tjCompress2(tjInstance, ses.data+((ses.shotw*(drcur.y1*3))+(drcur.x1*3)), cw, ses.shotw*3, ch, TJPF_RGB,&jpegBuf, &jpegSize, TJSAMP_444, ses.jpegQuality, TJFLAG_FASTDCT);
			if (tjcret==0){
				tot+=2+2+jpegSize;
				resizeDiffBufferIfNeed(tot);
				//ADD TYPE TOKEN
				shortToArray(diffBuffer,0,2); //2=TOKEN frame
				//ADD LAST TOKEN
				if (ardiff.size()==1){
					diffBuffer[2]=1;
				}else{
					diffBuffer[2]=0;
				}
				//ADD X Y
				shortToArray(diffBuffer,3,drcur.x1);
				shortToArray(diffBuffer,5,drcur.y1);
				memcpy(diffBuffer+7,jpegBuf,jpegSize);
				tjFree(jpegBuf);
				jpegBuf = NULL;
				cbdiff(tot,diffBuffer);
			}
			ardiff.erase(ardiff.begin());
		}
	}else{
		resizeDiffBufferIfNeed(3);
		//ADD TYPE TOKEN
		shortToArray(diffBuffer,0,2); //2=TOKEN frame
		//ADD LAST TOKEN
		diffBuffer[2]=1;
		cbdiff(3,diffBuffer);
	}
}


void ScreenCapture::differenceFrameTPALETTE(SESSION &ses, CAPTURE_IMAGE &capimage,CallbackDifference cbdiff){
	bool firstdata = false;
	unsigned long sz = (ses.shotw*ses.shoth);
	CAPTURE_RGB rgb;
	if (ses.data == NULL) {
		ses.data = (unsigned char*)malloc((sz*3) * sizeof(unsigned char));
		firstdata = true;
	}

	int indataSize=20480;//+(pcnt*3);
	unsigned char indata[indataSize];
	int CHUNK=16384;
	unsigned char outdata[CHUNK];
	unsigned long minRemaing=((float)sz*5.0)/100.0;
	int splitSize=20480;
	int fy=0;
	int fh=0;
	unsigned long ip=0;
	unsigned long inew=0;
	unsigned long idata=0;
	int cntFrameSend=0;
	int szb=indataSize;
	while(true){
		bool bchanged=false;
		bool bsplit=false;
		int pbf=2+1+2+2+2+2; //TYPE TOKEN + LAST + X + Y + W + H
		//TRANSPARENT FFFF=65535;
		memset(indata, 255, szb);
		szb=0;
		//PALETTE SIZE
		indata[szb]=ses.palette.redsize;
		szb+=1;
		indata[szb]=ses.palette.greensize;
		szb+=1;
		indata[szb]=ses.palette.bluesize;
		szb+=1;

		//ADD FRAME
		int zerr;
		z_stream strm;
		strm.zalloc = Z_NULL;
		strm.zfree  = Z_NULL;
		strm.opaque = Z_NULL;
		//zerr=deflateInit(&strm, Z_DEFAULT_COMPRESSION);
		zerr=deflateInit(&strm, Z_BEST_SPEED);
		//zerr=deflateInit(&strm, Z_NO_COMPRESSION);
		if (zerr != Z_OK){
			return;
		}
		fh=0;
		int szbold=szb;
		for (int y=fy;y<ses.shoth;y++){
			for (int x=0;x<ses.shotw;x++){
				getRGB(capimage, inew, rgb);
				if ((firstdata==true) || (rgb.red!=ses.data[idata]) || (rgb.green!=ses.data[idata+1]) || (rgb.blue!=ses.data[idata+2])){
					ses.data[idata] = rgb.red;
					ses.data[idata+1] = rgb.green;
					ses.data[idata+2] = rgb.blue;
					unsigned short idxcl = getPaletteColorIndexfromRGB(rgb, ses.palette);
					shortToArray(indata,szb,idxcl);
					bchanged=true;
				}
				szb+=2;
				inew+=capimage.bpc;
				idata+=3;
				ip++;
			}
			if (!bchanged){
				szb=szbold;
				fy++;
			}else{
				fh++;
			}

			unsigned long remaing = sz-ip;
			if ((pbf>=splitSize) && (remaing>minRemaing)){
				bsplit=true;
			}
			if ((bchanged) && ((bsplit) || (ip==sz) || (indataSize-szb<ses.shotw*2))){
				int flush=Z_NO_FLUSH;
				if ((bsplit) || (ip==sz)){
					flush=Z_FINISH;
				}
				strm.next_in = (unsigned char *)indata;
				strm.avail_in = szb;
				do {
					strm.avail_out = CHUNK;
					strm.next_out = outdata;
					zerr=deflate(&strm, flush);
					if (zerr == Z_STREAM_ERROR) {
						deflateEnd(&strm);
						return;
					}
					int appsz = CHUNK-strm.avail_out;
					if (appsz>0){
						resizeDiffBufferIfNeed(appsz+pbf);
						memcpy(diffBuffer+pbf,outdata,appsz);
						pbf+=appsz;
					}
				}while (strm.avail_out == 0);
				//TRANSPARENT FFFF=65535
				memset(indata, 255, szb);
				szb=0;
			}
			if (bsplit){
				break;
			}
		}
		deflateEnd(&strm);
		if ((bchanged) || ((!bsplit) && (cntFrameSend>0))){
			//ADD TYPE TOKEN
			shortToArray(diffBuffer,0,2); //2=TOKEN frame
			//ADD LAST TOKEN
			if (!bsplit){
				diffBuffer[2]=1;
			}else{
				diffBuffer[2]=0;
			}
			if (bchanged){
				//ADD X Y W H
				shortToArray(diffBuffer,3,0);
				shortToArray(diffBuffer,5,fy);
				shortToArray(diffBuffer,7,ses.shotw);
				shortToArray(diffBuffer,9,fh);
			}else{
				pbf=3;
			}
			cntFrameSend++;
			cbdiff(pbf,diffBuffer);
		}
		fy=fy+fh;
		if (!bsplit){
			break;
		}
	}
	//printf("ZIP TM:%d\n",tc.getCounter());
}

void ScreenCapture::resizeDiffBufferIfNeed(int needsz){
	bool bresz=false;
	while (needsz>diffBufferSize){
		diffBufferSize+=BUFFER_DIFF_SIZE;
		bresz=true;
	}
	if (bresz){
		diffBuffer = (unsigned char*)realloc(diffBuffer,diffBufferSize*sizeof(unsigned char));
	}
}

void ScreenCapture::monitor(int id, int index){
	map<int,SESSION>::iterator itmap = hmSession.find(id);
	if (itmap==hmSession.end()){
		return;
	}
	SESSION &ses = itmap->second;
	ses.monitor=index;
}

void ScreenCapture::difference(int id, int typeFrame, int quality, CallbackDifference cbdiff){
	dwdbg->print("ScreenCapture::difference#Start");
	map<int,SESSION>::iterator itmap = hmSession.find(id);
	if (itmap==hmSession.end()){
		dwdbg->print("ScreenCapture::difference#IDNOTFOUND");
		return;
	}
	SESSION &ses = itmap->second;

	//SUPPORTED FRAME
	if (ses.monitorCount==-1){
		//TYPE=11 SUPPORTED FRAME -> CNT-S1-S2
		int sz=2+2;
		short cnt=0;
		int p=0;
		p+=shortToArray(diffBuffer,p,11);
		p+=2;
		if(tjInstance != NULL){
			p+=shortToArray(diffBuffer,p,TYPE_FRAME_TJPEG_V1);
			sz+=2;
			cnt++;
		}
		p+=shortToArray(diffBuffer,p,TYPE_FRAME_PALETTE_V1);
		sz+=2;
		cnt++;
		shortToArray(diffBuffer,2,cnt);
		dwdbg->print("ScreenCapture::tokenSupportedFrame");
		cbdiff(sz,diffBuffer);
	}

	//MONITOR
	dwdbg->print("ScreenCapture::getMonitorCount#Start");
	int mc = captureNative.getMonitorCount();
	dwdbg->print("ScreenCapture::getMonitorCount#End");
	if (ses.monitorCount!=mc){
		ses.monitorCount=mc;
		//TYPE=10 MONITOR COUNT -> SZ
		int sz=2+2;
		int p=0;
		p+=shortToArray(diffBuffer,p,10);
		p+=shortToArray(diffBuffer,p,ses.monitorCount);
		dwdbg->print("ScreenCapture::tokenMonitorCount");
		cbdiff(sz,diffBuffer);
	}
	if (mc>0){
		if ((ses.monitor>=0) && (ses.monitor<=mc)) { //< 0 Viene utilizzato per individuare solo i monitor
			//SCREEN CAPTURE
			int dFMs=distanceFrameMsCalculator.calculate(captureNative.getCpuUsage());
			//TYPE=1 -> DISTANCE FRAME MS
			shortToArray(diffBuffer,0,1);
			intToArray(diffBuffer,2,dFMs);
			cbdiff(6,diffBuffer);
			CAPTURE_IMAGE capimg;
			dwdbg->print("ScreenCapture::captureScreen#Start");
			long shotID = captureNative.captureScreen(ses.monitor, dFMs, &capimg);
			dwdbg->print("ScreenCapture::captureScreen#End. shotID:",shotID);
			if (shotID==-1) {
				if (ses.screenLocked == false) {
					ses.screenLocked = true;
					//TYPE=701 -> CAPTURE LOCKED
					int sz=2;
					int p=0;
					p+=shortToArray(diffBuffer,p,701);
					dwdbg->print("ScreenCapture::tokenCaptureLocked");
					cbdiff(sz,diffBuffer);
				}
			}
			if (shotID>0) {
				if (ses.screenLocked == true) {
					ses.screenLocked = false;
					//TYPE=702 -> CAPTURE UNLOCKED
					int sz=2;
					int p=0;
					p+=shortToArray(diffBuffer,p,702);
					dwdbg->print("ScreenCapture::tokenCaptureLocked");
					cbdiff(sz,diffBuffer);
				}
				//PREPARA TOKENS
				if ((capimg.width!=ses.shotw) || (capimg.height!=ses.shoth)){
					ses.shotw = capimg.width;
					ses.shoth = capimg.height;
					ses.shotID=-1;
					if (ses.data!=NULL){
						free(ses.data);
						ses.data=NULL;
					}
					//TYPE=10 RESOLUTION -> 0-W-H
					int sz=2+2+2;
					int p=0;
					p+=shortToArray(diffBuffer,p,0);
					p+=shortToArray(diffBuffer,p,ses.shotw);
					p+=shortToArray(diffBuffer,p,ses.shoth);
					dwdbg->print("ScreenCapture::tokenMonitorCount");
					cbdiff(sz,diffBuffer);
				}

				if (ses.shotID != shotID) {
					ses.shotID = shotID;
					if (ses.typeFrame!=typeFrame){
						ses.typeFrame=typeFrame;
						if (ses.data != NULL) {
							free(ses.data);
							ses.data=NULL;
						}
					}
					if (ses.quality!=quality){
						ses.quality=quality;
						if (ses.data != NULL) {
							free(ses.data);
							ses.data=NULL;
						}
						loadQuality(&ses);
					}
					if (ses.typeFrame==TYPE_FRAME_PALETTE_V1){
						differenceFrameTPALETTE(ses, capimg, cbdiff);
					}else if (ses.typeFrame==TYPE_FRAME_TJPEG_V1){
						if(tjInstance != NULL){
							differenceFrameTJPEG(ses, capimg, cbdiff);
						}
					}
					dwdbg->print("ScreenCapture::prepareTokens");
				}
				//PREPARA CURSORE
				differenceCursor(ses, capimg, cbdiff);
			}
		}
	}
	dwdbg->print("ScreenCapture::difference#End");
}


void ScreenCapture::initSession(int id){
	hmSession[id].shotID=-1;
	hmSession[id].cursorID=-1;
	hmSession[id].cursorVisible=false;
	hmSession[id].cursorx=-1;
	hmSession[id].cursory=-1;
	hmSession[id].cursorw=-1;
	hmSession[id].cursorh=-1;
	hmSession[id].cursoroffsetx=-1;
	hmSession[id].cursoroffsety=-1;
	hmSession[id].cursorCounter.reset();
	hmSession[id].screenLocked=false;
	hmSession[id].quality=-1;
	hmSession[id].typeFrame=-1;

	/*hmSession[id].activeWinID=-1;
	hmSession[id].activeWinX=-1;
	hmSession[id].activeWinY=-1;
	hmSession[id].activeWinW=-1;
	hmSession[id].activeWinH=-1;*/

	hmSession[id].data=NULL;

	hmSession[id].monitorCount=-1;
	hmSession[id].monitor=-1;

}

void ScreenCapture::initialize(int id){
	dwdbg->print("ScreenCapture::initialize#Start");
	if (hmSession.size()==0){
		captureNative.initialize();
	}
	initSession(id);
	dwdbg->print("ScreenCapture::initialize#End");
}

void ScreenCapture::terminate(int id){
	dwdbg->print("ScreenCapture::terminate#Start");
	map<int,SESSION>::iterator itmap = hmSession.find(id);
	if (itmap!=hmSession.end()){
		if (itmap->second.data!=NULL){
			free(itmap->second.data);
			itmap->second.data=NULL;
		}
		/*if (itmap->second.newdata!=NULL){
			free(itmap->second.newdata);
			itmap->second.newdata=NULL;
		}*/
		hmSession.erase(itmap);
	}
	if (hmSession.size()==0){
		captureNative.terminate();
	}
	dwdbg->print("ScreenCapture::terminate#End");
}


void ScreenCapture::inputKeyboard(int id, const char* type, const char* key, bool ctrl, bool alt, bool shift, bool command){
	map<int,SESSION>::iterator itmap = hmSession.find(id);
	if (itmap==hmSession.end()){
		return;
	}
	captureNative.inputKeyboard(type,key,ctrl,alt,shift,command);
	inputsEvent();
}

void ScreenCapture::inputMouse(int id, int x, int y, int button, int wheel, bool ctrl, bool alt, bool shift, bool command){
	map<int,SESSION>::iterator itmap = hmSession.find(id);
	if (itmap==hmSession.end()){
		return;
	}
	SESSION &ses = itmap->second;
	captureNative.inputMouse(ses.monitor, x, y, button, wheel, ctrl, alt, shift,command);
	inputsEvent();
}

wchar_t* ScreenCapture::copyText(int id){
	captureNative.setClipboardText(NULL);
	captureNative.copy();
	inputsEvent();
	return captureNative.getClipboardText();
}

void ScreenCapture::pasteText(int id, wchar_t* str){
	captureNative.setClipboardText(str);
	captureNative.paste();
	inputsEvent();
}


