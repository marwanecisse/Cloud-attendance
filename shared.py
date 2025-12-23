# shared.py
import os, base64, datetime, uuid
import numpy as np
import cv2
import pymysql
import requests
from deepface import DeepFace
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from azure.storage.blob import BlobServiceClient, ContentSettings
from azure.core.exceptions import ResourceExistsError

# -------------------------
# Helpers ENV
# -------------------------
def require_env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise ValueError(f"Missing environment variable: {name}")
    return v

# -------------------------
# HTTP session robuste (Face API)
# -------------------------
_session = requests.Session()
retries = Retry(
    total=5,
    backoff_factor=1.5,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["POST"]
)
_session.mount("https://", HTTPAdapter(max_retries=retries))

# -------------------------
# MySQL
# -------------------------
def mysql_conn():
    # NOTE: si tu utilises un CA pem spécifique, on adaptera ssl={"ca": "..."}.
    return pymysql.connect(
        host=require_env("MYSQL_HOST"),
        user=require_env("MYSQL_USER"),
        password=require_env("MYSQL_PASSWORD"),
        database=require_env("MYSQL_DB"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
        ssl={"ssl": {}}
    )

# -------------------------
# Image utils
# -------------------------
def b64_to_bytes(b64_str: str) -> bytes:
    """
    Supporte:
    - base64 brut
    - data URL: data:image/jpeg;base64,....
    """
    if "," in b64_str:
        b64_str = b64_str.split(",", 1)[1]
    return base64.b64decode(b64_str)

def bytes_to_bgr_image(img_bytes: bytes):
    arr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Image invalide (imdecode retourne None)")
    return img

def b64_to_bgr_image(b64_str: str):
    return bytes_to_bgr_image(b64_to_bytes(b64_str))

def crop_face(bgr_img, rect: dict):
    top, left, width, height = rect["top"], rect["left"], rect["width"], rect["height"]
    h, w = bgr_img.shape[:2]
    x1, y1 = max(0, left), max(0, top)
    x2, y2 = min(w, left + width), min(h, top + height)
    face = bgr_img[y1:y2, x1:x2]
    if face.size == 0:
        raise ValueError("Crop vide (rectangle hors image)")
    return face

# -------------------------
# Azure Face API (Detect only)
# -------------------------
def face_detect_azure(image_bytes: bytes):
    endpoint = require_env("FACE_ENDPOINT").rstrip("/")
    key = require_env("FACE_KEY")

    url = f"{endpoint}/face/v1.0/detect"
    params = {
        "returnFaceId": "false",
        "returnFaceLandmarks": "false",
        "recognitionModel": "recognition_04",
        "detectionModel": "detection_03"
    }
    headers = {
        "Ocp-Apim-Subscription-Key": key,
        "Content-Type": "application/octet-stream"
    }

    # timeout=(connect, read)
    r = _session.post(url, params=params, headers=headers, data=image_bytes, timeout=(10, 90))
    r.raise_for_status()
    return r.json()

# -------------------------
# Embedding (DeepFace / Facenet512)
# -------------------------
def embed_face(face_bgr) -> np.ndarray:
    """
    Retourne un vecteur float32 (Facenet512).
    """
    rgb = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2RGB)
    rep = DeepFace.represent(rgb, model_name="Facenet512", enforce_detection=False)
    return np.array(rep[0]["embedding"], dtype=np.float32)

def cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) + 1e-10
    d = 1.0 - float(np.dot(a, b) / denom)
    # sécurité numérique (peut donner -1e-7)
    return max(0.0, d)

def now_date_time():
    now = datetime.datetime.now()
    return now.date(), now.time().replace(microsecond=0)

# -------------------------
# Azure Blob Storage
# -------------------------
def _ext_from_content_type(ct: str) -> str:
    ct = (ct or "").lower()
    if "png" in ct:
        return "png"
    if "webp" in ct:
        return "webp"
    # par défaut
    return "jpg"

def blob_client():
    conn_str = require_env("BLOB_CONNECTION_STRING")
    return BlobServiceClient.from_connection_string(conn_str)

def upload_bytes_to_blob(container: str, data: bytes, content_type: str, prefix: str = "images") -> str:
    """
    Upload bytes -> blob URL.
    """
    service = blob_client()
    cont = service.get_container_client(container)

    try:
        cont.create_container()
    except ResourceExistsError:
        pass

    ext = _ext_from_content_type(content_type)
    name = f"{prefix}/{uuid.uuid4().hex}.{ext}"

    blob = cont.get_blob_client(name)
    blob.upload_blob(
        data,
        overwrite=True,
        content_settings=ContentSettings(content_type=content_type or "application/octet-stream")
    )
    return blob.url

def download_url_bytes(url: str) -> bytes:
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    return r.content
