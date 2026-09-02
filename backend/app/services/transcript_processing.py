"""Transcript post-processing: sentences, topic chunks, filler cleanup."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

import numpy as np

from app.config import get_settings

logger = logging.getLogger(__name__)

_embedder = None

# Conservative standalone fillers only
_FILLER_RE = re.compile(
    r"\b(?:um|uh|uhm|erm|hmm|mm+|ah+)\b[,.]?",
    re.IGNORECASE,
)


def clean_transcript_text(text: str) -> str:
    cleaned = _FILLER_RE.sub("", text)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    cleaned = re.sub(r"\s+([,.!?])", r"\1", cleaned)
    return cleaned


def reconstruct_sentences(segments: list[dict]) -> list[dict]:
    """Merge Whisper segments into sentences using punctuation boundaries."""
    sentences: list[dict] = []
    buf_text: list[str] = []
    buf_start: float | None = None
    buf_end: float = 0.0

    def flush():
        nonlocal buf_text, buf_start, buf_end
        if not buf_text or buf_start is None:
            return
        text = clean_transcript_text(" ".join(buf_text).strip())
        if text:
            sentences.append({"start": buf_start, "end": buf_end, "text": text})
        buf_text = []
        buf_start = None

    for seg in segments:
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        if buf_start is None:
            buf_start = float(seg["start"])
        buf_end = float(seg["end"])
        buf_text.append(text)
        if re.search(r"[.!?…][\"')\]]*$", text):
            flush()

    flush()
    if not sentences and segments:
        # Fallback: treat each segment as a sentence
        for seg in segments:
            text = clean_transcript_text((seg.get("text") or "").strip())
            if text:
                sentences.append(
                    {
                        "start": float(seg["start"]),
                        "end": float(seg["end"]),
                        "text": text,
                    }
                )
    return sentences


def _get_embedder():
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer

        logger.info("Loading sentence-transformers model: all-MiniLM-L6-v2")
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedder


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def chunk_by_topic(
    sentences: list[dict],
    max_chunk_seconds: float = 45.0,
    similarity_threshold: float = 0.5,
) -> list[dict]:
    """Group sentences into topical chunks via embedding centroid similarity."""
    if not sentences:
        return []

    # Short transcripts: skip heavy model — single / time-based chunks
    if len(sentences) == 1:
        s = sentences[0]
        return [
            {
                "start": s["start"],
                "end": s["end"],
                "text": s["text"],
                "sentence_count": 1,
            }
        ]

    try:
        model = _get_embedder()
        texts = [s["text"] for s in sentences]
        embeddings = model.encode(texts, normalize_embeddings=True)
        embeddings = np.asarray(embeddings, dtype=np.float32)
    except Exception:  # noqa: BLE001
        logger.warning("Embedding model unavailable; falling back to time-based chunks")
        return _time_based_chunks(sentences, max_chunk_seconds)

    chunks: list[dict] = []
    current_idxs = [0]
    centroid = embeddings[0].copy()

    def emit(idxs: list[int]):
        group = [sentences[i] for i in idxs]
        chunks.append(
            {
                "start": group[0]["start"],
                "end": group[-1]["end"],
                "text": " ".join(g["text"] for g in group),
                "sentence_count": len(group),
            }
        )

    for i in range(1, len(sentences)):
        sim = _cosine(centroid, embeddings[i])
        span = float(sentences[i]["end"] - sentences[current_idxs[0]]["start"])
        if sim < similarity_threshold or span > max_chunk_seconds:
            emit(current_idxs)
            current_idxs = [i]
            centroid = embeddings[i].copy()
        else:
            current_idxs.append(i)
            # Running mean centroid
            n = len(current_idxs)
            centroid = ((n - 1) * centroid + embeddings[i]) / n

    emit(current_idxs)
    return chunks


def _time_based_chunks(sentences: list[dict], max_chunk_seconds: float) -> list[dict]:
    chunks: list[dict] = []
    current: list[dict] = []
    for s in sentences:
        if current and float(s["end"] - current[0]["start"]) > max_chunk_seconds:
            chunks.append(
                {
                    "start": current[0]["start"],
                    "end": current[-1]["end"],
                    "text": " ".join(c["text"] for c in current),
                    "sentence_count": len(current),
                }
            )
            current = []
        current.append(s)
    if current:
        chunks.append(
            {
                "start": current[0]["start"],
                "end": current[-1]["end"],
                "text": " ".join(c["text"] for c in current),
                "sentence_count": len(current),
            }
        )
    return chunks


def process_and_save_chunks(job_id: str, segments: list[dict]) -> list[dict]:
    sentences = reconstruct_sentences(segments)
    chunks = chunk_by_topic(sentences)
    settings = get_settings()
    out = settings.storage_dir / "uploads" / job_id / "chunks.json"
    out.write_text(
        json.dumps({"sentences": sentences, "chunks": chunks}, indent=2),
        encoding="utf-8",
    )
    return chunks


def load_chunks(job_id: str) -> dict | None:
    settings = get_settings()
    path = settings.storage_dir / "uploads" / job_id / "chunks.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
