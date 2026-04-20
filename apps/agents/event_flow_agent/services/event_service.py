#   apps/agents/event_flow_agent/services/event_service.py

from __future__ import annotations

from apps.agents.event_flow_agent.repositories.sync_event_repository import SyncEventRepository


class EventService:
    def __init__(self, repo: SyncEventRepository) -> None:
        self.repo = repo

    def get_events(self, limit: int = 10) -> list[dict]:
        if limit <= 0:
            return []
        if limit > 100:
            limit = 100
        return self.repo.fetch_events(limit=limit)