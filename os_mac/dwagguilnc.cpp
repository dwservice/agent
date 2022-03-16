/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <libgen.h>

int main(int argc, char **argv) {
	char cmd_to_execute[4096];
	strcpy(cmd_to_execute,"");
	strcat(cmd_to_execute, dirname(argv[0]));
	strcat(cmd_to_execute, "/dwagsvc run");
	system(cmd_to_execute);
	return 0;
}
