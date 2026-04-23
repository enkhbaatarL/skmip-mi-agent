#   apps/common/configs/database/sync_database/connection.py
#   kmj20260423목,  주석추가
"""
Sync DB 연결 및 SQLAlchemy 엔진/세션 팩토리 생성 모듈

역할:
- 환경설정(Settings)을 기반으로 DB 연결 정보(DSN)를 구성
- SQLAlchemy Engine 및 SessionFactory를 싱글톤으로 생성/관리
- DB 세션을 생성하는 진입점(get_sync_session) 제공

주요 기능:
- DB 타입에 따른 driver 자동 선택 (Postgres/MySQL/MariaDB)
- Engine 생성 (pool 설정 포함)
- SessionFactory 생성
- Session 생성
- DB healthcheck 기능

설계 의도:
- DB 연결 객체를 애플리케이션 전체에서 싱글톤으로 재사용
- 커넥션 풀 및 타임아웃 정책을 중앙에서 관리
- 서비스/레포지토리에서 DB 연결 세부 구현을 몰라도 되도록 추상화

주의사항:
- get_sync_session()으로 생성한 세션은 반드시 close 필요
- context manager 또는 try-finally 패턴 사용 권장

아키텍처 위치:
- DB 연결의 단일 진입점 (Infrastructure Layer)
"""

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
