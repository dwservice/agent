/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/

#include <windows.h>
#include <string>
#include <fstream>

using namespace std;

typedef void (*CallbackType)(const wchar_t*);

#ifndef MAIN_H_
#define MAIN_H_


extern "C"{
  bool checkUpdate();
  void setCallbackWriteLog(CallbackType callback);
}


#endif /* MAIN_H_ */
