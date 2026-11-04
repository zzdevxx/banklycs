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

    Set colEdge = objWMIService.ExecQuery("Select * from Win32_Process Where Name = 'msedge.exe' and CommandLine Like '%127.0.0.1:505%'")
    If Not colEdge Is Nothing Then
        If colEdge.Count > 0 Then isEdgeRunning = True
    End If
End If

' 2. Launch engine silently if not already running
If Not isServerRunning Then
    WshShell.Run chr(34) & strPath & "\engine\banklycs.exe" & chr(34) & " --no-browser", 0, False
    WScript.Sleep 600
End If

' 2b. Ask the engine which port it actually bound (it scans 5050-5055)
port = "5050"
portFile = strPath & "\engine\last_port.txt"
If fso.FileExists(portFile) Then
    Set ts = fso.OpenTextFile(portFile, 1, False)
    If Err.Number = 0 Then
        candidate = Trim(ts.ReadLine)
        ts.Close
        If IsNumeric(candidate) Then
            If CInt(candidate) > 0 Then port = CStr(CInt(candidate))
        End If
    End If
    On Error Resume Next
End If
serverUrl = "http://127.0.0.1:" & port

' 3. Bring existing window to focus or launch single instance
If isEdgeRunning Then
    WshShell.AppActivate "ProPresenter7 - Lyric Injector"
Else
    WshShell.Run "msedge.exe --app=" & serverUrl & " --start-maximized", 3, False
End If

Set WshShell = Nothing
