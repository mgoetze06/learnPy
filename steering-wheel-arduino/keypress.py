from pynput.keyboard import Key, Controller
import time


keyboard = Controller()

time.sleep(3)
while True:
    char = '4'
    print("pressing ",char)
    keyboard.press(char)
    time.sleep(0.2)
    print("releasing ",char)
    keyboard.release(char)
    time.sleep(3)
