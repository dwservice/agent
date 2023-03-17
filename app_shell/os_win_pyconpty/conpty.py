# -*- coding: utf-8 -*-

'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import time
import os
import utils
import ctypes
from threading import Thread
from ctypes import *
from .win32.native import *

##### TO FIX 22/09/2021
try:
    TMP_bytes_to_str=utils.bytes_to_str
    TMP_str_to_bytes=utils.str_to_bytes
except:
    TMP_bytes_to_str=lambda b, enc="ascii": b.decode(enc, errors="replace")
    TMP_str_to_bytes=lambda s, enc="ascii": s.encode(enc, errors="replace")
##### TO FIX 22/09/2021

def _split_user_domain(u):
    ar={"domain":".","user":u}
    if "@" in u:
        arsp=u.split("@")
        ar["domain"]=arsp[1]
        ar["user"]=arsp[0]
    elif "\\" in u:
        arsp=u.split("\\")
        ar["domain"]=arsp[0]
        ar["user"]=arsp[1]
    return ar
    

def check_login(u,p):    
    aruser = _split_user_domain(u)
    pswd = p
    logon_type = 2
    provider = 0
    htoken = wintypes.HANDLE()
    ret = LogonUserW(aruser["user"], aruser["domain"], pswd, logon_type, provider, ctypes.byref(htoken))
    if ret==1:
        CloseHandle(htoken)
        return True
    else:
        return False
    
def is_run_as_service():   
    token = wintypes.HANDLE()
    res = OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, ctypes.byref(token))
    if res > 0:
        return_length = wintypes.DWORD()
        params = [
            token,
            TOKEN_INFORMATION_CLASS.TokenUser,
            None,
            0,
            return_length,
        ]

        res = GetTokenInformation(*params)
        tbuff = ctypes.create_string_buffer(return_length.value)
        params[2] = tbuff
        params[3] = return_length.value    
        res = GetTokenInformation(*params)
        if res > 0:
            tuser = ctypes.cast(tbuff, ctypes.POINTER(TOKEN_USER)).contents
            if IsWellKnownSid(tuser.user.sid,WinLocalSystemSid):
                return True
            elif IsWellKnownSid(tuser.user.sid,WinLocalServiceSid):
                return True
        else:
            raise Exception("GetTokenInformation error.")
    else:
        raise Exception("OpenProcessToken error.")
    return False

class ConPty(Thread):

    def __init__(self, cmd, u, p, cols, rows, ferr=None):
        # Call the Thread class's init function
        Thread.__init__(self)

        # Setup handles
        self._hPC = HPCON()
        self._ptyIn = wintypes.HANDLE(INVALID_HANDLE_VALUE)
        self._ptyOut = wintypes.HANDLE(INVALID_HANDLE_VALUE)
        self._cmdIn = wintypes.HANDLE(INVALID_HANDLE_VALUE)
        self._cmdOut = wintypes.HANDLE(INVALID_HANDLE_VALUE)
        self._cmd = cmd
        self._cols = cols
        self._rows = rows
        self._consoleSize = COORD()
        self._func_err = ferr
        self._status=u"INIT"
        self._mem = None
        self._startupInfoEx=None
        self._lpProcessInformation=None
        self._user = u
        self._password = p
        

    def get_status(self):
        return self._status

    def write_err(self, m):
        if self._func_err is None:
            print(m)
        else:
            self._func_err(m)
    
    def resize(self, rows, cols):
        self._cols = cols
        self._rows = rows
        self._consoleSize.X = self._cols
        self._consoleSize.Y = self._rows
        hr = ResizePseudoConsole(self._hPC,self._consoleSize)
        if not hr == S_OK:
            self.write_err(u"Failed to resize pseudoconsole")
        
        
    
    def run(self):
        try:
            
             
            # Create pipes
            CreatePipe(byref(self._ptyIn),  # HANDLE read pipe
                       byref(self._cmdIn),  # HANDLE write pipe
                       None,                # LPSECURITY_ATTRIBUTES pipe attributes
                       0)                   # DWORD size of buffer for the pipe. 0 = default size
    
            CreatePipe(byref(self._cmdOut), # HANDLE read pipe
                       byref(self._ptyOut), # HANDLE write pipe
                       None,                # LPSECURITY_ATTRIBUTES pipe attributes
                       0)                   # DWORD size of buffer for the pipe. 0 = default size
            
    
            # Create pseudo console
            self._consoleSize.X = self._cols
            self._consoleSize.Y = self._rows
            hr = CreatePseudoConsole(self._consoleSize,  # ConPty Dimensions
                                     self._ptyIn,        # ConPty Input
                                     self._ptyOut,       # ConPty Output
                                     DWORD(0),           # Flags
                                     byref(self._hPC))   # ConPty Reference
            
            
            
            # Close the handles
            CloseHandle(self._ptyIn)        # Close the handles as they are now dup'ed into the ConHost
            CloseHandle(self._ptyOut)       # Close the handles as they are now dup'ed into the ConHost
                           
    
            if not hr == S_OK:
                raise Exception(u"Failed to create pseudoconsole")
    
            # Initialize startup info
            self._startupInfoEx = STARTUPINFOEX()
            self._startupInfoEx.StartupInfo.cb = sizeof(STARTUPINFOEX)
            
            self._startupInfoEx.StartupInfo.hStdError = self._ptyOut
            self._startupInfoEx.StartupInfo.hStdOutput = self._ptyOut
            self._startupInfoEx.StartupInfo.hStdInput = self._ptyIn
            self._startupInfoEx.StartupInfo.dwFlags |= STARTF_USESTDHANDLES;
            
            self.__initStartupInfoExAttachedToPseudoConsole()
            self._lpProcessInformation = PROCESS_INFORMATION()
    
            defpath = None
            try:
                defpath = os.getcwdu().split(os.path.sep)[0]+os.path.sep                
                if defpath[0]==os.path.sep:
                    defpath=None
            except:
                None
            
            
            if self._user is None:
                # Create process
                hr = CreateProcessW(None,                                        # _In_opt_      LPCTSTR
                                    self._cmd,                                   # _Inout_opt_   LPTSTR
                                    None,                                        # _In_opt_      LPSECURITY_ATTRIBUTES
                                    None,                                        # _In_opt_      LPSECURITY_ATTRIBUTES
                                    False,                                       # _In_          BOOL
                                    EXTENDED_STARTUPINFO_PRESENT,                # _In_          DWORD
                                    None,                                        # _In_opt_      LPVOID
                                    defpath,                                     # _In_opt_      LPCTSTR
                                    byref(self._startupInfoEx.StartupInfo),      # _In_          LPSTARTUPINFO
                                    byref(self._lpProcessInformation))           # _Out_
            
            else:   
                '''
                ptoken = wintypes.HANDLE()
                ret = OpenProcessToken(GetCurrentProcess(),  TOKEN_QUERY | TOKEN_ADJUST_PRIVILEGES, ctypes.byref(ptoken))
                
                luid = LUID()
                ret = LookupPrivilegeValueW(None,"SeTcbPrivilege",luid)
                
                size = ctypes.sizeof(TOKEN_PRIVILEGES)
                size += ctypes.sizeof(LUID_AND_ATTRIBUTES)
                buffer = ctypes.create_string_buffer(size)
                tp = ctypes.cast(buffer, ctypes.POINTER(TOKEN_PRIVILEGES)).contents
                tp.count = 1
                tp.get_array()[0].LUID = luid
                tp.get_array()[0].Attributes = SE_PRIVILEGE_ENABLED
                res = AdjustTokenPrivileges(ptoken, False, tp, 0, None, None)
                '''
                                    
                # TOKEN USER
                aruser = _split_user_domain(self._user)
                pswd = self._password
                self._password=None
                logon_type = 2
                provider = 0
                htoken = wintypes.HANDLE()
                ret = LogonUserW(aruser["user"], aruser["domain"], pswd, logon_type, provider, ctypes.byref(htoken))
                if ret == 0:
                    raise Exception(u"Failed to LogonUserW " + self._user)                                    
                
                # Create process
                hr = CreateProcessAsUserW(htoken,                                # _In_          HANDLE
                                    None,                                        # _In_opt_      LPCTSTR
                                    self._cmd,                                   # _Inout_opt_   LPTSTR
                                    None,                                        # _In_opt_      LPSECURITY_ATTRIBUTES
                                    None,                                        # _In_opt_      LPSECURITY_ATTRIBUTES
                                    False,                                       # _In_          BOOL
                                    EXTENDED_STARTUPINFO_PRESENT,                # _In_          DWORD
                                    None,                                        # _In_opt_      LPVOID
                                    defpath,                                    # _In_opt_      LPCTSTR
                                    byref(self._startupInfoEx.StartupInfo),      # _In_          LPSTARTUPINFO
                                    byref(self._lpProcessInformation))           # _Out_
        
                
                #CloseHandle(htoken);
    
            # Check if process is up
            if hr == 0x0:
                raise Exception(u"Failed to execute " + self._cmd + u": " + str(hr))
            
            self._status=u"OPEN"
            WaitForSingleObject(self._lpProcessInformation.hThread, 10 * 1000)
        except Exception as e:
            self._status=u"ERROR:" + utils.exception_to_string(e)
            self.write_err(utils.exception_to_string(e))
            self.close()

    def open(self, timeout=20):
        self.start()
        while self._status==u"INIT":
            time.sleep(0.5)
            timeout-=0.5
            if timeout<0:
                if self._status!=u"INIT":
                    break
                else:
                    raise Exception(u"Process not started.")
                
        if self._status.startswith(u"ERROR:"):
            raise Exception(self._status[6:])
            
    def __initStartupInfoExAttachedToPseudoConsole(self):        
        dwAttributeCount = 1
        dwFlags = 0
        lpSize = PVOID()

        # call with null lpAttributeList to get lpSize
        try:
            ok = InitializeProcThreadAttributeList(None, dwAttributeCount, dwFlags, byref(lpSize))
            if ok == 0x0:
                raise Exception(u"Failed to call InitializeProcThreadAttributeList")
        except WindowsError as err:
            if err.winerror == 122:
                # the data area passed to the system call is too small.
                SetLastError(0)
            else:
                raise

        mem = HeapAlloc(GetProcessHeap(), 0, lpSize.value)
        self._startupInfoEx.lpAttributeList = cast(mem, POINTER(c_void_p))
        
        ok = InitializeProcThreadAttributeList(self._startupInfoEx.lpAttributeList, dwAttributeCount, dwFlags, byref(lpSize))
        if ok == 0x0:
            raise Exception(u"Failed to call InitializeProcThreadAttributeList")
        ok = UpdateProcThreadAttribute(self._startupInfoEx.lpAttributeList, DWORD(0), DWORD(PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE),
                                  self._hPC, sizeof(self._hPC), None, None)

        if ok == 0x0:
            raise Exception(u"Failed to call UpdateProcThreadAttribute")

    def close(self):
        # cleanup
        self._status=u"CLOSE"
        try:
            CloseHandle(self._cmdIn)
        except:
                None
        try:
            CloseHandle(self._cmdOut)
        except:
                None
        if self._startupInfoEx is not None:
            DeleteProcThreadAttributeList(self._startupInfoEx.lpAttributeList)
        HeapFree(GetProcessHeap(), 0, self._mem)
        ClosePseudoConsole(self._hPC)
        if self._lpProcessInformation is not None:
            try:
                TerminateProcess(self._lpProcessInformation.hProcess, 0)
            except:
                None
            try:
                CloseHandle(self._lpProcessInformation.hThread)
            except:
                None
            try:
                CloseHandle(self._lpProcessInformation.hProcess)
            except:
                None        

    def read(self):
        MAX_READ = 1024*8
        lpBuffer = create_string_buffer(MAX_READ)
        lpNumberOfBytesRead = DWORD()
        lpNumberOfBytesAvail = DWORD()
        lpBytesLeftInMessage = DWORD()

        #   HANDLE  hNamedPipe,
        #   LPVOID  lpBuffer,
        #   DWORD   nBufferSize,
        #   LPDWORD lpBytesRead,
        #   LPDWORD lpTotalBytesAvail,
        #   LPDWORD lpBytesLeftThisMessage
        hr = PeekNamedPipe(self._cmdOut,
                           lpBuffer,
                           MAX_READ,
                           byref(lpNumberOfBytesRead),
                           byref(lpNumberOfBytesAvail),
                           byref(lpBytesLeftInMessage))

        if not hr == 0x0 and lpNumberOfBytesAvail.value > 0:
            hr = ReadFile(self._cmdOut,              # Handle to the file or i/o device
                     lpBuffer,                      # Pointer to the buffer that receive the data from the device
                     MAX_READ,                      # Maximum number of bytes to read
                     byref(lpNumberOfBytesRead),    # Number of bytes read from the device
                     NULL_PTR                       # Not used
                     )
            if hr == 0x0:
                self.write_err(u"failed to read: " + str(hr))
            return lpBuffer.raw[:lpNumberOfBytesRead.value]
        else:
            return ""

    def write(self, data):
        lpBuffer = create_string_buffer(data.encode('utf8'))
        lpNumberOfBytesWritten = DWORD()
        hr = WriteFile(self._cmdIn,            # Handle to the file or i/o device
                  lpBuffer,                     # Pointer to the buffer that contains the data to be written
                  sizeof(lpBuffer),             # Number of bytes to write
                  lpNumberOfBytesWritten,       # Number of bytes written
                  NULL_PTR)                     # Not used
        if hr == 0x0:
            self.write_err(u"Failed to write: " + str(hr))


if __name__ == '__main__':
    # Create a cmd.exe pty
    print("[!] creating pty")
    pty = ConPty("c:\\windows\\system32\\cmd.exe", 80, 60)
    pty.open()
    time.sleep(1)
    print("[!] pty created")
    output = pty.read()
    print('output1: ' + utils.bytes_to_str(output,"utf8"))
    time.sleep(3)
    pty.write("whoami\r\n")
    time.sleep(3)
    output = pty.read()
    print('output2: ' + utils.bytes_to_str(output,"utf8"))
    time.sleep(1)        
    print('[!] cleanup')
    pty.close()
