#   apps/common/configs/database/sync_database/repository.py
#   kmj20260423목,  주석추가
"""
Sync Repository DI 팩토리 모듈 (FastAPI 전용)

역할:
- 특정 Repository 클래스를 FastAPI Depends로 주입할 수 있도록 래핑
- Session → Repository 객체 생성 흐름을 자동화

주요 기능:
- get_repository(repo_type) 호출 시
  해당 repo에 Session을 주입하여 인스턴스 생성

사용 예:
- Depends(get_repository(UserRepository))

설계 의도:
- FastAPI에서 Repository 주입을 표준화
- Service 계층에서 Repository 생성 책임 제거
- 테스트 및 mocking 구조 단순화

아키텍처 위치:
- API Layer에서 Repository를 주입받기 위한 DI 유틸
"""

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
