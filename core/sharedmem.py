
# -*- coding: utf-8 -*-

'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''

import os
import mmap
import struct
import time
import platform
import ctypes
import string
import random
import json
import utils
import threading
import _multiprocessing
import multiprocessing.synchronize
import multiprocessing.forking
import native


'''
STREAM USE 3 FILES MAP:

FILE 0 - Semaphore and State file
    80 bytes: Semaphore handle
    01 bytes: State side 1 (C:Connected X:Close T:Terminate)
    01 bytes: keep alive side 1 (A:Is Alive K:Ok Alive)
    04 bytes: PID side 1
    01 bytes: State side 2 (C:Connected X:Close T:Terminate)
    01 bytes: keep alive side 2 (A:Is Alive K:Ok Alive)
    04 bytes: PID side 2
FILE 1 - Stream file (write for Side 1 and read for Side 2)
    04 bytes: position write side 1
    04 bytes: position read side 2
    ...
FILE 1 - Stream file (write for Side 2 and read for Side 1)
    04 bytes: position write side 2
    04 bytes: position read side 1
    ...
'''

CONDITION_SIZE_BYTE=80
FILE1_SIZE_BYTE=CONDITION_SIZE_BYTE+1+1+4+1+1+4
FILE2_3_SIZE_BYTE=2*1024*1024

SHAREDMEM_PATH="sharedmem"

_sharememmap={}
_sharememmap["semaphore"] = threading.Condition()

def load_semaphore_lib():
    _sharememmap["semaphore"].acquire()
    try:
        if utils.is_windows():
            return True
        else:
            try:
                if "libbase" in _sharememmap:
                    return True
                else:
                    _libbase = native.get_instance().get_library()
                    if _libbase is not None:
                        _libbase.semaphoreCreate.restype=ctypes.c_long
                        _libbase.semaphoreOpen.restype=ctypes.c_long
                        _sharememmap["libbase"]=_libbase
                        _sharememmap["sem_name"]="/dwagentshm"
                        _sharememmap["sem_counter"]=0
                        return True
                    else:
                        return False                
            except:
                return False            
    finally:
        _sharememmap["semaphore"].release()
            



def init_path():
    try:
        if not utils.path_exists(SHAREDMEM_PATH):
            utils.path_makedir(SHAREDMEM_PATH)
        else:
            #Elimina tutti i file
            lst=utils.path_list(SHAREDMEM_PATH);
            for fname in lst:
                try:
                    if fname[0:7]=="stream_":
                        if utils.path_exists(SHAREDMEM_PATH + utils.path_sep + fname):
                            utils.path_remove(SHAREDMEM_PATH + utils.path_sep + fname)
                except:
                    None
    except Exception as e:
        print "sharemem init error: " + str(e)

def create_semlock(obj, cpid, tp, val, imax):
    sid=None
    if utils.is_windows():
        obj._semlock = _multiprocessing.SemLock(tp, val, imax);
        chandle = _multiprocessing.win32.OpenProcess(_multiprocessing.win32.PROCESS_ALL_ACCESS, False, cpid)
        sid = multiprocessing.forking.duplicate(obj._semlock.handle,chandle)        
        multiprocessing.forking.close(chandle)
    else: 
        cnttry=0
        while True:
            _sharememmap["semaphore"].acquire()
            try:
                _sharememmap["sem_counter"]+=1
                sid=_sharememmap["sem_counter"]
            finally:
                _sharememmap["semaphore"].release()
            obj._sem_name=_sharememmap["sem_name"] + str(sid)
            _sharememmap["libbase"].semaphoreUnlink(obj._sem_name)
            obj._sem_t=_sharememmap["libbase"].semaphoreCreate(obj._sem_name, os.O_CREAT | os.O_EXCL, 0o666, val) 
            if obj._sem_t!=-1:
                break
            cnttry+=1
            if cnttry>=100:
                raise Exception("semaphoreOpen failed.")            
        obj._semlock = _multiprocessing.SemLock._rebuild(*(obj._sem_t, tp, imax))
    
    obj._make_methods()
    return (sid,tp,imax)

def connect_semlock(obj, state):
    if utils.is_windows():
        obj._semlock = _multiprocessing.SemLock._rebuild(*state)
    else: 
        obj._sem_name=_sharememmap["sem_name"] + str(state[0])
        obj._sem_t=_sharememmap["libbase"].semaphoreOpen(obj._sem_name, 0)
        obj._semlock = _multiprocessing.SemLock._rebuild(*(obj._sem_t,state[1],state[2]))
    obj._make_methods()
    
def destroy_semlock(obj):
    if obj._semlock is not None:
        try:
            obj._semlock.release()
        except:
            None
        obj._semlock=None
    if utils.is_windows():
        None
    else:
        _sharememmap["libbase"].semaphoreClose(obj._sem_t)
        _sharememmap["libbase"].semaphoreUnlink(obj._sem_name)

class Semaphore(multiprocessing.synchronize.Semaphore):
    
    def __init__(self, value=1):
        None
    
    def create(self, cpid, value=1):
        return create_semlock(self, cpid, multiprocessing.synchronize.SEMAPHORE, value, _multiprocessing.SemLock.SEM_VALUE_MAX)
            
    def connect(self, state):
        connect_semlock(self, state)        
        
    def destroy(self):
        destroy_semlock(self)        
        

class RLock(multiprocessing.synchronize.RLock):
    
    def __init__(self):
        None
    
    def create(self, cpid):
        return create_semlock(self, cpid, multiprocessing.synchronize.RECURSIVE_MUTEX, 1, 1)
            
    def connect(self, state):
        connect_semlock(self, state)
    
    def destroy(self):
        destroy_semlock(self)

class Condition(multiprocessing.synchronize.Condition):
    
    def __init__(self, lock=None):
        if load_semaphore_lib():
            self._dummy=False
        else:    
            self._dummy=True        
    
    def create(self, cpid):
        if self._dummy:
            return ((1, 1, 1),(1, 1, 1), (1, 1, 1), (1, 1, 1))
        else:
            arret = []
            self._lock = RLock()
            arret.append(self._lock.create(cpid))
            self._sleeping_count = Semaphore()
            arret.append(self._sleeping_count.create(cpid,0))
            self._woken_count = Semaphore()
            arret.append(self._woken_count.create(cpid,0))
            self._wait_semaphore = Semaphore()
            arret.append(self._wait_semaphore.create(cpid,0))
            self._make_methods()        
            return arret    
            
    def connect(self, arstate):
        if self._dummy:
            return
        self._lock = RLock()
        self._lock.connect(arstate[0])
        self._sleeping_count = Semaphore()
        self._sleeping_count.connect(arstate[1])
        self._woken_count = Semaphore()
        self._woken_count.connect(arstate[2])
        self._wait_semaphore = Semaphore()
        self._wait_semaphore.connect(arstate[3])
        self._make_methods()
    
    def acquire(self):
        if self._dummy:
            return
        #print "acquire inizio"
        if self._lock is not None:
            multiprocessing.synchronize.Condition.acquire(self)
        #print "acquire fine"
    
    def release(self):
        if self._dummy:
            return
        #print "release inizio"
        if self._lock is not None:
            multiprocessing.synchronize.Condition.release(self)
        #print "release fine"
    
    def wait(self, timeout=None):
        if self._dummy:
            time.sleep(0.005)
        else:
            #print "wait inizio"
            if self._lock is not None:
                multiprocessing.synchronize.Condition.wait(self, timeout)        
            #print "wait fine"
    
    def notify_all(self):
        if self._dummy:
            return
        #print "notify_all inizio"
        if self._lock is not None:
            multiprocessing.synchronize.Condition.notify_all(self)
        #print "notify_all fine"
    
    def destroy(self):        
        if self._dummy:
            return
        if self._wait_semaphore is not None:
            self._wait_semaphore.destroy()
            self._wait_semaphore=None
        if self._woken_count is not None:
            self._woken_count.destroy()
            self._woken_count=None        
        if self._sleeping_count is not None:
            self._sleeping_count.destroy()
            self._sleeping_count=None
        if self._lock is not None:
            self._lock.destroy()
            self._semlock=None   

class Stream():
        
    def __init__(self):
        self._semaphore = threading.Condition()
        self._binit=False
        self._mapfile=None
        self._file_idx_ctrl=0
        self._file_idx_write=1
        self._file_idx_read=2        
        self._locstate = None
        self._othstate = None
        self._buffer_reader = StreamBufferReader(self)
        self._buffer_writer = StreamBufferWriter(self)
    
    def _is_init(self):
        return self._binit
        
    def create(self,fixperm=None):
        self._semaphore.acquire()
        try:
            if self._binit==True:
                raise Exception("Shared file already initialized.")
            self._side=1
            self._mapfile = sharedmem_manager.createStream(fixperm)
            self._size = self._mapfile.get_size()
            self._initialize()
            return self._mapfile.get_name()
        finally:
            self._semaphore.release() 
        
    def connect(self,fname):
        self._semaphore.acquire()
        try:
            if self._binit==True:
                raise Exception("Shared file already initialized.")
            self._side=2
            
            self._mapfile = sharedmem_manager.openStream(fname)
            self._size=self._mapfile.get_size()
            self._initialize()
        finally:
            self._semaphore.release() 
    
    def _update_state(self):
        if self._is_init():
            self._semaphore.acquire()
            try:
                self._mapfile.seek(self._file_idx_ctrl, self._state_pos)
                self._locstate = self._mapfile.read(self._file_idx_ctrl, 1)
                self._mapfile.seek(self._file_idx_ctrl, self._state_other_pos)
                self._othstate = self._mapfile.read(self._file_idx_ctrl, 1)            
            finally:
                self._semaphore.release()            
        
    def _set_other_state(self,v):
        self._semaphore.acquire()
        try:
            self._mapfile.seek(self._file_idx_ctrl, self._state_other_pos)
            self._mapfile.write(self._file_idx_ctrl, v)
        finally:
            self._semaphore.release()

    def _get_local_alive(self):
        self._semaphore.acquire()
        try:
            self._mapfile.seek(self._file_idx_ctrl,self._alive_pos)
            return self._mapfile.read(self._file_idx_ctrl,1)
        finally:
            self._semaphore.release()
    
    def _set_local_alive(self,v):
        self._semaphore.acquire()
        try:
            self._mapfile.seek(self._file_idx_ctrl,self._alive_pos)
            self._mapfile.write(self._file_idx_ctrl,v)
        finally:
            self._semaphore.release()

    def _get_other_alive(self):
        self._semaphore.acquire()
        try:
            self._mapfile.seek(self._file_idx_ctrl,self._alive_other_pos)
            return self._mapfile.read(self._file_idx_ctrl,1)
        finally:
            self._semaphore.release()
            
    def _set_other_alive(self,v):
        self._semaphore.acquire()
        try:
            self._mapfile.seek(self._file_idx_ctrl,self._alive_other_pos)
            self._mapfile.write(self._file_idx_ctrl,v)
        finally:
            self._semaphore.release()            
    
    def _initialize(self):
        try:
            self._binit=True
            self._terminate_time=0
            self._terminate_retry=-1
            #self._side_size=(self._size-CONDITION_SIZE_BYTE)/2
            self._condition_shared=None
            self._condition_shared_pos=0
            if self._side==1:
                self._file_idx_ctrl=0
                self._file_idx_write=1
                self._file_idx_read=2
 
                self._state_pos=CONDITION_SIZE_BYTE+0
                self._alive_pos=CONDITION_SIZE_BYTE+1            
                self._pid_pos=CONDITION_SIZE_BYTE+2                
                self._state_other_pos=CONDITION_SIZE_BYTE+6                        
                self._alive_other_pos=CONDITION_SIZE_BYTE+7            
                self._pid_other_pos=CONDITION_SIZE_BYTE+8                
            elif self._side==2:
                self._file_idx_ctrl=0
                self._file_idx_write=2
                self._file_idx_read=1
                self._state_pos=CONDITION_SIZE_BYTE+6
                self._alive_pos=CONDITION_SIZE_BYTE+7            
                self._pid_pos=CONDITION_SIZE_BYTE+8
                self._state_other_pos=CONDITION_SIZE_BYTE+0                        
                self._alive_other_pos=CONDITION_SIZE_BYTE+1            
                self._pid_other_pos=CONDITION_SIZE_BYTE+2
                
            self._write_pnt_pos=0;
            self._write_data_pos=12;
            self._read_pnt_pos=4;
            self._read_data_pos=12
            self._write_limit=self._size-8
            self._read_limit=self._size-8
            self._last_read_time=long(time.time() * 1000)
            self._last_write_time=long(time.time() * 1000)        
            self._mapfile.seek(self._file_idx_ctrl,0)
            self._mapfile.write(self._file_idx_ctrl,struct.pack("!qiqqiqqiqqiq", -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1))
            if self._side==1:
                self._locstate = "C"
                self._othstate = "W"
                self._mapfile.seek(self._file_idx_ctrl,CONDITION_SIZE_BYTE)
                self._mapfile.write(self._file_idx_ctrl,struct.pack('!ccicci',self._locstate,'K',os.getpid(),self._othstate,'K',-1))            
                self._mapfile.seek(self._file_idx_write,0)
                self._mapfile.write(self._file_idx_write,struct.pack('!ii',0,0))
                self._mapfile.seek(self._file_idx_read,0)
                self._mapfile.write(self._file_idx_read,struct.pack('!ii',0,0))
                self._waitconn_tm=long(time.time() * 1000)                
            elif self._side==2:
                self._locstate = "C"
                self._othstate = "C"
                self._mapfile.seek(self._file_idx_ctrl,CONDITION_SIZE_BYTE+6)            
                self._mapfile.write(self._file_idx_ctrl,struct.pack('!cci',self._locstate,'K',os.getpid()))
        except Exception as ex:
            self._mapfile.close()
            self._mapfile.destroy()
            raise ex
        sharedmem_manager.add(self); 
        
    def _initlock(self):    
        while self._condition_shared is None:
            if self._side==1:
                #LEGGE PID REMOTO PER CREARE LOCK
                self._mapfile.seek(self._file_idx_ctrl,self._pid_other_pos)
                cpid=struct.unpack('!i', self._mapfile.read(self._file_idx_ctrl,4))[0]
                if cpid!=-1:                                                            
                    self._condition_shared=Condition()    
                    lp=self._condition_shared.create(cpid);
                    self._mapfile.seek(self._file_idx_ctrl,self._condition_shared_pos)
                    self._mapfile.write(self._file_idx_ctrl,struct.pack("!qiqqiqqiqqiq", lp[0][0], lp[0][1], lp[0][2], lp[1][0], lp[1][1], lp[1][2], lp[2][0], lp[2][1], lp[2][2], lp[3][0], lp[3][1], lp[3][2]))
                    
            elif self._side==2:
                #LEGGE LOCKID PER CONNETTESI AI LOCK
                if self._condition_shared is None:
                    self._mapfile.seek(self._file_idx_ctrl,self._condition_shared_pos)
                    applp=struct.unpack('!qiqqiqqiqqiq', self._mapfile.read(self._file_idx_ctrl,80))
                    if applp[0]!=-1:
                        lp=[]
                        lp.append((applp[0],applp[1],applp[2]))
                        lp.append((applp[3],applp[4],applp[5]))
                        lp.append((applp[6],applp[7],applp[8]))
                        lp.append((applp[9],applp[10],applp[11]))
                        self._condition_shared=Condition()    
                        self._condition_shared.connect(lp)
                                                    
            time.sleep(0.2)

        
    def _terminate(self):
        if self._binit==True:
            self._binit=False            
            self._terminate_time = long(time.time() * 1000)
            self._terminate_retry=0
            serr=""
            try:
                self._mapfile.seek(self._file_idx_ctrl,self._state_pos)
                self._mapfile.write(self._file_idx_ctrl,'T')
                self._mapfile.close()                
            except Exception as e:
                serr+="Error shared file close: " + str(e) + ";"
            if self._condition_shared is not None:            
                self._condition_shared.destroy()
                
            if (serr!=""):
                raise Exception(serr)
    
    def _destroy_mapfile(self):
        if self._side==1:
            if self._terminate_retry>=0:                
                apptm=long(time.time() * 1000)
                elp=apptm-self._terminate_time
                if elp>2000:
                    try:
                        self._terminate_retry+=1
                        self._mapfile.destroy()
                    except Exception as e:
                        if self._terminate_retry>=5:
                            raise e
                        return False
                    return True
                else:
                    if elp<0:
                        self._terminate_time = long(time.time() * 1000)
                    return False                    
        return True
    
    def _close(self):
        if self._binit==True:
            if self._mapfile is not None:
                self._mapfile.seek(self._file_idx_ctrl,self._state_pos)
                self._mapfile.write(self._file_idx_ctrl,'X')
                
    def close(self):
        self._semaphore.acquire()
        try:
            self._close()
        finally:
            self._semaphore.release()
    
    def is_closed(self):
        self._semaphore.acquire()
        try:
            if self._binit:
                return self._locstate=="X" or self._locstate=="T"
            return True
        finally:
            self._semaphore.release()
    
    def _check_close(self):
        if self._is_init():
            if (self._locstate=="X" or self._locstate=="C") and (self._othstate=="X" or self._othstate=="T"):
                self._terminate()
            else:
                return False            
        return True
    
    def _check_alive(self):
        if self._is_init():
            #Verifica se l'altro lato mi ha chiesto un keep alive
            appalive=self._get_local_alive()
            if appalive=="A":
                self._set_local_alive("K")
            #Verifica se devo richiedere il keep alive all'altro lato
            if self._othstate=="W":
                elapsed=long(time.time() * 1000)-self._waitconn_tm
                if elapsed<0: #Cambiato orario pc
                    self._waitconn_tm=long(time.time() * 1000)
                elif elapsed>=5000:
                    self._terminate()
            elif self._othstate!="T":
                appalive=self._get_other_alive()
                if appalive=="K":
                    self._alive_tm=long(time.time() * 1000)
                    self._set_other_alive("A")
                elif appalive=="A":
                    #Verifica se timeout
                    elapsed=long(time.time() * 1000)-self._alive_tm
                    if elapsed<0: #Cambiato orario pc
                        self._alive_tm=long(time.time() * 1000)
                    elif elapsed>=4000:
                        self._set_other_state("T")
                else:
                    self._set_other_state("T")
                    raise Exception("Invalid other alive (" + str(self._side) + ").")  
    
    def _get_pointer_write(self):
        self._mapfile.seek(self._file_idx_write,0)
        return struct.unpack('!ii', self._mapfile.read(self._file_idx_write,8))
               
    def write(self, data):
        if not self._is_init():
            raise Exception("Shared file closed. (1)");
        self._initlock()
        if self._locstate=="X" or self._othstate=="X" or self._othstate=="T":
            self._close()
            raise Exception("Shared file closed. (2)")
        while self._othstate=="W":
            time.sleep(0.2)
            if not self._is_init():
                raise Exception("Shared file closed. (3)");
            if self._locstate=="X" or self._othstate=="X" or self._othstate=="T":
                self._close()
                raise Exception("Shared file closed. (4)")
        apps=data
        dtpos=0
        towrite=len(apps)                
        while towrite>0:
            #Attende lettura da parte dell'altro side                    
            self._condition_shared.acquire()
            try:
                pw,pr=self._get_pointer_write()
                if not ((pr==pw) or (pr-pw)>1 or (self._write_limit-self._write_data_pos-pw+pr)>1):
                    while True:
                        pr=self._get_pointer_write()[1]                    
                        if (pr==pw) or (pr-pw)>1 or (self._write_limit-self._write_data_pos-pw+pr)>1:
                            break
                        self._condition_shared.wait(0.5)
                        #VERIFICA CHIUSURA
                        if not self._is_init():
                            raise Exception("Shared file closed. (5)");
                        if self._locstate=="X" or self._othstate=="X" or self._othstate=="T":
                            self._close()
                            raise Exception("Shared file closed. (6)")       
            finally:
                self._condition_shared.release()
                
                
            #Cursore write si trova dopo Cursore read
            rpw=self._write_data_pos+pw
            self._mapfile.seek(self._file_idx_write,rpw)
            if pw>=pr: 
                if towrite<self._write_limit-rpw:
                    utils.mmap_write(self._mapfile,self._file_idx_write,apps,dtpos,towrite)
                    pw+=towrite
                    dtpos+=towrite
                    towrite=0
                else:
                    if pr>0:
                        appsz=self._write_limit-rpw
                        utils.mmap_write(self._mapfile,self._file_idx_write,apps,dtpos,appsz)
                        pw=0
                    else:
                        appsz=self._write_limit-rpw-1
                        utils.mmap_write(self._mapfile,self._file_idx_write,apps,dtpos,appsz)
                        pw+=appsz
                    dtpos+=appsz
                    towrite-=appsz
            #Cursore write si trova prima Cursore read
            rpw=self._write_data_pos+pw
            self._mapfile.seek(self._file_idx_write,rpw)
            if pw<pr: 
                if towrite<=pr-pw-1:
                    utils.mmap_write(self._mapfile,self._file_idx_write,apps,dtpos,towrite)
                    pw+=towrite
                    dtpos+=towrite
                    towrite=0
                else:
                    appsz=pr-pw-1
                    utils.mmap_write(self._mapfile,self._file_idx_write,apps,dtpos,appsz)
                    pw=pr-1
                    dtpos+=appsz
                    towrite-=appsz
            
            #NOTIFICA IL CAMBIAMENTO
            self._condition_shared.acquire()
            try:
                self._mapfile.seek(self._file_idx_write,self._write_pnt_pos)
                self._mapfile.write(self._file_idx_write,struct.pack('!i', pw))
                self._condition_shared.notify_all()
            finally:
                self._condition_shared.release()        
                    
    
    
    def _get_pointer_read(self):
        self._mapfile.seek(self._file_idx_read,0)
        return struct.unpack('!ii', self._mapfile.read(self._file_idx_read,8))
    
    def read(self,timeout=0,maxbyte=0): #0 infinite
        dtread=None
        try:
            if not self._is_init():
                return None
            self._initlock()
            tm=long(time.time() * 1000)
            self._condition_shared.acquire()
            try:
                while True:
                    pw,pr=self._get_pointer_read()
                    if pr!=pw:
                        break
    
                    #VERIFICA CHIUSURA
                    if not self._is_init() or self._othstate=="X" or self._othstate=="T":
                        self._close();
                        return None
                    
                    self._condition_shared.wait(0.5)
                    
                    #VERIFICA TIMEOUT
                    elapsed=long(time.time() * 1000)-tm
                    if timeout>0:
                        if elapsed<0: #Cambiato orario pc
                            tm=long(time.time() * 1000)
                        elif elapsed>=timeout:
                            return ""
            finally:
                self._condition_shared.release()
                
            bread=0
            dtread = utils.Bytes()
            if pw<pr:
                bfullread=True
                appsz=self._read_limit-self._read_data_pos-pr;
                if maxbyte>0 and appsz>maxbyte:
                    appsz=maxbyte
                    bfullread=False
                rpr=self._read_data_pos+pr
                self._mapfile.seek(self._file_idx_read,rpr)
                dtread.append_bytes(utils.mmap_read(self._mapfile,self._file_idx_read,appsz))
                if bfullread:
                    pr=0
                else:
                    pr+=appsz
                bread+=appsz                
            if pw>pr:
                if maxbyte==0 or bread<maxbyte:
                    bfullread=True
                    appsz=pw-pr
                    if maxbyte>0 and appsz>maxbyte-bread:
                        appsz=maxbyte-bread
                        bfullread=False
                    rpr=self._read_data_pos+pr
                    self._mapfile.seek(self._file_idx_read,rpr)
                    dtread.append_bytes(utils.mmap_read(self._mapfile,self._file_idx_read,appsz))
                    if bfullread:
                        pr=pw
                    else:
                        pr+=appsz
                
            #NOTIFICA IL CAMBIAMENTO
            self._condition_shared.acquire()
            try:
                self._mapfile.seek(self._file_idx_read,self._read_pnt_pos)
                self._mapfile.write(self._file_idx_read,struct.pack('!i', pr))
                self._condition_shared.notify_all()
            finally:
                self._condition_shared.release()
            
        except Exception as ex:
            if self._othstate=="C":
                raise ex
        return dtread
    
    def get_buffer_writer(self):
        return self._buffer_writer
    
    def get_buffer_reader(self):
        return self._buffer_reader
    
class StreamBufferReader:
    
    def __init__(self, sr):
        self._stream = sr
        self._lock = threading.Lock()
        self._buff = None
        self._timeout_function = None
    
    def set_timeout_function(self,func):
        self._timeout_function = func
    
    def _read_buff(self, timeout=0, maxbyte=0):
        bfret = None
        if self._buff is None:
            self._buff = self._stream.read(timeout)
            if self._buff is not None:
                self._buff_pos=0
                self._buff_rem=len(self._buff)
        
        if self._buff is not None:
            if maxbyte==0:
                bfret = self._buff
                self._buff = None
            elif self._buff=="":
                bfret = self._buff
                self._buff = None
            else:                    
                tb = self._buff
                ps = self._buff_pos
                rd = maxbyte
                if rd>=self._buff_rem:
                    rd=self._buff_rem
                    self._buff = None                
                else:
                    self._buff_pos+=rd            
                    self._buff_rem-=rd            
                bfret = tb.new_buffer(ps, rd)
        return bfret
    
    def _get_fully(self, sz):
        bfl = None
        bflln=0
        while bflln<sz:
            bf=self._read_buff(maxbyte=sz-bflln, timeout=0.5)
            if bf==None:
                return None
            if len(bf)==0:
                if self._timeout_function is not None:
                    if self._timeout_function():
                        raise Exception("Read timeout")
            else:
                if bfl is None:
                    bfl = bf
                else:
                    bfl.append_bytes(bf)
                bflln=len(bfl)
        return bfl
        
    def get_bytes(self):
        self._lock.acquire()
        try:
            bts = self._get_fully(4)
            if bts is None:
                return None
            return self._get_fully(bts.get_int(0))
        finally:
            self._lock.release()
            
    def get_str(self):
        self._lock.acquire()
        try:
            bts = self._get_fully(4)
            if bts is None:
                return None
            bts = self._get_fully(bts.get_int(0))
            return bts.to_str()
        finally:
            self._lock.release()
    
    def get_int(self):
        self._lock.acquire()
        try:
            bts = self._get_fully(4)
            if bts is None:
                return None
            return bts.get_int(0)
        finally:
            self._lock.release()
    
    def get_pack(self, df):
        self._lock.acquire()
        try:
            ar=[]
            for i in range(len(df)):
                s = df[i]
                if s=="int":
                    bts = self._get_fully(4)
                    if bts is None:
                        return None
                    ar.append(bts.get_int(0))
                elif s=="str":
                    bts = self._get_fully(4)
                    if bts is None:
                        return None
                    bts = self._get_fully(bts.get_int(0))
                    ar.append(bts.to_str())            
                elif s=="bytes":
                    bts = self._get_fully(4)
                    if bts is None:
                        return None
                    ar.append(self._get_fully(bts.get_int(0)))
                else:
                    raise Exception("Invalid def.")
            return ar
        finally:
            self._lock.release()        

class StreamBufferWriter:
    
    def __init__(self, sr):
        self._stream = sr
        self._lock = threading.Lock()
        self._autoflush_time = -1
        self._autoflush_size = -1
        self._autoflush_counter = None
        self._autoflush_timer = None
        self._buff=None
    
    def set_autoflush_time(self,tm):
        self._autoflush_time=tm
        if self._autoflush_time>-1:
            self._autoflush_counter = utils.Counter()
        else:
            self._autoflush_counter = None
    
    def set_autoflush_size(self,sz):
        self._autoflush_size=sz
    
    def _add_buffer(self, ar):
        self._lock.acquire()
        try:                                
            for bts in ar:
                if self._buff is None:
                    self._buff=bts
                else:
                    self._buff.append_bytes(bts)
            if self._autoflush_size>-1 and len(self._buff)>=self._autoflush_size:
                self._flush()
            elif self._autoflush_time>-1 and self._autoflush_counter.is_elapsed(self._autoflush_time):
                self._flush()
            elif self._autoflush_time>0 and self._autoflush_timer is None:
                self._autoflush_timer = threading.Timer(self._autoflush_time, self._check_flush)
                self._autoflush_timer.start()
        finally:
            self._lock.release()
    
    def _check_flush(self):
        self._lock.acquire()
        try:
            self._autoflush_timer=None
            self._flush()
        finally:
            self._lock.release()
        
    def _flush(self):
        if self._buff is not None:
            self._stream.write(self._buff)
            self._buff=None
            if self._autoflush_time>-1:
                self._autoflush_counter.reset()
                if self._autoflush_timer is not None:
                    self._autoflush_timer.cancel()
                    self._autoflush_timer=None                
    
    def flush(self):
        self._lock.acquire()
        try:
            self._flush()
        finally:
            self._lock.release()
    
    def add_int(self, i):
        self._add_buffer([utils.Bytes(utils._struct_I.pack(i))]);
    
    def add_bytes(self, bts):
        self._add_buffer([utils.Bytes(utils._struct_I.pack(len(bts))), bts])
    
    def add_str(self, s):
        bts=utils.Bytes()
        bts.append_str(s)
        self._add_buffer([utils.Bytes(utils._struct_I.pack(len(bts))), bts])
    
    def add_pack(self,df,lst):
        ar=[]
        for i in range(len(df)):
            s = df[i]
            o = lst[i]
            if s=="int":
                ar.append(utils.Bytes(utils._struct_I.pack(o)))
            elif s=="str":
                bts=utils.Bytes()
                bts.append_str(o)
                ar.append(utils.Bytes(utils._struct_I.pack(len(bts))))
                ar.append(bts)            
            elif s=="bytes":
                ar.append(utils.Bytes(utils._struct_I.pack(len(o))))
                ar.append(o)
            else:
                raise Exception("Invalid def.")
        self._add_buffer(ar)
        
      
class Property():
    
    def __init__(self):
        self._semaphore = threading.Condition()
        self._binit=False
    
    def create(self, fname, fieldsdef, fixperm=None):
        self._semaphore.acquire()
        try:
            if self._binit:
                raise Exception("Already initialized.")
            self._path = sharedmem_manager.getPath(fname)
            if utils.path_exists(self._path):
                if fixperm is not None:
                    fixperm(self._path)
                self.open(fname)
                #Verifica se la struttura è identica
                bok=True
                for f in fieldsdef:
                    if f["name"] in self._fields:
                        if f["size"]!=self._fields[f["name"]]["size"]:
                            bok=False
                            break
                    else:
                        bok=False
                        break
                if not bok:
                    self.close()
                    #Prova a rimuovere il file
                    try:
                        utils.path_remove(self._path)
                    except:
                        raise Exception("Shared file is locked.")
                else:
                    self._binit=True
                    return
            #CREAZIONE DEL FILE
            self._fields={}
            szdata=0
            for f in fieldsdef:
                self._fields[f["name"]]={"pos":szdata,"size":f["size"]}
                szdata+=f["size"]
            shead=json.dumps(self._fields)
            self._len_def=len(shead)
            self._size=4+self._len_def+szdata
            with utils.file_open(self._path, "wb") as f:
                f.write(" "*self._size)
            if fixperm is not None:
                fixperm(self._path)
            self._file=utils.file_open(self._path, "r+b")
            self._mmap = mmap.mmap(self._file.fileno(), 0)
            self._mmap.seek(0)
            self._mmap.write(struct.pack('!i', self._len_def))
            self._mmap.write(shead)
            self._binit=True
        finally:
            self._semaphore.release()
    
    def exists(self, fname, bpath=None):
        return utils.path_exists(sharedmem_manager.getPath(fname, path=bpath))
    
    def open(self, fname, bpath=None):
        self._semaphore.acquire()
        try:
            if self._binit:
                raise Exception("Already initialized.")
            self._path = sharedmem_manager.getPath(fname, path=bpath)
            if not utils.path_exists(self._path):
                raise Exception("Shared file not found")
            self._file=utils.file_open(self._path, "r+b")
            self._mmap = mmap.mmap(self._file.fileno(), 0)
            self._mmap.seek(0)
            #Legge struttura
            self._len_def=struct.unpack('!i',self._mmap.read(4))[0]
            shead=self._mmap.read(self._len_def)
            self._fields = json.loads(shead)
            self._binit=True
        finally:
            self._semaphore.release()
    
    def close(self):
        self._semaphore.acquire()
        try:
            if self._binit:
                self._binit=False
                self._fields=None
                err=""
                try:
                    self._mmap.close()
                except Exception as e:
                    err+="Error map close:" + str(e) + "; "
                try:
                    self._file.close()
                except Exception as e:
                    err+="Error shared file close:" + str(e) + ";"
                if (err!=""):
                    raise Exception(err)
        finally:
            self._semaphore.release()
    
    def is_close(self):
        self._semaphore.acquire()
        try:
            return not self._binit;
        finally:
            self._semaphore.release()
    
    def set_property(self, name, val):
        self._semaphore.acquire()
        try:
            if self._binit:
                if name in self._fields:
                    f=self._fields[name];
                    if len(val)<=f["size"]:
                        self._mmap.seek(4+self._len_def+f["pos"])
                        appv=val + " "*(f["size"]-len(val))
                        self._mmap.write(appv)
                    else:
                        raise Exception("Invalid size for property " + name + ".")
                else:
                    raise Exception("Property " + name + " not found.")
            else:
                raise Exception("Not initialized.")
        finally:
            self._semaphore.release()
    
    def get_property(self, name):
        self._semaphore.acquire()
        try:
            if self._binit:
                if name in self._fields:
                    f=self._fields[name];
                    self._mmap.seek(4+self._len_def+f["pos"])
                    sret = self._mmap.read(f["size"])
                    return sret.strip() 
                else:
                    raise Exception("Property " + name + " not found.")
            else:
                raise Exception("Not initialized.")
        finally:
            self._semaphore.release()
        


class MapFile():
    _memlistname=[]
    
    def __init__(self):
        self._mmap=[None,None,None]
        self.bcreate=False
        self.bdestroy=True
        
    def _rndseq(self, cnt):
        ar=[]
        for x in range(cnt):
            if x==0:
                ar.append(random.choice(string.ascii_lowercase))
            else:
                ar.append(random.choice(string.ascii_lowercase + string.digits))            
        return ''.join(ar)
        
    def _new_mem_name(self):
        while True:
            nm = "dwastr" + self._rndseq(20)
            if nm not in MapFile._memlistname:
                MapFile._memlistname.append(nm)
                return nm
                break
    
    def _create_mem(self, fixperm):
        if not utils.is_windows():
            if load_semaphore_lib():
                cnt=5
                while True:
                    self.fname = self._new_mem_name()
                    self.fd1 = _sharememmap["libbase"].sharedMemoryOpen(self.fname + "_1", os.O_CREAT | os.O_EXCL , 0o666)                                        
                    self.fd2 = _sharememmap["libbase"].sharedMemoryOpen(self.fname + "_2", os.O_CREAT | os.O_EXCL , 0o666)
                    self.fd3 = _sharememmap["libbase"].sharedMemoryOpen(self.fname + "_3", os.O_CREAT | os.O_EXCL , 0o666)
                    if self.fd1!=-1 and self.fd2!=-1 and self.fd3!=-1:
                        self.ftype="M"
                        try:
                            #State file
                            os.ftruncate(self.fd1,FILE1_SIZE_BYTE)
                            stats=os.fstat(self.fd1)
                            if stats.st_size!=FILE1_SIZE_BYTE:
                                raise Exception("Invalid stat size.")
                            
                            os.ftruncate(self.fd2,FILE2_3_SIZE_BYTE)
                            stats=os.fstat(self.fd2)
                            if stats.st_size!=FILE2_3_SIZE_BYTE:
                                raise Exception("Invalid stat size.")
                            
                            os.ftruncate(self.fd3,FILE2_3_SIZE_BYTE)
                            stats=os.fstat(self.fd3)
                            if stats.st_size!=FILE2_3_SIZE_BYTE:
                                raise Exception("Invalid stat size.")
                            self._prepare_map()
                            self.bdestroy=False
                            return                
                            #print "create fd: " + str(self.fd) + " " + self.fname                
                        except Exception as ex:
                            if self.fd1!=-1:
                                os.close(self.fd1)
                                _sharememmap["libbase"].sharedMemoryUnlink(self.fname + "_1")
                            if self.fd1!=-2:
                                os.close(self.fd2)
                                _sharememmap["libbase"].sharedMemoryUnlink(self.fname + "_2")
                            if self.fd1!=-3:
                                os.close(self.fd3)
                                _sharememmap["libbase"].sharedMemoryUnlink(self.fname + "_3")
                            MapFile._memlistname.remove(self.fname)
                            raise ex
                    else:     
                        MapFile._memlistname.remove(self.fname)               
                        cnt-=1
                        if cnt==0:
                            raise Exception("Invalid fd.")
                        else:
                            time.sleep(0.2)
            else:
                raise Exception("Library not loaded.")
        else:   
            self.fname = self._new_mem_name()
            self.ftype="M"
            self._prepare_map()
            self.bdestroy=False
            
    def _create_disk(self, fixperm):
        while True:
            self.fname = "stream_" + self._rndseq(8)
            self.fpath1=SHAREDMEM_PATH + utils.path_sep + self.fname + "_1.shm"
            self.fpath2=SHAREDMEM_PATH + utils.path_sep + self.fname + "_2.shm"
            self.fpath3=SHAREDMEM_PATH + utils.path_sep + self.fname + "_3.shm"
            if not utils.path_exists(self.fpath1) and not utils.path_exists(self.fpath2) and not utils.path_exists(self.fpath3):
                with utils.file_open(self.fpath1, "wb") as f:
                    f.write(" "*FILE1_SIZE_BYTE)
                with utils.file_open(self.fpath2, "wb") as f:
                    f.write(" "*FILE2_3_SIZE_BYTE)
                with utils.file_open(self.fpath3, "wb") as f:
                    f.write(" "*FILE2_3_SIZE_BYTE)
                if fixperm is not None:
                    fixperm(self.fpath1)
                    fixperm(self.fpath2)
                    fixperm(self.fpath3)
                self.file1=utils.file_open(self.fpath1, "r+b")
                self.file2=utils.file_open(self.fpath2, "r+b")
                self.file3=utils.file_open(self.fpath3, "r+b")
                self.ftype="F"
                self._prepare_map()
                self.bdestroy=False                
                break
    
    def create(self,fixperm):
        try:
            self._create_mem(fixperm)
        except:
            self._create_disk(fixperm)
        self.bcreate=True 
              
        
    def open(self, name):
        self.ftype=name[0]
        self.fname=name[1:]        
        if self.ftype=="F":
            self.fpath1=sharedmem_manager.getPath(self.fname + "_1")
            self.fpath2=sharedmem_manager.getPath(self.fname + "_2")
            self.fpath3=sharedmem_manager.getPath(self.fname + "_3")
            if not utils.path_exists(self.fpath1) and not utils.path_exists(self.fpath2) and not utils.path_exists(self.fpath3):
                raise Exception("Shared file not found.")
            self.file1=utils.file_open(self.fpath1, "r+b")           
            self.file2=utils.file_open(self.fpath2, "r+b")
            self.file3=utils.file_open(self.fpath3, "r+b")
        elif self.ftype=="M":
            if not utils.is_windows():
                if load_semaphore_lib():
                    self.fd1 = _sharememmap["libbase"].sharedMemoryOpen(self.fname + "_1", 0, 0o666)                                        
                    self.fd2 = _sharememmap["libbase"].sharedMemoryOpen(self.fname + "_2", 0, 0o666)
                    self.fd3 = _sharememmap["libbase"].sharedMemoryOpen(self.fname + "_3", 0, 0o666)
                    if self.fd1!=-1 and self.fd2!=-1 and self.fd3!=-1:
                        #print "open fd: " + str(self.fd) + " " + self.fname
                        stats=os.fstat(self.fd1)
                        if stats.st_size!=FILE1_SIZE_BYTE:
                            raise Exception("Invalid map size.")                
                        stats=os.fstat(self.fd2)
                        if stats.st_size!=FILE2_3_SIZE_BYTE:
                            raise Exception("Invalid map size.")
                        stats=os.fstat(self.fd3)
                        if stats.st_size!=FILE2_3_SIZE_BYTE:
                            raise Exception("Invalid map size.")
                    else:
                        raise Exception("Invalid fd.")
                else:
                    raise Exception("Library not loaded.")            
        self._prepare_map()                
    
    def _prepare_map(self):
        try:
            if self.ftype=="F":
                self._mmap[0]=mmap.mmap(self.file1.fileno(), 0)
                self._mmap[1]=mmap.mmap(self.file2.fileno(), 0)
                self._mmap[2]=mmap.mmap(self.file3.fileno(), 0)
            elif self.ftype=="M":
                if not utils.is_windows():
                    self._mmap[0]=mmap.mmap(self.fd1, FILE1_SIZE_BYTE)
                    self._mmap[1]=mmap.mmap(self.fd2, FILE2_3_SIZE_BYTE)
                    self._mmap[2]=mmap.mmap(self.fd3, FILE2_3_SIZE_BYTE)
                else:
                    try:
                        self._mmap[0]=mmap.mmap(0, FILE1_SIZE_BYTE, "Global\\" + self.fname + "_1")
                        self._mmap[1]=mmap.mmap(0, FILE2_3_SIZE_BYTE, "Global\\" + self.fname + "_2")
                        self._mmap[2]=mmap.mmap(0, FILE2_3_SIZE_BYTE, "Global\\" + self.fname + "_3")
                    except Exception as e:
                        if self._mmap[0] is None:
                            self._mmap[0]=mmap.mmap(0, FILE1_SIZE_BYTE, "Local\\" + self.fname + "_1")
                            self._mmap[1]=mmap.mmap(0, FILE2_3_SIZE_BYTE, "Local\\" + self.fname + "_2")
                            self._mmap[2]=mmap.mmap(0, FILE2_3_SIZE_BYTE, "Local\\" + self.fname + "_3")
                        else:
                            raise e
        except Exception as ex:
            try:
                self.close()
            except:
                None
            raise ex
    
    def seek(self, i , p):
        try:
            self._mmap[i].seek(p)
        except:
            raise Exception("Shared memory file closed.")
    
    def write(self, i, dt):
        try:
            self._mmap[i].write(dt)
        except:
            raise Exception("Shared memory file closed.")
        
    def read(self, i, sz):
        try:
            return self._mmap[i].read(sz)
        except:
            raise Exception("Shared memory file closed.")
    
    def close(self):
        serr=""
        try:
            if self._mmap[0] is not None:
                self._mmap[0].close()
                self._mmap[0] = None            
            if self._mmap[1] is not None:
                self._mmap[1].close()
                self._mmap[1] = None
            if self._mmap[2] is not None:
                self._mmap[2].close()
                self._mmap[2] = None
        except Exception as e:
            serr+="Error map close: " + str(e) + "; ";
        
        if self.ftype=="F":
            if self.file1 is not None:
                self.file1.close()
                self.file1=None
            if self.file2 is not None:
                self.file2.close()
                self.file2=None
            if self.file3 is not None:
                self.file3.close()
                self.file3=None
        elif self.ftype=="M":
            if not utils.is_windows():
                if self.fd1 is not None:
                    os.close(self.fd1)
                    self.fd1=None
                if self.fd2 is not None:
                    os.close(self.fd2)
                    self.fd2=None
                if self.fd3 is not None:
                    os.close(self.fd3)
                    self.fd3=None
        if serr!="":
            raise Exception(serr)
    
    def destroy(self):        
        if not self.bdestroy:
            self.bdestroy=True
            if self.bcreate:
                if self.ftype=="F":
                    if utils.path_exists(self.fpath1):
                        utils.path_remove(self.fpath1)            
                    if utils.path_exists(self.fpath2):
                        utils.path_remove(self.fpath2)
                    if utils.path_exists(self.fpath3):
                        utils.path_remove(self.fpath3)
                elif self.ftype=="M":
                    if not utils.is_windows():
                        iret1 = _sharememmap["libbase"].sharedMemoryUnlink(self.fname + "_1")
                        iret2 = _sharememmap["libbase"].sharedMemoryUnlink(self.fname + "_2")
                        iret3 = _sharememmap["libbase"].sharedMemoryUnlink(self.fname + "_3")
                        if iret1!=0 or iret2!=0 or iret3!=0:                    
                            raise Exception("sharedMemoryUnlink fail")
                    else:
                        MapFile._memlistname.remove(self.fname)
                    
    def get_name(self):
        return self.ftype + self.fname
    
    def get_size(self):
        return FILE2_3_SIZE_BYTE
    

class Manager(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self,name="SharedMemManager")
        self.daemon=True
        
        
        self._semaphore = threading.Condition()
        self._list=[]
    
    def add(self,sm):
        self._semaphore.acquire()
        try:
            self._list.append(sm)
        finally:
            self._semaphore.release()
    
    def createStream(self,fixperm):
        s = MapFile()
        s.create(fixperm)
        return s
    
    def openStream(self, fname):
        s = MapFile()
        s.open(fname)
        return s        
    
    def getPath(self,name,path=None):
        if path is None:
            return SHAREDMEM_PATH + utils.path_sep + name + ".shm"
        else:
            return path + utils.path_sep + SHAREDMEM_PATH + utils.path_sep + name + ".shm"
    
    
    def run(self):
        remfile=[]
        try:
            while True:
                time.sleep(0.5)
                self._semaphore.acquire()
                try:
                    remlist=[]
                    for sm in self._list:
                        try:
                            sm._update_state()
                        except Exception as e:
                            print("SharedMem manager update state error: " + str(e))
                        try:
                            sm._check_alive()
                        except Exception as e:
                            print("SharedMem manager check alive error: " + str(e))
                        try:
                            #Verifica se e chiuso
                            if sm._check_close():
                                remlist.append(sm)
                        except Exception as e:
                            print("SharedMem manager check close error: " + str(e))
                    #RIMUOVE
                    try:
                        for sm in remlist:
                            self._list.remove(sm)
                            remfile.append(sm);
                    except Exception as e:
                        print("SharedMem remove list: " + str(e))
                    newremfile = []
                    for sm in remfile:
                        try:
                            if not sm._destroy_mapfile():
                                newremfile.append(sm)
                        except Exception as e:
                            print("SharedMem manager destroy file error: " + str(e))
                    remfile=newremfile
                finally:
                    self._semaphore.release()
        except:
            None #A volte allo shutdown (most likely raised during interpreter shutdown) errore: <type 'exceptions.TypeError'>: 'NoneType' object is not callable 
        
sharedmem_manager=Manager()
sharedmem_manager.start()


######################
######## TEST ########
######################
class TestThread(threading.Thread):
    
    def __init__(self,fname=None):
        threading.Thread.__init__(self)
        self._fname=fname
          
    def run(self):
        num=100000
        m1 = Stream()
        fname=None
        if self._fname==None:
            fname=m1.create()
        else:
            m1.connect(self._fname)
        if self._fname==None:
            t2 = TestThread(fname)
            t2.start()
            time.sleep(1)
            
            bfwr = m1.get_buffer_writer()
            
            print "START WRITE"
            tm=utils.get_time()
            try:
                bfwr.set_autoflush_time(0.1)
                #bfwr.set_autoflush_size(50000)
                for i in range(num):
                    #bfwr.add_bytes(utils.Bytes("TEST" + str(i+1)))
                    bfwr.add_str("TEST" + str(i+1))
                
                #bfwr.flush()                
                
            except Exception as e:
                print("Errore write remote closed: " + str(e))
            print("WRITE TIME:" + str(utils.get_time()-tm))
            print "END WRITE"
            t2.join()
            m1.close()
        else:
            
            print "WAIT READ..."
            time.sleep(0.1)
            
            print "START READ"
            bfrd = m1.get_buffer_reader()
            cnt=0
            tm=utils.get_time()
            ar=[]            
            while True:
                #dt=bfrd.get_bytes()
                dt=bfrd.get_str()
                                
                if dt is None:
                    #time.sleep(8);
                    raise Exception("Error read remote closed") 
                ar.append(dt)
                #print(s)
                #if s[len(s)-3:]=="END":
                #    break
                cnt+=1
                #print(str(cnt))
                if num==cnt:
                    break
            #print("***************")
            print("READ TIME:" + str(utils.get_time()-tm))
            print "END READ"
            
            if True:
                print("READ CHECK...")
                bok=True
                for i in range(num):
                    #s=ar[i].to_str("ascii")
                    s=ar[i]
                    if s!="TEST" + str(i+1):
                        bok=False
                        print ("ERRORE: '" + s + "' != 'PROVA" + str(i+1) + "'")
                if bok:
                    print "READ CHECK OK"        
            else:
                print "NO READ CHECK"
                
            m1.close()
            print "REMOVING FILE..."
            time.sleep(8);
            print "TO CHECK!"
            


if __name__ == "__main__":
    init_path()
    
    
    '''t1 = Property()
    fieldsdef=[]
    fieldsdef.append({"name":"status","size":1})
    fieldsdef.append({"name":"counter","size":10})
    fieldsdef.append({"name":"prova","size":5})
    t1.create("prova", fieldsdef)
    t1.set_property("status", "2")
    t1.set_property("counter", "0123456789")
    t1.set_property("counter", "012345")
    t1.close()
    
    t2 = Property()
    t2.open("prova")
    print t2.get_property("status")
    print t2.get_property("counter")
    t2.close()'''
    
    t1 = TestThread()
    t1.start()
    
    '''
    m1 = Stream()
    m2 = Stream()
    
    fname=m1.create()
    m2.connect(fname)
    
    
    m2.write_token("TOKEN123")
    m2.write_token("TOKEN999")
    m2.write_token("CIAO")
    m2.write_token("PIPPO")
    
    print(m1.read_token())
    print(m1.read_token())
    print(m1.read_token())
    print(m1.read_token())
    
    m1.close()
    m2.close()
    time.sleep(6)
    '''
    
        
   

    
    
        
        
        
            
            