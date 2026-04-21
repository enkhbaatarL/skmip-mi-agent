#   apps/agents/event_flow_agent/services/record_source_service.py
#   kmj20260421화 생성

from __future__ import annotations

from apps.agents.event_flow_agent.repositories.sync_record_repository import (
    SyncRecordRepository,
)
from apps.common.configs.database.sync_database.connection import get_sync_session
from apps.common.exceptions.custom import RdbDataFetchError


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
            return repository.fetch_news_records(
                market_category=market_category,
                limit=limit,
                from_first_created=from_first_created,
                to_first_created=to_first_created,
            )
        except Exception as exc:
            raise RdbDataFetchError(detail=str(exc)) from exc
        finally:
            session.close()