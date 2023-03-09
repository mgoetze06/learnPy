import serial
ser = serial.Serial('COM5', 115200, timeout=1)
import vgamepad as vg
import time
import numpy
import matplotlib.pyplot as plt
import numpy as np
from threading import Thread, Event, Lock
time.sleep(1)
gamepad = vg.VX360Gamepad()


def compute_average(sensors_historical,num_last_values):
    #compute the rolling average of all analog sensors using the num_last_values amount of last values
    
    #for i in range(len(current_sensors)):
    #    current_sensors
    avg_sensors = [0,0,0,0,0]
    for i in range(num_last_values):
        for j in range(len(sensors_historical[0])):
            avg_sensors[j] += sensors_historical[i][j]
    for i in range(len(sensors_historical[0])):
        avg_sensors[i] = avg_sensors[i] / num_last_values     

    return avg_sensors

def compute_array_sensors(sensors_historical,current_sensors,len_history):
    #have an array where the current sensor data is the top item
    #whenever a new item appears, move all old items to next place
    #if items are older than TODO, delete them from array

    #array already has full length, last value gets deleted
    for i in range(len_history-1,-1,-1):
        #print("index: ",i)
        if i == 0:
            sensors_historical[0] = current_sensors
        else:
            sensors_historical[i] = sensors_historical[i-1]

    return sensors_historical

def decodeString(sensors_in, string):
    sensor_values = []
    for i in range(sensors_in):

        sensor_name = "S" + str(i + 1) + ":"
        #print(sensor_name)
        sensor_value = string.split(sensor_name)[1]
        try:
            #print(sensor_value)
            sensor_name = "S" + str(i + 2) + ":"

            sensor_value = sensor_value.split(sensor_name)[0]
        except:
            pass
        sensor_values.append(int(sensor_value))
    return sensor_values

def handle_visuals_thread():
    global sensors_historical
    global sensors
    fig, ax = plt.subplots(ncols=5,figsize=(21,10))
    plt.show()
    while True:
        avg_sensors = compute_average(sensors_historical=sensors_historical,num_last_values=2)
        try:
            for idsensor,sensor in enumerate(sensors_historical[0]):
                #print(sensor)
                ax[idsensor].clear()
                ax[idsensor].bar(0,sensor)
                ax[idsensor].set_title("Sensor " + str(idsensor))
                ax[idsensor].set_xlim([-1, 1])
                ax[idsensor].set_ylim([-1, 1])
                ax[idsensor].hlines(avg_sensors[idsensor],-1,1,colors="C1")
                #ax[idsensor].clear()
                #fig.canvas.draw()
                #fig.canvas.flush_events()
        except:
            pass
        time.sleep(1)



len_history = 2
sensors_historical = [ [] for _ in range(len_history) ]
sensor0 = sensor1 = trigger1 = trigger2 = steering = 0
sum_sensor = 0

mythread = Thread(target=handle_visuals_thread, args=())
mythread.start()


try:
    for i in range(50):
        raw_data = ser.readline()
        stripped_data = raw_data.decode().strip()
        sum_sensor = sum_sensor + decodeString(5, stripped_data)[0]
    zero_sensor = sum_sensor/50
    print(zero_sensor)
except:
    pass

#exit(0)
while True:
    raw_data = ser.readline()
    try:
        #print(raw_data)
        stripped_data = raw_data.decode().strip()
        #rotary = int(stripped_data)
        #new_gamepad_x_float = rotary / 3000
        #print(new_gamepad_x_float)
        sensors = decodeString(5,stripped_data)
        print(sensors)
        #sensors_historical = compute_array_sensors(sensors_historical,sensors,len_history)

        sensor0 = sensors[0]
        if sensor0 > zero_sensor + 10:
            sensor0 = numpy.interp(sensor0, [zero_sensor, 800], [0, 1])
        else:
            if sensor0 < zero_sensor - 1:
                sensor0 = numpy.interp(sensor0, [0, zero_sensor], [-1, 0])
            else:
                sensor0 = 0

        sensor1 = sensors[1]
        steering = sensors[2] / 3000
        if steering > 1:
            steering = 1
        if steering < -1:
            steering = -1
        trigger1 = sensors[3]
        trigger2 = sensors[4]
        if trigger2 != 0:
            sensor0 = 0
        if trigger1 == 0:
            gamepad.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_A)
        else:
            gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_A)
        gamepad.left_joystick_float(x_value_float=steering, y_value_float=sensor0)
        gamepad.update()
        sensors_historical = compute_array_sensors(sensors_historical,[sensor0,sensor1,steering,trigger1,trigger2],len_history)
        avg_sensors = compute_average(sensors_historical=sensors_historical,num_last_values=2)
        fig, ax = plt.subplots(ncols=len(sensors),figsize=(21,10))
        for idsensor,sensor in enumerate(sensors_historical[0]):
            #print(sensor)
            ax[idsensor].bar(0,sensor)
            ax[idsensor].set_title("Sensor " + str(idsensor))
            ax[idsensor].set_xlim([-1, 1])
            ax[idsensor].set_ylim([-1, 1])
            ax[idsensor].hlines(avg_sensors[idsensor],-1,1,colors="C1")

        plt.show()
    except:
        #print("error")
        pass




