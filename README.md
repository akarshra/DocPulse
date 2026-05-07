#DocPulse
DocPulse is a full-stack AI-powered document intelligence app. Drop in a PDF, audio, or video file — and start a conversation with it. Ask questions, get summaries, and jump to the exact timestamp in your media where the answer lives.

🚀 Features
FeatureDescription📄Multi-format UploadSupports PDF, audio, and video files🎙️Auto TranscriptionAudio/video transcribed via Google Gemini File API📝PDF Text ExtractionFast text extraction using PyMuPDF🔍Vector SearchSemantic similarity search powered by FAISS🤖AI Q&AAnswers powered by gemini-2.5-flash📋Smart SummariesAuto-generated file summaries⚡Streaming ChatReal-time responses via Server-Sent Events (SSE)🎬Timestamp PlaybackJump directly to the answer in audio/video🎨Modern UIBuilt with Next.js, Framer Motion & Tailwind CSS

🛠️ Tech Stack
┌─────────────────────────────────────────────────────────┐
│                        DocPulse                         │
├──────────────────────┬──────────────────────────────────┤
│      Frontend        │           Backend                │
│  Next.js + React     │       FastAPI (Python)           │
│  Tailwind CSS        │       Google Gemini API          │
│  shadcn/ui           │       FAISS Vector Search        │
│  Framer Motion       │       PyMuPDF                    │
├──────────────────────┴──────────────────────────────────┤
│                      Database                           │
│                  PostgreSQL (Docker)                    │
├─────────────────────────────────────────────────────────┤
│              Infrastructure & DevOps                    │
│              Docker  ·  Docker Compose                  │
└─────────────────────────────────────────────────────────┘

⚙️ Getting Started
Prerequisites

🐳 Docker & Docker Compose
🔑 Google Gemini API key from Google AI Studio

Installation
1. Clone the repo
bashgit clone https://github.com/akarshra/DocPulse.git
cd DocPulse
2. Add your API key
Create a .env file inside the backend/ folder:
envGEMINI_API_KEY=your_gemini_key_here
3. Start with Docker Compose
bashdocker-compose up --build
4. Open in your browser
http://localhost:3000

✅ That's it! The frontend, backend, and database all spin up together.


📡 API Reference
MethodEndpointDescriptionPOST/api/uploadUpload a PDF, audio, or video filePOST/api/process/{file_id}Transcribe/extract & index the filePOST/api/chatAsk a question about a processed fileGET/api/summary/{file_id}Get the AI-generated file summaryGET/api/filesList all uploaded filesGET/healthHealth check

🗂️ Project Structure
DocPulse/
├── 📁 backend/              # FastAPI Python backend
│   ├── main.py              # API routes & app entry
│   ├── gemini.py            # Gemini API integration
│   └── vector_store.py      # FAISS vector search
│
├── 📁 frontend/             # Next.js React frontend
│   ├── app/                 # App router pages
│   ├── components/          # UI components
│   └── lib/                 # Utilities & API client
│
├── 📁 .github/workflows/    # CI/CD pipelines
├── 🐳 docker-compose.yml   # Multi-container setup
└── 📄 README.md

📊 Codebase
Show Image
Show Image
Show Image
Show Image
Show Image

🤝 Contributing
Contributions are welcome! Here's how to get involved:

Fork the repository
Create a feature branch → git checkout -b feature/amazing-feature
Commit your changes → git commit -m 'Add amazing feature'
Push to the branch → git push origin feature/amazing-feature
Open a Pull Request

Feel free to open an issue for bugs or feature requests.

📄 License
This project is open source. See the repository for details.

<div align="center">
Made with ❤️ by akarshra
⭐ Star this repo if you find it useful!
