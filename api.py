from flask import Flask, request, jsonify, render_template, send_from_directory, json
from flask_cors import CORS
import numpy as np
import cv2
import db_connector
import ssl


from keras.models import load_model
from keras.applications.inception_v3 import preprocess_input
from keras.preprocessing import image
import os
from datetime import datetime

import sys
import base64
import time


encoding = sys.getdefaultencoding()

os.environ["CUDA_DEVICE_ORDER"]="PCI_BUS_ID"   
os.environ["CUDA_VISIBLE_DEVICES"]="1" 


##########################################################################################
############################## 나중에 DB에서 가져와야 될 부분###############################
##########################################################################################

query = "SELECT model_no FROM model where model_nm='ensemble'"
dbConn = db_connector.DbConn()
model_no=dbConn.select(query=query)

query = f'SELECT * FROM ensemble_model where model_no={model_no[0][0]}'
ensemble_list=dbConn.select(query=query)

modelnum=len(ensemble_list)
modellist=[]

for i in ensemble_list:
    modellist.append(load_model(i[4]))

HUDDLE1=0.8
HUDDLE2=0.5

UNDEFMSG="Undefined"
undeflist=["background"]

## 현재는 이렇게 받아오는데 나중에는 요청 들어올때마다 받아와야하나? 아님 미리 메모리에 올려야되나?
query = "SELECT * FROM str_label"
dbConn = db_connector.DbConn()
dbConn.select(query=query)  
items_label=dbConn.select(query=query)
label={}
label_rev={}
for i in items_label:
    if i[0]==0:
        label[str(i[1])]=i[2]
        label_rev[i[2]]=str(i[1])

##########################################################################################
##########################################################################################
##########################################################################################

    
def FindTopN(predict, N):
    TopN={}
    for j in range(len(predict)):
        if len(TopN)<N:
            TopN[label[str(j)]]=round(100*predict[j],2)
        else:
            if round(100*predict[j],2)>min(TopN.values()):
                del(TopN[min(TopN, key=TopN.get)])
                TopN[label[str(j)]]=round(100*predict[j],2)
    TopN=dict(sorted(TopN.items(), key=lambda x: x[1], reverse=True))
    return TopN
def now():
    now = datetime.now()
    string = str(now).replace(":", "-")
    return string[0:10]+"_"+string[11:22]

def current_milli_time():
    return round(time.time() * 1000)

app = Flask(__name__, template_folder='web')
CORS(app, support_credentials=True)

FLUTTER_WEB_APP = 'web'


@app.route('/web/')
def render_page_web():
    return render_template('index.html')


@app.route('/web/<path:name>')
def return_flutter_doc(name):

    datalist = str(name).split('/')
    DIR_NAME = FLUTTER_WEB_APP

    if len(datalist) > 1:
        for i in range(0, len(datalist) - 1):
            DIR_NAME += '/' + datalist[i]

    return send_from_directory(DIR_NAME, datalist[-1])


@app.route('/run', methods=['POST'])
def run():

    timecheck=current_milli_time()
    
    #json에서 data 받아오기
    encoded_img=request.json['image']
    x_size=request.json['x_size']
    y_size=request.json['y_size']
    img_channel=request.json['channel']
    auth_key=request.json['key']
    auth=request.json['auth'] # code or id
    userID=request.json['ID']
    userPW=request.json['PW']

    query = "SELECT * FROM auth"
    dbConn = db_connector.DbConn()
    auth_dict_list=dbConn.select(query=query) 
    isauth=False
    if auth=="code":
        for i in auth_dict_list:
            if i['auth_cd']==auth_key and i['act_yn'] =="Y":
                isauth=True
                break
    #elif auth=="id"
    #   id/pw 매칭
    if isauth==False: ## 인증키 없으면
        return jsonify({'result': 'not permission', 'cls_list': None, 'infer_no' :None})
    # 파일명 생성 및 이미지 저장
    filename=now()+'.jpg'
    save_file_path = './request_image/'+filename
    while os.path.isfile(save_file_path):
        filename= filename.split(".jpg")[0]+"(1).jpg"
        save_file_path = './request_image/'+filename
    print(save_file_path)

    # string to bytes
    string_to_bytes = encoded_img.encode(encoding)
    bytes_to_numpy = base64.decodebytes(string_to_bytes)
    data = np.frombuffer(bytes_to_numpy, dtype='uint8').reshape((y_size, x_size, img_channel))
    cv2.imwrite(save_file_path,data)
    
    query = "INSERT INTO img_data(date,time,resol_x,resol_y,file_path)"
    query += f" VALUES(NOW() ,NOW() , {x_size} , {y_size}, '{save_file_path[1:]}' ) RETURNING image_no"
    dbConn = db_connector.DbConn()
    dbConn.insert(query=query)        
    img_no=dbConn.lastpick()
    ## 이미지전처리
    data_resize=cv2.resize(data,(299,299))
    predict_img = cv2.cvtColor(data_resize,cv2.COLOR_BGR2RGB)  
    x = image.image_utils.img_to_array(predict_img)
    x = np.expand_dims(x, axis = 0)     ## efficientnet일 경우
    ## preprocessing 없는 모델은 여기서 추론
    m4=modellist[3].predict(x,verbose = 0)[0]
    ## preprocessing 필요하면 여기서 추론
    x = preprocess_input(x)
    m1=modellist[0].predict(x,verbose = 0)[0]   
    m2=modellist[1].predict(x,verbose = 0)[0]   
    m3=modellist[2].predict(x,verbose = 0)[0]   
    features=sum(modellist)
    predicted_list=features
    predicted_class=[]
    predicted_set = { 
                        label[str(np.argmax(m1))],
                        label[str(np.argmax(m2))],
                        label[str(np.argmax(m3))],
                        label[str(np.argmax(m4))]
                        }
    top2=FindTopN(predicted_list,2)
    predicted_class=list(top2.keys())
    

    # ind_prob=[]
    # ind_prob.append(FindTopN(m1,2))
    # ind_prob.append(FindTopN(m2,2))
    # ind_prob.append(FindTopN(m3,2))
    # ind_prob.append(FindTopN(m4,2))

    cls_list = [] #마지막에 request로 전송할 결과값
    if predicted_class[0] in undeflist: ##1순위가 undef thing일때
        cls_list.append(predicted_class[0])
        phase=0
    elif max(predicted_list)>HUDDLE1*modelnum: ##1개만 출력
        cls_list.append(predicted_class[0])
        phase=1
    elif len(predicted_set)==modelnum: #undef출력
        cls_list.append(UNDEFMSG)
        phase=0
    elif max(max(m1),max(m2),max(m3),max(m4)) < HUDDLE2: #undef출력
        cls_list.append(UNDEFMSG)
        phase=0
    elif max(predicted_list)>HUDDLE2*2 :##2개합쳐서 2(*4)넘을때도하자
        cls_list.append(predicted_class[0]) 
        if predicted_class[1] in undeflist: # 1개
            phase=1
        else:
            cls_list.append(predicted_class[1]) #2개
            phase=2
    else:
        cls_list.append(UNDEFMSG)  
        phase=0
    ## 영어이름으로줌
    timecheck=current_milli_time()-timecheck

    if phase==0: #undefined
        query = "INSERT INTO infer_history(date, str_no, model_no, image_no, result1, result2, infer_speed, time, feedback)"
        query += f" VALUES(NOW() ,{0} , {0} , {img_no} , {-1}, NULL , {timecheck} ,NOW(), NULL) RETURNING infer_no"
        dbConn.insert(query=query)
    elif phase==1: #1 items infer
        query = "INSERT INTO infer_history(date, str_no, model_no, image_no, result1, result2, infer_speed, time, feedback)"
        query += f" VALUES(NOW() ,{0} , {0} , {img_no} , {int(label_rev[cls_list[0]])}, NULL , {timecheck} ,NOW(), NULL) RETURNING infer_no"
        dbConn.insert(query=query)
    elif phase==2: #2 items infer
        query = "INSERT INTO infer_history(date, str_no, model_no, image_no, result1, result2, infer_speed, time, feedback)"
        query += f" VALUES(NOW() ,{0} , {0} , {img_no} , {int(label_rev[cls_list[0]])}, {int(label_rev[cls_list[1]])} , {timecheck} ,NOW(), NULL) RETURNING infer_no"
        dbConn.insert(query=query)
    else: # error
        query = "INSERT INTO infer_history(date, str_no, model_no, image_no, result1, result2, infer_speed, time, feedback)"
        query += f" VALUES(NOW() ,{0} , {0} , {img_no} , NULL, NULL , {timecheck} ,NOW(), NULL) RETURNING infer_no"
        dbConn.insert(query=query)

    infer_no=dbConn.lastpick(id=0)

    # for i in ind_prob:
    #     m1top2[list(m1top2)[i]]
    #     query = "INSERT INTO ensemble_infer_history(infer_no, image_no, result1,result2,result1_prob,result2_prob,ensemble_model_no)"
    #     query += f" VALUES({infer_no},{img_no},{list(m1top2)[i]},{},{},{},{model_no[0][0]}) RETURNING infer_no"
    #     dbConn.insert(query=query)

    
    return jsonify({'result': 'ok', 'cls_list': cls_list, 'infer_no' :infer_no }) #feedback을 위해서 infer_no도 반환

@app.route('/infer_feedback', methods=['POST'])
def infer_feedback():
    query = "SELECT * FROM auth"
    dbConn = db_connector.DbConn()
    auth_dict_list=dbConn.select(query=query) 

    res = request.get_json()
    auth_key=res['key']
    isauth=False
    for i in auth_dict_list:
        if i['auth_cd']==auth_key and i['act_yn'] =="Y":
            isauth=True
            break
    if isauth:
        feedback=res['feedback']
        infer_no=res['infer_no']
        feeback_labelnum=int(label_rev[feedback])
        dbConn = db_connector.DbConn()
        query = f"UPDATE infer_history SET feedback = {feeback_labelnum} WHERE infer_no = {infer_no}"
        dbConn.insert(query=query)    
        return jsonify({'result': 'ok thanksyou for feedback' })
    else:
        return jsonify({'result': 'key is unvalid' })

@app.route('/get_model', methods=['GET', 'POST'])
def get_model():
    # GET 파라메터 받아와서 dict로 변환
    param_dict = request.args.to_dict()

    # 기본 모델 조회 쿼리(조건 언제나 TRUE)
    query = "SELECT * FROM model WHERE 1=1 "

    # 파라메터에 act_yn이 있으면 조건 추가
    cond = ''
    if 'act_yn' in param_dict:
        cond = f"AND act_yn = '{param_dict['act_yn']}'"
    query += cond

    # DB 객체 생성
    dbConn = db_connector.DbConn()
    # 쿼리 실행
    result = dbConn.select(query)

    # 결과 반환
    return jsonify({'result': 'ok', 'value': result})

@app.route('/auth', methods=('GET', 'POST'))
def login():

    param_dict = request.args.to_dict()

    query = "SELECT * FROM auth WHERE 1=1 "

    cond = ''
    if 'act_yn' in param_dict:
        cond = f"AND act_yn = '{param_dict['act_yn']}'"
    query += cond

    if 'auth_cd' in param_dict:
        cond = f"AND auth_cd = '{param_dict['auth_cd']}'"
    query += cond

    dbConn = db_connector.DbConn()

    auth_data = dbConn.select(query=query)

    auth_lst = []

    for data in auth_data:
        auth_dict = dict(zip(['auth_cd', 'act_yn', 'auth_no'],data))
        auth_lst.append(auth_dict)

        for dicta in auth_lst:
            if dicta['auth_cd'] == param_dict['auth_cd']:
                dicta['act_yn'] = 'Y'
                dicta['auth_result'] = 'ok'
            else:
                dicta['auth_yn'] = 'N'
                dicta['auth_result'] = 'fail'
    
    if len(auth_lst) > 0:
        auth_result = 'ok'
    else:
        auth_result = 'fail'

    return jsonify({'result': auth_lst, 'authorization_result' : auth_result})


@app.route('/log', methods=['GET', 'POST'])
def log():
    param_dict = request.args.to_dict()
    print(param_dict['test'])
    return jsonify({'result': 'ok'})


@app.route('/test', methods=['POST'])
def test():
    param_dict = request.form.get('val1')
    print(param_dict)

    # 기본 모델 조회 쿼리(조건 언제나 TRUE)
    query = "SELECT * FROM model WHERE 1=1 "

    # DB 객체 생성
    dbConn = db_connector.DbConn()
    # 쿼리 실행
    result = dbConn.selectAsDict(query)

    print(result)

    return jsonify({'result': 'ok'})


if __name__ == "__main__":
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS)
    ssl_context.load_cert_chain(certfile='server.crt', keyfile='server.key', password='1234')
    app.run(host='0.0.0.0', port=5564, ssl_context=ssl_context, debug=False)
