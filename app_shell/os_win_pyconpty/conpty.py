import time
from threading import Thread
from win32.native import *
from  ctypes import *

class ConPty(Thread):

    def __init__(self, cmd, cols, rows):
        # Call the Thread class's init function
        Thread.__init__(self)

        # Setup handles
        self._hPC = HPCON()                                     # handle to the pseudoconsole device
        self._ptyIn = wintypes.HANDLE(INVALID_HANDLE_VALUE)     # handle used to communicate with the pseudoconsole
        self._ptyOut = wintypes.HANDLE(INVALID_HANDLE_VALUE)    # handle used to communicate with the pseudocnosole
        self._cmdIn = wintypes.HANDLE(INVALID_HANDLE_VALUE)     #
        self._cmdOut = wintypes.HANDLE(INVALID_HANDLE_VALUE)    #
        self._cmd = cmd
        self._cols = cols
        self._rows = rows
        self._consoleSize = COORD()
        self._mem = None

    def run(self):
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
            print('oops, something went wrong...create pseudoconsole failed')

        # Initialize startup info
        self._startupInfoEx = STARTUPINFOEX()
        self._startupInfoEx.StartupInfo.cb = sizeof(STARTUPINFOEX)
        self.__initStartupInfoExAttachedToPseudoConsole()
        self._lpProcessInformation = PROCESS_INFORMATION()

        # Create process
        hr = CreateProcess(None,                                        # _In_opt_      LPCTSTR
                            self._cmd,                                   # _Inout_opt_   LPTSTR
                            None,                                        # _In_opt_      LPSECURITY_ATTRIBUTES
                            None,                                        # _In_opt_      LPSECURITY_ATTRIBUTES
                            False,                                       # _In_          BOOL
                            EXTENDED_STARTUPINFO_PRESENT,                # _In_          DWORD
                            None,                                        # _In_opt_      LPVOID
                            None,                                        # _In_opt_      LPCTSTR
                            byref(self._startupInfoEx.StartupInfo),      # _In_          LPSTARTUPINFO
                            byref(self._lpProcessInformation))           # _Out_

        # Check if process is up
        if hr == 0x0:
            print('oops, failed to execute ' + self._cmd + ': ' + str(hr))

        WaitForSingleObject(self._lpProcessInformation.hThread, 10 * 1000)

    def __initStartupInfoExAttachedToPseudoConsole(self):
        dwAttributeCount = 1
        dwFlags = 0
        lpSize = PVOID()

        # call with null lpAttributeList to get lpSize
        try:
            ok = InitializeProcThreadAttributeList(None, dwAttributeCount, dwFlags, byref(lpSize))
            if ok == 0x0:
                print('failed to call InitializeProcThreadAttributeList')
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
            print('failed to call InitializeProcThreadAttributeList')
        ok = UpdateProcThreadAttribute(self._startupInfoEx.lpAttributeList, DWORD(0), DWORD(PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE),
                                  self._hPC, sizeof(self._hPC), None, None)

        if ok == 0x0:
            print('failed to call UpdateProcThreadAttribute')

    def close(self):
        # cleanup
        CloseHandle(self._cmdIn)
        CloseHandle(self._cmdOut)
        DeleteProcThreadAttributeList(self._startupInfoEx.lpAttributeList)
        HeapFree(GetProcessHeap(), 0, self._mem)
        ClosePseudoConsole(self._hPC)
        CloseHandle(self._lpProcessInformation.hThread)
        CloseHandle(self._lpProcessInformation.hProcess)

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
                print('failed to read: ' + str(hr))
            return lpBuffer.raw[:lpNumberOfBytesRead.value]
        else:
            return ""

    def write(self, data):
        lpBuffer = create_string_buffer(data.encode('utf-8'))
        lpNumberOfBytesWritten = DWORD()
        hr = WriteFile(self._cmdIn,            # Handle to the file or i/o device
                  lpBuffer,                     # Pointer to the buffer that contains the data to be written
                  sizeof(lpBuffer),             # Number of bytes to write
                  lpNumberOfBytesWritten,       # Number of bytes written
                  NULL_PTR)                     # Not used
        if hr == 0x0:
            print('failed to write: ' + str(hr))


if __name__ == '__main__':

    # Create a cmd.exe pty
    print("[!] creating pty")
    pty = ConPty("c:\\windows\\system32\\cmd.exe", 80, 60)
    pty.start()
    time.sleep(1)
    print("[!] pty created")
    output = pty.read()
    print('output1: ' + output)
    time.sleep(10)
    pty.write("whoami\r\n")
    time.sleep(10)
    output2 = pty.read()
    print('output2: ' + output2)
    time.sleep(10)
    output3 = pty.read()
    print('output3: ' + output3)
    print('[!] cleanup')
    pty.close()
