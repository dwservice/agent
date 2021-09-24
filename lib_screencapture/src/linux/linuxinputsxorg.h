
/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/
#if defined OS_XORG

using namespace std;
#include <string.h>
#include <map>
#include <cstdlib>
#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <X11/keysym.h>
#include <X11/XKBlib.h>
#include <X11/extensions/XTest.h>
#include <X11/extensions/XShm.h>
#include "linuxkeysym2ucs.h"
#include "../common/util.h"


#ifndef LINUXINPUTS_H_
#define LINUXINPUTS_H_

class LinuxInputs{

public:
	LinuxInputs(void );
    ~LinuxInputs( void );
    void setDisplay(Display *d, Window r);
    void keyboardChanged();
    void keyboard(const char* type,const char* key, bool ctrl, bool alt, bool shift, bool command);
    void mouse(MONITORS_INFO_ITEM* moninfoitem, int x, int y, int button, int wheel, bool ctrl, bool alt, bool shift, bool command);
    void copy();
    void paste();
    int getClipboardText(wchar_t** wText);
    void setClipboardText(wchar_t* wText);


private:
    //bool isKeyboardChanged();
    void loadKeyMap();
    void unloadKeyMap();
	KeySym getKeySym(const char* key);
	void clearCustomKeyUnicode();
	KeyCode createCustomKeyUnicode(int uc);
	void ctrlaltshift(bool ctrl, bool alt, bool shift);
	void mouseMove(int x,int y);
	void mouseButton(int button,bool press);

	Display *xdpy;
	Window root;
    typedef struct{
		int unicode;
		KeySym sym;
		KeyCode code;
		int modifier;
	} KEYMAP;
	map<int,KEYMAP*> hmUnicodeMap;
    bool mousebtn1Down;
    bool mousebtn2Down;
    bool mousebtn3Down;
    bool ctrlDown;
    bool altDown;
    bool shiftDown;
    int max_grp;
    KeyCode kccustom;
    bool kccustominit;
    TimeCounter skipKeyboardChangedCounter;

};

#endif /* LINUXINPUTS_H_ */
#endif

