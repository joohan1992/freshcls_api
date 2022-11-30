

# -*- coding: utf-8 -*-
# <snippet_imports>
import cv2
import threading
import time
import numpy as np
import requests
from datetime import datetime
import base64
import sys
encoding = sys.getdefaultencoding()

#INFER_URL = 'http://10.28.100.11:8080//run'
INFER_URL = 'https://10.28.78.30:8889/run'
FEEDBACK_URL="https://10.28.78.30:8889/infer_feedback"
INIT_URL="https://10.28.78.30:8889/initialize"
CRUDENTIAL_KEY="7{@:M8IR;DW\\/X71uhHOd[nxa@uB%+m(/<Owq5LZ.kO%K583{t-fDb'GkE$YscX?N`X}M=WnMC<Ed}a4.$.lvDPL=q;i237fvcDjPPXmY`r.FU`@D*nQ]mBTNb#t7_Qw*Tr?f6]aTWm},Z(8L&^xI$^5Ccru'a.}'/uaN+{d\\Ox#FWv(ZT,>8vVC}kc2q2&'.qddiHnN}^*L]A*ZMT,{soMw@BrppFG[OIrv_bD/b67H:H0-;dxDID/Y[Yhz{y~VUVG|(aZ]]xj[jB*q)ARPA>)S._*JH]iE!zlnFzBatlkAfvy"

print("Program Starting")
###
LOGSRC="C:\\TOMATO\\POS\\cameradata.txt"
LOADIMGSRC="C:\\TOMATO\\POS\\SRC\\searching.jpg"
UNDEFMSG="Undefined"
CAM_MOVE_X=1300
CAM_MOVE_Y=28
IMGSIZE=(280,210)
DEVICENUM=0 
CAM_NAME="Camera"
BOARD_NAME="Board"
RTSP=""
STORE_NO=0
res = requests.post(INIT_URL,
        json={  "key": CRUDENTIAL_KEY,
                "store_no": STORE_NO, 
                "auth" : "code"
                }, verify=False) ## 나중에 ID 랑 PW 도 보내야됨(NONE으로)
result=res.json()['str_label_list']
item_Eng={}
item_Kor={}
for i in result:
    item_Eng[i[0]]=i[1]
    item_Kor[i[0]]=i[2]    
item_Kor[-1]=UNDEFMSG
item_Eng[-1]=UNDEFMSG

# 리스트 순회하면서 0번째 -> 1번째 (영어)
# 리스트 순회하면서 0번째 -> 2번째 (한글)
# 리스트 순회하면서 0번째 -> 3번째 (코드)
''' 예시
[[9, 'eggplant', '가지', '880008'], ....]]
'''
###
searching=cv2.imread(LOADIMGSRC,1)
btclk=False
btctrl=False
isCapt=False
isWrite=False
phase=0
camerastate=0

f_config = open('./config.txt', 'r')
lines = f_config.read()
print("Read Configuration")
sp_lines = lines.split('\n')
for line in sp_lines:
    token = line.split('\t')
    title = token[0]
    if title == 'DEVICENUM':
        DEVICENUM = int(token[1])
    elif title == 'RTSP':
        RTSP = str(token[1])
    elif title == 'INFER_URL':
        INFER_URL = str(token[1])
    elif title == 'FEEDBACK_URL':
        FEEDBACK_URL = str(token[1])
    elif title == 'INIT_URL':
        INIT_URL = str(token[1])
    elif title == 'CAM_MOVE_X':
        CAM_MOVE_X = str(token[1])
    elif title == 'CAM_MOVE_Y':
        CAM_MOVE_Y = str(token[1])
    elif title == 'CAM_NAME':
        CAM_NAME = str(token[1])
    elif title == 'BOARD_NAME':
        BOARD_NAME = str(token[1])        
    elif title == 'LOGSRC':
        LOGSRC = str(token[1])
    elif title == 'LOADIMGSRC':
        LOADIMGSRC = str(token[1])    
    elif title == 'KEY':
        CRUDENTIAL_KEY = str(token[1])
    elif title == 'Undefined Message':
        UNDEFMSG = str(token[1])
    elif title == 'IMGSIZE':
        IMGSIZE = ( int(str(token[1]).replace("(","").replace(")","").split(",")[0]),
                    int(str(token[1]).replace("(","").replace(")","").split(",")[1]))

print("Function Loading")


def label_to_board(item_num,item,label1,label2=None):
    if item_num==1:
        for i in range(0,56):
            for j in range(0,252):
                item[130+i][14+j]=label1[i][j]
        return item
    else:
        for i in range(0,56):
            for j in range(0,252):
                item[70+i][14+j]=label1[i][j]
        for i in range(0,56):
            for j in range(0,252):
                item[130+i][14+j]=label2[i][j]
def btctrl(event, x, y, flags, param):
   global btclk
   global phase
   if phase==2:
       if event==cv2.EVENT_LBUTTONDOWN:
            if (x>14 and x<266) and (y>70 and y<126):
                log(message=item_Kor[cls_list[0]],filepath=LOGSRC)
                phase=21
            elif (x>14 and x<266) and (y>130 and y<186):
                log(message=item_Kor[cls_list[1]],filepath=LOGSRC)
                phase=22
            else:
                btclk=switching(btclk)
   else:
       if event==cv2.EVENT_LBUTTONDOWN:
           btclk=switching(btclk)
def log(message,filepath,wtype="w"):
    file = open(filepath, wtype)
    file.write(message)
    file.close()
def now():
    now = datetime.now()
    string = str(now).replace(":", "-")
    return string[0:10]+"_"+string[11:22]
def switching(input):
    input = False if input == True else True
    return input

print("Video Initializing")

if len(RTSP)>4:
    try:
        capture = cv2.VideoCapture(RTSP)
        camerastate=-1
    except:
        print("Can't Find WebCamera. Use Local Camera...")
        capture = cv2.VideoCapture(DEVICENUM)
        camerastate=DEVICENUM
else:
    capture = cv2.VideoCapture(DEVICENUM)
    camerastate=DEVICENUM

ret, frame_origin = capture.read()
width = int(capture.get(3))
height = int(capture.get(4))
frame = None

cv2.namedWindow(BOARD_NAME, cv2.WINDOW_NORMAL)
cv2.setWindowProperty(BOARD_NAME, cv2.WND_PROP_FULLSCREEN, 1)
cv2.setWindowProperty(BOARD_NAME, cv2.WND_PROP_TOPMOST, 1)
cv2.resizeWindow(BOARD_NAME, IMGSIZE[0],IMGSIZE[1])
cv2.moveWindow(BOARD_NAME, CAM_MOVE_X,CAM_MOVE_Y)
cv2.setMouseCallback(BOARD_NAME,btctrl)

### camera threading
def camera():
    cv2.namedWindow(CAM_NAME, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(CAM_NAME, cv2.WND_PROP_FULLSCREEN, 1)
    cv2.setWindowProperty(CAM_NAME, cv2.WND_PROP_TOPMOST, 1)
    cv2.resizeWindow(CAM_NAME, IMGSIZE[0],IMGSIZE[1])
    cv2.moveWindow(CAM_NAME, CAM_MOVE_X+IMGSIZE[0],CAM_MOVE_Y)
    global frame
    time.sleep(2)
    while phase!=-1:
        cv2.setWindowProperty(CAM_NAME, cv2.WND_PROP_TOPMOST, 1)
        try:
            ret, frame_origin = capture.read()
            frame = cv2.resize(frame_origin, IMGSIZE)
            CAM_frame=frame.copy()
            cv2.putText(CAM_frame,"V4", (0, 30),cv2.FONT_HERSHEY_DUPLEX, 1, (0,0,0), 1, cv2.LINE_AA)
            cv2.imshow(CAM_NAME,CAM_frame)
            key = cv2.waitKey(1)
            if key & 0xFF == ord('q'):
                break 
        except:
            break
t=threading.Thread(target=camera)
t.daemon=True
t.start()
###
###
###

while(True):
    cv2.setWindowProperty(BOARD_NAME, cv2.WND_PROP_TOPMOST, 1)
    if frame is not None:
        if ret != True:  # read에 실패하면 loop탈출
          break
        if (isCapt==True and isWrite==False):
            Result1_IMG=frame.copy()
            Result2_IMG=frame.copy()

            if len(cls_list)==1:
                phase=1
                label_to_board(item_num=1,item=Result1_IMG,label1=cv2.imread("./fruitlabels/"+item_Eng[cls_list[0]]+".png",1))
                log(message=item_Kor[cls_list[0]],filepath=LOGSRC)

            elif len(cls_list)==2:## 두개있을때
                phase=2
                label_to_board(item_num=2,item=Result1_IMG,label1=cv2.imread("./fruitlabels/"+item_Eng[cls_list[0]]+".png",1), label2=cv2.imread("./fruitlabels/"+item_Eng[cls_list[1]]+".png",1))
            isWrite=True
            cv2.imshow(BOARD_NAME,Result1_IMG)

        if phase==21:
            label_to_board(item_num=1,item=Result2_IMG,label1=cv2.imread("./fruitlabels/"+item_Eng[cls_list[0]]+".png",1))
            cv2.imshow(BOARD_NAME,Result2_IMG)
            res = requests.post(FEEDBACK_URL,
                    json={  "feedback" : cls_list[0],
                            "infer_no":infer_no,
                            "key":CRUDENTIAL_KEY,
                            "auth" : "code"
                            }, verify=False)
            print(res.json()['result'])
            phase=3

        if phase==22:
            label_to_board(item_num=1,item=Result2_IMG,label1=cv2.imread("./fruitlabels/"+item_Eng[cls_list[1]]+".png",1))
            cv2.imshow(BOARD_NAME,Result2_IMG)
            res = requests.post(FEEDBACK_URL,
                    json={  "feedback" : cls_list[1],
                            "infer_no":infer_no,
                            "key":CRUDENTIAL_KEY,
                            "auth" : "code"
                            }, verify=False)
            print(res.json()['result'])
            phase=3
        key = cv2.waitKey(1)

        if btclk==True:
            #화면전환
            cv2.imshow(BOARD_NAME,searching)
            key = cv2.waitKey(1)
            # 초기화
            log(message=UNDEFMSG,filepath=LOGSRC)
            cls_list=[]
            isCapt=True
            isWrite=False
            if camerastate==-1:
                y=150
                h=260
                x=150
                w=490
                req_img=cv2.resize(req_img[y: y + h, x: x + w],IMGSIZE)
            try:
                # 전송할 이미지 현재 frame에서 copy
                req_img=frame.copy()
                # img to str
                encoded_byte = base64.b64encode(req_img)   
                imgstr=encoded_byte.decode(encoding)
                # request
                res = requests.post(INFER_URL,
                                    json={  "image" : imgstr,
                                            "x_size":IMGSIZE[0],
                                            "y_size":IMGSIZE[1],
                                            "channel":3,
                                            "key":CRUDENTIAL_KEY,
                                            "store_no":0,
                                            "auth":"code",
                                            "ID":"None",
                                            "PW":"None"
                                            }, verify=False)
                if res.json()['result']=="ok":
                    cls_list=res.json()['cls_list']
                    infer_no=res.json()['infer_no']
                    print("Server POST : "+res.json()['result'])
                else:
                    print("Server POST : "+res.json()['result'])
            except Exception as e:
                print("ERROR : ",end="")
                print(e)
            btclk=False
        if key & 0xFF == ord('q'):
            break
phase=-1
print("exit")
capture.release()
cv2.destroyAllWindows()





