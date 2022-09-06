# -*- coding: utf-8 -*-
'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import sys
import subprocess
import os
import struct
import time
import copy
import utils
import ctypes
import json
import string
import random
import mmap
import stat
import native
import importlib
import threading

_struct_IIcc=struct.Struct("!IIcc")
_struct_I=struct.Struct("!I")
_struct_BI=struct.Struct("!BI")
_struct_c=struct.Struct("!c")
_struct_cc=struct.Struct("!cc")
_struct_utmp = struct.Struct('hi32s4s32s256shhiii4i20s')

IPC_PATH="sharedmem"
MMP_NAME="/dwammp"
SEM_NAME="/dwasem"

_ipcmap={}
_ipcmap["libbaseloaded"] = False
_ipcmap["semaphore"] = threading.Condition()
_ipcmap["picklesemaphore"] = threading.Condition()
_ipcmap["pickleprocess"] = None
_ipcmap["childsharedobjsemaphore"] = threading.Condition()
_ipcmap["childsharedobj"] = []
_ipcmap["threadsharedobj"]={}
_ipcmap["list_names_lock"]=threading.RLock()
_ipcmap["list_names"]=[]

try:
    import _multiprocessing
    import multiprocessing.synchronize
    if utils.is_windows():
        if utils.is_py2():
            import multiprocessing.forking
            import _subprocess
        else:
            import _winapi
except:
    _ipcmap["libbaseloaded"] = True



class SEMAPHORE_DEF(ctypes.Structure):
    _fields_ = [("create",ctypes.c_int),
                ("mode",ctypes.c_int),
                ("fd",ctypes.c_int),
                ("semvalue",ctypes.c_int),
                ("sem",ctypes.c_void_p),
                ("name", ctypes.c_char_p)]

class SHAREDMEMORY_DEF(ctypes.Structure):
    _fields_ = [("create",ctypes.c_int),
                ("mode",ctypes.c_int),
                ("fd",ctypes.c_int),
                ("size",ctypes.c_int),
                ("name", ctypes.c_char_p)]

def _add_child_shared_obj(obj):
    _ipcmap["childsharedobjsemaphore"].acquire()    
    try:
        _ipcmap["childsharedobj"].append(obj)
    finally:
        _ipcmap["childsharedobjsemaphore"].release()

def _destroy_child_shared_obj():
    _ipcmap["childsharedobjsemaphore"].acquire()    
    try:
        for i in reversed(range(len(_ipcmap["childsharedobj"]))):
            try:
                obj=_ipcmap["childsharedobj"][i]
                obj._destroy()
            except:
                ex = utils.get_exception()
                print("_destroy_child_shared_obj  " + str(obj) + " - err: " + utils.exception_to_string(ex))
        _ipcmap["childsharedobj"]=None
    finally:
        _ipcmap["childsharedobjsemaphore"].release()

def _rndseq(cnt):
        ar=[]
        for x in range(cnt):
            if x==0:
                ar.append(random.choice(string.ascii_lowercase))
            else:
                ar.append(random.choice(string.ascii_lowercase + string.digits))            
        return ''.join(ar)

def _add_name(suffix):
        with _ipcmap["list_names_lock"]: 
            while True:
                spid=str(os.getpid())
                nm = suffix + "_" + spid + "_" + _rndseq(10)
                if nm not in _ipcmap["list_names"]:
                    _ipcmap["list_names"].append(nm)
                    if not utils.is_windows():
                        pth = process_manager._get_release_path("dwa_" + spid)
                        if not os.path.exists(pth):
                            with utils.file_open(pth, "w", encoding="utf-8") as f:
                                f.write("[]")
                            utils.path_change_permissions(pth, stat.S_IRUSR | stat.S_IWUSR)
                        with utils.file_open(pth, "w", encoding="utf-8") as f:
                            f.write(json.dumps(_ipcmap["list_names"])) 
                    return nm

def _rem_name(nm):
    with _ipcmap["list_names_lock"]:
        if nm in _ipcmap["list_names"]:
            _ipcmap["list_names"].remove(nm)
            if not utils.is_windows():
                spid=str(os.getpid())
                pth = process_manager._get_release_path("dwa_" + spid)
                with utils.file_open(pth, "w", encoding="utf-8") as f:
                    f.write(json.dumps(_ipcmap["list_names"]))

def _fix_perm_get_mode(fixperm):
    if fixperm is not None:
        jo = fixperm()
        if "mode" in jo:
            return jo["mode"]        
    return stat.S_IRUSR | stat.S_IWUSR 

def _fix_perm_path(fpath, fixperm):
    if utils.is_windows():
        None        
    else:
        utils.path_change_permissions(fpath, _fix_perm_get_mode(fixperm))

def initialize():
        try:
            if not utils.path_exists(IPC_PATH):
                utils.path_makedir(IPC_PATH)
            else:
                clear_path(True)
        except:
            e = utils.get_exception()
            print("ipc init_path error: " + utils.exception_to_string(e))        
        process_manager.start()

def terminate():
    process_manager.destory()
    process_manager.join(5)

def clear_path(checkpid=False):
    if utils.path_exists(IPC_PATH):
        lst=utils.path_list(IPC_PATH);
        for fname in lst:
            try:
                if fname.endswith(".mmp") or fname.endswith(".cfg"):
                    if utils.path_exists(IPC_PATH + utils.path_sep + fname):
                        utils.path_remove(IPC_PATH + utils.path_sep + fname)
            except:
                None
            try:
                if not utils.is_windows():
                    if fname.endswith(".rls"):
                        bdelfile=True                        
                        if is_load_libbase():                        
                            spid = fname[0:len(fname)-4].split("_")[1]
                            if checkpid==True:
                                try:
                                    if native.get_instance().is_task_running(int(spid)):
                                        bdelfile=False
                                except:
                                    bdelfile=False
                            if bdelfile:
                                applst=[]
                                try:
                                    with utils.file_open(IPC_PATH + utils.path_sep + fname, "rb") as f:
                                        applst=json.loads(f.read())
                                except:
                                    None
                                for n in applst:
                                    try:
                                        if n.startswith(SEM_NAME):
                                            _ipcmap["libbase"].semUnlink(str(n))
                                        elif n.startswith(MMP_NAME):
                                            _ipcmap["libbase"].shmUnlink(str(n))
                                    except:
                                        None                                
                        if bdelfile:
                            if utils.path_exists(IPC_PATH + utils.path_sep + fname):
                                utils.path_remove(IPC_PATH + utils.path_sep + fname)
            except:
                None

def _dump_obj(o, prc):    
    dtret=None
    _ipcmap["picklesemaphore"].acquire()
    oldprc = _ipcmap["pickleprocess"]
    try:
        _ipcmap["pickleprocess"] = prc
        sfile = utils.BytesIO()
        utils.Pickler(sfile, -1).dump(o)
        dtret = sfile.getvalue()
    finally:
        _ipcmap["pickleprocess"] = oldprc
        _ipcmap["picklesemaphore"].release()
    return dtret

def _load_obj(dt):
    if dt is None:
        return None    
    sfile = utils.BytesIO(dt)
    return utils.Unpickler(sfile).load()

def is_load_libbase():
    _ipcmap["semaphore"].acquire()
    try:
        if _ipcmap["libbaseloaded"]:
            return "libbase" in _ipcmap
        _ipcmap["libbaseloaded"]=True
        
        if utils.is_windows():
            _libbase = native.get_instance().get_library()
            if _libbase is not None:
                _ipcmap["libbase"]=_libbase
                return True
        else:
            try:
                _libbase = native.get_instance().get_library()
                if _libbase is not None:                    
                    _ipcmap["libbase"]=_libbase
                    return True                                
            except:
                None            
    finally:
        _ipcmap["semaphore"].release()
    return False


class SemIPC(object):

    def __init__(self, kind, value, maxvalue, fixperm=None):
        self._bdestroy=False
        self._bcreate=True
        self._countdup=0
        self._sem_name=None
        self._sem_def=None
        if is_load_libbase():
            self._libbase=_ipcmap["libbase"]
            if utils.is_windows():
                if utils.is_py2():
                    self._semlock = _multiprocessing.SemLock(kind, value, maxvalue)
                else:
                    self._semlock = _multiprocessing.SemLock(kind, value, maxvalue, "", True)
            else:
                cnttry=0
                while True:
                    sid=_add_name(SEM_NAME)
                    self._sem_name=sid
                    self._sem_def = SEMAPHORE_DEF()
                    self._sem_def.name=utils.str_to_bytes(self._sem_name)
                    self._sem_def.create=1
                    self._sem_def.mode=_fix_perm_get_mode(fixperm)
                    self._sem_def.semvalue=value
                    iret = self._libbase.semaphoreInitialize(ctypes.byref(self._sem_def))
                    if iret==0:
                        break
                    if sid is not None:
                        _rem_name(sid)
                        sid=None
                    cnttry+=1
                    if cnttry>=10 or iret!=-1:
                        raise Exception("Semaphore initialize failed.")
                    else:
                        time.sleep(0.2)
                
                if utils.is_py2():
                    self._semlock = _multiprocessing.SemLock._rebuild(*(self._sem_def.sem, kind, maxvalue))
                else:
                    self._semlock = _multiprocessing.SemLock._rebuild(*(self._sem_def.sem, kind, maxvalue, None))
            
            self._type=kind
            self._max=maxvalue
        else:
            raise Exception("Semaphore libabase load failed.")
            
                
    def __getstate__(self):
        prc = _ipcmap["pickleprocess"];
        if prc is None:
            raise Exception("No child process attached")
        sid=None        
        if utils.is_windows():
            if utils.is_py2():
                chandle = _multiprocessing.win32.OpenProcess(_multiprocessing.win32.PROCESS_ALL_ACCESS, False, prc.get_pid())
                sid = _subprocess.DuplicateHandle(_subprocess.GetCurrentProcess(), self._semlock.handle, chandle, 0, False, _subprocess.DUPLICATE_SAME_ACCESS).Detach()
                multiprocessing.forking.close(chandle)
            else:
                chandle = _winapi.OpenProcess(_winapi.PROCESS_ALL_ACCESS, False, prc.get_pid())
                sid = _winapi.DuplicateHandle(_winapi.GetCurrentProcess(), self._semlock.handle, chandle, 0, False, _winapi.DUPLICATE_SAME_ACCESS)
                _winapi.CloseHandle(chandle)
        else:
            sid = self._sem_name
        prc._add_shared_obj(self)
        self._countdup+=1        
        return (sid, self._type, self._max)

    def __setstate__(self, state):
        self._bdestroy=False
        self._bcreate=False
        self._countdup=0
        self._sem_def=None
        self._sem_name=None
        if is_load_libbase():
            self._libbase=_ipcmap["libbase"]
            if utils.is_windows():
                if utils.is_py2():
                    self._semlock = _multiprocessing.SemLock._rebuild(*state)
                else:
                    self._semlock = _multiprocessing.SemLock._rebuild(*(state[0],state[1],state[2],None))
            else: 
                self._sem_name=state[0]
                self._sem_def=SEMAPHORE_DEF()
                self._sem_def.name=utils.str_to_bytes(self._sem_name)
                self._sem_def.create=0
                iret = self._libbase.semaphoreInitialize(ctypes.byref(self._sem_def))                    
                if iret==0:
                    if utils.is_py2():
                        self._semlock=_multiprocessing.SemLock._rebuild(*(self._sem_def.sem,state[1],state[2]))
                    else:
                        self._semlock=_multiprocessing.SemLock._rebuild(*(self._sem_def.sem,state[1],state[2],None))
                else:
                    raise Exception("Semaphore initialize failed.")
            _add_child_shared_obj(self)
        else:
            raise Exception("Semaphore libbase load failed.")

       
    def acquire(self, blocking=True, timeout=None):
        if blocking and timeout is None:
            while not self._semlock.acquire(blocking,1):
                if self._bdestroy:
                    raise Exception("Semaphore destroyed.")
            return True
        else:
            return self._semlock.acquire(blocking,timeout)        
    
    def release(self):
        return self._semlock.release()

    def __enter__(self):
        return self.acquire()

    def __exit__(self, *args):
        return self.release()
    
    def get_value(self):
        return self._semlock._get_value()
    
    def __del__(self):
        try:
            self._destroy()            
        except:
            None
    
    def _destroy(self):
        if self._bdestroy==False:
            self._bdestroy=True
            if self._bcreate==True:
                if self._sem_name is not None:
                    _rem_name(self._sem_name)
                    self._sem_name=None
            if self._semlock is not None:
                if utils.is_windows():
                    self._libbase.closeHandle(self._semlock.handle)
                else:
                    self._libbase.semaphoreDestroy(ctypes.byref(self._sem_def))
                self._semlock=None
            

class SemTHC(object):

    def __init__(self, objthc):
        self._threadsharedobjid = None
        self._objthc=objthc
        self._make_methods()
    
    def __del__(self):
        try:
            if self._threadsharedobjid is not None and self._threadsharedobjid in _ipcmap["threadsharedobj"]:            
                del _ipcmap["threadsharedobj"][self._threadsharedobjid]
        except:
            None
    
    def __getstate__(self):
        if self._threadsharedobjid is None: 
            self._threadsharedobjid = id(self)
            _ipcmap["threadsharedobj"][self._threadsharedobjid]=self
        return self._threadsharedobjid
    
    def __setstate__(self, state):
        self._threadsharedobjid = None
        self._objthc=_ipcmap["threadsharedobj"][state]._objthc
        self._make_methods()
    
    def _make_methods(self):
        None
    
class LockIPC(SemIPC):

    def __init__(self, fixperm=None):
        SemIPC.__init__(self, multiprocessing.synchronize.SEMAPHORE, 1, 1, fixperm)

class LockTHC(SemTHC):
    
    def __init__(self):
        SemTHC.__init__(self, threading.Lock())
        
    def _make_methods(self):
        self.acquire = self._objthc.acquire
        self.release = self._objthc.release        

def Lock(fixperm=None):
    if is_load_libbase():
        return LockIPC(fixperm)
    else:
        return LockTHC()
   
class RLockIPC(SemIPC): 
    
    def __init__(self, fixperm=None):
        SemIPC.__init__(self, multiprocessing.synchronize.RECURSIVE_MUTEX, 1, 1, fixperm)

class RLockTHC(SemTHC): 
    
    def __init__(self):
        SemTHC.__init__(self, threading.RLock())
    
    def _make_methods(self):
        self.acquire = self._objthc.acquire
        self.release = self._objthc.release

def RLock(fixperm=None):
    if is_load_libbase():
        return RLockIPC(fixperm)
    else:
        return RLockTHC()

class SemaphoreIPC(SemIPC): 
    
    def __init__(self, value=1, fixperm=None):
        SemIPC.__init__(self, multiprocessing.synchronize.SEMAPHORE, value, _multiprocessing.SemLock.SEM_VALUE_MAX, fixperm)

class SemaphoreTHC(SemTHC): 
    
    def __init__(self, value=1):
        SemTHC.__init__(self, threading.Semaphore(value))
    
    def _make_methods(self):
        self.acquire = self._objthc.acquire
        self.release = self._objthc.release

def Semaphore(fixperm=None):
    if is_load_libbase():
        return SemaphoreIPC(fixperm)
    else:
        return SemaphoreTHC()
    
class BoundedSemaphoreIPC(SemaphoreIPC):

    def __init__(self, value=1, fixperm=None):
        SemIPC.__init__(self, multiprocessing.synchronize.SEMAPHORE, value, value, fixperm)


class BoundedSemaphoreTHC(SemTHC):

    def __init__(self, value=1):
        SemTHC.__init__(self, threading.BoundedSemaphore(value))
    
    def _make_methods(self):
        self.acquire = self._objthc.acquire
        self.release = self._objthc.release

def BoundedSemaphore(fixperm=None):
    if is_load_libbase():
        return BoundedSemaphoreIPC(fixperm)
    else:
        return BoundedSemaphoreTHC()

class ConditionIPC(object):
    
    def __init__(self, lock=None, fixperm=None):
        self._bdestroy=False
        self._lock = lock or RLockIPC(fixperm)
        self._sleeping_count = SemaphoreIPC(0,fixperm)
        self._woken_count = SemaphoreIPC(0,fixperm)
        self._wait_semaphore = SemaphoreIPC(0,fixperm)
        self._make_methods()
    
    def __del__(self):
        self._destroy()
    
    def _destroy(self):
        self._bdestroy=True
        self._wait_semaphore=None
        self._woken_count=None
        self._sleeping_count=None
        self._lock=None                    
    
    def __getstate__(self):
        prc = _ipcmap["pickleprocess"];
        if prc is None:
            raise Exception("No child process attached")
        prc._add_shared_obj(self)
        return (self._lock,self._sleeping_count,self._woken_count,self._wait_semaphore)
    
    def __setstate__(self, st):
        self._lock,self._sleeping_count,self._woken_count,self._wait_semaphore = st
        self._make_methods()
        _add_child_shared_obj(self)
    
    def __enter__(self):
        return self._lock.__enter__()

    def __exit__(self, *args):
        return self._lock.__exit__(*args)
        
    def _make_methods(self):        
        self.acquire = self._lock.acquire        
        self.release = self._lock.release        
    
    def wait(self, timeout=None):
        assert self._lock._semlock._is_mine(), 'must acquire() condition before using wait()'
        self._sleeping_count.release()
        count = self._lock._semlock._count()
        for i in utils.nrange(count):
            self._lock.release()
        try:
            self._wait_semaphore.acquire(True, timeout)
        finally:
            self._woken_count.release()
            for i in utils.nrange(count):
                self._lock.acquire()
        
    def notify(self):
        assert self._lock._semlock._is_mine(), 'lock is not owned'
        assert not self._wait_semaphore.acquire(False)
        while self._woken_count.acquire(False):
            res = self._sleeping_count.acquire(False)
            assert res

        if self._sleeping_count.acquire(False): 
            self._wait_semaphore.release()      
            self._woken_count.acquire()         
            self._wait_semaphore.acquire(False)        
    
    def notify_all(self):
        assert self._lock._semlock._is_mine(), 'lock is not owned'
        assert not self._wait_semaphore.acquire(False)
        while self._woken_count.acquire(False):
            res = self._sleeping_count.acquire(False)
            assert res
        sleepers = 0
        while self._sleeping_count.acquire(False):
            self._wait_semaphore.release()
            sleepers += 1

        if sleepers:
            for i in utils.nrange(sleepers):
                self._woken_count.acquire()
            while self._wait_semaphore.acquire(False):
                pass


class ConditionTHC(SemTHC):
    
    def __init__(self, lock=None):
        SemTHC.__init__(self, threading.Condition(lock))        
    
    def _make_methods(self):
        self.acquire = self._objthc.acquire
        self.release = self._objthc.release
        self.wait=self._objthc.wait
        self.notify=self._objthc.notify
        self.notify_all=self._objthc.notify_all

def Condition(lock=None,fixperm=None):
    if is_load_libbase():
        return ConditionIPC(lock=lock,fixperm=fixperm)
    else:
        return ConditionTHC(lock)

class EventIPC(object):

    def __init__(self, fixperm=None):
        self._cond = ConditionIPC(LockIPC(fixperm),fixperm)
        self._flag = SemaphoreIPC(0)

    def __del__(self):
        self._destroy()
    
    def _destroy(self):
        self._cond=None
        self._flag=None                    
    
    def __getstate__(self):
        prc = _ipcmap["pickleprocess"];
        if prc is None:
            raise Exception("No child process attached")
        prc._add_shared_obj(self)        
        return (self._cond,self._flag)
    
    def __setstate__(self, st):        
        self._cond, self._flag = st
        _add_child_shared_obj(self)
    
    def is_set(self):
        self._cond.acquire()
        try:
            if self._flag.acquire(False):
                self._flag.release()
                return True
            return False
        finally:
            self._cond.release()

    def set(self):
        self._cond.acquire()
        try:
            self._flag.acquire(False)
            self._flag.release()
            self._cond.notify_all()
        finally:
            self._cond.release()

    def clear(self):
        self._cond.acquire()
        try:
            self._flag.acquire(False)
        finally:
            self._cond.release()

    def wait(self, timeout=None):
        self._cond.acquire()
        try:
            if self._flag.acquire(False):
                self._flag.release()
            else:
                self._cond.wait(timeout)

            if self._flag.acquire(False):
                self._flag.release()
                return True
            return False
        finally:
            self._cond.release()

class EventTHC(SemTHC):

    def __init__(self):
        SemTHC.__init__(self, threading.Event())
        
    def _make_methods(self):
        self.is_set=self._objthc.is_set
        self.set=self._objthc.set
        self.clear=self._objthc.clear
        self.wait=self._objthc.wait

def Event(fixperm=None):
    if is_load_libbase():
        return EventIPC(fixperm)
    else:
        return EventTHC()


    
'''
STREAM FILES MAP:

04 bytes: position write side 1 (DATA1)
04 bytes: position read side 2 (DATA1)
01 bytes: State side 1 (C:Connected X:Close T:Terminate)
04 bytes: position write side 2 (DATA2)
04 bytes: position read side 1 (DATA2)
01 bytes: State side 2 (I:Initializing C:Connected X:Close T:Terminate)    
DATA1 - write for Side 1 and read for Side 2)
DATA2 - write for Side 2 and read for Side 1)
'''
class StreamIPC():
    
    def __init__(self,prop=None):
        self._bdestroy=False
        self._prop=prop
        self._side=0
        self._bclose=False        
        self._binit=False        
        self._mmap_state_size = 18
        self._size1 = 0
        self._size2 = 0
        self._read_start_pos=0
        self._write_start_pos=0
        self._write_size = 0
        self._read_size = 0
        self._mmap = None
        self._cond = None
        self._read_timeout_function=None
        self._mconf = None
        self._cprocess = None
        self._keepalive_counter = utils.Counter()
        self._semaphore = threading.Condition()
        #self._otherpid = None
    
    def __del__(self):
        try:
            self._destroy()
        except:
            None        
        
    def _destroy(self):
        if self._bdestroy==False:
            self._bdestroy=True
            try:
                if self._mmap is not None:
                    self._mmap.close()
            except:
                None        
            self._mmap=None
            self._cond = None
    
    def __getstate__(self):
        if self._cprocess is not None:
            raise Exception("Stream already attached to child process.")        
        self._cprocess = _ipcmap["pickleprocess"];
        self._create()
        self._cprocess._add_shared_obj(self)
        return (os.getpid(), self._mmap,self._cond,self._size1,self._size2)
    
    def __setstate__(self, st):
        self._bdestroy=False
        self.__init__()
        self._open(st)
        _add_child_shared_obj(self)
    
    def _is_init(self):
        return self._binit
    
    def _create(self):
        self._semaphore.acquire()
        try:                
            if self._binit==True:
                raise Exception("Stream already initialized.")
            fixperm=None
            if self._prop is not None and "fixperm" in self._prop:
                fixperm=self._prop["fixperm"]
            appsz = 1*1024*1024
            if self._prop is not None and "size" in self._prop:
                appsz=self._prop["size"] 
            self._size1 = int(appsz/2)
            if self._prop is not None and "size1" in self._prop:
                self._size1 = self._prop["size1"] 
            self._size2 = int(appsz/2)
            if self._prop is not None and "size2" in self._prop:
                self._size2 = self._prop["size2"]       
            
            self._mmap = MemMap(self._mmap_state_size + self._size1 + self._size2, fixperm)
            self._cond = Condition(fixperm=fixperm)
            #self._otherpid=self._cprocess.get_pid()
            self._initialize(1)
            self._binit=True            
        except:
            e = utils.get_exception()
            self._destroy()
            raise e
        finally:
            self._semaphore.release() 
        
    def _open(self, ostate):
        self._semaphore.acquire()
        try:
            if self._binit==True:
                raise Exception("Stream already initialized.")
            self._otherpid, self._mmap, self._cond, self._size1, self._size2 = ostate            
            self._initialize(2)
            self._binit=True
        except:
            e = utils.get_exception()
            self._destroy()
            raise e
        finally:
            self._semaphore.release() 
    
    def _initialize(self, side):
        self._side=side
        if self._side==1:
            self._write_size = self._size1
            self._read_size = self._size2
            self._write_pos=0
            self._read_pos=9
            self._state_pos=8
            self._state_pos_other=17
            self._write_start_pos=self._mmap_state_size
            self._read_start_pos=self._mmap_state_size + self._size1
            self._mmap.seek(0)
            self._mmap.write(_struct_IIcc.pack(self._write_start_pos,self._write_start_pos,b"C",b"K"))
            self._mmap.write(_struct_IIcc.pack(0,0,b"I",b"K"))
        elif self._side==2:
            self._write_size = self._size2
            self._read_size = self._size1
            self._write_pos=9
            self._read_pos=0
            self._state_pos=17
            self._state_pos_other=8
            self._write_start_pos=self._mmap_state_size + self._size1
            self._read_start_pos=self._mmap_state_size
            self._mmap.seek(self._write_pos)
            self._mmap.write(_struct_IIcc.pack(self._write_start_pos,self._write_start_pos,b"C",b"K"))                
     
    def _close_nosync(self):
        if not self._bclose:
            self._bclose=True
            self._mmap.seek(self._state_pos)
            self._mmap.write(_struct_c.pack(b"X"))
    
    def close(self):
        if self._binit==False or self._cond is None or self._mmap is None:
            return
        try:
            self._cond.acquire()
            try:
                self._close_nosync()
            finally:
                self._cond.release()
        except:
            self._close_nosync()
    
    def is_closed(self):
        return self._bclose
    
    def write(self, data):
        if self._bclose:
            raise Exception("Stream closed")
        self._cond.acquire()
        try:
            p=0
            sz=len(data)
            while not self._bclose and sz>0:
                self._mmap.seek(self._write_pos)
                pw, pr, st, ka = _struct_IIcc.unpack(self._mmap.read(10))
                self._mmap.seek(self._state_pos_other)
                st_other, ka_other = _struct_cc.unpack(self._mmap.read(2))
                #if st_other==b"X" or st_other==b"T":
                if st_other==b"X":
                    self._close_nosync()
                    break
                if pw>=pr:
                    szspace=self._write_size-(pw-pr)-1
                    szlimit=self._write_size-(pw-self._write_start_pos)
                    szremain=(pr-self._write_start_pos)-1
                    if szremain<=0:
                        szlimit-=1
                else: 
                    szspace=pr-pw-1
                    szlimit=szspace
                    szremain=0
                if szspace==0:
                    self._cond.wait(1)
                else:   
                    self._mmap.seek(pw)
                    if sz<=szlimit:
                        self._mmap.write(utils.buffer_new(data,p,len(data)-p))
                        pw+=sz
                        if pw-self._write_start_pos==self._write_size:
                            pw=self._write_start_pos
                        p+=sz
                        sz=0                                                    
                    else:
                        self._mmap.write(utils.buffer_new(data,p,szlimit))
                        pw+=szlimit
                        if pw-self._write_start_pos==self._write_size:
                            pw=self._write_start_pos
                        p+=szlimit
                        sz-=szlimit
                        if szremain>0:
                            ln = sz
                            if sz>szremain:
                                ln = szremain
                            self._mmap.seek(pw)
                            self._mmap.write(utils.buffer_new(data,p,ln))
                            pw+=ln
                            if pw-self._write_start_pos==self._write_size:
                                pw=self._write_start_pos
                            p+=ln
                            sz-=ln                            
                        
                    self._mmap.seek(self._write_pos)
                    self._mmap.write(_struct_I.pack(pw))
                    self._cond.notify_all()
        finally:
            self._cond.release()
        if self._bclose:
            raise Exception("Stream closed")
    
    def set_read_timeout_function(self,f):
        self._read_timeout_function=f    
    
    def read(self,numbytes=0):
        dt=None
        ardt=[]
        self._cond.acquire()
        try:
            while not self._bclose:
                self._mmap.seek(self._read_pos)
                pw, pr, st, ka = _struct_IIcc.unpack(self._mmap.read(10))
                if pw>pr:
                    sz=pw-pr
                elif pw<pr:
                    sz=self._read_size-(pr-self._read_start_pos)
                if pw==pr: # or (numbytes>0 and numbytes>sz):
                    #if st==b"X" or st==b"T":
                    if st==b"X":
                        self._close_nosync()
                        break
                    self._cond.wait(1)
                    if self._read_timeout_function is not None and self._read_timeout_function(self):
                        raise Exception("Read timeout")                    
                    if self._bdestroy:
                        raise Exception("Stream closed.")
                else: 
                    self._mmap.seek(pr)
                    if numbytes>0:
                        if sz>numbytes:
                            sz=numbytes                    
                        ardt.append(self._mmap.read(sz))
                        numbytes-=sz
                    else:
                        dt = self._mmap.read(sz)
                    pr+=sz
                    if pr-self._read_start_pos==self._read_size:
                        pr=self._read_start_pos
                    self._mmap.seek(self._read_pos+4)
                    self._mmap.write(_struct_I.pack(pr))
                    self._cond.notify_all()
                    if numbytes==0:
                        if dt is None:
                            dt=utils.bytes_join(ardt)
                        break
        finally:
            self._cond.release()
        return dt
    
    def write_int(self, i):
        self.write(_struct_I.pack(i))
    
    def read_int(self):
        bt = self.read(numbytes=4)
        if bt is None:
            return None
        return _struct_I.unpack(bt)[0]        
    
    def write_bytes(self, bts):
        self.write(_struct_I.pack(len(bts))+bts)
    
    def read_bytes(self):
        bt = self.read(numbytes=4)
        if bt is None:
            return None
        sz = _struct_I.unpack(bt)[0]
        if sz==0:
            return ""
        return self.read(numbytes=sz)
    
    def write_str(self, s, enc="utf8"):
        ba = bytearray(s,enc)
        self.write(_struct_BI.pack(len(enc),len(ba))+enc+ba)        
    
    def read_str(self):
        bt = self.read(numbytes=5)
        if bt is None:
            return None
        encsz, sz=_struct_BI.unpack(bt)
        enc = self.read(numbytes=encsz)
        if enc is None:
            return None
        if sz==0:
            return ""
        return self.read(numbytes=sz).decode(enc)
    
    def write_obj(self, o):
        bts = _dump_obj(o,self._cprocess)
        self.write(_struct_I.pack(len(bts))+bts)
    
    def read_obj(self):
        bt = self.read(numbytes=4)
        if bt is None:
            return None
        sz = _struct_I.unpack(bt)[0]
        return _load_obj(self.read(numbytes=sz))

class StreamTHC(StreamIPC):
    
    def __init__(self,prop=None):
        StreamIPC.__init__(self, prop)
        self._threadsharedobjid=None
    
    def __del__(self):
        try:
            if self._threadsharedobjid is not None and self._threadsharedobjid in _ipcmap["threadsharedobj"]:            
                del _ipcmap["threadsharedobj"][self._threadsharedobjid]
        except:
            None
    
    def __getstate__(self):
        if self._threadsharedobjid is None:
            self._create() 
            self._threadsharedobjid = id(self)
            _ipcmap["threadsharedobj"][self._threadsharedobjid]=self
        return self._threadsharedobjid
    
    def __setstate__(self, state):
        self.__init__()
        pobj=_ipcmap["threadsharedobj"][state]
        self._open((None, pobj._mmap,pobj._cond,pobj._size1,pobj._size2))
    

def Stream(prop=None):
    if is_load_libbase():
        return StreamIPC(prop)
    else:
        return StreamTHC(prop)

class MemMapIPC():
    
    def __init__(self,size,fixperm=None):
        self.shm_def = None
        self.file=None
        self.fixperm=fixperm
        self.mmap=None
        self.size=size
        self.bcreate=True
        self.bclose=False
        self.bdestroy=False
        self._create()
    
    def __del__(self):
        try: 
            self._destroy()        
        except:
            None
        
    def _destroy(self):
        if not self.bdestroy:
            self.bdestroy=True
            if self.bcreate:
                self.close()
                if self.ftype=="F":
                    if utils.path_exists(self.fpath):
                        try:
                            utils.path_remove(self.fpath)
                        except:
                            ex = utils.get_exception()
                            print("MemMap remove file error: " + utils.exception_to_string(ex))
                elif self.ftype=="M":
                    _rem_name(self.fname)
                    if not utils.is_windows():                        
                        iret = self._libbase.sharedMemoryDestroy(ctypes.byref(self.shm_def))
                        if iret!=0:
                            print("Shared memory destroy failed.")
            
    
    def __getstate__(self):
        if not self.bcreate:
            raise Exception("MemMap not initialized")
        prc = _ipcmap["pickleprocess"];
        if prc is None:
            raise Exception("No child process attached")
        prc._add_shared_obj(self)
        return {"type":self.ftype, "name":self.fname, "size":self.size}
    
    def __setstate__(self, st):
        self.file=None
        self.fixperm=None
        self.mmap=None
        self.size=None
        self.bcreate=False
        self.bclose=False
        self.bdestroy=False
        self._open(st)
        _add_child_shared_obj(self)
    
    def _create_mem(self, fixperm):
        if not utils.is_windows():
            if is_load_libbase():
                self._libbase=_ipcmap["libbase"]
                cnt=0
                while True:
                    self.fname = _add_name(MMP_NAME)
                    self.shm_def = SHAREDMEMORY_DEF()
                    self.shm_def.name=utils.str_to_bytes(self.fname)
                    self.shm_def.create=1
                    self.shm_def.size=self.size
                    self.shm_def.mode=_fix_perm_get_mode(fixperm)
                    iret = self._libbase.sharedMemoryInitialize(ctypes.byref(self.shm_def))
                    if iret==0:
                        self.ftype="M"
                        try:
                            self._prepare_map()
                            return
                        except:
                            ex = utils.get_exception()
                            self._libbase.sharedMemoryDestroy(ctypes.byref(self.shm_def))
                            _rem_name(self.fname)
                            raise ex
                    else:     
                        _rem_name(self.fname)               
                        cnt+=1
                        if cnt>=5 or iret!=-1:
                            raise Exception("SharedMemory initialize failed")
                        else:
                            time.sleep(0.2)            
            else:
                raise Exception("SharedMemory libbase load failed")
        else:
            self.fname = _add_name(MMP_NAME)
            self.ftype="M"
            try:
                self._prepare_map()
            except:
                _rem_name(self.fname)
                raise Exception(utils.get_exception())
            
    def _create_disk(self, fixperm):
        while True:
            spid=str(os.getpid())
            self.fname = MMP_NAME + "_" + spid + "_" + _rndseq(10)
            self.fpath=IPC_PATH + utils.path_sep + self.fname + ".mmp"
            if not utils.path_exists(self.fpath):
                with utils.file_open(self.fpath, "wb") as f:
                    f.write(" "*self.size)
                _fix_perm_path(self.fpath,fixperm)
                self.file=utils.file_open(self.fpath, "r+b")
                self.ftype="F"
                self._prepare_map()
                break
    
    def _create(self):
        try:
            self._create_mem(self.fixperm)
        except:
            self._create_disk(self.fixperm)

    def _open(self, mconf):
        self.ftype=mconf["type"]
        self.fname=mconf["name"]
        self.size=mconf["size"]
        if self.ftype=="F":
            self.fpath=process_manager._get_memmap_path(self.fname)
            if not utils.path_exists(self.fpath):
                raise Exception("Shared file not found.")
            self.file=utils.file_open(self.fpath, "r+b")
        elif self.ftype=="M":            
            if not utils.is_windows():
                if is_load_libbase():
                    self._libbase=_ipcmap["libbase"]
                    self.shm_def = SHAREDMEMORY_DEF()
                    self.shm_def.name=utils.str_to_bytes(self.fname)
                    self.shm_def.create=0
                    self.shm_def.size=self.size
                    iret = self._libbase.sharedMemoryInitialize(ctypes.byref(self.shm_def))
                    if iret!=0:
                        raise Exception("SharedMemory initialize failed")
                else:
                    raise Exception("SharedMemory libbase load failed")
        self._prepare_map()                
    
    def _prepare_map(self):
        try:
            if self.ftype=="F":
                self.mmap=mmap.mmap(self.file.fileno(), 0)                                
            elif self.ftype=="M":
                if not utils.is_windows():
                    self.mmap=mmap.mmap(self.shm_def.fd, self.size)
                else:
                    try:
                        self.mmap=mmap.mmap(0, self.size, "Global\\" + self.fname)
                    except:
                        e = utils.get_exception()
                        if self.mmap is None:
                            self.mmap=mmap.mmap(0, self.size, "Local\\" + self.fname)
                        else:
                            raise e
        except:
            ex = utils.get_exception()
            try:
                self.close()
            except:
                None
            raise ex
    
    def seek(self, p):
        self.mmap.seek(p)        
    
    def tell(self):
        return self.mmap.tell()     
    
    def write(self, dt):
        self.mmap.write(dt)
        
    def read(self, sz):
        return self.mmap.read(sz)        

    def close(self):
        if not self.bclose:            
            self.bclose=True
            self._mconf=None
            serr=""
            try:
                if self.mmap is not None:
                    self.mmap.close()
                    self.mmap=None                    
            except:
                e = utils.get_exception()
                serr+="Error map close: " + utils.exception_to_string(e) + "; ";
            
            if self.ftype=="F":
                if self.file is not None:  
                    self.file.close()
                    self.file=None
            elif self.ftype=="M":
                if not utils.is_windows():
                    if self.bcreate==False:
                        self._libbase.sharedMemoryDestroy(ctypes.byref(self.shm_def))            
            if serr!="":
                raise Exception(serr)
                        
    def get_size(self):
        return self.size


class MemMapTHC():
    
    def __init__(self,size,fixperm=None):
        self.fixperm=fixperm
        self.size=size
        self.pos=0
        self.data=bytearray(self.size)
        self.lck=threading.Lock()
        self._threadsharedobjid=None

    def __del__(self):
        try:
            if self._threadsharedobjid is not None and self._threadsharedobjid in _ipcmap["threadsharedobj"]:            
                del _ipcmap["threadsharedobj"][self._threadsharedobjid]
        except:
            None
    
    def __getstate__(self):
        if self._threadsharedobjid is None: 
            self._threadsharedobjid = id(self)
            _ipcmap["threadsharedobj"][self._threadsharedobjid]=self
        return self._threadsharedobjid
    
    def __setstate__(self, state):
        pobj=_ipcmap["threadsharedobj"][state]
        self.data=pobj.data
        self.size=pobj.size
        self.fixperm=pobj.fixperm
        self.lck=pobj.lck
        self.pos=0
        

    def seek(self, p):
        self.pos=p        
    
    def tell(self):
        return self.pos     
    
    def write(self, dt):
        if isinstance(dt,ctypes.Structure):
            dt=utils.convert_struct_to_bytes(dt)        
        with self.lck:
            sz=len(dt)
            self.data[self.pos:self.pos+sz]=dt
            self.pos+=sz
        
    def read(self, sz):
        with self.lck:
            sret = utils.bytes_new(self.data[self.pos:self.pos+sz])
            self.pos+=sz
            return sret

    def close(self):
        self.data=None
        self.lck=None
                        
    def get_size(self):
        return self.size


def MemMap(size,fixperm=None):
    if is_load_libbase():
        return MemMapIPC(size,fixperm)
    else:
        return MemMapTHC(size,fixperm)


class Property():
    
    def __init__(self):
        self._semaphore = threading.Condition()
        self._binit=False
        if utils.is_py2():
            self._mmap_write = lambda s: self._mmap.write(s.encode("utf8", errors="replace"))
            self._mmap_read = lambda n: self._mmap.read(n).decode("utf8", errors="replace")
        else:
            self._mmap_write = lambda s: self._mmap.write(bytes(s, "utf8"))
            self._mmap_read = lambda n: str(self._mmap.read(n), "utf8")
            
    
    def create(self, fname, fieldsdef, fixperm=None):
        self._semaphore.acquire()
        try:
            if self._binit:
                raise Exception("Already initialized.")
            self._path = process_manager._get_property_path(fname)
            if utils.path_exists(self._path):
                if fixperm is not None:
                    fixperm(self._path)
                self.open(fname)
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
                    try:
                        utils.path_remove(self._path)
                    except:
                        raise Exception("Shared file is locked.")
                else:
                    self._binit=True
                    return
            self._fields={}
            szdata=0
            for f in fieldsdef:
                self._fields[f["name"]]={"pos":szdata,"size":f["size"]}
                szdata+=f["size"]
            shead=json.dumps(self._fields)
            self._len_def=len(shead)
            self._size=4+self._len_def+szdata
            with utils.file_open(self._path, "wb") as f:
                f.write(b" "*self._size)
            if fixperm is not None:
                fixperm(self._path)
            self._file=utils.file_open(self._path, "r+b")
            self._mmap = mmap.mmap(self._file.fileno(), 0)
            self._mmap.seek(0)
            self._mmap.write(struct.pack('!i', self._len_def))
            self._mmap.write(utils.str_to_bytes(shead))
            self._binit=True
        finally:
            self._semaphore.release()
    
    def exists(self, fname, bpath=None):
        return utils.path_exists(process_manager._get_property_path(fname, path=bpath))
    
    def open(self, fname, bpath=None):
        self._semaphore.acquire()
        try:
            if self._binit:
                raise Exception("Already initialized.")
            self._path = process_manager._get_property_path(fname, path=bpath)
            if not utils.path_exists(self._path):
                raise Exception("Shared file not found")
            self._file=utils.file_open(self._path, "r+b")
            self._mmap = mmap.mmap(self._file.fileno(), 0)
            self._mmap.seek(0)
            #Legge struttura
            self._len_def=struct.unpack('!i',self._mmap.read(4))[0]
            shead=utils.bytes_to_str(self._mmap.read(self._len_def),"utf8")
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
                except:
                    e = utils.get_exception()
                    err+="Error map close:" + utils.exception_to_string(e) + "; "
                try:
                    self._file.close()
                except:
                    e = utils.get_exception()
                    err+="Error shared file close:" + utils.exception_to_string(e) + ";"
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
                    f=self._fields[name]
                    if len(val)<=f["size"]:
                        self._mmap.seek(4+self._len_def+f["pos"])
                        appv=val + " "*(f["size"]-len(val)) 
                        self._mmap_write(appv)
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
                    f=self._fields[name]
                    self._mmap.seek(4+self._len_def+f["pos"])
                    sret = self._mmap_read(f["size"])
                    return sret.strip() 
                else:
                    raise Exception("Property " + name + " not found.")
            else:
                raise Exception("Not initialized.")
        finally:
            self._semaphore.release()


class ProcessManager(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self,name="IPCProcessManager")
        self.daemon=True                
        self._lock=threading.RLock()
        #self._list_release_obj=[]
        self._list_process=[]
        self._bdestroy=False
            
    def _get_release_path(self,name,path=None):
        if path is None:
            return IPC_PATH + utils.path_sep + name + ".rls"
        else:
            return path + utils.path_sep + IPC_PATH + utils.path_sep + name + ".rls"
    
    def _get_config_path(self,name,path=None):
        if path is None:
            return IPC_PATH + utils.path_sep + name + ".cfg"
        else:
            return path + utils.path_sep + IPC_PATH + utils.path_sep + name + ".cfg"
    
    def _get_memmap_path(self,name,path=None):
        if path is None:
            return IPC_PATH + utils.path_sep + name + ".mmp"
        else:
            return path + utils.path_sep + IPC_PATH + utils.path_sep + name + ".mmp"
    
    def _get_property_path(self,name,path=None):
        if path is None:
            return IPC_PATH + utils.path_sep + name + ".shm"
        else:
            return path + utils.path_sep + IPC_PATH + utils.path_sep + name + ".shm"
    
    
    def _destroy_process_by_shared_obj(self, obj):
        tocloselist=[]
        with self._lock:
            for prc in self._list_process:
                if prc._contains_shared_object(obj):
                    tocloselist.append(prc)
        
        for prc in tocloselist:
            try:
                prc.close()                
            except:
                e = utils.get_exception()
                print("IPC manager _destroy_process_by_shared_obj error: " + utils.exception_to_string(e))
        
    def _add_process(self, prc):
        with self._lock:
            self._list_process.append(prc)
    
    def destory(self):
        self._bdestroy=True
            
    def run(self):
        try:
            while not self._bdestroy:
                time.sleep(1)
                if is_load_libbase():
                    #CHECK PROCESS
                    remlist=[]
                    lstprcs={}
                    with self._lock:
                        lstprcs=copy.copy(self._list_process)
                        
                    for prc in lstprcs:
                        try:
                            if prc._check_close():
                                remlist.append(prc)                        
                        except:
                            e = utils.get_exception()
                            print("IPC manager process check close error: " + utils.exception_to_string(e))
                            remlist.append(prc)
                    
                    #REMOVE PROCESS
                    with self._lock:
                        for prc in remlist:
                            self._list_process.remove(prc)
                            #print("PROCES REMOVED " + str(prc))                
                
        except:
            #ex = utils.get_exception()
            #print(utils.exception_to_string(ex))
            None #Sometime shutdown error (most likely raised during interpreter shutdown) errore: <type 'exceptions.TypeError'>: 'NoneType' object is not callable
        
process_manager=ProcessManager()
    
class ProcessConfig():
    
    def __init__(self):
        #STATUS: I=Init  O=OPEN  C=CLOSE
        self.POS_STATUS_PARENT=0
        self.POS_PID_PARENT=self.POS_STATUS_PARENT+1
        self.POS_STATUS_CHILD=self.POS_PID_PARENT+4
        self.POS_PID_CHILD=self.POS_STATUS_CHILD+1
        self.POS_ALIVE_TIME=self.POS_PID_CHILD+4
        self.POS_RUN_INFO=self.POS_ALIVE_TIME+8
        self._key=None   
        self._bclose=True             
    
    def create(self, prc, fixperm=None):        
        self._bcreate=True
        self._process=prc
        self._fixperm=fixperm
        _ipcmap["semaphore"].acquire()
        try:
            while True:
                spid=str(os.getpid())
                self._key = "dwa_" + spid + "_" + _rndseq(10)
                pth = process_manager._get_config_path(self._key)
                if not os.path.exists(pth):
                    break
            with utils.file_open(pth, "wb") as f:
                f.write(utils.bytes_new())
            _fix_perm_path(pth,fixperm)
        finally:
            _ipcmap["semaphore"].release()
        with utils.file_open(pth, "r+b") as f:
            f.write(struct.pack("!cIcIQI",b"I",os.getpid(),b"I",0,int(time.time()*1000),0))
        
        self._bclose=False
    
    def open(self, key):
        self._bcreate=False
        self._process=None
        self._key=key        
        pth = process_manager._get_config_path(self._key)
        if not os.path.exists(pth):
            self._key=None
            raise Exception("File config missing.")
        pth = process_manager._get_config_path(self._key)
        with utils.file_open(pth, "r+b") as f:
            f.seek(self.POS_PID_CHILD)
            f.write(struct.pack("!I",os.getpid()))
        self._bclose=False
        
    def set_status_parent(self, s):
        pth = process_manager._get_config_path(self._key)
        with utils.file_open(pth, "r+b") as f:
            f.seek(self.POS_STATUS_PARENT)
            f.write(s)
        
    def get_status_child(self):
        pth = process_manager._get_config_path(self._key)
        with utils.file_open(pth, "r+b") as f:
            f.seek(self.POS_STATUS_CHILD)
            return f.read(1)
    
    def set_status_child(self, s):
        pth = process_manager._get_config_path(self._key)
        with utils.file_open(pth, "r+b") as f:
            f.seek(self.POS_STATUS_CHILD)
            f.write(s)            
        
    def get_pid_child(self):
        pth = process_manager._get_config_path(self._key)
        with utils.file_open(pth, "r+b") as f:
            f.seek(self.POS_PID_CHILD)
            return struct.unpack("!I",f.read(4))[0]    
    
    def get_status_parent_and_alive_time(self):
        pth = process_manager._get_config_path(self._key)
        with utils.file_open(pth, "r+b") as f:
            f.seek(self.POS_STATUS_PARENT)
            s = f.read(1)
            f.seek(self.POS_ALIVE_TIME)
            t= struct.unpack("!Q",f.read(8))[0]
            return(s,t)
    
    def set_alive_time(self):
        pth = process_manager._get_config_path(self._key)
        with utils.file_open(pth, "r+b") as f:
            f.seek(self.POS_ALIVE_TIME)
            f.write(struct.pack("!Q",int(time.time()*1000)))
    
    def set_run_info(self, oconf):
        pth = process_manager._get_config_path(self._key)
        with utils.file_open(pth, "r+b") as f:
            f.seek(self.POS_RUN_INFO+4)
            apps = _dump_obj(oconf,self._process)
            f.write(apps)
            f.seek(self.POS_RUN_INFO)
            f.write(struct.pack("!I",len(apps)))
        self._process=None            
    
    def get_run_info(self):
        pth = process_manager._get_config_path(self._key)
        with utils.file_open(pth, "r+b") as f:
            f.seek(self.POS_RUN_INFO)
            ln = struct.unpack("!I",f.read(4))[0]
            if ln>0:
                oconf=_load_obj(f.read(ln))
                f.seek(self.POS_RUN_INFO)
                f.write(struct.pack("!I",0))
                f.write(b" "*ln)
                f.flush()
                return oconf
            else:
                return {}
    
    def is_close(self):
        return self._bclose
    
    def close(self):
        if not self._bclose:
            self._bclose=True
            if self._bcreate:
                pth = process_manager._get_config_path(self._key)
                if os.path.exists(pth):
                    if utils.path_exists(pth):
                        utils.path_remove(pth)
            self._key=None
            self._process=None
    
    def get_key(self):
        return self._key

class Process():
    
    def __init__(self, pkg, cls, args=None, fixperm=None,forcesubprocess=False):
        self._process=None
        self._ppid=None
        self._pkg=pkg
        self._cls=cls
        self._args=args
        if self._args is None:
            self._args=[]
        self._fixperm=fixperm
        self._forcesubprocess=forcesubprocess
        self._stream=None
        self._binit=False
        self._bclose=False
        self._tdclose=None
        self._config=None
        self._lock=threading.RLock()
        self._list_shared_obj=[]
        self._tdchild=None
        self._py_exe_path=None
        self._py_home_path=None        
    
    def __del__(self):
        self._stream=None
        self._process=None
        self._ppid=None
    
    def _add_shared_obj(self, obj):
        with self._lock:
            self._list_shared_obj.append(obj)
            
    def _contains_shared_object(self, obj):
        with self._lock:
            if self._list_shared_obj is not None:
                return obj in self._list_shared_obj
        return False
    
    def get_fixperm(self):
        return self._fixperm
    
    def get_pid(self):
        return self._ppid
    
    def _create_process(self, args):
        if utils.is_windows() and not self._forcesubprocess:
            appcmd=u"\"" + self._py_exe_path + u"\" -S -m agent " + utils.str_new(args[2]) + u" " + utils.str_new(args[3])            
            self._process=None
            self._ppid = native.get_instance().start_process(appcmd,self._py_home_path)
            if self._ppid==-1:
                self._ppid=None
                raise Exception("Start process error")
        elif utils.is_linux():
            libenv = os.environ
            if utils.path_exists("runtime"):
                libenv["LD_LIBRARY_PATH"]=utils.path_absname("runtime/lib")
            elif "LD_LIBRARY_PATH" in os.environ:
                libenv["LD_LIBRARY_PATH"]=os.environ["LD_LIBRARY_PATH"]
            self._process=subprocess.Popen(args, env=libenv)
            self._ppid=self._process.pid
        elif utils.is_mac():
            libenv = os.environ
            if utils.path_exists("runtime"):
                libenv["DYLD_LIBRARY_PATH"]=utils.path_absname("runtime/lib")
            elif "DYLD_LIBRARY_PATH" in os.environ:
                libenv["DYLD_LIBRARY_PATH"]=os.environ["DYLD_LIBRARY_PATH"]
            self._process=subprocess.Popen(args, env=libenv)
            self._ppid=self._process.pid
        else:
            self._process=subprocess.Popen(args)
            self._ppid=self._process.pid
    
    def _start_ipc(self):
        try:
            self._config=ProcessConfig()
            self._config.create(self, self._fixperm)
            #START CHILD PROCESS
            self._py_exe_path=utils.str_new(sys.executable) 
            if utils.is_windows():
                #sys.executable don't work well with unicode path
                self._py_home_path=u""
                appth="native\\service.properties"
                if (utils.path_exists(appth)):
                    f = utils.file_open(appth, 'r', encoding='utf-8')
                    sprop = f.read()
                    f.close()
                    lns = sprop.splitlines()
                    for line in lns:
                        if line.startswith("pythonPath="):
                            self._py_exe_path=utils.str_new(line[11:])
                        elif line.startswith("pythonHome="):
                            self._py_home_path=utils.str_new(line[11:])   
                                     
            self._create_process([self._py_exe_path, u"agent.py", u"app=ipc", self._config.get_key()])
            #WAIT CHILD PROCESS
            cnt=utils.Counter()
            cnt_timeout=15
            while True:
                if not self.is_running():
                    raise Exception("Process closed (child pid).")
                try:
                    apppid=self._config.get_pid_child()
                    if apppid!=0:
                        self._ppid=apppid
                        break
                except:
                    None
                if cnt.is_elapsed(cnt_timeout):
                    raise Exception("Start process timeout")
                time.sleep(0.5)                
            
            self._stream = Stream({"fixperm":self._fixperm})
            oconf={}
            oconf["package"]=self._pkg
            oconf["class"]=self._cls
            oconf["arguments"]=self._args
            oconf["stream"]=self._stream
            oconf["aliveTime"]=time.time()
            self._config.set_run_info(oconf)
            self._config.set_status_parent(b"O")
            while True:
                if not self.is_running():
                    raise Exception("Process closed (child status).")
                try:
                    stcl=self._config.get_status_child()
                    if stcl==b"O":
                        break
                    elif stcl==b"C":
                        raise Exception("Process closed (child status).")
                except:
                    None
                if cnt.is_elapsed(cnt_timeout):
                    raise Exception("Start process timeout")
                time.sleep(0.5)
            process_manager._add_process(self)
            #print("STARTED " + str(self._ppid) + " self._cls:" + self._cls)
        except:
            ex = utils.get_exception()
            try:
                self._config.set_status_parent(b"C")
                self._config.close()
            except:
                ex1 = utils.get_exception()
                print("_start_ipc close config file - err: " + str(ex1))
            self._kill()
            if self._stream is not None:
                self._stream.close()
                self._stream=None
            raise ex    
    
    def _start_thp(self):
        try:
            self._stream = Stream()
            pkn=self._pkg.rsplit('.',1)[0]
            if pkn==self._pkg:
                pkn=None                    
            cls = self._cls
            objlib = importlib.import_module(self._pkg,pkn)
            cls = getattr(objlib, cls, None)                    
            cstrm = _load_obj(_dump_obj(self._stream, None))
            self._tdchild = cls(cstrm,self._args)
            self._tdchild.start()
        except:
            ex = utils.get_exception()
            self._tdchild=None
            if self._stream is not None:
                self._stream.close()
                self._stream=None                
            raise ex
        
    
    def start(self):
        if self._binit:
            raise Exception("Process already initialized.")
        self._binit=True
        if is_load_libbase():
            self._start_ipc()
        else:
            self._start_thp()
        return self._stream

    def is_running(self):
        if is_load_libbase():
            try:
                if self._process!=None:
                    if self._process.poll() == None:
                        return True
                    else:
                        return False
            except:
                None
            if self._ppid!=None:
                if native.get_instance().is_task_running(self._ppid):
                    return True
        elif self._tdchild is not None:
            try:
                return self._tdchild.is_alive()
            except:
                None            
        return False

    def join(self, timeout=None):
        if is_load_libbase():
            cnt=utils.Counter() 
            while self.is_running():
                if timeout is not None and cnt.is_elapsed(timeout):
                    return
                time.sleep(0.5)
            self._stream=None
            self._process=None
            self._ppid=None
        elif self._tdchild is not None:
            self._tdchild.join(timeout)
            self._stream=None
            self._tdchild=None            
    
    def close(self):
        if not self._bclose:
            self._bclose=True
            if self.is_running():
                if is_load_libbase():
                    if self._tdclose is None:
                        try:
                            if self._config is not None:
                                self._config.set_status_parent(b"C")
                        except:
                            None
                        if self._stream is not None: 
                            self._stream.close()
                            self._stream=None
                        self._tdclose=threading.Thread(target=self._close_wait, name="IPCProcessClose")
                        self._tdclose.start()
                else:
                    if self._stream is not None: 
                        self._stream.close()
                        self._stream=None
                    self._tdchild.join(2)
                    self._tdchild=None
            else:
                if self._stream is not None: 
                    self._stream.close()
                    self._stream=None
                self._process=None
                self._ppid=None   
                self._tdchild=None
        
    def _close_wait(self):
        cnt=utils.Counter() 
        while self.is_running():
            if cnt.is_elapsed(5):
                break
            time.sleep(1)
        self._kill()
    
    def _check_close(self):
        if self._config is None:
            return True
        if self.is_running():
            self._config.set_alive_time()
        else:
            self._bclose=True
            stcl=self._config.get_status_child()
            try:
                self._config.close()
            except:
                ex = utils.get_exception()
                print("_check_close config file - err: " + utils.exception_to_string(ex))
            self._config=None
            if stcl==b"C":
                with self._lock:
                    self._list_shared_obj=None                                        
            else:
                #PROCESS TERMINATED ABNORMALLY
                lstshobj=None
                with self._lock:
                    lstshobj=self._list_shared_obj
                    self._list_shared_obj=None
                #CLOSE ALL PROCESS THAT USE SHARE OBJECT
                if lstshobj is not None:
                    for i in reversed(range(len(lstshobj))):
                        try:
                            obj=lstshobj[i]
                            process_manager._destroy_process_by_shared_obj(obj)
                        except:
                            ex = utils.get_exception()
                            print("_check_close close other process shared obj:  " + str(obj) + " - err: " + utils.exception_to_string(ex))
                    #DESTROY OBJECT (RELEASE LOCKS)
                    for i in reversed(range(len(lstshobj))):
                        try:
                            obj=lstshobj[i]
                            obj._destroy()
                        except:
                            ex = utils.get_exception()
                            print("_check_close destroy shared obj:  " + str(obj) + " - err: " + utils.exception_to_string(ex))                    
            self._stream=None
            self._process=None
            self._ppid=None            
            return True
        return False

    def _kill(self):
        if self.is_running():
            if self._stream is not None:
                self._stream.close()
                self._stream=None
            if self._process!=None:
                self._process.kill()
                self._process.poll()
                time.sleep(1)
            if self._ppid!=None:
                native.get_instance().task_kill(self._ppid)
        self._process=None
        self._ppid=None
        

class ProcessInActiveConsole(Process):
        def __init__(self, mdl, func, args=None, forcesubprocess=False):
            Process.__init__(self, mdl, func, args, self._process_fix_perm, forcesubprocess)
            self._forcesubprocess=forcesubprocess
            self._currentconsole=None
            self._currentconsolecounter=utils.Counter()
            
        
        def _process_fix_perm(self):
            jo={}
            appconsole = self._currentconsole
            if (utils.is_mac() or utils.is_linux()) and appconsole!=None and "uid" in appconsole and appconsole["uid"]!=os.getuid():
                jo["mode"]=stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH
            return jo
        
        def _get_linux_envirionment(self,uid,tty):
            bwaylanderr=False
            lstret={}
            
            #DETECT BY PROCESS
            if uid!=-1:       
                lst = native.get_instance().get_process_ids()
                try:
                    bok=False
                    cnt = utils.Counter()
                    while not bok and cnt.get_value()<=2:
                        for pid in lst:
                            if native.get_instance().get_process_uid(pid)==uid:
                                lstret={}
                                arenv = native.get_instance().get_process_environ(pid)
                                for apps in arenv:                        
                                    if apps=="XAUTHORITY" or apps=="DISPLAY" or apps.startswith("WAYLAND_") or apps.startswith("XDG_") or apps.startswith("LC_") or apps.startswith("LANG"):
                                        lstret[apps]=arenv[apps]
                                        #print("DETECT BY PROCESS- " + apps + ": " + lstret[apps])                                        
                                if ("DISPLAY" in lstret and "XAUTHORITY" in lstret):                                    
                                    bok=True
                                    break
                                lstret={}
                        time.sleep(0.5)
                except:
                    lstret={}
            
            #DETECT BY WHAT OF w COMMAND
            swhatcmd=None
            if uid!=-1:            
                try:
                    import pwd
                    pwinfo=pwd.getpwuid(uid)
                    if pwinfo is not None and pwinfo.pw_name is not None:
                        data = subprocess.Popen(["w"], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
                        so, se = data.communicate()
                        if so is not None and len(so)>0:
                            so=utils.bytes_to_str(so, "utf8")
                            ar = so.split("\n")
                            del ar[0]
                            bhead=True
                            pwhat=-1
                            for s in ar:
                                if bhead:
                                    #DETECT WHAT position
                                    bhead=False
                                    pwhat = s.upper().index("WHAT")                                
                                elif pwhat>=0 and s.split(" ")[0].rstrip(" ")==pwinfo.pw_name:
                                    swhatcmd = s[pwhat:].lstrip(" ").rstrip(" ")
                                    break
                except:
                    None
            if swhatcmd is not None:
                try:
                    lst = native.get_instance().get_process_ids()
                    for pid in lst:
                        sst = native.get_instance().get_process_stat(pid)
                        if native.get_instance().get_process_uid(pid)==uid:
                            bok=False
                            lret = native.get_instance().get_process_cmdline(pid)
                            lcmd=" ".join(lret).lstrip(" ").rstrip(" ")
                            if lcmd==swhatcmd:
                                arenv = native.get_instance().get_process_environ(pid)
                                for apps in arenv:                        
                                    if apps=="XAUTHORITY" or apps=="DISPLAY" or apps.startswith("WAYLAND_") or apps.startswith("XDG_") or apps.startswith("LC_") or apps.startswith("LANG"):
                                        lstret[apps]=arenv[apps]
                                        #print("DETECT BY WHAT OF w COMMAND - " + apps + ": " + lstret[apps])
                                break
                                                
                except:
                    None
            
            #DETECT DISPLAY BY w COMMAND
            if uid!=-1:
                try:
                    import pwd
                    pwinfo=pwd.getpwuid(uid)
                    if pwinfo is not None and pwinfo.pw_name is not None:
                        data = subprocess.Popen(["w"], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
                        so, se = data.communicate()
                        if so is not None and len(so)>0:
                            so=utils.bytes_to_str(so, "utf8")
                            ar = so.split("\n")
                            del ar[0]
                            bhead=True
                            ptty=-1
                            for s in ar:
                                if bhead:
                                    #DETECT WHAT position
                                    bhead=False
                                    ptty = s.upper().index("TTY")                                
                                elif ptty>=0 and s.split(" ")[0].rstrip(" ")==pwinfo.pw_name:
                                    sdisplay = s[ptty:]
                                    sdisplay=sdisplay[0:sdisplay.index(" ")]
                                    if len(sdisplay)==2:
                                        if sdisplay[0]==":" and sdisplay[1].isdigit():
                                            sdsp=sdisplay
                                    elif len(sdisplay)==4:
                                        if sdisplay[0]==":" and sdisplay[1].isdigit() and sdisplay[2]=="." and sdisplay[3].isdigit():
                                            sdsp=sdisplay
                                    if sdsp is not None:
                                        lstret["DISPLAY"] = sdsp
                                        #print("DETECT DISPLAY BY w COMMAND - DISPLAY: " + lstret["DISPLAY"])
                                        break
                except:
                    None
            
            #DETECT BY CMDLINE
            try:
                if tty is not None:
                    st = os.stat("/dev/" + tty)
                lst = native.get_instance().get_process_ids()
                for pid in lst:
                    sst = native.get_instance().get_process_stat(pid)
                    if (tty is None or sst["tty"]==st.st_rdev) and (uid==-1 or native.get_instance().get_process_uid(pid)==uid):
                        lret = native.get_instance().get_process_cmdline(pid)
                        bok=False
                        sxauth=None
                        sdsp=None
                        for i in range(len(lret)):
                            if i==0:
                                scmd = lret[i]
                                arcmd = scmd.split("/")
                                if len(arcmd)>0:
                                    scmd=arcmd[len(arcmd)-1]
                                    if scmd.upper()=="X" or "XORG" in scmd.upper():
                                        bok=True
                                    elif scmd.upper()=="XWAYLAND":
                                        bwaylanderr=True
                            if bok:
                                sitm = lret[i]
                                if i>0 and lret[i-1]=="-auth":
                                    sxauth=sitm
                                elif len(sitm)==2:
                                    if sitm[0]==":" and sitm[1].isdigit():
                                        sdsp=sitm
                                elif len(sitm)==4:
                                    if sitm[0]==":" and sitm[1].isdigit() and sitm[2]=="." and sitm[3].isdigit():
                                        sdsp=sitm
                        if sxauth is not None:
                            lstret["XAUTHORITY"] = sxauth                            
                            #print("DETECT BY CMDLINE - XAUTHORITY: " + lstret["XAUTHORITY"])                            
                        if sdsp is not None:
                            lstret["DISPLAY"] = sdsp
                            #print("DETECT BY CMDLINE - DISPLAY: " + lstret["DISPLAY"])
                        if bok:
                            bwaylanderr=False
                            break
                
            except:
                None
            
            if bwaylanderr or (("XDG_SESSION_TYPE" in lstret) and (lstret["XDG_SESSION_TYPE"].upper()=="WAYLAND")):
                raise Exception("XWayland is not supported.")                
            
            if "DISPLAY" not in lstret:
                lstret["DISPLAY"]=":0"
                
            if "XAUTHORITY" in lstret:
                sxauth = lstret["XAUTHORITY"]
                if not os.path.exists(sxauth):
                    try:
                        p = sxauth.rindex("/")
                        if p>=0:
                            sxauthdir = sxauth[0:p]
                            os.makedirs(sxauthdir, 0o700)
                            fd = os.open(sxauth,os.O_RDWR|os.O_CREAT, 0o600)
                            os.close(fd)                                                        
                    except:
                        None
            
            if "XAUTHORITY" not in lstret and (uid!=-1 or tty is not None): 
                return self._get_linux_envirionment(-1, None)
            
            '''
            if "DISPLAY" in lstret:
                print("DISPLAY: " + lstret["DISPLAY"])
            if "XAUTHORITY" in lstret:
                print("XAUTHORITY: " + lstret["XAUTHORITY"])
            '''
            
            return lstret
        
        def _load_linux_console_info(self,appconsole):
            if appconsole is not None:
                stty=appconsole["tty"]
                #print("\n\nTTY: " + stty)
                pwinfo=None
                try:
                    import pwd
                    if os.getuid()==0 and "cktype" in appconsole and appconsole["cktype"]!="":
                        if appconsole["cktype"]=="USER_NAME":
                            pwinfo=pwd.getpwnam(appconsole["ckvalue"])
                        elif appconsole["cktype"]=="USER_ID":
                            pwinfo=pwd.getpwuid(appconsole["ckvalue"])
                    else:
                        pwinfo=pwd.getpwuid(os.getuid())
                except:
                    None
                
                appuid=-1
                libenv={}
                if pwinfo is not None:
                    #print("uid: " + str(pwinfo.pw_uid))                                    
                    appconsole["user"] = pwinfo.pw_name
                    appconsole["uid"] = pwinfo.pw_uid
                    appconsole["gid"] = pwinfo.pw_gid
                    appconsole["home"] = pwinfo.pw_dir
                    appuid=pwinfo.pw_uid
                else:
                    libenv = os.environ
                
                lstret = self._get_linux_envirionment(appuid, stty)
                for k in lstret:
                    libenv[k]=lstret[k]
                if pwinfo is not None:
                    libenv['HOME'] = appconsole["home"]
                    libenv['LOGNAME'] = appconsole["user"]
                    libenv['USER'] = appconsole["user"]
                appconsole["env"]=libenv
        
        def _fix_linux_lang(self,libenv):
            bok=False            
            if "LANG" in libenv:
                ar = libenv["LANG"].split(".")
                if len(ar)>1 and (ar[1].upper()=="UTF8" or ar[1].upper()=="UTF-8"):
                    bok=True
            if not bok:
                if "LC_ALL" in libenv:
                    ar = libenv["LC_ALL"].split(".")
                    if len(ar)>1 and (ar[1].upper()=="UTF8" or ar[1].upper()=="UTF-8"):
                        libenv["LANG"]=libenv["LC_ALL"]
                        bok=True
            if not bok:
                if "LC_NAME" in libenv:
                    ar = libenv["LC_NAME"].split(".")
                    if len(ar)>1 and (ar[1].upper()=="UTF8" or ar[1].upper()=="UTF-8"):
                        libenv["LANG"]=libenv["LC_NAME"]
                        bok=True
            if not bok:
                dlng = native.get_instance().get_utf8_lang()
                if dlng is not None:
                    libenv["LANG"]=dlng
            #print("_fix_linux_lang: " + str(libenv))            
        
        def _load_mac_console_info(self,appconsole):
            if appconsole is not None:
                pwinfo=None            
                try:
                    import pwd
                    if os.getuid()==0:
                        pwinfo=pwd.getpwuid(appconsole["uid"])
                    else:
                        pwinfo=pwd.getpwuid(os.getuid())
                except:
                    None                
                libenv = os.environ                
                if pwinfo is not None:
                    try:
                        appconsole["user"] = pwinfo.pw_name
                        appconsole["gid"] = pwinfo.pw_gid
                        appconsole["home"] = pwinfo.pw_dir
                        libenv['HOME'] = appconsole["home"]
                        libenv['LOGNAME'] = appconsole["user"]
                        libenv['USER'] = appconsole["user"]
                    except:
                        None
                appconsole["env"]=libenv
        
        def _init_process_demote(self,user_uid, user_gid):
            def set_ids():
                os.setgid(user_gid)
                os.setuid(user_uid)
            return set_ids        

        def _is_old_windows(self):
            return (utils.is_windows() and (native.get_instance().is_win_xp()==1 or native.get_instance().is_win_2003_server()==1))
        
        def is_change_console(self):
            if self._currentconsole is not None and self._currentconsolecounter.is_elapsed(1):
                self._currentconsolecounter.reset()
                appc=self._detect_console()
                if appc is not None:
                    if utils.is_windows():
                        if self._is_old_windows() and appc["id"]>0:
                            native.get_instance().win_station_connect()
                            time.sleep(1)
                            return True
                        elif appc["id"]!=self._currentconsole["id"]:
                            return True
                    elif utils.is_mac():
                        if appc["uid"]!=self._currentconsole["uid"]:
                            return True
                    elif utils.is_linux():
                        if appc["tty"]!=self._currentconsole["tty"]:
                            if appc["cktype"]=="" or appc["cktype"]!=self._currentconsole["cktype"]:
                                return True
                            else:
                                return appc["ckvalue"]!=self._currentconsole["ckvalue"]
            return False
        
        def _detect_console(self):
            if utils.is_windows():
                return {"id": native.get_instance().get_active_console_id()}            
            elif utils.is_mac():
                return {"uid": native.get_instance().get_console_user_id()}            
            elif utils.is_linux():
                try:
                    ar={}
                    stty=native.get_instance().get_tty_active()
                    if stty is not None:
                        ar["tty"] = stty
                        ar["cktype"] = ""
                        ar["ckvalue"] = ""
                        try:
                            if os.getuid()==0:
                                sbuf = None
                                offset = 0                        
                                with open('/var/run/utmp', 'rb') as fd:
                                    sbuf = fd.read()
                                if sbuf is not None:
                                    while offset < len(sbuf):
                                        arutmp = _struct_utmp.unpack_from(sbuf, offset)
                                        stype=arutmp[0]
                                        if stype==7: #USER_PROCESS
                                            appstty=utils.bytes_to_str(arutmp[2].rstrip(b'\0'),"utf8")
                                            if appstty==stty:
                                                ar["cktype"]="USER_NAME"
                                                ar["ckvalue"]=utils.bytes_to_str(arutmp[4].rstrip(b'\0'),"utf8")
                                                break                                     
                                        offset += _struct_utmp.size
                        except:
                            None
                        if ar["cktype"]=="":
                            try:    
                                st = os.stat("/dev/" + stty)
                                ar["cktype"]="USER_ID"
                                ar["ckvalue"]=st.st_uid
                            except:
                                None
                        #print("_detect_console_:" + ar["cktype"] + " " + str(ar["ckvalue"]))
                        return ar
                except:
                    None 
                
            return None
                        
        def _create_process(self, args):        
            if utils.is_windows():
                if self._forcesubprocess:
                    self._currentconsole=None
                    self._process=subprocess.Popen(args)
                    self._ppid=self._process.pid
                else:
                    '''
                    runaselevatore=u"False"
                    if self._get_screen_module().DWAScreenCaptureIsUserInAdminGroup()==1:
                        if self._get_screen_module().DWAScreenCaptureIsRunAsAdmin()==1:
                            if self._get_screen_module().DWAScreenCaptureIsProcessElevated()==1:
                                runaselevatore=u"True"
                    '''            
                    appcmd=u"\"" + self._py_exe_path + u"\" -S -m agent " + utils.str_new(args[2]) + u" " + utils.str_new(args[3]) #+ u" " + TMP_str_new(str(self._agent_main._agent_debug_mode)) + u" windows " + runaselevatore            
                    self._process=None
                    self._ppid = native.get_instance().start_process_in_active_console(appcmd,self._py_home_path)
                    if self._ppid==-1:
                        self._ppid=None
                        self._currentconsole=None
                        raise Exception("Start process error")
            elif utils.is_linux():
                bfaultback=True
                if self._currentconsole!=None and "env" in self._currentconsole:
                    try:
                        libenv=self._currentconsole["env"]
                        if utils.path_exists("runtime"):
                            libenv["LD_LIBRARY_PATH"]=utils.path_absname("runtime/lib")
                        elif "LD_LIBRARY_PATH" in os.environ:
                            libenv["LD_LIBRARY_PATH"]=os.environ["LD_LIBRARY_PATH"]
                        self._fix_linux_lang(libenv)
                        self._process=subprocess.Popen(args, env=libenv, preexec_fn=self._init_process_demote(self._currentconsole["uid"], self._currentconsole["gid"]))                        
                        self._ppid=self._process.pid
                        bfaultback=False
                    except:
                        None
                if bfaultback:
                    libenv = os.environ
                    lstret = self._get_linux_envirionment(-1, None)
                    for k in lstret:
                        libenv[k]=lstret[k]
                    if utils.path_exists("runtime"):
                        libenv["LD_LIBRARY_PATH"]=utils.path_absname("runtime/lib")
                    elif "LD_LIBRARY_PATH" in os.environ:
                        libenv["LD_LIBRARY_PATH"]=os.environ["LD_LIBRARY_PATH"]
                    self._fix_linux_lang(libenv)
                    self._process=subprocess.Popen(args, env=libenv)
                    self._ppid=self._process.pid
                    
            elif utils.is_mac():
                bfaultback=True
                self._ppid=None
                if not self._forcesubprocess:
                    if not hasattr(native.get_instance(), "is_old_guilnc") or native.get_instance().is_old_guilnc():                
                        #GUI LAUNCHER OLD VERSION 03/11/2021 (DO NOT REMOVE)
                        if self._currentconsole!=None and "uid" in self._currentconsole:
                            self._ppid=native.get_instance().exec_guilnc(self._currentconsole["uid"],"ipc",[args[3]])
                    else:
                        if self._currentconsole!=None and "env" in self._currentconsole:
                            try:
                                libenv=self._currentconsole["env"]
                                if utils.path_exists("runtime"):
                                    libenv["DYLD_LIBRARY_PATH"]=utils.path_absname("runtime/lib")
                                elif "DYLD_LIBRARY_PATH" in os.environ:
                                    libenv["DYLD_LIBRARY_PATH"]=os.environ["DYLD_LIBRARY_PATH"]
                                self._process=subprocess.Popen(args, env=libenv, preexec_fn=self._init_process_demote(self._currentconsole["uid"], self._currentconsole["gid"]))                        
                                self._ppid=self._process.pid
                                bfaultback=False
                            except:
                                None
                                                
                if self._ppid is not None:
                    self._process = None
                    bfaultback=False                                    
                if bfaultback:
                    libenv = os.environ
                    if utils.path_exists("runtime"):
                        libenv["DYLD_LIBRARY_PATH"]=utils.path_absname("runtime/lib")
                    elif "DYLD_LIBRARY_PATH" in os.environ:
                        libenv["DYLD_LIBRARY_PATH"]=os.environ["DYLD_LIBRARY_PATH"]
                    self._process=subprocess.Popen(args, env=libenv)
                    self._ppid=self._process.pid
                    
                
        def _start_ipc(self):
            try:            
                self._currentconsole=self._detect_console()
                if utils.is_linux():                
                    self._load_linux_console_info(self._currentconsole)
                elif utils.is_mac():
                    self._load_mac_console_info(self._currentconsole)
                Process._start_ipc(self)
                self._currentconsolecounter.reset()
            except:
                ex = utils.get_exception()
                self._currentconsole=None
                raise ex

class ChildProcessThread(threading.Thread):
    
    def _get_thread_name(self):
        return type(self).__name__
    
    def _on_init(self):
        None
    
    def __init__(self, strm, args):
        threading.Thread.__init__(self,  name=self._get_thread_name())
        self._stream=strm
        self._args=args
        self._destroy=False
        self._on_init()
    
    def get_stream(self):
        return self._stream
    
    def get_arguments(self):
        return self._args
    
    def is_destroy(self):
        return self._destroy or self._stream.is_closed()
    
    def destroy(self):
        self._destroy=True
        self._stream.close()

def ctrlHandler(ctrlType):    
    return 1


def fmain(args): #SERVE PER MACOS APP
    if utils.is_windows():
        try:
            #Evita che si chiude durante il logoff
            HandlerRoutine = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_uint)(ctrlHandler)
            ctypes.windll.kernel32.SetConsoleCtrlHandler(HandlerRoutine, 1)
        except:
            None
    
    #fk = args[1]
    waittm=0.5
    parentAliveTime=None
    parentAliveCounter=utils.Counter()
    parentAliveTimeout=15    
    tdchild=None 
    #oconf={}
    conf=ProcessConfig()
    try:
        conf.open(args[1])
        while ((not parentAliveCounter.is_elapsed(parentAliveTimeout)) and (tdchild is None or tdchild.is_alive())):
            appst, apptm = conf.get_status_parent_and_alive_time()
            apptm = apptm*1000.0
            if parentAliveTime is None or parentAliveTime!=apptm:
                    parentAliveTime=apptm
                    parentAliveCounter.reset()
            if tdchild is None and appst==b"O":
                oconf=conf.get_run_info()            
                pkn = oconf["package"].rsplit('.',1)[0]
                if pkn == oconf["package"]:
                    pkn=None                    
                cls = oconf["class"]
                objlib = importlib.import_module(oconf["package"],pkn)
                cls = getattr(objlib, cls, None)                    
                cstrm = oconf["stream"]
                cargs = oconf["arguments"]
                if cls is not None:
                    tdchild = cls(cstrm,cargs)
                    tdchild.start()
                    conf.set_status_child(b"O")
                    waittm=1.0
                else:
                    break                    
            if appst==b"C":
                break            
            time.sleep(waittm)           
    except:
        ex = utils.get_exception()
        print(utils.exception_to_string(ex))
    if tdchild is not None:
        try:
            tdchild.destroy()
            tdchild.join(5)
        except:
            None
    _destroy_child_shared_obj()
    if not conf.is_close():
        conf.set_status_child(b"C")
    conf.close()
    
    
     
    
