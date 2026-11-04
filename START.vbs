On Error Resume Next
Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
strPath = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = strPath

' 1. Check if banklycs.exe and msedge are already running
Set objWMIService = GetObject("winmgmts:\\.\root\cimv2")
isServerRunning = False
isEdgeRunning = False

If Not objWMIService Is Nothing Then
    Set colProcesses = objWMIService.ExecQuery("Select * from Win32_Process Where Name = 'banklycs.exe'")
    If Not colProcesses Is Nothing Then
        If colProcesses.Count > 0 Then isServerRunning = True
    End If

    Set colEdge = objWMIService.ExecQuery("Select * from Win32_Process Where Name = 'msedge.exe' and CommandLine Like '%127.0.0.1:5050%'")
    If Not colEdge Is Nothing Then
        If colEdge.Count > 0 Then isEdgeRunning = True
    End If
End If

' 2. Launch engine silently if not already running
If Not isServerRunning Then
    WshShell.Run chr(34) & strPath & "\engine\banklycs.exe" & chr(34) & " --no-browser", 0, False
    WScript.Sleep 600
End If

' 3. Bring existing window to focus or launch single instance
If isEdgeRunning Then
    WshShell.AppActivate "ProPresenter7 - Lyric Injector"
Else
    WshShell.Run "msedge.exe --app=http://127.0.0.1:5050 --start-maximized", 3, False
End If

Set WshShell = Nothing
