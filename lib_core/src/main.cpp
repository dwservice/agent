/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/

#include "main.h"

#if defined OS_WINDOWS
int wmain(int argc, wchar_t **argv) {
#else
	int main(int argc, char **argv) {
#endif
	return 0;
}
