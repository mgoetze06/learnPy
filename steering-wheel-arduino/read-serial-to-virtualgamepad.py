import serial
ser = serial.Serial('COM5', 115200, timeout=1)
import vgamepad as vg
import time
time.sleep(1)
gamepad = vg.VX360Gamepad()
#gamepad = vg.VDS4Gamepad()
prev: int = 0
while True:
    raw_data = ser.readline()
    try:
        #print(raw_data)
        stripped_data = raw_data.decode().strip()
        rotary = int(stripped_data.split("P")[1].split("B")[0])
        button = int(stripped_data.split("P")[1].split("B")[1])
        #print(int(rotary))
        #print(button)
        if rotary > 1000:
            rotary = 1000
        if rotary < -1000:
            rotary = -1000
        if (rotary < 1000) and (rotary > -1000):
            offset = 0
            if rotary >= prev:
                offset = 100
                if rotary <= prev:
                    offset = -100
                else:
                    offset = 0
            rotary = rotary + offset

        new_gamepad_x_float = rotary/1000
        #new_gamepad_x = rotary * 10
        print(new_gamepad_x_float)
        gamepad.left_joystick_float(x_value_float=new_gamepad_x_float, y_value_float=0)
        #gamepad.left_joystick(x_value=new_gamepad_x, y_value=0)
        prev = rotary
        gamepad.update()
    except:
        pass