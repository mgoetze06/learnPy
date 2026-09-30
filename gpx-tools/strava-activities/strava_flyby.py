import requests
import json

def get_activity_id_from_share_link(share_link):
    response = requests.get(share_link)
    response.raise_for_status()
    if response.status_code != 200:
        return None

    fullText = response.text
    fullText = fullText.split('https://www.strava.com/activities/')[1]
    #print(fullText)
    fullText = fullText.split("?utm_source=")[0]
    #print(fullText)
    return fullText if fullText else None


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
        'Accept-Encoding': 'gzip, deflate, br, zstd',
    }
    print(headers)
    print(f"Fetching flyby matches for activity ID: {activity_id}")
    print(f"Request URL: {url}")
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except Exception as err:
        print(f"An error occurred: {err}")

# Example Usage:
if __name__ == "__main__":

    activity_id = get_activity_id_from_share_link('https://strava.app.link/<mobile_link>')
    print("Activity ID:_", activity_id, "_")
    if not activity_id:
        print("Failed to extract activity ID.")
        exit(0)

    data = get_strava_flyby_matches(activity_id)
    if not data:
        print("Failed to fetch flyby matches.")
        exit(0)
    print(data)
    print(len(data['matches']))
    ownActivity = data['activity']
    print(ownActivity)
    ownID = ownActivity['athleteId']
    print(ownID)
    athletes = data['athletes']
    print(athletes)
    count = len([entry for entry in athletes if str(entry) != str(ownID)])
    print("Matches: ", count)
    #print(json.dumps(data, indent=2))