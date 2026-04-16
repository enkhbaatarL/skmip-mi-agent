"""Sync Database 연결 설정 (Airflow 등 비-FastAPI 환경용)."""

from __future__ import annotations

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session, sessionmaker

from apps.common.configs.settings import settings


def _resolve_sync_driver(db_type: str) -> str:
    """DB 타입에 맞는 sync 드라이버를 반환한다."""
    t = (db_type or "").lower()
    if t in ("postgres", "postgresql", "pg"):
        return "postgresql+psycopg2"
    if t in ("mysql",):
        return "mysql+pymysql"
    if t in ("mariadb", "maria"):
        return "mariadb+pymysql"
    msg = f"Unsupported METADATA_DB_TYPE: {db_type}"
    raise ValueError(msg)


def _build_sync_dsn() -> URL:
    """Sync용 DSN을 생성한다."""
    driver = _resolve_sync_driver(settings.METADATA_DB_TYPE)

    return URL.create(
        drivername=driver,
        host=settings.METADATA_DB_HOST,
        port=settings.METADATA_DB_PORT,
        database=settings.METADATA_DB_NAME,
        username=settings.METADATA_DB_USERNAME,
        password=settings.METADATA_DB_PASSWORD,
    )


def _create_sync_engine() -> Engine:
    """Sync SQLAlchemy 엔진을 생성한다."""
    dsn = _build_sync_dsn()

    connect_args: dict = {}
    if dsn.drivername.startswith("mysql+"):
        connect_args.update({
            "charset": "utf8mb4",
            "connect_timeout": settings.DB_CONNECTION_TIMEOUT_SECONDS,
            "read_timeout": settings.READ_TIMEOUT_SECONDS,
        })

    return create_engine(
        dsn,
        echo=settings.IS_DB_ECHO_LOG,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_POOL_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT_SECONDS,
        pool_recycle=settings.POOL_RECYCLE_SECONDS,
        pool_pre_ping=settings.POOL_PRE_PING,
        connect_args=connect_args,
    )


# 모듈 레벨 싱글톤
_sync_engine: Engine | None = None
_sync_session_factory: sessionmaker[Session] | None = None


def get_sync_engine() -> Engine:
    """Sync 엔진 싱글톤을 반환한다."""
    global _sync_engine  # noqa: PLW0603
    if _sync_engine is None:
        _sync_engine = _create_sync_engine()
    return _sync_engine


def get_sync_session_factory() -> sessionmaker[Session]:
    """Sync 세션 팩토리 싱글톤을 반환한다."""
    global _sync_session_factory  # noqa: PLW0603
    if _sync_session_factory is None:
        _sync_session_factory = sessionmaker(
            bind=get_sync_engine(),
            expire_on_commit=settings.IS_DB_EXPIRE_ON_COMMIT,
            autoflush=False,
        )
    return _sync_session_factory


def get_sync_session() -> Session:
    """새로운 Sync DB 세션을 반환한다.

    사용 후 반드시 session.close()를 호출하거나 context manager로 사용해야 한다.

    Example:
        session = get_sync_session()
        try:
            # do something
            session.commit()
        finally:
            session.close()

        # 또는 context manager 사용
        with get_sync_session() as session:
            # do something
            session.commit()
    """
    return get_sync_session_factory()()


def healthcheck() -> bool:
    """DB 연결 상태를 확인한다."""
    try:
        with get_sync_session() as session:
            session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
