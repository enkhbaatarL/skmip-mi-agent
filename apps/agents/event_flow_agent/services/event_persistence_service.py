#   apps/agents/event_flow_agent/services/event_persistence_service.py
#   kmj20260422수 수정

from __future__ import annotations

import re
from datetime import datetime

from apps.agents.event_flow_agent.repositories.sync_event_repository import (
    SyncEventRepository,
)
from apps.common.configs.database.sync_database.connection import get_sync_session
from apps.common.exceptions.custom import RdbDataFetchError


def _normalize_occurred_at(value: str | None) -> str | None:
    if not value:
        return None

    raw = value.strip()
    if not raw:
        return None

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        return f"{raw} 00:00:00"

    if re.fullmatch(r"\d{4}-\d{2}", raw):
        return f"{raw}-01 00:00:00"

    if re.fullmatch(r"\d{4}", raw):
        return f"{raw}-01-01 00:00:00"

    if raw.endswith("Z"):
        raw = raw[:-1]

    try:
        dt = datetime.fromisoformat(raw)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


class EventPersistenceService:
    def save_events(self, events: list[dict]) -> list[int]:
        session = get_sync_session()

        try:
            repository = SyncEventRepository(session=session)
            saved_ids: list[int] = []

            for event in events:
                level_1 = event["event_type"]["level_1"]
                level_2 = event["event_type"]["level_2"]

                payload = {
                    "first_created": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                    "crt_usr_logn_id": "SYSTEM",
                    "mod_usr_logn_id": "SYSTEM",
                    "del_yn": "N",
                    "event_title_ko": event["event_title_ko"],
                    "one_line_summary": event.get("one_line_summary", "")[:200],
                    "detail_analysis": event.get("detail_analysis"),
                    "market_and_institution_view": event.get("market_and_institution_view"),
                    "language": "ko",
                    "occurred_at": _normalize_occurred_at(event.get("occurred_at")),
                    "probability": None,
                    "dedup_state": "raw",
                    "level_1_code": level_1,
                    "level_2_code": level_2,
                    "taxonomy_version": "0.1.0",
                    "status_code": None,
                    "status_label_ko": None,
                    "status_taxonomy_version": None,
                }

                saved_id = repository.insert_event(payload)
                saved_ids.append(saved_id)

            session.commit()
            return saved_ids

        except Exception as exc:
            session.rollback()
            raise RdbDataFetchError(detail=str(exc)) from exc

        finally:
            session.close()