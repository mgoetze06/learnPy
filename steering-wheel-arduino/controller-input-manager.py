import matplotlib.pyplot as plt
import numpy as np

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


len_history = 3
sensors_historical = [ [] for _ in range(len_history) ]
sensors = [0.7,-0.4,-0.8,1,0]
sensors_historical = compute_array_sensors(sensors_historical=sensors_historical,current_sensors=sensors,len_history=3)
#print(sensors_historical)
sensors = [0.4,-0.4,-0.4,0,1]
sensors_historical = compute_array_sensors(sensors_historical=sensors_historical,current_sensors=sensors,len_history=3)
sensors = [0.65,-0.4,-0.2,0,0]
sensors_historical = compute_array_sensors(sensors_historical=sensors_historical,current_sensors=sensors,len_history=3)
#print("sensors after adding to array: ",sensors_historical)

sensors = [0.7,-0.4,-0.8,1,1]
sensors_historical = compute_array_sensors(sensors_historical=sensors_historical,current_sensors=sensors,len_history=3)
#print(sensors_historical)
#print("average:")
#print(len(sensors_historical[0])-1)
avg_sensors = compute_average(sensors_historical=sensors_historical,num_last_values=2)

fig, ax = plt.subplots(ncols=len(sensors),figsize=(21,10))
for idsensor,sensor in enumerate(sensors_historical[0]):
    #print(sensor)
    ax[idsensor].bar(0,sensor)
    ax[idsensor].set_title("Sensor " + str(idsensor))
    ax[idsensor].set_xlim([-1, 1])
    ax[idsensor].set_ylim([-1, 1])
    ax[idsensor].hlines(avg_sensors[idsensor],-1,1,colors="C1")

image = plt.show()