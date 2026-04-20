# apps/agents/event_flow_agent/nodes/save_events.py

from __future__ import annotations

import re
import uuid
from datetime import datetime

from apps.agents.event_flow_agent.repositories.sync_event_repository import (
    SyncEventRepository,
)
from apps.agents.event_flow_agent.state.event_flow_state import EventFlowState
from apps.common.configs.database.sync_database.connection import get_sync_session


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


def save_events_node(state: EventFlowState) -> EventFlowState:
    state.current_node = "save_events"
    state.executed_nodes.append("save_events")

    session = get_sync_session()

    try:
        repository = SyncEventRepository(session=session)
        saved_ids: list[str] = []

        for event in state.extracted_events:
            payload = {
                "mi_event_id": _new_event_id(),
                "crt_user_id": "SYSTEM",
                "mod_user_id": "SYSTEM",
                "del_yn": "N",
                "mi_event_title_ko": event["event_title_ko"],
                "mi_event_summary_ko": event["detail_analysis"],
                "estimated_impact_id": None,  # kmj20260417,  아직 상태를 모르므로 일단 null로 저장, 추후 상태 결정 로직이 생기면 업데이트 예정
                "occurred_at": _normalize_occurred_at(event.get("occurred_at")),
                "updated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                "probability": None,  # kmj20260417,  아직 상태를 모르므로 일단 null로 저장, 추후 상태 결정 로직이 생기면 업데이트 예정
                "language": "ko",
                "dedup_state": "raw",
                "merged_into_mi_event_id": None,  # kmj20260417,  아직 상태를 모르므로 일단 null로 저장, 추후 상태 결정 로직이 생기면 업데이트 예정
                "mi_event_type_l1_code": event["event_type"]["level_1"],
                "mi_event_type_l2_code": event["event_type"]["level_2"],
                "mi_event_status_code": None,  # kmj20260417,  아직 상태를 모르므로 일단 null로 저장, 추후 상태 결정 로직이 생기면 업데이트 예정
                "signal_noise_label": None,  # kmj20260417,  아직 상태를 모르므로 일단 null로 저장, 추후 상태 결정 로직이 생기면 업데이트 예정
                "signal_noise_confidence": None,  # kmj20260417,  아직 상태를 모르므로 일단 null로 저장, 추후 상태 결정 로직이 생기면 업데이트 예정
            }

            repository.insert_event(payload)
            saved_ids.append(payload["mi_event_id"])

        session.commit()
        state.saved_event_ids = saved_ids
        return state

    except Exception as exc:
        session.rollback()
        state.saved_event_ids = []
        state.errors.append(f"event 저장 실패: {exc}")
        return state

    finally:
        session.close()