from __future__ import annotations

from apps.persistence.event.repository import EventRepository
from apps.persistence.event.schema import EventPayload


class EventService:
    def load_event(self, mi_event_id: int) -> EventPayload | None:
        from apps.common.configs.database.sync_database.connection import get_sync_session

        session = get_sync_session()
        try:
            event = EventRepository(session=session).fetch_event_by_id(mi_event_id)
            return EventPayload.model_validate(event) if event is not None else None
        finally:
            session.close()
