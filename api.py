from flask import Flask, request, jsonify, render_template, send_from_directory, json
from flask_cors import CORS
import cv2
import db_connector
import ssl

import Infer as inf

model_load_dict = {}

def authorize(auth_key):
    query = f"SELECT * FROM auth where auth_cd = '{auth_key}' and act_yn='Y'"
    dbConn = db_connector.DbConn()
    result=dbConn.select(query=query)
    del(dbConn)
    return False if len(result)==0 else True

app = Flask(__name__, template_folder='web')
CORS(app, support_credentials=True)

FLUTTER_WEB_APP = 'web'

def initialize(str_no):
    # 전달받은 str_no로 사용하고 있는 model_no 찾기
    query = f"SELECT model_no, act_yn from model where str_no={str_no} and use_yn= 'Y'"
    dbConn = db_connector.DbConn()

    model_no = dbConn.select(query=query)[0][0]   ##model_no
    model_state= dbConn.select(query=query)[0][1] ##act_yn

    if model_state == "N":
        return "fail"

    query = "SELECT model_label.label_no, item_label.label_nm_eng, item_label.label_nm_kor, item_cd FROM" # 라벨 / 영어 / 한글 / 아이템코드 전달(해당모델)
    query+= f" model_label LEFT JOIN item_label ON model_label.label_no = item_label.label_no where model_label.model_no={model_no}" #modelnum
    str_label_list=dbConn.select(query=query)
    str_label_list.append([-1, 'Undefined', 'Undefined','None'])
    del(dbConn)

    return str_label_list #feedback을 위해서 infer_no도 반환

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

@app.route('/client_init', methods=['POST'])
def client_init():
    '''
    input   :   'key'   /   'str_no'
    output  :   result : 'ok' / 'fail'
                str_label_list : list
    '''
    dbConn = db_connector.DbConn()

    res=request.get_json()
    auth_key    = res['key']
    
    query = f"SELECT str_no FROM auth WHERE auth_cd = '{auth_key}'"
    str_no      = dbConn.select(query=query)[0][0]
    query = f"SELECT model_no FROM model WHERE str_no = {str_no}"
    model_no=dbConn.select(query=query)[0][0]
    
    isauth=authorize(auth_key)
    global model_load_dict
    if isauth==False:
        return jsonify({'result' : 'fail'})
    # DB에서 api 형태로 query 정보를 받아오는 코드
    else:
        str_label_list = initialize(str_no)
        if auth_key in list(model_load_dict.keys()):
            print(f"MODEL NUMBER {model_no} has been already Loaded.")
        else:

            model_init=inf.model(model_no,1)
            model_load_dict[auth_key] = model_init # 나중엔 임시키 / gpu도 자동설정 str_no가 아니라 model_no으로 해야됨.
            print(f"MODEL NUMBER {model_no} is Loaded.")
            del(dbConn)
    return jsonify({'result' : 'ok', 'str_label_list':str_label_list})


@app.route('/login', methods=['POST'])
def login():
    global model_load_dict
    res=request.get_json()
    # Flutter에서 해당 url로 email과 password를 post한 내용을 받아오는 코드
        # request 방식 확인 코드
    userID = str(res['id'])
    userPW = str(res['password'])
    params = [userID, userPW]
    print(params)
    param_dict = dict(zip(['id', 'password'], params))

    # DB에서 api 형태로 query 정보를 받아오는 코드

    query = f"SELECT * FROM login WHERE id = '{userID}';"
    dbConn = db_connector.DbConn()

    ##아이디가 있나없나 보는거
    login_data = dbConn.select(query=query)
    login_dict = None
    if len(login_data) > 0:
        login_dict = dict(zip(['id', 'password', 'login_no', 'act_yn', 'str_no'],login_data[0]))
        print(login_dict)
        isIdExist = True
    else:
        isIdExist = False

    # Flutter에서 받아온 정보를 DB에서 받아온 정보와 비교하여 POST할 dict를 작성하는 코드
    # flutter에 전송할 dictionary
    # 형태는 {act_yn, login_no, str_no, log_in_state, log_in_text}
    '''
        result = 'ok' / 'fail'
        act_yn = 'Y' / 'N'
        login_no = 해당 로그인 정보
        str_no = 매장 정보
        log_in_st    =  0 : 로그인 성공 + 인증 Y, 
                        1 : 로그인 성공 + 인증 N, 
                        2 : ID 오류, 
                        3 : PW 오류(ID는 맞으나 PW 틀림)
        log_in_text =   0 : '로그인 및 인증을 모두 성공했습니다.' ,
                        1 : '인증이 되지 않은 로그인 정보입니다.',
                        2 : 'ID가 틀렸습니다.', 
                        3 : 'PW가 틀렸습니다.' 
    '''
    dict_result = {}
    dict_text = {   0 : '로그인 및 인증을 모두 성공했습니다.',
                    1 : '인증이 되지 않은 로그인 정보입니다.',
                    2 : 'ID가 틀렸습니다.', 
                    3 : 'PW가 틀렸습니다.',
                    4 : '인증 오류 발생'    }
    
    # 초기화
    log_in_st = 4
    dict_result['log_in_st'] = log_in_st 
    dict_result['result'] = 'fail'

    ## 5개 다 받아오긴함 패스워드랑 act까지 통과하면 ok
    if isIdExist: 
        if login_dict['password'] == param_dict['password'] and login_dict['act_yn'] == 'Y':
            log_in_st = 0
            dict_result['result'] = 'ok'
        elif login_dict['password'] == param_dict['password'] and login_dict['act_yn'] == 'N':
            log_in_st = 1
        else:
            log_in_st = 3
        dict_result['str_no'] = login_dict['str_no']
        dict_result['act_yn'] = login_dict['act_yn']
        dict_result['login_no'] = login_dict['login_no'] # 아이디가 있을때만 return
    else:
        log_in_st = 2

    
    str_no = login_dict['str_no']
    query = f"SELECT model_no FROM model WHERE str_no = {str_no}"
    model_no=dbConn.select(query=query)[0][0]

    # isIdExist랑 상관없이 무조건 return하는것
    dict_result['log_in_st'] = log_in_st
    dict_result['log_in_text'] = dict_text[log_in_st]
    
    if dict_result['result'] == 'ok':
        dict_result['label_init']=initialize(dict_result['str_no'])

        # 모델 불러오기
        if userID in list(model_load_dict.keys()):
            print(f"MODEL NUMBER {model_no} has been already Loaded.")
        else:
            model_init=inf.model(model_no,0)
            model_load_dict[userID] = model_init# 나중엔 임시키 / gpu도 자동설정 str_no가 아니라 model_no으로 해야됨.
            print(f"MODEL NUMBER {model_no} is Loaded.")
    print(dict_result)

    # 비교 후 작성된 dict 내용을 json 혹은 ajax 형태로 flutter에 전송하기 위한 코드
    # res = requests.post("https://192.168.0.108:2092/login", data = json.dumps(dict_result), verify = False)
    del(dbConn)
    return jsonify(dict_result)

@app.route('/run', methods=['POST'])
def run():
    global model_load_dict
    timecheck=inf.current_milli_time()
    
    #json에서 data 받아오기
    res=request.get_json()
    isauth=authorize(res['key'])
    if isauth == False: ## 인증키 없으면
        return jsonify({'result': 'fail'})
    if res['ID']=='None':
        model=model_load_dict[res['key']]
    else :
        model=model_load_dict[res['ID']]
    model.info()
    model.setImageInfo(res)
    model.saveImg()
    model.runMachine()
    cls_list=model.clsLogic()
    timecheck=inf.current_milli_time()-timecheck
    model.log(timecheck)

    return jsonify({'result': 'ok', 'cls_list': cls_list, 'infer_no' :model.infer_no }) #feedback을 위해서 infer_no도 반환

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
        return jsonify({'result': 'fail'})
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
