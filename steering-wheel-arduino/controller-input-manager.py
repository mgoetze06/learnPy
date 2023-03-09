import matplotlib.pyplot as plt
import numpy as np

def compute_average(current_sensors,num_last_values):
    #compute the rolling average of all analog sensors using the num_last_values amount of last values
    
    #for i in range(len(current_sensors)):
    #    current_sensors
    return np.average(sensors)

def compute_array_sensors(current_sensors):
    #have an array where the current sensor data is the top item
    #whenever a new item appears, move all old items to next place
    #if items are older than TODO, delete them from array
    print(current_sensors)

sensors = [0.7,-0.4,-0.8,1,0]
fig, ax = plt.subplots(ncols=len(sensors),figsize=(21,10))
for idsensor,sensor in enumerate(sensors):
    print(sensor)
    ax[idsensor].bar(0,sensor)
    ax[idsensor].set_title("Sensor " + str(idsensor))
    ax[idsensor].set_xlim([-1, 1])
    ax[idsensor].set_ylim([-1, 1])
    ax[idsensor].hlines(compute_average(sensors,2),-1,1,colors="C1")

image = plt.show()