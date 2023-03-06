import serial
ser = serial.Serial('COM5', 115200, timeout=1)
import vgamepad as vg
import time
import numpy
time.sleep(1)
gamepad = vg.VX360Gamepad()


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

sensor0 = sensor1 = steering = 0
sum_sensor = 0
for i in range(50):
    raw_data = ser.readline()
    stripped_data = raw_data.decode().strip()
    sum_sensor = sum_sensor + decodeString(3, stripped_data)[0]
zero_sensor = sum_sensor/50
print(zero_sensor)
#exit(0)
while True:
    raw_data = ser.readline()
    try:
        #print(raw_data)
        stripped_data = raw_data.decode().strip()
        #rotary = int(stripped_data)
        #new_gamepad_x_float = rotary / 3000
        #print(new_gamepad_x_float)
        sensors = decodeString(3,stripped_data)
        #print(sensors)
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
        print(sensor0,steering)
        gamepad.left_joystick_float(x_value_float=steering, y_value_float=sensor0)
        gamepad.update()
    except:
        pass




