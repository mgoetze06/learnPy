Private Sub Application_Startup()
    MsgBox "Foo"
    Call cal_export
End Sub

Sub cal_export()

Dim olApp As Object
Dim olNS As Object
Dim olFolder As Object
Dim FromDate As Date
Dim ToDate As Date
Dim logSTR As String
Dim My_filenumber As Integer
Dim File_Count As Integer

Set olApp = GetObject(, "Outlook.Application")
'If Err.Number > 0 Then Set olApp = CreateObject("Outlook.Application")
'On Error GoTo 0
File_Count = 0
FromDate = Date
ToDate = FromDate + 60
'response = MsgBox(ToDate)
My_filenumber = FreeFile

Set olNS = olApp.GetNamespace("MAPI")
Set olFolder = olNS.GetDefaultFolder(9).Items 'olFolderCalendar
olFolder.Sort "[Start]"
olFolder.IncludeRecurrences = True

'response = MsgBox("test")
'Open "C:\UserData\z003sz1x\OneDrive - Siemens AG\Dokumente\Temp\outlook.csv" For Output As #My_filenumber
Open "C:\Temp\outlook_sync\outlook.csv" For Output As #My_filenumber
'response = MsgBox("Datei geÃ¶ffnet")
logSTR = "olApt.Subject;olApt.Start;olApt.End;olApt.Location"
Print #My_filenumber, logSTR
For Each olApt In olFolder
'For Each olApt In olFolder.Items
    If (olApt.Start >= FromDate And olApt.Start <= ToDate) Then
        'response = MsgBox(olApt.Subject)
        logSTR = ""
        logSTR = logSTR & olApt.Subject & ";"
        logSTR = logSTR & olApt.Start & ";"
        logSTR = logSTR & olApt.End & ";"
        logSTR = logSTR & olApt.Location
        Print #My_filenumber, logSTR
        File_Count = File_Count + 1
    End If
Next olApt
Close #My_filenumber
'response = MsgBox("Datei geschlossen")
response = MsgBox(File_Count & " Termine (bis " & ToDate & ") exportiert")
End Sub

