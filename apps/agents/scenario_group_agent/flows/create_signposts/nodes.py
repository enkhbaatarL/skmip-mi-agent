from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import Any

from langgraph.runtime import Runtime

from apps.agents.scenario_group_agent.flows.create_signposts.state import (
    CreateSignpostsState,
    create_signposts_state_update,
)
from apps.agents.scenario_group_agent.persistence.event_service import EventService
from apps.agents.scenario_group_agent.persistence.scenario_group_service import (
    ScenarioGroupService,
)
from apps.agents.scenario_group_agent.persistence.scenario_service import (
    ScenarioService,
)
from apps.agents.scenario_group_agent.persistence.signpost_service import (
    SignpostService,
)
from apps.agents.scenario_group_agent.subgraphs.scenario_generation.nodes import (
    stage1_build_context_pack,
    stage4_synthesize_fixed_scenarios,
    stage6_validate,
)
from apps.agents.scenario_group_agent.subgraphs.signpost_generation.flow import (
    get_signpost_generation_subgraph,
)
from apps.agents.scenario_group_agent.subgraphs.signpost_generation.schema import (
    GeneratedSignpost,
    SignpostGenerationResult,
)
from apps.agents.scenario_group_agent.subgraphs.signpost_generation.state import (
    SignpostGenerationState,
)
from apps.common.exceptions.custom import MIBaseError
from apps.common.tracing.context import TraceContext, build_langgraph_config
from apps.common.values.error_codes import ErrorCode
from apps.persistence.enums import (
    ScenarioGroupStage,
    ScenarioGroupStatus,
    ScenarioStatus,
)
from apps.persistence.event.schema import EventPayload
from apps.persistence.scenario.schema import (
    NewScenarioGeneratedDetails,
)


_LIKELIHOOD_WEIGHTS: dict[str, int] = {
    "very_low": 5,
    "low": 10,
    "medium": 20,
    "high": 35,
    "very_high": 50,
}


def load_scenario_group(state: CreateSignpostsState) -> dict[str, object]:
    if state.scenario_group_id is None:
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="scenario_group_id is required")
    group = ScenarioGroupService().load_by_id(state.scenario_group_id)
    if group is None:
        raise MIBaseError(ErrorCode.ENTITY_NOT_FOUND, detail=f"Scenario group not found: {state.scenario_group_id}")
    request_usr_id = group.request_usr_id
    if request_usr_id is not None and request_usr_id != state.user_id:
        raise MIBaseError(
            ErrorCode.SCENARIO_GROUP_OWNERSHIP_CONFLICT,
            detail=f"이미 사용자 {request_usr_id}가 점유하고 있습니다.",
        )
    return {"scenario_group": group, "mi_event_id": int(group.mi_event_id)}


async def generate_new_scenario_row_details(
    event_data: EventPayload | dict[str, Any],
    dimension_values_list: list[dict[str, Any]],
    trace_context: TraceContext | None = None,
) -> list[NewScenarioGeneratedDetails]:
    if not dimension_values_list:
        return []

    pack = stage1_build_context_pack(event_data)
    stage4 = await stage4_synthesize_fixed_scenarios(
        pack,
        [
            {str(key): str(value) for key, value in dimension_values.items()}
            for dimension_values in dimension_values_list
        ],
        trace_context=trace_context,
    )
    stage6 = await stage6_validate(pack, stage4, trace_context=trace_context)
    likelihoods = [stage6.likelihood_prior.get(scenario.scenario_id, "medium") for scenario in stage4.scenarios]
    details: list[NewScenarioGeneratedDetails] = []
    for scenario, likelihood in zip(stage4.scenarios, likelihoods, strict=False):
        details.append(
            NewScenarioGeneratedDetails(
                narrative=scenario.description,
                probability_weight=Decimal(
                    _LIKELIHOOD_WEIGHTS.get(
                        likelihood,
                        _LIKELIHOOD_WEIGHTS["medium"],
                    ),
                ),
                probability_delta=Decimal("0.0"),
                impact_jkm=scenario.price_direction.jkm,
                impact_ttf=scenario.price_direction.ttf,
                impact_hh=scenario.price_direction.hh,
            ),
        )
    return details


async def generate_new_scenario_row_details_node(
    state: CreateSignpostsState,
    runtime: Runtime[TraceContext] | None = None,
) -> dict[str, object]:
    if state.scenario_group_id is None or state.scenario_group is None:
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="scenario_group_id is required")
    if state.request_table is None:
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="table is required")
    request_table = state.request_table.model_dump(exclude_unset=True)
    new_rows = [row for row in request_table.get("rows", []) or [] if row.get("scenario_id") is None]
    if not new_rows:
        return {}

    event_data = EventService().load_event(int(state.scenario_group.mi_event_id))
    if event_data is None:
        raise MIBaseError(ErrorCode.ENTITY_NOT_FOUND, detail="Event not found")

    scenario_service = ScenarioService()
    dimension_values_list = [
        scenario_service.cells_to_dimension_values(
            int(state.scenario_group.event_type_l2_id),
            row.get("cells") or {},
        )
        for row in new_rows
    ]
    trace_context = runtime.context if runtime is not None else None
    if trace_context is None:
        details = await generate_new_scenario_row_details(event_data, dimension_values_list)
    else:
        details = await generate_new_scenario_row_details(
            event_data,
            dimension_values_list,
            trace_context=trace_context,
        )
    return {"new_scenario_row_details": details}


def sync_scenarios_from_table(state: CreateSignpostsState) -> dict[str, object]:
    if state.scenario_group_id is None or state.scenario_group is None:
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="scenario_group_id is required")
    if state.user_id is None:
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="user_id is required")
    if state.request_table is None:
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="table is required")
    request_table = state.request_table.model_dump(exclude_unset=True)
    try:
        result = ScenarioService().sync_from_table(
            scenario_group_id=state.scenario_group_id,
            event_type_l2_id=int(state.scenario_group.event_type_l2_id),
            table_payload=request_table,
            user_id=state.user_id,
            new_row_details=state.new_scenario_row_details,
        )
    except ValueError as exc:
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail=str(exc)) from exc
    group = ScenarioGroupService().load_by_id(state.scenario_group_id)
    return create_signposts_state_update(
        scenario_group=group,
        signpost_target_scenario_ids=result["regenerate_scenario_ids"],
    )


def load_scenarios(state: CreateSignpostsState) -> dict[str, object]:
    if state.status == "failure" or state.scenario_group_id is None:
        return {}
    scenarios = ScenarioService().load_by_group_id(state.scenario_group_id)
    if not scenarios:
        raise MIBaseError(ErrorCode.ENTITY_NOT_FOUND, detail="No scenarios found")
    return {"scenarios": scenarios}


def check_existing_signposts(state: CreateSignpostsState) -> dict[str, object]:
    if state.status == "failure":
        return {}
    scenario_ids = [int(scenario.scenario_id) for scenario in state.scenarios]
    existing = SignpostService().load_by_scenario_ids(scenario_ids)
    return {"signposts": existing}


async def run_signpost_generation(
    state: CreateSignpostsState,
    runtime: Runtime[TraceContext] | None = None,
) -> dict[str, object]:
    if state.status in {"failure", "already_exist"}:
        return {}
    if state.mi_event_id is None:
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="mi_event_id is required")
    event = EventService().load_event(state.mi_event_id)
    if event is None:
        raise MIBaseError(ErrorCode.ENTITY_NOT_FOUND, detail="Event not found")

    pack = stage1_build_context_pack(event)
    c1 = pack.model_dump().get("C1_base_event", {})
    base_event_summary = {
        "title": c1.get("title", ""),
        "summary": c1.get("summary", ""),
        "driver": c1.get("driver", ""),
    }
    existing_scenario_ids = {int(signpost.scenario_id) for signpost in state.signposts}
    target_ids = {int(scenario_id) for scenario_id in state.signpost_target_scenario_ids}
    scenarios_to_process = [
        scenario.model_dump()
        for scenario in state.scenarios
        if int(scenario.scenario_id) in target_ids or int(scenario.scenario_id) not in existing_scenario_ids
    ]
    if not scenarios_to_process:
        return create_signposts_state_update(
            signpost_result=SignpostGenerationResult(
                scenario_group_id=state.scenario_group_id,
                scenario_results=[],
                signposts=[],
            ),
        )

    from apps.common.configs.config import get_settings

    sem = asyncio.Semaphore(get_settings().create_signposts_max_concurrent_scenarios)
    trace_context = runtime.context if runtime is not None else None

    async def process_one(
        scenario: dict[str, Any],
    ) -> tuple[list[GeneratedSignpost], dict[str, Any]]:
        async with sem:
            result_state = await get_signpost_generation_subgraph().ainvoke(
                SignpostGenerationState(
                    scenario=scenario,
                    base_event_summary=base_event_summary,
                ),
                config=build_langgraph_config(trace_context) if trace_context is not None else None,
                context=trace_context,
            )
            result = (
                result_state
                if isinstance(result_state, SignpostGenerationState)
                else SignpostGenerationState.model_validate(result_state)
            )
            if result.error:
                raise MIBaseError(ErrorCode.UNKNOWN_ERROR, detail=result.error)
            generated_signposts = list(result.signposts or [])
            return generated_signposts, {
                "scenario_id": scenario["scenario_id"],
                "status": "success",
                "signpost_count": len(generated_signposts),
            }

    results = await asyncio.gather(
        *(process_one(scenario) for scenario in scenarios_to_process),
    )
    generated: list[GeneratedSignpost] = []
    scenario_results: list[dict[str, Any]] = []
    for signposts, scenario_result in results:
        generated.extend(signposts)
        scenario_results.append(scenario_result)

    return create_signposts_state_update(
        signpost_result=SignpostGenerationResult(
            scenario_group_id=state.scenario_group_id,
            scenario_results=scenario_results,
            signposts=generated,
        ),
    )


def save_signposts(state: CreateSignpostsState) -> dict[str, object]:
    if state.status in {"failure", "already_exist"}:
        return {}
    if state.scenario_group_id is None:
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="scenario_group_id is required")
    signpost_result = state.signpost_result
    generated = signpost_result.signposts if signpost_result is not None else []
    scenario_group_service = ScenarioGroupService()
    if scenario_group_service.load_by_id(state.scenario_group_id) is None:
        raise MIBaseError(
            ErrorCode.ENTITY_NOT_FOUND,
            detail=f"Fail to save signposts because scenario group is deleted: {state.scenario_group_id}.",
        )

    saved_ids = SignpostService().save_generated_signposts(generated, user_id=state.user_id) if generated else []
    all_signposts = SignpostService().load_by_scenario_ids(
        [int(scenario.scenario_id) for scenario in state.scenarios],
    )
    ScenarioService().update_status(state.scenario_group_id, ScenarioStatus.CREATED.value)
    group = scenario_group_service.update_state(
        state.scenario_group_id,
        status=ScenarioGroupStatus.CREATING,
        stage=ScenarioGroupStage.SIGNPOST_CREATED,
        user_id=state.user_id,
    )
    return create_signposts_state_update(
        saved_signpost_ids=saved_ids,
        signposts=all_signposts,
        scenario_group=group,
        status="success",
        message=f"Created {len(saved_ids)} signposts",
    )
