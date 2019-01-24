# DWService - Agent
This is [DWService](https://www.dwservice.net) agent for operative systems Linux, Mac and Windows.
The code is written in python2 and several libraries are written c++. 

## Start the agent
If you prefer you can start the agent from the sources but you keep in mind in this mode the agent does not update automatically, so you need to update sources manually every time. Before to start the agent you need to:
- Install python2.7
- Install g++/make (if Windows download [Mingw-w64](https://mingw-w64.org) version [64bit](https://sourceforge.net/projects/mingw-w64/files/Toolchains%20targetting%20Win64/Personal%20Builds/mingw-builds/8.1.0/threads-win32/sjlj/) or [32bit](https://sourceforge.net/projects/mingw-w64/files/Toolchains%20targetting%20Win32/Personal%20Builds/mingw-builds/8.1.0/threads-win32/sjlj/))
- Download agent source code ([zip](https://github.com/dwservice/agent/archive/master.zip) or git clone)
- Execute these commands from agent/make:

```
python2.7 compile_all.py (compile all c++ libraries)
python2.7 create_config.py (create config.json in agent/core path)
```

now you are ready to start the agent by execute this command from agent/core:

```
python2.7 agent.py
```


## Setup the agent for development
Thanks [Eclipse](https://www.eclipse.org) + [Pydev](https://marketplace.eclipse.org/content/pydev-python-ide-eclipse) and [CDT](https://marketplace.eclipse.org/content/complete-eclipse-cc-ide) you can develop the agent with only one IDE from your prefer operative system. You also need of python2.7 and g++/make (if Windows download [Mingw-w64](https://mingw-w64.org) version [64bit](https://sourceforge.net/projects/mingw-w64/files/Toolchains%20targetting%20Win64/Personal%20Builds/mingw-builds/8.1.0/threads-win32/sjlj/) or [32bit](https://sourceforge.net/projects/mingw-w64/files/Toolchains%20targetting%20Win32/Personal%20Builds/mingw-builds/8.1.0/threads-win32/sjlj/)) installed on your system. After configuring the IDE and importing the source code, you need to execute same scripts of **"Start the agent"** section.

You can read the [guide on the wiki](https://github.com/dwservice/agent/wiki/Setup-the-agent-for-development) to learn how to setup the agent for development.

## License Agreement
This software is free and open source. 
It consists of one core component released under the MPLv2 license, and several libraries and components defined "app" that could be governed by different licenses. you can read the "LICENSE" file in each folder.