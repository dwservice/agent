/*
 This Source Code Form is subject to the terms of the Mozilla
 Public License, v. 2.0. If a copy of the MPL was not distributed
 with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
 */

#include "main.h"

int DWASoundCaptureVersion(){
	return 4;
}

int shortToArray(unsigned char* buffer,int p,short s){
	buffer[p] = (s >> 8) & 0xFF;
	buffer[p+1] = s & 0xFF;
	return 2;
}

bool checkzero(unsigned char *s, int l) {
	for(int i = 0; i < l; i++) {
		if(s[i] != 0) return false;
	}
	return true;
}

int record(void *outputBuffer, void *inputBuffer, unsigned int nBufferFrames,
		double streamTime, rtaudio_stream_status_t status, void *userData) {
	AudioCaptureSessionInfo* cs = (AudioCaptureSessionInfo*)userData;
	if (status){
		//printf("Stream overflow!\n");
	}else if (inputBuffer != NULL){
		unsigned char* s = (unsigned char*)inputBuffer;
		unsigned int l = nBufferFrames*cs->conf->numChannels*sizeof(float);
		if (!checkzero(s,l)){
			cs->callbackRecord(l,s);
		}
	}
	return 0;
}

int getCurOutput(rtaudio* adc){
	int dvout=-1;
	#if defined OS_LINUX
		for (unsigned int i=0;i<=deviceCount-1;i++){
			rtaudio_device_info_t di = rtaudio_get_device_info(adc,i);
			if (strcasestr(di.name,"monitor")!=NULL){
				dvout=i;
				break;
			}
		}
	#else
		dvout=rtaudio_get_default_output_device(adc);
	#endif
	return dvout;
}

int DWASoundCaptureStart(AUDIO_CONFIG* audioconf,CallbackRecord cbrec,void** capses){
	AudioCaptureSessionInfo* cs = new AudioCaptureSessionInfo();
	cs->bStreamAlive=false;
	cs->callbackRecord=NULL;

#if defined OS_WINDOWS
	cs->adc = rtaudio_create(RTAUDIO_API_WINDOWS_WASAPI);
#elif defined OS_LINUX
	cs->adc = rtaudio_create(RTAUDIO_API_LINUX_PULSE);
#else
	cs->adc = rtaudio_create(RTAUDIO_API_MACOSX_CORE);
#endif
	if (cs->adc==NULL){
		return -91;
	}
	deviceCount = rtaudio_device_count(cs->adc);
	deviceOut = getCurOutput(cs->adc);
	if (deviceCount==0 || deviceOut>deviceCount-1){
		rtaudio_destroy(cs->adc);
		return -92;
	}else{
		rtaudio_stream_parameters parameters;
		parameters.device_id = deviceOut;
		parameters.num_channels = audioconf->numChannels;
		parameters.first_channel = 0;
		cs->conf=audioconf;
		cs->callbackRecord=cbrec;
		int iret=rtaudio_open_stream(cs->adc, NULL, &parameters, RTAUDIO_FORMAT_FLOAT32, audioconf->sampleRate, &audioconf->bufferFrames, &record, cs, NULL, NULL);
		if (iret==0){
			iret=rtaudio_start_stream(cs->adc);
		}
		if (iret==0){
			*capses = cs;
			return 0;
		}
		return iret;
	}
	return -90;
}

int DWASoundCaptureGetDetectOutputName(void* capses,char* bf, int sz){
	AudioCaptureSessionInfo* cs = (AudioCaptureSessionInfo*)capses;
	int dvcnt = rtaudio_device_count(cs->adc);
	int dvout = getCurOutput(cs->adc);
	if (dvcnt==0 || dvout>dvcnt-1){
		return 0;
	}
	rtaudio_device_info_t di = rtaudio_get_device_info(cs->adc,dvout);
	strncpy(bf,di.name,sz);
	return strlen(di.name);
}

/*void DWASoundCaptureDetectOutput(){
	if (bStarted){
		bool bload=true;
		unsigned int devcnt = 0;
		unsigned int devout = 0;
		bool devread = false;
		if (!bStreamFirst){
			if (bStreamAlive){
				if (rtaudio_is_stream_running(adc)!=1){
					DWASoundCaptureDestroyStream();
				}else{
					devcnt = rtaudio_device_count(adc);
					devout = rtaudio_get_default_output_device(adc);
					devread = true;
					if ((deviceCount!=devcnt) || (deviceOut!=devout)){
						DWASoundCaptureDestroyStream();
					}
				}
				if (bStreamAlive){
					bload=false;
				}
			}else{
				devcnt = rtaudio_device_count(adc);
				devout = rtaudio_get_default_output_device(adc);
				devread = true;
				if ((deviceCount==devcnt) && (deviceOut==devout)){
					bload=false;
				}
			}
		}
		bStreamFirst=false;
		if (bload){
			if (devread){
				deviceCount = devcnt;
				deviceOut = devout;
			}else{
				deviceCount = rtaudio_device_count(adc);
				deviceOut = rtaudio_get_default_output_device(adc);
			}
			if (deviceCount==0 || deviceOut>deviceCount-1){
				bStreamAlive=false;
			}else{
				bufferFrames=(sampleRate*(40.0/1000.0));
				rtaudio_stream_parameters parameters;
				parameters.device_id = deviceOut;
				parameters.num_channels = numChannels;
				parameters.first_channel = 0;
				ringBufferSize = 4*sampleRate; //4 seconds
				ringBufferLimit=0;
				ringBuffer = (float*)malloc(sizeof(float)*ringBufferSize);
				ringBufferApp = (float*)malloc(sizeof(float)*ringBufferSize);
				int iret=rtaudio_open_stream(adc, NULL, &parameters, RTAUDIO_FORMAT_FLOAT32, sampleRate, &bufferFrames, &record, NULL, NULL, NULL);
				//adc.openStream(NULL, &parameters, RTAUDIO_FLOAT32, sampleRate, &bufferFrames, &record, NULL); rtaudio_cb_t
				if (iret==0){
					iret=rtaudio_start_stream(adc);
				}
				bStreamAlive = (iret==0);
			}

		}
	}
}
*/

void DWASoundCaptureStop(void* capses){
	AudioCaptureSessionInfo* cs = (AudioCaptureSessionInfo*)capses;
	rtaudio_stop_stream(cs->adc);
	if (rtaudio_is_stream_open(cs->adc)==1){
		rtaudio_close_stream(cs->adc);
	}
	rtaudio_destroy(cs->adc);
	cs->callbackRecord=NULL;
	cs->adc=NULL;
	delete cs;
}


int DWASoundCaptureOPUSEncoderInit(AUDIO_CONFIG* audioconf,void** encses){
	OPUSEncoderSessionInfo* oe = new OPUSEncoderSessionInfo();
	int err;
	oe->enc = opus_encoder_create(audioconf->sampleRate, audioconf->numChannels, OPUS_APPLICATION_RESTRICTED_LOWDELAY, &err);
	if(err != OPUS_OK || oe->enc==NULL){
		printf("opus_encoder_create ERROR!!");
		delete oe;
		return -2;
	}
	//opus_encoder_ctl(oe->enc, OPUS_SET_MAX_BANDWIDTH(OPUS_BANDWIDTH_NARROWBAND));
	opus_encoder_ctl(oe->enc, OPUS_SET_BITRATE(OPUS_AUTO)); // OPUS_AUTO
	oe->resultBufferSize = RESULT_DIFF_SIZE;
	oe->resultBuffer = (unsigned char*)calloc(oe->resultBufferSize,sizeof(unsigned char));
	oe->conf=audioconf;
	*encses=oe;
	return 0;
}

void DWASoundCaptureOPUSEncoderTerm(void* encses){
	OPUSEncoderSessionInfo* oe = (OPUSEncoderSessionInfo*)encses;
	opus_encoder_destroy(oe->enc);
	free(oe->resultBuffer);
	oe->enc=NULL;
	delete oe;
}

int DWASoundCaptureOPUSEncode(void* encses, unsigned char* rawinput, int sizeinput, CallbackEncodeResult cbresult){
	OPUSEncoderSessionInfo* oe = (OPUSEncoderSessionInfo*)encses;
	float* frawinput=(float*)rawinput;
	int p=0;
	int cnt=(sizeinput/sizeof(float));
	int iret=2;
	while (p<cnt){
		if (oe->resultBufferSize-iret<RESULT_DIFF_SIZE){
			oe->resultBuffer = (unsigned char*)realloc(oe->resultBuffer,oe->resultBufferSize*sizeof(unsigned char));
		}
		int c = opus_encode_float(oe->enc, frawinput+p, oe->conf->bufferFrames, oe->resultBuffer+iret+2, oe->resultBufferSize-iret-2);
		if (c>0){
			iret += shortToArray(oe->resultBuffer,iret,(short)c);
			iret += c;
		}else{
			return c;
		}
		p+=oe->conf->bufferFrames*oe->conf->numChannels;
	}
	shortToArray(oe->resultBuffer,0,810);
	cbresult(iret,oe->resultBuffer);
	return iret;
}


