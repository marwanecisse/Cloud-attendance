import requests

# URL de ta fonction RegisterStudent (locale ou cloud)
url = "http://localhost:7071/api/RegisterStudent"

# Exemple d'étudiant à enregistrer
data = {
    "matricule": "2025001",
    "first_name": "Alice",
    "last_name": "Dupont",
    "class_id": 1,
    "image_url": "https://attendanceimage.blob.core.windows.net/attendance/test/3ed49741be0e4d9cafb904cfd097c950.jpg"
}

resp = requests.post(url, json=data)

if resp.status_code == 200:
    print("Réponse :", resp.json())
else:
    print("Erreur :", resp.status_code, resp.text)
