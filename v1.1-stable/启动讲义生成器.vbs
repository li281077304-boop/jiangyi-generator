' Handout Generator Flash - silent launcher
' Double-click: start service (hidden console) and open browser automatically.
' The app.py itself also opens the browser when the port is ready.
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
base = fso.GetParentFolderName(WScript.ScriptFullName)
python = base & "\res\python\python.exe"
app = base & "\res\app\webapp\app.py"
shell.CurrentDirectory = base
shell.Run """" & python & """ """ & app & """", 0, False
