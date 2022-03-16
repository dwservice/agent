# -*- coding: utf-8 -*-

'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''

import json
import utils
import agent

##### TO FIX 22/09/2021
try:    
    import os
    import sys
    if sys.version_info[0]==2:
        if utils.path_exists(os.path.dirname(__file__) + os.sep + "__pycache__"):
            utils.path_remove(os.path.dirname(__file__) + os.sep + "__pycache__")
except: 
    None
##### TO FIX 22/09/2021

class LogWatch():
    
    def __init__(self, agent_main):
        self._agent_main=agent_main
    
    def _get_app_filesystem(self):
        return self._agent_main.get_app("filesystem")
    
    def has_permission(self,cinfo):
        return self._agent_main.has_app_permission(cinfo,"logwatch");
    
    def get_permission(self,cinfo):
        return self._get_app_filesystem().get_permission(cinfo, "logwatch")
    
    def check_and_replace_path(self, cinfo, path, operation, options={}):
        options["app"]="logwatch"
        return self._get_app_filesystem().check_and_replace_path(cinfo, path,  operation, options)
    
    def req_read(self, cinfo ,params):
        path = self.check_and_replace_path(cinfo, agent.get_prop(params,'path',None),  self._get_app_filesystem().OPERATION_VIEW)
        position = agent.get_prop(params,'position','')
        maxline = int(agent.get_prop(params,'position','1000'))        
        fpos = -1
        flen = utils.path_size(path)
        if  position!="":
            fpos = int(position)
            if fpos > flen:
                fpos = -1
        arl=[]
        if fpos < flen:
            bm = self._get_app_filesystem().detect_bom_file(path)
            enc=None
            if bm is not None:
                enc = bm["Name"]
            else:
                enc = None
            if enc is None:
                enc = "utf8"
            f = utils.file_open(path, 'r',  encoding=enc, errors='replace')
            try:
                if (fpos!=-1):
                    f.seek(fpos)
                while True:
                    ln = f.readline()
                    if ln=="":
                        break
                    arl.append(ln.rstrip('\n').rstrip('\r'))
                    if len(arl)>=maxline+1:
                        arl.remove(arl[0])
                if len(arl)>0:
                    arl.append("")
                fpos = f.tell()
            finally:
                f.close()
        ret={}
        ret["text"]='\n'.join(arl)
        if fpos!=-1:
            ret["position"]=str(fpos)
        return json.dumps(ret)
    