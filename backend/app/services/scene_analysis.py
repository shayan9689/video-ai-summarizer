"""Visual scene detection, motion scoring, and thumbnails."""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

import cv2
import numpy as np

from app.config import get_settings

logger = logging.getLogger(__name__)


def detect_scenes(video_path: str | Path) -> list[dict]:
    from scenedetect import SceneManager, open_video
    from scenedetect.detectors import ContentDetector

    video_path = Path(video_path)
    video = open_video(str(video_path))
    manager = SceneManager()
    manager.add_detector(ContentDetector(threshold=27.0))
    manager.detect_scenes(video)
    scene_list = manager.get_scene_list()

    scenes: list[dict] = []
    if not scene_list:
        # Single continuous shot — one scene covering full duration
        duration = _probe_duration(video_path)
        return [{"scene_index": 0, "start": 0.0, "end": duration}]

    for idx, (start_tc, end_tc) in enumerate(scene_list):
        scenes.append(
            {
                "scene_index": idx,
                "start": float(start_tc.get_seconds()),
                "end": float(end_tc.get_seconds()),
            }
        )
    return scenes


def _probe_duration(video_path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "quiet",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(video_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


def compute_motion_score(video_path: str | Path, start: float, end: float) -> float:
    """Mean absolute frame-difference at ~2fps within [start, end]."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return 0.0

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    sample_interval = max(int(fps / 2), 1)
    start_frame = int(start * fps)
    end_frame = max(int(end * fps), start_frame + 1)

    prev_gray = None
    diffs: list[float] = []
    frame_idx = start_frame
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

    while frame_idx < end_frame:
        ok, frame = cap.read()
        if not ok:
            break
        if (frame_idx - start_frame) % sample_interval == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.resize(gray, (160, 90))
            if prev_gray is not None:
                diffs.append(float(np.mean(cv2.absdiff(prev_gray, gray))))
            prev_gray = gray
        frame_idx += 1

    cap.release()
    if not diffs:
        return 0.0
    return float(np.mean(diffs))


def normalize_motion_scores(raw_scores: list[float]) -> list[float]:
    if not raw_scores:
        return []
    arr = np.asarray(raw_scores, dtype=np.float64)
    mx = float(arr.max())
    if mx <= 0:
        return [0.0] * len(raw_scores)
    return [float(x / mx) for x in arr]


def extract_thumbnail(video_path: str | Path, timestamp: float, output_path: str | Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        f"{timestamp:.3f}",
        "-i",
        str(video_path),
        "-frames:v",
        "1",
        "-q:v",
        "3",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=60)
    if result.returncode != 0 or not output_path.exists():
        raise RuntimeError(f"Thumbnail extraction failed at t={timestamp}")
    return output_path


def analyze_scenes(job_id: str, video_path: str | Path) -> list[dict]:
    settings = get_settings()
    thumb_dir = settings.storage_dir / "uploads" / job_id / "thumbnails"
    thumb_dir.mkdir(parents=True, exist_ok=True)

    scenes = detect_scenes(video_path)
    raw_motion = [compute_motion_score(video_path, s["start"], s["end"]) for s in scenes]
    norm_motion = normalize_motion_scores(raw_motion)

    enriched: list[dict] = []
    for scene, motion in zip(scenes, norm_motion):
        mid = (scene["start"] + scene["end"]) / 2.0
        thumb_name = f"scene_{scene['scene_index']:04d}.jpg"
        thumb_path = thumb_dir / thumb_name
        try:
            extract_thumbnail(video_path, mid, thumb_path)
            rel = f"{job_id}/thumbnails/{thumb_name}"
        except Exception:  # noqa: BLE001
            logger.warning("Thumbnail failed for scene %s", scene["scene_index"])
            rel = None

        enriched.append(
            {
                **scene,
                "motion_score": motion,
                "thumbnail_path": rel,
            }
        )

    out = settings.storage_dir / "uploads" / job_id / "scenes.json"
    out.write_text(json.dumps({"scenes": enriched}, indent=2), encoding="utf-8")
    return enriched


def load_scenes(job_id: str) -> dict | None:
    settings = get_settings()
    path = settings.storage_dir / "uploads" / job_id / "scenes.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
