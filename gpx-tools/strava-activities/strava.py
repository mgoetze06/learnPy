import requests
import urllib3
import pandas as pd
from pandas import json_normalize
from datetime import datetime,timedelta
from strava_secrets_request import getFullHeaderWithAccessToken
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import random
import time
import login
import json
import shutil
import os
from paho.mqtt import client as mqtt_client

def getFullStravaAnalyseFilename(filename):
    return "/home/boris/projects/gpx-heatmap/heatmap/"+filename

def copyStravaAnalyseToHA(filename):
    try:
       shutil.copyfile("/home/boris/projects/gpx-heatmap/heatmap/"+filename,"/mnt/homeassistant/www/"+filename)

    except Exception as e: 
        logToFile(str(e))
        logToFile("copyStravaAnalyseToHA failed")

        pass

def sortDataframeByKey(df,key):
    df = df.sort_values(by=[key], ascending=False)
    return df

def getLeaderboardScoreByActivityID(df,currentID,key):
    #data = df.iloc[[df['id'] == currentID]]
    fastest = df[key].max()
    current = df[df['id'] == currentID][key].max()
    speedDifference = fastest - current
    #data = df.iloc[:, 10] == currentID
    data = df.loc[:,'id'] == currentID
    booleanArray = data.to_numpy()
    for i,idx in enumerate(range(len(booleanArray))):
        if booleanArray[i] == True:
            return idx,len(booleanArray),speedDifference,fastest,current
    #data = df.index.get_loc(df[['id'] == currentID].index[0])
    return data
def getBaseHtmlString():
    base_html_string = '''<!DOCTYPE html>
    <html>
    <head>
        <title>Strava Analyse</title>
        <meta http-equiv="refresh" content="15">
        <style>
            table {
            width: 100%;
            text-align: center;
            thead th {
                background-color: #A2A2A2; 
            }
            tbody tr:nth-child(odd) {
                background-color: #f2f2f2; 
            }
            tbody tr:nth-child(even) {
                background-color: #ffffff; 
            }}
        </style>
    </head>
    <body>
        
        <p><b>Top 3 dieses Jahr</b></p>
        <div>
            <topThreeCurrentYear>
        </div>
        
        <p><b>Top 3 gesamter Zeitraum</b></p>
        <div>
            <topThreeAlltime>
        </div>
        <p><b>Letzte Fahrt</b></p>
        <div>
            <lastRide>
        </div>
        <p><b>https://www.strava.com/activities/id </b></p>
    </body>
    </html>
    '''
    return base_html_string

def getNewBaseHtmlString():
    return '''<!DOCTYPE html>
<html>
<head>
    <title>Strava Analyse</title>
    <meta http-equiv="refresh" content="15">
    <meta charset="UTF-8">
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; background-color: #f0f2f5; margin: 0; padding: 10px; color: #333; }
        .card { background: white; border-radius: 10px; box-shadow: 0 2px 6px rgba(0,0,0,0.08); padding: 10px 12px; margin-bottom: 10px; }
        .card h2 { color: #FC4C02; font-size: 0.85em; margin: 0 0 8px 0; padding-bottom: 5px; border-bottom: 2px solid #FC4C02; display: flex; align-items: center; gap: 5px; }
        .badge { display: inline-block; background: #FC4C02; color: white; border-radius: 10px; padding: 1px 7px; font-size: 0.7em; font-weight: 600; }
        .timestamp { text-align: right; font-size: 0.62em; color: #aaa; margin-top: 8px; }
        .top3-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 6px; }
        .top3-item { background: #fff5f2; border-left: 3px solid #FC4C02; border-radius: 5px; padding: 7px 8px; display: flex; flex-direction: column; gap: 4px; cursor: pointer; transition: background 0.2s; text-decoration: none; color: inherit; min-width: 0; }
        .top3-item:hover { background: #ffe5dc; }
        .top3-header { display: flex; flex-direction: column; gap: 1px; min-width: 0; }
        .top3-medal { font-size: 0.95em; }
        .top3-date { font-size: 0.5em; color: #999; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .top3-divider { border: none; border-top: 1px solid #f0d5cc; margin: 1px 0; }
        .top3-stats-row { display: flex; flex-direction: column; gap: 2px; }
        .top3-stat { display: grid; grid-template-columns: auto 1fr auto; align-items: baseline; gap: 2px; min-width: 0; }
        .top3-stat .label { font-size: 0.42em; color: #888; text-transform: uppercase; white-space: nowrap; }
        .top3-stat .value { font-size: 0.72em; font-weight: 700; color: #FC4C02; text-align: right; white-space: nowrap; }
        .top3-stat .unit { font-size: 0.42em; color: #555; white-space: nowrap; }
        .last-ride-item { background: #fff5f2; border-left: 3px solid #FC4C02; border-radius: 5px; padding: 8px 10px; cursor: pointer; transition: background 0.2s; }
        .last-ride-item:hover { background: #ffe5dc; }
        .last-ride-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; margin-bottom: 8px; text-align: center; }
        .last-ride-stat { display: flex; flex-direction: column; align-items: center; }
        .last-ride-stat .label { font-size: 0.58em; color: #888; text-transform: uppercase; }
        .last-ride-stat .value { font-size: 1em; font-weight: 700; color: #FC4C02; }
        .last-ride-stat .unit { font-size: 0.62em; color: #555; }
        .last-ride-divider { border: none; border-top: 1px solid #f0d5cc; margin: 6px 0; }
        .rank-info { font-size: 0.72em; line-height: 1.7; color: #444; }
        .rank-info span.highlight { color: #FC4C02; font-weight: 600; }
        @media (max-width: 400px) { .last-ride-stats { grid-template-columns: repeat(2, 1fr); } }
    </style>
</head>
<body>
    <div class="card">
        <h2>🏆 Top 3 dieses Jahr</h2>
        <div class="top3-grid"><topThreeCurrentYear></div>
    </div>
    <div class="card">
        <h2>🥇 Top 3 gesamter Zeitraum</h2>
        <div class="top3-grid"><topThreeAlltime></div>
    </div>
    <div class="card">
        <lastRide>
    </div>
</body>
</html>'''

def getHtmlFromPandasDataframe(df,columns,lines):
    topThree = df[columns].head(lines)
    html = topThree.to_html(render_links=True, escape=True)
    html = replacePandasHtmlString(html)
    html = replaceTableHeaders(html)
    return html
     

def replacePandasHtmlString(input):
    return input.replace('\n','').replace("border=\"1\"","").replace("style=\"text-align: right;\"","")

def replaceTableHeaders(input):
    newString = input.replace('distance', 'Distanz [km]')
    newString = newString.replace('average_speed', 'Durchschnittsgeschw. [km/h]')
    newString = newString.replace('start_date_local', 'Startzeit')
    newString = newString.replace('id', 'Strava ID')
    return newString

def getTop3HtmlItems(df, n=3):
    medals = ['🥇', '🥈', '🥉']
    html = ''
    for i, (_, row) in enumerate(df.head(n).iterrows()):
        medal = medals[i] if i < len(medals) else str(i+1)
        activity_id = row['id']
        date = str(row['start_date_local']).replace('T', ' ').replace('Z', '').strip()[:16]
        speed = round(row['average_speed'], 2)
        distance = round(row['distance'], 2)
        html += f'''
            <a class="top3-item" href="https://www.strava.com/activities/{activity_id}" target="_blank">
                <div class="top3-header">
                    <div class="top3-medal">{medal}</div>
                    <div class="top3-date">{date}</div>
                </div>
                <hr class="top3-divider">
                <div class="top3-stats-row">
                    <div class="top3-stat">
                        <div class="label">G</div>
                        <div class="value">{speed}</div>
                        <div class="unit">km/h</div>
                    </div>
                    <div class="top3-stat">
                        <div class="label">D</div>
                        <div class="value">{distance}</div>
                        <div class="unit">km</div>
                    </div>
                </div>
            </a>'''
    return html
    
def createLastRideHtmlSection(rides_df, current_year_rides_df, sortedCurrentYear, sortedAllTime, current_year, now):
    currentID = rides_df['id'].iloc[0]
    key = 'average_speed'

    # Speed rankings
    dataframeID_year, totalRides_year, speedDiff_year, fastest_year, current_speed = getLeaderboardScoreByActivityID(sortedCurrentYear, currentID, key)
    topPercent_year = round(((dataframeID_year + 1) / totalRides_year) * 100)

    dataframeID_all, totalRides_all, speedDiff_all, fastest_all, _ = getLeaderboardScoreByActivityID(sortedAllTime, currentID, key)
    topPercent_all = round(((dataframeID_all + 1) / totalRides_all) * 100)

    # Distance ranking (current year)
    sortedByDist = sortDataframeByKey(current_year_rides_df, 'distance')
    distID, distTotal, _, _, currentDist = getLeaderboardScoreByActivityID(sortedByDist, currentID, 'distance')
    yearTotalDist = round(sum(current_year_rides_df['distance']), 2)

    activity_id = rides_df['id'].iloc[0]
    name = rides_df['name'].iloc[0]
    start_raw = str(rides_df['start_date_local'].iloc[0]).replace('T', ' ').replace('Z', '').strip()
    start_date = start_raw[:10]
    start_time = start_raw[11:16] if len(start_raw) > 10 else ''
    duration_min = round(rides_df['moving_time'].iloc[0] / 60)
    speed = round(current_speed, 2)
    distance = round(rides_df['distance'].iloc[0], 2)

    html = f'''
        <h2>🚵 Letzte Fahrt &nbsp;<span class="badge">{name}</span></h2>
        <div class="last-ride-item" onclick="window.open('https://www.strava.com/activities/{activity_id}','_blank')">
            <div class="last-ride-stats">
                <div class="last-ride-stat">
                    <div class="label">Ø Geschw.</div>
                    <div class="value">{speed} <span class="unit">km/h</span></div>
                </div>
                <div class="last-ride-stat">
                    <div class="label">Distanz</div>
                    <div class="value">{distance} <span class="unit">km</span></div>
                </div>
                <div class="last-ride-stat">
                    <div class="label">Dauer</div>
                    <div class="value">{duration_min} <span class="unit">min</span></div>
                </div>
                <div class="last-ride-stat">
                    <div class="label">Start</div>
                    <div class="value" style="font-size:0.8em;">{start_date}</div>
                    <div class="unit">{start_time}</div>
                </div>
            </div>
            <hr class="last-ride-divider">
            <div class="rank-info">
                <div>📅 <b>{current_year}:<br></b> Platz <span class="highlight">{dataframeID_year+1} / {totalRides_year}</span> &nbsp;|&nbsp; Top <span class="highlight">{topPercent_year} %</span> &nbsp;|&nbsp; Δ Schnellster: <span class="highlight">−{round(speedDiff_year,2)} km/h</span></div>
                <div>🏅 <b>Alltime:<br></b> Platz <span class="highlight">{dataframeID_all+1} / {totalRides_all}</span> &nbsp;|&nbsp; Top <span class="highlight">{topPercent_all} %</span> &nbsp;|&nbsp; Δ Schnellster: <span class="highlight">−{round(speedDiff_all,2)} km/h</span></div>
                <div>📏 <b>Jahres-Distanz:<br></b> <span class="highlight">{yearTotalDist} km</span> &nbsp;|&nbsp; Platz <span class="highlight">{distID+1} / {distTotal}</span></div>
            </div>
        </div>
        <div class="timestamp">Zeitstempel: {now.strftime("%Y-%m-%d %H:%M:%S")}</div>'''
    return html

def createLastRideString(current_year_rides_df,rides_df,current_year,now=None):
    #print(getLeaderboardScore(sorted,17096086975))
    #currentID = rides_df.loc[0]['id']

    if now == None:
        now = datetime.now()

    currentID = rides_df['id'].iloc[0]

    key = 'average_speed'
    sortedCurrentYear = sortDataframeByKey(current_year_rides_df,key)
    sortedAllTime = sortDataframeByKey(rides_df,key)
    dataframeID,totalRides, speedDifference, fastest,current = getLeaderboardScoreByActivityID(sortedCurrentYear,currentID,key)
    topPerecent = round(((dataframeID+1) / totalRides) * 100)

    lastRideString = ""
    lastRideString = lastRideString + f"{rides_df['name'].iloc[0]} {rides_df['start_date_local'].iloc[0]}"+ "<br>"

    lastRideString = lastRideString + f"Durchschnittsgeschwindigkeit \t {round(current,2)} km/h" + "<br>"
    #print(f"Durchschnittsgeschwindigkeit \t {round(current,2)} km/h")
    #print(f"Dieses Jahr {current_year}  \t\t Platz: {dataframeID+1} von {totalRides}\t(Top {topPerecent} %) mit einer Geschwindigkeitsdifferenz zum Schnellsten ({round(fastest,2)} km/h) von {round(speedDifference,2)} km/h") 
    thisYearMessageHtml = f"Dieses Jahr {current_year}  \t\t Platz: {dataframeID+1} von {totalRides}\t(Top {topPerecent} %) mit einer Geschwindigkeitsdifferenz zum Schnellsten ({round(fastest,2)} km/h) von {round(speedDifference,2)} km/h" 
    #date = now.strftime("%Y%m%d %H:%M")
    thisRideSummary = f"{str(rides_df['start_date_local'].iloc[0]).replace('T',' ').replace('Z',' ')} {rides_df['distance'].iloc[0]} km {round(rides_df['moving_time'].iloc[0]/60)} min {current} km/h"
    thisYearMessage = thisRideSummary + f" ----- {current_year}: {dataframeID+1} von {totalRides} Top {topPerecent} % Abstand {round(speedDifference,2)} km/h zu {round(fastest,2)} km/h" 

    lastRideString = lastRideString + thisYearMessageHtml  + "<br>"
    dataframeID,totalRides, speedDifference, fastest,current = getLeaderboardScoreByActivityID(sortedAllTime,currentID,key)
    topPerecent = round(((dataframeID+1) / totalRides) * 100)

    #print(f"Alltime  \t \t\t Platz: {dataframeID+1} von {totalRides}\t(Top {topPerecent} %) mit einer Geschwindigkeitsdifferenz zum Schnellsten ({round(fastest,2)} km/h) von {round(speedDifference,2)} km/h")
    lastRideString = lastRideString + f"Alltime  \t \t\t Platz: {dataframeID+1} von {totalRides}\t(Top {topPerecent} %) mit einer Geschwindigkeitsdifferenz zum Schnellsten ({round(fastest,2)} km/h) von {round(speedDifference,2)} km/h"  + "<br>"
    lastRideString = lastRideString + f"Zeitstempel: {str(now)}"
    return lastRideString, sortedCurrentYear, sortedAllTime,thisYearMessage

def createLastRideMessageDistance(current_year_rides_df,rides_df,current_year,now=None):
    if now == None:
        now = datetime.now()

    currentID = rides_df['id'].iloc[0]
    key = 'distance'
    sortedCurrentYear = sortDataframeByKey(current_year_rides_df,key)
    sortedAllTime = sortDataframeByKey(rides_df,key)
    dataframeID,totalRides, speedDifference, fastest,current = getLeaderboardScoreByActivityID(sortedCurrentYear,currentID,key)
    topPerecent = round(((dataframeID+1) / totalRides) * 100)
    thisRideSummary = f"{str(rides_df['start_date_local'].iloc[0]).replace('T',' ').replace('Z',' ')} {rides_df['distance'].iloc[0]} km {round(rides_df['moving_time'].iloc[0]/60)} min {round(rides_df['average_speed'].iloc[0],2)} km/h"
    thisYearMessage = thisRideSummary + f" ----- {current_year}: {dataframeID+1} von {totalRides} Top {topPerecent} % Abstand {round(speedDifference,2)} km zu {round(fastest,2)} km" 
    return thisYearMessage

def logToFile(log):
    f = open("log.txt", "a",encoding='UTF-8')
    f.write(str(datetime.now()))
    f.write(": ")
    f.write(log + os.linesep)
    f.close()

def get_data_stream(activity_id,header):
    api_url = f'https://www.strava.com/api/v3/activities/{activity_id}/streams'
    query_params = 'time'
    # for key, value in self.streams.items():
    #     if value == 1:
    #         query_params += f',{key}'
    # url = f'{api_url}?keys={query_params}&key_by_type=true'
    url = api_url + "?keys=time,latlng,altitude&key_by_type=true"

    my_dataset = requests.get(url, headers=header).json()
    return my_dataset

def add_seconds_to_timestamp(start_timestamp, seconds):
    start_time = getDatetimeFromTimestamp(start_timestamp)
    new_time = start_time + timedelta(seconds=seconds)
    return (new_time.isoformat() + "Z").replace("+00:00", "")

def get_strava_activity(activity_id,header):
        print("getting details for activity_id", activity_id)
        api_url = 'https://www.strava.com/api/v3/activities/'
        url = f'{api_url}{activity_id}?include_all_efforts=false'
        print("requesting details from url", url)
        data = requests.get(url, headers=header).json()
        return data

def getDatetimeFromTimestamp(timestamp):
    replacedTimestamp = timestamp.replace("T"," ").replace("Z","")
    time = datetime.strptime(f"{replacedTimestamp}", "%Y-%m-%d %H:%M:%S") 
    #time = time + timedelta(hours=1)
    return time

def writeGPX(output,activity,data_streams):
    print("writing activity to gpx file", output)
    start_date = activity['start_date']

    gpx_content_start = f'''<?xml version="1.0" encoding="UTF-8"?>
<gpx xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd http://www.garmin.com/xmlschemas/GpxExtensions/v3 http://www.garmin.com/xmlschemas/GpxExtensionsv3.xsd http://www.garmin.com/xmlschemas/TrackPointExtension/v1 http://www.garmin.com/xmlschemas/TrackPointExtensionv1.xsd" creator="StravaGPX" version="1.1" xmlns="http://www.topografix.com/GPX/1/1" xmlns:gpxtpx="http://www.garmin.com/xmlschemas/TrackPointExtension/v1" xmlns:gpxx="http://www.garmin.com/xmlschemas/GpxExtensions/v3">
 <metadata>
  <time>{start_date}</time>
 </metadata>
 <trk>
  <name>{activity['name']}</name>
  <type>{activity['type']}</type>
  <trkseg>'''
    
    gpx_content_end = '''
  </trkseg>
 </trk>
</gpx>
'''
    if data_streams['latlng']['original_size'] != data_streams['time']['original_size']:
        print("Error: latlng does not equal Time")
        return

    trkpts = []
    for i in range(data_streams['time']['original_size']):
        time = add_seconds_to_timestamp(activity['start_date'], data_streams['time']['data'][i])
        trkpt = f'''
   <trkpt lat="{float(data_streams['latlng']['data'][i][0]):.7f}" lon="{float(data_streams['latlng']['data'][i][1]):.7f}">
    <ele>{float(data_streams['altitude']['data'][i]):.1f}</ele>
    <time>{time}</time>
   </trkpt>'''
        trkpts.append(trkpt)
#     <extensions>
#      <gpxtpx:TrackPointExtension>
# 
#         trkpts.append(trkpt)

# #         if self.streams['temp'] == 1:
# #             trkpt = f'''      <gpxtpx:atemp>{data_streams['temp']['data'][i]}</gpxtpx:atemp>
# # '''
# #             trkpts.append(trkpt)
# #         if self.streams['watts'] == 1:
# #             trkpt = f'''      <gpxtpx:watts>{data_streams['watts']['data'][i]}</gpxtpx:watts>
# # '''
# #             trkpts.append(trkpt)
# #         if self.streams['heartrate'] == 1:
# #             trkpt = f'''      <gpxtpx:hr>{data_streams['heartrate']['data'][i]}</gpxtpx:hr>
# # ''' 
# #             trkpts.append(trkpt)

# #         if self.streams['cadence'] == 1:
# #             trkpt = f'''      <gpxtpx:cad>{data_streams['cadence']['data'][i]}</gpxtpx:cad>
# # '''
#         trkpts.append(trkpt)

#         trkpt =f'''     </gpxtpx:TrackPointExtension>
#     </extensions>
        

    with open(output, 'a') as f:
        f.write(gpx_content_start)
        f.write(''.join(trkpts))
        f.write(gpx_content_end)

    print('GPX file saved successfully.')

def fileExistsHeatmapFolder(filename):
    try:
        destdir = "/home/boris/projects/gpx-heatmap/heatmap/gpx/"
        #destdir = "/heatmap/gpx/"
        fullPath = destdir + filename
        return os.path.isfile(fullPath)
    except:
        return False
    
def fileExistsLocalFolder(filename):
    try:
        return os.path.isfile(filename)
    except:
        return False


def copyGPXToHeatmapFolder(gpxfile):
    try:
        dest_dir = "/home/boris/projects/gpx-heatmap/heatmap/gpx"
        #dest_dir = "/heatmap/gpx"
        shutil.copy(gpxfile,dest_dir)
        return True
    except Exception as e: 
        logToFile(str(e))
        logToFile("copyGPXToHeatmapFolder failed")
        pass
    return False

def tryToRemoveFile(file):
    try:
        os.remove(file)
    except Exception as e: 
        logToFile(str(e))
        logToFile("removing gpx file failed.")
        pass

def getActivityID():

    activity_id = input("activity id:")
    if len(activity_id) < 11:
        return None
    
    if len(activity_id) == 11:
        return activity_id
    
    try:
        activity_id = activity_id.split("https://www.strava.com/activities/")[1].replace(" ","")
        return activity_id
    except Exception as e: 
        logToFile(str(e))
        pass


def downloadGPXFileFromActivityID(activity_id=None):

    header = getFullHeaderWithAccessToken()

    if activity_id == None:
        activity_id = getActivityID() #TODO check which activities already been downloaded and only get new ones
    

    activity = get_strava_activity(activity_id,header)
    output = activity['start_date_local'].replace("T","-").replace("Z","").replace(":","-") + "_" + activity['name'].replace(" ","_").replace("/","")+".gpx"
    
    if(fileExistsHeatmapFolder(output)):
        return
    if(fileExistsLocalFolder(output)):
        copyGPXToHeatmapFolder(output)
        return
    data_streams = get_data_stream(activity_id,header)
    writeGPX(output,activity,data_streams)
    if copyGPXToHeatmapFolder(output):
        tryToRemoveFile(output)


def getStravaData():
    now = datetime.now()

    auth_url = "https://www.strava.com/oauth/token"
    activites_url = "https://www.strava.com/api/v3/athlete/activities"

    header = getFullHeaderWithAccessToken()

    request_page_num = 1
    all_activities = []

    while True:
        param = {'per_page': 50, 'page': request_page_num}
        # initial request, where we request the first page of activities
        my_dataset = requests.get(activites_url, headers=header, params=param).json()

        # check the response to make sure it is not empty. If it is empty, that means there is no more data left. So if you have
        # 1000 activities, on the 6th request, where we request page 6, there would be no more data left, so we will break out of the loop
        if len(my_dataset) == 0:
            print("breaking out of while loop because the response is zero, which means there must be no more activities")
            break

        # if the all_activities list is already populated, that means we want to add additional data to it via extend.
        if all_activities:
            print("all_activities is populated")
            all_activities.extend(my_dataset)

        # if the all_activities is empty, this is the first time adding data so we just set it equal to my_dataset
        else:
            print("all_activities is NOT populated")
            all_activities = my_dataset

        request_page_num += 1
    print("received total activities: ",len(all_activities))
    # for count, activity in enumerate(all_activities):
    #     print(activity["name"])
    #     print(count)



    activities = json_normalize(all_activities)
    #activities.columns
    # Index(['resource_state', 'name', 'distance', 'moving_time', 'elapsed_time',
    #        'total_elevation_gain', 'type', 'sport_type', 'workout_type', 'id',
    #        'start_date', 'start_date_local', 'timezone', 'utc_offset',
    #        'location_city', 'location_state', 'location_country',
    #        'achievement_count', 'kudos_count', 'comment_count', 'athlete_count',
    #        'photo_count', 'trainer', 'commute', 'manual', 'private', 'visibility',
    #        'flagged', 'gear_id', 'start_latlng', 'end_latlng', 'average_speed',
    #        'max_speed', 'average_watts', 'device_watts', 'kilojoules',
    #        'has_heartrate', 'heartrate_opt_out', 'display_hide_heartrate_option',
    #        'elev_high', 'elev_low', 'upload_id', 'upload_id_str', 'external_id',
    #        'from_accepted_tag', 'pr_count', 'total_photo_count', 'has_kudoed',
    #        'athlete.id', 'athlete.resource_state', 'map.id',
    #        'map.summary_polyline', 'map.resource_state'],
    #       dtype='object')

    rides = activities.loc[activities['type'] == 'Ride']
    runs = activities.loc[activities['type'] == 'Run']

    current_month = now.strftime("%Y-%m")
    current_year = now.strftime("%Y")
    current_month_rides = rides[rides['start_date_local'].str.contains(current_month, na=False)]
    current_year_rides = rides[rides['start_date_local'].str.contains(current_year, na=False)]
    #current_month_rides['start_date_local'] = pd.to_datetime(rides['start_date_local'])
    #current_month_rides.loc[current_month_rides['start_date_local'] ]
    #current_month_rides

    d1 = round(sum(rides["distance"])/1000,2)
    d2 = round(sum(current_month_rides["distance"])/1000,2)
    d3 = round(sum(current_year_rides["distance"])/1000,2)
    d4 = round(current_month_rides["average_speed"].mean() * 3.6,2)
    d5 = round(current_month_rides["distance"].mean()/1000,2)
    d6 = round(max(rides['average_speed']) * 3.6,2)

    if d2 == 0:
        d4 = 0
        d5 = 0

    print("sum distance all rides: ",d1, "km")
    print("sum distance rides this month: ",d2, "km")
    print("sum distance rides this year: ",d3, "km")
    print("average speed this month: ",d4, "km/h")
    print("average distance this month: ",d5, "km")
    print("max average speed all rides: ",d6, "km/h")
    return now.strftime("%Y-%m-%d, %H:%M:%S"),d1,d2,d3,d4,d5,d6,rides

# broker = <IP>
# port = <PORT>
# topic = "python/mqtt"
# user = ""
# pw = ""




# Generate a Client ID with the publish prefix.
client_id = f'publish-{random.randint(0, 1000)}'

def connect_mqtt():
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect, return code %d\n", rc)

    #client = mqtt_client.Client(client_id)
    try:
        client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION2,client_id)
    except Exception as e: 
        logToFile(str(e))
        client = mqtt_client.Client(client_id)
    #client.username_pw_set(username, password)
    client.username_pw_set(login.user, login.pw)
    client.on_connect = on_connect
    try:
        client.connect(login.broker, login.port)
    except Exception as e: 
        logToFile(str(e))
        pass
    return client


def publishStravaData(client):
    timestamp,distance_all,distance_month,distance_year,average_speed_month,average_distance_month,max_average_speed,rides = getStravaData()
    MQTT_MSG=json.dumps({"timestamp": timestamp,"distance_all": distance_all,"distance_month":  distance_month,"distance_year": distance_year,"average_speed_month": average_speed_month,"average_distance_month": average_distance_month,"max_average_speed": max_average_speed});
    publishMQTT(client,MQTT_MSG,login.topic)
    return rides

def publishMessage(client,topic, message):
    MQTT_MSG=json.dumps({"message": message});
    publishMQTT(client,MQTT_MSG,topic)

def publishMQTT(client,MQTT_MSG,topic):
    result = client.publish(topic, MQTT_MSG)
    # result: [0, 1]
    status = result[0]
    if status == 0:
        print(f"Send `{MQTT_MSG}` to topic `{topic}`")
    else:
        print(f"Failed to send message to topic {topic}")


def downloadLastActivities(rides, downloadFiles):
    upperrange = downloadFiles
    for i in range(0,upperrange):
        loc = i
        #print(rides.iloc[loc])
        id = rides.iloc[loc]["id"]
        print("trying to download ride with id: ",id)
        try:
            downloadGPXFileFromActivityID(id)
        except Exception as e: 
            logToFile(str(e))
            print("error downloading ride with id: ",id)
            pass
    return 

def get_strava_flyby_matches(activity_id):
    """
    Fetches flyby matches for a specific Strava activity ID.
    """
    url = f"https://nene.strava.com/flyby/matches/{activity_id}"
    
    headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'de,en-US;q=0.9,en;q=0.8',
        'Referer': 'https://labs.strava.com/',
        'Origin': 'https://labs.strava.com',
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except Exception as err:
        print(f"An error occurred: {err}")

def getFlyByMessage(rides):
    try:
        id = rides.iloc[0]["id"]
        data = get_strava_flyby_matches(str(id))

        if not data:
            return None
        
        ownActivity = data['activity']
        #print(ownActivity)
        ownID = ownActivity['athleteId']
        #print(ownID)
        athletes = data['athletes']
        #print(athletes)
        count = len([entry for entry in athletes if str(entry) != str(ownID)])
        first_names = [user['firstName'].encode("ascii", "ignore").decode() for user in athletes.values() if str(user['id']) != str(ownID)]
        description = ", ".join(first_names)
        description = limitTextSize(description,255)
        #print("Matches: ", count)
        MQTT_MSG=json.dumps({"count": count,"description": description})
        return MQTT_MSG
    except:
        return None
    

def createStravaAnalyseHtml(filename, rides):
    fullFilename = getFullStravaAnalyseFilename(filename)
    rides['average_speed'] = round(rides['average_speed'] * 3.6, 2)
    rides['distance'] = round(rides['distance'] / 1000, 2)
    now = datetime.now()
    current_year = now.strftime("%Y")
    current_month = now.strftime("%Y-%m")
    current_year_rides = rides[rides['start_date_local'].str.contains(current_year, na=False)]

    key = 'average_speed'
    sortedCurrentYear = sortDataframeByKey(current_year_rides, key)
    sortedAllTime = sortDataframeByKey(rides, key)

    # Build last ride message strings (kept for MQTT)
    lastRideString, _, _, lastRideMessage = createLastRideString(current_year_rides, rides, current_year, now)
    lastRideMessageDistance = createLastRideMessageDistance(current_year_rides, rides, current_year, now)

    # Build new HTML
    html = getNewBaseHtmlString()
    html = html.replace('<topThreeCurrentYear>', getTop3HtmlItems(sortedCurrentYear))
    html = html.replace('<topThreeAlltime>', getTop3HtmlItems(sortedAllTime))
    html = html.replace('<lastRide>', createLastRideHtmlSection(rides, current_year_rides, sortedCurrentYear, sortedAllTime, current_year, now))

    try:
        if os.path.exists(fullFilename):
            os.remove(fullFilename)
        with open(fullFilename, 'w', encoding='utf-8') as f:
            f.write(html)
        copyStravaAnalyseToHA(filename)
    except Exception as e:
        logToFile(str(e))
        pass

    return lastRideMessage, lastRideMessageDistance

def limitTextSize(text,limit=255):
    if len(text) > limit:
        final_output = text[:limit-3] + "..."
    else:
        final_output = text

    return final_output

def run():
    #while True:
    client = connect_mqtt()
    client.loop_start()
    rides = publishStravaData(client)
    lastRideMessageSpeed,lastRideMessageDistance = createStravaAnalyseHtml('strava_analyse.html',rides)
    publishMessage(client,login.topicMessage,lastRideMessageSpeed)
    publishMessage(client,login.topicMessageDistance,lastRideMessageDistance)

    flybyMessage = getFlyByMessage(rides)
    publishMQTT(client,flybyMessage,login.topicMessageFlyby)


    client.loop_stop()

    downloadLastActivities(rides,3)
        # print("entering sleep")
        # time.sleep(60*60*6)
        # #time.sleep(20)
        # print("exiting from sleep")


if __name__ == '__main__':
    run()