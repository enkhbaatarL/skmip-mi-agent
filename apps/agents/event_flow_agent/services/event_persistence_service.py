#   apps/agents/event_flow_agent/services/event_persistence_service.py
#   kmj20260423목 수정
"""
event 저장 서비스 모듈

역할:
- 추출된 event 목록을 DB 스키마에 맞는 payload로 변환하여 저장한다.
- 저장 성공한 event의 ID 목록과 실패 정보를 반환한다.
- LLM 출력의 level_1/level_2 코드를 새 정규화된 event_type_l2_id FK로 변환한다.

입력:
- 추출된 event 목록

출력:
- 저장 성공한 event ID 목록
- 저장 실패 메시지 목록

설계 의도:
- node에서 직접 DB 저장/트랜잭션을 처리하지 않도록 분리
- 추출 결과를 실제 DB 테이블 구조에 맞게 매핑하는 책임 담당
- 현재는 건별 commit 방식으로 동작하여,
  일부 event 저장 실패 시에도 나머지 성공 건은 유지
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from apps.agents.event_flow_agent.repositories.sync_event_repository import (
    SyncEventRepository,
)
from apps.common.configs.database.sync_database.connection import get_sync_session


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
    def save_events(self, events: list[dict[str, Any]]) -> tuple[list[int], list[str]]:
        session = get_sync_session()

        try:
            repository = SyncEventRepository(session=session)
            saved_ids: list[int] = []
            errors: list[str] = []

            for idx, event in enumerate(events, start=1):
                try:
                    level_1 = event["event_type"]["level_1"]
                    level_2 = event["event_type"]["level_2"]

                    # Resolve event_type_l2_id from level_1/level_2 codes
                    event_type_l2_id = repository.resolve_event_type_l2_id(level_1, level_2)
                    if event_type_l2_id is None:
                        errors.append(
                            f"[{idx}] event_type 코드 미등록"
                            f" | level_1={level_1}"
                            f" | level_2={level_2}"
                        )
                        continue

                    key_bullets = event.get("key_bullets") or []
                    tags = event.get("tags") or []

                    payload = {
                        "crt_usr_logn_id": "SYSTEM",
                        "mod_usr_logn_id": "SYSTEM",
                        "del_yn": "N",
                        "event_title": event["event_title_ko"],
                        "one_line_summary": event.get("one_line_summary", "")[:300],
                        "event_summary": event.get("detail_analysis"),
                        "market_and_institution_view": event.get("market_and_institution_view"),
                        "occurred_at": _normalize_occurred_at(event.get("occurred_at")),
                        "probability": 1.0,
                        "dedup_state": "raw",
                        "mi_event_status_code": None,
                        "key_bullets_json": key_bullets if key_bullets else None,
                        "tags_json": tags if tags else None,
                        "event_type_l2_id": event_type_l2_id,
                        "signal_yn": "Y",
                        "signal_confidence": 0,
                        "signal_reason": None,
                    }

                    saved_id = repository.insert_event(payload)
                    session.commit()
                    saved_ids.append(saved_id)

                except Exception as exc:
                    session.rollback()
                    event_title = event.get("event_title_ko", "")
                    errors.append(
                        f"[{idx}] event 저장 실패"
                        f" | title={event_title}"
                        f" | level_1={event.get('event_type', {}).get('level_1')}"
                        f" | level_2={event.get('event_type', {}).get('level_2')}"
                        f" | error={exc}"
                    )
                    continue

            return saved_ids, errors

        finally:
            session.close()