from __future__ import annotations

from typing import Any

from apps.agents.scenario_design_agent.persistence.event.repository import EventRepository


class EventService:
    def load_event(self, mi_event_id: int) -> dict[str, Any] | None:
        from apps.common.configs.database.sync_database.connection import get_sync_session

        session = get_sync_session()
        try:
            return EventRepository(session=session).fetch_event_by_id(mi_event_id)
        finally:
            session.close()
