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

class machine():
    def __init__(self,info,gpu) -> None:
        self.model_no           = info[0]
        self.path               = info[1]
        self.preprocess         = info[2]
        self.ensemble_model_no  = info[3]
        self.isload=False
        self.load(self)
        os.environ["CUDA_DEVICE_ORDER"]="PCI_BUS_ID"
        os.environ["CUDA_VISIBLE_DEVICES"]=str(gpu)
    def info(self):
        pass
    def load(self):
        try:
            self.model  = load_model(self.path)
            self.isload = True
        except:
            self.model  = None
            self.isload = False
    def setImageInfo(self,res):
        self.encoded_img = res['image']
        self.x_size      = res['x_size']
        self.y_size      = res['y_size']
        self.img_channel = res['channel']
        self.userID      = res['ID']
        self.userPW      = res['PW']
        self.auth_key    = res['key']
        self.str_no      = res['str_no']
        self.send_device = res['send_device']
        self.auth        = res['auth'] # code or id
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
    def preprocessing(self):
        ## img resize / x,y size가 다르면 error 캐치하기 나중에추가
        data_resize=cv2.resize(self.data,(299,299))
        predict_img = cv2.cvtColor(data_resize,cv2.COLOR_BGR2RGB)
        self.x = image.image_utils.img_to_array(predict_img)
        self.x = np.expand_dims(self.x, axis = 0)     ## efficientnet일 경우 preprocessing 필요 x
        if self.preprocess=='Y':
            self.x = preprocess_input(self.x)
    def run(self, res):
        self.setImageInfo(res)
        self.saveImg()
        self.preprocessing()
        if self.isload:
            self.softmax = self.model.predict(self.x,verbose = 0)[0]
        else:
            self.load()
            self.softmax = self.model.predict(self.x,verbose = 0)[0]
        self.predict=sort_predict(self.softmax) # 내림차순으로 정렬
        self.log()
    def log(self):

        dbConn = db_connector.DbConn()

        seq=self.predict[0][0]
        label=self.seqToLabel(seq)
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

        ######여기부터하면됩니다.

    def seqToLabel(self,seq):
        dbConn = db_connector.DbConn()
        query = "SELECT model_label.label_no FROM model_label LEFT JOIN item_label ON model_label.label_no = item_label.label_no "
        query = f"WHERE label_seq= {seq} and model_no = {self.model_no}"
        result = dbConn.execute(query=query)[0][0]
        del(dbConn)
        return result

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
        query += f"WHERE item_label.valid_yn = 'N' and item_label.model_no = {model_no}"
        self.undeflist = [data for inner_list in dbConn.select(query=query) for data in inner_list]
        self.HUDDLE1=0.8
        self.HUDDLE2=0.7
        self.cls_list = []
        del(dbConn)
    def info(self):
        print("Number of Loaded Model : "+str(len(self.modellist)))
    def setHuddle(self,huddle1,huddle2):
        self.HUDDLE1=huddle1
        self.HUDDLE2=huddle2
    def runMachine(self,res):
        for i in self.modellist:
            i.run(res)
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
        if self.predicted_list[0][0] in self.undeflist: ##1순위가 undef thing일때 (얘는 undefthing label number를 반환)
            self.phase=1
        elif self.predicted_list[0][1]>self.HUDDLE1*len(self.modellist): ##1개만 출력
            self.phase=1
        elif len(self.predicted_set)==len(self.modellist): #undef출력 : -1
            self.phase=0
        elif self.maximumSoftmax < self.HUDDLE2: #undef출력 : -1
            self.phase=0
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
        query = f"WHERE label_seq= {seq} and model_no = {self.model_no}"
        result = dbConn.execute(query=query)[0][0]
        del(dbConn)
        return result

    def __del__(self):
        






##########################################################################################
##########################################################################################
