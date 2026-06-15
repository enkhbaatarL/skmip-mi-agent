#   apps/agents/event_flow_agent/services/record_source_service.py
#   kmj20260421화 생성
"""
원천 record 조회 서비스 모듈

역할:
- event_flow_agent가 분석할 원천 뉴스/레코드를 DB에서 조회한다.
- 조회 조건(market_category, 기간, limit)에 맞는 record 목록을 반환한다.

입력:
- 시장 구분
- 조회 기간
- 조회 건수 제한

출력:
- 원천 record 목록(list[dict])

설계 의도:
- node는 흐름 제어만 담당하고,
  실제 DB 세션 생성/종료 및 repository 호출은 service 계층에서 처리
- 원천 데이터 조회 책임을 독립된 서비스로 분리하여 재사용성과 테스트 용이성 확보
"""

from __future__ import annotations
from datetime import datetime

from apps.agents.event_flow_agent.repositories.sync_record_repository import (
    SyncRecordRepository,
)
from apps.common.configs.database.sync_database.connection import get_sync_session
from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode


class RecordSourceService:
    def fetch_news_records(
        self,
        market_category: str = "LNG",
        limit: int = 50,
        from_first_created: str | None = None,
        to_first_created: str | None = None,
    ) -> list[dict]:
        session = get_sync_session()

        try:
            repository = SyncRecordRepository(session=session)
            records = repository.fetch_news_records(
                market_category=market_category,
                limit=limit,
                from_first_created=from_first_created,
                to_first_created=to_first_created,
            )
            
            # Convert datetime objects to ISO strings (prevent JSON serialization errors)
            for record in records:
                if isinstance(record.get('first_created'), datetime):
                    record['first_created'] = record['first_created'].isoformat()
            
            return records
        except Exception as exc:
            raise MIBaseError(ErrorCode.RDB_DATA_FETCH_FAILED, detail=str(exc)) from exc
        finally:
            session.close()