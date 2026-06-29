from __future__ import annotations

from typing import Any
import uuid

from apps.agents.scenario_group_agent.schemas.graph.generation import (
    ScenarioGenerationResult,
)
from apps.agents.scenario_group_agent.subgraphs.scenario_generation.generation_stages import (
    stage1_build_context_pack,
    stage2_select_dimensions,
    stage3_reduce_values,
    stage4_synthesize_scenarios,
    stage5_validate,
    stage6_quick_validate,
    stage_generate_scenario_group_metadata,
)
from apps.agents.scenario_group_agent.subgraphs.scenario_generation.state import (
    ScenarioGenerationState,
)
from apps.common.logging.logger_config import logger


def _shorten_feedback(feedback: str | None, max_len: int = 600) -> str:
    if not feedback:
        return ""
    if len(feedback) <= max_len:
        return feedback
    return feedback[:max_len] + "..."


def build_context_node(state: ScenarioGenerationState) -> dict[str, Any]:
    if state.skip_generation:
        return {}
    if state.event_data is None:
        return {"error": "event_data is required"}
    return {"stage1_context_pack": stage1_build_context_pack(state.event_data)}


def select_dimensions_node(state: ScenarioGenerationState) -> dict[str, Any]:
    if state.skip_generation or state.error:
        return {}
    if (
        state.event_data is None
        or state.template is None
        or state.stage1_context_pack is None
    ):
        return {"error": "scenario generation input is incomplete"}
    return {
        "stage2_dimension_selection": stage2_select_dimensions(
            state.stage1_context_pack,
            state.event_data,
            state.template,
        ),
    }


def reduce_values_node(state: ScenarioGenerationState) -> dict[str, Any]:
    if state.skip_generation or state.error:
        return {}
    if (
        state.template is None
        or state.stage1_context_pack is None
        or state.stage2_dimension_selection is None
    ):
        return {"error": "scenario generation stage 2 output is missing"}
    return {
        "stage3_value_selection": stage3_reduce_values(
            state.stage1_context_pack,
            state.stage2_dimension_selection,
            state.template,
        ),
    }


def synthesize_scenarios_node(state: ScenarioGenerationState) -> dict[str, Any]:
    if state.skip_generation or state.error:
        return {}
    if (
        state.template is None
        or state.stage1_context_pack is None
        or state.stage3_value_selection is None
    ):
        return {"error": "scenario generation stage 3 output is missing"}
    return {
        "stage4_scenario_synthesis": stage4_synthesize_scenarios(
            state.stage1_context_pack,
            state.stage3_value_selection,
            state.template,
            validation_feedback=state.validation_feedback,
        ),
    }


def quick_validate_node(state: ScenarioGenerationState) -> dict[str, Any]:
    if state.skip_generation or state.error:
        return {}
    if (
        state.stage1_context_pack is None
        or state.stage3_value_selection is None
        or state.stage4_scenario_synthesis is None
        or state.template is None
    ):
        return {"error": "quick_validate 입력 누락"}

    passed, feedback = stage6_quick_validate(
        state.stage1_context_pack,
        state.stage3_value_selection,
        state.stage4_scenario_synthesis,
        state.template,
    )
    if passed:
        if state.quick_validate_retry_count > 0:
            logger.info(
                "[SCENARIO_GENERATION][stage6] quick validate passed after retry "
                f"| retry_count={state.quick_validate_retry_count}",
            )
        return {"validation_feedback": None}
    next_retry_count = state.quick_validate_retry_count + 1
    logger.info(
        "[SCENARIO_GENERATION][stage6] quick validate failed "
        f"| retry_count={next_retry_count} | feedback={_shorten_feedback(feedback)}",
    )
    return {
        "validation_feedback": feedback,
        "quick_validate_retry_count": next_retry_count,
    }


def validate_scenarios_node(state: ScenarioGenerationState) -> dict[str, Any]:
    if state.skip_generation or state.error:
        return {}
    if (
        state.event_data is None
        or state.stage1_context_pack is None
        or state.stage2_dimension_selection is None
        or state.stage3_value_selection is None
        or state.stage4_scenario_synthesis is None
    ):
        return {"error": "scenario generation stage output is incomplete"}

    stage5 = stage5_validate(
        state.stage1_context_pack,
        state.stage4_scenario_synthesis,
    )
    scenario_group_metadata = stage_generate_scenario_group_metadata(
        state.stage1_context_pack,
        state.event_data,
        state.stage4_scenario_synthesis,
    )
    event_type_l2_id = int(state.event_data.get("event_type_l2_id") or 0)
    stage4 = state.stage4_scenario_synthesis
    return ScenarioGenerationState(
        scenario_result=ScenarioGenerationResult(
            scenario_group_id=f"scg_{uuid.uuid4().hex[:10]}",
            stage1_context_pack=state.stage1_context_pack,
            stage2_dimension_selection=state.stage2_dimension_selection,
            stage3_value_selection=state.stage3_value_selection,
            stage4_scenario_synthesis=stage4,
            stage5_validation=stage5,
            scenario_group_metadata=scenario_group_metadata,
            cartesian_total=stage4.cartesian_total,
            filtered_by_compatibility=stage4.filtered_by_compatibility,
            scenario_count=len(stage4.scenarios),
            mece_passed=stage5.mece_check.mutually_exclusive,
            mi_event_id=state.event_data.get("mi_event_id"),
            event_type_l1_l2=state.stage1_context_pack.C1_base_event.event_type_l1_l2,
            template_id=str(event_type_l2_id),
        ),
    ).model_dump(
        include={"scenario_result"},
        exclude_none=True,
        exclude_unset=True,
    )
