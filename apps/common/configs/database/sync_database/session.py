#   apps/common/configs/database/sync_database/session.py

"""Sync Database 세션 DI 프로바이더 (FastAPI Depends 전용)."""

from __future__ import annotations
from collections.abc import Generator
from sqlalchemy.orm import Session
from apps.common.configs.database.sync_database.connection import get_sync_session


def get_sync_db() -> Generator[Session, None, None]:
    """FastAPI DI용 Sync DB 세션 제공자."""
    session = get_sync_session()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
