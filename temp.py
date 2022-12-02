
import requests

res=requests.post('https://10.28.100.11:5443/login',json={'id':'panda','password':'dbeaver'},verify=False)

print(res.json())