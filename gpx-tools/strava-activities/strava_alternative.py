import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path

import requests
from paho.mqtt import client as mqtt_client

import login
from strava_secrets_request import (
    getFullIntervalsHeaderWithAccessToken,
    getGPXHeader,
    get_intervals_url,
)

BASE_DIR = "/home/boris/projects/gpx-heatmap/heatmap" #Path(__file__).resolve().parent
HEATMAP_DIR = BASE_DIR / "heatmap"
HEATMAP_GPX_DIR = HEATMAP_DIR / "gpx"
HEATMAP_LOG_FILE = HEATMAP_DIR / "log.txt"


def fileExistsHeatmapFolder(filename):
    try:
        return (HEATMAP_GPX_DIR / Path(filename).name).is_file()
    except Exception:
        return False


def fileExistsLocalFolder(filename):
    try:
        return Path(filename).is_file()
    except Exception:
        return False


def copyGPXToHeatmapFolder(gpxfile):
    try:
        HEATMAP_GPX_DIR.mkdir(parents=True, exist_ok=True)
        destination = HEATMAP_GPX_DIR / Path(gpxfile).name
        shutil.copy2(gpxfile, destination)
        return True
    except Exception as e:
        logToFile(str(e))
        logToFile("copyGPXToHeatmapFolder failed")
        return False


def tryToRemoveFile(file):
    try:
        Path(file).unlink(missing_ok=True)
    except Exception as e:
        logToFile(str(e))
        logToFile("removing gpx file failed.")


def logToFile(log):
    HEATMAP_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HEATMAP_LOG_FILE, "a", encoding="utf-8") as file:
        file.write(f"{datetime.now()}: {log}{os.linesep}")

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
            activity = payload
            
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
    client_id = f'publish-972'
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

    activities = get_intervals_activities(header)
    if not activities:
        print("no activities")
        return

    for activity in activities:
        activity_name = activity.get("name", "activity")
        safe_activity_name = re.sub(r"[^A-Za-z0-9._-]+", "_", activity_name).strip("._")
        start_date_local = activity.get("start_date_local", "unknown_date").replace("T", "_").replace(":", "")
        output_filename = f"{start_date_local}_{safe_activity_name}.gpx"
        output_path = BASE_DIR / output_filename
        activity_id = activity.get("id")

        if fileExistsHeatmapFolder(output_filename):
            continue
        if fileExistsLocalFolder(str(output_path)):
            copyGPXToHeatmapFolder(str(output_path))
            continue

        downloadFile(activity_id, str(output_path))
        if copyGPXToHeatmapFolder(str(output_path)):
            tryToRemoveFile(str(output_path))

    return activities[0]


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
