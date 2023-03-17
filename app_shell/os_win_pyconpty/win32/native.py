# -*- coding: utf-8 -*-

'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
from ctypes import Structure, POINTER, windll, c_void_p, c_char_p, c_size_t, c_uint, HRESULT, WinError, wintypes
from ctypes.wintypes import *

PVOID = LPVOID
PULONG = c_void_p
LPTSTR = c_void_p
LPBYTE = c_char_p
SIZE_T = c_size_t
HPCON = HANDLE

if not hasattr(wintypes, 'LPDWORD'): # PY2
    wintypes.LPDWORD = POINTER(wintypes.DWORD)

def _errcheck_bool(value, func, args):
    if not value:
        raise WinError()
    return args


class STARTUPINFO(Structure):
    """ STARTUPINFO structure """
    _fields_ = [("cb", DWORD),
                ("lpReserved", LPTSTR),
                ("lpDesktop", LPTSTR),
                ("lpTitle", LPTSTR),
                ("dwX", DWORD),
                ("dwY", DWORD),
                ("dwXSize", DWORD),
                ("dwYSize", DWORD),
                ("dwXCountChars", DWORD),
                ("dwYCountChars", DWORD),
                ("dwFillAttribute", DWORD),
                ("dwFlags", DWORD),
                ("wShowWindow", WORD),
                ("cbReserved2", WORD),
                ("lpReserved2", LPBYTE),
                ("hStdInput", HANDLE),
                ("hStdOutput", HANDLE),
                ("hStdError", HANDLE)]


class STARTUPINFOEX(Structure):
    """ STARTUPINFOEX structure """
    _fields_ = [("StartupInfo", STARTUPINFO),
                ("lpAttributeList", POINTER(PVOID))]


class PROCESS_INFORMATION(Structure):
    """ PROCESS_INFORMATION structure """
    _fields_ = [("hProcess", HANDLE),
                ("hThread", HANDLE),
                ("dwProcessId", DWORD),
                ("dwThreadId", DWORD)]


class SECURITY_ATTRIBUTES(Structure):
    """ SECURITY_ATTRIBUTES structure """
    _fields_ = [("nLength", DWORD),
                ("lpSecurityDescriptor", HANDLE),
                ("bInheritHandle", DWORD)]


class COORD(Structure):
    """ COORD structure """
    _fields_ = [("X", SHORT),
                ("Y", SHORT)]

ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
DISABLE_NEWLINE_AUTO_RETURN = 0x0008
PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE = 0x00020016
EXTENDED_STARTUPINFO_PRESENT = 0x00080000
CREATE_NO_WINDOW = 0x08000000
STARTF_USESTDHANDLES = 0x00000100
BUFFER_SIZE_PIPE = 1048576

S_OK = 0x00000000
INFINITE = 0xFFFFFFFF
SW_HIDE = 0
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
FILE_ATTRIBUTE_NORMAL = 0x80
OPEN_EXISTING = 3
STD_INPUT_HANDLE = -10
STD_OUTPUT_HANDLE = -11
STD_ERROR_HANDLE = -12
INVALID_HANDLE_VALUE = -1

NULL_PTR = POINTER(c_void_p)()

# BOOL InitializeProcThreadAttributeList(
#   LPPROC_THREAD_ATTRIBUTE_LIST lpAttributeList,
#   DWORD                        dwAttributeCount,
#   DWORD                        dwFlags,
#   PSIZE_T                      lpSize
# );
InitializeProcThreadAttributeList = windll.kernel32.InitializeProcThreadAttributeList
InitializeProcThreadAttributeList.argtype = [POINTER(HANDLE), POINTER(HANDLE), PVOID, DWORD]
InitializeProcThreadAttributeList.restype = BOOL
InitializeProcThreadAttributeList.errcheck = _errcheck_bool

# BOOL UpdateProcThreadAttribute(
#   LPPROC_THREAD_ATTRIBUTE_LIST lpAttributeList,
#   DWORD                        dwFlags,
#   DWORD_PTR                    Attribute,
#   PVOID                        lpValue,
#   SIZE_T                       cbSize,
#   PVOID                        lpPreviousValue,
#   PSIZE_T                      lpReturnSize
# );
UpdateProcThreadAttribute = windll.kernel32.UpdateProcThreadAttribute
UpdateProcThreadAttribute.argtype = [
    POINTER(PVOID),
    DWORD,
    POINTER(DWORD),
    PVOID,
    SIZE_T,
    PVOID,
    POINTER(SIZE_T)
]
UpdateProcThreadAttribute.restype = BOOL
UpdateProcThreadAttribute.errcheck = _errcheck_bool

# BOOL CreateProcessW(
#   LPCWSTR               lpApplicationName,
#   LPWSTR                lpCommandLine,
#   LPSECURITY_ATTRIBUTES lpProcessAttributes,
#   LPSECURITY_ATTRIBUTES lpThreadAttributes,
#   BOOL                  bInheritHandles,
#   DWORD                 dwCreationFlags,
#   LPVOID                lpEnvironment,
#   LPCWSTR               lpCurrentDirectory,
#   LPSTARTUPINFOW        lpStartupInfo,
#   LPPROCESS_INFORMATION lpProcessInformation
# );
CreateProcessW = windll.kernel32.CreateProcessW
CreateProcessW.restype = BOOL
CreateProcessW.errcheck = _errcheck_bool

# BOOL CreateProcessAsUserW(
#   HANDLE                hToken,
#   LPCWSTR               lpApplicationName,
#   LPWSTR                lpCommandLine,
#   LPSECURITY_ATTRIBUTES lpProcessAttributes,
#   LPSECURITY_ATTRIBUTES lpThreadAttributes,
#   BOOL                  bInheritHandles,
#   DWORD                 dwCreationFlags,
#   LPVOID                lpEnvironment,
#   LPCWSTR               lpCurrentDirectory,
#   LPSTARTUPINFOW        lpStartupInfo,
#   LPPROCESS_INFORMATION lpProcessInformation
# );
CreateProcessAsUserW = windll.kernel32.CreateProcessAsUserW
CreateProcessAsUserW.restype = BOOL
CreateProcessAsUserW.errcheck = _errcheck_bool

# BOOL TerminateProcess(
#   INTPTR  hProcess,
#   UINT    uExitCode,
# );
TerminateProcess = windll.kernel32.TerminateProcess
TerminateProcess.restype = BOOL
TerminateProcess.errcheck = _errcheck_bool

# DWORD WaitForSingleObject(
#   HANDLE hHandle,
#   DWORD  dwMilliseconds
# );
WaitForSingleObject = windll.kernel32.WaitForSingleObject
WaitForSingleObject.restype = DWORD
WaitForSingleObject.argtypes = (
    HANDLE,
    DWORD
)

# BOOL SetStdHandle(
#   DWORD nStdHandle
#   HANDLE hHandle,
# );
GetStdHandle = windll.kernel32.GetStdHandle
GetStdHandle.argtype = [
    DWORD,
    HANDLE,
]
GetStdHandle.restype = BOOL

# HANDLE GetStdHandle(
#   _In_ DWORD nStdHandle
# );
GetStdHandle = windll.kernel32.GetStdHandle
GetStdHandle.argtype = [DWORD]
GetStdHandle.restype = HANDLE

# BOOL CloseHandle(
#   HANDLE hObject
# );
CloseHandle = windll.kernel32.CloseHandle
CloseHandle.argtypes = (
    HANDLE,  # hObject
)
CloseHandle.restype = BOOL
CloseHandle.errcheck = _errcheck_bool

# BOOL WINAPI CreatePipe(
#   _Out_    PHANDLE               hReadPipe,
#   _Out_    PHANDLE               hWritePipe,
#   _In_opt_ LPSECURITY_ATTRIBUTES lpPipeAttributes,
#   _In_     DWORD                 nSize
# );
CreatePipe = windll.kernel32.CreatePipe
CreatePipe.argtype = [POINTER(HANDLE), POINTER(HANDLE), PVOID, DWORD]
CreatePipe.restype = BOOL
CreatePipe.errcheck = _errcheck_bool

# HANDLE CreateFileW(
#   LPCWSTR               lpFileName,
#   DWORD                 dwDesiredAccess,
#   DWORD                 dwShareMode,
#   LPSECURITY_ATTRIBUTES lpSecurityAttributes,
#   DWORD                 dwCreationDisposition,
#   DWORD                 dwFlagsAndAttributes,
#   HANDLE                hTemplateFile
# );
CreateFileW = windll.kernel32.CreateFileW  # <-- Unicode version!
CreateFileW.restype = HANDLE
CreateFileW.argtype = [
    LPCWSTR,
    DWORD,
    DWORD,
    POINTER(c_void_p),
    DWORD,
    DWORD,
    HANDLE
]

# BOOL PeekNamedPipe(
#   HANDLE  hNamedPipe,
#   LPVOID  lpBuffer,
#   DWORD   nBufferSize,
#   LPDWORD lpBytesRead,
#   LPDWORD lpTotalBytesAvail,
#   LPDWORD lpBytesLeftThisMessage
# );
PeekNamedPipe = windll.kernel32.PeekNamedPipe
PeekNamedPipe.restype = BOOL
PeekNamedPipe.errcheck = _errcheck_bool
PeekNamedPipe.argtypes = (
    HANDLE,
    LPVOID,
    DWORD,
    wintypes.LPDWORD,
    wintypes.LPDWORD,
    wintypes.LPDWORD
)

# BOOL ReadFile(
#   HANDLE       hFile,
#   LPVOID       lpBuffer,
#   DWORD        nNumberOfBytesToRead,
#   LPDWORD      lpNumberOfBytesRead,
#   LPOVERLAPPED lpOverlapped
# );

ReadFile = windll.kernel32.ReadFile
ReadFile.restype = BOOL
ReadFile.errcheck = _errcheck_bool
ReadFile.argtypes = (
    HANDLE,  # hObject
    LPVOID,
    DWORD,
    wintypes.LPDWORD,
    POINTER(c_void_p)
)

# BOOL WriteFile(
#   HANDLE       hFile,
#   LPCVOID      lpBuffer,
#   DWORD        nNumberOfBytesToWrite,
#   LPDWORD      lpNumberOfBytesWritten,
#   LPOVERLAPPED lpOverlapped
# );
WriteFile = windll.kernel32.WriteFile
WriteFile.restype = BOOL
WriteFile.errcheck = _errcheck_bool
WriteFile.argtypes = (
    HANDLE,
    LPCVOID,
    DWORD,
    wintypes.LPDWORD,
    POINTER(c_void_p)
)

# HRESULT WINAPI CreatePseudoConsole(
#     _In_ COORD size,
#     _In_ HANDLE hInput,
#     _In_ HANDLE hOutput,
#     _In_ DWORD dwFlags,
#     _Out_ HPCON* phPC
# );
CreatePseudoConsole = windll.kernel32.CreatePseudoConsole
CreatePseudoConsole.argtype = [COORD, HANDLE, HANDLE, DWORD, POINTER(HPCON)]
CreatePseudoConsole.restype = HRESULT


# HRESULT WINAPI ResizePseudoConsole(
#     _In_ HANDLE phPC,
#     _In_ COORD size,
# );
ResizePseudoConsole = windll.kernel32.ResizePseudoConsole
ResizePseudoConsole.argtype = [HANDLE, COORD]
ResizePseudoConsole.restype = HRESULT


# void WINAPI ClosePseudoConsole(
#     _In_ HPCON hPC
# );
ClosePseudoConsole = windll.kernel32.ClosePseudoConsole
ClosePseudoConsole.argtype = [HPCON]

# BOOL WINAPI SetConsoleMode(
#   _In_ HANDLE hConsoleHandle,
#   _In_ DWORD  dwMode
# );
SetConsoleMode = windll.kernel32.SetConsoleMode
SetConsoleMode.argtype = [HANDLE, DWORD]
SetConsoleMode.restype = BOOL
SetConsoleMode.errcheck = _errcheck_bool

# BOOL WINAPI GetConsoleMode(
#   _In_  HANDLE  hConsoleHandle,
#   _Out_ LPDWORD lpMode
# );
GetConsoleMode = windll.kernel32.GetConsoleMode
GetConsoleMode.argtype = [HANDLE, wintypes.LPDWORD]
GetConsoleMode.restype = BOOL
# GetConsoleMode.errcheck = _errcheck_bool

# DECLSPEC_ALLOCATOR LPVOID HeapAlloc(
#   HANDLE hHeap,
#   DWORD  dwFlags,
#   SIZE_T dwBytes
# );
HeapAlloc = windll.kernel32.HeapAlloc
HeapAlloc.restype = LPVOID
HeapAlloc.argtypes = [HANDLE, DWORD, SIZE_T]

# BOOL HeapFree(
#   HANDLE                 hHeap,
#   DWORD                  dwFlags,
#   _Frees_ptr_opt_ LPVOID lpMem
# );
HeapFree = windll.kernel32.HeapFree
HeapFree.restype = BOOL
HeapFree.argtypes = [HANDLE, DWORD, LPVOID]
HeapFree.errcheck = _errcheck_bool

# HANDLE GetProcessHeap(
#
# );
GetProcessHeap = windll.kernel32.GetProcessHeap
GetProcessHeap.restype = HANDLE
GetProcessHeap.argtypes = []

# void WINAPI SetLastError(
#   _In_ DWORD dwErrCode
# );
SetLastError = windll.kernel32.SetLastError
SetLastError.argtype = [DWORD]

# void DeleteProcThreadAttributeList(
#   LPPROC_THREAD_ATTRIBUTE_LIST lpAttributeList
# );
DeleteProcThreadAttributeList = windll.kernel32.DeleteProcThreadAttributeList
DeleteProcThreadAttributeList.argtype = [
    POINTER(PVOID),
]

AllocConsole = windll.kernel32.AllocConsole
AllocConsole.restype = BOOL

FreeConsole = windll.kernel32.FreeConsole
FreeConsole.restype = BOOL

ShowWindow = windll.user32.ShowWindow
ShowWindow.argtype = [HANDLE, DWORD]
ShowWindow.restype = BOOL

GetConsoleWindow = windll.kernel32.GetConsoleWindow
GetConsoleWindow.restype = HANDLE


LogonUserW = windll.advapi32.LogonUserW
LogonUserW.argtypes = [LPCWSTR, LPCWSTR, LPCWSTR, DWORD, DWORD, HANDLE]
LogonUserW.restype = BOOL


class LUID(Structure):
    _fields_ = [
        ('low_part', wintypes.DWORD),
        ('high_part', wintypes.LONG),
        ]

    def __eq__(self, other):
        return (
            self.high_part == other.high_part and
            self.low_part == other.low_part
            )

    def __ne__(self, other):
        return not (self==other)

SE_PRIVILEGE_ENABLED            = (0x00000002)
LookupPrivilegeValueW = windll.advapi32.LookupPrivilegeValueW
LookupPrivilegeValueW.argtypes = [LPWSTR, LPWSTR, POINTER(LUID)]
LookupPrivilegeValueW.restype = wintypes.BOOL

class LUID_AND_ATTRIBUTES(Structure):
    _fields_ = [
        ('LUID', LUID),
        ('attributes', wintypes.DWORD),
        ]

    def is_enabled(self):
        return bool(self.attributes & SE_PRIVILEGE_ENABLED)

    def enable(self):
        self.attributes |= SE_PRIVILEGE_ENABLED

    def get_name(self):
        size = wintypes.DWORD(10240)
        buf = create_unicode_buffer(size.value)
        res = LookupPrivilegeValueW(None, self.LUID, buf, size)
        if res == 0: raise RuntimeError
        return buf[:size.value]

    def __str__(self):
        res = self.get_name()
        if self.is_enabled(): res += ' (enabled)'
        return res

class TOKEN_PRIVILEGES(Structure):
    _fields_ = [
        ('count', wintypes.DWORD),
        ('privileges', LUID_AND_ATTRIBUTES*0),
        ]

    def get_array(self):
        array_type = LUID_AND_ATTRIBUTES*self.count
        privileges = cast(self.privileges, POINTER(array_type)).contents
        return privileges

    def __iter__(self):
        return iter(self.get_array())

PTOKEN_PRIVILEGES = POINTER(TOKEN_PRIVILEGES)

PSID = LPVOID

class SID_AND_ATTRIBUTES(Structure):
    _fields_ = [
               ('sid',         PSID),
               ('attributes',  DWORD)
               ]     

class TOKEN_USER(Structure):
    _fields_ = [
        ('user', SID_AND_ATTRIBUTES)
        ]


GetCurrentProcess = windll.kernel32.GetCurrentProcess
GetCurrentProcess.restype = HANDLE

NtQueryInformationProcess = windll.ntdll.NtQueryInformationProcess
NtQueryInformationProcess.argtypes = [HANDLE, INT, PVOID, ULONG, POINTER(ULONG)]


TOKEN_QUERY = 0x0008
TOKEN_ADJUST_PRIVILEGES = 0x0020
OpenProcessToken = windll.advapi32.OpenProcessToken
OpenProcessToken.argtypes = [HANDLE, DWORD, HANDLE]
OpenProcessToken.restype = BOOL

GetTokenInformation = windll.advapi32.GetTokenInformation
GetTokenInformation.argtypes = [wintypes.HANDLE, c_uint, c_void_p, wintypes.DWORD, POINTER(wintypes.DWORD)]
GetTokenInformation.restype = wintypes.BOOL

class TOKEN_INFORMATION_CLASS:
    TokenUser = 1
    TokenGroups = 2
    TokenPrivileges = 3

WinLocalSystemSid = 22
WinLocalServiceSid = 23

IsWellKnownSid = windll.advapi32.IsWellKnownSid
IsWellKnownSid.argtypes = [PSID, c_uint]
IsWellKnownSid.restype = wintypes.BOOL

LookupPrivilegeValueW = windll.advapi32.LookupPrivilegeValueW
LookupPrivilegeValueW.argtypes = [LPWSTR, LPWSTR, POINTER(LUID)]
LookupPrivilegeValueW.restype = wintypes.BOOL


AdjustTokenPrivileges = windll.advapi32.AdjustTokenPrivileges
AdjustTokenPrivileges.restype = wintypes.BOOL
AdjustTokenPrivileges.argtypes = [HANDLE, BOOL, PTOKEN_PRIVILEGES, DWORD, PTOKEN_PRIVILEGES, POINTER(DWORD)]



