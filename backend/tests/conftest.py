import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import os
from pathlib import Path

# Ensure StaticFiles mount directory exists during test collection.
os.makedirs(os.path.join(Path(__file__).resolve().parents[1], "uploads"), exist_ok=True)

import app.main as main_module

import app.config as config_module
import app.services.upload_service as upload_module
import app.services.process_service as process_module
import app.services.chat_service as chat_module
import app.services.streaming_chat_service as streaming_module
import app.services.summary_service as summary_module
import app.services.file_service as files_module
import app.services.faiss_service as faiss_module
from app.models import Base


@pytest.fixture(autouse=True)
def isolate_backend(monkeypatch, tmp_path):
    upload_dir = tmp_path / "uploads"
    faiss_dir = tmp_path / "faiss"
    upload_dir.mkdir()
    faiss_dir.mkdir()

    monkeypatch.setattr(config_module, "UPLOAD_DIR", str(upload_dir))
    monkeypatch.setattr(config_module, "FAISS_INDEX_DIR", str(faiss_dir))

    sqlite_path = tmp_path / "test.db"
    engine = create_engine(
        f"sqlite:///{sqlite_path}",
        connect_args={"check_same_thread": False},
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    monkeypatch.setattr(config_module, "engine", engine)
    monkeypatch.setattr(config_module, "SessionLocal", SessionLocal)

    monkeypatch.setattr(upload_module, "UPLOAD_DIR", str(upload_dir))
    monkeypatch.setattr(upload_module, "SessionLocal", SessionLocal)

    monkeypatch.setattr(process_module, "UPLOAD_DIR", str(upload_dir))
    monkeypatch.setattr(process_module, "FAISS_INDEX_DIR", str(faiss_dir))
    monkeypatch.setattr(process_module, "SessionLocal", SessionLocal)

    # chat/streaming services no longer own FAISS paths; FAISS logic is in faiss_service
    monkeypatch.setattr(chat_module, "SessionLocal", SessionLocal)
    monkeypatch.setattr(streaming_module, "SessionLocal", SessionLocal)
    monkeypatch.setattr(faiss_module, "FAISS_INDEX_DIR", str(faiss_dir))

    monkeypatch.setattr(summary_module, "SessionLocal", SessionLocal)
    monkeypatch.setattr(files_module, "SessionLocal", SessionLocal)

    Base.metadata.create_all(bind=engine)

    yield


@pytest.fixture
def client():
    return TestClient(main_module.app)

