"""Video metadata extraction and audio track preparation."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".mkv"}


class VideoValidationError(ValueError):
    """Raised for client-facing validation failures (maps to HTTP 4xx)."""


def _run_ffprobe(path: Path) -> dict:
    cmd = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=60)
    except FileNotFoundError as exc:
        raise RuntimeError("ffprobe is not installed or not on PATH") from exc
    except subprocess.TimeoutExpired as exc:
        raise VideoValidationError("Timed out reading video metadata") from exc

    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "unknown ffprobe error").strip()
        raise VideoValidationError(f"Could not read video file (unsupported or corrupt): {detail}")

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise VideoValidationError("Invalid ffprobe output for uploaded file") from exc


def get_video_metadata(path: str | Path) -> dict:
    """Return duration, width, height, fps, and codec via ffprobe."""
    path = Path(path)
    data = _run_ffprobe(path)

    video_stream = next(
        (s for s in data.get("streams", []) if s.get("codec_type") == "video"),
        None,
    )
    if video_stream is None:
        raise VideoValidationError("No video stream found in uploaded file")

    fmt = data.get("format", {})
    try:
        duration = float(fmt.get("duration") or video_stream.get("duration") or 0)
    except (TypeError, ValueError):
        duration = 0.0

    width = int(video_stream.get("width") or 0)
    height = int(video_stream.get("height") or 0)
    codec = video_stream.get("codec_name") or "unknown"

    fps = 0.0
    rate = video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate") or "0/1"
    if isinstance(rate, str) and "/" in rate:
        num, den = rate.split("/", 1)
        try:
            den_f = float(den)
            fps = float(num) / den_f if den_f else 0.0
        except ValueError:
            fps = 0.0

    if duration <= 0:
        raise VideoValidationError("Could not determine video duration")

    return {
        "duration": duration,
        "width": width,
        "height": height,
        "fps": fps,
        "codec": codec,
    }


def validate_upload(
    filename: str,
    *,
    duration_seconds: float | None = None,
    max_duration_seconds: int,
) -> None:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise VideoValidationError(
            f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )
    if duration_seconds is not None and duration_seconds > max_duration_seconds:
        raise VideoValidationError(
            f"Video duration ({duration_seconds:.1f}s) exceeds limit of {max_duration_seconds}s"
        )


def extract_audio(video_path: str | Path, output_path: str | Path) -> Path:
    """Extract 16kHz mono WAV suitable for Whisper."""
    video_path = Path(video_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        str(output_path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=600)
    except FileNotFoundError as exc:
        raise RuntimeError("ffmpeg is not installed or not on PATH") from exc
    except subprocess.TimeoutExpired as exc:
        raise VideoValidationError("Audio extraction timed out") from exc

    if result.returncode != 0 or not output_path.exists():
        detail = (result.stderr or "ffmpeg failed").strip().splitlines()[-1:] or ["ffmpeg failed"]
        raise VideoValidationError(f"Audio extraction failed: {detail[0]}")

    return output_path
