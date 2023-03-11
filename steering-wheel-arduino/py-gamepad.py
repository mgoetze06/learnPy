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

def debounce_trigger(last_triggers,triggers,triggers_counter,debounce_count):
    triggers_debounced = [0] * len(triggers)
    #print("triggers_debounced",triggers_debounced)
    #print("triggers",triggers)
    for i in range(len(triggers)):
        if triggers[i] == 0:
            if last_triggers[i] == triggers[i]:
                triggers_counter[i] += 1

                if triggers_counter[i] > debounce_count:
                    triggers_debounced[i] = 1 #1 means trigger is pushed after debounce
                    triggers_counter[i] = 0
                else:
                    triggers_debounced[i] = 0 #0 means trigger was not pushed or not debounced yet
            else:
                triggers_counter[i] = 0     
                triggers_debounced[i] = 0
        else:
            triggers_counter[i] = 0
    #print("triggers_counter",triggers_counter)
    return triggers_counter,triggers_debounced



len_history = 2
sensors_historical = [ [] for _ in range(len_history) ]
sensor0 = sensor1 = trigger1 = trigger2 = trigger3 = trigger4 = trigger5 = steering = 0
sum_sensor = 0
triggers_counter = [0,0,0,0]
triggers_last = [1,1,1,1]
triggers = []
saved_sensors = [0,0]

#mythread = Thread(target=handle_visuals_thread, args=())
#mythread.start()

def zero_sensor(sensor_num_in_array):
    zero_sensor = 0
    sum_sensor = 0
    try:
        for i in range(50):
            raw_data = ser.readline()
            stripped_data = raw_data.decode().strip()
            sum_sensor = sum_sensor + decodeString(7, stripped_data)[sensor_num_in_array]
        zero_sensor = int(sum_sensor/50)
    except:
        pass
    return zero_sensor
zero_sensors = [zero_sensor(0),zero_sensor(1)]
print(zero_sensors)



while True:
    raw_data = ser.readline()
    #try:
        
    stripped_data = raw_data.decode().strip()

    sensors = decodeString(7,stripped_data)

    sensor0 = sensors[0]
    sensor1 = sensors[1]
    dead_zone = 0.03
    if sensor0 > zero_sensors[0]+dead_zone:
        sensor0 = numpy.interp(sensor0, [zero_sensors[0], 1023], [0, 1])
    else:
        if sensor0 < zero_sensors[0]-dead_zone:
            sensor0 = numpy.interp(sensor0, [0, zero_sensors[0]], [-1, 0])
        else:
            sensor0 = 0
    if sensor1 > zero_sensors[1]+dead_zone:
        sensor1 = numpy.interp(sensor1, [zero_sensors[1], 1023], [0, 1])
    else:
        if sensor1 < zero_sensors[1]-dead_zone:
            sensor1 = numpy.interp(sensor1, [0, zero_sensors[1]], [-1, 0])
        else:
            sensor1 = 0
    #
    steering = sensors[2] / 3000
    if steering > 1:
        steering = 1
    if steering < -1:
        steering = -1
    trigger1 = sensors[3]
    trigger2 = sensors[4]
    trigger3 = sensors[5]
    trigger4 = sensors[6]
    #trigger5 = sensors[7]
    
    triggers = sensors[3:7] #for normal push button use of the gamepaftriggers variable contains raw information from sensor (for a normal button push it creates 7-30 impulses)
    #                           for normal push button use of the gamepad this is the preferred variable
    #                           if you want to have just the simple impulse, use the varibale triggers_debounced, which sends the impuls if the trigger gets debounced and still holds the value
    triggers_counter,triggers_debounced = debounce_trigger(triggers_last,triggers,triggers_counter,8)
    print(sensors[0:2],round(steering,2),triggers,triggers_counter,triggers_debounced)
    triggers_last = triggers

    if triggers[0] != 1:
        gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_A)
    else:
        gamepad.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_A)
    if triggers[1] != 1:
        gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_B)
    else:
        gamepad.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_B)
    if triggers[2] == 1: # ---> trigger[2] is not used for gamepad mode but for switching between joystick mode "driving" and "bale loading"
        gamepad.left_joystick_float(x_value_float=steering, y_value_float=sensor0)
        gamepad.right_joystick_float(x_value_float=0, y_value_float=0)
        saved_sensors = [sensor0,sensor1]
    else:
        gamepad.left_joystick_float(x_value_float=steering, y_value_float=saved_sensors[0])
        gamepad.right_joystick_float(x_value_float=sensor0, y_value_float=sensor1)
    if triggers[3] != 1:
        gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP)
    else:
        gamepad.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP)       
    #gamepad.update()
    
    gamepad.update()
    
    gamepad.update()
    #print(sensor0,sensor1,steering,trigger1,trigger2,trigger3,trigger4,trigger5)
    #print(sensor0,sensor1,steering,triggers_debounced)
    # sensors_historical = compute_array_sensors(sensors_historical,[sensor0,sensor1,steering,trigger1,trigger2],len_history)
    # avg_sensors = compute_average(sensors_historical=sensors_historical,num_last_values=2)
    # fig, ax = plt.subplots(ncols=len(sensors),figsize=(21,10))wwwwwwwwww
    # for idsensor,sensor in enumerate(sensors_historical[0]):
    #     #print(sensor)
    #     ax[idsensor].bar(0,sensor)
    #     ax[idsensor].set_title("Sensor " + str(idsensor))
    #     ax[idsensor].set_xlim([-1, 1])
    #     ax[idsensor].set_ylim([-1, 1])
    #     ax[idsensor].hlines(avg_sensors[idsensor],-1,1,colors="C1")

    # plt.show()
#except:
    #print("error")
#    pass




