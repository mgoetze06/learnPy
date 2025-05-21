import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def getFullHeaderWithAccessToken():
    auth_url = "https://www.strava.com/oauth/token"

    payload = {
        'client_id': "",
        'client_secret': '',
        'refresh_token': '',
        'grant_type': "refresh_token",
        'f': 'json'
    }

    print("Requesting Token...\n")
    res = requests.post(auth_url, data=payload, verify=False)
    access_token = res.json()['access_token']

    #print("Access Token = {}\n".format(access_token))
    header = {'Authorization': 'Bearer ' + access_token}

    return header