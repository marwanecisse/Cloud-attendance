# UploadImage/__init__.py
import azure.functions as func
import json
from shared import upload_bytes_to_blob

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        img_bytes = req.get_body()
        if not img_bytes:
            return func.HttpResponse(
                json.dumps({"error": "No image bytes provided"}),
                status_code=400, mimetype="application/json"
            )

        content_type = req.headers.get("Content-Type", "image/jpeg")
        url = upload_bytes_to_blob(
            container="attendance",
            data=img_bytes,
            content_type=content_type,
            prefix="uploads"
        )

        return func.HttpResponse(
            json.dumps({"ok": True, "image_url": url}),
            status_code=200, mimetype="application/json"
        )
    except Exception as e:
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500, mimetype="application/json"
        )
