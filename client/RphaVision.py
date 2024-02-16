

# -*- coding: utf-8 -*-
# <snippet_imports>
import cv2
import threading
import requests
import base64
import sys
import time
encoding = sys.getdefaultencoding()

URL = 'https://211.58.242.46:8091'
INFER_URL = URL + '/run'
FEEDBACK_URL = URL + '/infer_feedback'
INIT_URL = URL + '/client_init'
EXIT_URL = URL + '/exit'
CRUDENTIAL_KEY="hanwhatest"

print("Program Starting")
###
LOGSRC="./cameradata.txt"
LOADIMGSRC="./searching.jpg"
UNDEFMSG="Undefined"
CAM_MOVE_X=1300
CAM_MOVE_Y=28
CAMSIZE=(280,210)
DEVICENUM=0 
CAM_NAME="Camera"
BOARD_NAME="Board"
RTSP=""
DELAYSECOND = 0.1
searching=cv2.imread(LOADIMGSRC,1)
btclk=False
phase=0
camerastate=0
yy=150
hh=260
xx=150
ww=490

try:
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
            INFER_URL = URL + '/run'
            FEEDBACK_URL = URL + '/infer_feedback'
            INIT_URL = URL + '/client_init'
            EXIT_URL = URL + '/exit'
        elif title == 'DELAY':
            DELAYSECOND = float(token[1])
        elif title == 'CAM_MOVE_X':
            CAM_MOVE_X = int(token[1])
        elif title == 'CAM_MOVE_Y':
            CAM_MOVE_Y = int(token[1])
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
        elif title == 'RTSP_X':
            xx = int(token[1])
        elif title == 'RTSP_Y':
            yy = int(token[1])
        elif title == 'RTSP_W':
            ww = int(token[1])
        elif title == 'RTSP_H':
            hh = int(token[1])
        elif title == 'CAMSIZE':
            CAMSIZE = ( int(str(token[1]).replace("(","").replace(")","").split(",")[0]),
                        int(str(token[1]).replace("(","").replace(")","").split(",")[1]))
except:
    print("Set Default Options. If you want to change options, write them in the [config.txt] file.")

res = requests.post(INIT_URL,
        json={  "key": CRUDENTIAL_KEY
                }, verify=False) ## 나중에 ID 랑 PW 도 보내야됨(NONE으로)
result=res.json()['str_label_list']
item_Eng={}
item_Kor={}
for i in result:
    item_Eng[i[0]]=str(i[1]).split("_")[0]
    item_Kor[i[0]]=str(i[2]).split("_")[0]

item_Kor[-1]=UNDEFMSG
item_Eng[-1]=UNDEFMSG
cls_list=[]
print(str(len(item_Kor))+" items are loaded.")
LABELSIZE=(int(253*CAMSIZE[0]/280),int(57*CAMSIZE[1]/210))

print("Function Loading")
def label_to_board(item_num,item,label1,label2=None,label3=None):
    if item_num==1:
        label1 = cv2.resize(label1, LABELSIZE)
        for i in range(0,LABELSIZE[1]-1):
            for j in range(0,LABELSIZE[0]-1):
                item[int(CAMSIZE[1]*13/21)+i][int((CAMSIZE[0]-LABELSIZE[0]+1)/2)+j]=label1[i][j]
        return item
    elif item_num==2:
        label1 = cv2.resize(label1, LABELSIZE)
        label2 = cv2.resize(label2, LABELSIZE)
        for i in range(0,LABELSIZE[1]-1):
            for j in range(0,LABELSIZE[0]-1):
                item[int(CAMSIZE[1]/3)+i][int((CAMSIZE[0]-LABELSIZE[0]+1)/2)+j]=label1[i][j]
        for i in range(0,LABELSIZE[1]-1):
            for j in range(0,LABELSIZE[0]-1):
                item[int(CAMSIZE[1]*13/21)+i][int((CAMSIZE[0]-LABELSIZE[0]+1)/2)+j]=label2[i][j]
    else :
        label1 = cv2.resize(label1, LABELSIZE)
        label2 = cv2.resize(label2, LABELSIZE)
        label3 = cv2.resize(label3, LABELSIZE)
        for i in range(0,LABELSIZE[1]-1):
            for j in range(0,LABELSIZE[0]-1):
                item[int(CAMSIZE[1]/21)+i][int((CAMSIZE[0]-LABELSIZE[0]+1)/2)+j]=label1[i][j]
        for i in range(0,LABELSIZE[1]-1):
            for j in range(0,LABELSIZE[0]-1):
                item[int(CAMSIZE[1]/3)+i][int((CAMSIZE[0]-LABELSIZE[0]+1)/2)+j]=label2[i][j]
        for i in range(0,LABELSIZE[1]-1):
            for j in range(0,LABELSIZE[0]-1):
                item[int(CAMSIZE[1]*13/21)+i][int((CAMSIZE[0]-LABELSIZE[0]+1)/2)+j]=label3[i][j]

def btctrl(event, x, y, flags, param):
   global btclk
   global phase
   global cls_list
   if phase==1: ## 1개
       if event==cv2.EVENT_LBUTTONDOWN:
            if (x>int((CAMSIZE[0]-LABELSIZE[0]+1)/2) and x<int((CAMSIZE[0]+LABELSIZE[0]+1)/2)) and (y>int(CAMSIZE[1]/3) and y<int((CAMSIZE[1]/3)+LABELSIZE[1])):
                log(message=item_Kor[cls_list[0]],filepath=LOGSRC)
                phase=11
   elif phase==2: ##2개
       if event==cv2.EVENT_LBUTTONDOWN:
            if (x>int((CAMSIZE[0]-LABELSIZE[0]+1)/2) and x<int((CAMSIZE[0]+LABELSIZE[0]+1)/2)) and (y>int(CAMSIZE[1]/21) and y<int((CAMSIZE[1]/21)+LABELSIZE[1])):
                log(message=item_Kor[cls_list[0]],filepath=LOGSRC)
                phase=21
            elif (x>int((CAMSIZE[0]-LABELSIZE[0]+1)/2) and x<int((CAMSIZE[0]+LABELSIZE[0]+1)/2)) and (y>int(CAMSIZE[1]/3) and y<int((CAMSIZE[1]/3)+LABELSIZE[1])):
                log(message=item_Kor[cls_list[1]],filepath=LOGSRC)
                phase=22
   elif phase == 3 :
       if event==cv2.EVENT_LBUTTONDOWN:
           btclk=switching(btclk)
   elif phase == 0 :
    if event == cv2.EVENT_LBUTTONDOWN:
        if (x>int((CAMSIZE[0]-LABELSIZE[0]+1)/2) and x<int((CAMSIZE[0]+LABELSIZE[0]+1)/2)) and (y>int(CAMSIZE[1]*13/21) and y<int((CAMSIZE[1]*13/21)+LABELSIZE[1])):
            btclk=switching(btclk)
    
def log(message,filepath,wtype="w"):
    file = open(filepath, wtype)
    file.write(message)
    file.close()
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
frame = None

### camera threading
### threading
def camera():
    global phase
    global cls_list
    global btclk
    btclk=True
    isCapt=True
    isWrite=False
    time.sleep(2)
    print("API INIT")
    cv2.namedWindow(BOARD_NAME, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(BOARD_NAME, cv2.WND_PROP_FULLSCREEN, 1)
    cv2.setWindowProperty(BOARD_NAME, cv2.WND_PROP_TOPMOST, 1)
    cv2.resizeWindow(BOARD_NAME, CAMSIZE[0],CAMSIZE[1])
    cv2.moveWindow(BOARD_NAME, CAM_MOVE_X,CAM_MOVE_Y)
    cv2.setMouseCallback(BOARD_NAME,btctrl)
    while(True):
        time.sleep(DELAYSECOND)
        if ret != True:  # read에 실패하면 loop탈출
            break
        if (isCapt==True and isWrite==False):
            print("INFER RECEPTION")
            Result1_IMG=frame.copy()
            Result2_IMG=frame.copy()
            if len(cls_list)==1: ## 1개있을때
                phase=1
                if item_Eng[cls_list[0]]=="Undefined":
                    label_to_board(item_num=2,item=Result1_IMG,label1=cv2.imread("./fruitlabels/"+item_Eng[cls_list[0]]+".png",1),label2=cv2.imread("./fruitlabels/retry.png",1))
                    phase=0
                else:
                    label_to_board(item_num=2,item=Result1_IMG,label1=cv2.imread("./fruitlabels/"+item_Eng[cls_list[0]]+".png",1),label2=cv2.imread("./fruitlabels/etc.png",1))
                log(message=item_Kor[cls_list[0]],filepath=LOGSRC)
            elif len(cls_list)==2:## 2개있을때
                phase=2
                label_to_board(item_num=3,item=Result1_IMG,label1=cv2.imread("./fruitlabels/"+item_Eng[cls_list[0]]+".png",1), label2=cv2.imread("./fruitlabels/"+item_Eng[cls_list[1]]+".png",1),label3=cv2.imread("./fruitlabels/etc.png",1))
            isWrite=True
            cv2.imshow(BOARD_NAME,Result1_IMG)
        if phase==11:
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
            try:
                # 전송할 이미지 현재 frame에서 copy
                req_img=frame_origin.copy()
                if camerastate==-1:
                    req_img=req_img[yy: yy + hh, xx: xx + ww].copy()
                # img to str
                encoded_byte = base64.b64encode(req_img)   
                imgstr=encoded_byte.decode(encoding)
                # request
                res = requests.post(INFER_URL,
                                    json={  "image" : imgstr,
                                            "x_size":req_img.shape[1],
                                            "y_size":req_img.shape[0],
                                            "key":CRUDENTIAL_KEY,
                                            "auth":"code",
                                            "ID":"None",
                                            "PW":"None",
                                            "send_device" : "client"},
                                            verify=False)
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
            phase=-1
            break
t=threading.Thread(target=camera)
t.daemon=True
t.start()
###
###
###
cv2.namedWindow(CAM_NAME, cv2.WINDOW_NORMAL)
cv2.setWindowProperty(CAM_NAME, cv2.WND_PROP_FULLSCREEN, 1)
cv2.setWindowProperty(CAM_NAME, cv2.WND_PROP_TOPMOST, 1)
cv2.resizeWindow(CAM_NAME, CAMSIZE[0],CAMSIZE[1])
cv2.moveWindow(CAM_NAME, CAM_MOVE_X+CAMSIZE[0],CAM_MOVE_Y)

while phase!=-1:
    ret, frame_origin = capture.read()
    frame = cv2.resize(frame_origin, CAMSIZE)
    CAM_frame=frame.copy()
    cv2.putText(CAM_frame,"CAM", (0, 30),cv2.FONT_HERSHEY_DUPLEX, 1, (0,0,0), 1, cv2.LINE_AA)
    cv2.imshow(CAM_NAME,CAM_frame)
    key = cv2.waitKey(1)
    if key & 0xFF == ord('q'):
        break 
ret=False
print("exit")
capture.release()
res=requests.post(EXIT_URL,
                    json={  "key":CRUDENTIAL_KEY,
                            }, verify=False)
print(res.json()['result'])
cv2.destroyAllWindows()





