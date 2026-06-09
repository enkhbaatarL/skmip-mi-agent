#   apps/common/configs/database/sync_database/__init__.py

"""Sync Database 모듈."""

from apps.common.configs.database.sync_database.base import BaseSyncSQLRepository


__all__ = [
    "BaseSyncSQLRepository",
    "get_sync_db",
    "get_sync_engine",
    "get_sync_session",
    "get_sync_session_factory",
    "healthcheck",
]


def __getattr__(name: str):
    if name in {"get_sync_engine", "get_sync_session", "get_sync_session_factory", "healthcheck"}:
        from apps.common.configs.database.sync_database import connection

        return getattr(connection, name)
    if name == "get_sync_db":
        from apps.common.configs.database.sync_database.session import get_sync_db

        return get_sync_db
    raise AttributeError(name)
