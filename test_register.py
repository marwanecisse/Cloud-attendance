import os
import requests
import mimetypes

API_BASE = "http://localhost:7071/api"
REGISTER_URL = f"{API_BASE}/RegisterStudent"

PHOTO_DIR = "students_photo"
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

def parse_filename(filename):
    """
    Extrait uniquement le matricule depuis le nom du fichier.
    Format attendu : A001_...
    """
    name = os.path.splitext(filename)[0]
    parts = name.split("_")

    if not parts or not parts[0].isalnum():
        return None

    return parts[0].strip().upper()

def upload_image(path):
    from shared import upload_bytes_to_blob

    with open(path, "rb") as f:
        data = f.read()
    content_type, _ = mimetypes.guess_type(path)
    content_type = content_type or "application/octet-stream"

    return upload_bytes_to_blob(
        container="attendance",
        data=data,
        content_type=content_type,
        prefix="batch"
    )

def upload_with_retry(path, retries=3):
    for i in range(retries):
        try:
            url = upload_image(path)
            print(f"   ↑ Blob URL: {url}")
            return url
        except Exception as e:
            print(f"⚠️ Upload attempt {i+1} failed: {e}")
            if i + 1 == retries:
                print("❌ All upload attempts failed")
                return None
            print("→ Retrying…")


def main():
    photos = sorted(os.listdir(PHOTO_DIR))
    print(f"[+] Found {len(photos)} photos in '{PHOTO_DIR}'")

    for photo_filename in photos:
        ext = os.path.splitext(photo_filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            print(f"⚠️ Ignoring {photo_filename}: unsupported extension")
            continue

        full_path = os.path.join(PHOTO_DIR, photo_filename)
        if not os.path.isfile(full_path):
            continue

        matricule = parse_filename(photo_filename)
        if not matricule:
            print(f"⚠️ Skipping {photo_filename}: unable to extract matricule")
            continue

        # Demander les infos manuellement
        print(f"\n📌 Informations pour {matricule} ({photo_filename})")
        first_name = input("Prénom : ").strip()
        last_name = input("Nom : ").strip()
        class_id = input("Class ID : ").strip()

        if not first_name or not last_name or not class_id:
            print(f"⚠️ Informations incomplètes pour {matricule}, skipping.")
            continue

        print(f"Processing {matricule} ({first_name} {last_name})")

        # Upload image to blob
        try:
            blob_url = upload_image(full_path)
            print(f"   ↑ Blob URL: {blob_url}")
        except Exception as e:
            print(f"⚠️ Failed to upload {photo_filename}: {e}")
            continue

        # Register student
        payload = {
            "matricule": matricule,
            "first_name": first_name,
            "last_name": last_name,
            "class_id": int(class_id),
            "image_url": blob_url
        }

        try:
            resp = requests.post(REGISTER_URL, json=payload, timeout=120)
            print(f" → Register status: {resp.status_code}")
            print(resp.text)
        except Exception as e:
            print(f"⚠️ Failed RegisterStudent for {matricule}: {e}")

    print("\n✨ Batch processing completed!")

if __name__ == "__main__":
    main()
