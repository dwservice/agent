# -*- coding: utf-8 -*-

'''
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''

import utils

def get_supported(agt):
    arSupportedApplications=[]
    arSupportedApplications.append("filesystem")
    arSupportedApplications.append("texteditor")
    arSupportedApplications.append("logwatch")
    arSupportedApplications.append("resource")
    arSupportedApplications.append("desktop")
    if utils.is_linux() or utils.is_mac() or utils.is_windows_10_or_later():
        arSupportedApplications.append("shell")
    return arSupportedApplications

