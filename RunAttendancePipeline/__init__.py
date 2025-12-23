# RunAttendancePipeline/__init__.py
import azure.functions as func
import json
import os
from datetime import date
import requests

def base_url():
    # Local: http://localhost:7071/api
    return os.getenv("FUNCTION_BASE_URL", "http://localhost:7071/api").rstrip("/")

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()

        class_id = body["class_id"]
        image_url = body["image_url"]
        threshold = float(body.get("threshold", 0.35))
        request_id = body.get("request_id", "pipeline-001")
        attendance_date = body.get("attendance_date", str(date.today()))

        b = base_url()

        # 1) Recognize + Mark
        r1 = requests.post(
            f"{b}/RecognizeAndMark",
            json={
                "class_id": class_id,
                "image_url": image_url,
                "threshold": threshold,
                "request_id": request_id
            },
            timeout=240
        )
        r1.raise_for_status()
        raw = r1.json()

        if not raw.get("ok"):
            raise ValueError(f"Recognition failed: {raw.get('error')}")

        data = raw.get("data", {})

        reco = {
            "faces_detected": data.get("faces_detected", 0),
            "total_students": data.get("total_students", 0),
            "present_count": data.get("present_count", 0),
            "attendance_percentage": data.get("attendance_percentage", 0.0),
            "results": data.get("results", [])
        }

        # Extraire liste des présents (uniques)
        present_map = {}
        for item in reco.get("results", []):
            if item.get("match") and item.get("student"):
                s = item["student"]
                sid = s.get("student_id")
                if sid and sid not in present_map:
                    present_map[sid] = {
                        "matricule": s.get("matricule"),
                        "first_name": s.get("first_name"),
                        "last_name": s.get("last_name")
                    }
        present_students = list(present_map.values())

        # 2) Generate PDF
        r2 = requests.post(
            f"{b}/GenerateAttendancePdf",
            json={
                "class_id": class_id,
                "attendance_date": attendance_date,
                "total_students": reco.get("total_students", 0),
                "present_count": reco.get("present_count", 0),
                "attendance_percentage": reco.get("attendance_percentage", 0.0),
                "present_students": present_students
            },
            timeout=120
        )
        r2.raise_for_status()
        pdf = r2.json()
        pdf_url = pdf.get("pdf_url")

        # 3) Send Email (avec pdf_url)
        r3 = requests.post(
            f"{b}/SendAttendanceEmail",
            json={
                "class_id": class_id,
                "attendance_date": attendance_date,
                "total_students": reco.get("total_students", 0),
                "present_count": reco.get("present_count", 0),
                "attendance_percentage": reco.get("attendance_percentage", 0.0),
                "present_students": present_students,
                "pdf_url": pdf_url
            },
            timeout=120
        )
        r3.raise_for_status()
        mail = r3.json()

        # réponse finale au frontend
        return func.HttpResponse(
            json.dumps({
                "ok": True,
                "class_id": class_id,
                "image_url": image_url,
                "recognition": reco,
                "pdf_url": pdf_url,
                "email": mail
            }),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        return func.HttpResponse(
            json.dumps({
                "ok": False,
                "error": str(e),
                "recognition": {
                    "faces_detected": 0,
                    "total_students": 0,
                    "present_count": 0,
                    "attendance_percentage": 0.0,
                    "results": []
                },
                "pdf_url": None,
                "email": None
            }),
            status_code=200,
            mimetype="application/json"
        )
