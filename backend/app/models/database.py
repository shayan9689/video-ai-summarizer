"""Database engine and session helpers.

Uses Supabase Postgres when DATABASE_URL is set; otherwise local SQLite.
"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.models.job import Base

settings = get_settings()

_connect_args: dict = {}
_url = settings.resolved_database_url
if _url.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}

engine = create_engine(_url, connect_args=_connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
