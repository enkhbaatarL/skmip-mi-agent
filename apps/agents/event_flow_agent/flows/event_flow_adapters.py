#   agents/event_flow_agent/flows/event_flow_adapters.py
#   kmj20260423목
"""
Event Flow Adapter 모듈

역할:
- 외부 입력(EventFlowInput 또는 dict)을 내부 실행 상태(EventFlowState)로 변환
- 내부 실행 결과(EventFlowState)를 최종 응답(EventFlowOutput)으로 변환

설계 의도:
- Flow(Graph)는 항상 State 기반으로 동작하도록 강제
- 외부 인터페이스(Input/Output)와 내부 상태(State)를 명확히 분리
- LangGraph / Runnable 구조에서 입출력 포맷을 표준화

구성:
- to_state  : 입력 → 내부 상태 변환 (Entry Point Adapter)
- to_output : 내부 상태 → 출력 변환 (Exit Point Adapter)
"""

from __future__ import annotations

from typing import Any

from apps.agents.event_flow_agent.schemas.event_flow_input import EventFlowInput
from apps.agents.event_flow_agent.schemas.event_flow_output import EventFlowOutput
from apps.agents.event_flow_agent.state.event_flow_state import EventFlowState


def to_state(input_data: EventFlowInput | dict[str, Any], **_: object) -> EventFlowState:
    parsed = EventFlowInput.model_validate(input_data)

    return EventFlowState(
        limit=parsed.limit,
    )

#   kmj20260421화 수정 (임시)
def to_output(state: EventFlowState | dict[str, Any]) -> EventFlowOutput:
    if isinstance(state, dict):
        state = EventFlowState.model_validate(state)

    return EventFlowOutput(
        summary=state.summary or "",
        llm_result=state.llm_result or "",
        rdb_result=state.rdb_result,
        errors=state.errors,
        executed_nodes=state.executed_nodes,
        saved_event_ids=state.saved_event_ids,
        source_records_count=len(state.source_records),
        record_analyses_count=len(state.record_analyses),
        extracted_events_count=len(state.extracted_events),
    )