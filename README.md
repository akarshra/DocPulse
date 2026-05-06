# DocPulse

A full-stack web application for uploading PDF/audio/video files and asking AI-powered questions about them.

## Features

- Upload PDF, audio, and video files
- Automatic transcription for audio/video using Google Gemini File API
- Text extraction from PDFs using PyMuPDF
- Vector similarity search using FAISS
- AI-powered Q&A using Google Gemini API (`gemini-2.5-flash`)
- File summary generation
- Real-time streaming chat responses with SSE
- Media player with seek-to-timestamp playback for audio/video answers
- Modern UI with Next.js, Framer Motion, and Tailwind CSS

## Tech Stack

- Backend: FastAPI (Python)
- Frontend: Next.js (React) with Tailwind CSS and shadcn/ui
- Database: PostgreSQL (via Docker) with SQLite local fallback
- Storage: Local file system
- AI: Google GenAI (Gemini API)
- Vector Search: FAISS
- Containerization: Docker & Docker Compose

## Setup

1. Clone the repository
2. Get a Google Gemini API key from Google AI Studio
3. Create a `.env` file in the `backend` folder with:
   ```
   GEMINI_API_KEY=your_gemini_key
   ```
4. Run with Docker Compose:
   ```
   docker-compose up --build
   ```
5. Access frontend at http://localhost:3000

## API Endpoints

- POST /api/upload - Upload a file
- POST /api/process/{file_id} - Process a file
- POST /api/chat - Ask a question
- GET /api/summary/{file_id} - Get file summary
- GET /api/files - List files
- GET /health - Health check