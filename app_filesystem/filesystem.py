# -*- coding: utf-8 -*-

'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''

import json
import agent
import re
import utils
import ctypes
import native

class FileSystem():
    
    OPERATION_VIEW='VIEW'
    OPERATION_EDIT='EDIT'
    OPERATION_DOWNLOAD='DOWNLOAD'
    OPERATION_UPLOAD='UPLOAD'
    
    TEXTFILE_BOM_TYPE = [
                {"Name":"UTF-8",  "Data": "\xef\xbb\xbf"}, 
                {"Name":"UTF-16BE",  "Data":"\xfe\xff"}, 
                {"Name":"UTF-16LE",  "Data":"\xff\xfe"}, 
                {"Name":"UTF-32BE",  "Data":"\x00\x00\xfe\xff"}, 
                {"Name":"UTF-32LE",  "Data":"\xff\xfe\x00\x00"}, 
                {"Name":"UTF-7",  "Data":"\x2b\x2f\x76"}, 
                {"Name":"UTF-1",  "Data":"\xf7\x64\x4c"}, 
                {"Name":"UTF-EBCDIC",  "Data":"\xdd\x73\x66\x73"}, 
                {"Name":"UTF-SCSU",  "Data":"\x0e\xfe\xff"}, 
                {"Name":"UTF-BOCU1",  "Data":"\xfb\xee\x28"}, 
                {"Name":"UTF-GB-18030",  "Data":"\x84\x31\x95\x33"},
            ]
    
    
    def __init__(self, agent_main):
        self._agent_main=agent_main
        if utils.is_windows():
            self._osnative = Windows(self._agent_main)
        elif utils.is_linux():
            self._osnative = Linux()
        elif utils.is_mac():
            self._osnative = Mac()
    
    def destroy(self,bforce):
        if self._osnative is not None:
            self._osnative.destroy()
            self._osnative = None
        return True
        
    def detect_bom_file(self, path):
        enc=None
        text_file = utils.file_open(path, 'rb')
        try:
            s = text_file.read(10)
            for bm in self.TEXTFILE_BOM_TYPE :
                if s.startswith(bm["Data"]):
                    enc=bm
                    break
        finally:
            text_file.close()
        return enc;
    
    def has_permission(self,cinfo):
        b = self._agent_main.has_app_permission(cinfo,"filesystem") or self._agent_main.has_app_permission(cinfo,"texteditor") or self._agent_main.has_app_permission(cinfo,"logwatch");
        return b
    
    def get_permission(self,cinfo,appnm="filesystem"):
        pret = None
        prms = cinfo.get_permissions()
        if prms["fullAccess"]:
            pret={"name":appnm,"fullAccess": True}
        else:
            pret=self._agent_main.get_app_permission(cinfo,appnm)
        return pret;
    
    def get_permission_path(self, cinfo, path, options={}):
        appnm="filesystem"
        if "app" in options:
            appnm = options["app"]
        
        #NEL CASO DI #FILESYSTEM:// POTREBBE CORRISPONDERE A PIU' PATH ES. /a/b/c puo' corrispondere agli alias dei path /a/ e a /b/
        #quindi provo tutti i path
        pathstocheck=[]
        apppath=path
        if apppath.startswith("#FILESYSTEM://"):
            path=path[14:]
            apppath=path
            if appnm!="filesystem":
                bcheck=True
                fsprms=self.get_permission(cinfo)
                if fsprms is not None:
                    if not fsprms["fullAccess"]:
                        ar = apppath.split(utils.path_sep);
                        name=ar[0];
                        bcheck=False
                        for permpt in fsprms["paths"]:
                            nm = permpt["name"]
                            if name==nm:
                                pt = permpt["_path"]
                                if pt.endswith(utils.path_sep):
                                    pt=pt[:len(pt)-1]
                                apppath = apppath[len(name):];
                                apppath= pt + apppath
                                bcheck=True
                                break
                    #SOSTITUISCE L'alias
                    if bcheck:
                        prms=self.get_permission(cinfo,appnm)
                        if prms is not None:
                            if not prms["fullAccess"]:
                                for permpt in prms["paths"]:
                                    pt = permpt["_path"]
                                    if not pt.endswith(utils.path_sep):
                                        pt=pt+utils.path_sep
                                    if self._osnative.pathStartswith(apppath,pt):
                                        pathstocheck.append(permpt["name"] + utils.path_sep + apppath[len(pt):]) 
                            else:
                                pathstocheck.append(apppath)
            else:
                pathstocheck.append(path)
        else:
            pathstocheck.append(path)

        pathsret=[]
        #Verifica permessi
        prms=self.get_permission(cinfo,appnm)
        if prms is not None:
            for apppath in pathstocheck:
                itmpth={}
                itmpth["alias"]=apppath
                itmpth["allow_view"]=True
                if not prms["fullAccess"]:
                    ar = apppath.split(utils.path_sep);
                    name=ar[0];
                    for permpt in prms["paths"]:
                        nm = permpt["name"]
                        if (name==nm):
                            pt = permpt["_path"]
                            if pt.endswith(utils.path_sep):
                                pt=pt[:len(pt)-1]
                            apppath = apppath[len(name):];
                            apppath= pt + apppath
                            itmpth["name"]=apppath
                            #Verifica i permessi
                            itmpth["allow_edit"]=False
                            if "edit" in permpt:
                                itmpth["allow_edit"]=permpt["edit"]
                            elif "default_allow_edit" in options:
                                itmpth["allow_edit"]=options["default_allow_edit"]
                            itmpth["allow_download"]=False
                            if "download" in permpt:
                                itmpth["allow_download"]=permpt["download"]
                            elif "default_allow_download" in options:
                                itmpth["allow_download"]=options["default_allow_download"]
                            itmpth["allow_upload"]=False
                            if "upload" in permpt:
                                itmpth["allow_upload"]=permpt["upload"]
                            elif "default_allow_upload" in options:
                                itmpth["allow_upload"]=options["default_allow_download"]
                            pathsret.append(itmpth)
                            
                else:
                    itmpth["name"]=apppath
                    itmpth["allow_edit"]=True
                    itmpth["allow_download"]=True
                    itmpth["allow_upload"]=True
                    pathsret.append(itmpth)
                        
        return pathsret
    
    def check_and_replace_path(self, cinfo, path, operation, options={}) :
        if path is None:
            raise Exception("Path is none")
        sret=None
        paths = self.get_permission_path(cinfo, path, options)
        for itmpth in paths:
            if operation==self.OPERATION_VIEW and itmpth["allow_view"]:
                sret = itmpth["name"]
                break
            elif operation==self.OPERATION_EDIT and itmpth["allow_edit"]:
                sret = itmpth["name"]
                break
            elif operation==self.OPERATION_DOWNLOAD and itmpth["allow_download"]:
                sret = itmpth["name"]
                break
            elif operation==self.OPERATION_UPLOAD and itmpth["allow_upload"]:
                sret = itmpth["name"]
                break             
            
        if sret is None:
            raise Exception("Permission denied.\nOperation: " + operation + "\nPath: " + path);
        #Verifica se esiste il path
        check_exists=True
        if "check_exists" in options:
            check_exists = options["check_exists"]
        if check_exists and not utils.path_exists(sret):
            raise Exception("Permission denied or read error.");
        return sret
    
    
    def get_osnative(self):
        return self._osnative;
    
    def _append_to_list(self, arret, fpath,  fname):
        fp = fpath + utils.path_sep + fname
        tp = None
        itm = {}
        if utils.path_isdir(fp) == True:
            tp="D"
        else:
            tp="F"
            try:
                itm["Length"]=utils.path_size(fp)
            except:
                None
        itm["Name"] = tp + ':' + fname 
        try:
            itm["LastModified"] = long(utils.path_time(fp)*1000)
        except:
                None
                
        finfo = self._osnative.get_file_permissions(fp)
        if "Rights" in finfo:
            itm["Rights"] = finfo["Rights"]
        if "Owner" in finfo:
            itm["Owner"] = finfo["Owner"]
        if "Group" in finfo:
            itm["Group"] = finfo["Group"]
        arret.append(itm)
            
    def req_list(self, cinfo ,params):
        path = agent.get_prop(params,'path',None)
        
        
        only_dir = agent.str2bool(agent.get_prop(params, "onlyDir", "false"))
        only_file = agent.str2bool(agent.get_prop(params, "onlyFile", "false"))
        app_name=agent.get_prop(params, "app")
        #image_info = agent.str2bool(agent.get_prop(params, "imageInfo", "false"))
        
        
        ptfilter = agent.get_prop(params, "filter", None)
        ptfilter_ignorecase = agent.str2bool(agent.get_prop(params, "filterIgnoreCase", "false"))
        ptfilterList= agent.get_prop(params, "filterList", None)
        refilter = None
        if ptfilter is not None:
            if ptfilter_ignorecase:
                refilter = re.compile(ptfilter)
            else:
                refilter = re.compile(ptfilter,re.IGNORECASE)
        arfilterList = None
        if ptfilterList is not None:
            arfilterList = json.loads(ptfilterList)
        
        arret=[]
        if path=="$":
            if app_name is None:
                prms=self.get_permission(cinfo);
            else:
                prms=self.get_permission(cinfo,app_name);
            if prms["fullAccess"]:
                ar = self._osnative.get_resource_path()
                for i in range(len(ar)):
                    itm={}
                    app=ar[i]
                    itm["Name"]=u"D:" + app["Name"];
                    if "Size" in app:
                        itm["Length"]=app["Size"];
                    arret.append(itm)
            else:
                for permpt in prms["paths"]:
                    arret.append({'Name': 'D:' + permpt["name"]})
                    
        else:
            lst=None            
            options={}
            if app_name is not None:
                options["app"]=app_name
            pdir =self.check_and_replace_path(cinfo, path, self.OPERATION_VIEW,options)
            if not utils.path_isdir(pdir):
                raise Exception("Permission denied or read error.");
            try:
                lst=utils.path_list(pdir)
            except Exception:
                raise Exception("Permission denied or read error.");
            #Carica la lista
            for fname in lst:
                #DA GESTIRE COSI EVITA GLI ERRORI MA PER FILENAME NON UTF8 NON RECUPERA ALTRE INFO TIPO LA DIMENSIONE E DATAMODIFICA
                if not isinstance(fname, unicode):
                    fname=fname.decode("utf8","replace")
                
                if pdir==utils.path_sep:
                    fp = pdir + fname
                else:
                    fp = pdir + utils.path_sep + fname
                if (self._osnative.is_file_valid(fp)) and ((not only_dir and not only_file) or (only_dir and utils.path_isdir(fp)) or (only_file and not utils.path_isdir(fp))):
                    bok = True
                    if refilter is not None:
                        bok = refilter.match(fname);
                    if bok and arfilterList is not None:
                        for appnm in arfilterList:
                            bok = False
                            if ptfilter_ignorecase:
                                bok = (fname.lower()==appnm.lower())
                            else:  
                                bok = (fname==appnm)
                            if bok:
                                break
                    if bok is True:
                        self._append_to_list(arret, pdir, fname)
                        # if (image_info==True): DA GESTIRE Width e Height  se file di tipo Immagini

        #ORDINA PER NOME
        arret = sorted(arret, key=lambda k: k['Name'].lower())
         
        jsret = {'items' : arret, 'permissions': {"apps":{}}}
        if path!="$" and app_name is None:
            a = jsret["permissions"]["apps"]
            paths = self.get_permission_path(cinfo, u"#FILESYSTEM://" + path, {"app":"texteditor" ,"check_exists": False})
            if len(paths)>0:
                a["texteditor"]={}
            paths = self.get_permission_path(cinfo, u"#FILESYSTEM://" + path, {"app":"logwatch" ,"check_exists": False})
            if len(paths)>0:
                a["logwatch"]={}
            
            None
         
        return json.dumps(jsret)
  
    def req_remove(self, cinfo ,params):
        path = self.check_and_replace_path(cinfo, agent.get_prop(params,'path',None), self.OPERATION_EDIT)
        files = agent.get_prop(params,'files',None)

        arfiles = json.loads(files)
        arret=[]
        for i in range(len(arfiles)):
            fp = path + arfiles[i]
            b = True
            try:
                utils.path_remove(fp)
            except Exception:
                b=False            
            tp = None
            if b is True:
                tp="K"
            else:
                tp="E"
            arret.append({'Name': tp + ":" + arfiles[i]})
        return json.dumps({'items' : arret})
    
    
    def _cpmv(self, tp, fs, fd, replace):
        bok = True
        if utils.path_isdir(fs):
            if not utils.path_exists(fd):
                utils.path_makedirs(fd)
                if tp=="copy":
                    self._agent_main.get_osmodule().fix_file_permissions("COPY_DIRECTORY",fd, fs)
                elif tp=="move":
                    self._agent_main.get_osmodule().fix_file_permissions("MOVE_DIRECTORY",fd, fs)
            lst=None
            try:
                lst=utils.path_list(fs)
                for fname in lst:
                    b = self._cpmv(tp, fs + utils.path_sep + fname, fd + utils.path_sep + fname, replace)
                    if bok is True:
                        bok = b
            except Exception:
                bok=False
            if tp=="move":
                try:
                    utils.path_remove(fs)
                except Exception:
                    bok=False
        else:
            b=True
            if utils.path_exists(fd):
                if replace is True:
                    try:
                        utils.path_remove(fd)
                    except Exception:
                        bok = False
                        b = False
                else:
                    b = False
            if b is True:
                try:
                    if tp=="copy":
                        utils.path_copy(fs, fd)
                        self._agent_main.get_osmodule().fix_file_permissions("COPY_FILE",fd, fs)
                    elif tp=="move":
                        utils.path_move(fs, fd)
                        self._agent_main.get_osmodule().fix_file_permissions("MOVE_FILE",fd)
                except Exception:
                    bok=False
        return bok
        
    def req_copy(self, cinfo ,params):
        pathsrc = self.check_and_replace_path(cinfo, agent.get_prop(params,'pathsrc',None),  self.OPERATION_EDIT)
        pathdst = self.check_and_replace_path(cinfo, agent.get_prop(params,'pathdst',None),  self.OPERATION_EDIT)
        files = agent.get_prop(params,'files',None)
        replace = agent.str2bool(agent.get_prop(params, "replace", "false"))

        arfiles = json.loads(files)
        arret=[]
        for i in range(len(arfiles)):
            nm = arfiles[i]
            fs = pathsrc + nm
            fd = pathdst + nm
            cnt = 0
            if fs==fd:
                while utils.path_exists(fd):
                    cnt+=1
                    nm = "copy " + str(cnt) + " of " + arfiles[i];
                    fd = pathdst + nm
            b = True
            if not fs==fd and fd.startswith(fs + utils.path_sep):
                b = False
            else:
                b = self._cpmv("copy", fs, fd, replace);
            if b is True:
                self._append_to_list(arret, pathdst, nm)
            else:
                arret.append({'Name': "E:" + nm})
            
        return json.dumps({'items' : arret})
    
    def req_move(self, cinfo ,params):
        pathsrc = self.check_and_replace_path(cinfo, agent.get_prop(params,'pathsrc',None), self.OPERATION_EDIT)
        pathdst = self.check_and_replace_path(cinfo, agent.get_prop(params,'pathdst',None), self.OPERATION_EDIT)
        files = agent.get_prop(params,'files',None)
        replace = agent.str2bool(agent.get_prop(params, "replace", "false"))

        arfiles = json.loads(files)
        arret=[]
        for i in range(len(arfiles)):
            nm = arfiles[i]
            fs = pathsrc + nm
            fd = pathdst + nm
            b = True
            if not fs==fd and fd.startswith(fs + utils.path_sep):
                b = False
            else:
                b = self._cpmv("move", fs, fd, replace);
            if b is True:
                self._append_to_list(arret, pathdst, nm)
            else:
                arret.append({'Name': "E:" + nm})
            
        return json.dumps({'items' : arret})
                                          
     
    def req_makedir(self, cinfo ,params):                                     
        path= self.check_and_replace_path(cinfo, agent.get_prop(params,'path',None), self.OPERATION_EDIT)
        name = agent.get_prop(params, "name", None)
        arret=[]
        try:
            fd = path + name
            utils.path_makedir(fd)
            self._agent_main.get_osmodule().fix_file_permissions("CREATE_DIRECTORY",fd)
            self._append_to_list(arret, path, name)
        except Exception:
            arret.append({'Name': "E:" + name})
        return json.dumps({'items' : arret})

    def req_rename(self, cinfo ,params):
        path= self.check_and_replace_path(cinfo, agent.get_prop(params,'path',None), self.OPERATION_EDIT)
        name = agent.get_prop(params, "name", None)
        newname = agent.get_prop(params, "newname", None)
        fs = path+name
        fd = path+newname
        arret=[]
        try:
            if utils.path_exists(fd):
                raise Exception("#FILEALREADYEXISTS")
            utils.path_rename(fs, fd)
            self._append_to_list(arret, path, newname)
        except Exception:
            arret.append({'Name': "E:" + newname})

        return json.dumps({'items' : arret})
                                        
    def req_set_permissions(self, cinfo ,params):
        path= self.check_and_replace_path(cinfo, agent.get_prop(params,'path',None), self.OPERATION_EDIT)
        name = agent.get_prop(params, "name", None)
        recursive = agent.str2bool(agent.get_prop(params, "recursive", "false"))
        fs = path+name
        arret=[]
        try:
            b=self._set_permissions(fs,params,recursive)
            if b is True:
                self._append_to_list(arret, path, name)
            else:
                arret.append({'Name': "E:" + name})
        except Exception:
            arret.append({'Name': "E:" + name})
        return json.dumps({'items' : arret})
    
    def _set_permissions(self, fs, params, recursive):
        bok = True
        if not utils.path_islink(fs):
            try:
                self._osnative.set_file_permissions(fs,params)
            except Exception:
                bok=False
            if recursive and utils.path_isdir(fs):
                lst=None
                try:
                    lst=utils.path_list(fs)
                    for fname in lst:
                        b = self._set_permissions(fs + utils.path_sep + fname, params, recursive)
                        if bok is True:
                            bok = b
                except Exception:
                    bok=False
        return bok
    
    def req_download(self, cinfo, fdownload):
        path=agent.get_prop(fdownload.get_properties(),'path',None);
        try:
            path = self.check_and_replace_path(cinfo, path, self.OPERATION_DOWNLOAD)
            fdownload.accept(path)        
        except Exception as e:
            if path is None:
                path=""
            raise e

    
    def req_upload(self, cinfo ,fupload):
        path=agent.get_prop(fupload.get_properties(),'path',None);
        try:
            path = self.check_and_replace_path(cinfo, path, self.OPERATION_UPLOAD, {"check_exists": False})
            fupload.accept(path)        
        except Exception as e:
            if path is None:
                path=""
            raise e

class Windows:
    
    def __init__(self,agent_main):
        self._agent_main=agent_main
        self._osmodule = self._agent_main.load_lib("osutil")

    def destroy(self):
        self._agent_main.unload_lib("osutil")
        self._osmodule=None;
    
    def get_resource_path(self):
        '''
        #LEGGE CARTELLA CSIDL_PROGRAM_FILES
        try:
            CSIDL_PROGRAM_FILES=0x0026
            buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
            ctypes.windll.shell32.SHGetFolderPathW(0, CSIDL_PROGRAM_FILES, None, 0, buf)
            if buf.value is not None and buf.value!="":
                drives.append(buf.value);
        except:
            None
        '''
        
        pi= self._osmodule.getDiskInfo()
        s=""
        if pi:
            s = ctypes.wstring_at(pi)
            self._osmodule.freeMemory(pi)
        return json.loads(s)
    
    def pathStartswith(self,apppath,pt):
        return apppath.lower().startswith(pt.lower());
    
    def is_file_valid(self,path):
        return not self._is_file_junction(path)
    
    def _is_file_junction(self,path):
        bret = self._osmodule.isFileJunction(path)
        return bret==1
    
    def get_file_permissions(self,path):
        return {}

    def set_file_permissions(self,path,prms):
        None
    
class Linux:
    
    def destroy(self):
        None
    
    def get_resource_path(self):
        pths = []
        itm={"Name": u"/"}
        pths.append(itm)
        if utils.path_exists(u"/home"):
            itm={"Name": u"/home"}
            pths.append(itm)
        if utils.path_exists(u"/root"):
            itm={"Name": u"/root"}
            pths.append(itm)
        return pths

    def pathStartswith(self,apppath,pt):
        return apppath.startswith(pt);

    def is_file_valid(self,path):
        return True
    
    def get_file_permissions(self,path):
        try:
            import pwd
            import grp
            import stat
            stat_info = utils.path_stat(path)
            user = stat_info.st_uid
            try:
                user = pwd.getpwuid(user).pw_name
            except:
                None
            group = stat_info.st_gid
            try:
                group = grp.getgrgid(group).gr_name
            except:
                None
            smode = str(oct(stat.S_IMODE(stat_info.st_mode)))[-3:]
            itm={}
            itm["Rights"] = smode
            itm["Owner"] = user
            itm["Group"] = group
            return itm
        except:
            return {}
    
    def set_file_permissions(self,path,prms):
        if "mode" in prms:
            utils.path_change_permissions(path, int(prms["mode"],8))
        if "owner" in prms and "group" in prms:
            import pwd
            import grp
            try:
                uid = pwd.getpwnam(prms["owner"]).pw_uid
            except:
                uid=int(prms["owner"])
            try:
                gid = grp.getgrnam(prms["group"]).gr_gid
            except:
                gid=int(prms["group"])
            utils.path_change_owner(path, uid, gid)
    

class Mac(Linux):
    
    def get_resource_path(self):
        pths = []
        itm={"Name": u"/"}
        pths.append(itm)
        if utils.path_exists(u"/Users"):
            itm={"Name": u"/Users"}
            pths.append(itm)
        if utils.path_exists(u"/Library"):
            itm={"Name": u"/Library"}
            pths.append(itm)
        if utils.path_exists(u"/System"):
            itm={"Name": u"/System"}
            pths.append(itm)
        if utils.path_exists(u"/Volumes"):
            itm={"Name": u"/Volumes"}
            pths.append(itm)
        return pths

