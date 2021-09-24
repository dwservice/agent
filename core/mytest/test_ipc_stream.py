# -*- coding: utf-8 -*-
'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''


import ipc
import json
import time
import utils

TEST_TYPE="ReadAndWrite"
#TEST_TYPE="SendStream"
TEST_NUM=100

class TestSendStream(ipc.ChildProcessThread):
    
    def run(self):
        strm = self.get_stream()
        strmother = strm.read_obj()
        while True:
            s = strmother.read()
            if s is None:
                break
            print "READ " + s
        strmother.close()
        strm.close()
        time.sleep(1)

class TestReadAndWrite(ipc.ChildProcessThread):
    
    def run(self):
        strm = self.get_stream()    
        print "WAIT READ..."
        time.sleep(0.1)
        #time.sleep(10)
        
        print "START READ"
        cnt=0
        tm=utils.get_time()
        ar=[]
        while True:
            try:
                dt=strm.read_bytes()
                #print "READ: "+ str(cnt)
            except Exception as e:
                print("READ ERROR: " + str(e) + "  CNT:" + str(cnt))
                break
            if dt is None:
                break 
            ar.append(dt)
            cnt+=1       
                
        #print("***************")
        print("READ TIME:" + str(utils.get_time()-tm) + "  CNT:" + str(cnt))
        print "END READ"
        
        if True:
            print("READ CHECK...")
            bok=True
            cnt=0
            for i in range(TEST_NUM):
                try:
                    s=ar[i]
                    cnt+=1
                    if s!="TEST" + str(i+1):
                        bok=False
                        print ("ERRORE: '" + s + "' != 'TEST" + str(i+1) + "'")
                except:
                    bok=False
                    print ("ERRORE: TEST out of range: " + str(i+1) + "'")
                    break
            if bok:
                print "READ CHECK OK - CNT:" + str(cnt)         
        else:
            print "NO READ CHECK"
        
        strm.close()
        time.sleep(1)

if __name__ == "__main__":    
    ipc.initialize()
    print ("BEGIN")
    
             
    p=ipc.Process("mytest.test_ipc_stream", "Test" + TEST_TYPE)
    lstrm = p.start()
          
    if TEST_TYPE=="ReadAndWrite":
          
        time.sleep(1)            
        print "START WRITE"
        tm=utils.get_time()
        cnt=0
        try:        
            for i in range(TEST_NUM):
                lstrm.write_bytes("TEST" + str(i+1))
                cnt+=1
                #print "WRITE: "+ str(i)
        except Exception as e:
            print("WRITE ERROR: " + str(e) + "  CNT:" + str(cnt))
        print("WRITE TIME:" + str(utils.get_time()-tm) + "  CNT:" + str(cnt))
        print "END WRITE"
    elif TEST_TYPE=="SendStream":
        
        lstrmother = ipc.Stream({"size":20})
        lstrm.write_obj(lstrmother)
        
        #time.sleep(2)
        bt="0123456789"*2
        lstrmother.write(bt)
        lstrmother.close()
    
    
    lstrm.close()
    
    
    print ("PARENT CLOSE")    
    #WAIT REMOVE IPC
    p.join()
    lstrm._destroy()
    time.sleep(4)
    print ("END")
    ipc.terminate()

    