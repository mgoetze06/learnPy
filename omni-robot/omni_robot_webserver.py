#https://github.com/davidrazmadzeExtra/RaspberryPi_HTTP_LED/blob/main/http_webserver.py

#https://tutorials-raspberrypi.com/mcp3008-read-out-analog-signals-on-the-raspberry-pi/



#import RPi.GPIO as GPIO
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


host_name = '192.168.0.6'  # IP Address of Raspberry Pi
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

motorspeed_manual_fromhtml = seconds_to_run = 0
counter = 0
enc1 = enc2 = enc3 = m1_current = m2_current = m3_current = 0

def button_pressed_callback(channel):
    global encoderPinA
    global counter
    #print("recieved channel input")
    if not GPIO.input(encoderPinA):
        #print("Button pressed!")
        counter += 1
        #print(counter)
    #else:
    #    print("Button released!")

def ioSetup():
    GPIO.setmode(GPIO.BOARD)
    encoderPinA = 15 #gpio22
    GPIO.setup(encoderPinA, GPIO.IN)
    #try:
    print("setup event detect")
    GPIO.add_event_detect(encoderPinA, GPIO.RISING,callback=button_pressed_callback, bouncetime=1)
    print("setup event detect2")
    #except:
    #    print("try setup event detect")
    #    pass
#ioSetup()

def calcMotorSpeedFromDirectionSpeed(x_speed,y_speed,rot_speed):
    m1 = A_inv[0] @ np.array([x_speed, y_speed, rot_speed]) *3
    m2 = A_inv[1] @ np.array([x_speed, y_speed, rot_speed]) *3
    m3 = A_inv[2] @ np.array([x_speed, y_speed, rot_speed]) *3


    #m1 = scale * m1 * 3
    #m1 = m1
    #print("calc m1 speed: ",m1)
    #m2 = scale * m2
    #m3 = scale * m3

    neg_limit = -100
    pos_limit = 100

    m1 = limit(m1, neg_limit,pos_limit)
    m2 = limit(m2, neg_limit, pos_limit)
    m3 = limit(m3, neg_limit, pos_limit)

    # = m1 / 100
    
    #m2 = (m2 / 100) * 255
    #m3 = (m3 / 100) * 255

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
           <h2>Manual Control</h2>
           <h3>Seconds to run </h3>
            <form action="/" method="POST">
              <label for="secondsName">Seconds to run motor :</label><br>
              <label for="secondsName">Current Duration:  <b>%s s</b></label><br>
                <input type="submit" name="secondsName" value="1" oninput="this.form.amountRangeSeconds.value=this.value">
                <input type="range" name="amountRangeSeconds" min="1" max="10" value="1" oninput="this.form.secondsName.value=this.value"/>
            </form>
           <h3>Overall motor speed</h3>
            <form action="/" method="POST">
              <label for="motorspeed">Motor Speed (1 - 100):</label><br>
              <label for="motorspeed">Current Speed:  <b>%s</b></label><br>
                <input type="submit" name="motorspeed" value="1" oninput="this.form.amountRangeMotorspeed.value=this.value">
                <input type="range" name="amountRangeMotorspeed" min="1" max="100" value="1" oninput="this.form.motorspeed.value=this.value"/>
                <!--<input type="number" name="amountInput" min="1" max="100" value="1" oninput="this.form.amountRangeMotorspeed.value=this.value" />-->
            </form>
            <h3>Individual Motor Control</h3>
            
            
            
            <form action="/" method="POST">

               Motor 1:
               <input type="submit" name="submit" value="M1_left">
               <input type="submit" name="submit" value="M1_right"><br>
                Motor 2:
               <input type="submit" name="submit" value="M2_left">
               <input type="submit" name="submit" value="M2_right"><br>
                Motor 3:
               <input type="submit" name="submit" value="M3_left">
               <input type="submit" name="submit" value="M3_right"><br>
               </form>
               <h3>Motor Control from Coordination Plane</h3>
           <form action="/" method="POST">
               <input type="submit" name="submit" value="X-Y">
               <input type="submit" name="submit" value="Y">
               <input type="submit" name="submit" value="XY"><br>
               <input type="submit" name="submit" value="X-">
               <input type="submit" name="submit" value="    ">
               <input type="submit" name="submit" value="X"><br>
               <input type="submit" name="submit" value="X-Y-">
               <input type="submit" name="submit" value="Y-">
               <input type="submit" name="submit" value="XY-"><br>
               <br>
               <input type="submit" name="submit" value="rot">
               <input type="submit" name="submit" value="rot-">
           </form>
           <h2>Sensor data</h2>
           <div>
           Encoder M1: %s<br>
           Encoder M2: %s<br>
           Encoder M3: %s<br>
           Motor Current M1: %s<br>
           Motor Current M2: %s<br>
           Motor Current M3: %s<br>
           </div>           
           </body>
           </html>
        ''' % (str(seconds_to_run),str(motorspeed_manual_fromhtml),enc1,enc2,enc3,m1_current,m2_current,m3_current)
        #temp = getTemperature()
        self.do_HEAD()
        #self.wfile.write(html.format(str(scale)).encode("utf-8"))
        #print(html)
        self.wfile.write(html.encode("utf-8"))


    def do_POST(self):
        global scale, speed_m1, speed_m2, speed_m3,motorspeed_manual_fromhtml,seconds_to_run
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode("utf-8")
        print(post_data)
        type_of_data = post_data.split("=")[0]
        post_data = post_data.split("=")[1]
        if type_of_data == "motorspeed":
            motorspeed_manual_fromhtml = int(post_data.split("&")[0])

            print("recieved speed change: ",motorspeed_manual_fromhtml)
        elif type_of_data == "secondsName":
            seconds_to_run = int(post_data.split("&")[0])

            print("recieved seconds to run change: ",seconds_to_run)
        else:
            ###submit contains normal values

            #setupGPIO()
            x_speed = 0
            y_speed = 0
            rot_speed = 0
            speed_m1 =  speed_m2 = speed_m3 = 0
            if post_data == "M1_left":
                speed_m1 = -motorspeed_manual_fromhtml
            if post_data == "M1_right":
                speed_m1 = motorspeed_manual_fromhtml
            if post_data == "M2_left":
                speed_m2 = -motorspeed_manual_fromhtml
            if post_data == "M2_right":
                speed_m2 = motorspeed_manual_fromhtml
            if post_data == "M3_left":
                speed_m3 = -motorspeed_manual_fromhtml
            if post_data == "M3_right":
                speed_m3 = motorspeed_manual_fromhtml
            if post_data == "X-Y":
                x_speed = -motorspeed_manual_fromhtml
                y_speed = motorspeed_manual_fromhtml
            if post_data == "Y":
                y_speed = motorspeed_manual_fromhtml
            if post_data == "XY":
                x_speed = motorspeed_manual_fromhtml
                y_speed = motorspeed_manual_fromhtml
            if post_data == "X":
                x_speed = motorspeed_manual_fromhtml
            if post_data == "XY-":
                x_speed = motorspeed_manual_fromhtml
                y_speed = -motorspeed_manual_fromhtml
            if post_data == "Y-":
                y_speed = -motorspeed_manual_fromhtml
            if post_data == "X-Y-":
                x_speed = -motorspeed_manual_fromhtml
                y_speed = -motorspeed_manual_fromhtml
            if post_data == "X-":
                x_speed = -motorspeed_manual_fromhtml
            if post_data == "rot":
                rot_speed = motorspeed_manual_fromhtml
            if post_data == "rot-":
                rot_speed = -motorspeed_manual_fromhtml
           #if post_data == "up":
           #     seconds_to_run = seconds_to_run + 1
           #     if seconds_to_run > 10:
           #         seconds_to_run = 10
           # if post_data == "down":
           #     seconds_to_run = seconds_to_run -1
           #     if seconds_to_run < 1:
           #         seconds_to_run = 1

            if((x_speed != 0) or (y_speed != 0) or (rot_speed != 0)):
                #speed is given in coordinates, need to calculate motor speed from coordinate speed
                print("direction speed: ",x_speed,y_speed,rot_speed)

                speed_m1, speed_m2, speed_m3 = calcMotorSpeedFromDirectionSpeed(x_speed, y_speed, rot_speed)
            print("motor speed: ",speed_m1, speed_m2, speed_m3)
        
        self._redirect('/')  # Redirect back to the root url
        self.handleThread() #call a thread with given speeds


    def handleThread(self):
        global threadStarted, mythread
        try:
            if threadStarted:
                event.set()
                mythread.join()
        except:
            print("could not join thread")
            pass
        event.clear()
        try:
            mythread = Thread(target=handle_io, args=(speed_m1,speed_m2,speed_m3,event))
            #mythread.start()
            threadStarted = True
        except:
            print("could not start thread")


    
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
    print("speed_m1: ",m1)
     #start PWM Signal with dutycycle 0 --> no output, but pwm started
    p1.start(abs(m1))
    #p2.start(abs(m2))
    #p3.start(abs(m3))




    start = time()
    signal_time = seconds_to_run #from webserver
    print("recieved variable: ", m1, m2, m3)
    while time()-start < signal_time:
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