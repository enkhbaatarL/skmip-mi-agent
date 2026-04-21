#   apps/common/configs/database/sync_database/repository.py

"""Sync Repository DI 팩토리 (FastAPI Depends 전용)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, TypeVar

from fastapi import Depends
from sqlalchemy.orm import Session

from apps.common.configs.database.sync_database.base import BaseSyncSQLRepository
from apps.common.configs.database.sync_database.session import get_sync_db


TRepo = TypeVar("TRepo", bound=BaseSyncSQLRepository)


def get_repository(repo_type: type[TRepo]) -> Callable[[Annotated[Session, Depends(get_sync_db)]], TRepo]:
    def _get_repo(session: Annotated[Session, Depends(get_sync_db)]) -> TRepo:
        return repo_type(session=session)

    return _get_repo
