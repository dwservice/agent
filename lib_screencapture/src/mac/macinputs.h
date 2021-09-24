
/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/
#if defined OS_MAC

#include <mach/vm_map.h>
#include <Carbon/Carbon.h>
#include "../common/util.h"

#ifndef MACINPUTS_H_
#define MACINPUTS_H_

class MacInputs{

public:
	MacInputs(void );
    ~MacInputs( void );
    void keyboard(const char* type,const char* key, bool ctrl, bool alt, bool shift, bool command);
    void mouse(MONITORS_INFO_ITEM* moninfoitem, int x, int y, int factx, int facty, int button, int wheel, bool ctrl, bool alt, bool shift, bool command);
    void copy();
    void paste();
    int getClipboardText(wchar_t** wText);
    void setClipboardText(wchar_t* wText);


private:
    CGKeyCode keyCodeForCharWithLayout(const char c, const UCKeyboardLayout *uchrHeader);
    CGKeyCode keyCodeForChar(const char c);
    CGKeyCode getCGKeyCode(const char* key);
    void ctrlaltshift(bool ctrl, bool alt, bool shift, bool command);
    int getModifiers(bool ctrl, bool alt, bool shift, bool command);

    int mousex;
    int mousey;
    bool mousebtn1Down;
    bool mousebtn2Down;
    bool mousebtn3Down;
    bool commandDown;
    bool ctrlDown;
    bool altDown;
    bool shiftDown;

};

#endif /* LINUXINPUTS_H_ */
#endif

