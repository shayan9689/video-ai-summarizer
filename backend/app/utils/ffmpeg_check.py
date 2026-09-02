"""Verify FFmpeg and ffprobe are available on PATH."""

from __future__ import annotations

import logging
import shutil
import subprocess

logger = logging.getLogger(__name__)

INSTALL_HINT = (
    "FFmpeg is required for video processing. Install it and ensure ffmpeg/ffprobe "
    "are on your PATH.\n"
    "  Windows: winget install Gyan.FFmpeg   (or https://ffmpeg.org/download.html)\n"
    "  macOS:   brew install ffmpeg\n"
    "  Linux:   sudo apt-get install ffmpeg"
)


def _which_or_none(name: str) -> str | None:
    return shutil.which(name)


def _can_run(binary: str) -> bool:
    try:
        result = subprocess.run(
            [binary, "-version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def verify_ffmpeg_installed(*, raise_on_missing: bool = False) -> bool:
    """
    Check that ffmpeg and ffprobe are installed and runnable.

    Logs a clear warning when missing. Set raise_on_missing=True to raise RuntimeError
    (useful for scripts); FastAPI startup should keep raise_on_missing=False.
    """
    ffmpeg_path = _which_or_none("ffmpeg")
    ffprobe_path = _which_or_none("ffprobe")

    missing: list[str] = []
    if not ffmpeg_path or not _can_run("ffmpeg"):
        missing.append("ffmpeg")
    if not ffprobe_path or not _can_run("ffprobe"):
        missing.append("ffprobe")

    if missing:
        msg = f"Missing binaries: {', '.join(missing)}. {INSTALL_HINT}"
        if raise_on_missing:
            raise RuntimeError(msg)
        logger.warning(msg)
        return False

    logger.info("FFmpeg OK: ffmpeg=%s ffprobe=%s", ffmpeg_path, ffprobe_path)
    return True
