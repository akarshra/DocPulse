import asyncio
import json
from pathlib import Path

import faiss
import numpy as np

import pytest
from unittest.mock import MagicMock

import app.config as config_module
import app.services.process_service as process_module
import app.services.streaming_chat_service as streaming_module
from app.models import File


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
    """Create sidecar metadata required by app.services.faiss_service.

    Note: faiss_service deterministically couples vector_id == index in `segments`.
    """
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


def create_faiss_index_for_segments(file_id: str, *, embeddings: np.ndarray):
    """Helper: write a FAISS index aligned to the number of embeddings."""
    index = process_module.faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings.astype("float32"))
    process_module.faiss.write_index(
        index,
        str(Path(config_module.FAISS_INDEX_DIR) / f"{file_id}.index"),
    )


def test_faiss_build_index_empty_creates_index_and_metadata(tmp_path):
    # Use faiss_service paths from conftest monkeypatching.
    file_id = "faiss-empty"

    from app.services.faiss_service import build_faiss_index
    from app.services.faiss_service import load_faiss_index

    index_path, metadata_path = build_faiss_index(file_id, segments=[])

    assert Path(index_path).exists()
    assert Path(metadata_path).exists()

    index, metadata = load_faiss_index(file_id)
    # empty index stores vectors: {} without a count key
    assert metadata.get("vectors") == {}



def test_faiss_build_index_valid_writes_metadata_and_search_returns_matches():
    file_id = "faiss-basic"

    from app.services.faiss_service import build_faiss_index, search_faiss

    segments = [
        {"segment_id": "s0", "start": 0.0, "end": 1.0, "text": "Zero"},
        {"segment_id": "s1", "start": 1.0, "end": 2.0, "text": "One"},
    ]

    # Deterministic embeddings: query close to first vector (smaller L2).
    embeddings = np.array(
        [
            [0.0] + [0.0] * 767,
            [10.0] + [0.0] * 767,
        ],
        dtype="float32",
    )

    build_faiss_index(file_id, segments=segments, embeddings=embeddings)

    query = np.array([0.0] + [0.0] * 767, dtype="float32")
    results = search_faiss(file_id, query, top_k=2)

    assert len(results) == 2
    assert results[0]["segment_id"] == "s0"
    assert results[0]["start"] == 0.0
    assert results[0]["end"] == 1.0
    assert results[0]["text"] == "Zero"


def test_faiss_load_index_missing_files_raise():
    file_id = "faiss-missing"

    from app.services.faiss_service import load_faiss_index

    with pytest.raises(FileNotFoundError) as exc:
        load_faiss_index(file_id)
    assert "FAISS index not found" in str(exc.value)


def test_faiss_build_index_validation_errors():
    file_id = "faiss-validate"

    from app.services.faiss_service import build_faiss_index

    segments = [
        {"segment_id": "s0", "start": 0.0, "end": 1.0, "text": "Zero"},
        {"segment_id": "s1", "start": 1.0, "end": 2.0, "text": "One"},
    ]

    # embeddings missing
    with pytest.raises(ValueError) as exc:
        build_faiss_index(file_id, segments=segments, embeddings=None)
    assert "embeddings must be provided" in str(exc.value)

    # embeddings wrong ndim
    with pytest.raises(ValueError) as exc:
        build_faiss_index(
            file_id,
            segments=segments,
            embeddings=np.array([1, 2, 3], dtype="float32"),
        )
    assert "2D array" in str(exc.value)

    # embeddings wrong row count
    with pytest.raises(ValueError) as exc:
        build_faiss_index(
            file_id,
            segments=segments,
            embeddings=np.zeros((1, 768), dtype="float32"),
        )
    assert "row count" in str(exc.value)

    # embeddings wrong dimension
    with pytest.raises(ValueError) as exc:
        build_faiss_index(
            file_id,
            segments=segments,
            embeddings=np.zeros((2, 700), dtype="float32"),
            dimension=768,
        )
    assert "column count" in str(exc.value)


def test_faiss_search_empty_index_returns_empty():
    file_id = "faiss-search-empty"

    from app.services.faiss_service import build_faiss_index, search_faiss

    build_faiss_index(file_id, segments=[])

    query = np.zeros(768, dtype="float32")
    results = search_faiss(file_id, query, top_k=3)
    assert results == []


def test_extract_text_from_pdf_reads_text_from_document(monkeypatch):

    page_a = MagicMock(get_text=MagicMock(return_value="Page A text."))
    page_b = MagicMock(get_text=MagicMock(return_value="Page B text."))
    doc = [page_a, page_b]
    monkeypatch.setattr(process_module, "fitz", MagicMock(open=MagicMock(return_value=doc)))

    result = process_module.extract_text_from_pdf("dummy.pdf")
    assert result == "Page A text.Page B text."


def test_transcribe_audio_video_gemini_raises_without_gemini_client():
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(process_module, "gemini_client", None)
    try:
        with pytest.raises(Exception) as exc_info:
            process_module.transcribe_audio_video_gemini("dummy.mp3")
        assert hasattr(exc_info.value, "status_code")
        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Gemini API key not configured"
    finally:
        monkeypatch.undo()


def test_transcribe_audio_video_gemini_parses_json_response(tmp_path, monkeypatch):
    mock_gemini = MagicMock()
    mock_uploaded_file = MagicMock()
    mock_uploaded_file.state.name = "DONE"
    mock_uploaded_file.name = "testfile"
    mock_gemini.files.upload.return_value = mock_uploaded_file
    mock_gemini.models.generate_content.return_value = MagicMock(
        text='[{"start": 0.0, "text": "Hello"}, {"start": 1.5, "text": "World"}]'
    )
    mock_gemini.files.delete.return_value = None
    monkeypatch.setattr(process_module, "gemini_client", mock_gemini)

    temp_file = tmp_path / "audio.mp3"
    temp_file.write_bytes(b"content")

    segments = process_module.transcribe_audio_video_gemini(str(temp_file))
    assert len(segments) == 2
    assert segments[0]["start"] == 0.0
    assert segments[0]["end"] == 1.5
    assert float(segments[1]["end"]) >= float(segments[1]["start"])
    assert [seg["text"] for seg in segments] == ["Hello", "World"]
    assert all("segment_id" in seg for seg in segments)



def test_transcribe_audio_video_gemini_uses_processing_loop(tmp_path, monkeypatch):
    mock_gemini = MagicMock()
    uploading = MagicMock()
    uploading.name = "upload-1"
    uploading.state.name = "PROCESSING"
    done_file = MagicMock()
    done_file.name = "upload-1"
    done_file.state.name = "DONE"
    mock_gemini.files.upload.return_value = uploading
    mock_gemini.files.get.return_value = done_file
    mock_gemini.models.generate_content.return_value = MagicMock(text='[{"start":0.0,"text":"A"}]')
    mock_gemini.files.delete.return_value = None
    monkeypatch.setattr(process_module, "gemini_client", mock_gemini)

    temp_file = tmp_path / "audio.mp3"
    temp_file.write_bytes(b"content")

    segments = process_module.transcribe_audio_video_gemini(str(temp_file))
    assert len(segments) == 1
    # normalize_segments last-segment default: end = start + bounded(delta)
    assert segments[0]["end"] >= 1.0


def test_transcribe_audio_video_gemini_falls_back_on_invalid_json(tmp_path, monkeypatch):
    mock_gemini = MagicMock()
    uploaded_file = MagicMock()
    uploaded_file.name = "upload-2"
    uploaded_file.state.name = "DONE"
    mock_gemini.files.upload.return_value = uploaded_file
    mock_gemini.models.generate_content.return_value = MagicMock(text="not json")
    mock_gemini.files.delete.return_value = None
    monkeypatch.setattr(process_module, "gemini_client", mock_gemini)

    temp_file = tmp_path / "audio.mp3"
    temp_file.write_bytes(b"content")

    segments = process_module.transcribe_audio_video_gemini(str(temp_file))
    # Updated assertion per sidecar/stable schema requirements
    assert len(segments) == 1
    assert segments[0]["start"] == 0.0
    assert segments[0]["end"] == 1.0
    assert segments[0]["text"] == "not json"
    assert "segment_id" in segments[0]


def test_transcribe_audio_video_gemini_raises_on_failed_processing(monkeypatch):
    mock_gemini = MagicMock()
    failed_file = MagicMock()
    failed_file.name = "upload-3"
    failed_file.state.name = "FAILED"
    mock_gemini.files.upload.return_value = failed_file
    monkeypatch.setattr(process_module, "gemini_client", mock_gemini)

    with pytest.raises(Exception) as exc_info:
        process_module.transcribe_audio_video_gemini("audio.mp3")

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Gemini file processing failed"


@pytest.mark.asyncio
async def test_process_file_missing_file_raises_404():
    with pytest.raises(Exception) as exc_info:
        await process_module.process_file("missing-file", "session-x")
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "File not found"


@pytest.mark.asyncio
async def test_process_file_raises_500_when_gemini_client_not_configured(monkeypatch, tmp_path):
    file_id = "pdf-gemini-missing"
    create_file_record("session-pdf", file_id, "doc.pdf", "application/pdf", status="uploaded")
    Path(config_module.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    (Path(config_module.UPLOAD_DIR) / file_id).write_bytes(b"dummy")
    monkeypatch.setattr(process_module, "extract_text_from_pdf", lambda _: "Hello world")
    monkeypatch.setattr(process_module, "gemini_client", None)

    with pytest.raises(Exception) as exc_info:
        await process_module.process_file(file_id, "session-pdf")

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Gemini API key not configured"


@pytest.mark.asyncio
async def test_stream_chat_invalid_transcript_yields_error(monkeypatch):
    file_id = "stream-invalid"
    create_file_record(
        "session-stream",
        file_id,
        "audio.mp3",
        "audio/mpeg",
        status="ready",
        transcript=[{"text": "Hello", "start": 0.0, "end": 2.0}],
    )
    db = config_module.SessionLocal()
    try:
        record = db.query(File).filter(File.id == file_id).first()
        record.transcript = "not valid json"
        db.commit()
    finally:
        db.close()

    events = []
    async for event in streaming_module.stream_chat(file_id, "Hello", "session-stream"):
        events.append(event)

    assert len(events) == 1
    assert "Invalid transcript data" in events[0]


@pytest.mark.asyncio
async def test_stream_chat_missing_index_yields_error(monkeypatch):
    file_id = "stream-no-index"
    create_file_record(
        "session-stream",
        file_id,
        "audio.mp3",
        "audio/mpeg",
        status="ready",
        transcript=[{"text": "Hello", "start": 0.0, "end": 2.0}],
    )

    events = []
    async for event in streaming_module.stream_chat(file_id, "Hello", "session-stream"):
        events.append(event)

    assert len(events) == 1
    # faiss_service throws Index/metadata not found; streaming wraps as unexpected error
    assert "error" in events[0]
    # error is wrapped as a generic unexpected error by stream_chat exception handler
    assert "unexpected" in events[0].lower()


@pytest.mark.asyncio
async def test_stream_chat_gemini_not_configured_yields_error(monkeypatch):
    file_id = "stream-no-gemini"
    segments = [{"text": "Hello", "start": 0.0, "end": 2.0, "segment_id": "seg-0"}]
    create_file_record(
        "session-stream",
        file_id,
        "audio.mp3",
        "audio/mpeg",
        status="ready",
        transcript=[{"text": "Hello", "start": 0.0, "end": 2.0}],
    )

    # build index + sidecar
    index = process_module.faiss.IndexFlatL2(768)
    index.add(process_module.np.array([[1.0] + [0.0] * 767], dtype="float32"))
    process_module.faiss.write_index(index, str(Path(config_module.FAISS_INDEX_DIR) / f"{file_id}.index"))
    create_faiss_sidecar(file_id, segments)

    monkeypatch.setattr(streaming_module, "gemini_client", None)

    events = []
    async for event in streaming_module.stream_chat(file_id, "Hello", "session-stream"):
        events.append(event)

    assert len(events) == 1
    assert "Gemini API not configured" in events[0] or "Gemini API" in events[0]


@pytest.mark.asyncio
async def test_stream_chat_embedding_failure_yields_error(monkeypatch):
    file_id = "stream-embed-error"
    segments = [{"text": "Hello", "start": 0.0, "end": 2.0, "segment_id": "seg-0"}]
    create_file_record(
        "session-stream",
        file_id,
        "audio.mp3",
        "audio/mpeg",
        status="ready",
        transcript=[{"text": "Hello", "start": 0.0, "end": 2.0}],
    )

    index = process_module.faiss.IndexFlatL2(768)
    index.add(process_module.np.array([[1.0] + [0.0] * 767], dtype="float32"))
    process_module.faiss.write_index(index, str(Path(config_module.FAISS_INDEX_DIR) / f"{file_id}.index"))
    create_faiss_sidecar(file_id, segments)

    mock_gemini = MagicMock()
    mock_gemini.models = MagicMock()
    mock_gemini.models.embed_content.side_effect = RuntimeError("embedding failed")
    monkeypatch.setattr(streaming_module, "gemini_client", mock_gemini)

    events = []
    async for event in streaming_module.stream_chat(file_id, "Hello", "session-stream"):
        events.append(event)

    assert len(events) == 1
    assert "Failed to process question" in events[0]


@pytest.mark.asyncio
async def test_stream_chat_generate_content_error_yields_error(monkeypatch):
    file_id = "stream-gen-error"
    segments = [{"text": "Hello", "start": 0.0, "end": 2.0, "segment_id": "seg-0"}]
    create_file_record(
        "session-stream",
        file_id,
        "audio.mp3",
        "audio/mpeg",
        status="ready",
        transcript=[{"text": "Hello", "start": 0.0, "end": 2.0}],
    )

    index = process_module.faiss.IndexFlatL2(768)
    index.add(process_module.np.array([[1.0] + [0.0] * 767], dtype="float32"))
    process_module.faiss.write_index(index, str(Path(config_module.FAISS_INDEX_DIR) / f"{file_id}.index"))
    create_faiss_sidecar(file_id, segments)

    chunk = MagicMock(text="Hello")
    mock_gemini = MagicMock()
    mock_gemini.models = MagicMock()
    mock_gemini.models.embed_content.return_value = MagicMock(
        embeddings=[MagicMock(values=[1.0] + [0.0] * 767)]
    )
    mock_gemini.models.generate_content.side_effect = RuntimeError("streaming unavailable")
    monkeypatch.setattr(streaming_module, "gemini_client", mock_gemini)

    events = []
    async for event in streaming_module.stream_chat(file_id, "Hello", "session-stream"):
        events.append(event)

    assert len(events) == 1
    assert "Failed to generate response" in events[0] or "Failed" in events[0]


@pytest.mark.asyncio
async def test_stream_chat_success_with_streaming_content(monkeypatch):
    file_id = "stream-success"
    segments = [{"text": "Hello", "start": 0.0, "end": 2.0, "segment_id": "seg-0"}]
    create_file_record(
        "session-stream",
        file_id,
        "audio.mp3",
        "audio/mpeg",
        status="ready",
        transcript=[{"text": "Hello", "start": 0.0, "end": 2.0}],
    )

    index = process_module.faiss.IndexFlatL2(768)
    index.add(process_module.np.array([[1.0] + [0.0] * 767], dtype="float32"))
    process_module.faiss.write_index(index, str(Path(config_module.FAISS_INDEX_DIR) / f"{file_id}.index"))
    create_faiss_sidecar(file_id, segments)

    chunk = MagicMock(text="Hello")
    mock_gemini = MagicMock()
    mock_gemini.models = MagicMock()
    mock_gemini.models.embed_content.return_value = MagicMock(
        embeddings=[MagicMock(values=[1.0] + [0.0] * 767)]
    )
    mock_gemini.models.generate_content.return_value = [chunk]
    monkeypatch.setattr(streaming_module, "gemini_client", mock_gemini)

    events = []
    async for event in streaming_module.stream_chat(file_id, "Hello", "session-stream"):
        events.append(event)

    assert any("event: token" in e for e in events)
    assert any("event: metadata" in e for e in events)
    assert any("event: done" in e for e in events)

    # also exercise process_file path
    file_id2 = "audio-file"
    create_file_record("session-audio", file_id2, "recording.mp3", "audio/mpeg", status="uploaded")

    upload_path = Path(config_module.UPLOAD_DIR)
    upload_path.mkdir(parents=True, exist_ok=True)
    (upload_path / file_id2).write_bytes(b"dummy")

    monkeypatch.setattr(process_module, "transcribe_audio_video_gemini", lambda _: [
        {"segment_id": "seg-0", "text": "Hello", "start": 0.0, "end": 2.0},
        {"segment_id": "seg-1", "text": "World", "start": 2.0, "end": 4.0},
    ])
    mock_gemini2 = MagicMock()
    mock_gemini2.models = MagicMock()
    mock_gemini2.models.embed_content.return_value = MagicMock(embeddings=[MagicMock(values=[0.1] * 768)])
    monkeypatch.setattr(process_module, "gemini_client", mock_gemini2)

    result = await process_module.process_file(file_id2, "session-audio")
    assert result == {"status": "processed"}
    assert (Path(config_module.FAISS_INDEX_DIR) / f"{file_id2}.index").exists()


@pytest.mark.asyncio
async def test_stream_chat_yields_error_when_file_is_missing():
    events = []
    async for event in streaming_module.stream_chat("missing", "Hello", "session-x"):
        events.append(event)

    assert len(events) == 1
    assert "error" in events[0]
    assert "File not found" in events[0]


@pytest.mark.asyncio
async def test_stream_chat_succeeds_with_streaming_response(monkeypatch):
    file_id = "stream-file"
    transcript = [{"text": "Hello world", "start": 0.0, "end": 2.0}]
    create_file_record("session-stream", file_id, "audio.mp3", "audio/mpeg", status="ready", transcript=transcript)

    from app.config import FAISS_INDEX_DIR

    index = process_module.faiss.IndexFlatL2(768)
    index.add(process_module.np.array([[1.0] + [0.0] * 767], dtype="float32"))
    process_module.faiss.write_index(index, str(Path(FAISS_INDEX_DIR) / f"{file_id}.index"))
    create_faiss_sidecar(file_id, [{"segment_id": "seg-0", "text": "Hello world", "start": 0.0, "end": 2.0}])

    mock_gemini = MagicMock()
    chunk = MagicMock(text="Hello")
    mock_gemini.models = MagicMock()
    mock_gemini.models.embed_content.return_value = MagicMock(
        embeddings=[MagicMock(values=[1.0] + [0.0] * 767)]
    )
    mock_gemini.models.generate_content.return_value = [chunk]
    monkeypatch.setattr(streaming_module, "gemini_client", mock_gemini)

    events = []
    async for event in streaming_module.stream_chat(file_id, "Hello", "session-stream"):
        events.append(event)

    assert any("event: token" in e for e in events)
    assert any("event: metadata" in e for e in events)
    assert any("event: done" in e for e in events)


@pytest.mark.asyncio
async def test_stream_chat_falls_back_when_streaming_fails(monkeypatch):
    file_id = "stream-fallback"
    transcript = [{"text": "Hello world", "start": 0.0, "end": 2.0}]
    create_file_record("session-stream", file_id, "audio.mp3", "audio/mpeg", status="ready", transcript=transcript)

    from app.config import FAISS_INDEX_DIR

    index = process_module.faiss.IndexFlatL2(768)
    index.add(process_module.np.array([[1.0] + [0.0] * 767], dtype="float32"))
    process_module.faiss.write_index(index, str(Path(FAISS_INDEX_DIR) / f"{file_id}.index"))
    create_faiss_sidecar(file_id, [{"segment_id": "seg-0", "text": "Hello world", "start": 0.0, "end": 2.0}])

    mock_gemini = MagicMock()
    mock_gemini.models = MagicMock()
    mock_gemini.models.embed_content.return_value = MagicMock(
        embeddings=[MagicMock(values=[1.0] + [0.0] * 767)]
    )
    mock_gemini.models.generate_content.side_effect = [
        RuntimeError("streaming unavailable"),
        MagicMock(text="Hello world."),
    ]
    monkeypatch.setattr(streaming_module, "gemini_client", mock_gemini)

    events = []
    async for event in streaming_module.stream_chat(file_id, "Hello", "session-stream"):
        events.append(event)

    assert any("event: token" in e for e in events)
    assert any("event: metadata" in e for e in events)
    assert any("event: done" in e for e in events)

