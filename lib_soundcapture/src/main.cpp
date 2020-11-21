/*
 This Source Code Form is subject to the terms of the Mozilla
 Public License, v. 2.0. If a copy of the MPL was not distributed
 with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
 */

#include "main.h"

int record(void *outputBuffer, void *inputBuffer, unsigned int nBufferFrames,
		double streamTime, rtaudio_stream_status_t status, void *userData) {
	if (status){
		printf("Stream overflow!\n");
	}else if (inputBuffer != NULL){
		//printf("nBufferFrames %d\n",nBufferFrames);
		DWASoundCaptureLock();
		float *rptr = (float*)inputBuffer;
		bool bok=false;
		int oldrbl=ringBufferLimit;
		for( unsigned int i=0; i<nBufferFrames*numChannels; i++ ){
			if( inputBuffer == NULL ){
				ringBuffer[ringBufferLimit]=0.0f;
			}else{
				ringBuffer[ringBufferLimit]=*rptr++;
			}
			if (ringBuffer[ringBufferLimit]!=0.0f){
				bok=true;
			}
			ringBufferLimit++;
			if (ringBufferLimit>=ringBufferSize){
				ringBufferLimit=0;
			}
		}
		if (!bok){
			ringBufferLimit=oldrbl;
		}
		DWASoundCaptureUnlock();
	}
	return 0;
}

int DWASoundCaptureVersion(){
	return 0;
}

void DWASoundCaptureCreateLock(){
#if defined OS_WINDOWS
	mtx=CreateMutex(NULL,FALSE,NULL);
#else
	pthread_mutex_init(&mtx, NULL);
#endif
}

void DWASoundCaptureDestroyLock(){
#if defined OS_WINDOWS
	CloseHandle(mtx);
#else
	pthread_mutex_lock(&mtx);
#endif
}

void DWASoundCaptureLock(){
#if defined OS_WINDOWS
		WaitForSingleObject(mtx, INFINITE);
#else
		pthread_mutex_lock(&mtx);
#endif
}

void DWASoundCaptureUnlock(){
#if defined OS_WINDOWS
		ReleaseMutex(mtx);
#else
		pthread_mutex_unlock(&mtx);
#endif
}

unsigned int DWASoundCaptureGetSampleRate(){
	return sampleRate;
}

unsigned int DWASoundCaptureGetNumChannels(){
	return numChannels;
}

unsigned int DWASoundCaptureGetBufferFrames(){
	return bufferFrames;
}

int DWASoundCaptureGetDetectOutputName(char* bf, int sz){
	rtaudio_device_info_t di = rtaudio_get_device_info(adc,rtaudio_get_default_output_device(adc));
	strncpy(bf,di.name,sz);
	return strlen(di.name);
}

void DWASoundCaptureStart(){
	if (!bStarted){
		DWASoundCaptureCreateLock();
#if defined OS_WINDOWS
		adc = rtaudio_create(RTAUDIO_API_WINDOWS_WASAPI);
#elif defined OS_LINUX
		adc = rtaudio_create(RTAUDIO_API_LINUX_PULSE);
#else
		adc = rtaudio_create(RTAUDIO_API_MACOSX_CORE);
#endif
		bStarted=true;
		DWASoundCaptureDetectOutput();
	}
}

void DWASoundCaptureStop(){
	if (bStarted){
		DWASoundCaptureDestroyStream();
		rtaudio_destroy(adc);
		DWASoundCaptureDestroyLock();
		bStarted=false;
	}
}

void DWASoundCaptureDetectOutput(){
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
				if (iret==0){
					bStreamAlive=true;
				}else{
					bStreamAlive=false;
					ringBufferSize=0;
					bufferFrames=0;
					free(ringBuffer);
				}
			}

		}
	}
}

void DWASoundCaptureDestroyStream(){
	if (bStreamAlive){
		bStreamAlive=false;
		rtaudio_stop_stream(adc);
		if (rtaudio_is_stream_open(adc)==1){
			rtaudio_close_stream(adc);
		}
		free(ringBuffer);
		free(ringBufferApp);
		ringBufferSize=0;
		bufferFrames=0;
	}
}

int shortToArray(unsigned char* buffer,int p,short s){
	buffer[p] = (s >> 8) & 0xFF;
	buffer[p+1] = s & 0xFF;
	return 2;
}

int DWASoundCaptureGetData(int id, unsigned char** data) {
	int iret=0;
	int p=0;
	int cnt=0;
	if (bStarted) {
		DWASoundCaptureLock();
		if (!bStreamAlive){
			DWASoundCaptureUnlock();
			return iret;
		}
		std::map<int,SESSION>::iterator itmap = hmSession.find(id);
		if (itmap==hmSession.end()){
			DWASoundCaptureUnlock();
			return iret;
		}
		SESSION &ses = itmap->second;
		if (ses.ringBufferPos>ringBufferLimit){
			int appcnt=ringBufferSize-ses.ringBufferPos;
			memcpy(ringBufferApp, ringBuffer+ses.ringBufferPos, appcnt*sizeof(float));
			ses.ringBufferPos=0;
			cnt+=appcnt;
		}
		if (ses.ringBufferPos<ringBufferLimit){
			int appcnt=ringBufferLimit-ses.ringBufferPos;
			memcpy(ringBufferApp+cnt, ringBuffer+ses.ringBufferPos, appcnt*sizeof(float));
			ses.ringBufferPos=ringBufferLimit;
			cnt+=appcnt;
		}
		DWASoundCaptureUnlock();
		while (p<cnt){
			int c = opus_encode_float(ses.enc, ringBufferApp+p, bufferFrames, ses.buffer+iret+2, ses.bufferSize-iret-2);
			if (c>0){
				iret += shortToArray(ses.buffer,iret,(short)c);
				iret += c;
			}else{
				//printf("iret %d\n",iret);
			}
			p+=bufferFrames*numChannels;
		}
		*data = ses.buffer;
	}
	return iret;
}

int DWASoundCaptureInit(int id, int enctype, int quality) {
	if (bStarted) {
		int err;
		OpusEncoder* enc = opus_encoder_create(sampleRate, numChannels, OPUS_APPLICATION_RESTRICTED_LOWDELAY, &err);
		if(err != OPUS_OK || enc==NULL){
			printf("opus_encoder_create ERROR!!");
			return 2;
		}
		//opus_encoder_ctl(enc, OPUS_SET_MAX_BANDWIDTH(OPUS_BANDWIDTH_NARROWBAND));
		opus_encoder_ctl(enc, OPUS_SET_BITRATE(OPUS_AUTO)); // OPUS_AUTO
		DWASoundCaptureLock();
		DWASoundCaptureTermNoSync(id);
		hmSession[id].enc=enc;
		hmSession[id].enctype=enctype;
		hmSession[id].quality=quality;
		hmSession[id].ringBufferPos=0;
		hmSession[id].bufferSize=ringBufferSize*sizeof(float)*2;
		hmSession[id].buffer=(unsigned char*)malloc(sizeof(unsigned char)*hmSession[id].bufferSize);
		DWASoundCaptureUnlock();
		return 0;
	}else{
		return 1;
	}

}

void DWASoundCaptureTermNoSync(int id) {
	std::map<int,SESSION>::iterator itmap = hmSession.find(id);
	if (itmap!=hmSession.end()){
		if (itmap->second.buffer!=NULL){
			free(itmap->second.buffer);
			itmap->second.buffer=NULL;
		}
		if (itmap->second.enc!=NULL){
			opus_encoder_destroy(itmap->second.enc);
			itmap->second.enc=NULL;
		}
		hmSession.erase(itmap);
	}
}

void DWASoundCaptureTerm(int id) {
	DWASoundCaptureLock();
	DWASoundCaptureTermNoSync(id);
	DWASoundCaptureUnlock();
}
