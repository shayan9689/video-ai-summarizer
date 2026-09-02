"""Video upload, status, artifacts, and websocket progress endpoints."""

from __future__ import annotations

import asyncio
import logging
import shutil
import uuid
from pathlib import Path

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.database import get_db
from app.models.job import Job, JobStatus
from app.services import pipeline as pipeline_service
from app.services.highlight_scoring import load_highlights
from app.services.scene_analysis import load_scenes
from app.services.summarization import load_summary
from app.services.transcript_processing import load_chunks
from app.services.transcription import load_transcript
from app.services.video_ingestion import (
    VideoValidationError,
    extract_audio,
    get_video_metadata,
    validate_upload,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/videos", tags=["videos"])
ws_router = APIRouter(tags=["websocket"])

settings = get_settings()

# Statuses that mean transcript is ready
_TRANSCRIPT_READY = {
    JobStatus.transcribed,
    JobStatus.segmented,
    JobStatus.analyzing_scenes,
    JobStatus.scenes_analyzed,
    JobStatus.summarizing,
    JobStatus.summarized,
    JobStatus.scoring_highlights,
    JobStatus.highlights_scored,
    JobStatus.rendering,
    JobStatus.complete,
}


def _job_dir(job_id: str) -> Path:
    path = settings.storage_dir / "uploads" / job_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def _get_job_or_404(db: Session, job_id: str) -> Job:
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/upload")
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    try:
        validate_upload(file.filename, max_duration_seconds=settings.max_video_duration_seconds)
    except VideoValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    job_id = str(uuid.uuid4())
    dest_dir = _job_dir(job_id)
    original_path = dest_dir / file.filename

    try:
        with original_path.open("wb") as out:
            shutil.copyfileobj(file.file, out)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save upload: {exc}") from exc
    finally:
        await file.close()

    if original_path.stat().st_size < 100:
        original_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Uploaded file is empty or too small")

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if original_path.stat().st_size > max_bytes:
        shutil.rmtree(dest_dir, ignore_errors=True)
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds max upload size of {settings.max_upload_size_mb}MB",
        )

    job = Job(
        id=job_id,
        filename=file.filename,
        original_path=str(original_path),
        status=JobStatus.uploaded,
        progress_percent=5,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    try:
        meta = get_video_metadata(original_path)
        validate_upload(
            file.filename,
            duration_seconds=meta["duration"],
            max_duration_seconds=settings.max_video_duration_seconds,
        )

        job.duration_seconds = meta["duration"]
        job.width = meta["width"]
        job.height = meta["height"]
        job.fps = meta["fps"]
        job.codec = meta["codec"]
        job.status = JobStatus.extracting_audio
        job.progress_percent = 10
        db.commit()

        audio_path = dest_dir / "audio.wav"
        extract_audio(original_path, audio_path)
        job.audio_path = str(audio_path)
        job.status = JobStatus.uploaded
        job.progress_percent = 15
        db.commit()
        db.refresh(job)
    except VideoValidationError as exc:
        job.status = JobStatus.failed
        job.error_message = str(exc)
        db.commit()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Upload processing failed for job %s", job_id)
        job.status = JobStatus.failed
        job.error_message = str(exc)
        db.commit()
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    background_tasks.add_task(pipeline_service.run_pipeline, job_id)

    return {
        "job_id": job.id,
        "duration_seconds": job.duration_seconds,
        "status": job.status.value,
        "progress_percent": job.progress_percent,
    }


@router.get("/{job_id}/status")
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    job = _get_job_or_404(db, job_id)
    return {
        "job_id": job.id,
        "status": job.status.value,
        "progress_percent": job.progress_percent,
        "error_message": job.error_message,
        "duration_seconds": job.duration_seconds,
        "filename": job.filename,
    }


@router.get("/{job_id}/transcript")
def get_transcript(job_id: str, db: Session = Depends(get_db)):
    job = _get_job_or_404(db, job_id)
    if job.status == JobStatus.failed:
        raise HTTPException(status_code=400, detail=job.error_message or "Job failed")
    data = load_transcript(job_id)
    if data is None or job.status not in _TRANSCRIPT_READY:
        return JSONResponse(
            status_code=202,
            content={"status": job.status.value, "progress_percent": job.progress_percent},
        )
    return data


@router.get("/{job_id}/chunks")
def get_chunks(job_id: str, db: Session = Depends(get_db)):
    _get_job_or_404(db, job_id)
    data = load_chunks(job_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Chunks not ready yet")
    return data


@router.get("/{job_id}/scenes")
def get_scenes(job_id: str, db: Session = Depends(get_db)):
    _get_job_or_404(db, job_id)
    data = load_scenes(job_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Scenes not ready yet")
    return data


@router.get("/{job_id}/summary")
def get_summary(job_id: str, db: Session = Depends(get_db)):
    _get_job_or_404(db, job_id)
    data = load_summary(job_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Summary not ready yet")
    return data


@router.get("/{job_id}/highlights")
def get_highlights(job_id: str, db: Session = Depends(get_db)):
    _get_job_or_404(db, job_id)
    data = load_highlights(job_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Highlights not ready yet")
    return data


@router.get("/{job_id}/download/highlight-reel")
def download_highlight_reel(job_id: str, db: Session = Depends(get_db)):
    job = _get_job_or_404(db, job_id)
    path = Path(job.highlight_reel_path) if job.highlight_reel_path else None
    if path is None or not path.exists():
        fallback = settings.storage_dir / "uploads" / job_id / "highlight_reel.mp4"
        path = fallback if fallback.exists() else None
    if path is None:
        raise HTTPException(status_code=404, detail="Highlight reel not ready")
    return FileResponse(
        path,
        media_type="video/mp4",
        filename=f"{Path(job.filename).stem}_highlights.mp4",
    )


@router.get("/{job_id}/download/original")
def download_original(job_id: str, db: Session = Depends(get_db)):
    job = _get_job_or_404(db, job_id)
    path = Path(job.original_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Original video not found")
    return FileResponse(path, media_type="video/mp4", filename=job.filename)


@router.get("/{job_id}/full-result")
def get_full_result(job_id: str, db: Session = Depends(get_db)):
    job = _get_job_or_404(db, job_id)
    return {
        "status": job.status.value,
        "progress_percent": job.progress_percent,
        "error_message": job.error_message,
        "video_metadata": {
            "filename": job.filename,
            "duration_seconds": job.duration_seconds,
            "width": job.width,
            "height": job.height,
            "fps": job.fps,
            "codec": job.codec,
        },
        "summary": load_summary(job_id),
        "highlights": load_highlights(job_id),
        "scenes": load_scenes(job_id),
    }


@ws_router.websocket("/ws/videos/{job_id}")
async def job_progress_ws(websocket: WebSocket, job_id: str):
    await websocket.accept()
    queue: asyncio.Queue = asyncio.Queue()

    async def push(payload: dict):
        await queue.put(payload)

    pipeline_service.subscribe(job_id, push)
    try:
        # Send current status immediately
        from app.models.database import SessionLocal

        db = SessionLocal()
        try:
            job = db.get(Job, job_id)
            if job:
                await websocket.send_json(pipeline_service._job_payload(job))
            else:
                await websocket.send_json(
                    {"job_id": job_id, "status": "failed", "error_message": "Job not found"}
                )
        finally:
            db.close()

        while True:
            try:
                payload = await asyncio.wait_for(queue.get(), timeout=25)
                await websocket.send_json(payload)
                if payload.get("status") in ("complete", "failed"):
                    break
            except asyncio.TimeoutError:
                # keepalive ping
                await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        pass
    finally:
        pipeline_service.unsubscribe(job_id, push)
