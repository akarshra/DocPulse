from app.config import UPLOAD_DIR, SessionLocal
from app.models import File
import uuid
import os

async def upload_file(file, session_id: str):
    file_id = str(uuid.uuid4())
    file_name = file.filename
    file_type = file.content_type

    file_path = os.path.join(UPLOAD_DIR, file_id)
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    url = f"/files/{file_id}"

    db = SessionLocal()
    try:
        db_file = File(id=file_id, name=file_name, type=file_type, status="uploaded", url=url, session_id=session_id)
        db.add(db_file)
        db.commit()
        db.refresh(db_file)
    finally:
        db.close()

    return {"file_id": file_id, "status": "uploaded"}