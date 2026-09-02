"""LLM-based map-reduce summarization (Anthropic preferred, OpenAI fallback)."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from app.config import get_settings

logger = logging.getLogger(__name__)

DIRECT_CHAR_THRESHOLD = 6000
CHARS_PER_TOKEN_EST = 4


class SummarizationError(RuntimeError):
    pass


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // CHARS_PER_TOKEN_EST)


def _client():
    settings = get_settings()
    if settings.anthropic_api_key:
        import anthropic

        return "anthropic", anthropic.Anthropic(api_key=settings.anthropic_api_key)
    if settings.openai_api_key:
        from openai import OpenAI

        return "openai", OpenAI(api_key=settings.openai_api_key)
    return None, None


def _offline_summary(chunks: list[dict], video_title: str | None = None) -> dict:
    """Deterministic fallback when no LLM API key is configured (local/dev)."""
    texts = [c.get("text", "") for c in chunks if c.get("text")]
    joined = " ".join(texts)
    overview = (
        f"Offline summary for {video_title or 'video'}: "
        + (joined[:280] + ("…" if len(joined) > 280 else ""))
        if joined
        else f"Offline summary for {video_title or 'video'} (empty transcript)."
    )
    key_points = []
    for c in chunks[:6]:
        t = (c.get("text") or "").strip()
        if t:
            key_points.append(t[:120] + ("…" if len(t) > 120 else ""))
    if not key_points:
        key_points = ["No transcript content available."]
    quotes = []
    for c in chunks[:3]:
        t = (c.get("text") or "").strip()
        if t:
            quotes.append({"text": t[:100], "timestamp": float(c.get("start") or 0.0)})
    return {"overview": overview, "key_points": key_points, "notable_quotes": quotes}


def _chat(system: str, user: str) -> str:
    provider, client = _client()
    if provider is None or client is None:
        raise SummarizationError(
            "No LLM API key configured. Set ANTHROPIC_API_KEY or OPENAI_API_KEY in .env"
        )
    if provider == "anthropic":
        msg = client.messages.create(
            model="claude-3-5-haiku-latest",
            max_tokens=2048,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(block.text for block in msg.content if hasattr(block, "text"))
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.3,
    )
    return resp.choices[0].message.content or ""


def _parse_json(raw: str) -> dict:
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    # Find outermost object
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    return json.loads(text)


def summarize_chunk(chunk_text: str) -> str:
    system = "You summarize spoken video transcripts. Be concise and factual."
    user = f"Summarize this transcript chunk in one paragraph:\n\n{chunk_text}"
    return _chat(system, user).strip()


def reduce_summaries(chunk_summaries: list[str], video_title: str | None = None) -> dict:
    title_line = f"Video title: {video_title}\n" if video_title else ""
    joined = "\n\n".join(f"- {s}" for s in chunk_summaries)
    system = (
        "You create structured video summaries. Return ONLY valid JSON with keys: "
        "overview (string, 2-3 sentences), key_points (array of 5-8 strings), "
        "notable_quotes (array of objects with text and timestamp float; use 0.0 if unknown)."
    )
    user = (
        f"{title_line}Combine these chunk summaries into one structured JSON summary:\n\n{joined}"
    )
    raw = _chat(system, user)
    try:
        return _parse_json(raw)
    except json.JSONDecodeError:
        raw2 = _chat(
            system + " Return only valid JSON. No markdown fences, no preamble.",
            user,
        )
        return _parse_json(raw2)


def summarize_transcript_direct(full_text: str, video_title: str | None = None) -> dict:
    title_line = f"Video title: {video_title}\n" if video_title else ""
    system = (
        "You create structured video summaries from transcripts. Return ONLY valid JSON with keys: "
        "overview (string, 2-3 sentences), key_points (array of 5-8 strings), "
        "notable_quotes (array of {text: string, timestamp: float} — pick real quotes "
        "and approximate timestamps from context if present as [mm:ss] markers; else 0.0)."
    )
    user = f"{title_line}Transcript:\n\n{full_text}"
    raw = _chat(system, user)
    try:
        return _parse_json(raw)
    except json.JSONDecodeError:
        raw2 = _chat(system + " Return only valid JSON.", user)
        return _parse_json(raw2)


def summarize_job(job_id: str, chunks: list[dict], video_title: str | None = None) -> dict:
    settings = get_settings()
    full_text = "\n".join(
        f"[{c['start']:.1f}s] {c['text']}" for c in chunks
    )
    est_tokens = _estimate_tokens(full_text)
    logger.info("Job %s estimated summary input tokens: %s", job_id, est_tokens)
    if est_tokens > settings.max_summary_input_tokens:
        raise SummarizationError(
            f"Transcript too long ({est_tokens} tokens) for limit "
            f"{settings.max_summary_input_tokens}"
        )

    provider, _client_obj = _client()
    if provider is None:
        logger.warning("No LLM API key — using offline summary fallback for job %s", job_id)
        summary = _offline_summary(chunks, video_title=video_title)
    elif len(full_text) <= DIRECT_CHAR_THRESHOLD:
        summary = summarize_transcript_direct(full_text, video_title=video_title)
    else:
        partials = [summarize_chunk(c["text"]) for c in chunks]
        summary = reduce_summaries(partials, video_title=video_title)

    # Normalize shape
    summary.setdefault("overview", "")
    summary.setdefault("key_points", [])
    summary.setdefault("notable_quotes", [])
    if not isinstance(summary["key_points"], list):
        summary["key_points"] = [str(summary["key_points"])]
    quotes = []
    for q in summary.get("notable_quotes") or []:
        if isinstance(q, dict):
            quotes.append(
                {
                    "text": str(q.get("text", "")),
                    "timestamp": float(q.get("timestamp") or 0.0),
                }
            )
        elif isinstance(q, str):
            quotes.append({"text": q, "timestamp": 0.0})
    summary["notable_quotes"] = quotes

    out = settings.storage_dir / "uploads" / job_id / "summary.json"
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def load_summary(job_id: str) -> dict | None:
    settings = get_settings()
    path = settings.storage_dir / "uploads" / job_id / "summary.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
