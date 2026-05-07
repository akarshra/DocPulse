# DocPulse

AI-powered Document & Multimedia Q&A Web Application built with FastAPI, Next.js, Gemini AI, and FAISS.

## 🚀 Features

- 📄 Upload and process PDF documents
- 🎵 Upload audio and video files
- 🤖 AI-powered question answering using Google Gemini
- 🔍 Semantic search using FAISS vector database
- 📌 Timestamp-based answers for media files
- ⚡ Real-time streaming chat responses using SSE
- 📝 Automatic summaries for uploaded files
- 🎧 Audio/video transcription with Gemini File API
- 🐳 Dockerized full-stack setup
- ✅ Unit tests with 95%+ coverage

---

## 🛠 Tech Stack

### Frontend
- Next.js 15
- TypeScript
- Tailwind CSS
- shadcn/ui

### Backend
- FastAPI
- SQLAlchemy
- FAISS
- PyMuPDF
- Google Gemini API

### Deployment
- Vercel (Frontend)
- Render (Backend)
- Docker & Docker Compose

---

## 📂 Project Structure

```bash
DocPulse/
│
├── frontend/              # Next.js frontend
│
├── backend/               # FastAPI backend
│   ├── app/
│   │   ├── services/
│   │   ├── models.py
│   │   ├── config.py
│   │   └── main.py
│   │
│   ├── tests/
│   └── requirements.txt
│
├── docker-compose.yml
└── README.md
```

---

## ⚙️ Environment Variables

### Backend `.env`

```env
GEMINI_API_KEY=your_api_key
```

### Frontend `.env.local`

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## ▶️ Running Locally

### 1️⃣ Clone Repository

```bash
git clone https://github.com/akarshra/DocPulse.git
cd DocPulse
```

---

### 2️⃣ Run Backend

```bash
cd backend

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

uvicorn app.main:app --reload
```

Backend runs on:

```
http://localhost:8000
```

---

### 3️⃣ Run Frontend

Open another terminal:

```bash
cd frontend

npm install
npm run dev
```

Frontend runs on:

```
http://localhost:3000
```

---

## 🐳 Run with Docker

```bash
docker-compose up --build
```

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/upload` | Upload file |
| POST | `/api/process/{file_id}` | Process uploaded file |
| POST | `/api/chat` | Ask questions |
| GET | `/api/chat/stream` | Streaming chat endpoint |
| GET | `/api/summary/{file_id}` | Generate summary |
| GET | `/api/files` | Get uploaded files |
| GET | `/health` | Health check |

---

## 🧠 How It Works

1. User uploads PDF/audio/video file
2. Backend extracts text/transcript
3. Text chunks are embedded using Gemini embeddings
4. Embeddings stored in FAISS vector index
5. User asks questions
6. Relevant chunks retrieved semantically
7. Gemini generates contextual answers
8. Streaming responses delivered using SSE

---

## 🧪 Running Tests

```bash
cd backend

pytest --cov=app --cov-report=term-missing
```

Coverage:

```
95%+
```

---

## 🌐 Deployment

### Frontend
Deployed on Vercel

### Backend
Deployed on Render

---

## 🔒 CORS Configuration

Production-ready CORS setup:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://docpulse-eta.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 👨‍💻 Author

Akarsh Raj

GitHub: https://github.com/akarshra  
Project Repository: https://github.com/akarshra/DocPulse  

---

## 📄 License

This project is developed as part of an SDE-1 assignment submission.
