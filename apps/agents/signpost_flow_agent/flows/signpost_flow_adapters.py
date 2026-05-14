"""
Signpost Flow Adapter 모듈

역할:
- 외부 입력(SignpostFlowInput 또는 dict)을 내부 실행 상태(SignpostFlowState)로 변환
- 내부 실행 결과(SignpostFlowState)를 최종 응답(SignpostFlowOutput)으로 변환

설계 의도:
- Flow(Graph)는 항상 State 기반으로 동작하도록 강제
- 외부 인터페이스(Input/Output)와 내부 상태(State)를 명확히 분리
"""
from __future__ import annotations

from typing import Any

from apps.agents.signpost_flow_agent.schemas.signpost_flow_output import (
    EventResult,
    SignpostFlowOutput,
)
from apps.agents.signpost_flow_agent.state.signpost_flow_state import SignpostFlowState


def to_state(mi_event_id: int, **_: object) -> SignpostFlowState:
    """Convert a single mi_event_id to internal state for one event."""
    return SignpostFlowState(
        mi_event_id=str(mi_event_id),
    )


def to_output(state: SignpostFlowState | dict[str, Any]) -> dict[str, Any]:
    """Convert internal state to a per-event result dict for aggregation."""
    if isinstance(state, dict):
        state = SignpostFlowState.model_validate(state)

    if state.error:
        return {
            "mi_event_id": int(state.mi_event_id),
            "status": "failure",
            "message": state.error,
        }

    # Count results
    scenario_results = state.scenario_results or []
    success_count = sum(1 for r in scenario_results if r["status"] == "success")
    already_exist_count = sum(1 for r in scenario_results if r["status"] == "already_exist")
    failure_count = sum(1 for r in scenario_results if r["status"] == "failure")
    total_signposts = len(state.signposts_generated or [])

    return {
        "mi_event_id": int(state.mi_event_id),
        "status": "success" if success_count > 0 else ("already_exist" if already_exist_count > 0 and failure_count == 0 else "failure"),
        "message": (
            f"Processed {len(scenario_results)} scenarios: "
            f"{success_count} generated ({total_signposts} signposts), "
            f"{already_exist_count} skipped (already exist), "
            f"{failure_count} failed"
        ),
    }


def build_batch_output(results: list[dict[str, Any]]) -> SignpostFlowOutput:
    """Aggregate per-event results into a single batch output with summary."""
    total = len(results)
    success = sum(1 for r in results if r["status"] == "success")
    already_exist = sum(1 for r in results if r["status"] == "already_exist")
    failure = sum(1 for r in results if r["status"] == "failure")

    return SignpostFlowOutput(
        results=[EventResult(**r) for r in results],
        summary={
            "total": total,
            "success": success,
            "already_exist": already_exist,
            "failure": failure,
        },
    )