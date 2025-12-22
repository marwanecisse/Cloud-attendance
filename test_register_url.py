import requests
import json

REGISTER_URL = "http://localhost:7071/api/RegisterStudent"

payload = {
    "matricule": "A006",
    "first_name": "Yoonchae",
    "last_name": "Jeong",
    "class_id": 1,
    "image_url": "https://attendanceimage.blob.core.windows.net/attendance/test/78aece20ceaf4dbc97cb9970709e2f3e.jpg"
}

r = requests.post(REGISTER_URL, json=payload, timeout=180)
print("STATUS:", r.status_code)
print(r.text)
