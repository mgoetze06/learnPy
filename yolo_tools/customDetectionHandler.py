#script needs to be placed inside the yolov7 directory
#https://github.com/WongKinYiu/yolov7


#needs the file customDetectModule.py in the same directory




import argparse
from customDetectModule import customDetect
import cv2
import numpy as np
import glob

from utils.datasets import letterbox

#https://stackoverflow.com/questions/28345780/how-do-i-create-a-python-namespace-argparse-parse-args-value
class Namespace:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)



def limit(val,low,high):
    if val < low:
        val = low
    if val > high:
        val = high
    return val
    
    
def detectOnSingleImage(opt,img_path):
    ####################################################
    #https://github.com/WongKinYiu/yolov7/blob/main/utils/datasets.py
    #loadImage Function (this is where original detect.py loads its image
    ################################################
    img0 = cv2.imread(img_path)  # BGR
    org_img = np.copy(img0)
    assert img0 is not None, 'Image Not Found ' + path
            #print(f'image {self.count}/{self.nf} {path}: ', end='')

        # Padded resize
    myimage = letterbox(img0, img_size, stride=32)[0]

    # Convert
    myimage = myimage[:, :, ::-1].transpose(2, 0, 1)  # BGR to RGB, to 3x416x416
    myimage = np.ascontiguousarray(myimage)
    ######################################################


    #normal prediction using path from --source argument
    #img, det = customDetect(opt,customImg=None,customImg0=None,customPath = None)
    
    
    #prediction inside a script (using already opened cv2 image) and ignoring the --source argument
    img, det = customDetect(opt,customImg=myimage,customImg0=img0,customPath=img_path)
    show_single_detection = False
    if(show_single_detection):
        print(img.size)
        for d in range(len(det)):
            print(det[d])
            if det[d][1] == "0":
                x = det[d][0][0]*img.shape[1]
                y = det[d][0][1]*img.shape[0]
                w = det[d][0][2]*img.shape[1]
                h = det[d][0][3]*img.shape[0]
                
                print(x,y,w,h)
                x1 = int(x - w/2)
                x2 = int(x + w/2)
                y1 = int(y - h/2)
                y2 = int(y + h/2)
                
                x1 = limit(x1,0,img.shape[1])
                x2 = limit(x2,0,img.shape[1])
                y1 = limit(y1,0,img.shape[0])
                y2 = limit(y2,0,img.shape[0])
                
                
                print(img.shape)
                print(x1,x2,y1,y2)
                person = org_img[y1:y2,x1:x2]
                #file = "C:\projects\cv2\cv2_kamera\detections\person" + str(d) + ".jpeg"
                #cv2.imwrite(file,person)
                cv2.imshow("detection",person)
                cv2.waitKey()
    cv2.imshow("detection",img)
    cv2.waitKey()
    cv2.destroyAllWindows()

def detectOnImage(opt,img_path):
    files = []
    extension = [".jpg",".JPG","JPEG",".png"]
    
    if img_path.endswith(".jpg") or img_path.endswith(".png"):
        print("single image")
        files.append(img_path)
    else:
        print("is a path")
        print(img_path)
        for ext in extension:
            for file in glob.glob(img_path + "/*"+ext):
                files.append(file)
    print(files)
    model, stride = None, None
    for img_path in files:
    
            ####################################################
        #https://github.com/WongKinYiu/yolov7/blob/main/utils/datasets.py
        #loadImage Function (this is where original detect.py loads its image
        ################################################
        img0 = cv2.imread(img_path)  # BGR
        org_img = np.copy(img0)
        assert img0 is not None, 'Image Not Found ' + path
                #print(f'image {self.count}/{self.nf} {path}: ', end='')

            # Padded resize
        myimage = letterbox(img0, img_size, stride=32)[0]

        # Convert
        myimage = myimage[:, :, ::-1].transpose(2, 0, 1)  # BGR to RGB, to 3x416x416
        myimage = np.ascontiguousarray(myimage)
        ######################################################


        #normal prediction using path from --source argument
        #img, det = customDetect(opt,customImg=None,customImg0=None,customPath = None)
        
        
        #prediction inside a script (using already opened cv2 image) and ignoring the --source argument
        img, det, model, stride = customDetect(opt,customImg=myimage,customImg0=img0,customPath=img_path, model=model,stride=stride)
        show_single_detection = False
        if(show_single_detection):
            print(img.size)
            for d in range(len(det)):
                print(det[d])
                if det[d][1] == "0":
                    x = det[d][0][0]*img.shape[1]
                    y = det[d][0][1]*img.shape[0]
                    w = det[d][0][2]*img.shape[1]
                    h = det[d][0][3]*img.shape[0]
                    
                    print(x,y,w,h)
                    x1 = int(x - w/2)
                    x2 = int(x + w/2)
                    y1 = int(y - h/2)
                    y2 = int(y + h/2)
                    
                    x1 = limit(x1,0,img.shape[1])
                    x2 = limit(x2,0,img.shape[1])
                    y1 = limit(y1,0,img.shape[0])
                    y2 = limit(y2,0,img.shape[0])
                    
                    
                    print(img.shape)
                    print(x1,x2,y1,y2)
                    person = org_img[y1:y2,x1:x2]
                    #file = "C:\projects\cv2\cv2_kamera\detections\person" + str(d) + ".jpeg"
                    #cv2.imwrite(file,person)
                    cv2.imshow("detection",person)
                    cv2.waitKey()
        cv2.imshow("detection",img)
        cv2.waitKey()
    cv2.destroyAllWindows()




if __name__ == '__main__':
    print("script started")
    img_size=640
    opt = Namespace(weights='best.pt',#weights='yolov7.pt',
                    source="C:\projects\cv2\cv2_kamera\img1.jpeg",
                    img_size=img_size,
                    view_img=False,
                    no_trace=True,
                    save_txt=True,
                    nosave=False,
                    project='./',
                    exist_ok=True,
                    name='exp',
                    update=False,
                    augment=True,
                    agnostic_nms=True,
                    save_conf=True,
                    device='',
                    iou_thres=0.45,
                    conf_thres=0.5,
                    classes=None) #hier kann klassenfilter angegeben werden

    #print("detecting on single image")
    #detectOnSingleImage(opt,"C:\projects\cv2\cv2_kamera\data\\test_imgs\pic71.png")
    
    print("detecting on directory")
    detectOnImage(opt,"C:\projects\cv2\cv2_kamera\data\\test_imgs\\")
    #detectOnSingleImage(opt)
    
    
    
    
    
    #parser = argparse.ArgumentParser()
    #parser.add_argument('--weights', nargs='+', type=str, default='yolov7.pt', help='model.pt path(s)')
    #parser.add_argument('--source', type=str, default='inference/images', help='source')  # file/folder, 0 for webcam
    #parser.add_argument('--img-size', type=int, default=640, help='inference size (pixels)')
    #parser.add_argument('--conf-thres', type=float, default=0.25, help='object confidence threshold')
    #parser.add_argument('--iou-thres', type=float, default=0.45, help='IOU threshold for NMS')
    #parser.add_argument('--device', default='', help='cuda device, i.e. 0 or 0,1,2,3 or cpu')
    #parser.add_argument('--view-img', action='store_true', help='display results')
    #parser.add_argument('--save-txt', action='store_true', help='save results to *.txt')
    #parser.add_argument('--save-conf', action='store_true', help='save confidences in --save-txt labels')
    #parser.add_argument('--nosave', action='store_true', help='do not save images/videos')
    #parser.add_argument('--classes', nargs='+', type=int, help='filter by class: --class 0, or --class 0 2 3')
    #parser.add_argument('--agnostic-nms', action='store_true', help='class-agnostic NMS')
    #parser.add_argument('--augment', action='store_true', help='augmented inference')
    #parser.add_argument('--update', action='store_true', help='update all models')
    #parser.add_argument('--project', default='runs/detect', help='save results to project/name')
    #parser.add_argument('--name', default='exp', help='save results to project/name')
    #parser.add_argument('--exist-ok', action='store_true', help='existing project/name ok, do not increment')
    #parser.add_argument('--no-trace', action='store_true', help='don`t trace model')
    #opt = parser.parse_args('--weights yolov7.pt')
    #opt = parser.parse_args()
    
    #python .\detect.py --weights .\yolov7.pt --conf 0.5 --img-size 640
    #--source C:\projects\cv2\cv2_kamera\data\test_imgs\img1.jpeg --view-img --no-trace
    