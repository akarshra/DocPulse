from fastapi import HTTPException
from app.config import UPLOAD_DIR, SessionLocal, gemini_client, FAISS_INDEX_DIR
from app.models import File

import fitz  # PyMuPDF
import faiss
import numpy as np

import json
import os
import time
import uuid
from typing import Any, Dict, List, Optional


def extract_text_from_pdf(file_path: str) -> str:
    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text


def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip())
    except Exception:
        return None


def normalize_segments(
    segments: Any,
    *,
    duration_estimate_for_last: float = 5.0,
    last_min_end_delta: float = 1.0,
    last_max_end_delta: float = 10.0,
) -> List[Dict[str, Any]]:
    """Validate + normalize transcription segments into a stable schema.

    Required output schema per segment:
      {
        "segment_id": <uuid>,
        "start": float,  # seconds
        "end": float,    # seconds
        "text": str
      }

    Validation / normalization rules:
    - start/end must be numeric (convert string -> float if possible)
    - start >= 0
    - end >= start
    - if end is missing/None, compute it using next segment start
    - if end is missing and it is last segment, set end = start + bounded(duration_estimate_for_last)
    - if text is missing or empty, skip segment
    - if segment invalid, skip it

    All timestamps are treated as seconds.
    """

    if not isinstance(segments, list):
        return []

    candidates: List[Dict[str, Any]] = []

    # Pre-filter + parse
    for seg in segments:
        if not isinstance(seg, dict):
            continue

        raw_text = seg.get("text")
        if raw_text is None:
            continue
        text = str(raw_text).strip()
        if not text:
            continue

        start = _safe_float(seg.get("start"))
        if start is None or start < 0:
            continue

        end = _safe_float(seg.get("end"))
        if end is not None and end < start:
            continue

        candidates.append({"text": text, "start": start, "end": end})

    if not candidates:
        return []

    normalized: List[Dict[str, Any]] = []
    for i, cand in enumerate(candidates):
        start = float(cand["start"])
        end = cand["end"]

        if end is None:
            if i < len(candidates) - 1:
                next_start = float(candidates[i + 1]["start"])
                end = next_start
            else:
                delta = float(duration_estimate_for_last)
                delta = max(last_min_end_delta, min(last_max_end_delta, delta))
                end = start + delta

        end = float(end)

        # Defensive validation
        if start < 0 or end < start:
            continue

        normalized.append(
            {
                "segment_id": str(uuid.uuid4()),
                "start": start,
                "end": end,
                "text": cand["text"],
            }
        )

    return normalized


def transcribe_audio_video_gemini(file_path: str, mime_type: str = "audio/mpeg") -> List[Dict[str, Any]]:
    """Use Gemini File API to upload media, wait for processing, and request a timestamped transcript."""

    if not gemini_client:
        raise HTTPException(status_code=500, detail="Gemini API key not configured")

    uploaded_file = gemini_client.files.upload(file=file_path, config={'mime_type': mime_type})

    # Wait for processing
    while uploaded_file.state.name == "PROCESSING":
        time.sleep(2)
        uploaded_file = gemini_client.files.get(name=uploaded_file.name)

    if uploaded_file.state.name == "FAILED":
        raise HTTPException(status_code=500, detail="Gemini file processing failed")

    prompt = (
        "Please provide a detailed transcript of this media file. "
        "For each spoken segment, provide the start time in seconds and the text. "
        "Format the output as a strict JSON array of objects, where each object has "
        "'start' (float) and 'text' (string). "
        "Do not output any markdown formatting, only the raw JSON array."
    )

    response = gemini_client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=[uploaded_file, prompt],
    )

    # Cleanup uploaded file
    gemini_client.files.delete(name=uploaded_file.name)

    try:
        # Clean up potential markdown fences
        json_str = (
            response.text.replace("```json\n", "")
            .replace("```\n", "")
            .replace("```", "")
            .strip()
        )
        raw_segments = json.loads(json_str)

        normalized = normalize_segments(raw_segments)
        if not normalized:
            # Parsing succeeded but normalization filtered everything
            return [
                {
                    "segment_id": str(uuid.uuid4()),
                    "start": 0.0,
                    "end": 1.0,
                    "text": str(response.text).strip(),
                }
            ]

        return normalized
    except Exception:
        # Fallback to single segment
        return [
            {
                "segment_id": str(uuid.uuid4()),
                "start": 0.0,
                "end": 1.0,
                "text": str(response.text).strip(),
            }
        ]


async def process_file(file_id: str, session_id: str):
    db = SessionLocal()
    try:
        db_file = db.query(File).filter(File.id == file_id, File.session_id == session_id).first()
        if not db_file:
            raise HTTPException(status_code=404, detail="File not found")

        file_type = db_file.type
        file_path = os.path.join(UPLOAD_DIR, file_id)

        # Verify file exists
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"File not found at {file_path}")

        if file_type == "application/pdf":
            text = extract_text_from_pdf(file_path)

            # For PDF, create segments by splitting text into chunks.
            # Note: these timestamps are character-offset based and playback is disabled on the frontend.
            chunk_size = 1000
            segments: List[Dict[str, Any]] = []
            for i in range(0, len(text), chunk_size):
                segments.append(
                    {
                        "segment_id": str(uuid.uuid4()),
                        "text": text[i : i + chunk_size],
                        "start": float(i),
                        "end": float(i + chunk_size),
                    }
                )

        elif file_type.startswith("audio/") or file_type.startswith("video/"):
            # normalize_segments() guarantees seconds + stable schema for audio/video.
            segments = transcribe_audio_video_gemini(file_path, file_type)

        else:
            raise HTTPException(status_code=400, detail="Unsupported file type")

        # Save transcript to DB (stable schema)
        db_file.transcript = json.dumps(segments)
        db_file.status = "processing"
        db.commit()

        # Build embeddings using Gemini
        if not gemini_client:
            raise HTTPException(status_code=500, detail="Gemini API key not configured")

        texts = [seg["text"] for seg in segments]
        embeddings = []
        try:
            for text in texts:
                result = gemini_client.models.embed_content(
                    model="text-embedding-004",
                    contents=text,
                )
                embeddings.append(result.embeddings[0].values)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Embedding generation failed: {str(e)}")

        embeddings = np.array(embeddings).astype("float32")

        # Dynamically determine dimension from actual embeddings
        if embeddings.shape[0] == 0:
            raise HTTPException(status_code=500, detail="No embeddings generated")

        dimension = embeddings.shape[1]

        # Create FAISS index
        index = faiss.IndexFlatL2(dimension)
        index.add(embeddings)

        # Save index
        index_path = os.path.join(FAISS_INDEX_DIR, f"{file_id}.index")
        try:
            faiss.write_index(index, index_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save FAISS index: {str(e)}")

        # Update status
        db_file.status = "ready"
        db.commit()

        return {"status": "processed"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File processing failed: {str(e)}")
    finally:
        db.close()
