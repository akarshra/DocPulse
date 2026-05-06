from fastapi import HTTPException
from app.config import SessionLocal, gemini_client
from app.models import File
import json

async def get_summary(file_id, session_id):
    db = SessionLocal()
    try:
        db_file = db.query(File).filter(File.id == file_id, File.session_id == session_id).first()
        if not db_file:
            raise HTTPException(status_code=404, detail="File not found")

        transcript = json.loads(db_file.transcript)
        text = "\n".join([seg["text"] for seg in transcript])

        if not gemini_client:
            raise HTTPException(status_code=500, detail="Gemini API key not configured")

        prompt = f"Summarize the following text in a clear, structured way. Highlight the key takeaways:\n\n{text}"

        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=prompt
        )
        summary = response.text

        # Calculate timestamp range if available (for audio/video files)
        timestamp_range = None

        # Check if file is audio/video (has real timestamps) vs PDF (has character offsets)
        is_media_file = db_file.type and (
            db_file.type.startswith("audio/") or db_file.type.startswith("video/")
        )

        if is_media_file and transcript and len(transcript) > 0:
            first_seg = transcript[0]
            last_seg = transcript[-1]

            # For audio/video files, get the full duration
            if "start" in first_seg and "end" in last_seg:
                start_val = first_seg["start"]
                end_val = last_seg["end"]

                if isinstance(start_val, (int, float)) and isinstance(end_val, (int, float)):
                    timestamp_range = {
                        "start_time": float(start_val),
                        "end_time": float(end_val)
                    }

        return {
            "summary": summary,
            "timestamp_range": timestamp_range,
            "source_file": file_id
        }
    finally:
        db.close()
