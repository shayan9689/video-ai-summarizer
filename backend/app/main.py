"""FastAPI entrypoint for video-ai-summarizer."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.models.database import init_db
from app.routers import videos
from app.utils.ffmpeg_check import verify_ffmpeg_installed

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    (settings.storage_dir / "uploads").mkdir(parents=True, exist_ok=True)
    init_db()
    logger.info("Storage directory: %s", settings.storage_dir)
    logger.info("Database: %s", settings.resolved_database_url.split("@")[-1])
    verify_ffmpeg_installed(raise_on_missing=False)
    yield


app = FastAPI(
    title="Video AI Summarizer",
    description="Transcribe, summarize, and auto-generate highlight reels from raw video.",
    version="0.1.0",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(videos.router)
app.include_router(videos.ws_router)

uploads_root = Path(settings.storage_dir) / "uploads"
uploads_root.mkdir(parents=True, exist_ok=True)
app.mount("/static/uploads", StaticFiles(directory=str(uploads_root)), name="uploads")


@app.get("/health")
async def health():
    ffmpeg_ok = verify_ffmpeg_installed(raise_on_missing=False)
    return {"status": "ok", "ffmpeg": ffmpeg_ok}
