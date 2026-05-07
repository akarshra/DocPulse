from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from app.services.upload_service import upload_file
from app.services.process_service import process_file
from app.services.chat_service import chat
from app.services.streaming_chat_service import stream_chat
from app.services.summary_service import get_summary
from app.services.file_service import get_files
from app.config import engine, Base

app = FastAPI(title="DocPulse API", description="AI-powered Document & Multimedia Q&A API")

app.add_middleware(
    CORSMiddleware,
    # Allow all origins for development; restrict in production
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.mount("/files", StaticFiles(directory="uploads"), name="files")

# Create database tables
Base.metadata.create_all(bind=engine)

def get_session_id(x_session_id: str = Header(None), session_id: str = None):
    # Accept session ID from header or query parameter (for EventSource compatibility)
    sid = x_session_id or session_id
    if not sid:
        raise HTTPException(status_code=400, detail="X-Session-ID header or session_id query parameter required")
    return sid

@app.post("/api/upload")
async def upload(file: UploadFile = File(...), session_id: str = Depends(get_session_id)):
    return await upload_file(file, session_id)

@app.post("/api/process/{file_id}")
async def process(file_id: str, session_id: str = Depends(get_session_id)):
    return await process_file(file_id, session_id)

@app.post("/api/chat")
async def chat_endpoint(data: dict, session_id: str = Depends(get_session_id)):
    return await chat(data, session_id)

@app.get("/api/chat/stream")
async def chat_stream(
    file_id: str,
    question: str,
    session_id: str = Depends(get_session_id)
):
    """
    Stream chat response token-by-token using Server-Sent Events (SSE).

    Query Parameters:
    - file_id: ID of the file to ask about
    - question: User's question
    - X-Session-ID: Session ID (header)

    Returns: SSE stream with events: token, metadata, done, error
    """
    return StreamingResponse(
        stream_chat(file_id, question, session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )

@app.get("/api/summary/{file_id}")
async def summary(file_id: str, session_id: str = Depends(get_session_id)):
    return await get_summary(file_id, session_id)

@app.get("/api/files")
async def files(session_id: str = Depends(get_session_id)):
    return await get_files(session_id)

@app.get("/health")
async def health():
    return {"status": "ok"}
