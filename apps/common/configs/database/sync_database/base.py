#   apps/common/configs/database/sync_database/base.py
#   kmj20260423목,  주석추가
"""
Sync DB Repository 베이스 클래스 모듈

역할:
- 모든 Sync DB Repository가 공통으로 상속받는 기본 클래스 정의
- SQLAlchemy Session 객체를 주입받아 보관한다
- SQLAlchemy ORM DeclarativeBase 공유 베이스 제공

주요 기능:
- self.session을 통해 DB 쿼리 수행 가능
- ORMBase를 통해 모든 ORM 모델이 공통 베이스 사용

설계 의도:
- Repository 계층에서 DB 세션 전달 방식을 일관되게 유지
- 공통 인터페이스 없이도 최소한의 구조 통일성 확보
- 향후 공통 로직(logging, retry, audit 등) 확장 가능

아키텍처 위치:
- Repository 계층의 최상위 공통 베이스
"""

from sqlalchemy.orm import DeclarativeBase, Session as SQLAlchemySession


class ORMBase(DeclarativeBase):
    """SQLAlchemy ORM 모델을 위한 DeclarativeBase.

    모든 agent의 ORM 모델은 이 클래스를 상속받아야 한다.
    """
    pass


class BaseSyncSQLRepository:
    """Sync Repository 베이스 클래스."""

    def __init__(self, session: SQLAlchemySession) -> None:
        self.session = session