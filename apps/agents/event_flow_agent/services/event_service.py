#   apps/agents/event_flow_agent/services/event_service.py
#   kmj20260421화 수정
from __future__ import annotations

from apps.agents.event_flow_agent.repositories.sync_event_repository import SyncEventRepository
from apps.common.configs.database.sync_database.connection import get_sync_session
from apps.common.exceptions.custom import RdbDataFetchError


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
            raise RdbDataFetchError(detail=str(exc)) from exc
        finally:
            session.close()