# -*- coding: utf-8 -*-

'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''

import json
import agent
import ctypes
import native
import signal
import os
import platform
import time
import re
import subprocess
import stat
import utils

class Resource():

    def __init__(self, agent_main):
        self._agent_main=agent_main
        self._osnative = None
        if agent.is_windows():
            self._osnative = NativeWindows(self._agent_main)
        elif agent.is_linux():
            self._osnative = NativeLinux()
        elif agent.is_mac():
            self._osnative = NativeMac()
        
        
    def destroy(self,bforce):
        if self._osnative is not None:
            self._osnative.destroy()
            self._osnative = None
        return True
    
    def has_permission(self,cinfo):
        return self._agent_main.has_app_permission(cinfo,"resource"); 
    
    def req_systeminfo(self, cinfo ,params):
        ret = self._osnative.get_system_info()
        return json.dumps(ret)
        
    def req_listdiskpartition(self, cinfo ,params):
        ret = self._osnative.get_diskpartition_info()
        return json.dumps({'items' : ret})
        
    def req_performanceinfo(self, cinfo ,params):
        ret = self._osnative.get_performance_info()
        return json.dumps(ret)

    def req_listtask(self, cinfo ,params):
        ret = self._osnative.get_task_list()
        #ORDINA PER NOME
        ret = sorted(ret, key=lambda k: k['Name'].lower()) 
        return json.dumps({'items' : ret})
    
    def req_killtask(self, cinfo ,params):
        pid = agent.get_prop(params,"pid", None)
        bok = self._osnative.task_kill(int(pid));
        if (bok is True):
            ret = "{ok: true}"
        else:
            ret = "{ok: false}"
        return ret
    
    def req_listservice(self, cinfo ,params):
        ret = self._osnative.get_service_list()
        #ORDINA PER NOME
        ret = sorted(ret, key=lambda k: k['Name'].lower()) 
        return json.dumps({'items' : ret})
        
    def req_startservice(self, cinfo ,params):
        name = agent.get_prop(params,"name", None)
        bok = self._osnative.service_start(name);
        if (bok is True):
            ret = "{ok: true}"
        else:
            ret = "{ok: false}"
        return ret
    
    def req_stopservice(self, cinfo ,params):
        name = agent.get_prop(params,"name", None)
        bok = self._osnative.service_stop(name);
        if (bok is True):
            ret = "{ok: true}"
        else:
            ret = "{ok: false}"
        return ret

class NativeWindows:
    
    def __init__(self,agent_main):
        self._agent_main=agent_main
        self._osmodule = self._agent_main.load_lib("osutil")

    def destroy(self):
        self._agent_main.unload_lib("osutil")
        self._osmodule=None;
    
    def get_system_info(self):
        pi= self._osmodule.getSystemInfo()
        s=""
        if pi:
            s = ctypes.wstring_at(pi)
            self._osmodule.freeMemory(pi)
        return json.loads(s)
    
    def get_diskpartition_info(self):
        '''
        res = []
        bitmask = ctypes.windll.kernel32.GetLogicalDrives()
        for letter in string.uppercase:
            if bitmask & 1:
                nm = letter+":\\"
                total_bytes = ctypes.c_ulonglong(0)
                free_bytes = ctypes.c_ulonglong(0)
                ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(nm), None, ctypes.pointer(total_bytes), ctypes.pointer(free_bytes))
                info = { "Name" : nm,  
                            "Size": total_bytes.value  , 
                            "Free": free_bytes.value 
                        }
                res.append(info)
            bitmask >>= 1
        return res
        '''
        pi= self._osmodule.getDiskInfo()
        s=""
        if pi:
            s = ctypes.wstring_at(pi)
            self._osmodule.freeMemory(pi)
        return json.loads(s)
    
    def get_performance_info(self):
        pi= self._osmodule.getPerformanceInfo()
        s=""
        if pi:
            s = ctypes.wstring_at(pi)
            self._osmodule.freeMemory(pi)
        return json.loads(s)  
        
    def get_task_list(self):
        pi= self._osmodule.getTaskList()
        s=""
        if pi:
            s = ctypes.wstring_at(pi)
            self._osmodule.freeMemory(pi)
        return json.loads(s)
    
    def task_kill(self, pid):
        bret = self._osmodule.taskKill(pid)
        return bret==1
    
    def get_service_list(self):
        pi= self._osmodule.getServiceList()
        s=""
        if pi:
            s = ctypes.wstring_at(pi)
            self._osmodule.freeMemory(pi)
        return json.loads(s)
    
    def service_start(self,name):
        bret = self._osmodule.startService(name)
        return bret==1
    
    def service_stop(self,name):
        bret = self._osmodule.stopService(name)
        return bret==1

class NativeLinux:
    def __init__(self):
        self._PAGESIZE = os.sysconf("SC_PAGE_SIZE")
        self._CLOCKTICKS = os.sysconf("SC_CLK_TCK")
        self._timer = getattr(time, 'monotonic', time.time)
        self._oldcputime=None
        self._cpu_logical_count=self.get_cpu_logical_count()
   
    def destroy(self):
        None
   
    def get_system_info(self):
        hmcpu={}
        f = utils.file_open("/proc/cpuinfo", "r")
        try:
            for line in f:
                if line.startswith("model name"):
                    ar = line.split(":")
                    n = ar[1].strip()
                    if n not in hmcpu:
                        hmcpu[n]=1
                    else:
                        hmcpu[n]=hmcpu[n]+1
        finally:
            f.close()
        cpuName=""
        for k in hmcpu:
            if cpuName!="":
                cpuName+= ", " 
            cpuName+=k
        return  {"osName":platform.platform(),  "osUpdate":"", "osBuild":platform.version(), "pcName":platform.node() , "cpuName":cpuName,  "cpuArchitecture":platform.machine()}
    
    def get_diskpartition_info(self):
        arret = []
        phydevs = []
        f = utils.file_open("/proc/filesystems", "r")
        try:
            for line in f:
                if not line.startswith("nodev"):
                    phydevs.append(line.strip())
        finally:
            f.close()
        #Legge fstab
        f = utils.file_open("/etc/fstab", "r")
        try:
            for line in f:
                line=line.strip()
                if not line.strip().startswith("#"):
                    line=line.replace('\t',' ')
                    ar=[]
                    arapp = line.split(" ")
                    for a in arapp:
                        if a.strip()!="":
                            ar.append(a.strip())
                    if len(ar)>=3:
                        nm = ar[1]
                        tp = ar[2]
                        if tp in phydevs:
                            path=nm
                            try:
                                st = os.statvfs(path)
                            except UnicodeEncodeError:
                                if isinstance(path, unicode):
                                    try:
                                        import sys
                                        path = path.encode(sys.getfilesystemencoding())
                                    except UnicodeEncodeError:
                                        pass
                                    st = os.statvfs(path)
                                else:
                                    raise
                            free = (st.f_bavail * st.f_frsize)
                            size = (st.f_blocks * st.f_frsize)
                            arret.append({"Name":nm, "Size":size, "Free":free})
        finally:
            f.close()
        return arret    
    
    def get_cpu_logical_count(self):
        num = 0
        try:
            try:
                num = os.sysconf("SC_NPROCESSORS_ONLN")
            except ValueError:
                None
            
            if num == 0:
                f = utils.file_open('/proc/cpuinfo', 'rb')
                try:
                    lines = f.readlines()
                finally:
                    f.close()
                for line in lines:
                    if line.lower().startswith('processor'):
                        num += 1
            if num == 0:
                f = utils.file_open('/proc/stat', 'rt')
                try:
                    lines = f.readlines()
                finally:
                    f.close()
                search = re.compile('cpu\d')
                for line in lines:
                    line = line.split(' ')[0]
                    if search.match(line):
                        num += 1
        except:
            None
        return num
    
    def get_performance_info(self):
        ret  = {}
        cpuUsagePerc=0
        #Legge info cpu
        f = utils.file_open('/proc/stat', 'rb')
        try:
            arline = f.readline().split()
        finally:
            f.close()
        cputime = {}
        cputime['user'] = float(arline[1]) / self._CLOCKTICKS
        cputime['nice'] = float(arline[2]) / self._CLOCKTICKS
        cputime['system'] = float(arline[3]) / self._CLOCKTICKS
        cputime['idle'] = float(arline[4]) / self._CLOCKTICKS
        cputime['iowait'] = float(arline[5]) / self._CLOCKTICKS
        cputime['irq'] = float(arline[6]) / self._CLOCKTICKS
        cputime['softirq'] = float(arline[7]) / self._CLOCKTICKS
        timer = lambda: self._timer() * self._cpu_logical_count
        cputime['timer']=timer()
        if self._oldcputime is not None:
            try:
                delta_proc = (cputime['user'] - self._oldcputime['user']) + (cputime['system'] - self._oldcputime['system'])
                delta_time = cputime['timer'] - self._oldcputime['timer']
                cpuUsagePerc = int(((delta_proc / delta_time) * 100) * self._cpu_logical_count)
                if cpuUsagePerc>100:
                    cpuUsagePerc=100
            except ZeroDivisionError:
                None
        self._oldcputime = cputime     
        ret["cpuUsagePerc"]=cpuUsagePerc
        
        #Legge la memoria
        f = utils.file_open('/proc/meminfo', 'rb')
        memoryPhysicalTotal=0
        memoryPhysicalAvailable=-1
        memoryFree=0
        memoryVirtualTotal=0
        memoryVirtualAvailable=0
        try:
            for line in f:
                if line.startswith("MemTotal:"):
                    memoryPhysicalTotal = long(line.split()[1]) * 1024
                elif line.startswith("MemFree:"):
                    memoryFree = long(line.split()[1]) * 1024
                elif line.startswith("MemAvailable:"):
                    memoryPhysicalAvailable = long(line.split()[1]) * 1024
                elif line.startswith("SwapTotal:"):
                    memoryVirtualTotal = long(line.split()[1]) * 1024
                elif line.startswith("SwapFree:"):
                    memoryVirtualAvailable = long(line.split()[1]) * 1024
        finally:
            f.close()
        
        ret["memoryPhysicalTotal"]=memoryPhysicalTotal
        if memoryPhysicalAvailable==-1:
            memoryPhysicalAvailable=memoryFree
        ret["memoryPhysicalAvailable"]=memoryPhysicalAvailable
        ret["memoryVirtualTotal"]=memoryVirtualTotal
        ret["memoryVirtualAvailable"]=memoryVirtualAvailable
        ret["memoryTotal"]=ret["memoryPhysicalTotal"]+ret["memoryVirtualTotal"]
        ret["memoryAvailable"]=ret["memoryPhysicalAvailable"]+ret["memoryVirtualAvailable"]
        return ret        
        
    def get_task_list(self):
        import pwd
        ret = []
        for x in utils.path_list('/proc') :
            if x.isdigit():
                try:
                    itm={}
                    #PID
                    itm["PID"]=long(x)
                    #Name
                    f = utils.file_open("/proc/%s/stat" % x)
                    try:
                        itm["Name"] = f.read().split(' ')[1].replace('(', '').replace(')', '')
                    finally:
                        f.close()
                    #Memory
                    f = utils.file_open("/proc/%s/statm" % x)
                    try:
                        vms, rss = f.readline().split()[:2]
                        itm["Memory"] = long(rss) * long(self._PAGESIZE)
                        #int(vms) * _PAGESIZE)
                    finally:
                        f.close()
                    #Owner
                    f = utils.file_open("/proc/%s/status" % x)
                    try:
                        for line in f:
                            if line.startswith('Uid:'):
                                    r = line.split()
                                    itm["Owner"] = pwd.getpwuid(int(r[1])).pw_name
                                    break
                    finally:
                        f.close()
                    ret.append(itm)
                except:
                    None
        return ret
    
    def task_kill(self, pid):
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError as e:
            return False
        return True
    
    def _which(self, name):
        p = subprocess.Popen("which " + name, stdout=subprocess.PIPE, shell=True)
        (po, pe) = p.communicate()
        p.wait()
        return len(po) > 0
    
    def get_service_list(self):
        ret=[]
        if self._which("systemctl"):
            p = subprocess.Popen("systemctl --all --full list-units | grep \.service", stdout=subprocess.PIPE, shell=True)
            (po, pe) = p.communicate()
            p.wait()
            if po is not None and len(po)>0:
                appar = po.split("\n")
                for appln in appar:
                    sv = ""
                    stcnt = -1
                    stapp = ""
                    ar = appln.split(" ")
                    for k in ar:
                        if len(k)>0:
                            if stcnt == -1:
                                if k.endswith(".service"):
                                    sv+=k[0:len(k)-8]
                                    stcnt+=1
                                else:
                                    sv+=k
                            else:
                                stcnt+=1
                                if stcnt==3:
                                    stapp=k
                    if stcnt != -1:
                        if  stapp == "running":
                            st = 4
                        else:
                            st = 1
                        ret.append({"Name":sv,"Label":"","Status":st})
        else:
            #SYSVINIT
            for x in utils.path_list('/etc/init.d'):
                if x.lower()!="rc" and x.lower()!="rcs" and x.lower()!="halt" and x.lower()!="reboot" and x.lower()!="single":
                    xp = "/etc/init.d/" + x
                    st = utils.path_stat(xp)
                    if bool(st.st_mode & stat.S_IXUSR) or bool(st.st_mode & stat.S_IXGRP) or bool(st.st_mode & stat.S_IXOTH):                        
                        appf = utils.file_open("/etc/init.d/" + x)
                        apps = appf.read()
                        appf.close()                        
                        if "status)" in apps or "status|" in apps:  
                            p = subprocess.Popen("/etc/init.d/" + x + " status", stdout=subprocess.PIPE, shell=True)
                            (po, pe) = p.communicate()
                            p.wait()
                            if po is not None and len(po)>0:
                                st = 999
                                if "running" in po.lower() or "started" in po.lower():
                                    st = 4
                                elif "not running" in po.lower() or "not started" in po.lower() or "failed" in po.lower():
                                    st = 1
                                ret.append({"Name":x,"Label":"","Status":st})
        return ret
    
    def service_start(self, name):
        if self._which("systemctl"):
            #SYSTEMD
            p = subprocess.Popen("systemctl start " + name + ".service", stdout=subprocess.PIPE, shell=True)
            (po, pe) = p.communicate()
            p.wait()
            return (po is None or len(po)==0) and (pe is None or len(pe)==0)
        else:
            #SYSVINIT
            p = subprocess.Popen("/etc/init.d/" + name + " start", stdout=subprocess.PIPE, shell=True)
            (po, pe) = p.communicate()
            p.wait()
            p = subprocess.Popen("/etc/init.d/" + name + " status", stdout=subprocess.PIPE, shell=True)
            (po, pe) = p.communicate()
            p.wait()
            return "running" in po.lower() or "started" in po.lower()
        
    
    def service_stop(self, name):
        if self._which("systemctl"):
            #SYSTEMD
            p = subprocess.Popen("systemctl stop " + name + ".service", stdout=subprocess.PIPE, shell=True)
            (po, pe) = p.communicate()
            p.wait()
            return (po is None or len(po)==0) and (pe is None or len(pe)==0)
        else:
            #SYSVINIT
            p = subprocess.Popen("/etc/init.d/" + name + " stop", stdout=subprocess.PIPE, shell=True)
            (po, pe) = p.communicate()
            p.wait()
            p = subprocess.Popen("/etc/init.d/" + name + " status", stdout=subprocess.PIPE, shell=True)
            (po, pe) = p.communicate()
            p.wait()
            return "not running" in po.lower() or "not started" in po.lower()  or "failed" in po.lower()
       
class NativeMac:
    def __init__(self):
        self._PAGESIZE = os.sysconf("SC_PAGE_SIZE")
   
    def destroy(self):
        None
   
    def get_system_info(self):
        cpuName=""
        try:
            appout = subprocess.Popen("sysctl machdep.cpu.brand_string", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate() 
            lines = appout[0].splitlines()
            for l in lines:
                try:
                    idx = l.index(':')
                    cpuName=l[idx+1:].strip()
                    break
                except:
                    None
        except:
            None
        return  {"osName":platform.platform(),  "osUpdate":"", "osBuild":platform.version(), "pcName":platform.node() , "cpuName":cpuName,  "cpuArchitecture":platform.machine()}
    
    def get_diskpartition_info(self):
        arret = []
        try:
            appout = subprocess.Popen("diskutil info /", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate() 
            lines = appout[0].splitlines()
            size=0
            free=0
            for l in lines:
                if len(l.strip())>0:
                    try:
                        idx = l.index(':')
                        key=l[:idx].strip()
                        if key.lower()=="total size":
                            try:
                                iapp1 = l.index('(')
                                iapp2 = l.index(' ',iapp1)
                                size=long(l[iapp1+1:iapp2].strip())
                            except:
                                None
                        elif key.lower()=="volume free space":
                            try:
                                iapp1 = l.index('(')
                                iapp2 = l.index(' ',iapp1)
                                free=long(l[iapp1+1:iapp2].strip())
                            except:
                                None
                    except:
                        None
            arret.append({"Name":"/", "Size":size, "Free":free})
        except:
            None
        return arret
        
    
    def get_performance_info(self):
        ret  = {}
        ret["cpuUsagePerc"]=0
        ret["memoryPhysicalTotal"]=0
        ret["memoryPhysicalAvailable"]=0
        ret["memoryVirtualTotal"]=0
        ret["memoryVirtualAvailable"]=0
        
        #CPU
        try:
            appout = subprocess.Popen("iostat -c 2", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
            lines = appout[0].splitlines()
            cnt=0
            idxus=-1
            idxsy=-1 
            for l in lines:
                cnt+=1
                if cnt==2:
                    ar = l.strip().split();
                    for idx in range(len(ar)):
                        if ar[idx]=="us":
                            idxus=idx
                        elif ar[idx]=="sy":
                            idxsy=idx
                if cnt==4 and idxus!=-1 and idxsy!=-1:
                    if len(l.strip())>0:
                        ar = l.strip().split();
                        cpu = float(ar[6]) + float(ar[7]) 
                        ret["cpuUsagePerc"]=cpu
                    break    
        except Exception as e:
            None
        
        #MEMORIA
        try:
            ps = subprocess.Popen(['ps', '-caxm', '-orss,comm'], stdout=subprocess.PIPE).communicate()[0]
            vm = subprocess.Popen(['vm_stat'], stdout=subprocess.PIPE).communicate()[0]
            processLines = ps.split('\n')
            sep = re.compile('[\s]+')
            for row in range(1,len(processLines)):
                rowText = processLines[row].strip()
                rowElements = sep.split(rowText)
                try:
                    rss = float(rowElements[0]) * 1024
                except:
                    rss = 0 
            vmLines = vm.split('\n')
            sep = re.compile(':[\s]+')
            vmStats = {}
            for row in range(1,len(vmLines)-2):
                rowText = vmLines[row].strip()
                rowElements = sep.split(rowText)
                vmStats[(rowElements[0])] = int(rowElements[1].strip('\.')) * 4096
            
            ret["memoryPhysicalTotal"]=vmStats["Pages wired down"]+vmStats["Pages active"]+vmStats["Pages inactive"]+vmStats["Pages free"]
            ret["memoryPhysicalAvailable"]= vmStats["Pages wired down"]+vmStats["Pages active"]+vmStats["Pages inactive"]
        except Exception as e:
            None
        
        ret["memoryTotal"]=ret["memoryPhysicalTotal"]+ret["memoryVirtualTotal"]
        ret["memoryAvailable"]=ret["memoryPhysicalAvailable"]+ret["memoryVirtualAvailable"]
        return ret        
        
    def get_task_list(self):
        ret = []
        try:
            size_pid=10;
            size_user=200;
            size_rss=50;
            size_comm=200;
            appout = subprocess.Popen("ps -axc -o pid=" + ("-"*size_pid) + ",user=" + ("-"*size_user) + ",rss=" + ("-"*size_rss) + ",comm=" + ("-"*size_comm), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate() 
            lines = appout[0].splitlines()
            bfirst=True
            for l in lines:
                if not bfirst:
                    itm={}
                    p=0
                    try:
                        itm["PID"]=long(l[p:p+size_pid].strip())
                    except:
                        itm["PID"]=-1
                    p=p+size_pid+1
                    itm["Owner"] = l[p:p+size_user].strip()
                    p=p+size_user+1
                    try:
                        itm["Memory"] = long(l[p:p+size_rss].strip())
                    except: 
                        itm["Memory"] = 0
                    p=p+size_rss+1
                    itm["Name"] = l[p:p+size_comm].strip()
                    ret.append(itm)
                bfirst=False
            ret.remove(ret[len(ret)-1]) #ELIMINA IL COMANDO CORRENTE PS
        except:
            None
        return ret
    
    def task_kill(self, pid):
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError as e:
            return False
        return True
    
    def _get_service_list(self):
        import xml.etree.ElementTree as ET
        ret={}
        path='/System/Library/LaunchDaemons'
        for x in utils.path_list(path):
            try:
                bok=False
                tree = ET.parse(path + "/" + x)
                root = tree.getroot()
                for dict in root:
                    if dict.tag=="dict":
                        for child in dict:
                            if bok==True:
                                if child.tag.lower()=="string":
                                    ret[child.text]=path + "/" + x
                                    break
                            if child.tag.lower()=="key" and child.text.lower()=="label":
                                bok=True
                    if bok==True:
                        break     
            except Exception as e:
                None
        return ret
    
    def _get_service_status(self,name):
        try:
            appout = subprocess.Popen("launchctl list " + name, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
            lines = appout[0].splitlines()
            for l in lines:
                if "LastExitStatus" in l:
                    return 4
            return 1
        except:
            return 999
    
    def get_service_list(self):
        ret=[]
        hmsvc = self._get_service_list()
        for s in hmsvc:
            st=self._get_service_status(s)
            ret.append({"Name":s,"Label":"","Status":st})
        return ret
    
    def service_start(self, name):
        try:
            hmsvc = self._get_service_list()
            if name in hmsvc:
                p = subprocess.Popen("launchctl load -F " + hmsvc[name], stdout=subprocess.PIPE, shell=True)
                (po, pe) = p.communicate()
                p.wait()
                return (po is None or len(po)==0) and (pe is None or len(pe)==0)
            return False
        except:
            return False
        
    
    def service_stop(self, name):
        try:
            hmsvc = self._get_service_list()
            if name in hmsvc:
                p = subprocess.Popen("launchctl unload " + hmsvc[name], stdout=subprocess.PIPE, shell=True)
                (po, pe) = p.communicate()
                p.wait()
                return (po is None or len(po)==0) and (pe is None or len(pe)==0)
            return False
        except:
            return False
