import cv2
from flask import Flask, render_template, Response, send_file
import time, glob, random, os
from threading import Thread

camera = cv2.VideoCapture(0)
#camera = cv2.VideoCapture(0,cv2.CAP_DSHOW)
#fourcc = cv2.VideoWriter_fourcc(*'XVID')
print("Frame default resolution: (" + str(camera.get(cv2.CAP_PROP_FRAME_WIDTH)) + "; " + str(camera.get(cv2.CAP_PROP_FRAME_HEIGHT)) + ")")
camera.set(cv2.CAP_PROP_FRAME_WIDTH, 7680.0)#(7680, 4320
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 4320.0)
#1920#
#1080

#1280.0
#720.0

print("Frame resolution set to: (" + str(camera.get(cv2.CAP_PROP_FRAME_WIDTH)) + "; ")
app = Flask(__name__)

def take_snapshot():
    global camera
    while True:
        success, frame = camera.read()  # read the camera frame
        if not success:
            break
        else:
            named_tuple = time.localtime() # get struct_time
            time_string = time.strftime("%d.%m.%Y  %H:%M:%S", named_tuple)
            #print(time_string)
            frame = cv2.resize(frame, (780, 540),interpolation = cv2.INTER_LINEAR)
            cv2.putText(frame,time_string,(30,30),cv2.FONT_HERSHEY_SIMPLEX,1, (255,255,255), 2, cv2.LINE_AA)
            cv2.imwrite("./static/new_image.png", frame)
        time.sleep(15)


try:
    mythread = Thread(target=take_snapshot)
    mythread.start()
    threadStarted = True
except:
    print("could not start thread")


    


# def gen_frames():
#     while True:
#         success, frame = camera.read()  # read the camera frame
#         if not success:
#             break
#         else:
#             ret, buffer = cv2.imencode('.jpg', frame)
#             frame = buffer.tobytes()
#             yield (b'--frame\r\n'
#                    b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')  # concat frame one by one and show result
#         time.sleep(0.04)
# def gen_slideshow():
#     #success, frame = camera.read()  # read the camera frame
#     #if not success:
#     #    break
#     #else:
#     images = glob.glob("./images/*jpg")
#     while True:
#         #for file in glob.glob("./images/*jpg"):
#         file = random.sample(images, 1)
#         frame = cv2.imread(file[0])
#         frame = cv2.resize(frame,(1280,720))
#         ret, buffer = cv2.imencode('.jpg', frame)
#         frame = buffer.tobytes()
#         yield (b'--frame\r\n'
#                b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')  # concat frame one by one and show result
#         time.sleep(2)

# def testCamera():
#     print("camera init")
#     time.sleep(3)
#     print("starting....")
#     while True:
#         success, frame = camera.read()  # read the camera frame
#         if not success:
#             break
#         else:
#             cv2.imshow("frame",frame)
#             cv2.waitKey()

# @app.route('/video_feed_1')
# def video_feed_1():
#     #Video streaming route. Put this in the src attribute of an img tag
#     return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')
# @app.route('/video_feed_2')
# def video_feed_2():
#     #Video streaming route. Put this in the src attribute of an img tag
#     return Response(gen_slideshow(), mimetype='multipart/x-mixed-replace; boundary=frame')

# @app.route('/')
# def index():
#     """Video streaming home page."""
#     return render_template('index2.html')
# @app.route('/fullscreen1')
# def fullscreen1():
#     """Video streaming home page."""
#     return render_template('fullscreen1.html')
# @app.route('/fullscreen2')
# def fullscreen2():
#     """Video streaming home page."""
#     return render_template('fullscreen2.html')



@app.route('/snapshot1')
def snapshot1():
    """
    Return a random image from the ones in the static/ directory
    """
    img_dir = "./static"
    #img_list = os.listdir(img_dir)
    #img_path = os.path.join(img_dir, random.choice(img_list))
    img_path = os.path.join(img_dir, "new_image.png")
    return send_file(img_path, mimetype='image/png')   


if __name__ == '__main__':
    app.run(host="0.0.0.0")
    #app.run(debug=False)