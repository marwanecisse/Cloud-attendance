import requests

UPLOAD_URL = "http://localhost:7071/api/UploadImage"

with open("photo.jpg", "rb") as f:
    r = requests.post(
        UPLOAD_URL,
        data=f.read(),
        headers={"Content-Type": "image/jpeg"},
        timeout=120
    )

print("STATUS:", r.status_code)
print(r.text)
