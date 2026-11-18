Set shell = CreateObject("WScript.Shell")
WScript.Sleep 15000
shell.CurrentDirectory = "C:\Users\athom\Tools\DWService"
shell.Run "powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File ""C:\Users\athom\Tools\DWService\run-portable.ps1""", 0, False