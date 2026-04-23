# apps/agents/event_flow_agent/nodes/extract_events_with_llm.py
#   kmj20260420월
"""
event 추출 노드

역할:
- record별 분석 결과를 바탕으로, 서로 연관된 record들을 통합하여 event 단위 결과를 추출한다.
- N개의 record 분석 결과를 M개의 시장 event로 재구성한다.

입력:
- state.record_analyses

출력:
- state.extracted_events 에 추출된 event 목록 저장

설계 의도:
- record 단위 분석을 실제 저장 가능한 event 단위 데이터로 변환
- 여러 record에 걸친 동일 사건을 하나의 event로 통합하는 단계
"""

from __future__ import annotations

from apps.agents.event_flow_agent.services.event_extraction_service import (
    EventExtractionService,
)
from apps.agents.event_flow_agent.state.event_flow_state import EventFlowState


async def extract_events_with_llm_node(state: EventFlowState) -> EventFlowState:
    state.current_node = "extract_events_with_llm"
    state.executed_nodes.append("extract_events_with_llm")

    try:
        service = EventExtractionService()
        result = await service.extract(state.record_analyses)
        state.extracted_events = [event.model_dump(mode="json") for event in result.events]
        return state

    except Exception as exc:
        state.extracted_events = []
        state.errors.append(f"event 추출 실패: {exc}")
        return state