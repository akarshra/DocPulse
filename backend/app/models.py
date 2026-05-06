from sqlalchemy import Column, Integer, String, DateTime, Text
from app.config import Base
from datetime import datetime

class File(Base):
    __tablename__ = "files"

    id = Column(String, primary_key=True, index=True)
    name = Column(String)
    type = Column(String)
    status = Column(String, default="uploaded")
    transcript = Column(Text)
    url = Column(String)
    session_id = Column(String, index=True)