import requests
from datetime import date

URL = "http://localhost:7071/api/SendAttendanceEmail"

payload = {
    "class_id": 1,
    "attendance_date": str(date.today()),
    "total_students": 4,
    "present_count": 2,
    "attendance_percentage": 50.0,
    "present_students": [
        {"matricule": "A002", "first_name": "Justin", "last_name": "Bieber"},
        {"matricule": "A003", "first_name": "Selena", "last_name": "Gomez"}
    ]
}

r = requests.post(URL, json=payload, timeout=60)
print("STATUS:", r.status_code)
print(r.text)
