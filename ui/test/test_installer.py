# -*- coding: utf-8 -*-
'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import sys
import installer

        
if __name__ == "__main__":
    arotps={}
    arotps["gui"]=True
    arotps["mock"]=True #shows only steps it is do nothing
    #arotps["lang"]="fr"
    
    #TEST install.json
    arij={}
    #arij["name"]="Test";
    arij["title"]="Test Title";
    #arij["mode"]="run";
    #arij["runputcode"]=True;
    #arij["lang"]="en"   
    #arij["topimage"]="image.bmp"
    #arij["logo"]="logo.ico"
    arij["welcometext"]="Hi this is a welcome message\n\ntest message"
    arij["runtoptext"]="runtoptext"
    arij["runbottomtext"]="runbottomtext"
    arij["leftcolor"]="ff4400"
    arotps["install.json"]=arij
    
    
    '''
    arij1={}
    arij1["lang"]="fr" 
    arotps["install.json"]=arij1
    '''
    
    i = installer.Install()
    i.start(arotps)    
    sys.exit(0)
            


