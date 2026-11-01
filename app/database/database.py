"""Database engine and session management."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.database.models import Base

_engine = None
_SessionLocal = None


def get_engine():
    """Return (and lazily create) the global SQLAlchemy engine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        db_path = settings.get_db_path()
        db_path.parent.mkdir(parents=True, exist_ok=True)

        _engine = create_engine(
            settings.database_url,
            echo=False,
            pool_pre_ping=True,
            connect_args=(
                {"check_same_thread": False}
                if "sqlite" in settings.database_url
                else {}
            ),
        )

        # Enable WAL mode and foreign keys for SQLite
        if "sqlite" in settings.database_url:

            @event.listens_for(_engine, "connect")
            def _set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

    return _engine


def get_session_factory():
    """Return (and lazily create) the global session factory."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(), autocommit=False, autoflush=False
        )
    return _SessionLocal


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Provide a transactional session scope."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """Create all tables that don't already exist."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)


def drop_db() -> None:
    """Drop all tables — use with extreme caution."""
    engine = get_engine()
    Base.metadata.drop_all(bind=engine)
