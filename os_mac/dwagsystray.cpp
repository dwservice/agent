/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/

#include <stdio.h>
#include <unistd.h>
#include <string.h>
#include <stdlib.h>

int main(int argc, char **argv) {
  char path_dwa[2048];
  char env_library[2048];
  char cmd_to_execute[2048];
  
  strcpy(path_dwa,"");
  strcat(path_dwa, argv[1]);
  
  strcpy(env_library,"DYLD_LIBRARY_PATH=");
  strcat(env_library, path_dwa);
  strcat(env_library, "/runtime/lib");
  
  strcpy(cmd_to_execute,"");
  strcat(cmd_to_execute, path_dwa);
  strcat(cmd_to_execute, "/runtime/bin/dwagent");
  
  
  chdir(path_dwa);
  char *args[] = {cmd_to_execute, (char*)"monitor.pyc", (char*)"systray", NULL};
  char *env[] = {env_library, NULL};
  execve(cmd_to_execute, args , env);
  

  return 0;
}