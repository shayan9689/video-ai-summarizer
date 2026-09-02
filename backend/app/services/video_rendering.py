"""Highlight reel clip extraction and concatenation via FFmpeg."""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

from app.config import get_settings

logger = logging.getLogger(__name__)


def extract_clip(
    video_path: str | Path,
    start: float,
    end: float,
    output_path: str | Path,
) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    duration = max(0.05, end - start)
    settings = get_settings()

    # Fast path: stream copy (seconds, not minutes of re-encode)
    if settings.light_mode:
        cmd = [
            "ffmpeg",
            "-y",
            "-ss",
            f"{start:.3f}",
            "-i",
            str(video_path),
            "-t",
            f"{duration:.3f}",
            "-c",
            "copy",
            "-avoid_negative_ts",
            "make_zero",
            str(output_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=120)
        if result.returncode == 0 and output_path.exists():
            return output_path
        logger.warning("Stream-copy clip failed; falling back to ultrafast re-encode")

    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        f"{start:.3f}",
        "-i",
        str(video_path),
        "-t",
        f"{duration:.3f}",
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-crf",
        "28",
        "-c:a",
        "aac",
        "-b:a",
        "96k",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=300)
    if result.returncode != 0 or not output_path.exists():
        raise RuntimeError(f"Clip extraction failed [{start}-{end}]: {result.stderr[-400:]}")
    return output_path


def concatenate_clips(
    clip_paths: list[Path],
    output_path: str | Path,
    transition: str = "cut",
) -> Path:
    if transition != "cut":
        logger.warning("Only transition='cut' is implemented; ignoring %s", transition)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if len(clip_paths) == 1:
        shutil.copyfile(clip_paths[0], output_path)
        return output_path

    list_file = output_path.with_suffix(".txt")
    lines = [f"file '{p.resolve().as_posix()}'" for p in clip_paths]
    list_file.write_text("\n".join(lines), encoding="utf-8")
    try:
        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-c",
            "copy",
            str(output_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=180)
        if result.returncode != 0 or not output_path.exists():
            cmd = [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_file),
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                "-c:a",
                "aac",
                str(output_path),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=300)
            if result.returncode != 0:
                raise RuntimeError(f"Concatenation failed: {result.stderr[-400:]}")
    finally:
        list_file.unlink(missing_ok=True)

    return output_path


def render_highlight_reel(
    job_id: str,
    video_path: str | Path,
    highlight_segments: list[dict],
) -> str:
    settings = get_settings()
    final_path = settings.storage_dir / "uploads" / job_id / "highlight_reel.mp4"

    if not highlight_segments:
        extract_clip(video_path, 0, min(15.0, 15.0), final_path)
        return str(final_path)

    # Cap clips for speed (client budget)
    segments = highlight_segments[:5]

    tmp_dir = Path(tempfile.mkdtemp(prefix=f"hl_{job_id}_"))
    try:
        clips: list[Path] = []
        for i, seg in enumerate(segments):
            clip_path = tmp_dir / f"clip_{i:03d}.mp4"
            extract_clip(video_path, float(seg["start"]), float(seg["end"]), clip_path)
            clips.append(clip_path)
        concatenate_clips(clips, final_path, transition="cut")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return str(final_path)
