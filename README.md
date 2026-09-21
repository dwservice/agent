# DWService - Agent

This is [DWService](https://www.dwservice.net) agent for operative systems Linux, Mac and Windows.
The code is written in Python 3 and maintains a compatibility layer for Python 2; several libraries are written in C++.

## Start the agent

If you prefer you can start the agent from the sources but you keep in mind in this mode the agent does not update automatically, so you need to update sources manually every time. Before to start the agent you need to:
- Install python3
- Install g++/make (if Windows download [Mingw-w64](https://mingw-w64.org) version [64bit](https://sourceforge.net/projects/mingw-w64/files/Toolchains%20targetting%20Win64/Personal%20Builds/mingw-builds/8.1.0/threads-win32/sjlj/) or [32bit](https://sourceforge.net/projects/mingw-w64/files/Toolchains%20targetting%20Win32/Personal%20Builds/mingw-builds/8.1.0/threads-win32/sjlj/))
- To compile Wayland support on Linux, install libraries: `libpipewire-0.3-dev`, `libdbus-1-3`, and `libdbus-1-dev`
- Download agent source code ([zip](https://github.com/dwservice/agent/archive/master.zip) or git clone)
- Execute these commands from agent/make:

```bash
python3 ./compile_all.py; # Compile all c++ libraries.
python3 ./create_config.py; # Create Agent config.json in agent/core path.
```

Now you are ready to start the agent by execute this command from agent/core:

```
python3 ./agent.py;
```

If the agent still tries setting up a Xorg session on client connect, with Wayland active and even environment `XDG_SESSION_TYPE=wayland` set, try forcing Wayland in the agent configuration:
```diff
    "enabled": true,
    "debug_mode": true,
+     "desktop": {
+         "force_capturescreenlib": "wayland"
+     }
```

## Setup the agent for development

Thanks [Eclipse](https://www.eclipse.org) + [Pydev](https://marketplace.eclipse.org/content/pydev-python-ide-eclipse) and [CDT](https://marketplace.eclipse.org/content/complete-eclipse-cc-ide) you can develop the agent with only one IDE from your prefer operative system. You also need of python3 and g++/make (if Windows download [Mingw-w64](https://mingw-w64.org) version [64bit](https://sourceforge.net/projects/mingw-w64/files/Toolchains%20targetting%20Win64/Personal%20Builds/mingw-builds/8.1.0/threads-win32/sjlj/) or [32bit](https://sourceforge.net/projects/mingw-w64/files/Toolchains%20targetting%20Win32/Personal%20Builds/mingw-builds/8.1.0/threads-win32/sjlj/)) installed on your system. After configuring the IDE and importing the source code, you need to execute same scripts of **"Start the agent"** section.

You can read the [guide on the wiki](https://github.com/dwservice/agent/wiki/Setup-the-agent-for-development) to learn how to setup the agent for development.

## License Agreement

This software is free and open source. 
It consists of one core component released under the MPLv2 license, and several libraries and components defined "app" that could be governed by different licenses. you can read the "LICENSE" file in each folder.
