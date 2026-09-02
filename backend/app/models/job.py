"""SQLAlchemy models for processing jobs."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class JobStatus(str, enum.Enum):
    uploaded = "uploaded"
    extracting_audio = "extracting_audio"
    transcribing = "transcribing"
    transcribed = "transcribed"
    segmented = "segmented"
    analyzing_scenes = "analyzing_scenes"
    scenes_analyzed = "scenes_analyzed"
    summarizing = "summarizing"
    summarized = "summarized"
    scoring_highlights = "scoring_highlights"
    highlights_scored = "highlights_scored"
    rendering = "rendering"
    complete = "complete"
    failed = "failed"


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    original_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    audio_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    highlight_reel_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, native_enum=False),
        default=JobStatus.uploaded,
        nullable=False,
    )
    progress_percent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fps: Mapped[float | None] = mapped_column(Float, nullable=True)
    codec: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
