"""Slow integration test — skipped unless --runslow and sample video present."""

from pathlib import Path

import pytest

SAMPLE = Path(__file__).parent / "fixtures" / "sample.mp4"


@pytest.mark.slow
def test_full_pipeline_produces_reel(tmp_path, monkeypatch):
    if not SAMPLE.exists():
        pytest.skip("Place a ~15s sample.mp4 under backend/tests/fixtures/")

    monkeypatch.setenv("STORAGE_DIR", str(tmp_path))
    # Force re-import settings after env change
    from app.config import get_settings

    get_settings.cache_clear()

    # This test is intentionally manual/slow; document presence here.
    pytest.skip("Enable after providing ANTHROPIC_API_KEY and sample.mp4 — run with -m slow")
