from datetime import datetime, timedelta
# from datetime import date
import dateutil.parser as dateparser
import os.path
import os, time
import xml.etree.ElementTree as ET

csvdate = "29.07.2022"
googledate = "2022-04-28T13:00:00+02:00"

csvdate = csvdate.rstrip()
if ":" in csvdate:
    csvdate += "+02:00"
# print("csv date before parsing: ",csvdate)
print(dateparser.parse(csvdate, dayfirst=True).isoformat())
print(dateparser.parse(csvdate).isoformat())

(mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime) = os.stat("outlook.csv")
print("last modified: %s" % time.ctime(mtime))
synctime = os.path.getctime("outlook.csv")
text = "last Outlook sync. " + str(time.ctime(mtime))

start = datetime.now()
end = start + timedelta(minutes=30)
start = start.isoformat()
end = end.isoformat()

print(start)
print(end)

print(text)


def createEventCaption(oldcaption, location):
    root = ET.parse('keywords.xml').getroot()
    # keywords = root.find('keywords')
    # print(root.text)
    keywordMatch = False
    for kwType in root.findall('type'):
        # print(kwType.text)
        desc = kwType.find('description').text
        # print(desc)
        typeUsed = False
        for keyword in kwType.findall('keyword'):
            # print(keyword.text)
            if keyword.text in oldcaption and not typeUsed:
                if keywordMatch:  # more than one keyword match
                    newcaption = newcaption + " " + desc
                else:
                    newcaption = desc
                keywordMatch = True
                typeUsed = True
    if not keywordMatch:
        newcaption = "Termin"

    if "Microsoft Teams-Besprechung" in location:
        newlocation = "Meeting"
    return newcaption, newlocation


print(createEventCaption("Dow Leuna Simoreg Steuerung Umrichtertausch", "Microsoft Teams-Besprechung"))
(mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime) = os.stat("outlook.csv")
# print("last modified: %s" % time.ctime(mtime))
text = "last Outlook sync. " + str(time.ctime(mtime))
today = datetime.today()
year = today.strftime("%Y")
month = today.strftime("%m")
day = today.strftime("%d")
start = datetime(int(year),int(month),int(day),4,30)
end = start + timedelta(minutes=30)
start = start.isoformat()
end = end.isoformat()

print(start)
print(end)
# d1 = today.strftime("%d/%m/%Y")
# print(today)
