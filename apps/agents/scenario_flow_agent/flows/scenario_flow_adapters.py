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
- to_output : 내부 상태 → 출력 변환 (Exit Point Adapter)
"""
from __future__ import annotations

from typing import Any
from datetime import datetime

from apps.agents.scenario_flow_agent.schemas.scenario_flow_input import ScenarioFlowInput
from apps.agents.scenario_flow_agent.schemas.scenario_flow_output import ScenarioFlowOutput
from apps.agents.scenario_flow_agent.state.scenario_flow_state import ScenarioFlowState


def to_state(input_data: ScenarioFlowInput | dict[str, Any], **_: object) -> ScenarioFlowState:
    """Convert external input to internal state. This is where mi_event_id is set."""
    parsed = ScenarioFlowInput.model_validate(input_data)

    return ScenarioFlowState(
        mi_event_id=str(parsed.mi_event_id),
    )


def to_output(state: ScenarioFlowState | dict[str, Any]) -> ScenarioFlowOutput:
    """Convert internal state to final output response."""
    if isinstance(state, dict):
        state = ScenarioFlowState.model_validate(state)
    
    # Calculate execution time
    execution_time_ms = 0
    if state.completed_at and state.started_at:
        delta = state.completed_at - state.started_at
        execution_time_ms = int(delta.total_seconds() * 1000)
    
    return ScenarioFlowOutput(
        scenario_group_id=state.scenario_group_id,
        mi_event_id=state.mi_event_id,
        event_type_l1_l2=state.event_type_l1_l2,
        template_id=state.template_id,
        cartesian_total=state.cartesian_total or 0,
        filtered_by_compatibility=state.filtered_by_compatibility or 0,
        scenario_count=state.scenario_count or 0,
        mece_passed=state.mece_passed or False,
        scenarios=state.stage4_scenario_synthesis.get("scenarios", []) if state.stage4_scenario_synthesis else [],
        likelihood_prior=state.stage4_scenario_synthesis.get("likelihood_prior", {}) if state.stage4_scenario_synthesis else {},
        success=state.error is None,
        error=state.error,
        execution_time_ms=execution_time_ms,
        completed_at=state.completed_at or datetime.utcnow(),
        output_file_path=state.output_file_path,
    )