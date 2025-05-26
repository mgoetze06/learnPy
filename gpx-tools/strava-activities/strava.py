import requests
import urllib3
import pandas as pd
from pandas import json_normalize
from datetime import datetime
from strava_secrets_request import getFullHeaderWithAccessToken
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import random
import time
import login
import json
from paho.mqtt import client as mqtt_client

def getStravaData(getDatasetActivities = False):
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
    print(len(all_activities))
    for count, activity in enumerate(all_activities):
        print(activity["name"])
        print(count)



    activities = json_normalize(all_activities)
    if getDatasetActivities:
        return activities
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

    print("sum distance all rides: ",d1, "km")
    print("sum distance rides this month: ",d2, "km")
    print("sum distance rides this year: ",d3, "km")
    print("average speed this month: ",d4, "km/h")
    print("average distance this month: ",d5, "km")
    print("max average speed all rides: ",d6, "km/h")
    return now.strftime("%Y-%m-%d, %H:%M:%S"),d1,d2,d3,d4,d5,d6

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
    except:
        client = mqtt_client.Client(client_id)
    #client.username_pw_set(username, password)
    client.username_pw_set(login.user, login.pw)
    client.on_connect = on_connect
    client.connect(login.broker, login.port)
    return client


def publish(client):
    timestamp,distance_all,distance_month,distance_year,average_speed_month,average_distance_month,max_average_speed = getStravaData()
    MQTT_MSG=json.dumps({"timestamp": timestamp,"distance_all": distance_all,"distance_month":  distance_month,"distance_year": distance_year,"average_speed_month": average_speed_month,"average_distance_month": average_distance_month,"max_average_speed": max_average_speed});
    result = client.publish(login.topic, MQTT_MSG)
    # result: [0, 1]
    status = result[0]
    if status == 0:
        print(f"Send `{MQTT_MSG}` to topic `{login.topic}`")
    else:
        print(f"Failed to send message to topic {login.topic}")



def run():
    while True:
        client = connect_mqtt()
        client.loop_start()
        publish(client)
        client.loop_stop()
        time.sleep(60*60*8)



if __name__ == '__main__':
    run()