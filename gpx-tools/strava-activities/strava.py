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
        #destdir = "/home/boris/projects/gpx-heatmap/heatmap/gpx/"
        destdir = "/heatmap/gpx/"
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
        #dest_dir = "/home/boris/projects/gpx-heatmap/heatmap/gpx"
        dest_dir = "/heatmap/gpx"
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


def publish(client):
    timestamp,distance_all,distance_month,distance_year,average_speed_month,average_distance_month,max_average_speed,rides = getStravaData()
    MQTT_MSG=json.dumps({"timestamp": timestamp,"distance_all": distance_all,"distance_month":  distance_month,"distance_year": distance_year,"average_speed_month": average_speed_month,"average_distance_month": average_distance_month,"max_average_speed": max_average_speed});
    result = client.publish(login.topic, MQTT_MSG)
    # result: [0, 1]
    status = result[0]
    if status == 0:
        print(f"Send `{MQTT_MSG}` to topic `{login.topic}`")
    else:
        print(f"Failed to send message to topic {login.topic}")

    return rides


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


def run():
    while True:
        client = connect_mqtt()
        client.loop_start()
        rides = publish(client)
        client.loop_stop()

        downloadLastActivities(rides,3)
        print("entering sleep")
        time.sleep(60*60*6)
        #time.sleep(20)
        print("exiting from sleep")


if __name__ == '__main__':
    run()
