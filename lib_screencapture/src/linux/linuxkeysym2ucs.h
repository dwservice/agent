/*
 * This module converts keysym values into the corresponding ISO 10646-1
 * (UCS, Unicode) values.
 */

#if defined OS_LINUX

#include <X11/X.h>

long keysym2ucs(KeySym keysym);
KeySym ucs2keysym(long uc);

#endif
