# -*- coding: utf-8 -*-
'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import ipc
import time
    
    
class Test(ipc.ChildProcessThread):
    
    def run(self):
        strm = self.get_stream()
        mp1 = strm.read_obj()
        mp1.seek(0)
        s = mp1.read(11)
        print("CHILD READ: " + s)
        mp1.write("HELLO PARENT")        
        mp1.close()
        strm.close()
        print ("CHILD CLOSE")
        time.sleep(2)
    
    

if __name__ == "__main__":    
    ipc.initialize()
    print ("BEGIN")
    p=ipc.Process("mytest.test_ipc_memmap", "Test")
    lstrm = p.start()
    
    mp = ipc.MemMap(512*1024)
    lstrm.write_obj(mp)
    mp.seek(0)
    mp.write("HELLO CHILD")
    time.sleep(1)
    s = mp.read(12)
    print("PARENT READ: " + s)
    time.sleep(1)
    
    mp.close()
    lstrm.close()
    
    
    print ("PARENT CLOSE")
    
    #WAIT REMOVE IPC
    p.join()
    time.sleep(2)
    
    print ("END")
    ipc.terminate()

