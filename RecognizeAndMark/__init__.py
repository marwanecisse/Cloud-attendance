import azure.functions as func
import json
import numpy as np

from shared import (
    mysql_conn, face_detect_azure,
    crop_face, embed_face,
    now_date_time, download_url_bytes, bytes_to_bgr_image
)

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
        image_url = body["image_url"]
        threshold = float(body.get("threshold", 0.35))
        request_id = body.get("request_id")

        # ✅ class_id requis pour calculer le pourcentage
        class_id = body.get("class_id")
        if not class_id:
            return func.HttpResponse(
                json.dumps({"error": "class_id is required to compute percentage"}),
                status_code=400, mimetype="application/json"
            )
        class_id = int(class_id)

        # 1) Télécharger la photo de groupe depuis Blob
        img_bytes = download_url_bytes(image_url)
        bgr = bytes_to_bgr_image(img_bytes)

        conn = mysql_conn()

        # ✅ 1bis) Total étudiants dans la classe
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS total FROM students WHERE class_id=%s", (class_id,))
            total_students = int(cur.fetchone()["total"])

        # 2) Detect multi-visages
        faces = face_detect_azure(img_bytes)
        if len(faces) == 0:
            return func.HttpResponse(
                json.dumps({
                    "ok": True,
                    "class_id": class_id,
                    "faces_detected": 0,
                    "threshold": threshold,
                    "total_students": total_students,
                    "present_count": 0,
                    "attendance_percentage": 0.0,
                    "marked_present_student_ids": [],
                    "results": []
                }),
                status_code=200, mimetype="application/json"
            )

        # 3) Charger encodages connus (filtrés par classe)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT f.student_id, f.face_encoding, s.matricule, s.first_name, s.last_name
                FROM faces f
                JOIN students s ON s.id = f.student_id
                WHERE s.class_id = %s
            """, (class_id,))
            rows = cur.fetchall()

        if not rows:
            return func.HttpResponse(
                json.dumps({"error": "Aucun visage enregistré pour cette classe", "class_id": class_id}),
                status_code=400, mimetype="application/json"
            )

        known = np.vstack([np.frombuffer(r["face_encoding"], dtype=np.float32) for r in rows])
        meta = [{
            "student_id": r["student_id"],
            "matricule": r["matricule"],
            "first_name": r["first_name"],
            "last_name": r["last_name"]
        } for r in rows]

        results = []
        present_ids = set()
        att_date, att_time = now_date_time()

        # 4) Match visage par visage
        for f in faces:
            crop = crop_face(bgr, f["faceRectangle"])
            emb = embed_face(crop)

            denom = (np.linalg.norm(known, axis=1) * (np.linalg.norm(emb) + 1e-10)) + 1e-10
            sim = (known @ emb) / denom
            dist = 1.0 - sim
            best_i = int(np.argmin(dist))
            best_d = float(dist[best_i])
            if best_d < 0:
                best_d = 0.0

            if best_d <= threshold:
                m = meta[best_i]
                present_ids.add(m["student_id"])
                results.append({"match": True, "distance": best_d, "student": m})
            else:
                results.append({"match": False, "distance": best_d})

        # ✅ Calcul du pourcentage (basé sur reconnus uniques)
        present_count = len(present_ids)
        attendance_percentage = 0.0
        if total_students > 0:
            attendance_percentage = round((present_count / total_students) * 100, 2)

        # 5) DB: insert attendance + log
        inserted = []
        with conn.cursor() as cur:
            for sid in present_ids:
                try:
                    cur.execute(
                        "INSERT INTO attendance (student_id, attendance_date, attendance_time, source) "
                        "VALUES (%s,%s,%s,'FACE')",
                        (sid, att_date, att_time)
                    )
                    inserted.append(sid)
                except Exception:
                    # doublon même jour = normal (uq_attendance_student_day)
                    pass

            cur.execute(
                "INSERT INTO recognition_logs (request_id, faces_detected, matched_students, payload_meta) "
                "VALUES (%s,%s,%s,%s)",
                (request_id, len(faces), len(inserted),
                 json.dumps({"image_url": image_url, "class_id": class_id,
                             "total_students": total_students, "present_count": present_count,
                             "attendance_percentage": attendance_percentage}))
            )

        return func.HttpResponse(
            json.dumps({
                "ok": True,
                "class_id": class_id,
                "faces_detected": len(faces),
                "threshold": threshold,
                "total_students": total_students,
                "present_count": present_count,
                "attendance_percentage": attendance_percentage,
                "marked_present_student_ids": inserted,
                "results": results
            }),
            status_code=200, mimetype="application/json"
        )

    except Exception as e:
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500, mimetype="application/json"
        )
