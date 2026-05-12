"""
Scenario Flow Adapter 모듈

역할:
- 외부 입력(ScenarioFlowInput 또는 dict)을 내부 실행 상태(ScenarioFlowState)로 변환
- 내부 실행 결과(ScenarioFlowState)를 최종 응답(ScenarioFlowOutput)으로 변환

설계 의도:
- Flow(Graph)는 항상 State 기반으로 동작하도록 강제
- 외부 인터페이스(Input/Output)와 내부 상태(State)를 명확히 분리
- LangGraph / Runnable 구조에서 입출력 포맷을 표준화

구성:
- to_state  : 입력 → 내부 상태 변환 (Entry Point Adapter)
- to_output : 내부 상태 → 최종 출력 변환 (Exit Point Adapter)
"""
from __future__ import annotations

from typing import Any

from apps.agents.scenario_flow_agent.schemas.scenario_flow_output import (
    EventResult,
    ScenarioFlowOutput,
)
from apps.agents.scenario_flow_agent.state.scenario_flow_state import ScenarioFlowState


def to_state(mi_event_id: int, **_: object) -> ScenarioFlowState:
    """Convert a single mi_event_id to internal state for one event."""
    return ScenarioFlowState(
        mi_event_id=str(mi_event_id),
    )


def to_output(state: ScenarioFlowState | dict[str, Any]) -> dict[str, Any]:
    """Convert internal state to a per-event result dict for aggregation."""
    if isinstance(state, dict):
        state = ScenarioFlowState.model_validate(state)

    if state.error:
        return {
            "mi_event_id": int(state.mi_event_id),
            "status": "failure",
            "message": state.error,
        }

    return {
        "mi_event_id": int(state.mi_event_id),
        "status": "success",
        "message": f"Generated {state.scenario_count or 0} scenarios",
    }


def build_batch_output(results: list[dict[str, Any]]) -> ScenarioFlowOutput:
    """Aggregate per-event results into a single batch output with summary."""
    total = len(results)
    success = sum(1 for r in results if r["status"] == "success")
    already_exist = sum(1 for r in results if r["status"] == "already_exist")
    failure = sum(1 for r in results if r["status"] == "failure")

    return ScenarioFlowOutput(
        results=[EventResult(**r) for r in results],
        summary={
            "total": total,
            "success": success,
            "already_exist": already_exist,
            "failure": failure,
        },
    )
