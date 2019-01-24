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

#Il file di n KB e diviso in 2 parti
# SIDE 1 scrive sulla parte 1 e legge sulla parte 2
# SIDE 2 scrive sulla parte 2 e legge sulla parte 1
#
#
#
# 80 byte condition handle
# SIDE 1 parte da 0
# 1 byte stato= C:Connesso X:Chiuso T:Terminato
# 1 byte keepalive= A:Is Alive K:Ok Aliva
# 4 byte pid
# 4 byte identificano posizione write side 1    
# 4 byte identificano posizione read side 2
# SIDE 2 parte da pos n/2
# 1 byte stato= C:Connesso W:Attesa connessione X:Chiuso T:Terminato
# 1 byte keepalive= A:Is Alive K:Ok Aliva
# 4 byte pid
# 4 byte identificano posizione write side 2    
# 4 byte identificano posizione read side 1
#
# SIDE 1 CREA IL FILE


CONDITION_SIZE_BYTE=80
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
            obj._sem_t=_sharememmap["libbase"].semaphoreCreate(obj._sem_name, val) 
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
        obj._sem_t=_sharememmap["libbase"].semaphoreOpen(obj._sem_name)
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
        self._mmap=None
    
    def _is_init(self):
        return self._binit
        
    def create(self,size=2*512*1024,fixperm=None):
        self._semaphore.acquire()
        try:
            if self._binit==True:
                raise Exception("Shared file already initialized.")
            self._side=1
            self._size=size
            fname = sharedmem_manager.getStreamFile(self._size)
            self._path=sharedmem_manager.getPath(fname)
            if fixperm is not None:
                fixperm(self._path)
            self._initialize()
            return fname
        finally:
            self._semaphore.release() 
        
    def connect(self,fname):
        self._semaphore.acquire()
        try:
            if self._binit==True:
                raise Exception("Shared file already initialized.")
            self._side=2
            self._path=sharedmem_manager.getPath(fname)
            if not utils.path_exists(self._path):
                raise Exception("Shared file not found.")
            self._size=utils.path_size(self._path)
            self._initialize()
        finally:
            self._semaphore.release() 
    
    def _get_state(self):
        self._semaphore.acquire()
        try:
            self._mmap.seek(self._state_pos)
            locstate = self._mmap.read(1)
            self._mmap.seek(self._state_other_pos)
            othstate = self._mmap.read(1)
            return (locstate,othstate)
        finally:
            self._semaphore.release()            

    
    def _set_other_state(self,v):
        self._semaphore.acquire()
        try:
            self._mmap.seek(self._state_other_pos)
            self._mmap.write(v)
        finally:
            self._semaphore.release()

    def _get_local_alive(self):
        self._semaphore.acquire()
        try:
            self._mmap.seek(self._alive_pos)
            return self._mmap.read(1)
        finally:
            self._semaphore.release()
    
    def _set_local_alive(self,v):
        self._semaphore.acquire()
        try:
            self._mmap.seek(self._alive_pos)
            self._mmap.write(v)
        finally:
            self._semaphore.release()

    def _get_other_alive(self):
        self._semaphore.acquire()
        try:
            self._mmap.seek(self._alive_other_pos)
            return self._mmap.read(1)
        finally:
            self._semaphore.release()
            
    def _set_other_alive(self,v):
        self._semaphore.acquire()
        try:
            self._mmap.seek(self._alive_other_pos)
            self._mmap.write(v)
        finally:
            self._semaphore.release()            
    
    def _get_pointer(self,pos):
        self._semaphore.acquire()
        try:
            self._mmap.seek(pos)
            return struct.unpack('!i', self._mmap.read(4))[0]
        finally:
            self._semaphore.release()
        
    def _initialize(self):
        self._binit=True
        self._terminate_time=0
        self._terminate_retry=-1
        self._side_size=(self._size-CONDITION_SIZE_BYTE)/2
        self._condition_shared=None
        self._condition_shared_pos=0
        if self._side==1:
            self._state_pos=CONDITION_SIZE_BYTE+0
            self._alive_pos=CONDITION_SIZE_BYTE+1            
            self._pid_pos=CONDITION_SIZE_BYTE+2
            self._write_pnt_pos=CONDITION_SIZE_BYTE+6;
            self._write_data_pos=CONDITION_SIZE_BYTE+14;
            self._state_other_pos=CONDITION_SIZE_BYTE+self._side_size                        
            self._alive_other_pos=CONDITION_SIZE_BYTE+self._side_size+1            
            self._pid_other_pos=CONDITION_SIZE_BYTE+self._side_size+2
            self._read_pnt_pos=CONDITION_SIZE_BYTE+self._side_size+10;
            self._read_data_pos=CONDITION_SIZE_BYTE+self._side_size+14
            self._write_limit=CONDITION_SIZE_BYTE+self._side_size
            self._read_limit=self._size
        elif self._side==2:
            self._state_pos=CONDITION_SIZE_BYTE+self._side_size
            self._alive_pos=CONDITION_SIZE_BYTE+self._side_size+1
            self._pid_pos=CONDITION_SIZE_BYTE+self._side_size+2
            self._write_pnt_pos=CONDITION_SIZE_BYTE+self._side_size+6
            self._write_data_pos=CONDITION_SIZE_BYTE+self._side_size+14
            self._state_other_pos=CONDITION_SIZE_BYTE+0
            self._alive_other_pos=CONDITION_SIZE_BYTE+1
            self._pid_other_pos=CONDITION_SIZE_BYTE+2
            self._read_pnt_pos=CONDITION_SIZE_BYTE+10
            self._read_data_pos=CONDITION_SIZE_BYTE+14
            self._write_limit=self._size
            self._read_limit=CONDITION_SIZE_BYTE+self._side_size
        self._last_read_time=long(time.time() * 1000)
        self._last_write_time=long(time.time() * 1000)
        self._file=utils.file_open(self._path, "r+b")
        self._mmap = mmap.mmap(self._file.fileno(), 0)
        self._mmap.seek(0)
        self._mmap.write(struct.pack("!qiqqiqqiqqiq", -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1))
        if self._side==1:
            self._mmap.seek(CONDITION_SIZE_BYTE)
            self._mmap.write(struct.pack('!cciii','C','K',os.getpid(),0,0))            
            self._mmap.seek(CONDITION_SIZE_BYTE+self._side_size)
            self._mmap.write(struct.pack('!cciii','W','K',-1,0,0))
            self._waitconn_tm=long(time.time() * 1000)
        elif self._side==2:
            self._mmap.seek(CONDITION_SIZE_BYTE+self._side_size)            
            self._mmap.write(struct.pack('!cciii','C','K',os.getpid(),0,0))
        sharedmem_manager.add(self);
        
    def _initlock(self):    
        while self._condition_shared is None:
            if self._side==1:
                #LEGGE PID REMOTO PER CREARE LOCK
                self._mmap.seek(self._pid_other_pos)
                cpid=struct.unpack('!i', self._mmap.read(4))[0]
                if cpid!=-1:                                                            
                    self._condition_shared=Condition()    
                    lp=self._condition_shared.create(cpid);
                    self._mmap.seek(self._condition_shared_pos)
                    self._mmap.write(struct.pack("!qiqqiqqiqqiq", lp[0][0], lp[0][1], lp[0][2], lp[1][0], lp[1][1], lp[1][2], lp[2][0], lp[2][1], lp[2][2], lp[3][0], lp[3][1], lp[3][2]))
                    
            elif self._side==2:
                #LEGGE LOCKID PER CONNETTESI AI LOCK
                if self._condition_shared is None:
                    self._mmap.seek(self._condition_shared_pos)
                    applp=struct.unpack('!qiqqiqqiqqiq', self._mmap.read(80))
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
            err=""
            try:
                self._mmap.seek(self._state_pos)
                self._mmap.write('T')
                self._mmap.close()
            except Exception as e:
                err+="Error map close: " + str(e) + "; ";
            try:
                self._file.close()
            except Exception as e:
                err+="Error shared file close: " + str(e) + ";"
            if self._condition_shared is not None:
                self._condition_shared.destroy()
            if (err!=""):
                raise Exception(err)
    
    def _destroy_file(self):
        if self._side==1:
            if self._terminate_retry>=0:
                if utils.path_exists(self._path):
                    apptm=long(time.time() * 1000)
                    elp=apptm-self._terminate_time
                    if elp>2000:
                        try:
                            self._terminate_retry+=1
                            utils.path_remove(self._path)
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
            if self._mmap is not None:
                self._mmap.seek(self._state_pos)
                self._mmap.write('X')
                
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
                locstate, othstate = self._get_state()
                return locstate=="X" or locstate=="T"
            return True
        finally:
            self._semaphore.release()
    
    def _check_close(self):
        if self._is_init():
            locstate, othstate = self._get_state()
            if (locstate=="X" or locstate=="C") and (othstate=="X" or othstate=="T"):
                self._terminate()
            else:
                return False
            '''
            if self._side==1:
                if (locstate=="X" or locstate=="T") and othstate=="T":
                    self._terminate()
                else:
                    return False
            else:
                if (locstate=="X" or locstate=="T") and (othstate=="X" or othstate=="T"):
                    self._terminate()
                else:
                    return False
            '''
        return True
    
    def _check_alive(self):
        if self._is_init():
            #Verifica se l'altro lato mi ha chiesto un keep alive
            appalive=self._get_local_alive()
            if appalive=="A":
                self._set_local_alive("K")
            #Verifica se devo richiedere il keep alive all'altro lato
            locstate, othstate = self._get_state()
            if othstate=="W":
                elapsed=long(time.time() * 1000)-self._waitconn_tm
                if elapsed<0: #Cambiato orario pc
                    self._waitconn_tm=long(time.time() * 1000)
                elif elapsed>=5000:
                    self._terminate()
            elif othstate!="T":
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
                   
    def write(self, data):
        if not self._is_init():
            raise Exception("Shared file closed. (1)");
        self._initlock()
        locstate, othstate = self._get_state()
        if locstate=="X" or othstate=="X" or othstate=="T":
            self._close()
            raise Exception("Shared file closed. (2)")
        while othstate=="W":
            time.sleep(0.2)
            if not self._is_init():
                raise Exception("Shared file closed. (3)");
            locstate, othstate = self._get_state()
            if locstate=="X" or othstate=="X" or othstate=="T":
                self._close()
                raise Exception("Shared file closed. (4)")
        pw=self._get_pointer(self._write_pnt_pos)
        apps=data
        dtpos=0
        towrite=len(apps)                
        while towrite>0:
            #Attende lettura da parte dell'altro side
            self._condition_shared.acquire()
            try:
                while True:
                    pr=self._get_pointer(self._write_pnt_pos+4)
                    if pr==pw:
                        break  
                    elif pr>pw:
                        if pr-pw>1:
                            break
                    elif pr<pw:
                        if self._write_limit-self._write_data_pos-pw+pr>1:
                            break
                    self._condition_shared.wait(0.5)
                    
                    #VERIFICA CHIUSURA
                    if not self._is_init():
                        raise Exception("Shared file closed. (5)");
                    locstate, othstate = self._get_state()
                    if locstate=="X" or othstate=="X" or othstate=="T":
                        self._close()
                        raise Exception("Shared file closed. (6)")       
            finally:
                self._condition_shared.release()
            
            self._semaphore.acquire()
            try:
                #Cursore write si trova dopo Cursore read
                rpw=self._write_data_pos+pw
                self._mmap.seek(rpw)
                if pw>=pr: 
                    if towrite<self._write_limit-rpw:
                        utils.mmap_write(self._mmap,apps,dtpos,towrite)
                        pw+=towrite
                        dtpos+=towrite
                        towrite=0
                    else:
                        if pr>0:
                            appsz=self._write_limit-rpw
                            utils.mmap_write(self._mmap,apps,dtpos,appsz)
                            pw=0
                        else:
                            appsz=self._write_limit-rpw-1
                            utils.mmap_write(self._mmap,apps,dtpos,appsz)
                            pw+=appsz
                        dtpos+=appsz
                        towrite-=appsz
                #Cursore write si trova prima Cursore read
                rpw=self._write_data_pos+pw
                self._mmap.seek(rpw)
                if pw<pr: 
                    if towrite<=pr-pw-1:
                        utils.mmap_write(self._mmap,apps,dtpos,towrite)
                        pw+=towrite
                        dtpos+=towrite
                        towrite=0
                    else:
                        appsz=pr-pw-1
                        utils.mmap_write(self._mmap,apps,dtpos,appsz)
                        pw=pr-1
                        dtpos+=appsz
                        towrite-=appsz
                
                self._mmap.seek(self._write_pnt_pos)
                self._mmap.write(struct.pack('!i', pw))
            finally:
                self._semaphore.release()
                
            #NOTIFICA IL CAMBIAMENTO
            self._condition_shared.acquire()
            self._condition_shared.notify_all()
            self._condition_shared.release()
                
    def read(self,timeout=0,maxbyte=0): #0 infinite
        if not self._is_init():
            return None
        self._initlock()
        pr=self._get_pointer(self._read_pnt_pos)
        tm=long(time.time() * 1000)
        self._condition_shared.acquire()
        try:
            while True:
                pw=self._get_pointer(self._read_pnt_pos-4)
                if pr!=pw:
                    break
                #VERIFICA CHIUSURA
                locstate, appstate = self._get_state()
                if not self._is_init() or appstate=="X" or appstate=="T":
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
        
        dtread = utils.Bytes()
        self._semaphore.acquire()
        try:                   
            bread=0
            if pw<pr:
                bfullread=True
                appsz=self._read_limit-self._read_data_pos-pr;
                if maxbyte>0 and appsz>maxbyte:
                    appsz=maxbyte
                    bfullread=False
                rpr=self._read_data_pos+pr
                self._mmap.seek(rpr)
                dtread.append_bytes(utils.mmap_read(self._mmap,appsz))
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
                    self._mmap.seek(rpr)
                    dtread.append_bytes(utils.mmap_read(self._mmap,appsz))
                    if bfullread:
                        pr=pw
                    else:
                        pr+=appsz
            
            self._mmap.seek(self._read_pnt_pos)
            self._mmap.write(struct.pack('!i', pr))
        finally:
            self._semaphore.release()
        
        #NOTIFICA IL CAMBIAMENTO
        self._condition_shared.acquire()
        self._condition_shared.notify_all()
        self._condition_shared.release()
        return dtread;
    
    def write_token(self,data):
        dtwrite = utils.Bytes()
        dtwrite.append_int(len(data))
        dtwrite.append_bytes(data)
        self.write(dtwrite)
    
    def read_token(self):
        bfl = utils.Bytes()
        while len(bfl)<4:
            bf=self.read(maxbyte=4-len(bfl))
            if bf==None:
                return None
            bfl.append_bytes(bf)
        ln=bfl.get_int()
        bfret = utils.Bytes()
        while len(bfret)<ln:
            bf=self.read(maxbyte=ln-len(bfret))
            if bf==None:
                return None
            bfret.append_bytes(bf)
        return bfret

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
        


class Manager(threading.Thread):
    def __init__(self,fname=None):
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
    
    def getStreamFile(self,size):
        fname=None
        self._semaphore.acquire()
        try:
            while True:
                ar=[]
                for x in range(8):
                    if x==0:
                        ar.append(random.choice(string.ascii_lowercase))
                    else:
                        ar.append(random.choice(string.ascii_lowercase + string.digits))
                fname = "stream_" + ''.join(ar)
                fpath=SHAREDMEM_PATH + utils.path_sep + fname + ".shm"
                if not utils.path_exists(fpath):
                    with utils.file_open(fpath, "wb") as f:
                        f.write(" "*size)
                    break
            
        finally:
            self._semaphore.release()    
        return fname
    
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
                            if not sm._destroy_file():
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
        num=1000
        m1 = Stream()
        fname=None
        if self._fname==None:
            fname=m1.create()
        else:
            m1.connect(self._fname)
        if self._fname==None:
            t2 = TestThread(fname)
            t2.start()
            try:
                for i in range(num):
                    #m1.write(utils.Bytes("PROVA" + str(i+1) + " "))
                    m1.write_token(utils.Bytes(buffer("PROVA" + str(i+1) + " ")))
                
                '''
                appars=[]
                for i in range(1000): #0000):
                    appars.append("PROVA" + str(i+1) + " ")
                m1.write_token(utils.Bytes(buffer("".join(appars))))
                '''
                #m1.write(utils.Bytes("END"))
                #m1.write_token("END")
            except Exception as e:
                print("Errore write remote closed: " + str(e))
            time.sleep(8)
            m1.close()
        else:
            print "INIZIO..."
            cnt=0
            tm=utils.get_time()
            ar=[]            
            while True:
                #dt=m1.read()
                dt=m1.read_token()
                #s=dt.get_string()
                
                if dt is None:
                    #time.sleep(8);
                    raise Exception("Errore read remote closed") 
                ar.append(dt)
                #print(s)
                #if s[len(s)-3:]=="END":
                #    break
                cnt+=1
                #print(str(cnt))
                if num==cnt:
                    break
            #print("***************")
            print("TEMPO:" + str(utils.get_time()-tm))
            
            
            #print("VERIFICA...")
            #apps = "".join(ar);
            #ar=apps.split(" ");
            #bok=True
            #for i in range(num):
            #    if ar[i]!="PROVA" + str(i+1):
            #        bok=False
            #        print ("ERRORE: " + ar[i] + "  (PROVA" + str(i+1) + ")")
            #if bok:
            #    print "TUTTO OK"
            #print "FINE"
            m1.close()
            print "ATTESA RIMOZIONE FILE..."
            time.sleep(8);
            print "VERIFICARE!"
            

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
    
        
   

    
    
        
        
        
            
            