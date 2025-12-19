import base64
import requests
import json

BASE_URL = "http://localhost:7071/api"
# Si authLevel=function et que ça exige une clé, ajoute ?code=... à l'URL (voir plus bas)
REGISTER_URL = f"{BASE_URL}/RegisterStudent"
RECO_URL = f"{BASE_URL}/RecognizeAndMark"

def img_to_b64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

# -------- 1) Test RegisterStudent (1 visage) --------
img_b64 = img_to_b64("photo.jpg")

payload_register = {
    "matricule": "A001",
    "first_name": "Ali",
    "last_name": "Diallo",
    "class_id": 1,
    "image_b64": img_b64
}

r = requests.post(REGISTER_URL, json=payload_register, timeout=120)
print("REGISTER status:", r.status_code)
print(r.text)

# -------- 2) Test RecognizeAndMark (peut être multi-visages) --------
payload_reco = {
    "request_id": "sess-001",
    "image_b64": img_b64,      # tu peux remplacer par une image multi-visages plus tard
    "threshold": 0.35
}

r2 = requests.post(RECO_URL, json=payload_reco, timeout=120)
print("\nRECO status:", r2.status_code)
print(r2.text)
