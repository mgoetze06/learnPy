from __future__ import print_function

import datetime
import os.path
import csv

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from datetime import date
#from cal_setup import get_calendar_service

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

def createEvent():
    # creates one hour event tomorrow 10 AM IST
    #service = get_calendar_service()
    today = date.today()
    d1 = today.strftime("%d/%m/%Y")
    print(d1)
    #d = datetime.now().date()
    #tomorrow = datetime(d.year, d.month, d.day, 10) + timedelta
    #start = tomorrow.isoformat()
    #end = (tomorrow + timedelta(hours=1)).isoformat()
    #print(start)
    #print(end)

def openCsv(filename):
    with open(filename)as csvfile:

        filereader = csv.DictReader(csvfile, delimiter=",")
        data = list(filereader)
        #filereader = csv.reader(csvfile, delimiter=",")
        #for row in filereader:
            #print(row)
            #print("Subject:",row['olApt.Subject'],"\nvon: ",row['olApt.Start'], " bis ", row['olApt.End'], "\nOrt: ",row['olApt.Location'])
        return data

def compareEvents(events):
    print("this is comparing events")
    outlookEventsCsv = openCsv("outlook.csv")
    for row in outlookEventsCsv:
        csvEventName = row['olApt.Subject'].rstrip()
        newEvent = True
        #print(csvEventName)
        for event in events:
            #print(event['summary'])
            if event['summary'] == csvEventName: #TODO event comparison also based on date not only on name
                #print("matching events")
                #print(csvEventName)
                event['summary']
                newEvent=False
                break
            #else:
                #print("no match")
        if(newEvent): #currentCSV EVent is a truly new event (no doubles)
            print("need to add to google calendar: ",csvEventName)
            createEvent()
        else:
            #current Event from CSV is already in google calendar
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
        now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
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
        compareEvents(events)

    except HttpError as error:
        print('An error occurred: %s' % error)





if __name__ == '__main__':
    main()