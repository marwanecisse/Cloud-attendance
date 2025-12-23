import requests

URL = "http://localhost:7071/api/RunAttendancePipeline"

payload = {
    "class_id": 1,
    "image_url": "https://attendanceimage.blob.core.windows.net/attendance/test/b952aa34d31c4756870acebb261cbb60.jpg",
    "threshold": 0.35,
    "request_id": "demo-001"
}

r = requests.post(URL, json=payload, timeout=300)
print("STATUS:", r.status_code)
print(r.text)
