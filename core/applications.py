# -*- coding: utf-8 -*-

'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''

import agent
import platform

def get_supported(agt):
    arSupportedApplications=[]
    arSupportedApplications.append("filesystem")
    arSupportedApplications.append("texteditor")
    arSupportedApplications.append("logwatch")
    arSupportedApplications.append("resource")
    arSupportedApplications.append("desktop")
    if agent.is_linux() or agent.is_mac() or (agent.is_windows() and platform.release() == '10'):
        arSupportedApplications.append("shell")
    return arSupportedApplications
        