#RegisterStudent/__init__.py
import azure.functions as func
import json
import numpy as np

from shared import (
    mysql_conn,
    face_detect_azure,
    crop_face,
    embed_face,
    download_url_bytes,
    bytes_to_bgr_image
)

EMBED_DIM = 512

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()

        matricule = body["matricule"]
        first_name = body.get("first_name")
        last_name = body.get("last_name")
        class_id = body.get("class_id")
        image_url = body["image_url"]

        # 1) Télécharger image
        img_bytes = download_url_bytes(image_url)
        bgr = bytes_to_bgr_image(img_bytes)

        # 2) Détection visage (1 seul requis)
        faces = face_detect_azure(img_bytes)
        if len(faces) != 1:
            return func.HttpResponse(
                json.dumps({
                    "ok": False,
                    "error": "La photo doit contenir exactement un visage",
                    "faces_detected": len(faces)
                }),
                status_code=400,
                mimetype="application/json"
            )

        # 3) Crop + embedding
        face_crop = crop_face(bgr, faces[0]["faceRectangle"])
        emb = embed_face(face_crop)

        # 4) Validation embedding
        if emb.shape != (EMBED_DIM,):
            raise ValueError(f"Embedding invalide: shape={emb.shape}")

        if not np.isfinite(emb).all():
            raise ValueError("Embedding contient NaN ou inf")

        norm = float(np.linalg.norm(emb))
        if norm < 0.1 or norm > 100:
            raise ValueError(f"Embedding anormal (norm={norm})")

        emb = emb / norm  # normalisation L2

        # 5) DB: insert / update
        conn = mysql_conn()
        with conn.cursor() as cur:
            # 5.a) Rechercher étudiant existant
            cur.execute("SELECT id FROM students WHERE matricule=%s", (matricule,))
            row = cur.fetchone()

            if row:
                student_id = row["id"]

                # mettre à jour les infos si nécessaires
                cur.execute(
                    """
                    UPDATE students
                    SET first_name=%s,
                        last_name=%s,
                        class_id=%s,
                        profile_image_url=%s
                    WHERE id=%s
                    """,
                    (first_name, last_name, class_id, image_url, student_id)
                )

            else:
                # insérer nouvel étudiant
                cur.execute(
                    """
                    INSERT INTO students
                    (matricule, first_name, last_name, class_id, profile_image_url)
                    VALUES (%s,%s,%s,%s,%s)
                    """,
                    (matricule, first_name, last_name, class_id, image_url)
                )
                student_id = cur.lastrowid

            # 5.b) Ajouter un nouvel embedding sans supprimer les anciens
            cur.execute(
                """
                INSERT INTO faces (student_id, encoding_format, face_encoding)
                VALUES (%s,%s,%s)
                """,
                (
                    student_id,
                    "facenet512_l2",
                    emb.astype(np.float32).tobytes()
                )
            )

        return func.HttpResponse(
            json.dumps({
                "ok": True,
                "student_id": student_id,
                "profile_image_url": image_url
            }),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        return func.HttpResponse(
            json.dumps({"ok": False, "error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
