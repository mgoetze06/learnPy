#https://github.com/davidrazmadzeExtra/RaspberryPi_HTTP_LED/blob/main/http_webserver.py

#https://tutorials-raspberrypi.com/mcp3008-read-out-analog-signals-on-the-raspberry-pi/



import RPi.GPIO as GPIO
import os
#import cv2
import math
import numpy as np
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread, Event, Lock
from time import sleep, time

data_lock = Lock()
event = Event()

# import RPi.GPIO as GPIO  # always needed with RPi.GPIO
# GPIO.setmode(GPIO.BCM)  # choose BCM or BOARD numbering schemes. I use BCM


host_name = '10.0.1.221'  # IP Address of Raspberry Pi
host_port = 8000

angles = [240,120,0]
a = math.cos((angles[0]/360)*2*math.pi)
b = math.cos((angles[1]/360)*2*math.pi)
c = math.cos(angles[2])
d = math.sin((angles[0]/360)*2*math.pi)
e = math.sin((angles[1]/360)*2*math.pi)
f = math.sin(angles[2])
g = h = i = 1
A = np.array([[a,b,c],
              [d,e,f],
              [g,h,i]], dtype=float)
A_inv = np.linalg.inv(A)


scale = 1
speed_m1 = speed_m2 = speed_m3 = 0
threadStarted = False
mythread = Thread()
event = Event()
GPIO.setmode(GPIO.BOARD)

counter = 0

def button_pressed_callback(channel):
    global encoderPinA
    global counter
    #print("recieved channel input")
    if not GPIO.input(encoderPinA):
        #print("Button pressed!")
        counter += 1
        print(counter)
    #else:
    #    print("Button released!")


encoderPinA = 15 #gpio22
GPIO.setup(encoderPinA, GPIO.IN)
#try:
print("setup event detect")
GPIO.add_event_detect(encoderPinA, GPIO.RISING,callback=button_pressed_callback, bouncetime=1)
print("setup event detect2")
#except:
#    print("try setup event detect")
#    pass 


def calcMotorSpeedFromDirectionSpeed(x_speed,y_speed,rot_speed,scale):
    m1 = A_inv[0] @ np.array([x_speed, y_speed, rot_speed])
    m2 = A_inv[1] @ np.array([x_speed, y_speed, rot_speed])
    m3 = A_inv[2] @ np.array([x_speed, y_speed, rot_speed])

    m1 = scale * m1
    m2 = scale * m2
    m3 = scale * m3

    neg_limit = -100
    pos_limit = 100

    m1 = limit(m1,neg_limit,pos_limit)
    m2 = limit(m2, neg_limit, pos_limit)
    m3 = limit(m3, neg_limit, pos_limit)

    m1 = (m1/100)*255
    m2 = (m2 / 100) * 255
    m3 = (m3 / 100) * 255

    return m1,m2,m3


def getTemperature():
    #temp = os.popen("/opt/vc/bin/vcgencmd measure_temp").read()
    temp = "35"
    return temp
def limit(m,min,max):
    if m > max:
        m = max
    if m < min:
        m = min
    return m

class MyServer(BaseHTTPRequestHandler):

    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def _redirect(self, path):
        self.send_response(303)
        self.send_header('Content-type', 'text/html')
        print(path)
        self.send_header('Location', path)
        self.end_headers()

    def do_GET(self):
        global scale
        html = '''
           <html>
           <title>Robotino</title>
           <body 
            style="width:960px; margin: 20px auto;">
           <h1>Robotino</h1>
           <p>Program to control Robotino (omni-directional robot) from webserver </p>
            <form action="/" method="POST">
               speed:
               <input type="submit" name="submit" value="up">
               <input type="submit" name="submit" value="down">
               {}
           </form>
           <form action="/" method="POST">
               control:
               <input type="submit" name="submit" value="X10">
               <input type="submit" name="submit" value="X-10">
               <input type="submit" name="submit" value="Y10">
               <input type="submit" name="submit" value="Y-10">
               <input type="submit" name="submit" value="rot">
               <input type="submit" name="submit" value="rot-">
           </form>
           </body>
           </html>
        '''
        #temp = getTemperature()
        self.do_HEAD()
        self.wfile.write(html.format(str(scale)).encode("utf-8"))


    def do_POST(self):
        global scale, speed_m1, speed_m2, speed_m3
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode("utf-8")
        print(post_data)
        post_data = post_data.split("=")[1]

        #setupGPIO()
        x_speed = 0
        y_speed = 0
        rot_speed = 0

        if post_data == "X10":
            x_speed = 10
        if post_data == "X-10":
            x_speed = -10
        if post_data == "Y10":
            y_speed = 10
        if post_data == "Y-10":
            y_speed = -10
        if post_data == "rot":
            rot_speed = 10
        if post_data == "rot-":
            rot_speed = -10
        if post_data == "up":
            scale = scale + 1
            if scale > 10:
                scale = 10
        if post_data == "down":
            scale = scale -1
            if scale < 1:
                scale = 1

        # if post_data == 'On':
        #     print("on")
        #     #GPIO.output(18, GPIO.HIGH)
        # else:
        #     print("off")
        #     #GPIO.output(18, GPIO.LOW)

        print("direction speed: ",x_speed,y_speed,rot_speed)

        speed_m1, speed_m2, speed_m3 = calcMotorSpeedFromDirectionSpeed(x_speed, y_speed, rot_speed,scale)
        print("motor speed: ",speed_m1, speed_m2, speed_m3)

        self._redirect('/')  # Redirect back to the root url
        self.handleThread() #call a thread with given speeds


    def handleThread(self):
        global threadStarted, mythread
        if threadStarted:
            event.set()
            mythread.join()
        event.clear()
        mythread = Thread(target=handle_io, args=(speed_m1,speed_m2,speed_m3,event))
        mythread.start()
        threadStarted = True


    
def handle_io(m1,m2,m3,event):
    #since this is a button controlled robot only write pwm for specified time
    #not constantly outputting signal
    

    
    
    m_enable = 38 #gpio20
    
    m1_pin = 11 #gpio17
    #m2_pin = 22
    #m3_pin = 23
    m1_dir_pin = 13 #gpio27
    #m2_dir_pin = 25
    #m3_dir_pin = 26
    
    #encoderPinA = 15 #gpio22
    #encoderPinB = 26 #gpio1
    
    
   
    GPIO.setup(m_enable, GPIO.OUT)
    GPIO.setup(m1_pin, GPIO.OUT)
    #GPIO.setup(m2_pin, GPIO.OUT)
    #GPIO.setup(m3_pin, GPIO.OUT)
    GPIO.setup(m1_dir_pin, GPIO.OUT)
    #GPIO.setup(m2_dir_pin, GPIO.OUT)
    #GPIO.setup(m3_dir_pin, GPIO.OUT)
    
    GPIO.output(m1_dir_pin, GPIO.HIGH)
    
    
    GPIO.output(m_enable, GPIO.HIGH)
    if m1 < 0:
        GPIO.output(m1_dir_pin, GPIO.HIGH)
    else:
        GPIO.output(m1_dir_pin, GPIO.LOW)
    #if m2 < 0:
    #    GPIO.output(m2_dir_pin, GPIO.HIGH)
    #else:
    #    GPIO.output(m2_dir_pin, GPIO.LOW)
    #if m3 < 0:
    #    GPIO.output(m3_dir_pin, GPIO.HIGH)
    #else:
    #    GPIO.output(m3_dir_pin, GPIO.LOW)
    
     #init PWM
    p1 = GPIO.PWM(m1_pin, 100) #port, freq
    #p2 = GPIO.PWM(m2_pin, 100)
    #p3 = GPIO.PWM(m3_pin, 100)
    #
     #start PWM Signal with dutycycle 0 --> no output, but pwm started
    p1.start(abs(m1))
    #p2.start(abs(m2))
    #p3.start(abs(m3))




    start = time()
    signal_time = 3
    print("recieved variable: ", m1, m2, m3)
    while time()-start < signal_time:

        #place gpio stuff here
        # import RPi.GPIO as GPIO  # always needed with RPi.GPIO
        # GPIO.setmode(GPIO.BCM)  # choose BCM or BOARD numbering schemes. I use BCM
        # GPIO.setup(25, GPIO.OUT)  # set GPIO 25 as an output. You can use any GPIO port
        # p = GPIO.PWM(25, 50)  # create an object p for PWM on port 25 at 50 Hertz
        # # you can have more than one of these, but they need
        # # different names for each port
        # # e.g. p1, p2, motor, servo1 etc.
        # p.start(50)  # start the PWM on 50 percent duty cycle
        # # duty cycle value can be 0.0 to 100.0%, floats are OK
        # p.ChangeDutyCycle(90)  # change the duty cycle to 90%
        # p.ChangeFrequency(100)  # change the frequency to 100 Hz (floats also work)
        # # e.g. 100.5, 5.2
        # p.stop()  # stop the PWM output
        # GPIO.cleanup()

        print("time left: ", signal_time - (time()-start))
        # print("encoder: ", GPIO.input(encoderPinA))
        #     with data_lock:
        #         var[i] += 1
        #         print(var[i])
        if event.is_set():
            event.clear()
            break
        sleep(0.1)
    print('Stopping output')
    p1.stop()
    #p2.stop()
    #p3.stop()
    GPIO.output(m_enable, GPIO.LOW)

# # # # # Main # # # # #

if __name__ == '__main__':
    http_server = HTTPServer((host_name, host_port), MyServer)
    print("Server Starts - %s:%s" % (host_name, host_port))

    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        http_server.server_close()

    # GPIO.cleanup()