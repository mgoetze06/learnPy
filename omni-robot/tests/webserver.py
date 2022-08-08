#https://github.com/davidrazmadzeExtra/RaspberryPi_HTTP_LED/blob/main/http_webserver.py


#import RPi.GPIO as GPIO
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

host_name = '192.168.0.10'  # IP Address of Raspberry Pi
host_port = 8000


# def setupGPIO():
#     GPIO.setmode(GPIO.BCM)
#     GPIO.setwarnings(False)
#
#     GPIO.setup(18, GPIO.OUT)


def getTemperature():
    #temp = os.popen("/opt/vc/bin/vcgencmd measure_temp").read()
    temp = "35"
    return temp


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
           <p>Program to control Robotino (omni-directional robot) from webserver {}</p>
           <form action="/" method="POST">
               control :
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
        temp = getTemperature()
        self.do_HEAD()
        self.wfile.write(html.format(temp).encode("utf-8"))

    def do_POST(self):

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
        # if post_data == 'On':
        #     print("on")
        #     #GPIO.output(18, GPIO.HIGH)
        # else:
        #     print("off")
        #     #GPIO.output(18, GPIO.LOW)

        print(x_speed,y_speed,rot_speed)
        self._redirect('/')  # Redirect back to the root url


# # # # # Main # # # # #

if __name__ == '__main__':
    http_server = HTTPServer((host_name, host_port), MyServer)
    print("Server Starts - %s:%s" % (host_name, host_port))

    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        http_server.server_close()
