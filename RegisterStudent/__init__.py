import azure.functions as func
import json
import numpy as np
import cv2

from shared import (
    mysql_conn, face_detect_azure,
    crop_face, embed_face,
    download_url_bytes, bytes_to_bgr_image
)

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
        matricule = body["matricule"]
        first_name = body.get("first_name")
        last_name = body.get("last_name")
        class_id = body.get("class_id")
        image_url = body["image_url"]

        # 1) Télécharger l'image depuis Blob
        img_bytes = download_url_bytes(image_url)
        bgr = bytes_to_bgr_image(img_bytes)

        # 2) Détection via Face API
        faces = face_detect_azure(img_bytes)
        if len(faces) != 1:
            return func.HttpResponse(
                json.dumps({"error": "La photo doit contenir exactement 1 visage", "faces_detected": len(faces)}),
                status_code=400, mimetype="application/json"
            )

        # 3) Crop + Embedding local
        face_crop = crop_face(bgr, faces[0]["faceRectangle"])
        emb = embed_face(face_crop)

        # 4) DB: student + face
        conn = mysql_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM students WHERE matricule=%s", (matricule,))
            row = cur.fetchone()

            if row:
                student_id = row["id"]
                cur.execute(
                    """
                    UPDATE students
                    SET first_name=%s, last_name=%s, class_id=%s, profile_image_url=%s
                    WHERE id=%s
                    """,
                    (first_name, last_name, class_id, image_url, student_id)
                )
            else:
                cur.execute(
                    """
                    INSERT INTO students (matricule, first_name, last_name, class_id, profile_image_url)
                    VALUES (%s,%s,%s,%s,%s)
                    """,
                    (matricule, first_name, last_name, class_id, image_url)
                )
                student_id = cur.lastrowid

            cur.execute(
                "INSERT INTO faces (student_id, encoding_format, face_encoding) VALUES (%s,%s,%s)",
                (student_id, "facenet512_f32", emb.tobytes())
            )

        return func.HttpResponse(
            json.dumps({"ok": True, "student_id": student_id, "profile_image_url": image_url}),
            status_code=200, mimetype="application/json"
        )

    except Exception as e:
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500, mimetype="application/json"
        )
