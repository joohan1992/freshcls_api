import requests

res = requests.post('https://192.168.0.88/test', verify=False)
print(res.json())