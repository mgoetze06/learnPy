import requests
import urllib3
from datetime import datetime
import os,shutil
from strava_secrets_request import getFullHeaderWithAccessToken,getSecrets
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


#########################################################################

# original source code: https://github.com/Jime567/strava2gpx
# https://jamesephelps.com/2024/07/18/how-to-get-gpx-files-from-the-strava-api-strava2gpx-python/
# code was adapted to work without async part from Jime567



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
    from datetime import datetime, timedelta
    #start_time = datetime.fromisoformat(start_timestamp.split("T")[0])
    start_timestamp = start_timestamp.replace("T"," ").replace("Z","")
    start_time = datetime.strptime(f"{start_timestamp}", "%Y-%m-%d %H:%M:%S") 
    new_time = start_time + timedelta(seconds=seconds)
    return (new_time.isoformat() + "Z").replace("+00:00", "")

def get_strava_activity(activity_id,header):
        api_url = 'https://www.strava.com/api/v3/activities/'
        url = f'{api_url}{activity_id}?include_all_efforts=false'

        data = requests.get(url, headers=header).json()
        return data
def writeGPX(output,activity,data_streams):
    gpx_content_start = f'''<?xml version="1.0" encoding="UTF-8"?>
<gpx xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd http://www.garmin.com/xmlschemas/GpxExtensions/v3 http://www.garmin.com/xmlschemas/GpxExtensionsv3.xsd http://www.garmin.com/xmlschemas/TrackPointExtension/v1 http://www.garmin.com/xmlschemas/TrackPointExtensionv1.xsd" creator="StravaGPX" version="1.1" xmlns="http://www.topografix.com/GPX/1/1" xmlns:gpxtpx="http://www.garmin.com/xmlschemas/TrackPointExtension/v1" xmlns:gpxx="http://www.garmin.com/xmlschemas/GpxExtensions/v3">
 <metadata>
  <time>{activity['start_date']}</time>
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

def copyGPXToHeatmapFolder(gpxfile):
    try:
        dest_dir = "/home/boris/projects/gpx-heatmap/heatmap/gpx"
        shutil.copyfile(gpxfile,dest_dir)
    except:
        logToFile("copyGPXToHeatmapFolder failed")
        pass

def tryToRemoveFile(file):
    try:
        os.remove(file)
    except:
        logToFile("removing gpx file failed.")
        pass

def main_http():

    header = getFullHeaderWithAccessToken()

    activity_id = 16875233580 #TODO check which activities already been downloaded and only get new ones
    

    activity = get_strava_activity(activity_id,header)
    output = activity['start_date'].replace("T","-").replace("Z","").replace(":","-") + "_" + activity['name'].replace(" ","_")+".gpx"
    data_streams = get_data_stream(activity_id,header)
    tryToRemoveFile(output)

    writeGPX(output,activity,data_streams)
    copyGPXToHeatmapFolder(output)

if __name__ == '__main__':
    main_http()
