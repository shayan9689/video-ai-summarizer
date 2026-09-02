"""Unit tests for highlight scoring and topic chunking."""

from app.services.highlight_scoring import select_highlights
from app.services.transcript_processing import chunk_by_topic, clean_transcript_text


def test_select_highlights_chronological_and_duration():
    scenes = [
        {"scene_index": 0, "start": 0, "end": 10, "score": 0.2},
        {"scene_index": 1, "start": 10, "end": 20, "score": 0.9},
        {"scene_index": 2, "start": 20, "end": 30, "score": 0.8},
        {"scene_index": 3, "start": 30, "end": 40, "score": 0.1},
    ]
    selected = select_highlights(scenes, target_duration_seconds=20)
    assert [s["start"] for s in selected] == sorted(s["start"] for s in selected)
    total = sum(s["end"] - s["start"] for s in selected)
    assert total <= 25  # slight overrun allowed by algorithm
    assert selected[0]["start"] <= selected[-1]["start"]
    # Highest scores should be preferred
    idxs = {s["scene_index"] for s in selected}
    assert 1 in idxs and 2 in idxs


def test_select_highlights_when_target_exceeds_video():
    scenes = [
        {"scene_index": 0, "start": 0, "end": 5, "score": 0.5},
        {"scene_index": 1, "start": 5, "end": 10, "score": 0.6},
    ]
    selected = select_highlights(scenes, target_duration_seconds=999)
    assert len(selected) == 2


def test_chunk_by_topic_respects_max_seconds():
    sentences = [
        {"start": 0.0, "end": 5.0, "text": "Hello world one."},
        {"start": 5.0, "end": 10.0, "text": "Hello world two."},
        {"start": 10.0, "end": 50.0, "text": "Completely different topic about rockets."},
        {"start": 50.0, "end": 55.0, "text": "More rockets and spaceflight."},
    ]
    chunks = chunk_by_topic(sentences, max_chunk_seconds=20, similarity_threshold=0.99)
    assert len(chunks) >= 2
    for c in chunks:
        assert c["end"] - c["start"] <= 45 or c["sentence_count"] == 1


def test_clean_filler_words():
    assert "hello" in clean_transcript_text("um hello uh there").lower()
    assert "um" not in clean_transcript_text("um hello").lower().split()
