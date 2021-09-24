# -*- coding: utf-8 -*-
'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import ipc

if __name__ == "__main__":
    
    ipc.initialize()
    print ("BEGIN")
    
    t1 = ipc.Property()
    fieldsdef=[]
    fieldsdef.append({"name":"status","size":1})
    fieldsdef.append({"name":"counter","size":10})
    fieldsdef.append({"name":"prova","size":5})
    t1.create("prova", fieldsdef)
    t1.set_property("status", "2")
    t1.set_property("counter", "0123456789")
    t1.set_property("counter", "012345")
    t1.close()
    
    t2 = ipc.Property()
    t2.open("prova")
    print t2.get_property("status")
    print t2.get_property("counter")
    t2.close()
    print ("END")
    ipc.terminate()





