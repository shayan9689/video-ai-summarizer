"""Download remote video URLs (YouTube, Vimeo, direct MP4, etc.) via yt-dlp."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from urllib.parse import urlparse

from app.config import get_settings
from app.services.video_ingestion import VideoValidationError

logger = logging.getLogger(__name__)

_ALLOWED_SCHEMES = {"http", "https"}


def validate_video_url(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        raise VideoValidationError("Video URL is required")
    parsed = urlparse(raw)
    if parsed.scheme not in _ALLOWED_SCHEMES or not parsed.netloc:
        raise VideoValidationError("Enter a valid http(s) video link")
    return raw


def download_video_from_url(url: str, dest_dir: Path) -> tuple[Path, str]:
    """
    Download a video to dest_dir.
    Returns (file_path, display_filename).
    """
    import yt_dlp

    settings = get_settings()
    dest_dir.mkdir(parents=True, exist_ok=True)
    url = validate_video_url(url)

    outtmpl = str(dest_dir / "source.%(ext)s")
    ydl_opts: dict = {
        "outtmpl": outtmpl,
        "format": "bv*[height<=720][ext=mp4]+ba[ext=m4a]/b[height<=720]/b",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "retries": 2,
        # Keep downloads short for demo budget
        "match_filter": None,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        if info is None:
            raise VideoValidationError("Could not read video info from this link")

        duration = float(info.get("duration") or 0)
        if duration <= 0:
            # Direct file links may omit duration — allow and validate later via ffprobe
            pass
        elif duration > settings.max_video_duration_seconds:
            raise VideoValidationError(
                f"Video duration ({duration:.0f}s) exceeds limit of "
                f"{settings.max_video_duration_seconds}s. Use a shorter clip."
            )

        title = info.get("title") or "video"
        safe_title = re.sub(r"[^\w\s\-]+", "", title).strip() or "video"
        safe_title = safe_title[:60]

        ydl.download([url])

    # Find produced file
    candidates = sorted(
        list(dest_dir.glob("source.*")) + list(dest_dir.glob("*.mp4")) + list(dest_dir.glob("*.mkv")),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    # Prefer non-temp
    candidates = [p for p in candidates if p.is_file() and p.suffix.lower() in {".mp4", ".mkv", ".webm", ".mov"}]
    if not candidates:
        raise VideoValidationError("Download finished but no video file was found")

    path = candidates[0]
    final_name = f"{safe_title}{path.suffix.lower()}"
    final_path = dest_dir / final_name
    if final_path != path:
        path.replace(final_path)
        path = final_path

    return path, final_name
