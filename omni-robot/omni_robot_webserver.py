#https://github.com/davidrazmadzeExtra/RaspberryPi_HTTP_LED/blob/main/http_webserver.py


#import RPi.GPIO as GPIO
import os
import cv2
import math
import numpy as np
from http.server import BaseHTTPRequestHandler, HTTPServer

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
        global scale
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode("utf-8")
        print(post_data)
        post_data = post_data.split("=")[1]

        #setupGPIO()
        x_speed = 0
        y_speed = 0
        rot_speed = 0
        match post_data:
            case "X10":
                x_speed = 10
            case "X-10":
                x_speed = -10
            case "Y10":
                y_speed = 10
            case "Y-10":
                y_speed = 10
            case "rot":
                rot_speed = 10
            case "rot-":
                rot_speed = -10
            case "up":
                scale = scale + 1
            case "down":
                scale = scale - 1
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


# # # # # Main # # # # #

if __name__ == '__main__':
    http_server = HTTPServer((host_name, host_port), MyServer)
    print("Server Starts - %s:%s" % (host_name, host_port))

    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        http_server.server_close()
