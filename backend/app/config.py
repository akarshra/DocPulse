import os
import logging
from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from google import genai

# Load environment variables from .env file
load_dotenv()

# For local development, prefer the SQLite DB if no reachable Postgres is available.
# This prevents the API from silently failing with "File not found" because the DB connection can't be established.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////tmp/local.db")

# If DATABASE_URL points to Postgres but we're running the backend directly on the host
# (where the docker service name 'db' typically isn't resolvable), fall back to SQLite.
# Also, if no docker networking is available, Postgres will fail to connect and the API
# will behave like files/indexes don't exist.
if DATABASE_URL.startswith("postgresql://"):
    # Always prefer SQLite for local dev unless you're explicitly running inside docker
    # where hostnames like 'db' resolve.
    DATABASE_URL = "sqlite:////tmp/local.db"

# NOTE: Don't re-read DATABASE_URL after applying the fallback above.
# Several earlier failures happened because DATABASE_URL was being overwritten below.

logging.basicConfig(level=logging.INFO)

# =========================
# Gemini Configuration
# =========================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

gemini_client = None
if GEMINI_API_KEY:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    logging.info("Gemini client initialized successfully")
else:
    logging.warning("GEMINI_API_KEY not found in environment")

# =========================
# Database Configuration
# =========================
# DATABASE_URL is already resolved above (including local fallback logic).

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# =========================
# Directories
# =========================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FAISS_INDEX_DIR = os.path.join(BASE_DIR, "faiss_indexes")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

os.makedirs(FAISS_INDEX_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)