# -*- coding: utf-8 -*-
'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''

import sys
import os
import shutil
import codecs
import subprocess
import zipfile
import platform
import traceback
import time
import ctypes
import threading
import logging.handlers
import zlib
import base64

path_sep=os.sep
line_sep=os.linesep

_biswindows=(platform.system().lower().find("window") > -1)
_bislinux=(platform.system().lower().find("linux") > -1)
_bismac=(platform.system().lower().find("darwin") > -1)


def is_py2():
    return sys.version_info[0]==2

if is_py2():    
    import Queue
    import BaseHTTPServer
    import urllib
    import urlparse
    try:
        import cStringIO
        BytesIO = cStringIO.StringIO
    except ImportError:
        import StringIO
        BytesIO = StringIO.StringIO    
    try:
        import cPickle
        Pickler = cPickle.Pickler
        Unpickler = cPickle.Unpickler
    except ImportError:
        import pickle 
        Pickler = pickle.Pickler
        Unpickler = pickle.Unpickler    
    Queue = Queue.Queue
    HTTPServer = BaseHTTPServer.HTTPServer
    BaseHTTPRequestHandler = BaseHTTPServer.BaseHTTPRequestHandler
    nrange=xrange
    sys_maxsize=sys.maxint
    os_getcwd=os.getcwdu        
else:
    import queue
    import http.server
    import urllib
    import io
    import pickle 
    BytesIO = io.BytesIO    
    Pickler = pickle.Pickler
    Unpickler = pickle.Unpickler        
    Queue = queue.Queue
    HTTPServer = http.server.HTTPServer
    BaseHTTPRequestHandler = http.server.BaseHTTPRequestHandler    
    nrange=range
    sys_maxsize=sys.maxsize
    os_getcwd=os.getcwd


def is_windows():
    return _biswindows

def is_linux():
    return _bislinux

def is_mac():
    return _bismac

def exception_to_string(e):
    bamsg=False;
    try:
        if len(e.message)>0:
            bamsg=True;
    except:
        None
    try:
        appmsg=None
        if bamsg:
            appmsg=str_new(e.message)
        else:
            appmsg=str_new(e)
        return appmsg
    except:
        return u"Unexpected error."
    
def get_stacktrace_string():
    try:
        s = traceback.format_exc();
        if s is None:
            return u""
        else:
            return str_new(s)
    except:
        return u"Unexpected error (get_stacktrace_string)."

def get_exception_string(e, tx=u""):
    msg = str_new(tx)
    msg += exception_to_string(e)
    msg += u"\n" + get_stacktrace_string()
    #msg += e.__class__.__name__
    #if e.args is not None and len(e.args)>0 and e.args[0] != '':
    #        msg = e.args[0]
    return msg

def get_exception():
    try:
        ar = sys.exc_info()
        if len(ar)>1 and sys.exc_info()[1] is not None:
            return sys.exc_info()[1]
        else:
            return sys.exc_info()[0]
    except:
        return Exception("Unexpected error (get_exception).")


if is_windows():
    if is_py2():
        get_time=time.clock        
    else:
        get_time=time.perf_counter
else:
    get_time=time.time

def unload_package(pknm):
    mdtorem=[]
    for nm in sys.modules:
        if nm.startswith(pknm):
            mdtorem.append(nm)
    for nm in mdtorem:
        del sys.modules[nm]

def convert_bytes_to_structure(st, byte):
    ctypes.memmove(ctypes.addressof(st), byte, ctypes.sizeof(st))

def convert_struct_to_bytes(st):
    bf = ctypes.create_string_buffer(ctypes.sizeof(st))
    ctypes.memmove(bf, ctypes.addressof(st), ctypes.sizeof(st))
    return bf.raw

##########
# BUFFER #
##########
if is_py2():
    buffer_new=lambda o, p, l: buffer(o,p,l)        
else:
    buffer_new=lambda o, p, l: memoryview(o)[p:p+l]    


#########
# BYTES #
#########
if is_py2():    
    bytes_new=str
    bytes_join=lambda ar: "".join(ar)
    bytes_get=lambda b, i: ord(b[i])
    bytes_to_str_hex=lambda s: s.encode('hex')            
else:
    bytes_new=bytes
    bytes_join=lambda ar: b"".join(ar)
    bytes_get=lambda b, i: b[i]
    bytes_to_str_hex=bytes.hex
bytes_to_str=lambda b, enc="ascii": b.decode(enc, errors="replace")


#######
# STR #
#######
if is_py2():
    def _py2_str_new(o):
        if isinstance(o, unicode):
            return o 
        elif isinstance(o, str):
            return o.decode("utf8", errors="replace")
        else:
            return str(o).decode("utf8", errors="replace")
    str_new=_py2_str_new
    str_is_unicode=lambda s: isinstance(s, unicode) #TO REMOVE
    str_hex_to_bytes=lambda s: s.decode('hex')
else:
    str_new=str
    str_is_unicode=lambda s: isinstance(s, str) #TO REMOVE
    str_hex_to_bytes=bytes.fromhex
str_to_bytes=lambda s, enc="ascii": s.encode(enc, errors="replace")

#######
# URL #
#######
if is_py2():    
    url_parse=urlparse.urlparse
    url_parse_quote_plus=urllib.quote_plus
    url_parse_quote=urllib.quote
    url_parse_qs=urlparse.parse_qs        
else:    
    url_parse=urllib.parse.urlparse
    url_parse_quote_plus=urllib.parse.quote_plus
    url_parse_quote=urllib.parse.quote
    url_parse_qs=urllib.parse.parse_qs
    

##############
# FILESYSTEM #
##############
def _path_fix(pth):
    if not is_py2() or not is_linux() or isinstance(pth, str):
        return pth
    else:
        return pth.encode('utf-8')
            
def path_exists(pth):
    return os.path.exists(_path_fix(pth))

def path_isdir(pth):
    return os.path.isdir(_path_fix(pth))

def path_isfile(pth):
    return os.path.isfile(_path_fix(pth))

def path_makedirs(pth):
    os.makedirs(_path_fix(pth))

def path_makedir(pth):
    os.mkdir(_path_fix(pth))

def path_remove(pth):
    apppt=_path_fix(pth)
    if os.path.isdir(apppt):
        shutil.rmtree(apppt)
    else:
        os.remove(apppt)        

def path_list(pth):
    return os.listdir(_path_fix(pth))

def path_walk(pth):
    return os.walk(_path_fix(pth))

def path_islink(pth):    
    return os.path.islink(_path_fix(pth))
          
def path_readlink(pth):        
    return os.readlink(_path_fix(pth))

def path_symlink(pths,pthd):
    os.symlink(_path_fix(pths), _path_fix(pthd))

def path_copy(pths,pthd):
    shutil.copy2(_path_fix(pths), _path_fix(pthd))
    
def path_move(pths,pthd):
    shutil.move(_path_fix(pths), _path_fix(pthd))

def path_rename(pths,pthd):
    os.rename(_path_fix(pths), _path_fix(pthd))

def path_change_permissions(pth, prms):
    os.chmod(_path_fix(pth),  prms)

def path_change_owner(pth, uid, gid):
    os.chown(_path_fix(pth), uid, gid)

def path_dirname(pth):
    return os.path.dirname(pth)

def path_basename(pth):
    return os.path.basename(pth)

def path_absname(pth):
    return os.path.abspath(pth)

def path_realname(pth):
    return os.path.realpath(pth)

def path_expanduser(pth):
    return os.path.expanduser(pth)

def path_size(pth):
    return os.path.getsize(_path_fix(pth))

def path_time(pth):
    return os.path.getmtime(_path_fix(pth))

def path_stat(pth):
    return os.stat(_path_fix(pth))

########
# FILE #
########
if is_py2():
    def file_open(filename, mode='rb', encoding=None, errors='strict', buffering=1):
        return codecs.open(_path_fix(filename), mode, encoding, errors, buffering)
else:
    def file_open(filename, mode='r', encoding=None, errors='strict', buffering=-1):
        return codecs.open(_path_fix(filename), mode, encoding, errors, buffering)

##########
# SYSTEM #
##########
def system_changedir(pth):
    os.chdir(_path_fix(pth))

def system_call(*popenargs, **kwargs):
    lst = list(popenargs)
    for i in range(len(lst)):
        lst[i]=_path_fix(popenargs[i])
    return subprocess.call(*lst,**kwargs)


###########
# ENCODER #
###########
if is_py2():    
    enc_base64_encode=lambda b: base64.b64encode(buffer(b))
    enc_base64_decode=lambda b: base64.b64decode(buffer(b))    
else:
    enc_base64_encode=lambda b: base64.b64encode(b)
    enc_base64_decode=lambda b: base64.b64decode(b)
    

############
# COMPRESS #
############
def zipfile_open(filename, mode="r", compression=zipfile.ZIP_STORED, allowZip64=False):
    return zipfile.ZipFile(_path_fix(filename),mode, compression, allowZip64)

if is_py2():    
    zlib_decompress=lambda b: zlib.decompress(buffer(b))
    zlib_compress=lambda b: zlib.compress(buffer(b))
else:
    zlib_decompress=lambda b: zlib.decompress(b)
    zlib_compress=lambda b: zlib.compress(b)


##########
# SOCKET #
##########
def socket_sendall(sock, bts):
    count = 0
    amount = len(bts)
    v = sock.send(bts)
    count += v
    while (count < amount):
        v = sock.send(buffer_new(bts,count,amount-count))
        count += v


LOGGER_INFO=logging.INFO
LOGGER_WARN=logging.WARN
LOGGER_CRITICAL=logging.CRITICAL
LOGGER_FATAL=logging.FATAL
LOGGER_DEBUG=logging.DEBUG
LOGGER_ERROR=logging.ERROR

class LoggerStdRedirect(object):
    
    def __init__(self,lg,lv):
        self._logger = lg;
        self._level = lv;
        
    def write(self, data):
        for line in data.rstrip().splitlines():
            self._logger.log(self._level, line.rstrip())
    
    def flush(self):
        None


class Logger():
    
    def __init__(self, conf):
        self._logger = logging.getLogger()
        if "filename" in conf:
            hdlr = logging.handlers.RotatingFileHandler(conf["filename"], 'a', 1000000, 3)
        else:
            hdlr = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        hdlr.setFormatter(formatter)
        self._logger.addHandler(hdlr) 
        self._logger.setLevel(logging.INFO)
        #Reindirizza stdout e stderr
        sys.stdout=LoggerStdRedirect(self._logger,logging.DEBUG)
        sys.stderr=LoggerStdRedirect(self._logger,logging.ERROR)
        self._lock = threading.Lock()

    def set_level(self, lv):
        self._logger.setLevel(lv)
    
    def write(self, lv, msg):
        self._lock.acquire()
        try:
            ar = []
            ar.append(str_new(threading.current_thread().name))
            ar.append(str_new(u" "))
            ar.append(str_new(msg))
            self._logger.log(lv, u"".join(ar))
        except:
            e=get_exception()
            print(exception_to_string(e))
        finally:
            self._lock.release()

class DebugProfile():

    def __init__(self, writeobj, conf):
        self._write_obj=writeobj
        self._debug_path = conf["debug_path"]
        self._debug_indentation_max=conf["debug_indentation_max"]
        self._debug_thread_filter=conf["debug_thread_filter"]
        self._debug_class_filter=conf["debug_class_filter"]
        self._debug_info = {}
    
    def _trunc_msg(self, msg, sz):
        smsg="None"
        if msg is not None:
            smsg=u""
            try:
                smsg = str_new(msg)
            except:
                e = get_exception()
                smsg = u"EXCEPTION:" + exception_to_string(e)
            if len(smsg)>sz:
                smsg=smsg[0:sz] + u" ..."
            smsg = smsg.replace("\n", " ").replace("\r", " ").replace("\t", "   ")
        return smsg
    
    def _filter_check(self,nm,flt):
        if flt is not None:
            ar = flt.split(";")
            for f in ar:
                if f.startswith("*") and nm.endswith(f[1:]):
                    return True
                elif f.endswith("*") and nm.startswith(f[0:len(f)-1]):
                    return True
                elif nm==f:
                    return True
            return False
        return False
    
    def get_function(self, frame, event, arg): 
        #sys._getframe(0)
        if event == "call" or event == "return":
            try:
                bshow = True
                fcode = frame.f_code
                flocs = frame.f_locals
                fn = path_absname(str_new(fcode.co_filename))
                if not fcode.co_name.startswith("<") and fn.startswith(self._debug_path):
                    fn = fn[len(self._debug_path):]
                    fn = fn.split(".")[0]
                    fn = fn.replace(path_sep,".")
                    nm = fcode.co_name
                    if flocs is not None and "self" in flocs:
                        flocssf=flocs["self"]
                        nm = flocssf.__class__.__name__ + "." +nm
                    nm=fn + u"." + nm
                    thdn = threading.current_thread().name
                    if thdn not in self._debug_info:
                        self._debug_info[thdn]={}
                        self._debug_info[thdn]["time"]=[]
                        self._debug_info[thdn]["indent"]=0
                    debug_time=self._debug_info[thdn]["time"]
                    debug_indent=self._debug_info[thdn]["indent"]
                    bshow=self._debug_indentation_max==-1 or debug_indent<=self._debug_indentation_max
                    #THREAD NAME
                    if bshow:
                        bshow=self._filter_check(thdn, self._debug_thread_filter)
                    #CLASS NAME
                    if bshow:
                        bshow=self._filter_check(nm, self._debug_class_filter)
                    #VISUALIZZA
                    if bshow:
                        if event == "return":
                            debug_indent -= 1
                        soper=""
                        arpp = []
                        if event == "call":
                            soper="INIT"
                            debug_time.append(int(time.time() * 1000))
                            if flocs is not None:
                                sarg=[]
                                for k in flocs:
                                    if not k == "self":
                                        sarg.append(str_new(k) + u"=" + self._trunc_msg(flocs[k], 20))
                                if len(sarg)>0:
                                    arpp.append(u"args: " + u",".join(sarg))
                            
                        elif event == "return":
                            soper="TERM"
                            tm = debug_time.pop()
                            arpp.append(u"time: " + str(int(time.time() * 1000) - tm) + u" ms")
                            arpp.append(u"return: " + self._trunc_msg(arg, 80))
                                
                        armsg=[]
                        armsg.append(u"   "*debug_indent + nm + u" > " + soper)
                        if len(arpp)>0:
                            armsg.append(u" ")
                            armsg.append(u"; ".join(arpp))
                        self._write_obj.write_debug(u"".join(armsg))
                        if event == "call":
                            debug_indent += 1
                        self._debug_info[thdn]["indent"]=debug_indent
            except:
                e = get_exception()
                self._write_obj.write_except(e)


class Counter:
    
    def __init__(self, v=None):
        self._current_elapsed = 0
        self._current_time = get_time()
        self._time_to_elapsed=v
        self._stopped=False

    def start(self):
        if self._stopped:
            self._current_time = get_time()
            self._stopped=False
    
    def stop(self):
        if not self._stopped:
            self._stopped=True

    def reset(self):
        self._current_elapsed = 0
        self._current_time = get_time()
    
    def is_elapsed(self, v=None):
        if v is None:
            v=self._time_to_elapsed
        return self.get_value()>=v
   
    def get_value(self):
        if self._stopped:
            return self._current_elapsed
        apptm=get_time()
        elp=apptm-self._current_time
        if elp>=0:
            self._current_elapsed+=elp
            self._current_time=apptm
        else:
            self._current_time=get_time()
        #print("self._current_elapsed(" + str(self) + "): " +  str(self._current_elapsed))
        return self._current_elapsed




