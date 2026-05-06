import json
from io import BytesIO
from pathlib import Path

import faiss
import numpy as np
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

import app.config as config_module
from app.main import app
from app.models import File

client = TestClient(app)


def create_file_record(session_id, file_id, name, file_type, status="uploaded", transcript=None, url=None):
    db = config_module.SessionLocal()
    try:
        db_file = File(
            id=file_id,
            name=name,
            type=file_type,
            status=status,
            transcript=json.dumps(transcript) if transcript is not None else None,
            url=url or f"/files/{file_id}",
            session_id=session_id,
        )
        db.add(db_file)
        db.commit()
        return db_file
    finally:
        db.close()


def create_faiss_sidecar(file_id: str, segments, *, dimension: int = 768):
    sidecar_path = Path(config_module.FAISS_INDEX_DIR) / f"{file_id}.json"
    vectors = {}
    for i, seg in enumerate(segments):
        vectors[str(i)] = {
            "segment_id": seg.get("segment_id", f"seg-{i}"),
            "start": float(seg["start"]),
            "end": float(seg["end"]),
            "text": seg["text"],
        }
    sidecar = {"dimension": dimension, "count": len(segments), "vectors": vectors}
    sidecar_path.write_text(json.dumps(sidecar), encoding="utf-8")


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_upload_pdf_creates_file_record_and_returns_id():
    file_content = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"
    files = {"file": ("document.pdf", BytesIO(file_content), "application/pdf")}

    response = client.post("/api/upload", files=files, headers={"X-Session-ID": "session-1"})
    assert response.status_code == 200

    payload = response.json()
    assert payload["status"] == "uploaded"
    assert "file_id" in payload

    file_id = payload["file_id"]
    db = config_module.SessionLocal()
    try:
        stored = db.query(File).filter(File.id == file_id).first()
        assert stored is not None
        assert stored.type == "application/pdf"
        assert stored.session_id == "session-1"
    finally:
        db.close()


def test_upload_audio_creates_file_record():
    files = {"file": ("recording.mp3", BytesIO(b"audio bytes"), "audio/mpeg")}
    response = client.post("/api/upload", files=files, headers={"X-Session-ID": "audio-session"})
    assert response.status_code == 200

    payload = response.json()
    assert payload["status"] == "uploaded"
    assert "file_id" in payload

    file_id = payload["file_id"]
    db = config_module.SessionLocal()
    try:
        stored = db.query(File).filter(File.id == file_id).first()
        assert stored.type == "audio/mpeg"
        assert stored.session_id == "audio-session"
    finally:
        db.close()


def test_upload_video_creates_file_record():
    files = {"file": ("clip.mp4", BytesIO(b"video bytes"), "video/mp4")}
    response = client.post("/api/upload", files=files, headers={"X-Session-ID": "video-session"})
    assert response.status_code == 200

    payload = response.json()
    assert payload["status"] == "uploaded"
    assert "file_id" in payload

    file_id = payload["file_id"]
    db = config_module.SessionLocal()
    try:
        stored = db.query(File).filter(File.id == file_id).first()
        assert stored.type == "video/mp4"
        assert stored.session_id == "video-session"
    finally:
        db.close()


def test_files_endpoint_only_returns_user_session_files():
    create_file_record("session-a", "file-a", "a.pdf", "application/pdf")
    create_file_record("session-b", "file-b", "b.pdf", "application/pdf")

    response = client.get("/api/files", headers={"X-Session-ID": "session-a"})
    assert response.status_code == 200
    assert response.json() == [{"id": "file-a", "name": "a.pdf", "type": "application/pdf", "status": "uploaded", "url": "/files/file-a"}]


def test_process_pdf_generates_faiss_index_and_marks_ready(monkeypatch):
    file_id = "pdf-file"
    create_file_record("session-2", file_id, "doc.pdf", "application/pdf", status="uploaded")

    from app.config import UPLOAD_DIR, FAISS_INDEX_DIR

    Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    with open(Path(UPLOAD_DIR) / file_id, "wb") as f:
        f.write(b"dummy content")

    mock_gemini = MagicMock()
    mock_gemini.models = MagicMock()
    mock_gemini.models.embed_content.return_value = MagicMock(embeddings=[MagicMock(values=[0.1] * 768)])
    monkeypatch.setattr("app.services.process_service.gemini_client", mock_gemini)
    monkeypatch.setattr("app.services.process_service.extract_text_from_pdf", lambda _: "A" * 2100)

    response = client.post(f"/api/process/{file_id}", headers={"X-Session-ID": "session-2"})
    assert response.status_code == 200
    assert response.json() == {"status": "processed"}

    db = config_module.SessionLocal()
    try:
        stored = db.query(File).filter(File.id == file_id).first()
        assert stored.status == "ready"
        assert stored.transcript is not None
    finally:
        db.close()

    assert (Path(FAISS_INDEX_DIR) / f"{file_id}.index").exists()


def test_process_unsupported_file_type_returns_400():
    file_id = "unsupported-file"
    create_file_record("session-3", file_id, "readme.txt", "text/plain", status="uploaded")
    response = client.post(f"/api/process/{file_id}", headers={"X-Session-ID": "session-3"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported file type"


def test_chat_endpoint_returns_answer_with_timestamp_ranges(monkeypatch):
    file_id = "chat-file"
    transcript = [
        {"text": "Hello world", "start": 0.0, "end": 2.0},
        {"text": "Second segment", "start": 2.0, "end": 4.0},
    ]
    create_file_record("session-chat", file_id, "audio.mp3", "audio/mpeg", status="ready", transcript=transcript)

    from app.config import FAISS_INDEX_DIR

    index = faiss.IndexFlatL2(768)
    index.add(np.array([[1.0] + [0.0] * 767, [0.0] + [0.0] * 767], dtype="float32"))
    faiss.write_index(index, str(Path(FAISS_INDEX_DIR) / f"{file_id}.index"))

    # sidecar metadata required by chat_service
    create_faiss_sidecar(file_id, [
        {"segment_id": "seg-0", "start": 0.0, "end": 2.0, "text": "Hello world"},
        {"segment_id": "seg-1", "start": 2.0, "end": 4.0, "text": "Second segment"},
    ])

    mock_gemini = MagicMock()
    mock_gemini.models = MagicMock()
    mock_gemini.models.embed_content.return_value = MagicMock(embeddings=[MagicMock(values=[1.0] + [0.0] * 767)])
    mock_gemini.models.generate_content.return_value = MagicMock(text="This is the answer.")
    monkeypatch.setattr("app.services.chat_service.gemini_client", mock_gemini)

    response = client.post(
        "/api/chat",
        json={"file_id": file_id, "question": "What is the content?"},
        headers={"X-Session-ID": "session-chat"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] == "This is the answer."
    # timestamp_ranges now include FAISS sidecar text + segment_id
    assert payload["timestamp_ranges"] == [
        {"segment_id": "seg-0", "start_time": 0.0, "end_time": 2.0, "text": "Hello world"},
        {"segment_id": "seg-1", "start_time": 2.0, "end_time": 4.0, "text": "Second segment"},
    ]
    assert payload["source_file"] == file_id


def test_summary_endpoint_returns_summary_and_timestamp_range(monkeypatch):
    file_id = "summary-file"
    transcript = [
        {"text": "First line", "start": 0.0, "end": 3.0},
        {"text": "Last line", "start": 3.0, "end": 6.0},
    ]
    create_file_record("session-sum", file_id, "video.mp4", "video/mp4", status="ready", transcript=transcript)

    mock_gemini = MagicMock()
    mock_gemini.models = MagicMock()
    mock_gemini.models.generate_content.return_value = MagicMock(text="A concise summary.")
    monkeypatch.setattr("app.services.summary_service.gemini_client", mock_gemini)

    response = client.get(f"/api/summary/{file_id}", headers={"X-Session-ID": "session-sum"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"] == "A concise summary."
    assert payload["timestamp_range"] == {"start_time": 0.0, "end_time": 6.0}
    assert payload["source_file"] == file_id


def test_chat_endpoint_missing_file_returns_404():
    response = client.post(
        "/api/chat",
        json={"file_id": "missing", "question": "Q?"},
        headers={"X-Session-ID": "session-chat"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "File not found"


def test_summary_endpoint_missing_file_returns_404():
    response = client.get("/api/summary/missing", headers={"X-Session-ID": "session-sum"})
    assert response.status_code == 404
    assert response.json()["detail"] == "File not found"


def test_summary_endpoint_without_gemini_client_returns_500(monkeypatch):
    file_id = "summary-no-gemini"
    transcript = [{"text": "Hello", "start": 0.0, "end": 1.0}]
    create_file_record("session-sum", file_id, "audio.mp3", "audio/mpeg", status="ready", transcript=transcript)
    monkeypatch.setattr("app.services.summary_service.gemini_client", None)

    response = client.get(f"/api/summary/{file_id}", headers={"X-Session-ID": "session-sum"})
    assert response.status_code == 500
    assert response.json()["detail"] == "Gemini API key not configured"

