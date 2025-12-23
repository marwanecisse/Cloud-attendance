# RecognizeAndMark/__init__.py
import azure.functions as func
import json
import numpy as np

from shared import (
    mysql_conn,
    face_detect_azure,
    crop_face,
    embed_face,
    now_date_time,
    download_url_bytes,
    bytes_to_bgr_image
)

EMBED_DIM = 512

# Valeur réaliste pour photo de groupe
DEFAULT_THRESHOLD = 0.55


def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()

        image_url = body.get("image_url")
        class_id = body.get("class_id")
        threshold = float(body.get("threshold", DEFAULT_THRESHOLD))
        request_id = body.get("request_id")

        if not image_url or not class_id:
            return func.HttpResponse(
                json.dumps({"ok": False, "error": "image_url et class_id requis"}),
                status_code=400,
                mimetype="application/json"
            )

        class_id = int(class_id)

        # --------------------------------------------------
        # 1) Télécharger image
        # --------------------------------------------------
        img_bytes = download_url_bytes(image_url)
        bgr = bytes_to_bgr_image(img_bytes)

        conn = mysql_conn()

        # --------------------------------------------------
        # 2) Nombre total d'étudiants
        # --------------------------------------------------
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) AS total FROM students WHERE class_id=%s",
                (class_id,)
            )
            total_students = int(cur.fetchone()["total"])

        # --------------------------------------------------
        # 3) Détection visages
        # --------------------------------------------------
        faces = face_detect_azure(img_bytes)

        if not faces:
            return func.HttpResponse(
                json.dumps({
                    "ok": True,
                    "data": {
                        "faces_detected": 0,
                        "total_students": total_students,
                        "present_count": 0,
                        "attendance_percentage": 0.0,
                        "results": []
                    },
                    "error": None
                }),
                status_code=200,
                mimetype="application/json"
            )

        # --------------------------------------------------
        # 4) Charger embeddings DB groupés par étudiant
        # --------------------------------------------------
        embeddings_by_student = {}
        meta_by_student = {}

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    f.student_id,
                    f.face_encoding,
                    s.matricule,
                    s.first_name,
                    s.last_name
                FROM faces f
                JOIN students s ON s.id = f.student_id
                WHERE s.class_id = %s
                """,
                (class_id,)
            )
            rows = cur.fetchall()

        for r in rows:
            e = np.frombuffer(r["face_encoding"], dtype=np.float32)

            if e.shape != (EMBED_DIM,) or not np.isfinite(e).all():
                continue

            n = float(np.linalg.norm(e))
            if n < 0.1 or n > 100:
                continue

            e = e / n
            sid = r["student_id"]

            if sid not in embeddings_by_student:
                embeddings_by_student[sid] = []
                meta_by_student[sid] = {
                    "student_id": sid,
                    "matricule": r["matricule"],
                    "first_name": r["first_name"],
                    "last_name": r["last_name"]
                }

            embeddings_by_student[sid].append(e)

        if not embeddings_by_student:
            raise ValueError("Aucun embedding valide en base pour cette classe")

        # --------------------------------------------------
        # 5) Matching visage par visage (PAR ÉTUDIANT)
        # --------------------------------------------------
        results = []
        present_ids = set()
        att_date, att_time = now_date_time()

        for f in faces:
            crop = crop_face(bgr, f["faceRectangle"])
            emb = embed_face(crop)

            if emb.shape != (EMBED_DIM,) or not np.isfinite(emb).all():
                results.append({"match": False, "reason": "embedding_invalide"})
                continue

            n = float(np.linalg.norm(emb))
            if n < 0.1 or n > 100:
                results.append({"match": False, "reason": "embedding_norm"})
                continue

            emb = emb / n

            best_sid = None
            best_dist = 1.0

            # 🔑 distance minimale PAR ÉTUDIANT
            for sid, emb_list in embeddings_by_student.items():
                d = min(
                    1.0 - float(np.dot(known_emb, emb))
                    for known_emb in emb_list
                )

                if d < best_dist:
                    best_dist = d
                    best_sid = sid

            if best_sid is not None and best_dist <= threshold:
                present_ids.add(best_sid)
                results.append({
                    "match": True,
                    "distance": round(best_dist, 4),
                    "student": meta_by_student[best_sid]
                })
            else:
                results.append({
                    "match": False,
                    "distance": round(best_dist, 4)
                })

        # --------------------------------------------------
        # 6) Stats présence
        # --------------------------------------------------
        present_count = len(present_ids)
        attendance_percentage = (
            round((present_count / total_students) * 100, 2)
            if total_students > 0 else 0.0
        )

        # --------------------------------------------------
        # 7) Insert attendance + logs
        # --------------------------------------------------
        inserted = []

        with conn.cursor() as cur:
            for sid in present_ids:
                try:
                    cur.execute(
                        """
                        INSERT INTO attendance
                        (student_id, attendance_date, attendance_time, source)
                        VALUES (%s,%s,%s,'FACE')
                        """,
                        (sid, att_date, att_time)
                    )
                    inserted.append(sid)
                except Exception:
                    pass

            cur.execute(
                """
                INSERT INTO recognition_logs
                (request_id, faces_detected, matched_students, payload_meta)
                VALUES (%s,%s,%s,%s)
                """,
                (
                    request_id,
                    len(faces),
                    len(inserted),
                    json.dumps({
                        "class_id": class_id,
                        "threshold": threshold,
                        "total_students": total_students,
                        "present_count": present_count,
                        "attendance_percentage": attendance_percentage
                    })
                )
            )

        print(
            f"[RECO] class={class_id} faces={len(faces)} "
            f"matched={present_count} threshold={threshold}"
        )

        return func.HttpResponse(
            json.dumps({
                "ok": True,
                "data": {
                    "faces_detected": len(faces),
                    "total_students": total_students,
                    "present_count": present_count,
                    "attendance_percentage": attendance_percentage,
                    "results": results
                },
                "error": None
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
