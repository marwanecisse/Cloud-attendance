import base64
import requests

BASE_URL = "http://localhost:7071/api"
REGISTER_URL = f"{BASE_URL}/RegisterStudent"
RECO_URL = f"{BASE_URL}/RecognizeAndMark"

def img_to_b64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

# 3) Recognize on group photo (2 faces)
payload_reco = {
    "request_id": "group-test-001",
    "image_b64": img_to_b64("selenaetjustin.jpg"),
    "threshold": 0.35
}
r = requests.post(RECO_URL, json=payload_reco, timeout=180)
print("\nRECO GROUP:", r.status_code)
print(r.text)