import azure.functions as func
import json
from io import BytesIO
from datetime import date
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from shared import upload_bytes_to_blob

def build_pdf_bytes(class_id, attendance_date, total_students, present_count, attendance_percentage, present_students):
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    y = height - 60
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, "Rapport de présence")
    y -= 30

    c.setFont("Helvetica", 12)
    c.drawString(50, y, f"Classe ID : {class_id}")
    y -= 18
    c.drawString(50, y, f"Date : {attendance_date}")
    y -= 18
    c.drawString(50, y, f"Présents : {present_count}/{total_students}  ({attendance_percentage}%)")
    y -= 30

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Liste des présents :")
    y -= 18

    c.setFont("Helvetica", 11)
    if not present_students:
        c.drawString(60, y, "- Aucun")
        y -= 16
    else:
        for s in present_students:
            line = f"- {s.get('matricule','')} {s.get('first_name','')} {s.get('last_name','')}".strip()
            c.drawString(60, y, line)
            y -= 16
            if y < 60:
                c.showPage()
                y = height - 60
                c.setFont("Helvetica", 11)

    c.showPage()
    c.save()
    return buf.getvalue()

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()

        class_id = body.get("class_id")
        attendance_date = body.get("attendance_date") or str(date.today())

        # ✅ validations + conversions robustes
        if not class_id:
            return func.HttpResponse(
                json.dumps({"error": "class_id is required"}),
                status_code=400, mimetype="application/json"
            )

        total_students = int(body.get("total_students", 0))
        present_count = int(body.get("present_count", 0))
        attendance_percentage = float(body.get("attendance_percentage", 0.0))
        present_students = body.get("present_students", [])

        # Générer PDF
        pdf_bytes = build_pdf_bytes(
            class_id=class_id,
            attendance_date=attendance_date,
            total_students=total_students,
            present_count=present_count,
            attendance_percentage=attendance_percentage,
            present_students=present_students
        )

        # Upload vers Blob
        pdf_url = upload_bytes_to_blob(
            container="attendance",
            data=pdf_bytes,
            content_type="application/pdf",
            prefix=f"reports/class_{class_id}"
        )

        return func.HttpResponse(
            json.dumps({"ok": True, "pdf_url": pdf_url}),
            status_code=200, mimetype="application/json"
        )

    except Exception as e:
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500, mimetype="application/json"
        )
