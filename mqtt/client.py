import paho.mqtt.client as mqtt
import time

def on_message(client, userdata, message):
    print("message received " ,str(message.payload.decode("utf-8")))
    print("message topic=",message.topic)
    #print("message qos=",message.qos)
    #print("message retain flag=",message.retain)

mqttc = mqtt.Client()
#mqttc.on_message=on_message
#mqttc.connect("mqtt.eclipseprojects.io")
mqttc.connect("localhost")
mqttc.loop_start()
#mqttc.subscribe("test/home/test1")
counter = 0
while True:
    counter += 1
    mqttc.publish("test/home/test1",str(counter))
    print("published new data")
    time.sleep(2)
mqttc.loop_stop()