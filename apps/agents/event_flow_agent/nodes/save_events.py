# apps/agents/event_flow_agent/nodes/save_events.py
#   kmj20260423목 수정
"""
추출 event 저장 노드

역할:
- LLM으로 추출된 event 목록을 DB에 저장한다.
- 저장 성공한 event의 ID를 state에 기록하고, 실패한 건은 오류로 누적한다.

입력:
- state.extracted_events

출력:
- state.saved_event_ids 에 저장 성공한 event ID 목록 저장
- state.errors 에 저장 실패 정보 누적 가능

설계 의도:
- event 추출 결과를 영속화하는 단계
- 현재는 건별 commit 방식으로 동작하여, 일부 실패가 발생해도 나머지 성공 건은 유지
"""

from __future__ import annotations

from apps.agents.event_flow_agent.services.event_persistence_service import (
    EventPersistenceService,
)
from apps.agents.event_flow_agent.state.event_flow_state import EventFlowState


def save_events_node(state: EventFlowState) -> EventFlowState:
    state.current_node = "save_events"
    state.executed_nodes.append("save_events")

    try:
        saved_ids, save_errors = EventPersistenceService().save_events(
            state.extracted_events
        )
        state.saved_event_ids = saved_ids
        state.errors.extend(save_errors)
        return state

    except Exception as exc:
        state.saved_event_ids = []
        state.errors.append(f"event 저장 실패: {exc}")
        return state