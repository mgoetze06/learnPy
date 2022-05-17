from datetime import datetime, timedelta
# from datetime import date
import dateutil.parser as dateparser
import os.path
import os, time
import xml.etree.ElementTree as ET
import logging

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

test1 = "03.05.2022  08:00:00"
test2 = "03.05.2022  12:00:00"
if start > dateparser.parse(test1).isoformat():
    print(test1)
    print("Vergangenheit")

if start > dateparser.parse(test2).isoformat():
    print(test2)
    print("Zukunft")


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
outlook_time = mtime
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


logging.basicConfig(filename='outlook_sync_logging.log', encoding='utf-8', level=logging.DEBUG,format='%(asctime)s %(message)s')
logging.debug('This message should go to the log file')
logging.info('So should this')
logging.warning('And this, too')
logging.warning('%s before you %s', 'Look', 'leap!')



f = open("lastSync.txt",'w')
f.write("")
f.close()
def compareFileTimes(file1,file2):
    (mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime) = os.stat(file1)
    # print("last modified: %s" % time.ctime(mtime))
    #text = "last Outlook sync. " + str(time.ctime(mtime))
    time1 = mtime
    (mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime) = os.stat(file2)
    # print("last modified: %s" % time.ctime(mtime))
    #text = "last Outlook sync. " + str(time.ctime(mtime))
    time2 = mtime
    if time1 > time2:
        print("file1 is newer")
    else:
        print("file1 is older")

    return time1>time2

# d1 = today.strftime("%d/%m/%Y")
# print(today)

if compareFileTimes("outlook.csv","lastSync.txt"):
    print("i need to check for new events")