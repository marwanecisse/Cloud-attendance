# SendAttendanceEmail/__init__.py
import azure.functions as func
import json, os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, TrackingSettings, ClickTracking

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()

        class_id = body.get("class_id")
        attendance_date = body.get("attendance_date")
        present_students = body.get("present_students", [])
        total_students = body.get("total_students")
        present_count = body.get("present_count")
        attendance_percentage = body.get("attendance_percentage")

        # ✅ lien PDF optionnel
        pdf_url = body.get("pdf_url")

        api_key = os.getenv("SENDGRID_API_KEY")
        from_email = os.getenv("SENDGRID_FROM_EMAIL")
        to_email = os.getenv("SENDGRID_TO_EMAIL")

        if not api_key or not from_email or not to_email:
            return func.HttpResponse(
                json.dumps({"error": "Missing SendGrid env vars (SENDGRID_API_KEY/FROM/TO)"}),
                status_code=500, mimetype="application/json"
            )

        if not class_id or not attendance_date:
            return func.HttpResponse(
                json.dumps({"error": "class_id and attendance_date are required"}),
                status_code=400, mimetype="application/json"
            )

        subject = f"Liste de présence - Classe {class_id} - {attendance_date}"

        lines = [
            f"Classe: {class_id}",
            f"Date: {attendance_date}",
            f"Présents: {present_count}/{total_students} ({attendance_percentage}%)",
            "",
            "Liste des présents:"
        ]

        if not present_students:
            lines.append("- Aucun")
        else:
            for s in present_students:
                line = f"- {s.get('matricule','')} {s.get('first_name','')} {s.get('last_name','')}".strip()
                lines.append(line)

        if pdf_url:
            lines.append("")
            lines.append(f"Rapport PDF (lien direct): {pdf_url}")

        content = "\n".join(lines)

        message = Mail(
            from_email=from_email,
            to_emails=to_email,
            subject=subject,
            plain_text_content=content
        )

        # ✅ IMPORTANT : désactive le click-tracking (sinon SendGrid remplace ton lien)
        message.tracking_settings = TrackingSettings(
            click_tracking=ClickTracking(enable=False, enable_text=False)
        )

        sg = SendGridAPIClient(api_key)
        resp = sg.send(message)

        return func.HttpResponse(
            json.dumps({"ok": True, "sendgrid_status": resp.status_code}),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
