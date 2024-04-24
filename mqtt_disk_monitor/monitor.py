                        
import psutil
import random
import time
import login
import json

from paho.mqtt import client as mqtt_client


disk = psutil.disk_usage('/')
disk_free = round((disk.free /2**30),2)
disk_total = round((disk.total /2**30),2)
disk_percentage = round((disk_free /disk_total)*100,2)

#print(disk_free,disk_total,disk_percentage)


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

    client = mqtt_client.Client(client_id)
    #client.username_pw_set(username, password)
    client.username_pw_set(login.user, login.pw)
    client.on_connect = on_connect
    client.connect(login.broker, login.port)
    return client


def publish(client):

    MQTT_MSG=json.dumps({"disk_free": disk_free,"disk_total":  disk_total,"disk_percentage": disk_percentage});
    result = client.publish(login.topic, MQTT_MSG)
    # result: [0, 1]
    status = result[0]
    if status == 0:
        print(f"Send `{MQTT_MSG}` to topic `{login.topic}`")
    else:
        print(f"Failed to send message to topic {login.topic}")



def run():
    client = connect_mqtt()
    client.loop_start()
    publish(client)
    client.loop_stop()


if __name__ == '__main__':
    run()