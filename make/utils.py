# -*- coding: utf-8 -*-

'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import platform
import compileall
import os
import shutil
import urllib2
import zipfile
import tarfile
import codecs
import subprocess
import json
import xml.etree.ElementTree

MAIN_URL = "https://www.dwservice.net/"

PATHDEP=".." + os.sep + "make" + os.sep + "dependencies"
PATHCORE=".." + os.sep + "core"
PATHUI=".." + os.sep + "ui"
PATHNATIVE="native"
PATHTMP="tmp"


_biswindows=(platform.system().lower().find("window") > -1)
_bislinux=(platform.system().lower().find("linux") > -1)
_bismac=(platform.system().lower().find("darwin") > -1)


def is_windows():
    return _biswindows

def is_linux():
    return _bislinux

def is_mac():
    return _bismac

def info(msg):
    print msg    

def exception_to_string(e):
    if isinstance(e, unicode) or isinstance(e, str) or len(e.message)==0:
        try:
            return unicode(e)
        except:
            return str(e)
    elif isinstance(e.message, unicode):
        return e.message;
    else:
        return unicode(e.message, errors='replace')

def remove_path(src):
    info("remove path " + src)
    if os.path.exists(src):
        shutil.rmtree(src)

def make_tmppath():
    if not os.path.exists(PATHTMP):
        os.makedirs(PATHTMP)

def init_path(pth):
    if os.path.exists(pth):
        shutil.rmtree(pth)
    os.makedirs(pth)

def download_file(url,dest):
    info("download file " + url)
    infile = urllib2.urlopen(url)
    with open(dest,'wb') as outfile:
        outfile.write(infile.read())
    
def remove_file(src):
    info("remove file " + src)
    os.remove(src)

def untar_file(src, dst):
    info("untar file " + src)
    tar = tarfile.open(src, "r:gz")
    tar.extractall(path=dst)
    tar.close()

def unzip_file(src, dst, sdir=None):
    info("unzip file " + src)
    zfile = zipfile.ZipFile(src)
    try:
        for nm in zfile.namelist():
            
            bok=True
            if sdir is not None:                    
                bok=nm.startswith(sdir)
            if bok:
                npath = dst            
                appnm = nm
                appar = nm.split("/")
                if (len(appar)>1):
                    appnm=appar[len(appar)-1]
                    appoth=nm[0:len(nm)-len(appnm)]
                    if sdir is not None:
                        appoth=appoth[len(sdir):]
                    npath+=appoth.replace("/",os.sep)
                if not os.path.exists(npath):
                    os.makedirs(npath)
                if not appnm == "":
                    npath+=appnm
                    if os.path.exists(npath):
                        os.remove(npath)
                    fd = codecs.open(npath,"wb")
                    fd.write(zfile.read(nm))
                    fd.close()
    finally:
        zfile.close()

def compile_py():
    compileall.compile_dir(PATHCORE, 0, ddir=PATHCORE)        
    compileall.compile_dir(PATHUI, 0, ddir=PATHUI)
    compileall.compile_dir(PATHUI + os.sep + "messages", 0, ddir=PATHUI + os.sep + "messages")
    compileall.compile_dir(PATHUI + os.sep + "images", 0, ddir=PATHUI + os.sep + "images")
    pth = '..'
    for f in os.listdir(pth):
        if f.startswith('app_'):
            apth=".." + os.sep +  f
            compileall.compile_dir(apth, 0, ddir=apth)

            
def system_exec(cmd,wkdir):
    scmd=cmd
    if not isinstance(scmd, str):
        scmd=" ".join(cmd)
    print "Execute: " + scmd
    p = subprocess.Popen(cmd, cwd=wkdir, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (o,e) = p.communicate()
    if not o == "":
        print "Output:\n" + o
    if not e == "":
        print "Error:\n" + e
        #return False
    return True            

def remove_from_native(mainconf):
    if is_windows():        
        if not "windows" in mainconf:
            return None
        cconf = mainconf["windows"]
    elif is_linux():
        if not "linux" in mainconf:
            return None
        cconf = mainconf["linux"]
    elif is_mac():    
        if not "mac" in mainconf:
            return None
        cconf = mainconf["mac"]
    psrc = PATHNATIVE + os.sep + cconf["outname"]
    if os.path.exists(psrc):
        os.remove(psrc)

def copy_to_native(mainconf):
    if is_windows():        
        if not "windows" in mainconf:
            return None
        cconf = mainconf["windows"]
    elif is_linux():
        if not "linux" in mainconf:
            return None
        cconf = mainconf["linux"]
    elif is_mac():    
        if not "mac" in mainconf:
            return None
        cconf = mainconf["mac"]
    
    pth=mainconf["pathdst"]
    name=cconf["outname"]
    
    if not os.path.exists(PATHNATIVE):
        os.makedirs(PATHNATIVE)
    psrc = pth + os.sep + name
    if not os.path.exists(psrc):
        raise Exception("File " + name + " not generated. Please check compilation details.")
    pdst = PATHNATIVE + os.sep + name
    if os.path.exists(pdst):
        os.remove(pdst)
    shutil.copy2(psrc, pdst)
    
    
def compile_lib(mainconf):
    
    init_path(mainconf["pathdst"])
    cflgs=""    
    lflgs=""
    if is_windows():        
        if not "windows" in mainconf:
            print "NO CONFIGURATION."
            return None
        cconf = mainconf["windows"]        
        if "cpp_compiler_flags" in cconf:
            cflgs=cconf["cpp_compiler_flags"]
        if "linker_flags" in cconf:
            lflgs=cconf["linker_flags"]
        cconf["cpp_compiler"]="g++ " + cflgs + " -DOS_WINDOWS %INCLUDE_PATH% -O3 -g3 -Wall -c -fmessage-length=0 -o \"%NAMEO%\" \"%NAMECPP%\""
        cconf["linker"]="g++ " + lflgs + " %LIBRARY_PATH% -s -static-libgcc -static-libstdc++ -municode -shared -o %OUTNAME% %SRCFILES% %LIBRARIES%"
    elif is_linux():
        if not "linux" in mainconf:
            print "NO CONFIGURATION."
            return None
        cconf = mainconf["linux"]
        if "cpp_compiler_flags" in cconf:
            cflgs=cconf["cpp_compiler_flags"]
        if "linker_flags" in cconf:
            lflgs=cconf["linker_flags"]
        cconf["cpp_compiler"]="g++ " + cflgs + " -DOS_LINUX %INCLUDE_PATH% -O3 -Wall -c -fmessage-length=0 -fPIC -MMD -MP -MF\"%NAMED%\" -MT\"%NAMEO%\" -o \"%NAMEO%\" \"%NAMECPP%\""
        cconf["linker"]="g++ " + lflgs + " %LIBRARY_PATH% -s -shared -o %OUTNAME% %SRCFILES% %LIBRARIES%"
    elif is_mac():    
        if not "mac" in mainconf:
            print "NO CONFIGURATION."
            return None
        cconf = mainconf["mac"]
        if "cpp_compiler_flags" in cconf:
            cflgs=cconf["cpp_compiler_flags"]
        if "linker_flags" in cconf:
            lflgs=cconf["linker_flags"]
        cconf["cpp_compiler"]="g++ " + cflgs + " -DOS_MAC %INCLUDE_PATH% -O3 -Wall -c -fmessage-length=0 -o \"%NAMEO%\" \"%NAMECPP%\""
        cconf["linker"]="g++ " + lflgs + " %LIBRARY_PATH% -s -dynamiclib -o %OUTNAME% %SRCFILES% %LIBRARIES% %FRAMEWORKS%"
    
    if not "libraries" in cconf or len(cconf["libraries"])==0:
        cconf ["linker"]=cconf ["linker"].replace("%LIBRARIES%", "")
    else:
        libsar=[]
        for i in range(len(cconf["libraries"])):
            libsar.append("-l" + cconf["libraries"][i])
        cconf["linker"]=cconf ["linker"].replace("%LIBRARIES%", " ".join(libsar))
        
    if not "frameworks" in cconf or len(cconf["frameworks"])==0:
        cconf["linker"]=cconf ["linker"].replace("%FRAMEWORKS%", "")
    else:
        fwksar=[]
        for i in range(len(cconf["frameworks"])):
            fwksar.append("-framework " + cconf["frameworks"][i])
        cconf["linker"]=cconf ["linker"].replace("%FRAMEWORKS%", " ".join(fwksar))
    
    srcfiles=""
    dsrc = os.listdir(mainconf["pathsrc"])
    for f in dsrc:
        if f.endswith(".cpp"):
            srcname=f
            scmd=cconf["cpp_compiler"]
            apprs=""
            if "cpp_include_paths" in cconf:
                for i in range(len(cconf["cpp_include_paths"])):
                    if i>0:
                        apprs+=" "
                    apprs+="-I\"" + os.path.abspath(cconf["cpp_include_paths"][i]) + "\""
            scmd=scmd.replace("%INCLUDE_PATH%", apprs)
            scmd=scmd.replace("%NAMED%", srcname.split(".")[0] + ".d")
            scmd=scmd.replace("%NAMEO%", srcname.split(".")[0] + ".o")
            scmd=scmd.replace("%NAMECPP%", os.path.abspath(mainconf["pathsrc"]) + os.sep + srcname)        
            if not system_exec(scmd,mainconf["pathdst"]):
                raise Exception("Compiler error.")
            srcfiles+=srcname.split(".")[0] + ".o "    
            
    scmd=cconf["linker"]
    apprs=""
    if "cpp_library_paths" in cconf:
        for i in range(len(cconf["cpp_include_paths"])):
            if i>0:
                apprs+=" "
            apprs+="-L\"" + os.path.abspath(cconf["cpp_library_paths"][i]) + "\""
    scmd=scmd.replace("%LIBRARY_PATH%", apprs)
    scmd=scmd.replace("%OUTNAME%", cconf["outname"])
    scmd=scmd.replace("%SRCFILES%", srcfiles)
    if not system_exec(scmd,mainconf["pathdst"]):
        raise Exception("Linker error.")
    return cconf
 
def xml_to_prop(s):
    prp = {}
    root = xml.etree.ElementTree.fromstring(s)
    for child in root:
        prp[child.attrib['key']] = child.text
    return prp

def get_node_url():
    contents = urllib2.urlopen(MAIN_URL + "getAgentFile.dw?name=files.xml").read();
    prp = xml_to_prop(contents)
    return prp["nodeUrl"]
    
    

def read_json_file(fn):
    appjs=None
    if os.path.exists(fn):
        f=None
        try:
            f = codecs.open(fn, 'rb', None, 'strict', 1)
            appjs = json.loads(f.read())
        except:
            None
        finally:
            if f is not None:
                f.close()
        None
    return appjs

def write_json_file(conf,fn):
    s = json.dumps(conf,fn, sort_keys=True, indent=1)
    f = codecs.open(fn, 'wb', None, 'strict', 1)
    f.write(s)
    f.close()
    
# UTILIZZATI DA DETECTINFO
def path_exists(pth):
    return os.path.exists(pth)

def file_open(filename, mode='rb', encoding=None, errors='strict', buffering=1):
    return codecs.open(filename, mode, encoding, errors, buffering)
# UTILIZZATI DA DETECTINFO

    