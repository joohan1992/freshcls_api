import requests

res = requests.post('https://10.28.78.30:8889/test', verify=False)
print(res.json())