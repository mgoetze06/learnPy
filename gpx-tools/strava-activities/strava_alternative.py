import json
import os
import pickle
import random
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

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HEATMAP_DIR = PROJECT_ROOT / "heatmap"
HEATMAP_GPX_DIR = HEATMAP_DIR / "gpx"
HEATMAP_LOG_FILE = HEATMAP_DIR / "log.txt"
HEATMAP_ACTIVITY_PKL_FILE = HEATMAP_DIR / "activities.pkl"


def _load_activity_store():
    HEATMAP_DIR.mkdir(parents=True, exist_ok=True)
    if not HEATMAP_ACTIVITY_PKL_FILE.is_file():
        return []

    try:
        import pandas as pd
        store = pd.read_pickle(HEATMAP_ACTIVITY_PKL_FILE)
        return store
    except Exception:
        pass

    try:
        with open(HEATMAP_ACTIVITY_PKL_FILE, "rb") as file:
            store = pickle.load(file)
            return store
    except Exception as e:
        logToFile(f"Failed to load activity pickle: {e}")
        return []


def _save_activity_store(store):
    HEATMAP_DIR.mkdir(parents=True, exist_ok=True)
    try:
        if isinstance(store, list):
            with open(HEATMAP_ACTIVITY_PKL_FILE, "wb") as file:
                pickle.dump(store, file)
            return

        import pandas as pd
        store.to_pickle(HEATMAP_ACTIVITY_PKL_FILE)
    except ImportError:
        with open(HEATMAP_ACTIVITY_PKL_FILE, "wb") as file:
            pickle.dump(store, file)
    except Exception as e:
        logToFile(f"Failed to save activity pickle: {e}")


def add_activity_to_pickle(activity: dict) -> bool:
    if not activity or 'id' not in activity:
        return False

    activity_id = activity['id']
    store = _load_activity_store()

    if isinstance(store, list):
        if any(item.get('id') == activity_id for item in store if isinstance(item, dict)):
            return False
        store.append(activity)
        _save_activity_store(store)
        return True

    try:
        import pandas as pd
        df = store
        if not df.empty and 'id' in df.columns and activity_id in df['id'].values:
            return False
        activity_df = pd.DataFrame([activity])
        if df.empty:
            df = activity_df
        else:
            df = pd.concat([df, activity_df], ignore_index=True)
        _save_activity_store(df)
        return True
    except Exception:
        logToFile(f"Failed to update activity pickle for id {activity_id}")
        return False


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
    logToFile(f"Saved GPX to {output_path}")

def connect_mqtt():
    client_id = f'publish-{random.randint(100, 999)}'
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


def load_pickled_activities():
    store = _load_activity_store()
    if isinstance(store, list):
        return [item for item in store if isinstance(item, dict)]
    try:
        import pandas as pd
        if hasattr(store, 'to_dict'):
            return store.to_dict(orient='records')
    except Exception:
        pass
    return []


def _parse_activity_datetime(activity):
    for key in ('start_date_local', 'start_date'):
        value = activity.get(key)
        if not value:
            continue
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            try:
                return datetime.strptime(value, '%Y-%m-%dT%H:%M:%S')
            except Exception:
                continue
    return None


def _activity_distance_meters(activity):
    for key in ('distance', 'distance_raw', 'moving_distance'):
        value = activity.get(key)
        if value is None:
            continue
        try:
            return float(value)
        except Exception:
            continue
    return 0.0


def _activity_average_speed(activity):
    for key in ('average_speed', 'moving_average_speed', 'avg_speed'):
        value = activity.get(key)
        if value is None:
            continue
        try:
            return float(value)
        except Exception:
            continue
    return 0.0


def get_pickle_summary():
    activities = load_pickled_activities()
    now = datetime.now()
    current_month = now.strftime('%Y-%m')
    current_year = now.strftime('%Y')

    distance_all = 0.0
    distance_month = 0.0
    distance_year = 0.0
    month_speeds = []
    all_speeds = []
    month_distances = []

    for activity in activities:
        distance = _activity_distance_meters(activity)
        speed = _activity_average_speed(activity)
        activity_dt = _parse_activity_datetime(activity)

        distance_all += distance
        if speed > 0:
            all_speeds.append(speed)

        if activity_dt is None:
            continue

        if activity_dt.strftime('%Y-%m') == current_month:
            distance_month += distance
            month_distances.append(distance)
            if speed > 0:
                month_speeds.append(speed)

        if activity_dt.strftime('%Y') == current_year:
            distance_year += distance

    average_speed_month = round((sum(month_speeds) / len(month_speeds)) * 3.6, 2) if month_speeds else 0.0
    average_distance_month = round((sum(month_distances) / len(month_distances)) / 1000, 2) if month_distances else 0.0
    max_average_speed = round(max(all_speeds) * 3.6, 2) if all_speeds else 0.0

    return {
        'timestamp': now.strftime('%Y-%m-%d, %H:%M:%S'),
        'distance_all': round(9135.2 + round(distance_all / 1000, 2), 2),
        'distance_month': round(distance_month / 1000, 2),
        'distance_year': round(2970.7 + round(distance_year / 1000, 2), 2),
        'average_speed_month': average_speed_month,
        'average_distance_month': average_distance_month,
        'max_average_speed': max_average_speed,
    }


def publish_pickle_summary(client):
    summary = get_pickle_summary()
    MQTT_MSG = json.dumps(summary)
    publishMQTT(client, MQTT_MSG, login.topic)


def downloadGPXFile():
    header = getFullIntervalsHeaderWithAccessToken()

    activities = get_intervals_activities(header)
    if not activities:
        print("no activities")
        logToFile("no activities")
        return

    for activity in activities:
        activity_name = activity.get("name", "activity")
        safe_activity_name = re.sub(r"[^A-Za-z0-9._-]+", "_", activity_name).strip("._")
        start_date_local = activity.get("start_date_local", "unknown_date").replace("T", "_").replace(":", "")
        output_filename = f"{start_date_local}_{safe_activity_name}.gpx"
        output_path = HEATMAP_GPX_DIR / output_filename
        activity_id = activity.get("id")

        if add_activity_to_pickle(activity):
            print(f"Saved activity {activity_id} to pickle")
        else:
            print(f"Activity {activity_id} already in pickle or missing id")

        if fileExistsHeatmapFolder(output_filename):
            continue
        if fileExistsLocalFolder(str(output_path)):
            copyGPXToHeatmapFolder(str(output_path))
            continue
        logToFile(f"Downloading GPX for activity {activity_id} to {output_path}")
        downloadFile(activity_id, str(output_path))
        if copyGPXToHeatmapFolder(str(output_path)):
            tryToRemoveFile(str(output_path))

    return activities[0]


def run():
    activity = downloadGPXFile()
    client = connect_mqtt()
    client.loop_start()
    publish_pickle_summary(client)
    client.loop_stop()



if __name__ == '__main__':
    run()
