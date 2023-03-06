import serial
ser = serial.Serial('COM5', 115200, timeout=1)
import vgamepad as vg
import time
time.sleep(1)
gamepad = vg.VX360Gamepad()
while True:
    raw_data = ser.readline()
    try:
        #print(raw_data)
        stripped_data = raw_data.decode().strip()
        rotary = int(stripped_data)
        new_gamepad_x_float = rotary / 3000
        print(new_gamepad_x_float)
        gamepad.left_joystick_float(x_value_float=new_gamepad_x_float, y_value_float=0)
        gamepad.update()
    except:
        pass