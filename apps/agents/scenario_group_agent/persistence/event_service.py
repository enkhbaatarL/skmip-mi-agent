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

    def load_events(self, mi_event_ids: list[int]) -> list[EventPayload]:
        events: list[EventPayload] = []
        for mi_event_id in mi_event_ids:
            event = self.load_event(mi_event_id)
            if event is not None:
                events.append(event)
        return events

    def load_event_snapshot(self, mi_event_snapshot_id: int) -> EventPayload | None:
        from apps.common.configs.database.sync_database.connection import get_sync_session

        session = get_sync_session()
        try:
            snapshot = EventRepository(session=session).fetch_snapshot_by_id(mi_event_snapshot_id)
            return EventPayload.model_validate(snapshot) if snapshot is not None else None
        finally:
            session.close()

    def load_events_with_snapshot_fallback(
        self,
        event_refs: list[tuple[int, int | None]],
    ) -> list[EventPayload]:
        """그룹 생성 시점에 고정된 snapshot이 있으면 snapshot을, 없으면 live Event를 사용."""
        events: list[EventPayload] = []
        for mi_event_id, mi_event_snapshot_id in event_refs:
            event = (
                self.load_event_snapshot(mi_event_snapshot_id)
                if mi_event_snapshot_id is not None
                else self.load_event(mi_event_id)
            )
            if event is not None:
                events.append(event)
        return events
