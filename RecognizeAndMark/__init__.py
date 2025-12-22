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
MARGIN = 0.05

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()

        image_url = body.get("image_url")
        class_id = body.get("class_id")
        threshold = float(body.get("threshold", 0.35))
        request_id = body.get("request_id")

        if not image_url or not class_id:
            return func.HttpResponse(
                json.dumps({"ok": False, "error": "image_url et class_id requis"}),
                status_code=400,
                mimetype="application/json"
            )

        class_id = int(class_id)

        # 1) Télécharger image
        img_bytes = download_url_bytes(image_url)
        bgr = bytes_to_bgr_image(img_bytes)

        conn = mysql_conn()

        # 2) Total étudiants
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS total FROM students WHERE class_id=%s", (class_id,))
            total_students = int(cur.fetchone()["total"])

        # 3) Détection visages
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

        # 4) Charger embeddings DB
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT f.student_id, f.face_encoding,
                       s.matricule, s.first_name, s.last_name
                FROM faces f
                JOIN students s ON s.id = f.student_id
                WHERE s.class_id = %s
                """,
                (class_id,)
            )
            rows = cur.fetchall()

        valid_known = []
        valid_meta = []

        for r in rows:
            e = np.frombuffer(r["face_encoding"], dtype=np.float32)

            if e.shape != (EMBED_DIM,):
                continue
            if not np.isfinite(e).all():
                continue

            n = float(np.linalg.norm(e))
            if n < 0.1 or n > 100:
                continue

            valid_known.append(e / n)
            valid_meta.append({
                "student_id": r["student_id"],
                "matricule": r["matricule"],
                "first_name": r["first_name"],
                "last_name": r["last_name"]
            })

        if not valid_known:
            raise ValueError("Aucun embedding valide en base")

        known = np.vstack(valid_known)
        meta = valid_meta

        results = []
        present_ids = set()
        att_date, att_time = now_date_time()

        # 5) Matching visage par visage
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

            sim = known @ emb
            dist = 1.0 - sim

            order = np.argsort(dist)
            best_i = int(order[0])
            best_d = float(dist[best_i])
            second_d = float(dist[order[1]]) if len(dist) > 1 else 1.0

            if best_d <= threshold and (second_d - best_d) >= MARGIN:
                m = meta[best_i]
                present_ids.add(m["student_id"])
                results.append({
                    "match": True,
                    "distance": round(best_d, 4),
                    "student": m
                })
            else:
                results.append({
                    "match": False,
                    "distance": round(best_d, 4)
                })

        present_count = len(present_ids)
        attendance_percentage = (
            round((present_count / total_students) * 100, 2)
            if total_students > 0 else 0.0
        )

        # 6) DB insert + logs
        inserted = []
        with conn.cursor() as cur:
            for sid in present_ids:
                try:
                    cur.execute(
                        """
                        INSERT INTO attendance (student_id, attendance_date, attendance_time, source)
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
                        "total_students": total_students,
                        "present_count": present_count,
                        "attendance_percentage": attendance_percentage
                    })
                )
            )

        print(f"[RECO] class={class_id} faces={len(faces)} matched={present_count}")

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
