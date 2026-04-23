#   apps/agents/event_flow_agent/nodes/analyze_records_with_llm.py
#   kmj20260420월
"""
원천 record별 LLM 분석 노드

역할:
- 조회된 각 source record를 개별적으로 LLM에 전달하여 구조화된 분석 결과를 생성한다.
- record별 category, entity, timing 등의 분석 정보를 state에 누적한다.

입력:
- state.source_records

출력:
- state.record_analyses 에 record별 분석 결과 저장

설계 의도:
- record 단위의 비정형 텍스트를 event 추출에 적합한 구조화 정보로 변환
- 이후 event 추출 단계에서 여러 record를 통합 판단할 수 있도록 중간 분석 결과 생성
"""

from __future__ import annotations

from apps.agents.event_flow_agent.services.record_analysis_service import (
    RecordAnalysisService,
)
from apps.agents.event_flow_agent.state.event_flow_state import EventFlowState


async def analyze_records_with_llm_node(state: EventFlowState) -> EventFlowState:
    state.current_node = "analyze_records_with_llm"
    state.executed_nodes.append("analyze_records_with_llm")

    service = RecordAnalysisService()
    analyzed_records: list[dict] = []

    for idx, record in enumerate(state.source_records, start=1):
        mi_record_id = record.get("mi_record_id")

        try:
            title = record.get("title", "") or ""
            body = record.get("smry", "") or ""

            analysis = await service.analyze(
                title=title,
                body=body,
            )

            analyzed_records.append(
                {
                    **record,
                    "record_analysis": analysis.model_dump(mode="json"),
                }
            )

        except Exception as exc:
            msg = f"mi_record_id={mi_record_id} record 분석 실패: {exc}"
            state.errors.append(msg)

    state.record_analyses = analyzed_records
    return state