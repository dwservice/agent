# -*- coding: utf-8 -*-

'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''

import json
import utils
import agent
import shutil
import random

##### TO FIX 22/09/2021
try:
    TMP_bytes_to_str=utils.bytes_to_str
    TMP_str_to_bytes=utils.str_to_bytes
    TMP_nrange=utils.nrange
except:
    TMP_bytes_to_str=lambda b, enc="ascii": b.decode(enc, errors="replace")
    TMP_str_to_bytes=lambda s, enc="ascii": s.encode(enc, errors="replace")
    TMP_nrange=xrange
try:    
    import os
    import sys
    if sys.version_info[0]==2:        
        if utils.path_exists(os.path.dirname(__file__) + os.sep + "__pycache__"):
            utils.path_remove(os.path.dirname(__file__) + os.sep + "__pycache__")
except: 
    None
##### TO FIX 22/09/2021

class TextEditor():
    
    def __init__(self, agent_main):
        self._agent_main=agent_main
    
    def _get_app_filesystem(self):
        return self._agent_main.get_app("filesystem")
    
    def has_permission(self,cinfo):
        return self._agent_main.has_app_permission(cinfo,"texteditor")
    
    def get_permission(self,cinfo):
        return self._get_app_filesystem().get_permission(cinfo, "texteditor")
    
    def check_and_replace_path(self, cinfo, path, operation, options={}):
        options["app"]="texteditor"
        return self._get_app_filesystem().check_and_replace_path(cinfo, path, operation, options)

    def req_load(self, cinfo ,params):
        path = self.check_and_replace_path(cinfo, agent.get_prop(params,'path',None),  self._get_app_filesystem().OPERATION_VIEW)
        ret=self._read(path)
        return json.dumps(ret)
        
    def req_save(self, cinfo ,params):
        path = self.check_and_replace_path(cinfo, agent.get_prop(params,'path',None),  self._get_app_filesystem().OPERATION_EDIT, {"check_exists": False})
        self._write(path,  params)
        return None

    def _get_bom_byname(self, nm):
        for bm in self._get_app_filesystem().TEXTFILE_BOM_TYPE:
            if nm==bm["Name"]:
                return bm
        return None

    def _read(self, path):
        
        if utils.path_size(path)>2*1024*1024:
            raise Exception("File too large.")
        
        prop ={}
        enc=None
        bom=False
        text_file = utils.file_open(path, 'rb')
        try:
            bts = text_file.read()
            for bm in self._get_app_filesystem().TEXTFILE_BOM_TYPE:
                lnbm = len(bm["Data"])
                if len(bts)>=lnbm and bts[0:lnbm]==bm["Data"]:
                    enc=bm["Name"]
                    bts=bts[lnbm:] #REMOVE BOM
                    bom=True
                    break
            
            if not bom:
                enc="utf8"                
            s=TMP_bytes_to_str(bts,enc)
            endline=utils.line_sep
            if s.find("\r\n")>0:
                endline="\r\n"
            elif s.find("\n")>0:
                endline="\n"
            elif s.find("\r")>0 and s[len(s)-1]!="\r":
                endline="\r"
            
            prop["bom"]=bom
            prop["encoding"]=enc
            prop["endline"]=endline
            sret=s.splitlines()
            for i in TMP_nrange(len(sret)):
                sret[i]=sret[i].rstrip('\n').rstrip('\r')
            prop["text"] = "\n".join(sret)
        finally:
            text_file.close()
        return prop
        
        
        
    def _write(self,  path,  prop):
        if "encoding" in prop:
            enc = prop["encoding"]
        else:
            enc =  None
        if enc is None:
            enc = "utf8"
        if "endline" in prop:
            endl = prop["endline"]
        else:
            endl = utils.line_sep
        bm=None
        
        #CREA FILE TEMPORANEO
        pathtmp = None
        sprnpath=utils.path_dirname(path);    
        while True:
            r="".join([random.choice("0123456789") for x in TMP_nrange(6)])            
            pathtmp=sprnpath + utils.path_sep + "temporary" + r + ".dwstext";
            if not utils.path_exists(pathtmp):
                utils.file_open(pathtmp, 'wb').close() #Crea il file per imposta i permessi
                self._agent_main.get_osmodule().fix_file_permissions("CREATE_FILE",pathtmp)
                text_file = utils.file_open(pathtmp, 'wb')
                if "bom" in prop and prop["bom"]=='true':
                    bm = self._get_bom_byname(enc)
                    if bm is not None:
                        #Write BOM
                        text_file = utils.file_open(pathtmp, 'wb')
                        text_file.write(bm["Data"])                        
                break
        try:
            s = prop["text"]
            s = endl.join(s.split("\n"))            
            text_file.write(TMP_str_to_bytes(s,enc))
        finally:
            text_file.close()
        if utils.path_exists(path):
            if utils.path_isdir(path):
                utils.path_remove(self._tmpname)
                raise Exception("PATH is directory.")
            else:
                self._agent_main.get_osmodule().fix_file_permissions("COPY_FILE",pathtmp, path)
                utils.path_remove(path)
        shutil.move(pathtmp, path)

    
