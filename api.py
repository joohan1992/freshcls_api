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

os.environ["CUDA_DEVICE_ORDER"]="PCI_BUS_ID"   
os.environ["CUDA_VISIBLE_DEVICES"]="1"

def iferror(item, err="error"):
    try:
        return item
    except:
        return err
    
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

    # 파일명
    filename=now()+'.jpg'
    save_file_path = './request_image/'+filename
    while os.path.isfile(save_file_path):
        filename= filename.split(".jpg")[0]+"(1).jpg"
        save_file_path = './request_img/'+filename
    print(save_file_path)
    # 다시조립
    data = request.data
    data = np.frombuffer(data, dtype='float32').reshape((210, 280, 3))
    data = np.array(data, dtype='uint8')
    cv2.imwrite(save_file_path,data)
    
    query = "INSERT INTO img_data(date,time,resol_x,resol_y,file_path)"
    query += f" VALUES(NOW() ,NOW() , {280} , {210}, '{save_file_path[1:]}' ) RETURNING image_no"
    dbConn = db_connector.DbConn()
    dbConn.insert(query=query)        
    
            
    # 일반 Post로 전송했을 경우 데이터를 받는 코드(기존 클라이언트), xsize랑 ysize도 같이 받아야 함.
    ## 중간코드 추후작성요망
    
    cls_list = ['true']
    query = "INSERT INTO infer_history(date, str_no, model_no, image_no, result1, result2, result3, infer_speed, time, feedback)"
    query += f" VALUES(NOW() ,{0} , {0} , {dbConn.lastpick()} , 1, NULL , NULL, {23} ,NOW(), NULL) RETURNING infer_no"
    dbConn.insert(query=query)    
    
    return jsonify({'result': 'ok', 'cls_list': cls_list, 'infer_no':dbConn.lastpick(id=0) })

@app.route('/infer_feedback', methods=['POST'])
def infer_feedback():
    

    res= request.get_json()
    
    dbConn = db_connector.DbConn()
    query = f"UPDATE infer_history SET feedback = {res['feedback']} WHERE infer_no = {res['infer_no']}"
    dbConn.insert(query=query)    
    
    return jsonify({'result': 'ok thanksyou for feedback' })


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
