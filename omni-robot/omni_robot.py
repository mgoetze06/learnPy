import cv2
import math
import numpy as np
#https://www.youtube.com/watch?v=wwQQnSWqB7A

#angles [angle m1, angle m2, angle 3]
angles = [240,120,0]
#angles = [150,30,270]

#print(math.cos(270))
a = math.cos((angles[0]/360)*2*math.pi)
b = math.cos((angles[1]/360)*2*math.pi)
c = math.cos(angles[2])
d = math.sin((angles[0]/360)*2*math.pi)
e = math.sin((angles[1]/360)*2*math.pi)
f = math.sin(angles[2])
g = h = i = 1

det = (a*e*i)+(b*f*g)+(c*d*h)-(c*e*g)-(a*f*h)-(b*d*i)

A = np.array([[a,b,c],
              [d,e,f],
              [g,h,i]], dtype=float)
A_inv = np.linalg.inv(A)

# print(A)
# print(A_inv)
#
# print(a)
# print(A[0][0])
# print(A_inv[0][0])
#
# print(b)
# print(A[0][1])
# print(A_inv[0][1])
#
# print(f)
# print(A[1][2])
# print(A_inv[1][2])
height = width = 600
img = np.zeros((height, width, 3), np.uint8)
img[:, :] = [255, 255, 255]
center = (int(height/2), int(height/2))
cv2.circle(img, center, 2, (0, 255, 0), -1)
distance = int(height/3)

motor_center = [(center[0]-int(distance*math.sin((30/360)*2*math.pi)),center[1]+int(distance*math.cos((30/360)*2*math.pi))),
                (center[0]-int(distance*math.sin((30/360)*2*math.pi)),center[1]-int(distance*math.cos((30/360)*2*math.pi))),
                (center[0]+distance,center[1])]

def drawMotorPosition(img,point,text):
    cv2.circle(img, point, 7, (0, 255, 0), -1)
    cv2.putText(img, text, (point[0]+10,point[1]-50), cv2.FONT_HERSHEY_SIMPLEX,1, (0,0,0), 2, cv2.LINE_AA)

    return


def drawMotorSpeeds(img,m1,m2,m3):
    text = "M1: " + str(int(m1)) + " M2: " + str(int(m2)) + " M3: " + str(int(m3))
    cv2.putText(img, text, (0, height-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)


def drawSetValue(img,x,y,rot):
    text = "x: " + str(x) + " y: " + str(y) + " rot: " + str(rot)
    cv2.putText(img, text, (0,30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 1, cv2.LINE_AA)
    x_off = int(center[0] + y)
    y_off = int(center[1] + x)
    end_point = (x_off,y_off)
    cv2.line(img,center, end_point, (0, 255, 200), 1)
    cv2.circle(img, end_point, 4, (0, 200, 200), -1)

def drawMotorForce(img,point,direction,angle):
    scale = 0.75
    angle = ((angle)/360)*2*math.pi
    x_off = int(point[0] + math.sin(angle) * direction*scale)
    y_off = int(point[1] + math.cos(angle) * direction*scale)

    end_point = (x_off,y_off)
    cv2.line(img,point, end_point, (0, 255, 0), 1)
    cv2.circle(img, end_point, 4, (0, 100, 100), -1)

    return

def calcMotorSpeedFromDirectionSpeed(x_speed,y_speed,rot_speed):
    m1 = A_inv[0] @ np.array([x_speed, y_speed, rot_speed])
    m2 = A_inv[1] @ np.array([x_speed, y_speed, rot_speed])
    m3 = A_inv[2] @ np.array([x_speed, y_speed, rot_speed])

    neg_limit = -100
    pos_limit = 100

    m1 = limit(m1,neg_limit,pos_limit)
    m2 = limit(m2, neg_limit, pos_limit)
    m3 = limit(m3, neg_limit, pos_limit)

    m1 = (m1/100)*255
    m2 = (m2 / 100) * 255
    m3 = (m3 / 100) * 255

    return m1,m2,m3

def drawCoord(img):
    cv2.line(img, center, (center[0]+40,center[1]), (0, 255, 200), 1)
    cv2.line(img, center, (center[0],center[1]+40), (0, 255, 200), 1)
    cv2.putText(img, "y", (center[0]+40,center[1]-5), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 1, cv2.LINE_AA)
    cv2.putText(img, "x", (center[0]-30,center[1]+40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 1, cv2.LINE_AA)

def limit(m,min,max):
    if m > max:
        m = max
    if m < min:
        m = min
    return m
def mouse_click(event, x, y, flags, param):
    global x_speed,y_speed
    max_X = max_Y = 100
    if event == cv2.EVENT_LBUTTONDOWN:
        x_speed = y - center[1]
        y_speed = x - center[0]
        rot_speed = 0
       # draw circle here (etc...)
       #print('x = %d, y = %d'%(x, y))
x_speed = 20
y_speed = 0
rot_speed = 0
drawSetValue(img,x_speed,y_speed,rot_speed)
speed_m1,speed_m2,speed_m3 = calcMotorSpeedFromDirectionSpeed(x_speed,y_speed,rot_speed)
print(speed_m1,speed_m2,speed_m3)

drawMotorForce(img,motor_center[2],speed_m3,angles[2])
drawMotorForce(img,motor_center[1],speed_m2,angles[1])
drawMotorForce(img,motor_center[0],speed_m1,angles[0])

cv2.namedWindow("window")
cv2.setMouseCallback("window",mouse_click)

while(1):
    img = np.zeros((height, width, 3), np.uint8)
    img[:, :] = [255, 255, 255]
    cv2.circle(img, center, 2, (0, 255, 0), -1)
    drawCoord(img)
    drawMotorPosition(img, motor_center[2], "M3")
    drawMotorPosition(img, motor_center[1], "M2")
    drawMotorPosition(img, motor_center[0], "M1")
    drawSetValue(img, x_speed, y_speed, rot_speed)

    speed_m1, speed_m2, speed_m3 = calcMotorSpeedFromDirectionSpeed(x_speed, y_speed, rot_speed)
    drawMotorSpeeds(img,speed_m1, speed_m2, speed_m3)
    drawMotorForce(img, motor_center[2], speed_m3, angles[2])
    drawMotorForce(img, motor_center[1], speed_m2, angles[1])
    drawMotorForce(img, motor_center[0], speed_m1, angles[0])

    cv2.imshow("window", img)
    k = cv2.waitKey(20) & 0xFF
    if k == 27:
        break
# w = 1920
# h = 1080
# blank_image = np.zeros((h,w,3), np.uint8)
#
# img = cv2.imread("test_gesicht.JPG")
#
#
# def rescaleImage(img,w,h):
#     rescaled_image = np.zeros((h, w, 3), np.uint8)
#     imgHeight, imgWidth, _ = img.shape
#     if imgWidth > w or imgHeight > h:
#         ratio = min(w / imgWidth, h / imgHeight)
#         # ratio = w / imgWidth
#         # ratio = h / imgHeight
#         imgWidth = int(imgWidth * ratio)
#         imgHeight = int(imgHeight * ratio)
#         print(imgWidth, imgHeight)
#         # pilImage = pilImage.resize((imgWidth, imgHeight), Image.ANTIALIAS)
#         resized = cv2.resize(img, (imgWidth, imgHeight), interpolation=cv2.INTER_AREA)
#         x_offset = int(w / 2 - imgWidth / 2)
#         y_offset = int(h / 2 - imgHeight / 2)
#         print(x_offset, y_offset)
#         rescaled_image[y_offset:y_offset + imgHeight, x_offset:x_offset + imgWidth] = resized
#         cv2.imwrite("resized.jpg", resized)
#     return rescaled_image
#
# img = rescaleImage(img,w,h)
# cv2.namedWindow("window", cv2.WND_PROP_FULLSCREEN)
# cv2.setWindowProperty("window",cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN)
# cv2.imshow("window", img)
# cv2.waitKey(3000)
# img = cv2.imread("selection_collage.jpg")
# cv2.imshow("window", img)
# cv2.waitKey(0)



