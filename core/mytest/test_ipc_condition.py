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
        print ("CHILD ACQUIRE")
        mp1.acquire()
        print ("CHILD SLEEP 4s")
        
        time.sleep(4)
        
        mp1.notify_all()
        print ("CHILD NOTIFY ALL")
        mp1.release()
        time.sleep(2)
        strm.close()
        print ("CHILD CLOSE")
        time.sleep(2)
    

if __name__ == "__main__":
    ipc.initialize()
    print ("BEGIN")
    
    mp = ipc.Condition()
    print ("PARENT ACQUIRE")
    mp.acquire()     
    
             
    p=ipc.Process("mytest.test_ipc_condition", "Test")
    lstrm = p.start()    
    lstrm.write_obj(mp)      
   
    print ("PARENT WAIT 5s")
    mp.wait(5)    
    

    print ("PARENT RELEASE")        
    mp.release()        
    lstrm.close()    
    
    print ("PARENT CLOSE")    
    #WAIT REMOVE IPC
    p.join()
    time.sleep(4)    
    print ("END")
    ipc.terminate()






