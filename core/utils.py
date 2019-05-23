# -*- coding: utf-8 -*-
'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''

import sys
import struct
import zlib
import os
import shutil
import codecs
import subprocess
import zipfile
import platform
import traceback
import time
import base64

path_sep=os.sep
line_sep=os.linesep

_biswindows=(platform.system().lower().find("window") > -1)
_bislinux=(platform.system().lower().find("linux") > -1)
_bismac=(platform.system().lower().find("darwin") > -1)

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
            appmsg=e.message
        elif isinstance(e, unicode) or isinstance(e, str):
            appmsg=e
        else:
            try:
                appmsg=unicode(e)
            except:
                appmsg=str(e)
        try:
            if isinstance(appmsg, unicode):
                return appmsg
            elif isinstance(appmsg, str):
                return appmsg.decode("UTF8")
        except:
            return unicode(appmsg, errors='replace')
    except:
        return "Unexpected error."
    
def get_stacktrace_string():
    try:
        s = traceback.format_exc();
        if s is None:
            s=u""
        if isinstance(s, unicode):
            return s;
        else:
            try:
                return s.decode("UTF8")
            except:
                return unicode(s, errors='replace')
    except:
        return "Unexpected error."

def get_time():
    if is_windows():
        return time.clock()
    else:
        return time.time()

def unload_package(pknm):
    mdtorem=[]
    for nm in sys.modules:
        if nm.startswith(pknm):
            mdtorem.append(nm)
    for nm in mdtorem:
        del sys.modules[nm]



##############
# FILESYSTEM #
##############
def _path_fix(pth):
    if not is_linux() or isinstance(pth, str):
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
def file_open(filename, mode='rb', encoding=None, errors='strict', buffering=1):
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


############
# COMPRESS #
############
def zipfile_open(filename, mode="r", compression=zipfile.ZIP_STORED, allowZip64=False):
    return zipfile.ZipFile(_path_fix(filename),mode, compression, allowZip64)

def zlib_decompress(b):
    return Bytes(zlib.decompress(buffer(b._pydata)))

def zlib_compress(b):
    return Bytes(zlib.compress(buffer(b._pydata)))


##########
# Base64 #
##########

def base64_encode(b):
    return Bytes(base64.b64encode(buffer(b._pydata)))

def base64_decode(b):
    return Bytes(base64.b64decode(buffer(b._pydata)))

##########
# SOCKET #
##########
def socket_sendall(sock, bts, p, ln):
    sock.sendall(buffer(bts._pydata,p,ln))



########
# File #
########
def file_read(f, n):
    return Bytes(f.read(n))

def file_write(f,b):
    f.write(buffer(b._pydata))



########
# MMAP #
########
def mmap_write(mmap,bts,p,ln):
    mmap.write(buffer(bts._pydata,p,ln))

def mmap_read(mmap,sz):
    return Bytes(buffer(mmap.read(sz)))





'''
if sys.version_info[0]==3: #PYTHON 3 TODO
    def _bytes_instance(data):
        if data is None:
            return bytes()
        else:
            return bytes(data)
else:
    def _bytes_instance(data):
        if data is None:
            return bytearray()
        else:
            return bytearray(data)
'''

class Bytes():
    
    def __init__(self, data=None):
        if data is not None:
            self._pydata=bytearray(data)
        else:
            self._pydata=bytearray()
        
    def __len__(self):
        return len(self._pydata)
    
    def insert_byte(self, p, b):
        self._pydata.insert(p, b)
        
    def insert_int(self, p, i):
        self._pydata[p:p] = struct.pack("!I",i)
    
    def append_byte(self, b):
        self._pydata+=struct.pack('!B', b)[0]
    
    def append_bytes(self, bts):
        self._pydata+=bts._pydata
        
    def append_int(self, i):
        self._pydata+=struct.pack("!I",i)
        
    def append_str(self, s, enc):
        self._pydata+=bytearray(s,enc)
    
    def to_str(self, enc="utf8"):
        return self._pydata.decode(enc)
    
    def encode_base64(self):
        self._pydata=bytearray(base64.b64encode(buffer(self._pydata)))
    
    def decode_base64(self):
        self._pydata=bytearray(base64.b64decode(buffer(self._pydata)))
    
    def compress_zlib(self):
        self._pydata=bytearray(zlib.compress(buffer(self._pydata)))
    
    def decompress_zlib(self):
        self._pydata=bytearray(zlib.decompress(buffer(self._pydata)))
    
    def get_int(self):
        return struct.unpack('!i', self._pydata)[0]
    
    def new_buffer(self,p=None,l=None):
        if p is None:
            p=0
        if l is None:
            l=len(self._pydata)-p
        return Bytes(buffer(self._pydata,p,l))

    def __getitem__(self, i):
        return self._pydata[i]
               
    
