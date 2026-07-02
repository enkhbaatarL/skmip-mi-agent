from __future__ import annotations

from typing import Any

from apps.agents.scenario_group_agent.subgraphs.signpost_generation.generation_stages import (
    stage2_observability_filter,
    stage3_assign_axes,
    stage4_assign_direction_strength,
    stage5_mint_keywords,
)
from apps.agents.scenario_group_agent.subgraphs.signpost_generation.schema import GeneratedSignpost
from apps.agents.scenario_group_agent.subgraphs.signpost_generation.state import (
    SignpostGenerationState,
)
from apps.common.logging.logger_config import logger as app_logger
from apps.persistence.enums import DirectionCode, SignpostStrength


def _scenario_pk(scenario: dict[str, Any]) -> int:
    scenario_id = scenario.get("scenario_id", 0)
    if isinstance(scenario_id, (int, str)) and str(scenario_id).isdigit():
        return int(scenario_id)
    return 0


async def observability_filter_node(state: SignpostGenerationState) -> dict[str, Any]:
    if state.skip_generation or state.error:
        return {}
    if state.scenario is None:
        return {"error": "scenario is required"}
    labels = await stage2_observability_filter(state.scenario, state.base_event_summary)
    if not labels:
        app_logger.info("[{}] Stage 2 통과 0건 - signposts 비어있음", _scenario_pk(state.scenario))
    return {"labels": labels}


async def direction_strength_node(state: SignpostGenerationState) -> dict[str, Any]:
    if state.skip_generation or state.error or not state.labels:
        return {}
    if state.scenario is None:
        return {"error": "scenario is required"}
    assignments = await stage4_assign_direction_strength(
        state.scenario,
        state.base_event_summary,
        state.labels,
    )
    strengths = [
        SignpostStrength.from_string_or_default(
            assignment.get("strength"),
            default=SignpostStrength.MEDIUM,
        )
        for assignment in assignments
    ]
    app_logger.info(
        "[{}] Stage 4 vs={} s={} m={} w={} vw={}",
        _scenario_pk(state.scenario),
        sum(1 for strength in strengths if strength == SignpostStrength.VERYSTRONG),
        sum(1 for strength in strengths if strength == SignpostStrength.STRONG),
        sum(1 for strength in strengths if strength == SignpostStrength.MEDIUM),
        sum(1 for strength in strengths if strength == SignpostStrength.WEAK),
        sum(1 for strength in strengths if strength == SignpostStrength.VERYWEAK),
    )
    return {"stage4_assignments": assignments}


async def keyword_hints_node(state: SignpostGenerationState) -> dict[str, Any]:
    if state.skip_generation or state.error or not state.labels:
        return {}
    if state.scenario is None:
        return {"error": "scenario is required"}
    keyword_hints = await stage5_mint_keywords(
        state.scenario,
        state.base_event_summary,
        state.labels,
    )
    return {"stage5_keyword_hints": keyword_hints}


def assemble_signposts_node(state: SignpostGenerationState) -> dict[str, Any]:
    if state.skip_generation or state.error or state.scenario is None:
        return {}
    axes = stage3_assign_axes()
    scenario_pk = _scenario_pk(state.scenario)
    signposts: list[GeneratedSignpost] = []
    for label, assignment, keyword_hints in zip(
        state.labels,
        state.stage4_assignments,
        state.stage5_keyword_hints,
        strict=False,
    ):
        signposts.append(
            GeneratedSignpost(
                scenario_id=scenario_pk,
                signpost_class="observation",
                label=label,
                signpost_source=axes["signpost_source"],
                direction=DirectionCode.SUP,
                strength=SignpostStrength.from_string_or_default(
                    assignment.get("strength"),
                    default=SignpostStrength.MEDIUM,
                ),
                rationale_ko=assignment.get("rationale_ko", ""),
                keyword_hints=keyword_hints,
            ),
        )
    return {"signposts": signposts}
