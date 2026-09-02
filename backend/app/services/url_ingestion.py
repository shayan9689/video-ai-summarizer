"""Download remote video URLs (YouTube, Vimeo, direct MP4, etc.) via yt-dlp."""

from __future__ import annotations

import logging
import os
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


def _friendly_ytdlp_error(exc: BaseException) -> str:
    msg = str(exc)
    lower = msg.lower()
    if "sign in to confirm" in lower or "not a bot" in lower or "cookies" in lower:
        return (
            "YouTube blocked this download (bot check). "
            "Please upload the video file instead, or try a direct .mp4 link / Vimeo URL. "
            "On production servers, YouTube often requires browser cookies."
        )
    if "private video" in lower or "login required" in lower:
        return "This video is private or requires login. Upload the file instead."
    if "video unavailable" in lower:
        return "This video is unavailable. Check the link or upload a file."
    # Keep message short for UI
    short = msg.split("\n")[0]
    if len(short) > 180:
        short = short[:177] + "…"
    return f"Could not download this link. Try another URL or upload a file. ({short})"


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

    # Prefer mobile/TV clients — datacenter IPs often fail on default "web" client
    ydl_opts: dict = {
        "outtmpl": outtmpl,
        "format": "bv*[height<=720]+ba/b[height<=720]/b",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "retries": 3,
        "fragment_retries": 3,
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "ios", "tv", "mweb", "web"],
            }
        },
    }

    # Optional: place cookies.txt on the server or set YTDLP_COOKIES_FILE
    cookies = os.environ.get("YTDLP_COOKIES_FILE", "").strip()
    if cookies and Path(cookies).is_file():
        ydl_opts["cookiefile"] = cookies
        logger.info("Using yt-dlp cookies file: %s", cookies)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info is None:
                raise VideoValidationError("Could not read video info from this link")

            duration = float(info.get("duration") or 0)
            if duration > settings.max_video_duration_seconds:
                raise VideoValidationError(
                    f"Video duration ({duration:.0f}s) exceeds limit of "
                    f"{settings.max_video_duration_seconds}s. Use a shorter clip."
                )

            title = info.get("title") or "video"
            safe_title = re.sub(r"[^\w\s\-]+", "", title).strip() or "video"
            safe_title = safe_title[:60]

            ydl.download([url])
    except VideoValidationError:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("yt-dlp failed for %s", url)
        raise VideoValidationError(_friendly_ytdlp_error(exc)) from exc

    candidates = sorted(
        list(dest_dir.glob("source.*"))
        + list(dest_dir.glob("*.mp4"))
        + list(dest_dir.glob("*.mkv"))
        + list(dest_dir.glob("*.webm")),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    candidates = [
        p
        for p in candidates
        if p.is_file() and p.suffix.lower() in {".mp4", ".mkv", ".webm", ".mov"}
    ]
    if not candidates:
        raise VideoValidationError(
            "Download finished but no video file was found. Try uploading the file instead."
        )

    path = candidates[0]
    final_name = f"{safe_title}{path.suffix.lower()}"
    final_path = dest_dir / final_name
    if final_path != path:
        path.replace(final_path)
        path = final_path

    return path, final_name
