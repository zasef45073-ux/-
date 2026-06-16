import requests

response = requests.post("http://192.168.10.88:8000/analyze/", files={"file": open("/home/hyung/Downloads/h_1.png", "rb")})
result = response.json().get("component_results")
print(result)