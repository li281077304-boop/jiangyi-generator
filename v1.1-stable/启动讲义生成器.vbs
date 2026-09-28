' Handout Generator Flash - silent launcher
' Double-click: start service (hidden console) and open browser automatically.
' The app.py itself also opens the browser when the port is ready.
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
base = fso.GetParentFolderName(WScript.ScriptFullName)
python = base & "\res\python\python.exe"
app = base & "\res\app\webapp\app.py"
shell.CurrentDirectory = base
If Not fso.FileExists(python) Then
    message = UnicodeText("7F3A,5C11,5185,7F6E,0020,0050,0079,0074,0068,006F,006E,0020,8FD0,884C,65F6,FF0C,65E0,6CD5,542F,52A8,8BB2,4E49,751F,6210,5668,3002") & vbCrLf & python & vbCrLf & _
        UnicodeText("8BF7,4ECE,5B8C,6574,0020,0057,0069,006E,0064,006F,0077,0073,0020,53D1,5E03,5305,91CD,65B0,89E3,538B,540E,518D,542F,52A8,3002")
    MsgBox message, vbExclamation, UnicodeText("8BB2,4E49,751F,6210,5668")
    WScript.Quit 2
End If
If Not fso.FileExists(app) Then
    MsgBox UnicodeText("53D1,5E03,5305,6587,4EF6,4E0D,5B8C,6574,FF0C,627E,4E0D,5230,5E94,7528,542F,52A8,7A0B,5E8F,3002") & vbCrLf & app, vbExclamation, UnicodeText("8BB2,4E49,751F,6210,5668")
    WScript.Quit 3
End If
shell.Run """" & python & """ """ & app & """", 0, False

Function UnicodeText(hexCodes)
    Dim pieces, piece, result
    result = ""
    pieces = Split(hexCodes, ",")
    For Each piece In pieces
        result = result & ChrW(CLng("&H" & piece))
    Next
    UnicodeText = result
End Function
