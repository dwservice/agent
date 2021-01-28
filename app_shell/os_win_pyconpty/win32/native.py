# -*- coding: utf-8 -*-

'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
from ctypes import Structure, POINTER, windll, c_void_p, c_char_p, c_size_t, HRESULT, WinError, wintypes
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

# BOOL CreateProcessA(
#   LPCTSTR                 lpApplicationName,
#   LPTSTR                  lpCommandLine,
#   LPSECURITY_ATTRIBUTES   lpProcessAttributes,
#   LPSECURITY_ATTRIBUTES   lpThreadAttributes,
#   BOOL                    bInheritHandles,
#   DWORD                   dwCreationFlags,
#   LPVOID                  lpEnvironment,
#   LPCTSTR                 lpCurrentDirectory,
#   LPSTARTUPINFO           lpStartupInfo,
#   LPPROCESS_INFORMATION   lpProcessInformation,
#   );
CreateProcess = windll.kernel32.CreateProcessA
CreateProcess.restype = BOOL
CreateProcess.errcheck = _errcheck_bool

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
CreateProcessW = windll.kernel32.CreateProcessW  # <-- Unicode version!
CreateProcessW.restype = BOOL
CreateProcessW.errcheck = _errcheck_bool

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

GetModuleHandle = windll.kernel32.GetModuleHandleA
GetModuleHandle.argtype = [LPCWSTR]
GetModuleHandle.restype = HANDLE

GetProcAddress = windll.kernel32.GetProcAddress
GetProcAddress.argtype = [HANDLE, LPCWSTR]
GetProcAddress.restype = HANDLE