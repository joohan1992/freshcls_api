

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

URL = 'http://10.28.100.11:8080//run'
URL = 'https://10.28.78.30:8889//run'
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

itemKor={'eggplant' : '가지', 'persimmon' : '감', 'potato' : '감자', 'sweetpotato' : '고구마', 
        'pepper' : '고추', 'sesame' : '깻잎', 'paprika(yellow)' : '파프리카(노랑)', 'carrot' : '당근', 
        'green onion' : '대파', 'lemon' : '레몬', 'radish' : '무', 'banana' : '바나나', 
        'broccoli' : '브로콜리', 'paprika(red)' : '파프리카(빨강)', 'apple' : '사과', 'shinemuscat' : '샤인머스캣', 
        'avocado' : '아보카도', 'babypumpkin' : '애호박', 'cabbage' : '양배추', 'gganonion' : '깐양파',
        'angganonion' : '안깐양파', 'orange' : '오렌지', 'cucumber' : '오이', 'grape' : '포도', 
        'garibi' : '가리비', 'gosari' : '고사리', 'gosu' : '고수', 'mushroom' : '느타리버섯', 'daechu' : '대추',
        'strawberry' : '딸기', 'garlic' : '마늘', 'pear' : '배', 'koreancabbage' : '배추', 'peach' : '복숭아',
        'sangchu' : '상추', 'sora' : '소라', 'watermelon' : '수박', 'spinach' : '시금치', 'ssukgod' : '쑥갓',
        'cone' : '옥수수', 'abalone' : '전복', 'trueoutside' : '참외', 'chungkyoungchae' : '청경채', 
        'paprika(green)' : '파프리카(초록)', 'chicory' : '치커리', 'beannamul' : '콩나물', 'kiwi' : '키위', 
        'tomato' : '토마토', 'pineapple' : '파인애플', 'pumpkin' : '호박', 'background' : UNDEFMSG , UNDEFMSG : UNDEFMSG
}
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
    elif title == 'URL':
        URL = str(token[1])
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

def find_item_name(item):
    global itemKor
    return itemKor[item]
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
                log(message=find_item_name(tag1),filepath=LOGSRC)
                phase=21
            elif (x>14 and x<266) and (y>130 and y<186):
                log(message=find_item_name(tag2),filepath=LOGSRC)
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
            if phase==1:
                label_to_board(item_num=1,item=Result1_IMG,label1=cv2.imread("./fruitlabels/"+tag1+".png",1))
                log(message=find_item_name(tag1),filepath=LOGSRC)
            elif phase==2:## 두개있을때
                label_to_board(item_num=2,item=Result1_IMG,label1=cv2.imread("./fruitlabels/"+tag1+".png",1), label2=cv2.imread("./fruitlabels/"+tag2+".png",1))
            isWrite=True
            cv2.imshow(BOARD_NAME,Result1_IMG)
        if phase==21:
            label_to_board(item_num=1,item=Result2_IMG,label1=cv2.imread("./fruitlabels/"+tag1+".png",1))
            cv2.imshow(BOARD_NAME,Result2_IMG)
            res = requests.post('https://10.28.100.11:5564/infer_feedback',
                    json={  "feedback" : tag1,
                            "infer_no":infer_no,
                            "key":CRUDENTIAL_KEY,
                            }, verify=False)
            print(res.json()['result'])
            phase=3
        if phase==22:
            label_to_board(item_num=1,item=Result2_IMG,label1=cv2.imread("./fruitlabels/"+tag2+".png",1))
            cv2.imshow(BOARD_NAME,Result2_IMG)
            res = requests.post('https://10.28.100.11:5564/infer_feedback',
                    json={  "feedback" : tag2,
                            "infer_no":infer_no,
                            "key":CRUDENTIAL_KEY,
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
                testframe=cv2.resize(testframe[y: y + h, x: x + w],IMGSIZE)
            try:
                testframe=frame.copy()
                encoded_byte = base64.b64encode(testframe)   
                imgstr=encoded_byte.decode(encoding)
                res = requests.post('https://10.28.100.11:5564/run',
                                    json={  "image" : imgstr,
                                            "x_size":IMGSIZE[0],
                                            "y_size":IMGSIZE[1],
                                            "channel":3,
                                            "key":CRUDENTIAL_KEY,
                                            "auth":"code",
                                            "ID":"None",
                                            "PW":"None",
                                            }, verify=False)
                if res.json()['result']=="ok":
                    cls_list=res.json()['cls_list']
                    infer_no=res.json()['infer_no']
                else:
                    print("Server POST : "+res.json()['result'])
            except Exception as e:
                print("ERROR : ",end="")
                print(e)
            if len(cls_list)==1:
                tag1=cls_list[0]
                phase=1
            elif len(cls_list)==2:
                tag1=cls_list[0]
                tag2=cls_list[1]
                phase=2
            else:
                print("Error : The server is not responding.")
                phase=0
            btclk=False
        if key & 0xFF == ord('q'):
            break
phase=-1
print("exit")
capture.release()
cv2.destroyAllWindows()





