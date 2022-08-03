import cv2
import math
import numpy as np
#https://www.youtube.com/watch?v=wwQQnSWqB7A


#print(math.cos(270))
a = math.cos(240)
b = math.cos(120)
c = math.cos(0)
d = math.sin(240)
e = math.sin(120)
f = math.sin(0)
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


def calcMotorSpeedFromDirectionSpeed(x_speed,y_speed,rot_speed):
    m1 = A_inv[0]@np.array([x_speed,y_speed,rot_speed])
    m2 = A_inv[1] @ np.array([x_speed, y_speed, rot_speed])
    m3 = A_inv[2] @ np.array([x_speed, y_speed, rot_speed])
    return m1,m2,m3

print(calcMotorSpeedFromDirectionSpeed(0,0,0))

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



