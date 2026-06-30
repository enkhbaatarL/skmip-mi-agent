from __future__ import annotations

import asyncio
from typing import Any

from apps.agents.scenario_group_agent.persistence.event.service import EventService
from apps.agents.scenario_group_agent.persistence.scenario.service import (
    ScenarioService,
)
from apps.agents.scenario_group_agent.persistence.scenario_group.service import (
    ScenarioGroupService,
)
from apps.agents.scenario_group_agent.persistence.signpost.service import (
    SignpostService,
)
from apps.agents.scenario_group_agent.schemas.enums import (
    ScenarioGroupStage,
    ScenarioGroupStatus,
    ScenarioStatus,
)
from apps.agents.scenario_group_agent.schemas.graph.generation import (
    GeneratedSignpost,
    SignpostGenerationResult,
)
from apps.agents.scenario_group_agent.state import ScenarioDesignState, state_update
from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode


_MAX_CONCURRENT_SCENARIOS = 7


def load_scenario_group(state: ScenarioDesignState) -> dict[str, object]:
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


def sync_scenarios_from_table(state: ScenarioDesignState) -> dict[str, object]:
    if state.scenario_group_id is None or state.scenario_group is None:
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="scenario_group_id is required")
    if state.user_id is None:
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="user_id is required")
    if state.request_table is None:
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="table is required")
    event_data = None
    request_table = state.request_table.model_dump(exclude_unset=True)
    has_new_rows = any(
        row.get("scenario_id") is None
        for row in request_table.get("rows", []) or []
    )
    if has_new_rows:
        event_data = EventService().load_event(int(state.scenario_group.mi_event_id))
        if event_data is None:
            raise MIBaseError(ErrorCode.ENTITY_NOT_FOUND, detail="Event not found")
    try:
        result = ScenarioService().sync_from_table(
            scenario_group_id=state.scenario_group_id,
            event_type_l2_id=int(state.scenario_group.event_type_l2_id),
            table_payload=request_table,
            user_id=state.user_id,
            event_data=event_data,
        )
    except ValueError as exc:
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail=str(exc)) from exc
    group = ScenarioGroupService().load_by_id(state.scenario_group_id)
    return state_update(
        scenario_group=group,
        signpost_target_scenario_ids=result["regenerate_scenario_ids"],
    )


def load_scenarios(state: ScenarioDesignState) -> dict[str, object]:
    if state.status == "failure" or state.scenario_group_id is None:
        return {}
    scenarios = ScenarioService().load_by_group_id(state.scenario_group_id)
    if not scenarios:
        raise MIBaseError(ErrorCode.ENTITY_NOT_FOUND, detail="No scenarios found")
    return {"scenarios": scenarios}


def check_existing_signposts(state: ScenarioDesignState) -> dict[str, object]:
    if state.status == "failure":
        return {}
    scenario_ids = [int(scenario.scenario_id) for scenario in state.scenarios]
    existing = SignpostService().load_by_scenario_ids(scenario_ids)
    return {"signposts": existing}


async def run_signpost_generation(state: ScenarioDesignState) -> dict[str, object]:
    if state.status in {"failure", "already_exist"}:
        return {}
    if state.mi_event_id is None:
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="mi_event_id is required")
    event = EventService().load_event(state.mi_event_id)
    if event is None:
        raise MIBaseError(ErrorCode.ENTITY_NOT_FOUND, detail="Event not found")

    from apps.agents.scenario_group_agent.subgraphs.scenario_generation.generation_stages import (
        stage1_build_context_pack,
    )
    from apps.agents.scenario_group_agent.subgraphs.signpost_generation.flow import (
        signpost_generation_runnable,
    )

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
        if int(scenario.scenario_id) in target_ids
        or int(scenario.scenario_id) not in existing_scenario_ids
    ]
    if not scenarios_to_process:
        return state_update(
            signpost_result=SignpostGenerationResult(
                scenario_group_id=state.scenario_group_id,
                scenario_results=[],
                signposts=[],
            ),
        )

    sem = asyncio.Semaphore(_MAX_CONCURRENT_SCENARIOS)

    async def process_one(
        scenario: dict[str, Any],
    ) -> tuple[list[GeneratedSignpost], dict[str, Any]]:
        async with sem:
            output = await signpost_generation_runnable.ainvoke(
                {
                    "scenario": scenario,
                    "base_event_summary": base_event_summary,
                },
            )
            generated_signposts = list(output.get("signposts") or [])
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

    return state_update(
        signpost_result=SignpostGenerationResult(
            scenario_group_id=state.scenario_group_id,
            scenario_results=scenario_results,
            signposts=generated,
        ),
    )


def save_signposts(state: ScenarioDesignState) -> dict[str, object]:
    if state.status in {"failure", "already_exist"}:
        return {}
    signpost_result = state.signpost_result
    generated = signpost_result.signposts if signpost_result is not None else []
    group = ScenarioGroupService().update_state(
        state.scenario_group_id,
        status=ScenarioGroupStatus.CREATING,
        stage=ScenarioGroupStage.SIGNPOST_CREATED,
        user_id=state.user_id,
    )
    if group is None:
        raise MIBaseError(
            ErrorCode.ENTITY_NOT_FOUND,
            detail=f"Fail to save signposts because scenario group is deleted: {state.scenario_group_id}.",
        )

    saved_ids = (
        SignpostService().save_generated_signposts(generated, user_id=state.user_id)
        if generated
        else []
    )
    all_signposts = SignpostService().load_by_scenario_ids(
        [int(scenario.scenario_id) for scenario in state.scenarios],
    )
    ScenarioService().update_status(state.scenario_group_id, ScenarioStatus.CREATED.value)
    return state_update(
        saved_signpost_ids=saved_ids,
        signposts=all_signposts,
        scenario_group=group,
        status="success",
        message=f"Created {len(saved_ids)} signposts",
    )
