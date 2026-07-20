import json
import os
import pickle
import random
import re
import shutil
from datetime import datetime
from html import escape
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


def _activity_moving_time_seconds(activity):
    for key in ("moving_time", "elapsed_time"):
        value = activity.get(key)
        if value is None:
            continue
        try:
            return int(float(value))
        except Exception:
            continue
    return 0


def _is_activity_store_fresh(max_age_minutes=30):
    if not HEATMAP_ACTIVITY_PKL_FILE.is_file():
        return False

    try:
        age_seconds = datetime.now().timestamp() - HEATMAP_ACTIVITY_PKL_FILE.stat().st_mtime
        return age_seconds <= max_age_minutes * 60
    except Exception:
        return False


def _select_latest_activity(activities):
    if not isinstance(activities, list):
        return None

    valid_activities = [item for item in activities if isinstance(item, dict)]
    if not valid_activities:
        return None

    def sort_key(activity):
        parsed_dt = _parse_activity_datetime(activity)
        if parsed_dt is not None:
            return parsed_dt

        raw_value = activity.get("start_date_local") or activity.get("start_date") or ""
        try:
            return datetime.fromisoformat(str(raw_value).replace("Z", "+00:00"))
        except Exception:
            return datetime.min

    return max(valid_activities, key=sort_key)


def _format_relative_time(past_time, now=None):
    now = now or datetime.now()
    delta = now - past_time
    total_seconds = max(int(delta.total_seconds()), 0)

    if total_seconds < 60:
        return "gerade eben"

    minutes = total_seconds // 60
    if minutes < 60:
        return f"vor {minutes} Minute{'n' if minutes != 1 else ''}"

    hours = minutes // 60
    if hours < 24:
        return f"vor {hours} Stunde{'n' if hours != 1 else ''}"

    days = hours // 24
    return f"vor {days} Tag{'en' if days != 1 else ''}"


def _format_duration(minutes):
    hours, remainder = divmod(int(minutes), 60)
    if hours and remainder:
        return f"{hours}h {remainder}m"
    if hours:
        return f"{hours}h"
    return f"{remainder}m"


def get_last_ride_html(activities, now=None):
    now = now or datetime.now()
    activity = _select_latest_activity(activities)

    if not activity:
        return f"""<!DOCTYPE html>
<html lang=\"de\">
<head>
    <meta charset=\"UTF-8\">
    <title>Letzte Fahrt</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f3f4f6; color: #111827; }}
        .card {{ background: white; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); padding: 20px; max-width: 460px; }}
        .title {{ font-size: 1.1rem; font-weight: 600; margin-bottom: 8px; }}
        .meta {{ color: #6b7280; font-size: 0.95rem; margin-bottom: 12px; }}
        .message {{ color: #374151; font-size: 0.95rem; line-height: 1.5; }}
    </style>
</head>
<body>
    <div class=\"card\">
        <div class=\"title\">Letzte Fahrt</div>
        <div class=\"meta\">{now.strftime('%d.%m.%Y %H:%M:%S')}</div>
        <div class=\"message\">Noch keine Daten verfügbar.</div>
    </div>
</body>
</html>"""

    name = escape(str(activity.get("name") or "Unbekannte Fahrt"))
    start_dt = _parse_activity_datetime(activity)
    start_text = start_dt.strftime("%d.%m.%Y %H:%M") if start_dt else "Unbekannt"
    distance_km = round(_activity_distance_meters(activity) / 1000, 2)
    speed_kmh = round(_activity_average_speed(activity) * 3.6, 2)
    duration_minutes = round(_activity_moving_time_seconds(activity) / 60)
    duration_text = _format_duration(duration_minutes)
    relative_update = _format_relative_time(now, now)

    html = f"""<!DOCTYPE html>
<html lang=\"de\">
<head>
    <meta charset=\"UTF-8\">
    <meta http-equiv=\"refresh\" content=\"15\">
    <title>Letzte Fahrt</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; min-height: 100vh; padding: 20px; background: #0f172a; color: #e5e7eb; display: flex; align-items: center; justify-content: center; box-sizing: border-box; }}
        .card {{ background: #111827; border: 1px solid #374151; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.35); padding: 20px; width: min(100%, 720px); }}
        .title {{ font-size: 1.1rem; font-weight: 600; margin-bottom: 6px; color: #f9fafb; }}
        .meta {{ color: #9ca3af; font-size: 0.95rem; margin-bottom: 16px; }}
        .stats {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }}
        .stat {{ background: #1f2937; border: 1px solid #374151; border-radius: 10px; padding: 10px; text-align: center; }}
        .label {{ font-size: 0.75rem; color: #9ca3af; text-transform: uppercase; letter-spacing: 0.04em; }}
        .value {{ font-size: 1rem; font-weight: 600; color: #f9fafb; margin-top: 4px; }}
        .footer {{ margin-top: 14px; color: #9ca3af; font-size: 0.85rem; }}
    </style>
</head>
<body>
    <div class=\"card\">
        <div class=\"title\">{name}</div>
        <div class=\"meta\">{start_text}</div>
        <div class=\"stats\">
            <div class=\"stat\">
                <div class=\"label\">Ø Geschwindigkeit</div>
                <div class=\"value\">{speed_kmh} km/h</div>
            </div>
            <div class=\"stat\">
                <div class=\"label\">Distanz</div>
                <div class=\"value\">{distance_km} km</div>
            </div>
            <div class=\"stat\">
                <div class=\"label\">Dauer</div>
                <div class=\"value\">{duration_text}</div>
            </div>
        </div>
        <div class=\"footer\">Letzte Aktualisierung: {now.strftime('%d.%m.%Y %H:%M:%S')} ({relative_update})</div>
    </div>
</body>
</html>"""
    return html


def copyStravaAnalyseToHA(filename):
    try:
        destination = Path("/mnt/homeassistant/www") / filename
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(HEATMAP_DIR / filename, destination)
    except Exception as e:
        logToFile(str(e))
        logToFile("copyStravaAnalyseToHA failed")


def create_last_ride_html_file(filename, activities, now=None):
    HEATMAP_DIR.mkdir(parents=True, exist_ok=True)
    output_path = HEATMAP_DIR / filename
    html = get_last_ride_html(activities, now=now)

    try:
        if output_path.exists():
            output_path.unlink()
        with open(output_path, "w", encoding="utf-8") as file:
            file.write(html)
        copyStravaAnalyseToHA(filename)
    except Exception as e:
        logToFile(str(e))

    return output_path


def createStravaAnalyseHtml(filename, activities, now=None):
    return create_last_ride_html_file(filename, activities, now=now)


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
    def on_connect(client, userdata, flags, rc, properties=None):
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

    return activities


def run():
    client = connect_mqtt()
    client.loop_start()
    publish_pickle_summary(client)

    if _is_activity_store_fresh():
        activities = load_pickled_activities()
    else:
        activities = downloadGPXFile()
        if not activities:
            activities = load_pickled_activities()

    create_last_ride_html_file("strava_analyse.html", activities)
    client.loop_stop()



if __name__ == '__main__':
    run()
