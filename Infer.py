from keras.models import load_model
from keras.applications.inception_v3 import preprocess_input
from keras.preprocessing import image
import os
from datetime import datetime
import sys
import db_connector
import time
import cv2
import numpy as np
import base64

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
def authorize(auth_key):
    query = f"SELECT * FROM auth where auth_cd = '{auth_key}' and act_yn='Y'"
    dbConn = db_connector.DbConn()
    result=dbConn.select(query=query)
    del(dbConn)
    return False if len(result)==0 else True

encoding = sys.getdefaultencoding()
class model():
    def __init__(self,model_no,gpu) -> None: ## 이건 클라킬때 한번 해야됨.
        dbConn = db_connector.DbConn()
        self.model_no=model_no
        query = "SELECT ensemble_model.model_no, ensemble_model.model_path, ensemble_model.preprocess, ensemble_model.ensemble_model_no "
        query+= f"FROM ensemble_model LEFT JOIN model ON (model.model_no = ensemble_model.model_no) WHERE model.model_no={model_no}"
        self.ensemble_list=dbConn.select(query=query)
        self.modellist=[]
        for info in self.ensemble_list:
            self.modellist.append(machine(info,gpu=str(gpu))) # 뒤에숫자 gpu
        query =  "SELECT model_label.label_seq FROM model_label LEFT JOIN item_label "
        query += "ON model_label.label_no = item_label.label_no "
        query += f"WHERE item_label.valid_yn = 'N' and model_label.model_no = {model_no}"
        self.undeflist = [data for inner_list in dbConn.select(query=query) for data in inner_list]
        self.HUDDLE1=0.8
        self.HUDDLE2=0.7
        self.cls_list = []
        del(dbConn)
    def setHuddle(self,huddle1,huddle2):
        self.HUDDLE1=huddle1
        self.HUDDLE2=huddle2
    def info(self):
        print("Model Num : "+str(self.model_no))
    def setImageInfo(self,res):
        self.encoded_img = res['image']
        self.x_size      = res['x_size']
        self.y_size      = res['y_size']
        self.userID      = res['ID']
        self.userPW      = res['PW']
        self.auth_key    = res['key']
        self.send_device = res['send_device']
        self.auth        = res['auth'] # code or id

        dbConn = db_connector.DbConn()
        if self.userID=="None":
            query = f"SELECT * FROM auth WHERE auth_cd='{self.auth_key}' "
            self.str_no = dbConn.selectAsDict(query)[0]['str_no']
        else:
            query = f"SELECT * FROM login WHERE id='{self.userID}' "
            self.str_no = dbConn.selectAsDict(query)[0]['str_no']
        del(dbConn)

    def saveImg(self):  
        # set filename
        filename=now()+'.jpg'
        self.save_file_path = './request_image/'+filename
        while os.path.isfile(self.save_file_path):
            filename = filename.split(".jpg")[0]+"(1).jpg"
            self.save_file_path = './request_image/' + filename
        print(self.save_file_path)

        # string to bytes & write
        string_to_bytes = self.encoded_img.encode(encoding)
        bytes_to_numpy = base64.decodebytes(string_to_bytes)
        if self.send_device=="android" or self.send_device=="web":
            list_bytes = []
            bytes_to_numpy = bytes_to_numpy.split(b'[')[1].split(b']')[0].split(b', ')
            for item in bytes_to_numpy:
                list_bytes.append(int(item))
            self.data = cv2.cvtColor(np.array(list_bytes, dtype=np.uint8).reshape((int(self.y_size), int(self.x_size), -1))[:, :, :3],cv2.COLOR_RGB2BGR)
        else:
            self.data = np.frombuffer(bytes_to_numpy, dtype=np.uint8).reshape((self.y_size, self.x_size, -1))
        cv2.imwrite(self.save_file_path, self.data)

        # insert image data into db
        query = "INSERT INTO img_data(date,time,resol_x,resol_y,file_path)"
        query += f" VALUES(NOW() ,NOW() , {self.x_size} , {self.y_size}, '{self.save_file_path[1:]}' ) RETURNING image_no"
        dbConn = db_connector.DbConn()
        dbConn.insert(query=query)

        self.img_no=dbConn.lastpick() # pick image no

        del(dbConn)

    def runMachine(self):
        for i in self.modellist:
            i.run(self.data)
        self.max_predicted_set()
        self.clsLogic()

    def max_predicted_set(self):
        self.predicted_set = set()
        self.maximumSoftmax=-1
        temp=0 # 이거 어떻게 없이 한줄로 하는코드있으면 좋겠다.
        for i in self.modellist:
            self.predicted_set.add(i.predict[0][0])
            if i.predict[0][1] > self.maximumSoftmax:
                self.maximumSoftmax = i.predict[0][1]
            if temp==0:
                features  = i.softmax
            else:
                features += i.softmax
            temp+=1
        self.predicted_list=sort_predict(features) # 내림차순으로 정렬
        return self.predicted_set
        #각 모델들의 1순위들 index (seq)
    #0개 / 1개 / 2개 잖아.
    def clsLogic(self):
        self.cls_list=[]
        phase=-1
        if self.predicted_list[0][0] in self.undeflist: ##1순위가 undef thing일때 (얘는 undefthing label number를 반환)
            phase=1
        elif self.predicted_list[0][1]>self.HUDDLE1*len(self.modellist): ##1개만 출력
            phase=1
        elif len(self.predicted_set)==len(self.modellist): #undef출력 : -1
            phase=0
        elif self.maximumSoftmax < self.HUDDLE2: #undef출력 : -1
            phase=0
        elif (self.predicted_list[0][1]+self.predicted_list[1][1]) > self.HUDDLE2*len(self.modellist) :##2개합쳐서 huddle2*4넘을때도하자
            if self.predicted_list[1][0] in self.undeflist: # 2순위가 undef일때
                phase=1
            else:
                phase=2
        else:
            phase=0        
        ####분류끝
        if phase==1:
            seq=self.predicted_list[0][0]
            result=self.seqToLabel(seq)        
            self.cls_list.append(result)
        elif phase==2:
            seq=self.predicted_list[0][0]
            result=self.seqToLabel(seq)        
            self.cls_list.append(result)
            seq=self.predicted_list[1][0]
            result=self.seqToLabel(seq)
            self.cls_list.append(result)            
        else:
            self.cls_list.append(-1)
        #### cls_list에 넣기
        return self.cls_list

    def seqToLabel(self,seq):
        dbConn = db_connector.DbConn()
        query = "SELECT model_label.label_no FROM model_label LEFT JOIN item_label ON model_label.label_no = item_label.label_no "
        query += f"WHERE label_seq = {seq} and model_no = {self.model_no}"
        result = dbConn.execute(query=query)[0][0]
        del(dbConn)
        return result

    def log(self,timecheck):
        self.log_cls_list=[]
        self.log_cls_list=self.cls_list.copy()
        if len(self.log_cls_list)==0 or self.log_cls_list==None:
            self.log_cls_list=['NULL','NULL']
        elif len(self.log_cls_list)==1: 
            self.log_cls_list.append('NULL')
        else:
            pass
        dbConn = db_connector.DbConn()
        query = "INSERT INTO infer_history(date, str_no, model_no, image_no, result1, result2, infer_speed, time, feedback)"
        query += f" VALUES(NOW() ,{self.str_no} , {self.model_no} , {self.img_no} , {self.log_cls_list[0]}, {self.log_cls_list[1]} , {timecheck} ,NOW(), NULL) RETURNING infer_no"
        dbConn.insert(query=query)
        self.infer_no=dbConn.lastpick(id=0)
        for machine in self.modellist:
            machine.log(self.img_no, self.infer_no)
        del(dbConn)

    def __del__(self):
        pass

class machine():
    def __init__(self,info,gpu) -> None:
        os.environ["CUDA_DEVICE_ORDER"]="PCI_BUS_ID"
        os.environ["CUDA_VISIBLE_DEVICES"]='"'+str(gpu)+'"'
        self.model_no           = info[0]
        self.path               = info[1]
        self.preprocess         = info[2]
        self.ensemble_model_no  = info[3]
        self.isload=False
        self.load()
        self.info()
    def info(self):
        if self.isload:
            print(f"machine {self.ensemble_model_no} init")
        else:
            print(f"machine {self.ensemble_model_no} cannot load file.")
    def load(self):
        try:
            self.model  = load_model(self.path)
            self.isload = True
        except Exception as e:
            self.model  = None
            self.isload = False
            print(e)
    def preprocessing(self,data):
        ## img resize / x,y size가 다르면 error 캐치하기 나중에추가
        data_resize=cv2.resize(data,(299,299))
        predict_img = cv2.cvtColor(data_resize,cv2.COLOR_BGR2RGB)
        self.x = image.image_utils.img_to_array(predict_img)
        self.x = np.expand_dims(self.x, axis = 0)     ## efficientnet일 경우 preprocessing 필요 x
        if self.preprocess=='Y':
            self.x = preprocess_input(self.x)
    def run(self, data):
        self.preprocessing(data)
        if self.isload:
            self.softmax = self.model.predict(self.x,verbose = 0)[0]
        else:
            self.load()
            self.softmax = self.model.predict(self.x,verbose = 0)[0]
        self.predict=sort_predict(self.softmax) # 내림차순으로 정렬

    def log(self,img_no,infer_no):
        self.infer_no=infer_no
        dbConn = db_connector.DbConn()

        seq=self.predict[0][0]
        result1=self.seqToLabel(seq)
        seq=self.predict[1][0]
        result2=self.seqToLabel(seq)

        # prob 1,2 (점수)
        prob1=self.predict[0][1]
        prob2=self.predict[1][1]
        query = "INSERT INTO ensemble_infer_history(infer_no, image_no, result1, result2, result1_prob, result2_prob,ensemble_model_no)"
        query += f" VALUES({self.infer_no} ,{img_no},{result1},{result2},{prob1},{prob2},{self.ensemble_model_no} ) "
        dbConn.insert(query=query)

    def seqToLabel(self,seq):
        dbConn = db_connector.DbConn()
        query = "SELECT model_label.label_no FROM model_label LEFT JOIN item_label ON model_label.label_no = item_label.label_no "
        query += f"WHERE label_seq = {seq} and model_no = {self.model_no}"
        result = dbConn.execute(query=query)[0][0]
        del(dbConn)
        return result


        ####################### EOF #######################