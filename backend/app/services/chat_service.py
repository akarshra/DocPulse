from fastapi import HTTPException

import json
import numpy as np

from app.config import SessionLocal, gemini_client
from app.models import File
from app.services.faiss_service import search_faiss


async def chat(data, session_id):
    file_id = data["file_id"]
    question = data["question"]

    db = SessionLocal()
    try:
        db_file = db.query(File).filter(File.id == file_id, File.session_id == session_id).first()
        if not db_file:
            raise HTTPException(status_code=404, detail="File not found")

        # Keep transcript loading for backward compatibility (may be used by other logic/tests)
        _transcript = json.loads(db_file.transcript) if db_file.transcript else []

        if not gemini_client:
            raise HTTPException(status_code=500, detail="Gemini API key not configured")

        # Embed the question
        embed_response = gemini_client.models.embed_content(
            model="text-embedding-004",
            contents=question,
        )
        query_embedding = np.array([embed_response.embeddings[0].values]).astype("float32")

        # FAISS search with deterministic coupling via sidecar metadata
        matches = search_faiss(file_id, query_embedding, top_k=3)

        # Evidence text for LLM prompt (top match)
        evidence_text = matches[0]["text"] if matches else ""

        # Context for LLM prompt (still include multiple matches)
        context = "\n".join([m.get("text", "") for m in matches if m.get("text")])

        prompt = (
            f"Context: {context}\n\n"
            f"Question: {question}\n\n"
            f"Answer based on the context provided: {evidence_text}"
        )

        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
        )
        answer = response.text

        # timestamp_ranges derived ONLY from FAISS sidecar metadata
        timestamp_ranges = []

        # If file is PDF, do not return playback timestamps.
        is_pdf = db_file.type == "application/pdf"
        if not is_pdf:
            for m in matches:
                start_time = m.get("start")
                end_time = m.get("end")

                if isinstance(start_time, (int, float)) and isinstance(end_time, (int, float)):
                    start_time_f = float(start_time)
                    end_time_f = float(end_time)

                    if start_time_f >= 0 and end_time_f >= start_time_f:
                        timestamp_ranges.append(
                            {
                                "segment_id": m.get("segment_id"),
                                "start_time": start_time_f,
                                "end_time": end_time_f,
                                "text": m.get("text"),
                            }
                        )

        return {
            "answer": answer,
            "timestamp_ranges": timestamp_ranges,
            "source_file": file_id,
        }
    finally:
        db.close()

