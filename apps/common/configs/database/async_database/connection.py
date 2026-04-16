# apps/core/configs/database/async_database/connection.py

import asyncio

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from starlette.status import HTTP_503_SERVICE_UNAVAILABLE

from src.core.configs.settings.base import BackendBaseSettings


def _resolve_driver(db_type: str) -> str:
    t = (db_type or "").lower()
    if t in ("postgres", "postgresql", "pg"):
        return "postgresql+psycopg"
    if t in ("mysql",):
        return "mysql+asyncmy"
    if t in ("mariadb", "maria"):
        return "mariadb+asyncmy"
    raise ValueError(f"Unsupported METADATA_DB_TYPE: {db_type}")


class AsyncDatabase:
    def __init__(self, settings: BackendBaseSettings) -> None:
        self._settings = settings
        self._lock = asyncio.Lock()
        self._ready = False
        self.dsn: URL | None = None
        self.async_engine: AsyncEngine | None = None
        self.sessionmaker: async_sessionmaker[AsyncSession] | None = None

    def _build(self) -> None:
        driver = _resolve_driver(self._settings.METADATA_DB_TYPE)

        query: dict[str, object] = {}

        if driver.startswith("mysql+"):
            query.update(
                {
                    "charset": "utf8mb4",
                    "connect_timeout": self._settings.DB_CONNECTION_TIMEOUT_SECONDS,
                    "read_timeout": self._settings.READ_TIMEOUT_SECONDS,
                },
            )

        elif driver.startswith("postgresql+"):
            query.update({"connect_timeout": self._settings.DB_CONNECTION_TIMEOUT_SECONDS})

        self.dsn = URL.create(
            drivername=driver,
            host=self._settings.METADATA_DB_HOST,
            port=self._settings.METADATA_DB_PORT,
            database=self._settings.METADATA_DB_NAME,
            username=self._settings.METADATA_DB_USERNAME,
            password=self._settings.METADATA_DB_PASSWORD,
        )

        self.async_engine = create_async_engine(
            self.dsn,
            echo=self._settings.IS_DB_ECHO_LOG,
            pool_size=self._settings.DB_POOL_SIZE,
            max_overflow=self._settings.DB_POOL_OVERFLOW,
            pool_timeout=self._settings.DB_POOL_TIMEOUT_SECONDS,
            pool_recycle=self._settings.POOL_RECYCLE_SECONDS,
            pool_pre_ping=self._settings.POOL_PRE_PING,
            echo_pool=self._settings.ECHO_POOL,
        )

        self.sessionmaker = async_sessionmaker(
            bind=self.async_engine,
            expire_on_commit=self._settings.IS_DB_EXPIRE_ON_COMMIT,
            autoflush=False,
        )

    async def startup(self) -> None:
        async with self._lock:
            if self.async_engine is None:
                self._build()
            await self._healthcheck()
            warm_pool_conns = self._settings.DB_POOL_WARM_CONNS
            if warm_pool_conns:
                assert self.async_engine is not None
                for _ in range(warm_pool_conns):
                    async with self.async_engine.connect() as conn:
                        await conn.execute(text("SELECT 1"))
                        await conn.commit()
            self._ready = True

    async def shutdown(self) -> None:
        async with self._lock:
            if self.async_engine is not None:
                await self.async_engine.dispose()
            self._ready = False

    async def _healthcheck(self) -> None:
        if self.sessionmaker is None:
            self._build()
        assert self.sessionmaker is not None
        async with self.sessionmaker() as s:
            await s.execute(text("SELECT 1"))

    @property
    def ready(self) -> bool:
        return self._ready

    def rendered_url(self, show_password: bool = False) -> str:
        assert self.async_engine is not None
        return self.async_engine.sync_engine.url.render_as_string(
            hide_password=not show_password,
        )


def require_ready(db: "AsyncDatabase") -> "AsyncDatabase":
    if not db.ready:
        raise HTTPException(HTTP_503_SERVICE_UNAVAILABLE, "DB not ready")
    return db
