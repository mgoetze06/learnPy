from __future__ import print_function

from datetime import datetime, timedelta
import os.path
import csv
import os, time  # get file creation time

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import xml.etree.ElementTree as ET
from datetime import date
import dateutil.parser as dateparser  # date conversion from csvdateformat to isoformat

# from cal_setup import get_calendar_service

# If modifying these scopes, delete the file token.json.
# SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
SCOPES = ['https://www.googleapis.com/auth/calendar']
debug = False


# todo create labels for calendar events --> not only blocked in google calendar but a hint to what the event is in work calendar e.g. meeting (teams), on-site event, boss ...

def parseCsvDateToIso(csvdate):
    csvdate = csvdate.rstrip()
    if ":" in csvdate:
        # csvdate already has a time --> need to add the timezone
        csvdate += "+02:00"
        converted = dateparser.parse(csvdate, dayfirst=True).isoformat()
    else:
        # csv date is without time --> parser adds 00:00:00 because no time is given
        converted = dateparser.parse(csvdate, dayfirst=True).isoformat()
        # add timezone afterwards, now there is a time with timezone --> matching google time
        converted += "+02:00"
    # print("csv date before parsing: ",csvdate)
    return converted


def createSyncEvent(service):
    (mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime) = os.stat("outlook.csv")
    # print("last modified: %s" % time.ctime(mtime))
    text = "last Outlook sync. " + str(time.ctime(mtime))
    today = datetime.today()
    year = today.strftime("%Y")
    month = today.strftime("%m")
    day = today.strftime("%d")
    start = datetime(int(year), int(month), int(day), 4, 30)
    end = start + timedelta(minutes=30)
    start = start.isoformat()
    end = end.isoformat()

    event_result = service.events().insert(calendarId='primary', body={
        "summary": text,
        "description": 'sync. from outlook calendar',
        "start": {
            "dateTime": start,
            "timeZone": 'Europe/Berlin'},
        "end": {
            "dateTime": end,
            "timeZone": 'Europe/Berlin'},
    }).execute()


def createEvent(csvEvent, service):
    # creates one hour event tomorrow 10 AM IST
    # d = datetime.now().date()
    # tomorrow = datetime(d.year, d.month, d.day, 10) + timedelta
    startTime = parseCsvDateToIso(csvEvent['olApt.Start'])
    endTime = parseCsvDateToIso(csvEvent['olApt.End'])
    summary, location = createEventCaption(csvEvent['olApt.Subject'], csvEvent['olApt.Location'])
    if location == "":
        location = "sync. from outlook calendar"
    # print(start)
    # print(end)

    event_result = service.events().insert(calendarId='primary', body={
        "summary": summary,
        "description": location,
        "start": {
            "dateTime": startTime,
            "timeZone": 'Europe/Berlin'},
        "end": {
            "dateTime": endTime,
            "timeZone": 'Europe/Berlin'},
    }).execute()

    print("created event")
    # print("id: ", event_result['id'])
    # print("summary: ", event_result['summary'])
    # print("starts at: ", event_result['start']['dateTime'])
    # print("ends at: ", event_result['end']['dateTime'])


def openCsv(filename):
    with open(filename) as csvfile:
        filereader = csv.DictReader(csvfile, delimiter=";")
        data = list(filereader)
        # filereader = csv.reader(csvfile, delimiter=",")
        # for row in filereader:
        # print(row)
        # print("Subject:",row['olApt.Subject'],"\nvon: ",row['olApt.Start'], " bis ", row['olApt.End'], "\nOrt: ",row['olApt.Location'])
        return data


def createEventCaption(oldcaption, location):
    root = ET.parse('keywords.xml').getroot()
    # keywords = root.find('keywords')
    # print(root.text)
    keywordMatch = False
    newlocation = ""
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


def compareEvents(events, service):
    print("this is comparing events")
    outlookEventsCsv = openCsv("outlook.csv")
    if (debug):
        print("no sync. because of debug")
    else:
        createSyncEvent(service)
    for row in outlookEventsCsv:  # csv events from outlook
        csvEventName = row['olApt.Subject'].rstrip()
        csvStartDate = parseCsvDateToIso(row['olApt.Start'])
        csvEndDate = parseCsvDateToIso(row['olApt.End'])
        newEvent = True
        # print(csvEventName)
        print("csv event from: ", csvStartDate, " to ", csvEndDate)
        for event in events:  # events from google calendar
            # print(event['summary'])
            # if event['summary'] == csvEventName:
            # print("google event from: ", event['start']['dateTime'], " to ", event['end']['dateTime'])
            if event['start']['dateTime'] == csvStartDate and event['end']['dateTime'] == csvEndDate:
                # TODO event comparison also based on date not only on name
                # todo only check if there is a event in given time range, if not --> create new event
                # todo if there is already a event in google calendar --> nothing to do
                print("event already in google calendar")
                # print(csvEventName)
                event['summary']
                newEvent = False
                break
            # else:
            # print("no match")
        if (newEvent):  # currentCSV EVent is a truly new event (no doubles)
            print("need to add to google calendar: ", csvEventName)
            # todo to minimize api calls check wether an event is recurring
            # todo check if "abgesagt" is inside the subject --> new subject = "free"
            # todo events for whole day (no time information, only date) -->
            if (debug):
                print("event not added because of debug")
            else:
                createEvent(row, service)
        else:
            # current Event from CSV is already in google calendar
            print("already in google calendar: ", csvEventName)


def main():
    """Shows basic usage of the Google Calendar API.
       Prints the start and name of the next 10 events on the user's calendar.
       """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    try:
        service = build('calendar', 'v3', credentials=creds)

        # Call the Calendar API
        now = datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
        print('Getting the upcoming 20 events')
        events_result = service.events().list(calendarId='primary', timeMin=now,
                                              maxResults=20, singleEvents=True,
                                              orderBy='startTime').execute()
        events = events_result.get('items', [])

        if not events:
            print('No upcoming events found.')
            return

        # Prints the start and name of the next 10 events
        for event in events:
            print(event)
            start = event['start'].get('dateTime', event['start'].get('date'))
            print(start, event['summary'])
        compareEvents(events, service)

    except HttpError as error:
        print('An error occurred: %s' % error)


if __name__ == '__main__':
    main()
