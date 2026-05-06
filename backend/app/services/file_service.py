from app.config import SessionLocal
from app.models import File

async def get_files(session_id: str):
    db = SessionLocal()
    try:
        files = db.query(File).filter(File.session_id == session_id).all()
        result = [{"id": f.id, "name": f.name, "type": f.type, "status": f.status, "url": f.url} for f in files]
        return result
    finally:
        db.close()