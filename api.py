from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
import numpy as np
import cv2
import db_connector

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
    data = request.data
    np_data = np.frombuffer(data, dtype='float32').reshape((299, 299, 3))

    int_np_data = np.array(np_data, dtype='int').reshape((299, 299, 3))
    cv2.imwrite('./test/test_white_rt/1.png', int_np_data)

    np_data_nm = np_data / 255.0
    frame = np_data_nm.reshape((1, 299, 299, 3))

    cls_list = []

    return jsonify({'result': 'ok', 'cls_list': cls_list})


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
    
    if auth_lst

    return jsonify({'result': auth_lst, 'authorization_result' : auth_result})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)


