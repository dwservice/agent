# -*- coding: utf-8 -*-
'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import sys
import os
import configure

        
if __name__ == "__main__":
    i = configure.Configure()
    i._set_config_base_path(".." + os.sep + "core")
    i.start()    
    sys.exit(0)
            


