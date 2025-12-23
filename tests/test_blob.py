from shared import upload_bytes_to_blob

with open("YoonchaeJeong.jpg", "rb") as f:
    url = upload_bytes_to_blob(
        container="attendance",
        data=f.read(),
        content_type="image/jpeg",
        prefix="test"
    )

print("URL:", url)
