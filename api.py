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
model_no=dbConn.select(query=query)[0][0]

query = f'SELECT model_path FROM ensemble_model where model_no={model_no}'
ensemble_list=dbConn.select(query=query)
del(dbConn)
modelnum=len(ensemble_list)
modellist=[]
model_pre=[]
for path in ensemble_list:
    modellist.append(load_model(path[0]))
    if path[0] in "effi":
        model_pre.append(1)
    else:
        model_pre.append(0)
HUDDLE1=0.8
HUDDLE2=0.7

##########################################################################################
##########################################################################################

def authorize(auth_key):
    query = f"SELECT * FROM auth where auth_cd = '{auth_key}' and act_yn='Y'"
    dbConn = db_connector.DbConn()
    result=dbConn.select(query=query)
    del(dbConn)
    return False if len(result)==0 else True


def now():
    now = datetime.now()
    string = str(now).replace(":", "-")
    return string[0:10]+"_"+string[11:22]
def current_milli_time():
    return round(time.time() * 1000)
def sort_predict(predict):
    """
    predict의 index와 값을 tuple로 하는 list를
    내림차순으로 정렬한 값을 반환하는 함수입니다.

    predict(list) : infer한 list
    return : [(seq , prob), ...]
    """
    predict_dict={}
    for i in range(len(predict)):
        predict_dict[i]=predict[i]
    predict_dict=(sorted(predict_dict.items(), key=lambda x: x[1], reverse=True))
    return predict_dict


app = Flask(__name__, template_folder='web')
CORS(app, support_credentials=True)

FLUTTER_WEB_APP = 'web'

@app.route('/initialize', methods=['POST'])
def initialize():
    res=request.get_json()
    auth_key = res['key']
    store_no = res['store_no']
    auth =     res['auth'] # code or id (나중에 ID랑 PW도 받아야됨)
    if auth=="code":
        isauth=authorize(auth_key)
    #elif auth=="id"
    #   id/pw 매칭
    if isauth==False: ## 인증키 없으면
        return jsonify({'result': 'Fail'})

    # 전달받은 store_no로 사용하고 있는 model_no 찾기
    query = f"SELECT model_no, act_yn from model where str_no={store_no} and use_yn= 'Y'"
    dbConn = db_connector.DbConn()

    model_no = dbConn.select(query=query)[0][0]   ##model_no
    model_state= dbConn.select(query=query)[0][1] ##act_yn

    if model_state == "N":
        return jsonify({'result': 'Fail'})

    query = "SELECT model_label.label_no, item_label.label_nm_eng, item_label.label_nm_kor, item_cd FROM" # 라벨 / 영어 / 한글 / 아이템코드 전달(해당모델)
    query+= f" model_label LEFT JOIN item_label ON model_label.label_no = item_label.label_no where model_label.model_no={model_no}" #modelnum

    str_label_list=dbConn.select(query=query)
    str_label_list.append([-1, 'Undefined', 'Undefined','None'])
    del(dbConn)

    return jsonify({'result': 'ok', 'str_label_list': str_label_list}) #feedback을 위해서 infer_no도 반환

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

@app.route('/login', methods=['POST'])
def login():

    # Flutter에서 해당 url로 email과 password를 post한 내용을 받아오는 코드

        # request 방식 확인 코드

    id = str(request.form.get('id'))
    pwd = request.form.get('password')
    params = [id, pwd]
    print(params)
    param_dict = dict(zip(['id', 'password'], params))

    # DB에서 api 형태로 query 정보를 받아오는 코드

    query = f"SELECT * FROM login WHERE id = '{id}';"
    dbConn = db_connector.DbConn()
    login_data = dbConn.select(query=query)
    login_dict = None
    if len(login_data) > 0:
        login_dict = dict(zip(['id', 'password', 'login_no', 'act_yn', 'str_no'],login_data[0]))
        print(login_dict)
        id_s = 1
    else:
        id_s = 0


    # Flutter에서 받아온 정보를 DB에서 받아온 정보와 비교하여 POST할 dict를 작성하는 코드

    # flutter에 전송할 dictionary
    # 형태는 {act_yn, login_no, str_no, log_in_state, log_in_text}
    '''
        act_yn = 'Y' / 'N'
        login_no = 해당 로그인 정보
        str_no = 매장 정보
        log_in_st = 0 : 로그인 성공 + 인증 Y, 1 : 로그인 성공 + 인증 N, 2 : ID 오류, 3 : PW 오류(ID는 맞으나 PW 틀림)
        log_in_text = 0 : '로그인 및 인증을 모두 성공했습니다.' , 1 : '인증이 되지 않은 로그인 정보입니다.', 2 : 'ID가 틀렸습니다.', 3 : 'PW가 틀렸습니다.' 
    '''
    dict_result = {}
    dict_text = {0 : '로그인 및 인증을 모두 성공했습니다.', 1 : '인증이 되지 않은 로그인 정보입니다.', 2 : 'ID가 틀렸습니다.', 3 : 'PW가 틀렸습니다.', 4 : '인증 오류 발생'}
    log_in_st = 4

    if id_s == 1:
        dict_result['log_in_st'] = log_in_st
        dict_result['str_no'] = login_dict['str_no']
        dict_result['login_no'] = login_dict['login_no']
        if login_dict['password'] == param_dict['password']:
            if login_dict['act_yn'] == 'Y':
                dict_result['act_yn'] = login_dict['act_yn']
                log_in_st = 0
                dict_result['log_in_st'] = log_in_st

            else:
                dict_result['act_yn'] = login_dict['act_yn']
                log_in_st = 1
                dict_result['log_in_st'] = log_in_st

        else:
            log_in_st = 3
            dict_result['log_in_st'] = log_in_st

    else:
        log_in_st = 2
        dict_result['log_in_st'] = log_in_st

    dict_result['log_in_text'] = dict_text[log_in_st]

    print(dict_result)

    # 비교 후 작성된 dict 내용을 json 혹은 ajax 형태로 flutter에 전송하기 위한 코드

    # res = requests.post("https://192.168.0.108:2092/login", data = json.dumps(dict_result), verify = False)
    return jsonify(dict_result)

@app.route('/run', methods=['POST'])
def run():
    timecheck=current_milli_time()
    res=request.get_json()
    #json에서 data 받아오기
    encoded_img = res['image']
    x_size      = res['x_size']
    y_size      = res['y_size']
    img_channel = res['channel']
    userID      = res['ID']
    userPW      = res['PW']
    auth_key    = res['key']
    str_no      = res['store_no']
    send_device = res['send_device']
    auth        = res['auth'] # code or id
    if auth == "code":
        isauth=authorize(auth_key)
    #elif auth=="id"
    #   id/pw 매칭
    if isauth == False: ## 인증키 없으면
        return jsonify({'result': 'Fail'})

    # 파일명 생성 및 이미지 저장
    filename=now()+'.jpg'
    save_file_path = './request_image/'+filename
    while os.path.isfile(save_file_path):
        filename= filename.split(".jpg")[0]+"(1).jpg"
        save_file_path = './request_image/'+filename
    print(save_file_path)

    # string to bytes & write
    string_to_bytes = encoded_img.encode(encoding)
    bytes_to_numpy = base64.decodebytes(string_to_bytes)
    if send_device=="android" or send_device=="web":
        list_bytes = []
        bytes_to_numpy = bytes_to_numpy.split(b'[')[1].split(b']')[0].split(b', ')
        for item in bytes_to_numpy:
            list_bytes.append(int(item))
        data = cv2.cvtColor(np.array(list_bytes, dtype=np.uint8).reshape((int(y_size), int(x_size), -1))[:, :, :3],cv2.COLOR_RGB2BGR)
    else:
        data = np.frombuffer(bytes_to_numpy, dtype=np.uint8).reshape((y_size, x_size, img_channel))
    cv2.imwrite(save_file_path, data)

    # insert image data into db
    query = "INSERT INTO img_data(date,time,resol_x,resol_y,file_path)"
    query += f" VALUES(NOW() ,NOW() , {x_size} , {y_size}, '{save_file_path[1:]}' ) RETURNING image_no"
    dbConn = db_connector.DbConn()
    dbConn.insert(query=query)
    img_no=dbConn.lastpick() # pick image no


    ## img resize
    data_resize=cv2.resize(data,(299,299))
    predict_img = cv2.cvtColor(data_resize,cv2.COLOR_BGR2RGB)
    x = image.image_utils.img_to_array(predict_img)
    x = np.expand_dims(x, axis = 0)     ## efficientnet일 경우 preprocessing 필요 x
    ## preprocessing 없는 모델은 여기서 추론
    m4=modellist[3].predict(x,verbose = 0)[0]
    ## preprocessing 필요하면 여기서 추론
    x = preprocess_input(x)
    m1=modellist[0].predict(x,verbose = 0)[0]
    m2=modellist[1].predict(x,verbose = 0)[0]
    m3=modellist[2].predict(x,verbose = 0)[0]

    features=m1+m2+m3+m4 # 4개의 softmax값을 다 더한것
    predicted_list=sort_predict(features) # 내림차순으로 정렬
    max_predicted_set = {
                        np.argmax(m1),
                        np.argmax(m2),
                        np.argmax(m3),
                        np.argmax(m4)
                        } #각 모델들의 1순위들 index (seq)

    cls_list = [] #마지막에 request로 전송할 결과값 (label)
    # undeflist 받아오기 (seq로)
    query = "SELECT model_label.label_seq FROM model_label LEFT JOIN item_label ON model_label.label_no = item_label.label_no WHERE item_label.valid_yn = 'N'"
    undeflist = [data for inner_list in dbConn.select(query=query) for data in inner_list]

    if predicted_list[0][0] in undeflist: ##1순위가 undef thing일때 (얘는 undefthing label number를 반환)
        seq=predicted_list[0][0]
        query = f"SELECT model_label.label_no FROM model_label LEFT JOIN item_label ON model_label.label_no = item_label.label_no WHERE label_seq= {seq} and model_no = 0"
        result=dbConn.execute(query=query)[0][0]         
        cls_list.append(result)
        phase=1
    elif predicted_list[0][1]>HUDDLE1*modelnum: ##1개만 출력
        seq=predicted_list[0][0]
        query = f"SELECT model_label.label_no FROM model_label LEFT JOIN item_label ON model_label.label_no = item_label.label_no WHERE label_seq= {seq} and model_no = 0"
        result=dbConn.execute(query=query)[0][0]
        cls_list.append(result)
        phase=1
    elif len(max_predicted_set)==modelnum: #undef출력 : -1
        cls_list.append(-1)
        phase=0
    elif max(max(m1),max(m2),max(m3),max(m4)) < HUDDLE2: #undef출력 : -1
        cls_list.append(-1)
        phase=0
    elif (predicted_list[0][1]+predicted_list[1][1]) > HUDDLE2*modelnum :##2개합쳐서 huddle2*4넘을때도하자
        seq=predicted_list[0][0]
        query = f"SELECT model_label.label_no FROM model_label LEFT JOIN item_label ON model_label.label_no = item_label.label_no WHERE label_seq= {seq} and model_no = 0"
        result=dbConn.execute(query=query)[0][0]
        cls_list.append(result)
        if predicted_list[1][0] in undeflist: # 2순위가 undef일때
            phase=1
        else:
            seq=predicted_list[1][0]
            query = f"SELECT model_label.label_no FROM model_label LEFT JOIN item_label ON model_label.label_no = item_label.label_no WHERE label_seq= {seq} and model_no = 0"
            result=dbConn.execute(query=query)[0][0]
            cls_list.append(result)
            phase=2
    else:
        cls_list.append(-1)  
        phase=0
    ## 영어이름으로줌
    timecheck=current_milli_time()-timecheck
    #반환값이 seq인데 이걸 label_no로 변환해서 줘야한다.

    if phase==0: #undefined
        query = "INSERT INTO infer_history(date, str_no, model_no, image_no, result1, result2, infer_speed, time, feedback)"
        query += f" VALUES(NOW() ,{str_no} , {0} , {img_no} , {-1}, NULL , {timecheck} ,NOW(), NULL) RETURNING infer_no"
        dbConn.insert(query=query)
    elif phase==1: #1 items infer
        query = "INSERT INTO infer_history(date, str_no, model_no, image_no, result1, result2, infer_speed, time, feedback)"
        query += f" VALUES(NOW() ,{str_no} , {0} , {img_no} , {cls_list[0]}, NULL , {timecheck} ,NOW(), NULL) RETURNING infer_no"
        dbConn.insert(query=query)
    elif phase==2: #2 items infer
        query = "INSERT INTO infer_history(date, str_no, model_no, image_no, result1, result2, infer_speed, time, feedback)"
        query += f" VALUES(NOW() ,{str_no} , {0} , {img_no} , {cls_list[0]}, {cls_list[1]} , {timecheck} ,NOW(), NULL) RETURNING infer_no"
        dbConn.insert(query=query)
    else: # error
        query = "INSERT INTO infer_history(date, str_no, model_no, image_no, result1, result2, infer_speed, time, feedback)"
        query += f" VALUES(NOW() ,{str_no} , {0} , {img_no} , NULL, NULL , {timecheck} ,NOW(), NULL) RETURNING infer_no"
        dbConn.insert(query=query)

    infer_no=dbConn.lastpick(id=0)

    ## 앙상블 모델별 추론결과 저장
    sort_m1=sort_predict(m1)
    seq=sort_m1[0][0]
    query = f"SELECT model_label.label_no FROM model_label LEFT JOIN item_label ON model_label.label_no = item_label.label_no WHERE label_seq= {seq} and model_no = 0"
    m1_result1=dbConn.execute(query=query)[0][0]
    seq=sort_m1[1][0]
    query = f"SELECT model_label.label_no FROM model_label LEFT JOIN item_label ON model_label.label_no = item_label.label_no WHERE label_seq= {seq} and model_no = 0"
    m1_result2=dbConn.execute(query=query)[0][0]
    # prob 1,2 (점수)
    m1_prob1=sort_m1[0][1]
    m1_prob2=sort_m1[1][1]
    query = "INSERT INTO ensemble_infer_history(infer_no, image_no, result1, result2, result1_prob, result2_prob,ensemble_model_no)"
    query += f" VALUES({infer_no} ,{img_no},{m1_result1},{m1_result2},{m1_prob1},{m1_prob2},{1} ) "
    dbConn.insert(query=query)

    sort_m2=sort_predict(m2)
    seq=sort_m2[0][0]
    query = f"SELECT model_label.label_no FROM model_label LEFT JOIN item_label ON model_label.label_no = item_label.label_no WHERE label_seq= {seq} and model_no = 0"
    m2_result1=dbConn.execute(query=query)[0][0]
    seq=sort_m2[1][0]
    query = f"SELECT model_label.label_no FROM model_label LEFT JOIN item_label ON model_label.label_no = item_label.label_no WHERE label_seq= {seq} and model_no = 0"
    m2_result2=dbConn.execute(query=query)[0][0]
    # prob 1,2 (점수)
    m2_prob1=sort_m2[0][1]
    m2_prob2=sort_m2[1][1]
    query = "INSERT INTO ensemble_infer_history(infer_no, image_no, result1, result2, result1_prob, result2_prob,ensemble_model_no)"
    query += f" VALUES({infer_no} ,{img_no},{m2_result1},{m2_result2},{m2_prob1},{m2_prob2},{2} ) "
    dbConn.insert(query=query)

    sort_m3=sort_predict(m3)
    seq=sort_m3[0][0]
    query = f"SELECT model_label.label_no FROM model_label LEFT JOIN item_label ON model_label.label_no = item_label.label_no WHERE label_seq= {seq} and model_no = 0"
    m3_result1=dbConn.execute(query=query)[0][0]
    seq=sort_m3[1][0]
    query = f"SELECT model_label.label_no FROM model_label LEFT JOIN item_label ON model_label.label_no = item_label.label_no WHERE label_seq= {seq} and model_no = 0"
    m3_result2=dbConn.execute(query=query)[0][0]
    # prob 1,2 (점수)
    m3_prob1=sort_m3[0][1]
    m3_prob2=sort_m3[1][1]
    query = "INSERT INTO ensemble_infer_history(infer_no, image_no, result1, result2, result1_prob, result2_prob,ensemble_model_no)"
    query += f" VALUES({infer_no} ,{img_no},{m3_result1},{m3_result2},{m3_prob1},{m3_prob2},{3} ) "
    dbConn.insert(query=query)

    sort_m4=sort_predict(m4)
    seq=sort_m4[0][0]
    query = f"SELECT model_label.label_no FROM model_label LEFT JOIN item_label ON model_label.label_no = item_label.label_no WHERE label_seq= {seq} and model_no = 0"
    m4_result1=dbConn.execute(query=query)[0][0]
    seq=sort_m4[1][0]
    query = f"SELECT model_label.label_no FROM model_label LEFT JOIN item_label ON model_label.label_no = item_label.label_no WHERE label_seq= {seq} and model_no = 0"
    m4_result2=dbConn.execute(query=query)[0][0]
    # prob 1,2 (점수)
    m4_prob1=sort_m4[0][1]
    m4_prob2=sort_m4[1][1]
    query = "INSERT INTO ensemble_infer_history(infer_no, image_no, result1, result2, result1_prob, result2_prob,ensemble_model_no)"
    query += f" VALUES({infer_no} ,{img_no},{m4_result1},{m4_result2},{m4_prob1},{m4_prob2},{4} ) "
    dbConn.insert(query=query)

    del(dbConn)
    return jsonify({'result': 'ok', 'cls_list': cls_list, 'infer_no' :infer_no }) #feedback을 위해서 infer_no도 반환

@app.route('/infer_feedback', methods=['POST'])
def infer_feedback():
    res = request.get_json()
    auth_key = res['key']
    auth =     res['auth'] # code or id
    if auth=="code":
        isauth=authorize(auth_key)
    #elif auth=="id"
    #   id/pw 매칭
    if isauth==False: ## 인증키 없으면
        return jsonify({'result': 'Fail'})
    feedback=res['feedback'] # client랑 소통하는건 label_no으로만
    infer_no=res['infer_no']

    dbConn = db_connector.DbConn()
    query = f"UPDATE infer_history SET feedback = {feedback} WHERE infer_no = {infer_no}"
    dbConn.insert(query=query)
    del(dbConn)
    return jsonify({'result': 'ok' })


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
    del(dbConn)
    # 결과 반환
    return jsonify({'result': 'ok', 'value': result})

@app.route('/auth', methods=('GET', 'POST'))
def auth():

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
    del(dbConn)
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
    del(dbConn)
    return jsonify({'result': 'ok'})


if __name__ == "__main__":
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS)
    ssl_context.load_cert_chain(certfile='server.crt', keyfile='server.key', password='1234')
    app.run(host='0.0.0.0', port=5443, ssl_context=ssl_context, debug=False)
