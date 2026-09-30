import argparse
import json
import os
import pickle
import random
import re
import time
import shutil
from datetime import datetime, timedelta
from html import escape
from pathlib import Path

import requests
from paho.mqtt import client as mqtt_client

import login
from strava_secrets_request import (
    getFullIntervalsHeaderWithAccessToken,
    getGPXHeader,
    get_intervals_url,
    getSyncUrl,
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


def _sanitize_activity_name(value):
    text = str(value or "").strip()
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", text)
    return text.strip("._")


def _activity_key(activity):
    if not isinstance(activity, dict):
        return ""

    name = _sanitize_activity_name(activity.get("name") or activity.get("activity_name") or "")
    raw_value = activity.get("start_date_local") or activity.get("start_date") or ""
    key_timestamp = ""

    if raw_value:
        try:
            parsed = datetime.fromisoformat(str(raw_value).replace("Z", "+00:00"))
            key_timestamp = parsed.strftime("%Y-%m-%d-%H-%M-%S")
        except ValueError:
            key_timestamp = str(raw_value).replace("T", "-").replace(":", "-").replace("Z", "")
            key_timestamp = key_timestamp.split("+")[0].replace("_", "-")

    if not key_timestamp:
        start_dt = _parse_activity_datetime(activity)
        if start_dt is not None:
            key_timestamp = start_dt.strftime("%Y-%m-%d-%H-%M-%S")

    if key_timestamp and name:
        return f"{key_timestamp}_{name}"
    return key_timestamp or name


def _gpx_file_key(filename):
    stem = Path(filename).stem
    match = re.search(r"\d{4}-\d{2}-\d{2}(?:[-_]\d{2}){0,3}", stem)
    if not match:
        return ""

    ts = match.group(0).replace("_", "-")
    name = _sanitize_activity_name(stem[match.end():].lstrip("_"))
    if name:
        return f"{ts}_{name}"
    return ts


def _activity_from_gpx_filename(filename):
    stem = Path(filename).stem
    parsed = re.match(r"^(?P<ts>\d{4}-\d{2}-\d{2}(?:[-_]\d{2}){0,3})(?:[_-]+(?P<name>.*))?$", stem)

    timestamp = ""
    name = "Unbekannte Fahrt"

    if parsed:
        timestamp = (parsed.group("ts") or "").replace("_", "-")
        raw_name = parsed.group("name") or ""
        name = _sanitize_activity_name(raw_name) or "Unbekannte Fahrt"

    if not timestamp:
        timestamp = "1970-01-01-00-00-00"

    try:
        start_date_local = datetime.strptime(timestamp, "%Y-%m-%d-%H-%M-%S").isoformat(timespec="seconds")
    except ValueError:
        try:
            start_date_local = datetime.strptime(timestamp, "%Y-%m-%d-%H-%M").isoformat(timespec="seconds")
        except ValueError:
            try:
                start_date_local = datetime.strptime(timestamp, "%Y-%m-%d").isoformat(timespec="seconds")
            except ValueError:
                start_date_local = "1970-01-01T00:00:00"

    return {
        "id": f"gpx::{stem}",
        "name": name,
        "start_date_local": start_date_local,
        "distance": 0.0,
        "average_speed": 0.0,
        "moving_time": 0,
        "elapsed_time": 0,
        "total_elevation_gain": 0,
        "source": "gpx_scan",
    }


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


def scan_heatmap_gpx_dir():
    try:
        HEATMAP_GPX_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    if not HEATMAP_GPX_DIR.is_dir():
        return []

    known_keys = {
        _activity_key(item)
        for item in load_pickled_activities()
        if isinstance(item, dict) and _activity_key(item)
    }

    missing_files = []
    for gpx_path in sorted(HEATMAP_GPX_DIR.glob("*.gpx")):
        if not gpx_path.is_file():
            continue
        key = _gpx_file_key(gpx_path.name)
        if key and key not in known_keys:
            missing_files.append(gpx_path.name)
            activity = _activity_from_gpx_filename(gpx_path.name)
            if add_activity_to_pickle(activity):
                logToFile(f"Added missing GPX activity to pickle: {gpx_path.name}")

    if missing_files:
        logToFile(
            "Detected GPX files missing from pickle: " + ", ".join(sorted(missing_files))
        )
    return missing_files


def _remove_matching_gpx_files(activity):
    if not isinstance(activity, dict):
        return

    activity_key = _activity_key(activity)
    if not activity_key:
        return

    try:
        HEATMAP_GPX_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    if not HEATMAP_GPX_DIR.is_dir():
        return

    for gpx_path in HEATMAP_GPX_DIR.glob("*.gpx"):
        if _gpx_file_key(gpx_path.name) == activity_key:
            try:
                gpx_path.unlink(missing_ok=True)
            except Exception as exc:
                logToFile(f"Failed to remove GPX file {gpx_path}: {exc}")


def delete_activity_by_id(activity_id, remove_gpx=True):
    if activity_id in (None, ""):
        return False

    store = _load_activity_store()
    target_id = str(activity_id)
    removed_activity = None

    if isinstance(store, list):
        filtered = []
        for item in store:
            if isinstance(item, dict) and str(item.get("id")) == target_id:
                removed_activity = item
                continue
            filtered.append(item)

        if removed_activity is None:
            return False

        _save_activity_store(filtered)
        if remove_gpx:
            _remove_matching_gpx_files(removed_activity)
        return True

    try:
        import pandas as pd
        if hasattr(store, "columns") and "id" in store.columns:
            matches = store["id"].astype(str) == target_id
            if not matches.any():
                return False
            removed_activity = store.loc[matches].iloc[0].to_dict()
            cleaned_store = store.loc[~matches].copy()
            _save_activity_store(cleaned_store)
            if remove_gpx:
                _remove_matching_gpx_files(removed_activity)
            return True
    except Exception:
        pass

    return False


def update_activity_distance_by_id(activity_id, distance):
    if activity_id in (None, ""):
        return False

    try:
        distance_value = float(distance)
    except (TypeError, ValueError):
        return False

    store = _load_activity_store()
    target_id = str(activity_id)
    updated = False

    if isinstance(store, list):
        for item in store:
            if isinstance(item, dict) and str(item.get("id")) == target_id:
                item["distance"] = distance_value
                item["distance_raw"] = distance_value
                if "distance" not in item:
                    item["distance"] = distance_value
                updated = True
        if updated:
            _save_activity_store(store)
            return True
        return False

    try:
        import pandas as pd
        if hasattr(store, "columns") and "id" in store.columns:
            matches = store["id"].astype(str) == target_id
            if not matches.any():
                return False
            store.loc[matches, "distance"] = distance_value
            store.loc[matches, "distance_raw"] = distance_value
            _save_activity_store(store)
            return True
    except Exception:
        pass

    return False


def get_month_activity_rows(month_value, now=None):
    if month_value is None:
        now = now or datetime.now()
        month_value = now.strftime("%Y-%m")

    if not re.fullmatch(r"\d{4}-\d{2}", str(month_value)):
        raise ValueError("month must be in YYYY-MM format")

    rows = []
    target_month = str(month_value)

    for activity in load_pickled_activities():
        if not isinstance(activity, dict):
            continue

        activity_dt = _parse_activity_datetime(activity)
        if activity_dt is None:
            continue
        if activity_dt.strftime("%Y-%m") != target_month:
            continue

        rows.append({
            "id": activity.get("id"),
            "distance": _activity_distance_meters(activity),
            "date": activity_dt.strftime("%Y-%m-%d %H:%M:%S"),
        })

    rows.sort(key=lambda row: row["date"])
    return rows


def print_month_activities(month_value=None, now=None):
    rows = get_month_activity_rows(month_value, now=now)
    if not rows:
        label = month_value or (now or datetime.now()).strftime("%Y-%m")
        print(f"No activities for {label} in pickle.")
        return rows

    print("ID | Distance | Date")
    for row in rows:
        print(f"{row['id']} | {row['distance']} | {row['date']}")
    return rows


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
        return age_seconds <= max_age_minutes * 1
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


def _get_activity_elevation_gain(activity):
    if not isinstance(activity, dict):
        return 0

    for key in ("total_elevation_gain", "elevation_gain", "climbing", "total_ascent"):
        value = activity.get(key)
        if value is None:
            continue
        try:
            return int(float(value))
        except Exception:
            continue

    return 0


def _get_activity_period_summary(activities, now=None):
    now = now or datetime.now()
    start_of_week = now - timedelta(days=now.weekday())
    start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_week = start_of_week + timedelta(days=6, hours=23, minutes=59, seconds=59)

    summary = {
        "total": {"count": 0, "elevation_gain": 0},
        "this_week": {"count": 0, "elevation_gain": 0},
        "this_month": {"count": 0, "elevation_gain": 0},
        "this_year": {"count": 0, "elevation_gain": 0},
    }

    if not isinstance(activities, list):
        return summary

    for activity in activities:
        if not isinstance(activity, dict):
            continue

        activity_dt = _parse_activity_datetime(activity)
        elevation_gain = _get_activity_elevation_gain(activity)

        summary["total"]["count"] += 1
        summary["total"]["elevation_gain"] += elevation_gain

        if activity_dt is None:
            continue

        if activity_dt.year == now.year:
            summary["this_year"]["count"] += 1
            summary["this_year"]["elevation_gain"] += elevation_gain

        if activity_dt.year == now.year and activity_dt.month == now.month:
            summary["this_month"]["count"] += 1
            summary["this_month"]["elevation_gain"] += elevation_gain

        if start_of_week <= activity_dt <= end_of_week:
            summary["this_week"]["count"] += 1
            summary["this_week"]["elevation_gain"] += elevation_gain

    return summary


def _get_activity_period_counts(activities, now=None):
    summary = _get_activity_period_summary(activities, now=now)
    return {key: values["count"] for key, values in summary.items()}


def _get_total_elevation_gain(activities):
    summary = _get_activity_period_summary(activities)
    return summary["total"]["elevation_gain"]


def get_last_ride_html(activities, now=None):
    now = now or datetime.now()
    activity = _select_latest_activity(activities)
    period_summary = _get_activity_period_summary(activities, now=now)
    data_block = f"""<div class=\"card\" style=\"margin-top: 16px; width: min(100%, 720px); background: #111827; border: 1px solid #374151; box-shadow: 0 2px 8px rgba(0,0,0,0.35);\">
    <div class=\"title\">Daten</div>
    <div class=\"meta\">Höhenmeter nach Zeitraum</div>
    <div style=\"display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px;\">
        <div style=\"background: #1f2937; border: 1px solid #374151; border-radius: 10px; padding: 10px; text-align: center;\">
            <div style=\"font-size: 0.7rem; color: #9ca3af; text-transform: uppercase; letter-spacing: 0.04em;\">Diese Woche</div>
            <div style=\"font-size: 1rem; font-weight: 600; color: #f9fafb; margin-top: 4px;\">{period_summary['this_week']['elevation_gain']} m</div>
            <div style=\"font-size: 0.75rem; color: #9ca3af; margin-top: 6px;\">{period_summary['this_week']['count']} Fahrten</div>
        </div>
        <div style=\"background: #1f2937; border: 1px solid #374151; border-radius: 10px; padding: 10px; text-align: center;\">
            <div style=\"font-size: 0.7rem; color: #9ca3af; text-transform: uppercase; letter-spacing: 0.04em;\">Dieser Monat</div>
            <div style=\"font-size: 1rem; font-weight: 600; color: #f9fafb; margin-top: 4px;\">{period_summary['this_month']['elevation_gain']} m</div>
            <div style=\"font-size: 0.75rem; color: #9ca3af; margin-top: 6px;\">{period_summary['this_month']['count']} Fahrten</div>
        </div>
        <div style=\"background: #1f2937; border: 1px solid #374151; border-radius: 10px; padding: 10px; text-align: center;\">
            <div style=\"font-size: 0.7rem; color: #9ca3af; text-transform: uppercase; letter-spacing: 0.04em;\">Dieses Jahr</div>
            <div style=\"font-size: 1rem; font-weight: 600; color: #f9fafb; margin-top: 4px;\">{period_summary['this_year']['elevation_gain']} m</div>
            <div style=\"font-size: 0.75rem; color: #9ca3af; margin-top: 6px;\">{period_summary['this_year']['count']} Fahrten</div>
        </div>
    </div>
</div>"""

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
    {data_block}
</body>
</html>"""

    name = escape(str(activity.get("name") or "Unbekannte Fahrt"))
    start_dt = _parse_activity_datetime(activity)
    start_text = start_dt.strftime("%d.%m.%Y %H:%M") if start_dt else "Unbekannt"
    distance_km = round(_activity_distance_meters(activity) / 1000, 2)
    speed_kmh = round(_activity_average_speed(activity) * 3.6, 2)
    duration_minutes = round(_activity_moving_time_seconds(activity) / 60)
    duration_text = _format_duration(duration_minutes)

    html = f"""<!DOCTYPE html>
<html lang=\"de\">
<head>
    <meta charset=\"UTF-8\">
    <meta http-equiv=\"refresh\" content=\"15\">
    <title>Letzte Fahrt</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; min-height: 100vh; padding: 20px; background: #0f172a; color: #e5e7eb; display: flex; flex-direction: column; gap: 16px; align-items: center; justify-content: flex-start; box-sizing: border-box; }}
        .card {{ background: #111827; border: 1px solid #374151; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.35); padding: 20px; width: min(100%, 720px); }}
        .title {{ font-size: 1.1rem; font-weight: 600; margin-bottom: 6px; color: #f9fafb; }}
        .meta {{ color: #9ca3af; font-size: 0.95rem; margin-bottom: 16px; }}
        .stats {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }}
        .stat {{ background: #1f2937; border: 1px solid #374151; border-radius: 10px; padding: 10px; text-align: center; }}
        .label {{ font-size: 0.75rem; color: #9ca3af; text-transform: uppercase; letter-spacing: 0.04em; }}
        .value {{ font-size: 1rem; font-weight: 600; color: #f9fafb; margin-top: 4px; }}
        .summary {{ margin-top: 14px; background: #1f2937; border: 1px solid #374151; border-radius: 10px; padding: 12px; }}
        .summary-title {{ font-size: 0.9rem; font-weight: 600; color: #f9fafb; margin-bottom: 8px; }}
        .summary-grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px; }}
        .summary-item {{ background: #111827; border: 1px solid #374151; border-radius: 8px; padding: 8px; text-align: center; }}
        .summary-item .label {{ font-size: 0.7rem; color: #9ca3af; text-transform: uppercase; letter-spacing: 0.04em; }}
        .summary-item .value {{ font-size: 1rem; font-weight: 600; color: #f9fafb; margin-top: 4px; }}
        .summary-note {{ margin-top: 10px; color: #9ca3af; font-size: 0.8rem; line-height: 1.4; }}
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
        <div class=\"footer\">Letzte Aktualisierung: <span id=\"last-update\" data-ts=\"{now.strftime('%Y-%m-%dT%H:%M:%S')}\">{now.strftime('%d.%m.%Y %H:%M:%S')}</span> (<span id=\"last-update-relative\">lade...</span>)</div>
    </div>
    {data_block}
    <script>
        (function(){{
            function formatRelative(pastIso) {{
                var now = new Date();
                var past = new Date(pastIso);
                var delta = Math.floor((now - past) / 1000);
                if (delta < 60) return "gerade eben";
                var minutes = Math.floor(delta / 60);
                if (minutes < 60) return "vor " + minutes + " Minute" + (minutes !== 1 ? "n" : "");
                var hours = Math.floor(minutes / 60);
                if (hours < 24) return "vor " + hours + " Stunde" + (hours !== 1 ? "n" : "");
                var days = Math.floor(hours / 24);
                return "vor " + days + " Tag" + (days !== 1 ? "en" : "");
            }}

            function updateRelative() {{
                var tsEl = document.getElementById('last-update');
                var relEl = document.getElementById('last-update-relative');
                if (!tsEl || !relEl) return;
                var iso = tsEl.getAttribute('data-ts');
                if (!iso) return;
                relEl.textContent = formatRelative(iso);
            }}

            // Update immediately and then every 15 seconds
            updateRelative();
            setInterval(updateRelative, 15000);
        }})();
    </script>
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
        #print(json.dumps(payload, indent=2, ensure_ascii=False))
        
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
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            try:
                dt = datetime.strptime(value, '%Y-%m-%dT%H:%M:%S')
            except Exception:
                continue

        try:
            # Normalize tz-aware datetimes to local naive datetimes so comparisons
            # with naive `datetime.now()` work consistently.
            if dt.tzinfo is not None:
                dt = dt.astimezone().replace(tzinfo=None)
        except Exception:
            # If conversion fails, fall back to the parsed datetime as-is
            pass

        return dt
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

    period_counts = _get_activity_period_counts(activities, now=now)
    total_elevation_gain = _get_total_elevation_gain(activities)

    return {
        'timestamp': now.strftime('%Y-%m-%d, %H:%M:%S'),
        'distance_all': round(9135.2 + round(distance_all / 1000, 2), 2),
        'distance_month': round(distance_month / 1000, 2),
        'distance_year': round(2970.7 + round(distance_year / 1000, 2), 2),
        'average_speed_month': average_speed_month,
        'average_distance_month': average_distance_month,
        'max_average_speed': max_average_speed,
        'activity_counts': period_counts,
        'elevation_gain_total': total_elevation_gain,
    }


def publish_pickle_summary(client):
    summary = get_pickle_summary()
    MQTT_MSG = json.dumps(summary)
    publishMQTT(client, MQTT_MSG, login.topic)

def sync_activities(sleeptime = 5, header=None):
    sync_url, auth = getSyncUrl()
    try:
        response = requests.get(sync_url, headers=header)
        response.raise_for_status()
        print("Sync successful.")
        logToFile("Sync successful.")
        time.sleep(sleeptime)  # Optional: Wait for a short period to ensure the sync is processed
    except requests.exceptions.RequestException as e:
        print(f"Sync failed: {e}")
        logToFile(f"Sync failed: {e}")

def downloadGPXFile():
    header = getFullIntervalsHeaderWithAccessToken()

    sync_activities(5, header)


    print("Fetching activities after sync...")
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
        print(f"Processing activity {activity_id}: {activity_name} -> {output_path}")
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


def run(argv=None):
    parser = argparse.ArgumentParser(description="Strava heatmap sync helper")
    parser.add_argument("--delete-activity-id", type=str, help="Delete an activity from the pickle by its ID and remove matching GPX files.")
    parser.add_argument("--scan-heatmap-gpx-dir", action="store_true", help="Check the heatmap GPX directory against the pickle and print missing files.")
    parser.add_argument("--update-distance-id", type=str, help="Set the stored distance for a pickle activity by its ID.") #gpx::2026-05-03-18-43-26_Abendradfahrt
    parser.add_argument("--distance", type=float, help="Distance in meters to store for --update-distance-id.")
    parser.add_argument("--show-month", type=str, help="Print activities for a given month in YYYY-MM format, e.g. 2026-09 or 2025-01.")
    args = parser.parse_args(argv)

    if args.delete_activity_id is not None:
        deleted = delete_activity_by_id(args.delete_activity_id)
        print(f"Deleted activity {args.delete_activity_id}: {deleted}")
        return deleted

    if args.update_distance_id is not None:
        if args.distance is None:
            raise SystemExit("--distance is required when using --update-distance-id")
        updated = update_activity_distance_by_id(args.update_distance_id, args.distance)
        print(f"Updated distance for activity {args.update_distance_id}: {updated}")
        return updated

    if args.show_month is not None:
        try:
            rows = print_month_activities(args.show_month)
            return bool(rows)
        except ValueError as exc:
            raise SystemExit(str(exc))

    if args.scan_heatmap_gpx_dir:
        missing = scan_heatmap_gpx_dir()
        print(json.dumps(missing, ensure_ascii=False))
        return bool(missing)

    scan_heatmap_gpx_dir()

    client = connect_mqtt()
    client.loop_start()

    if _is_activity_store_fresh():
        activities = load_pickled_activities()
    else:
        activities = downloadGPXFile()
        if not activities:
            activities = load_pickled_activities()

    publish_pickle_summary(client)

    create_last_ride_html_file("strava_analyse.html", activities)
    client.loop_stop()
    return True


if __name__ == '__main__':
    run()
