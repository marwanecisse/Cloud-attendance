import requests
import json

REGISTER_URL = "http://localhost:7071/api/RegisterStudent"

payload = {
    "matricule": "A010",
    "first_name": "Test",
    "last_name": "Blob",
    "class_id": 1,
    "image_url": "https://attendanceimage.blob.core.windows.net/attendance/uploads/7c7fa7c277134d75b0f4557ea261b171.jpg"
}

r = requests.post(REGISTER_URL, json=payload, timeout=180)
print("STATUS:", r.status_code)
print(r.text)
