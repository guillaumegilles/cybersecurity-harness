"""Database engine/session management.

Schema is managed via SQLAlchemy metadata (create_all) for the SQLite
dev/evaluation environment; alembic migrations are deferred to the
PostgreSQL pilot (documented deviation from T006).
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from harness.config.settings import get_settings
from harness.storage.models import Base

_engine = None
_session_factory: sessionmaker | None = None


def init_db(database_url: str | None = None):
    global _engine, _session_factory
    url = database_url or get_settings().database_url
    _engine = create_engine(url, connect_args={"check_same_thread": False} if url.startswith("sqlite") else {})
    Base.metadata.create_all(_engine)
    _session_factory = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


def get_session() -> Session:
    if _session_factory is None:
        init_db()
    assert _session_factory is not None
    return _session_factory()
