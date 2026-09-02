"""Visual scene detection, motion scoring, and thumbnails (fast-path aware)."""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

import numpy as np

from app.config import get_settings

logger = logging.getLogger(__name__)


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


def detect_scenes(video_path: str | Path) -> list[dict]:
    video_path = Path(video_path)
    settings = get_settings()

    # Fast path: fixed windows — avoids full PySceneDetect scan on CPU
    if settings.light_mode:
        duration = _probe_duration(video_path) or 30.0
        window = 8.0
        scenes = []
        idx = 0
        t = 0.0
        while t < duration - 0.5:
            end = min(t + window, duration)
            scenes.append({"scene_index": idx, "start": t, "end": end})
            idx += 1
            t = end
        return scenes or [{"scene_index": 0, "start": 0.0, "end": duration}]

    from scenedetect import SceneManager, open_video
    from scenedetect.detectors import ContentDetector

    video = open_video(str(video_path))
    manager = SceneManager()
    manager.add_detector(ContentDetector(threshold=27.0))
    manager.detect_scenes(video)
    scene_list = manager.get_scene_list()

    if not scene_list:
        duration = _probe_duration(video_path)
        return [{"scene_index": 0, "start": 0.0, "end": duration}]

    return [
        {
            "scene_index": idx,
            "start": float(start_tc.get_seconds()),
            "end": float(end_tc.get_seconds()),
        }
        for idx, (start_tc, end_tc) in enumerate(scene_list)
    ]


def compute_motion_score(video_path: str | Path, start: float, end: float) -> float:
    """Mean absolute frame-difference — skipped in light mode."""
    import cv2

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return 0.0

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    # Sample sparsely (~1 fps) for speed
    sample_interval = max(int(fps), 1)
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
            gray = cv2.resize(gray, (96, 54))
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
        "5",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=30)
    if result.returncode != 0 or not output_path.exists():
        raise RuntimeError(f"Thumbnail extraction failed at t={timestamp}")
    return output_path


def analyze_scenes(job_id: str, video_path: str | Path) -> list[dict]:
    settings = get_settings()
    thumb_dir = settings.storage_dir / "uploads" / job_id / "thumbnails"
    thumb_dir.mkdir(parents=True, exist_ok=True)

    scenes = detect_scenes(video_path)

    if settings.light_mode:
        # Flat motion + at most 6 thumbnails to stay fast
        norm_motion = [0.5] * len(scenes)
        thumb_budget = 6
    else:
        raw_motion = [compute_motion_score(video_path, s["start"], s["end"]) for s in scenes]
        norm_motion = normalize_motion_scores(raw_motion)
        thumb_budget = len(scenes)

    enriched: list[dict] = []
    for i, (scene, motion) in enumerate(zip(scenes, norm_motion)):
        mid = (scene["start"] + scene["end"]) / 2.0
        rel = None
        if i < thumb_budget:
            thumb_name = f"scene_{scene['scene_index']:04d}.jpg"
            thumb_path = thumb_dir / thumb_name
            try:
                extract_thumbnail(video_path, mid, thumb_path)
                rel = f"{job_id}/thumbnails/{thumb_name}"
            except Exception:  # noqa: BLE001
                logger.warning("Thumbnail failed for scene %s", scene["scene_index"])

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
