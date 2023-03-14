/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/
#if defined OS_WINDOWS

#include <windows.h>
#include <string>
#include "../common/util.h"

#ifndef WINDOWSINPUTS_H_
#define WINDOWSINPUTS_H_

class WindowsInputs{

public:
	WindowsInputs(void );
    ~WindowsInputs( void );
    void keyboard(const char* type,const char* key, bool ctrl, bool alt, bool shift, bool command);
    void mouse(MONITORS_INFO_ITEM* moninfoitem, int x, int y, int button, int wheel, bool ctrl, bool alt, bool shift, bool command);
    void copy();
    void paste();

private:
    bool mousebtn1Down;
    bool mousebtn2Down;
    bool mousebtn3Down;
    bool commandDown;
    bool ctrlDown;
    bool altDown;
    bool shiftDown;

    void addCtrlAltShift(INPUT (&inputs)[20],int &p,bool ctrl, bool alt, bool shift, bool command);
    void sendInputs(INPUT (&inputs)[20],int max);
    bool isExtendedKey(int key);
    int getKeyCode(const char* key);
    void addInputMouse(INPUT (&inputs)[20],int &p,int x, int y,DWORD dwFlags,int mouseData,int tm);

};

#endif /* WINDOWSINPUTS_H_ */
#endif

