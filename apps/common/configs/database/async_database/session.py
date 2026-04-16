# apps/core/configs/database/async_database/session.py
from collections.abc import AsyncIterator
from typing import cast

from fastapi import Depends, FastAPI, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from src.core.values.constants.app_state import STATE_DB_ATTR

from .connection import AsyncDatabase, require_ready


async def get_async_db(request: Request) -> AsyncDatabase:
    app = cast("FastAPI", request.app)
    db = getattr(app.state, STATE_DB_ATTR, None)
    if not isinstance(db, AsyncDatabase):
        raise HTTPException(HTTP_500_INTERNAL_SERVER_ERROR, "DB handle missing")
    return db


async def get_async_session(db: AsyncDatabase = Depends(get_async_db)) -> AsyncIterator[AsyncSession]:
    require_ready(db)
    sm = db.sessionmaker
    if sm is None:
        raise HTTPException(HTTP_500_INTERNAL_SERVER_ERROR, "Session factory not initialized")
    async with sm() as session:
        yield session
