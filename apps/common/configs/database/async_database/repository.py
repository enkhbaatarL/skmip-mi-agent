# repository.py
from collections.abc import Callable
from typing import Annotated, TypeVar

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.configs.database.async_database.base import BaseAsyncSQLRepository
from src.core.configs.database.async_database.session import get_async_session


TRepo = TypeVar("TRepo", bound=BaseAsyncSQLRepository)


def get_repository(repo_type: type[TRepo]) -> Callable[[Annotated[AsyncSession, Depends(get_async_session)]], TRepo]:
    def _get_repo(session: Annotated[AsyncSession, Depends(get_async_session)]) -> TRepo:
        return repo_type(async_session=session)

    return _get_repo
