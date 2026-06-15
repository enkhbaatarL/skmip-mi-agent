#   apps/agents/event_flow_agent/services/event_service.py
#   kmj20260421화 수정
"""
저장된 event 조회 서비스 모듈

역할:
- DB에 저장된 event 데이터를 조회하여 반환한다.
- limit 조건에 따라 최신 event 목록을 가져온다.

입력:
- 조회 건수 제한(limit)

출력:
- event 목록(list[dict])

설계 의도:
- node는 조회 흐름만 담당하고,
  실제 DB 세션 및 repository 호출은 service 계층에서 처리
- 저장 후 재조회 및 후속 요약 단계에서 공통으로 사용할 수 있는 event 조회 책임 분리
"""

from __future__ import annotations

from apps.agents.event_flow_agent.repositories.sync_event_repository import SyncEventRepository
from apps.common.configs.database.sync_database.connection import get_sync_session
from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode


class EventService:
    def get_events(self, limit: int = 10) -> list[dict]:
        if limit <= 0:
            return []
        if limit > 100:
            limit = 100

        session = get_sync_session()

        try:
            repo = SyncEventRepository(session=session)
            return repo.fetch_events(limit=limit)
        except Exception as exc:
            raise MIBaseError(ErrorCode.RDB_DATA_FETCH_FAILED, detail=str(exc)) from exc
        finally:
            session.close()