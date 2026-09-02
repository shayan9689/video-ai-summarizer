"""Speech-to-text via faster-whisper (speed-tuned for CPU demos)."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from app.config import get_settings

logger = logging.getLogger(__name__)

_model = None


def get_whisper_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel

        settings = get_settings()
        size = settings.whisper_model_size
        logger.info("Loading faster-whisper model: %s", size)
        _model = WhisperModel(size, device="cpu", compute_type="int8")
    return _model


def warmup_whisper() -> None:
    """Load model into memory so the first job doesn't pay download latency mid-request."""
    try:
        get_whisper_model()
        logger.info("Whisper warmup complete")
    except Exception:  # noqa: BLE001
        logger.exception("Whisper warmup failed (will retry on first job)")


def transcribe_audio(audio_path: str | Path, model_size: str | None = None) -> list[dict]:
    """
    Transcribe audio to segment list: [{start, end, text}, ...].
    Uses fast CPU settings (beam_size=1) to stay within a ~2–3 min pipeline budget.
    """
    _ = model_size
    model = get_whisper_model()
    segments_iter, _info = model.transcribe(
        str(audio_path),
        word_timestamps=False,
        vad_filter=True,
        beam_size=1,
        best_of=1,
        temperature=0.0,
        condition_on_previous_text=False,
    )
    segments: list[dict] = []
    for seg in segments_iter:
        text = (seg.text or "").strip()
        if not text:
            continue
        segments.append(
            {
                "start": float(seg.start),
                "end": float(seg.end),
                "text": text,
            }
        )
    return segments


def save_transcript(job_id: str, segments: list[dict]) -> Path:
    settings = get_settings()
    out = settings.storage_dir / "uploads" / job_id / "transcript.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"segments": segments}, indent=2), encoding="utf-8")
    return out


def load_transcript(job_id: str) -> dict | None:
    settings = get_settings()
    path = settings.storage_dir / "uploads" / job_id / "transcript.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
