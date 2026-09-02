"""Sequential pipeline orchestrator with concurrency guard and progress updates."""

from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from typing import Any, Callable

from app.config import get_settings
from app.models.database import SessionLocal
from app.models.job import Job, JobStatus
from app.services.highlight_scoring import score_and_select
from app.services.scene_analysis import analyze_scenes
from app.services.summarization import summarize_job
from app.services.transcript_processing import process_and_save_chunks
from app.services.transcription import save_transcript, transcribe_audio
from app.services.video_rendering import render_highlight_reel

logger = logging.getLogger(__name__)

_subscribers: dict[str, list[Callable[[dict], Any]]] = defaultdict(list)
_semaphore: asyncio.Semaphore | None = None


def get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        settings = get_settings()
        _semaphore = asyncio.Semaphore(settings.max_concurrent_jobs)
    return _semaphore


def subscribe(job_id: str, callback: Callable[[dict], Any]) -> None:
    _subscribers[job_id].append(callback)


def unsubscribe(job_id: str, callback: Callable[[dict], Any]) -> None:
    cbs = _subscribers.get(job_id, [])
    _subscribers[job_id] = [c for c in cbs if c is not callback]
    if not _subscribers[job_id]:
        _subscribers.pop(job_id, None)


async def _notify(job_id: str, payload: dict) -> None:
    for cb in list(_subscribers.get(job_id, [])):
        try:
            result = cb(payload)
            if asyncio.iscoroutine(result):
                await result
        except Exception:  # noqa: BLE001
            logger.exception("Subscriber notify failed for %s", job_id)


def _job_payload(job: Job) -> dict:
    return {
        "job_id": job.id,
        "status": job.status.value,
        "progress_percent": job.progress_percent,
        "error_message": job.error_message,
    }


def _update_job(job_id: str, **fields) -> dict:
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if not job:
            return {"job_id": job_id, "status": "failed", "error_message": "Job not found"}
        for key, value in fields.items():
            setattr(job, key, value)
        db.commit()
        db.refresh(job)
        return _job_payload(job)
    finally:
        db.close()


def _run_stages_with_hooks(job_id: str, loop: asyncio.AbstractEventLoop) -> None:
    def update(**fields):
        payload = _update_job(job_id, **fields)
        fut = asyncio.run_coroutine_threadsafe(_notify(job_id, payload), loop)
        try:
            fut.result(timeout=5)
        except Exception:  # noqa: BLE001
            pass
        return payload

    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if not job:
            raise RuntimeError("Job not found")
        video_path = job.original_path
        audio_path = job.audio_path
        filename = job.filename
    finally:
        db.close()

    if not audio_path:
        raise RuntimeError("Audio path missing — upload/extraction incomplete")

    try:
        update(status=JobStatus.transcribing, progress_percent=20, error_message=None)
        segments = transcribe_audio(audio_path)
        save_transcript(job_id, segments)
        update(status=JobStatus.transcribed, progress_percent=35)

        process_and_save_chunks(job_id, segments)
        chunks_path = get_settings().storage_dir / "uploads" / job_id / "chunks.json"
        chunks = json.loads(chunks_path.read_text(encoding="utf-8"))["chunks"]
        update(status=JobStatus.segmented, progress_percent=45)

        update(status=JobStatus.analyzing_scenes, progress_percent=50)
        scenes = analyze_scenes(job_id, video_path)
        update(status=JobStatus.scenes_analyzed, progress_percent=60)

        update(status=JobStatus.summarizing, progress_percent=65)
        summary = summarize_job(job_id, chunks, video_title=filename)
        update(status=JobStatus.summarized, progress_percent=75)

        update(status=JobStatus.scoring_highlights, progress_percent=80)
        highlights = score_and_select(job_id, scenes, chunks, audio_path, summary)
        update(status=JobStatus.highlights_scored, progress_percent=88)

        update(status=JobStatus.rendering, progress_percent=92)
        reel_path = render_highlight_reel(job_id, video_path, highlights["segments"])
        update(
            status=JobStatus.complete,
            progress_percent=100,
            highlight_reel_path=reel_path,
            error_message=None,
        )
    except Exception as exc:
        update(status=JobStatus.failed, error_message=f"{type(exc).__name__}: {exc}")
        raise


async def run_pipeline(job_id: str) -> None:
    sem = get_semaphore()
    await sem.acquire()
    try:
        await _notify(
            job_id,
            {"job_id": job_id, "status": "uploaded", "progress_percent": 15, "error_message": None},
        )
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, _run_stages_with_hooks, job_id, loop)
        except Exception:  # noqa: BLE001 — already recorded on Job
            logger.exception("Pipeline failed for job %s", job_id)
        finally:
            db = SessionLocal()
            try:
                job = db.get(Job, job_id)
                if job:
                    await _notify(job_id, _job_payload(job))
            finally:
                db.close()
    finally:
        sem.release()
