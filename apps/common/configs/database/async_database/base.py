#   apps/common/configs/database/async_database/base.py

from sqlalchemy.ext.asyncio import AsyncSession as SQLAlchemyAsyncSession


class BaseAsyncSQLRepository:
    def __init__(self, async_session: SQLAlchemyAsyncSession):
        self.async_session = async_session
