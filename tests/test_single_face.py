import base64
import requests

RECO_URL = "http://localhost:7071/api/RecognizeAndMark"

def img_to_b64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

payload = {
    "request_id": "single-001",
    "image_b64": img_to_b64("ManonBannerman.webp"),
    "threshold": 0.35
}

r = requests.post(RECO_URL, json=payload, timeout=180)
print("STATUS:", r.status_code)
print(r.text)
