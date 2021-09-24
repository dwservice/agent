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
        idx = self.get_arguments()[0]
        mp1 = strm.read_obj()
        
        
        if idx>1:
            time.sleep(1)
        
        print ("CHILD " + str(idx) + " ACQUIRE BEFORE")
        mp1.acquire()
        print ("CHILD " + str(idx) + " ACQUIRE AFTER")
        
        
        if idx==10:
            time.sleep(3)
            print ("CHILD " + str(idx) + " KILL")
            import os
            os.kill(os.getpid(), 9)
        
        
        print ("CHILD " + str(idx) + " SEEP 5s")
        time.sleep(5)
        
        #print ("CHILD KILL")
        #import os
        #os.kill(os.getpid(), 9)
        
        
        mp1.release()
        print ("CHILD " + str(idx) + " RELEASE")
        time.sleep(2)
        strm.close()
        print ("CHILD " + str(idx) + " CLOSE")
        time.sleep(2)
    
    
    

if __name__ == "__main__":
    
    ipc.initialize()
    print ("BEGIN")
    
    mp = ipc.RLock()
    
    
             
    p=ipc.Process("mytest.test_ipc_lock", "Test", [1])
    lstrm = p.start()    
    lstrm.write_obj(mp)
    
    '''
    p1=ipc.Process("mytest.test_ipc_lock", "Test", [2])
    lstrm1 = p1.start()    
    lstrm1.write_obj(mp)
    
    p2=ipc.Process("mytest.test_ipc_lock", "Test", [3])
    lstrm2 = p2.start()    
    lstrm2.write_obj(mp)
    '''
    
    time.sleep(2)
    
    print ("PARENT ACQUIRE BEFORE")
    mp.acquire()
    print ("PARENT ACQUIRE AFTER")
    
    time.sleep(2)
    
    mp.release()
    print ("PARENT RELEASE")
            
    print ("PARENT CLOSE")    
    lstrm.close()
    lstrm=None
    p.join()
    '''
    lstrm1.close()
    lstrm1=None
    p1.join()
    lstrm2.close()
    lstrm2=None
    p2.join()
    '''
    time.sleep(4)
    print ("END")
    #ipc.ipc_manager.destory()
    #time.sleep(2)    
    #print ("MANAGER DESTORY")
    ipc.terminate()





