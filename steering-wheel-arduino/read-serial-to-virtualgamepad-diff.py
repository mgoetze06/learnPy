import serial
ser = serial.Serial('COM5', 115200, timeout=1)
import vgamepad as vg
import time
time.sleep(1)
gamepad = vg.VX360Gamepad()
#gamepad = vg.VDS4Gamepad()
prev = 0
rotary = 0
python_rotary = 0
temp2 = 0
temp = 0

#determine the first value that is sent over serial to get inital value for "prev"

no_prev = True
while no_prev:
    try:
        raw_data = ser.readline()
        stripped_data = raw_data.decode().strip()
        rotary = int(stripped_data.split("P")[1].split("BA")[0])
        print("input: ", rotary)
        prev = rotary
        no_prev = False
    except:
        pass

#actual application loop
prev_float = 0
direction_before = 0
steps_in_same_direction = 0
new_gamepad_x_float = 0
while True:
    try:
        raw_data = ser.readline()
        #print(raw_data)
        stripped_data = raw_data.decode().strip()
        print(stripped_data)
        error = False
        rotary = int(stripped_data.split("P")[1].split("BA")[0])
        print("input: ",rotary)
        button1 = int(stripped_data.split("P")[1].split("BA")[1].split("BB")[0])
        print("button1",button1)
        button2 = int(stripped_data.split("P")[1].split("BA")[1].split("BB")[1])
        print("button2", button2)
    except:
        error = True
        #pass
    if not error:
        if button2 != 0:
            gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER)
            gamepad.update()
            time.sleep(0.5)
            gamepad.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER)
            gamepad.update()
        #if button3 != 0:
        #    gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP)
        if button1 == 0:
            direction_now = int(rotary - prev)
            print("input - prev: ",direction_now)
            if direction_before == direction_now:
                steps_in_same_direction += 1
            else:
                steps_in_same_direction = 0
            direction_before = direction_now
            #temp2 = temp2 + temp
            #python_rotary = float(temp2 / 1000)
            python_rotary = prev_float + float(direction_now / 1000)
            print("python rotary: ",python_rotary)
            if python_rotary <= 0.1 and python_rotary > 0:
                #inside threshold
                if direction_now < 0: #from bigger than thresh to zero
                    print("back to zero")
                    #new_gamepad_x_float = 0
                    python_rotary = 0
                    prev_float = 0
                else:
                    python_rotary = 0.1
            if python_rotary >= -0.1 and python_rotary < 0:
                #inside threshold
                if direction_now > 0: #from lower than thresh to zero
                    print("back to zero")
                    #new_gamepad_x_float = 0
                    python_rotary = 0
                    prev_float = 0
                else:
                    python_rotary = -0.1
            if python_rotary == 0:
                #if direction_now > 0:
                #    python_rotary = 0.1
                #else:
                #    python_rotary = -0.1
                python_rotary = 0

            new_gamepad_x_float = python_rotary


            prev_float = new_gamepad_x_float
            prev = rotary
        else:
            python_rotary = 0
            prev_float = 0
        new_gamepad_x_float = python_rotary
        if new_gamepad_x_float > 1:
            new_gamepad_x_float = 1
        if new_gamepad_x_float < -1:
            new_gamepad_x_float = -1
        print(new_gamepad_x_float)
        gamepad.left_joystick_float(x_value_float=new_gamepad_x_float, y_value_float=0)
        #gamepad.left_joystick(x_value=new_gamepad_x, y_value=0)



        gamepad.update()
