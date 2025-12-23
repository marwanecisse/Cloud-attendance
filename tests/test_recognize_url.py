import requests

RECO_URL = "http://localhost:7071/api/RecognizeAndMark"

payload = {
    "request_id": "group-001",
    "class_id": 1,
    "image_url": "https://attendanceimage.blob.core.windows.net/attendance/uploads/d1b1c14d82da449fad81dc0021a7ec02.jpg",
    "threshold": 0.35
}

r = requests.post(RECO_URL, json=payload, timeout=180)
print("STATUS:", r.status_code)
print(r.text)
