/* 
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/

//PROTOCOL ENCODE: TYPE-DATA
// TYPE=2 DATA=L-X-Y-W-H-IMG -> TOKEN FRAME - L=End frame (1:YES 0:NO)
// TYPE=3 DATA=V-X-Y-W-H-OFFX-OFFY-IMG -> TOKEN CURSOR - V=Visible (1:YES 0:NO)
// TYPE=4 DATA=SX-SY-SW-SH-DX-DY -> COPY AREA

#if defined OS_MAIN

#include "main.h"
#include "common/timecounter.h"


#if defined OS_WINDOWS

#define _CRT_SECURE_NO_WARNINGS
#define _WIN32_DCOM
#define WIDTHBYTES(bits)    (((bits) + 31) / 32 * 4)
//#pragma comment(lib,"UserEnv.lib")
//#pragma warning(disable : 4995)

WindowsLoadLib loadLibWin;
OSVERSIONINFOEX m_osVerInfo = { 0 };
//EXTERN_C IMAGE_DOS_HEADER __ImageBase;

#endif

#if defined OS_WINDOWS

void initOSVersionInfo(){
  if (m_osVerInfo.dwOSVersionInfoSize == 0) {
    m_osVerInfo.dwOSVersionInfoSize = sizeof(OSVERSIONINFO);

    if (!GetVersionEx((OSVERSIONINFO*)&m_osVerInfo)) {
      m_osVerInfo.dwOSVersionInfoSize = 0;
    }
  }
}

int isVistaOrLater(){
  initOSVersionInfo();
  if (m_osVerInfo.dwMajorVersion >= 6){
	  return 1;
  }
  return 0;
}

int DWAScreenCaptureSAS(){
	BOOL bret=FALSE;
	if (isVistaOrLater() && loadLibWin.SendSasFunc()) {
		HKEY regkey;
		LSTATUS st = RegOpenKeyEx(HKEY_LOCAL_MACHINE,"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System", 0, KEY_ALL_ACCESS, &regkey);
		if (st==ERROR_SUCCESS){
			DWORD oldvalue=0;
			DWORD size=sizeof(DWORD);
			DWORD dwType=REG_DWORD;
			st = RegQueryValueEx(regkey, "SoftwareSASGeneration", 0, &dwType, (BYTE*)&oldvalue, &size);
			boolean brem=true;
			if (st==ERROR_SUCCESS){
				brem=false;
			}
			if ((brem) || (oldvalue!=1)){
				DWORD value=1;
				st = RegSetValueEx(regkey, "SoftwareSASGeneration",0, REG_DWORD, (const BYTE*)&value, sizeof(value));
				if (st==ERROR_SUCCESS){
					loadLibWin.SendSasFunc()(FALSE);
					bret=TRUE;
					if (!brem){
						st = RegSetValueEx(regkey, "SoftwareSASGeneration",0, REG_DWORD, (const BYTE*)&oldvalue, sizeof(oldvalue));
					}else{
						RegDeleteValue(regkey,"SoftwareSASGeneration");
					}
				}else{
					loadLibWin.SendSasFunc()(FALSE);
					bret=TRUE;
				}
			}else{
				loadLibWin.SendSasFunc()(FALSE);
				bret=TRUE;
			}
			RegCloseKey(regkey);
		}
	}
	if (bret==TRUE){
		return 1;
	}else{
		return 0;
	}
}

#endif


/*
void DWAScreenCaptureRGBImageFree(RGB_IMAGE* rgbimage){
	if (rgbimage->data!=NULL){
		free(rgbimage->data);
		rgbimage->data=NULL;
		rgbimage->width=0;
		rgbimage->height=0;
	}
}
*/

int DWAScreenCaptureVersion(){
	return 4;
}

int DWAScreenCapturePaletteEncoderVersion(){
	z_stream strm;
	strm.zalloc = Z_NULL;
	strm.zfree  = Z_NULL;
	strm.opaque = Z_NULL;
	if (deflateInit(&strm, Z_BEST_SPEED) != Z_OK){
		return 0;
	}
	deflateEnd(&strm);
	return 1;
}


void resizeResultBufferIfNeedPaletteEncoder(PaletteEncoderSessionInfo* es, int needsz){
	bool bresz=false;
	while (needsz>es->resultBufferSize){
		es->resultBufferSize+=RESULT_DIFF_SIZE;
		bresz=true;
	}
	if (bresz){
		es->resultBuffer = (unsigned char*)realloc(es->resultBuffer,es->resultBufferSize*sizeof(unsigned char));
	}
}

short getPaletteColorIndexfromRGB(unsigned char red, unsigned char green, unsigned char blue, PALETTE& palinfo) {
	return (short)(((red >> palinfo.redsf) << (palinfo.greencnt + palinfo.bluecnt)) + ((green >> palinfo.greensf) << palinfo.bluecnt) + (blue >> palinfo.bluesf));
}

int DWAScreenCapturePaletteEncoderInit(int ver, void** encses){
	PaletteEncoderSessionInfo* es = new PaletteEncoderSessionInfo();
	es->resultBufferSize = RESULT_DIFF_SIZE;
	es->resultBuffer = (unsigned char*)calloc(es->resultBufferSize,sizeof(unsigned char));
	es->data=NULL;
	es->width=0;
	es->height=0;
	es->palette.redsize=0;
	es->palette.greensize=0;
	es->palette.bluesize=0;
	*encses = es;
	return 0;
}

void DWAScreenCapturePaletteEncoderTerm(int ver, void* encses){
	PaletteEncoderSessionInfo* es = (PaletteEncoderSessionInfo*)encses;

	free(es->resultBuffer);
	if (es->data!=NULL){
		free(es->data);
	}
	es->data=NULL;
	delete es;
}

unsigned long DWAScreenCapturePaletteEncode(int ver, void* encses, int redsize, int greensize, int bluesize, RGB_IMAGE* rgbimage, CallbackEncodeResult cbresult){
	unsigned long lret=0;
	PaletteEncoderSessionInfo* es = (PaletteEncoderSessionInfo*)encses;
	bool firstdata = false;
	if ((es->data!=NULL) and (es->width!=rgbimage->width or es->height!=rgbimage->height)) {
		free(es->data);
		es->data=NULL;
	}
	if (es->data==NULL){
		es->width=rgbimage->width;
		es->height=rgbimage->height;
		es->data = (unsigned char*)malloc((rgbimage->sizedata) * sizeof(unsigned char));
		firstdata = true;
	}
	//FIX PALETTE
	if (es->palette.redsize!=redsize){
		es->palette.redsize=redsize;
		es->palette.redcnt=countSetBits(redsize);
		es->palette.redsf=countSetBits((int)(255-(redsize-1)));
	}

	if (es->palette.greensize!=greensize){
		es->palette.greensize=greensize;
		es->palette.greencnt=countSetBits(greensize-1);
		es->palette.greensf=countSetBits((int)(255-(greensize-1)));
	}

	if (es->palette.bluesize!=bluesize){
		es->palette.bluesize=bluesize;
		es->palette.bluecnt=countSetBits(bluesize-1);
		es->palette.bluesf=countSetBits((int)(255-(bluesize-1)));
	}
	unsigned long sz = rgbimage->width*rgbimage->height;
	int indataSize=20480;//+(pcnt*3);
	unsigned char indata[indataSize];
	int CHUNK=16384;
	unsigned char outdata[CHUNK];
	unsigned long minRemaing=((float)sz*5.0)/100.0;
	int splitSize=20480;
	int fy=0;
	int fh=0;
	unsigned long ip=0;
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
		indata[szb]=redsize;
		szb+=1;
		indata[szb]=greensize;
		szb+=1;
		indata[szb]=bluesize;
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
			return -1;
		}
		fh=0;
		int szbold=szb;
		//idata=(fy*rgbimage->width*3);
		for (int y=fy;y<es->height;y++){
			for (int x=0;x<es->width;x++){
				if ((firstdata==true) || (es->data[idata]!=rgbimage->data[idata]) || (es->data[idata+1]!=rgbimage->data[idata+1]) || (es->data[idata+2]!=rgbimage->data[idata+2])){
					es->data[idata] = rgbimage->data[idata];
					es->data[idata+1] = rgbimage->data[idata+1];
					es->data[idata+2] = rgbimage->data[idata+2];
					unsigned short idxcl = getPaletteColorIndexfromRGB(es->data[idata],es->data[idata+1],es->data[idata+2], es->palette);
					shortToArray(indata,szb,idxcl);
					bchanged=true;
				}
				szb+=2;
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
			if ((bchanged) && ((bsplit) || (ip==sz) || (indataSize-szb<rgbimage->width*2))){
				int flush=Z_NO_FLUSH;
				if ((bsplit) || (ip==sz)){
					flush=Z_FINISH;
				}
				strm.next_in = (unsigned char *)indata;
				strm.avail_in = szb;
				do{
					strm.avail_out = CHUNK;
					strm.next_out = outdata;
					zerr=deflate(&strm, flush);
					if (zerr == Z_STREAM_ERROR){
						deflateEnd(&strm);
						return -2;
					}
					int appsz = CHUNK-strm.avail_out;
					if (appsz>0){
						resizeResultBufferIfNeedPaletteEncoder(es,appsz+pbf);
						memcpy(es->resultBuffer+pbf,outdata,appsz);
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
			shortToArray(es->resultBuffer,0,2); //2=TOKEN frame
			//ADD LAST TOKEN
			if (!bsplit){
				es->resultBuffer[2]=1;
			}else{
				es->resultBuffer[2]=0;
			}
			if (bchanged){
				//ADD X Y W H
				shortToArray(es->resultBuffer,3,0);
				shortToArray(es->resultBuffer,5,fy);
				shortToArray(es->resultBuffer,7,rgbimage->width);
				shortToArray(es->resultBuffer,9,fh);
			}else{
				pbf=3;
			}
			cntFrameSend++;
			cbresult(pbf,es->resultBuffer);
			lret+=pbf;
		}
		fy=fy+fh;
		if (!bsplit){
			break;
		}

	}
	//printf("ZIP TM:%d\n",tc.getCounter());

	return lret;
}


void resizeResultBufferIfNeedTJPEGEncoder(TJPEGEncoderSessionInfo* es, int needsz){
	bool bresz=false;
	while (needsz>es->resultBufferSize){
		es->resultBufferSize+=RESULT_DIFF_SIZE;
		bresz=true;
	}
	if (bresz){
		es->resultBuffer = (unsigned char*)realloc(es->resultBuffer,es->resultBufferSize*sizeof(unsigned char));
	}
}

int DWAScreenCaptureTJPEGEncoderVersion(){
	tjhandle ic = tjInitCompress();
	if (ic==NULL){
		return 0; //NOT SUPPORTED
	}
	tjDestroy(ic);
	return 2;
}

int DWAScreenCaptureTJPEGEncoderInit(int ver, void** encses){
	tjhandle ic = tjInitCompress();
	if (ic==NULL){
		return 1;
	}
	TJPEGEncoderSessionInfo* es = new TJPEGEncoderSessionInfo();
	es->tjInstance = ic;
	es->resultBufferSize = RESULT_DIFF_SIZE;
	es->resultBuffer = (unsigned char*)calloc(es->resultBufferSize,sizeof(unsigned char));
	es->data=NULL;
	es->width=0;
	es->height=0;
	es->jpegBufSize=0;
	es->jpegBuf=NULL;
	*encses = es;
	return 0;
}

void DWAScreenCaptureTJPEGEncoderTerm(int ver, void* encses){
	TJPEGEncoderSessionInfo* es = (TJPEGEncoderSessionInfo*)encses;

	if (es->jpegBuf!=NULL){
		tjFree(es->jpegBuf);
	}
	es->jpegBuf=NULL;
	if (es->tjInstance != NULL){
		tjDestroy(es->tjInstance);
	}
	es->tjInstance=NULL;
	free(es->resultBuffer);
	if (es->data!=NULL){
		free(es->data);
	}
	es->data=NULL;
	delete es;
}


unsigned long DWAScreenCaptureTJPEGEncode(int ver, void* encses, int jpegQuality, int bufferSendSize, RGB_IMAGE* rgbimage, CallbackEncodeResult cbresult){
	unsigned long lret=0;
	TJPEGEncoderSessionInfo* es = (TJPEGEncoderSessionInfo*)encses;
	int BLOCK_SIZE=64;
	bool firstdata = false;
	if ((es->data!=NULL) and (es->width!=rgbimage->width or es->height!=rgbimage->height)) {
		free(es->data);
		es->data=NULL;
	}
	if (es->data==NULL){
		es->width=rgbimage->width;
		es->height=rgbimage->height;
		es->data = (unsigned char*)malloc((rgbimage->sizedata) * sizeof(unsigned char));
		firstdata = true;
	}

	//detect changes and make blocks
	int rows = (int)(rgbimage->height/BLOCK_SIZE);
	if (rgbimage->height % BLOCK_SIZE != 0){
		rows++;
	}
	int cols = (int)(rgbimage->width/BLOCK_SIZE);
	if (rgbimage->width % BLOCK_SIZE != 0){
		cols++;
	}
	bool matrixchng[rows][cols];
	for (int r=0;r<rows;r++){
		for (int c=0;c<cols;c++){
			matrixchng[r][c]=false;
			unsigned long ip=0;
			int xs=c*BLOCK_SIZE;
			int xe=xs+BLOCK_SIZE;
			if (xe>rgbimage->width){
				xe=rgbimage->width;
			}
			int ys=r*BLOCK_SIZE;
			int ye=ys+BLOCK_SIZE;
			if (ye>rgbimage->height){
				ye=rgbimage->height;
			}
			bool bexit=false;
			for (int y=ys;y<ye;y++){
				ip=(y*rgbimage->width*3)+(xs*3);
				for (int x=xs;x<xe;x++){
					if ((firstdata==true) || (es->data[ip]!=rgbimage->data[ip]) || (es->data[ip+1]!=rgbimage->data[ip+1]) || (es->data[ip+2]!=rgbimage->data[ip+2])){
						matrixchng[r][c]=true;
						bexit=true;
						break;
					}
					if (bexit){
						break;
					}
					ip+=3;
				}
			}
		}
	}
	//STORE FRAME FOR NEXT DIFFERENCE
	memcpy(es->data, rgbimage->data, rgbimage->sizedata);

	//join near blocks
	std::vector<DIFF_RECT>ardiff;
	DIFF_RECT drcur = DIFF_RECT();
	int sr=-1;
	int sc=-1;
	int er=-1;
	int ec=-1;
	long szr=0;
	while (true){
		for (int r=0;r<rows;r++){
			for (int c=0;c<cols;c++){
				if (matrixchng[r][c]==true){
					if (sr==-1){
						sr=r;
						sc=c;
						er=r;
						ec=c;
						szr=BLOCK_SIZE;
					}else{
						ec=c;
						szr+=BLOCK_SIZE;
					}
				}else{
					if (sr!=-1){
						break;
					}
				}
			}
			if (sr!=-1){
				szr=szr*3;
				long szt=szr;
				for (int r=sr+1;r<rows;r++){
					bool bok=true;
					for (int c=sc;c<=ec;c++){
						if (matrixchng[r][c]==false){
							bok=false;
						}
					}
					if (bok==false){
						break;
					}
					er=r;
					szt+=szr*BLOCK_SIZE;
					if (szt>=TJPEG_SPLIT_SIZE){
						break;
					}
				}
				break;
			}
		}
		if (sr!=-1){
			int x1=sc*BLOCK_SIZE;
			int x2=(ec*BLOCK_SIZE)+BLOCK_SIZE;
			if (x2>rgbimage->width){
				x2=rgbimage->width;
			}
			int y1=sr*BLOCK_SIZE;
			int y2=(er*BLOCK_SIZE)+BLOCK_SIZE;
			if (y2>rgbimage->height){
				y2=rgbimage->height;
			}
			drcur = DIFF_RECT();
			drcur.x1=x1;
			drcur.y1=y1;
			drcur.x2=x2-1;
			drcur.y2=y2-1;
			ardiff.push_back(drcur);

			for (int r=sr;r<=er;r++){
				for (int c=sc;c<=ec;c++){
					matrixchng[r][c]=false;
				}
			}
			sr=-1;
			sc=-1;
			er=-1;
			ec=-1;
		}else{
			break;
		}
	}
	if (ardiff.size()>0){
		while (!ardiff.empty()){
			drcur = ardiff[0];
			int cw=(drcur.x2-drcur.x1)+1;
			int ch=(drcur.y2-drcur.y1)+1;
			if (es->jpegBufSize<3*cw*ch){
				if (es->jpegBuf!=NULL){
					tjFree(es->jpegBuf);
					es->jpegBuf=NULL;
				}
				es->jpegBufSize = 3*cw*ch;
				es->jpegBuf = tjAlloc(es->jpegBufSize);
			}
			unsigned long jpegSize = 0;
			int tjcret = tjCompress2(es->tjInstance, rgbimage->data+((rgbimage->width*(drcur.y1*3))+(drcur.x1*3)), cw, rgbimage->width*3, ch, TJPF_RGB,&es->jpegBuf, &jpegSize, TJSAMP_420, jpegQuality, TJFLAG_FASTDCT | TJFLAG_NOREALLOC);
			if (tjcret==0){
				if (ver==1){
					int tot=2+1+2+2+jpegSize;
					resizeResultBufferIfNeedTJPEGEncoder(es,tot);
					//ADD TYPE TOKEN
					shortToArray(es->resultBuffer,0,2); //2=TOKEN frame
					//ADD LAST TOKEN
					if (ardiff.size()==1){
						es->resultBuffer[2]=1;
					}else{
						es->resultBuffer[2]=0;
					}
					//ADD X Y
					shortToArray(es->resultBuffer,3,drcur.x1);
					shortToArray(es->resultBuffer,5,drcur.y1);
					memcpy(es->resultBuffer+7,es->jpegBuf,jpegSize);
					cbresult(tot,es->resultBuffer);
					lret+=tot;
				}else if (ver==2){
					int pos=0;
					int rmn=jpegSize;
					while (rmn>0){
						int cnt=bufferSendSize;
						if (cnt>rmn){
							cnt=rmn;
						}
						rmn-=cnt;
						int tot=2+1;
						if (pos==0){
							tot+=2+2;
						}
						tot+=cnt;
						resizeResultBufferIfNeedTJPEGEncoder(es,tot);
						//ADD TYPE TOKEN
						shortToArray(es->resultBuffer,0,2); //2=TOKEN FRAME
						//ADD LAST/PARTIAL TOKEN
						if (rmn>0){
							es->resultBuffer[2]=0;
						}else{
							if (ardiff.size()==1){
								es->resultBuffer[2]=1;
							}else{
								es->resultBuffer[2]=2;
							}
						}
						//ADD X Y
						if (pos==0){
							shortToArray(es->resultBuffer,3,drcur.x1);
							shortToArray(es->resultBuffer,5,drcur.y1);
							memcpy(es->resultBuffer+7,es->jpegBuf+pos,cnt);
						}else{
							memcpy(es->resultBuffer+3,es->jpegBuf+pos,cnt);
						}
						cbresult(tot,es->resultBuffer);
						lret+=tot;
						pos+=cnt;
					}
				}
			}else{
				printf("tjCompress2 error: %s\n", tjGetErrorStr2(NULL));
				resizeResultBufferIfNeedTJPEGEncoder(es,3);
				//ADD TYPE TOKEN
				shortToArray(es->resultBuffer,0,2); //2=TOKEN frame
				//ADD LAST TOKEN
				es->resultBuffer[2]=1;
				cbresult(3,es->resultBuffer);
				lret+=3;
				return -1;
			}
			ardiff.erase(ardiff.begin());
		}
	}else{
		resizeResultBufferIfNeedTJPEGEncoder(es,3);
		//ADD TYPE TOKEN
		shortToArray(es->resultBuffer,0,2); //2=TOKEN frame
		//ADD LAST TOKEN
		es->resultBuffer[2]=1;
		cbresult(3,es->resultBuffer);
		lret+=3;
	}
	return lret;
}

void resizeResultBufferIfNeedCursor(int needsz){
	bool bresz=false;
	while (needsz>resultBufferCursorSize){
		resultBufferCursorSize+=RESULT_DIFF_SIZE;
		bresz=true;
	}
	if (bresz){
		resultBufferCursor = (unsigned char*)realloc(resultBufferCursor,resultBufferCursorSize*sizeof(unsigned char));
	}
}

unsigned long DWAScreenCaptureCursorEncode(int ver, CURSOR_IMAGE* curimage, CallbackEncodeResult cbresult){
	unsigned long lret=0;
	int pbf=0;
	//ADD TYPE TOKEN
	pbf+=shortToArray(resultBufferCursor,pbf,3); //3=TOKEN cursor
	if (!curimage->visible){
		lret=pbf+1;
		resizeResultBufferIfNeedCursor(lret);
		resultBufferCursor[pbf]=0;
	}else if (curimage->sizedata==0){
		lret=pbf+1+2+2;
		resizeResultBufferIfNeedCursor(lret);
		resultBufferCursor[pbf]=1;
		pbf++;
		pbf+=shortToArray(resultBufferCursor,pbf,curimage->x);
		pbf+=shortToArray(resultBufferCursor,pbf,curimage->y);
	}else{
		lret=pbf+1+2+2+2+2+2+2+2+2+2+2+curimage->sizedata;
		resizeResultBufferIfNeedCursor(lret);
		resultBufferCursor[pbf]=1;
		pbf++;
		pbf+=shortToArray(resultBufferCursor,pbf,curimage->x);
		pbf+=shortToArray(resultBufferCursor,pbf,curimage->y);
		pbf+=shortToArray(resultBufferCursor,pbf,curimage->width);
		pbf+=shortToArray(resultBufferCursor,pbf,curimage->height);
		pbf+=shortToArray(resultBufferCursor,pbf,curimage->offx);
		pbf+=shortToArray(resultBufferCursor,pbf,curimage->offy);
		//IMAGE
		pbf+=shortToArray(resultBufferCursor,pbf,0);
		pbf+=shortToArray(resultBufferCursor,pbf,0);
		pbf+=shortToArray(resultBufferCursor,pbf,curimage->width);
		pbf+=shortToArray(resultBufferCursor,pbf,curimage->height);
		int appcrsz=curimage->width*curimage->height;
		unsigned char indata[(appcrsz*4)];
		int szb=0;
		int i=0;
		for (int ip=0;ip<appcrsz;ip++){
			indata[szb]=curimage->data[i];
			szb++;
			indata[szb]=curimage->data[i+1];
			szb++;
			indata[szb]=curimage->data[i+2];
			szb++;
			indata[szb]=curimage->data[i+3];
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
					memcpy(resultBufferCursor+pbf,outdata,appsz);
					pbf+=appsz;
				}
			}while (strm.avail_out == 0);
			deflateEnd(&strm);
			if (zerr == Z_STREAM_ERROR) {
				return 0;
			}
		}else{
			return 0;
		}
	}
	cbresult(lret,resultBufferCursor);
	return lret;
}



void callbackDifference(int sz, unsigned char* data){
	//printf("LN:%d\n",sz);
}

#if defined OS_WINDOWS
int wmain(int argc, wchar_t **argv) {
#else
	int main(int argc, char **argv) {
#endif

	return 0;
}

#endif
