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




host_name = '192.168.0.10'  # IP Address of Raspberry Pi
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
enable = False
threadStarted = False
mythread = Thread()
event = Event()

motorspeed_manual_fromhtml = seconds_to_run = 0
counter = 0
enc1 = enc2 = enc3 = m1_current = m2_current = m3_current = 0




def encoder_callback1(channel):
    #rising edge of encoderPinA
    global encoder1PinB
    global enc1
    if GPIO.input(encoder1PinB):
        #both encoders are high
        #first direction
        enc1 -= 1
    else:
        #encA is high, but B is low
        #other direction
        enc1 += 1
def encoder_callback2(channel):
    #rising edge of encoderPinA
    global encoder2PinB
    global enc2
    if GPIO.input(encoder2PinB):
        #both encoders are high
        #first direction
        enc2 -= 1
    else:
        #encA is high, but B is low
        #other direction
        enc2 += 1
def encoder_callback3(channel):
    #rising edge of encoderPinA
    global encoder3PinB
    global enc3
    if GPIO.input(encoder3PinB):
        #both encoders are high
        #first direction
        enc3 -= 1
    else:
        #encA is high, but B is low
        #other direction
        enc3 += 1

def adcSetup():
    # Simple demo of reading each analog input from the ADS1x15 and printing it to
    # the screen.
    # Author: Tony DiCola
    # License: Public Domain
    # https://learn.adafruit.com/raspberry-pi-analog-to-digital-converters/ads1015-slash-ads1115
    # Import the ADS1x15 module.
    import Adafruit_ADS1x15
    # sudo pip install adafruit-ads1x15

    # Create an ADS1115 ADC (16-bit) instance.
    adc = Adafruit_ADS1x15.ADS1115()

    # Or create an ADS1015 ADC (12-bit) instance.
    # adc = Adafruit_ADS1x15.ADS1015()

    # Note you can change the I2C address from its default (0x48), and/or the I2C
    # bus by passing in these optional parameters:
    # adc = Adafruit_ADS1x15.ADS1015(address=0x49, busnum=1)

    # Choose a gain of 1 for reading voltages from 0 to 4.09V.
    # Or pick a different gain to change the range of voltages that are read:
    #  - 2/3 = +/-6.144V
    #  -   1 = +/-4.096V
    #  -   2 = +/-2.048V
    #  -   4 = +/-1.024V
    #  -   8 = +/-0.512V
    #  -  16 = +/-0.256V
    # See table 3 in the ADS1015/ADS1115 datasheet for more info on gain.
    GAIN = 1
    #print('Reading ADS1x15 values, press Ctrl-C to quit...')
    # Print nice channel column headers.
    #print('| {0:>6} | {1:>6} | {2:>6} | {3:>6} |'.format(*range(4)))
    #print('-' * 37)
    return adc,GAIN

def readADC(adc,gain,seconds_to_sleep):
    values = [0] * 4
    for i in range(4):
    # Read the specified ADC channel using the previously set gain value.

        values[i] = adc.read_adc(i, gain=gain)
        #print(values[i])
        # Note you can also pass in an optional data_rate parameter that controls
        # the ADC conversion time (in samples/second). Each chip has a different
        # set of allowed data rate values, see datasheet Table 9 config register
        # DR bit values.
        #values[i] = adc.read_adc(i, gain=GAIN, data_rate=128)
        # Each value will be a 12 or 16 bit signed integer value depending on the
        # ADC (ADS1015 = 12-bit, ADS1115 = 16-bit).
        # Print the ADC values.
    #print(value)
    # print('| {0:>6} | {1:>6} | {2:>6} | {3:>6} |'.format(*values))
    # Pause for half a second.
    sleep(seconds_to_sleep)
    return values

def handleADC():
    global m1_current,m2_current,m3_current
    seconds_to_sleep = 1
    adc,gain = adcSetup()
    while True:
        if (not adc)or(not gain):
            adc, gain = adcSetup()
        m1_current,m2_current,m3_current,_ = readADC(adc,gain,seconds_to_sleep)


def ioSetup():
    print("RPI: io setup starting...")
    global encoder1PinA
    global encoder1PinB
    global encoder2PinA
    global encoder2PinB
    global encoder3PinA
    global encoder3PinB

    encoder1PinA = 15 #gpio22
    encoder1PinB = 19 #gpio10
    encoder2PinA = 29 #gpio5
    encoder2PinB = 31 #gpio6
    encoder3PinA = 37 #gpio26
    encoder3PinB = 39 #not sure

    GPIO.setmode(GPIO.BOARD)

    GPIO.setup(encoder1PinA, GPIO.IN)
    GPIO.setup(encoder1PinB, GPIO.IN)
    GPIO.setup(encoder2PinA, GPIO.IN)
    GPIO.setup(encoder2PinB, GPIO.IN)
    GPIO.setup(encoder3PinA, GPIO.IN)
    GPIO.setup(encoder3PinB, GPIO.IN)


    GPIO.add_event_detect(encoder1PinA, GPIO.RISING, callback=encoder_callback1, bouncetime=1)
    GPIO.add_event_detect(encoder2PinA, GPIO.RISING, callback=encoder_callback2, bouncetime=1)
    GPIO.add_event_detect(encoder3PinA, GPIO.RISING, callback=encoder_callback3, bouncetime=1)

    try:
        adcthread = Thread(target=handleADC)
        adcthread.start()
        print("RPI: adc thread started")
        #threadStarted = True
    except:
        print("RPI: could not start adc thread")

    print("RPI: io setup complete!")



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
            <div style="width: 800px; float:left;">
            <div style="width: 400px; float:left;">
            <h3>Overall motor speed</h3>
            <form action="/" method="POST">
              <label for="motorspeed">Motor Speed (1 - 100):</label><br>
              <label for="motorspeed">Current Speed:  <b>%s</b></label><br>
                <input type="submit" name="motorspeed" value="1" oninput="this.form.amountRangeMotorspeed.value=this.value">
                <input type="range" name="amountRangeMotorspeed" min="1" max="100" value="1" oninput="this.form.motorspeed.value=this.value"/>
                <!--<input type="number" name="amountInput" min="1" max="100" value="1" oninput="this.form.amountRangeMotorspeed.value=this.value" />-->
            </form>
            </div>
            <div style="width: 400px; float:left;">
            <h3>Enable motors</h3>
            <form action="/" method="POST">
                <input type="submit" name="enable" value="enable">
                <input type="submit" name="enable" value="disable">
            </form>
            </div>
            </div>
            <div style="width: 800px; float:left;">
            <div style="width: 400px; float:left;">
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
            </div>
            <div style="width: 400px; float:left;">
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
           </div>
           </div>
           <div style="width: 800px; float:left;">
           <h2>Sensor data</h2>
            <div style="width: 400px; float:left;">
           Encoder M1: %s<br>Encoder M2: %s<br>Encoder M3: %s<br>
           </div>    
           <div style="width: 400px; float:left;">
           Motor Current M1: %s<br>Motor Current M2: %s<br>Motor Current M3: %s<br>
           </div>      
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
        global scale, speed_m1, speed_m2, speed_m3,motorspeed_manual_fromhtml,seconds_to_run,enable
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
        elif type_of_data == "enable":
            if post_data =="enable":
                enable = True
            elif post_data == "disable":
                enable = False
            print("recieved enable")
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
            mythread = Thread(target=handle_io, args=(speed_m1,speed_m2,speed_m3,event,enable))
            mythread.start()
            threadStarted = True
        except:
            print("could not start thread")


    
def handle_io(m1,m2,m3,event,enable):
    #since this is a button controlled robot only write pwm for specified time
    #not constantly outputting signal
    global pi_is_used
    
    if pi_is_used:
        m_enable = 38 #gpio20

        m1_pin = 11 #gpio17
        m2_pin = 22
        m3_pin = 23
        m1_dir_pin = 13 #gpio27
        m2_dir_pin = 25
        m3_dir_pin = 26

        GPIO.setup(m_enable, GPIO.OUT)
        GPIO.setup(m1_pin, GPIO.OUT)
        GPIO.setup(m2_pin, GPIO.OUT)
        GPIO.setup(m3_pin, GPIO.OUT)
        GPIO.setup(m1_dir_pin, GPIO.OUT)
        GPIO.setup(m2_dir_pin, GPIO.OUT)
        GPIO.setup(m3_dir_pin, GPIO.OUT)

        GPIO.output(m1_dir_pin, GPIO.HIGH)

        if enable:
            GPIO.output(m_enable, GPIO.HIGH)
        else:
            GPIO.output(m_enable, GPIO.LOW)
        if m1 < 0:
            GPIO.output(m1_dir_pin, GPIO.HIGH)
        else:
            GPIO.output(m1_dir_pin, GPIO.LOW)
        if m2 < 0:
            GPIO.output(m2_dir_pin, GPIO.HIGH)
        else:
            GPIO.output(m2_dir_pin, GPIO.LOW)
        if m3 < 0:
            GPIO.output(m3_dir_pin, GPIO.HIGH)
        else:
            GPIO.output(m3_dir_pin, GPIO.LOW)

         #init PWM
        p1 = GPIO.PWM(m1_pin, 100) #port, freq
        p2 = GPIO.PWM(m2_pin, 100)
        p3 = GPIO.PWM(m3_pin, 100)
        #
        #print("speed_m1: ",m1)
        #start PWM Signal with dutycycle 0 --> no output, but pwm started
        p1.start(abs(m1))
        p2.start(abs(m2))
        p3.start(abs(m3))
        print("recieved variable: ", m1, m2, m3)



    start = time()
    signal_time = seconds_to_run #from webserver
    while time()-start < signal_time:
        print(time()-start)
        if event.is_set():
            event.clear()
            break
        sleep(0.2)
    print('Stopping output')
    if pi_is_used:
        p1.stop()
        p2.stop()
        p3.stop()
        GPIO.output(m_enable, GPIO.LOW)

# # # # # Main # # # # #

if __name__ == '__main__':
    global pi_is_used
    pi_is_used = False
    if pi_is_used:
        import RPi.GPIO as GPIO  # always needed with RPi.GPIO
        ioSetup()

    http_server = HTTPServer((host_name, host_port), MyServer)
    print("Server Starts - %s:%s" % (host_name, host_port))
    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        http_server.server_close()

    # GPIO.cleanup()