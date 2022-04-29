Attribute VB_Name = "Modul2"
Sub cal_export_items()

Dim olApp As Object
Dim olNS As Object
Dim FromDate As Date
Dim ToDate As Date
Dim logSTR, sFilter As String
Dim My_filenumber As Integer
Dim ResItems As Outlook.Items
Dim CalItems As Outlook.Items
Dim olFolder As Outlook.MAPIFolder
Dim oFilterAppointments As Object
Dim currentAppointment As Object
Dim EventCounter As Integer
Dim Text, FileName As String


'change values to adapt the script
FromDate = Date
ToDate = FromDate + 100
FileName = "C:\UserData\z003sz1x\OneDrive - Siemens AG\Dokumente\Temp\outlook.csv"
EventCounter = 0



My_filenumber = FreeFile
Set olApp = GetObject(, "Outlook.Application")
Set olNS = olApp.GetNamespace("MAPI")
Set olFolder = olNS.GetDefaultFolder(9)

'Sort all Items in Calendar and include Recurrences (only the recurring ones)
Set CalItems = olFolder.Items
CalItems.Sort "[Start]"
CalItems.IncludeRecurrences = True
Set currentAppointment = CalItems.Find("[Start] >= """ & FromDate & """ and [Start] <= """ & ToDate & """ And [IsRecurring] = True") 'apply a filter to all sorted items
Open FileName For Output As #My_filenumber
logSTR = "olApt.Subject;olApt.Start;olApt.End;olApt.Location" 'write file header (.csv format, comma separated)
Print #My_filenumber, logSTR
While TypeName(currentAppointment) <> "Nothing" 'no items left in filter --> end while
    logSTR = ""
    logSTR = logSTR & currentAppointment.Subject & ";"
    logSTR = logSTR & currentAppointment.Start & ";"
    logSTR = logSTR & currentAppointment.End & ";"
    logSTR = logSTR & currentAppointment.Location
    EventCounter = EventCounter + 1 'count all items from start to end
    Print #My_filenumber, logSTR 'write string to file
    Set currentAppointment = CalItems.FindNext() 'search for next item in filter
Wend

For Each olApt In olFolder.Items 'all normal items in calendar no recurring, simple start and end date with a subject and location
    If (olApt.Start >= FromDate And olApt.Start <= ToDate) Then
        logSTR = ""
        logSTR = logSTR & olApt.Subject & ";"
        logSTR = logSTR & olApt.Start & ";"
        logSTR = logSTR & olApt.End & ";"
        logSTR = logSTR & olApt.Location
        EventCounter = EventCounter + 1 'count all items from start to end
        Print #My_filenumber, logSTR 'write string to file
    End If
Next olApt
Close #My_filenumber

'Write a response to the user
Text = CStr(EventCounter) & " Kalendereinträge wurden exportiert!"
response = MsgBox(Text)
End Sub

