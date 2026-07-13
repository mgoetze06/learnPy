from random import random

import requests
from datetime import datetime
import json
import login
from strava_secrets_request import getFullIntervalsHeaderWithAccessToken,getGPXHeader,get_intervals_url
from paho.mqtt import client as mqtt_client
import shutil

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

def logToFile(log):
    f = open("log.txt", "a",encoding='UTF-8')
    f.write(str(datetime.now()))
    f.write(": ")
    f.write(log + os.linesep)
    f.close()

def get_intervals_activities(header):
    intervals_activities_url = get_intervals_url()
    response = requests.get(intervals_activities_url, headers=header)
    response.raise_for_status()
    activity = None
    try:
        payload = response.json()
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        
        # Extract first activity's id and name
        if payload and len(payload) > 0:
            activity = payload[0]
            
        #print(response.status_code)
    except ValueError:
        print(response.text) 
    return activity

def downloadFile(activity_id,output_path):
    # Download GPX file using the extracted id
    intervals_activity_gpx_url = f"https://intervals.icu/api/v1/activity/{activity_id}/gpx-file"

        
    gpx_response = requests.get(intervals_activity_gpx_url, headers=getGPXHeader())
    gpx_response.raise_for_status()
    

    with open(output_path, "wb") as f:
        f.write(gpx_response.content)
    
    print(gpx_response.status_code)
    print(f"Saved GPX to {output_path}")

def connect_mqtt():
    client_id = f'publish-{random.randint(0, 1000)}'
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


def downloadGPXFile():

    header = getFullIntervalsHeaderWithAccessToken()

    activity = get_intervals_activities(header)
    if not activity:
        print("No activities found.")
        return
    activity_name = activity.get("name", "activity")
    start_date_local = activity.get("start_date_local", "unknown_date").replace('T', '_').replace(':', '')
    output = f"{start_date_local}_{activity_name}.gpx"
    activity_id = activity.get("id")
    
    if(fileExistsHeatmapFolder(output)):
        return
    if(fileExistsLocalFolder(output)):
        copyGPXToHeatmapFolder(output)
        return
    downloadFile(activity_id, output)
    if copyGPXToHeatmapFolder(output):
        tryToRemoveFile(output)

    return activity


def run():
    activity = downloadGPXFile()
    if not activity:
        print("No activity downloaded.")
        return
    client = connect_mqtt()
    client.loop_start()
    publishMessage(client,login.topicMessage,activity.get("name", "activity"))
    client.loop_stop()



if __name__ == '__main__':
    run()