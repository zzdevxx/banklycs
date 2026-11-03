Set WshShell = CreateObject("WScript.Shell")
strPath = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = strPath
WshShell.Run chr(34) & strPath & "\engine\banklycs.exe" & chr(34), 0, False
WScript.Sleep 400
WshShell.Run "msedge.exe --app=http://127.0.0.1:5050 --start-maximized", 3, False
Set WshShell = Nothing
