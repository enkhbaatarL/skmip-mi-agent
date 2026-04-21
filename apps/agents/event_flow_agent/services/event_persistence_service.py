#   apps/agents/event_flow_agent/services/event_persistence_service.py
#   kmj20260421화 생성

from __future__ import annotations

import re
import uuid
from datetime import datetime

from apps.agents.event_flow_agent.repositories.sync_event_repository import (
    SyncEventRepository,
)
from apps.common.configs.database.sync_database.connection import get_sync_session
from apps.common.exceptions.custom import RdbDataFetchError


def _new_event_id() -> str:
    return f"ev_{uuid.uuid4().hex[:12]}"


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
    def save_events(self, events: list[dict]) -> list[str]:
        session = get_sync_session()

        try:
            repository = SyncEventRepository(session=session)
            saved_ids: list[str] = []

            for event in events:
                payload = {
                    "mi_event_id": _new_event_id(),
                    "crt_user_id": "SYSTEM",
                    "mod_user_id": "SYSTEM",
                    "del_yn": "N",
                    "mi_event_title_ko": event["event_title_ko"],
                    "mi_event_summary_ko": event["detail_analysis"],
                    "estimated_impact_id": None,
                    "occurred_at": _normalize_occurred_at(event.get("occurred_at")),
                    "updated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                    "probability": None,
                    "language": "ko",
                    "dedup_state": "raw",
                    "merged_into_mi_event_id": None,
                    "mi_event_type_l1_code": event["event_type"]["level_1"],
                    "mi_event_type_l2_code": event["event_type"]["level_2"],
                    "mi_event_status_code": None,
                    "signal_noise_label": None,
                    "signal_noise_confidence": None,
                }

                repository.insert_event(payload)
                saved_ids.append(payload["mi_event_id"])
            session.commit()
            return saved_ids

        except Exception as exc:
            session.rollback()
            raise RdbDataFetchError(detail=str(exc)) from exc

        finally:
            session.close()