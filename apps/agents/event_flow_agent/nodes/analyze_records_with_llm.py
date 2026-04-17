#   apps/agents/event_flow_agent/nodes/analyze_records_with_llm.py

from __future__ import annotations

from apps.agents.event_flow_agent.state.event_flow_state import EventFlowState


async def analyze_records_with_llm(
    state: EventFlowState,
    service,
) -> EventFlowState:
    state.current_node = "analyze_records_with_llm"
    state.executed_nodes.append(state.current_node)

    analyzed_records: list[dict] = []

    for idx, record in enumerate(state.source_records, start=1):
        mi_record_id = record.get("mi_record_id")
        print(f"[analyze_records_with_llm] start idx={idx}, mi_record_id={mi_record_id}")
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
            print(f"[analyze_records_with_llm] success idx={idx}, mi_record_id={mi_record_id}")
        except Exception as exc:
            msg = f"mi_record_id={mi_record_id} record 분석 실패: {exc}"
            state.errors.append(msg)
            print(f"[analyze_records_with_llm] fail idx={idx}, mi_record_id={mi_record_id}, error={exc}")

    state.record_analyses = analyzed_records
    return state