/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/

#include <stdio.h>
#include <unistd.h>
#include <string.h>
#include <stdlib.h>
#include <fstream>

int main(int argc, char **argv) {
  char path_dwa[2048];
  char env_library[2048];
  char path_check_file[2048];
  char cmd_to_execute[2048];
  
  strcpy(path_dwa,"");
  strcat(path_dwa, argv[1]);
  
  strcpy(path_check_file,"");
  strcat(path_check_file, path_dwa);
  strcat(path_check_file, "/guilnc.run");  
  
  strcpy(env_library,"DYLD_LIBRARY_PATH=");
  strcat(env_library, path_dwa);
  strcat(env_library, "/runtime/lib");
  
  strcpy(cmd_to_execute,"");
  strcat(cmd_to_execute, path_dwa);
  strcat(cmd_to_execute, "/runtime/bin/dwagent");
  
  //CHECK guilnc.run 
  while(true){
    std::ifstream f(path_check_file);
    if (f.good()){
        break;
    }
    sleep(1);
  }
  
  //printf("%s\n", path_dwa_runtime_library);
  //printf("%s\n", cmd_to_execute);
  
  std::ifstream f(path_check_file);
  if (f.good()){  
    //EXECUTE guilnc
    chdir(path_dwa);
    char *args[] = {cmd_to_execute, (char*)"agent.pyc", (char*)"guilnc", NULL};
    char *env[] = {env_library, NULL};
    execve(cmd_to_execute, args , env);
  }

  return 0;
}