# -*- coding: utf-8 -*-

'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''

import locale
import subprocess
import utils
import threading
import importlib

class ResText:
    
    def __init__(self, pkgnm):
        if utils.path_exists(".srcmode"):
            self._pkgnm = pkgnm.split(".")[1]
        else:
            self._pkgnm=pkgnm
        self._data_default = self._get_data("default")
        self._lang_current = None
        self._data_current = None
        self._semaphore=threading.Condition()

    def _get_data(self,lng):
        try:
            if lng is None or lng=="":
                return None
            arlng = lng.split("_")
            testlng=""
            for i in range(len(arlng)):
                if i==0:
                    arlng[i]=arlng[i].lower()
                    testlng=arlng[i]
                else:
                    arlng[i]=arlng[i].upper()
                    testlng+="_" + arlng[i]            
            objlib = importlib.import_module(self._pkgnm + "." + lng)
            if objlib is None:
                raise Exception("Not found.")
            return getattr(objlib, 'data', None)
        except:
            arlng = lng.split("_")
            if len(arlng)>1:
                testlng=""
                for i in range(len(arlng)-1):
                    if i>0:
                        testlng+="_"
                    testlng+=arlng[i]
                return self._get_data(testlng)
            else:
                return None

    def set_locale(self, lng):
        self._semaphore.acquire()
        try:
            self._set_locale(lng)
        finally:
            self._semaphore.release()
    
    def _set_locale(self, lng):
        appdt = self._get_data(lng)
        if appdt is not None:
            self._lang_current=lng
            self._data_current=appdt
        else:
            self._lang_current="default"
            self._data_current=self._data_default
            
    def get(self, key):
        try:
            self._semaphore.acquire()
            try:
                if self._lang_current is None:
                    applng=None
                    try:
                        if utils.is_windows():
                            import ctypes
                            windll = ctypes.windll.kernel32
                            windll.GetUserDefaultUILanguage()
                            wl = locale.windows_locale[windll.GetUserDefaultUILanguage()]
                            applng=wl.split("_")[0]
                        elif utils.is_mac():
                            p = subprocess.Popen(['defaults', 'read', '-g', 'AppleLocale'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                            sout, serr = p.communicate()
                            if sout is not None:
                                applng = sout.replace("\n","").replace(" ","_")[:10]
                    except:
                        None                    
                    try:
                        if applng is None:
                            l = locale.getdefaultlocale()
                            if l is not None:
                                applng=l[0]
                    except:
                        None
                    
                    self._set_locale(applng)
                    
            finally:
                self._semaphore.release()
            
            if key in self._data_current:
                return self._data_current[key]
            elif key in self._data_default:
                return self._data_default[key]
            else:
                return "RES_MISSING#" + key
        except:
            return "RES_ERROR#" + key
    
class ResImage:
    
    def __init__(self, pkgnm):
        if utils.path_exists(".srcmode"):
            self._pkgnm = pkgnm.split(".")[1]
        else:
            self._pkgnm=pkgnm        
        self._basepth=unicode(self._pkgnm.replace(".",utils.path_sep))
        
    def get(self, nm):
        
        return self._basepth + utils.path_sep + unicode(nm)
        
        