import requests
import json

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

# Example Usage:
if __name__ == "__main__":
    data = get_strava_flyby_matches('<ID>')
    if data:
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