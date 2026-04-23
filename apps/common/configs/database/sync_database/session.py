#   apps/common/configs/database/sync_database/session.py
#   kmj20260423목,  주석추가
"""
FastAPI DI용 Sync DB 세션 제공 모듈

역할:
- FastAPI의 Depends를 통해 DB Session을 주입하기 위한 provider 정의
- 요청 단위로 Session을 생성하고, 종료 시 자동 정리

주요 기능:
- 요청 시작 시 Session 생성
- 예외 발생 시 rollback 수행
- 요청 종료 시 session.close() 보장

설계 의도:
- FastAPI 환경에서 안전한 트랜잭션 관리
- 세션 lifecycle을 DI 컨테이너에 위임
- 서비스/레포지토리에서 세션 관리 책임 제거

아키텍처 위치:
- API Layer ↔ DB Layer 연결 (Dependency Injection)
"""

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
