"""Multi-signal highlight scoring and segment selection."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np

from app.config import get_settings

logger = logging.getLogger(__name__)

_embedder = None


def _get_embedder():
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer

        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedder


def _normalize(values: list[float]) -> list[float]:
    if not values:
        return []
    arr = np.asarray(values, dtype=np.float64)
    mx = float(arr.max())
    if mx <= 0:
        return [0.0] * len(values)
    return [float(v / mx) for v in arr]


def compute_audio_energy(audio_path: str | Path, start: float, end: float) -> float:
    """RMS energy in window (full-quality path)."""
    import librosa

    y, sr = librosa.load(str(audio_path), sr=16000, mono=True)
    s = max(0, int(start * sr))
    e = min(len(y), int(end * sr))
    if e <= s:
        return 0.0
    window = y[s:e]
    return float(np.sqrt(np.mean(np.square(window)) + 1e-12))


def compute_transcript_salience(chunk: dict, summary: dict) -> float:
    key_points = summary.get("key_points") or []
    quotes = summary.get("notable_quotes") or []
    text = chunk.get("text") or ""
    if not text:
        return 0.0

    bonus = 0.0
    lower = text.lower()
    for q in quotes:
        qt = (q.get("text") or "").lower().strip()
        if qt and qt in lower:
            bonus = 0.35
            break

    if not key_points:
        return min(1.0, 0.2 + bonus)

    if get_settings().light_mode:
        words = set(text.lower().split())
        scores = []
        for kp in key_points:
            kp_words = set(kp.lower().split())
            if not kp_words:
                continue
            scores.append(len(words & kp_words) / len(kp_words))
        salience = max(scores) if scores else 0.2
        return min(1.0, salience + bonus)

    try:
        model = _get_embedder()
        emb_chunk = model.encode([text], normalize_embeddings=True)[0]
        emb_points = model.encode(key_points, normalize_embeddings=True)
        sims = emb_points @ emb_chunk
        salience = float(np.max(sims))
    except Exception:  # noqa: BLE001
        words = set(text.lower().split())
        scores = []
        for kp in key_points:
            kp_words = set(kp.lower().split())
            if not kp_words:
                continue
            scores.append(len(words & kp_words) / len(kp_words))
        salience = max(scores) if scores else 0.2

    return min(1.0, salience + bonus)


def _overlap(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    return max(0.0, min(a_end, b_end) - max(a_start, b_start))


def compute_highlight_scores(
    scenes: list[dict],
    chunks: list[dict],
    audio_path: str | Path,
    summary: dict,
) -> list[dict]:
    settings = get_settings()

    if settings.light_mode:
        norm_energy = [0.4] * len(scenes)
    else:
        try:
            import librosa

            y, sr = librosa.load(str(audio_path), sr=16000, mono=True)
            energies = []
            for s in scenes:
                a = max(0, int(s["start"] * sr))
                b = min(len(y), int(s["end"] * sr))
                if b <= a:
                    energies.append(0.0)
                else:
                    window = y[a:b]
                    energies.append(float(np.sqrt(np.mean(np.square(window)) + 1e-12)))
            norm_energy = _normalize(energies)
        except Exception:  # noqa: BLE001
            logger.warning("Audio energy failed; using flat scores")
            norm_energy = [0.4] * len(scenes)

    scored: list[dict] = []
    for scene, energy in zip(scenes, norm_energy):
        overlapping = [
            c
            for c in chunks
            if _overlap(scene["start"], scene["end"], c["start"], c["end"]) > 0
        ]
        if overlapping:
            salience = max(compute_transcript_salience(c, summary) for c in overlapping)
        else:
            salience = 0.0

        motion = float(scene.get("motion_score") or 0.0)
        energy_f = float(energy)
        if settings.light_mode and scenes:
            mid = len(scenes) / 2.0
            pos = 1.0 - abs(scene["scene_index"] - mid) / max(mid, 1.0)
            energy_f = 0.3 * energy_f + 0.7 * pos

        score = 0.4 * motion + 0.3 * energy_f + 0.3 * salience
        scored.append(
            {
                "scene_index": scene["scene_index"],
                "start": scene["start"],
                "end": scene["end"],
                "score": float(score),
                "motion_score": motion,
                "audio_energy": energy_f,
                "transcript_salience": float(salience),
                "selected": False,
            }
        )
    return scored


def select_highlights(
    scored_scenes: list[dict],
    target_duration_seconds: float,
) -> list[dict]:
    if not scored_scenes:
        return []

    total_video = sum(s["end"] - s["start"] for s in scored_scenes)
    if target_duration_seconds >= total_video:
        selected = [dict(s, selected=True) for s in scored_scenes]
        selected.sort(key=lambda s: s["start"])
        return selected

    ranked = sorted(scored_scenes, key=lambda s: s["score"], reverse=True)
    picked: list[dict] = []
    duration = 0.0
    for scene in ranked:
        seg_dur = scene["end"] - scene["start"]
        if duration + seg_dur > target_duration_seconds and picked:
            if duration >= target_duration_seconds * 0.85:
                break
        picked.append(dict(scene, selected=True))
        duration += seg_dur
        if duration >= target_duration_seconds:
            break

    picked.sort(key=lambda s: s["start"])
    return picked


def score_and_select(
    job_id: str,
    scenes: list[dict],
    chunks: list[dict],
    audio_path: str | Path,
    summary: dict,
) -> dict:
    settings = get_settings()
    scored = compute_highlight_scores(scenes, chunks, audio_path, summary)
    selected = select_highlights(scored, settings.highlight_target_duration_seconds)
    selected_idxs = {s["scene_index"] for s in selected}
    for s in scored:
        s["selected"] = s["scene_index"] in selected_idxs

    result = {
        "segments": selected,
        "all_scored": scored,
        "total_duration": sum(s["end"] - s["start"] for s in selected),
        "target_duration": settings.highlight_target_duration_seconds,
    }
    out = settings.storage_dir / "uploads" / job_id / "highlights.json"
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def load_highlights(job_id: str) -> dict | None:
    settings = get_settings()
    path = settings.storage_dir / "uploads" / job_id / "highlights.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
