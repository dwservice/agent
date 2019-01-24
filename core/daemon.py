# -*- coding: utf-8 -*-

'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''

import os, sys
ppid = os.fork()
if ppid == 0:
	stdin = 0
	stdout = 1
	stderr = 2
	env = os.environ.copy()
	os.dup2(stderr, stdout)
	arg=[]
	i=0;
	for v in sys.argv:
		if i>=1:
			arg.append(v)
		i+=1
	os.execv(sys.argv[1],arg)
	os._exit(0)
sys.exit(0)
