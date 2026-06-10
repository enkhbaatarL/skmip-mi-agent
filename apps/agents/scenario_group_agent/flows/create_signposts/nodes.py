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
from apps.agents.scenario_group_agent.state import ScenarioDesignState

_MAX_CONCURRENT_SCENARIOS = 7


def load_scenario_group(state: ScenarioDesignState) -> dict[str, Any]:
    if state.scenario_group_id is None:
        return {
            "status": "failure",
            "error": "scenario_group_id is required",
            "message": "scenario_group_id is required",
        }
    group = ScenarioGroupService().load_by_id(state.scenario_group_id)
    if group is None:
        return {
            "status": "failure",
            "error": f"Scenario group not found: {state.scenario_group_id}",
            "message": f"Scenario group not found: {state.scenario_group_id}",
        }
    return {"scenario_group": group, "mi_event_id": group["mi_event_id"]}


def load_scenarios(state: ScenarioDesignState) -> dict[str, Any]:
    if state.status == "failure" or state.scenario_group_id is None:
        return {}
    scenarios = ScenarioService().load_by_group_id(state.scenario_group_id)
    if not scenarios:
        return {
            "status": "failure",
            "error": "No scenarios found",
            "message": "No scenarios found",
        }
    return {"scenarios": scenarios}


def check_existing_signposts(state: ScenarioDesignState) -> dict[str, Any]:
    if state.status == "failure":
        return {}
    scenario_ids = [int(s["scenario_id"]) for s in state.scenarios]
    existing = SignpostService().load_by_scenario_ids(scenario_ids)
    if len(existing) == 0:
        return {}
    if len({sp["scenario_id"] for sp in existing}) == len(scenario_ids):
        group = ScenarioGroupService().update_state(
            state.scenario_group_id,
            stage="signpost_created",
            user_id=state.user_id,
        )
        return {
            "signposts": existing,
            "scenario_group": group,
            "status": "already_exist",
            "message": "Signposts already exist for all scenarios",
        }
    return {"signposts": existing}


async def run_signpost_generation(state: ScenarioDesignState) -> dict[str, Any]:
    if state.status in {"failure", "already_exist"}:
        return {}
    if state.mi_event_id is None:
        return {
            "status": "failure",
            "error": "mi_event_id is required",
            "message": "mi_event_id is required",
        }
    event = EventService().load_event(state.mi_event_id)
    if event is None:
        return {
            "status": "failure",
            "error": "Event not found",
            "message": "Event not found",
        }

    from apps.agents.scenario_agent.services.scenario_pipeline import (
        stage1_build_context_pack,
    )
    from apps.agents.signpost_flow_agent.services.signpost_pipeline import (
        build_signposts_for_scenario,
    )

    pack = stage1_build_context_pack(event)
    c1 = pack.model_dump().get("C1_base_event", {})
    base_event_summary = {
        "title": c1.get("title", ""),
        "summary": c1.get("summary", ""),
        "driver": c1.get("driver", ""),
    }
    existing_scenario_ids = {int(sp["scenario_id"]) for sp in state.signposts}
    scenarios_to_process = [
        s for s in state.scenarios if int(s["scenario_id"]) not in existing_scenario_ids
    ]

    sem = asyncio.Semaphore(_MAX_CONCURRENT_SCENARIOS)

    async def process_one(
        scenario: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        async with sem:
            signposts = await build_signposts_for_scenario(scenario, base_event_summary)
            return signposts, {
                "scenario_id": scenario["scenario_id"],
                "status": "success",
                "signpost_count": len(signposts),
            }

    results = await asyncio.gather(
        *(process_one(scenario) for scenario in scenarios_to_process)
    )
    generated: list[dict[str, Any]] = []
    scenario_results: list[dict[str, Any]] = []
    for signposts, scenario_result in results:
        generated.extend(signposts)
        scenario_results.append(scenario_result)

    return {
        "signposts": [*state.signposts, *generated],
        "signpost_result": {
            "scenario_group_id": state.scenario_group_id,
            "scenario_results": scenario_results,
            "signposts": generated,
        },
    }


def save_signposts(state: ScenarioDesignState) -> dict[str, Any]:
    if state.status in {"failure", "already_exist"}:
        return {}
    generated = (state.signpost_result or {}).get("signposts", [])
    saved_ids = (
        SignpostService().save_generated_signposts(generated, user_id=state.user_id)
        if generated
        else []
    )
    all_signposts = SignpostService().load_by_scenario_ids(
        [int(s["scenario_id"]) for s in state.scenarios]
    )
    group = ScenarioGroupService().update_state(
        state.scenario_group_id,
        stage="signpost_created",
        user_id=state.user_id,
    )
    return {
        "saved_signpost_ids": saved_ids,
        "signposts": all_signposts,
        "scenario_group": group,
        "status": "success",
        "message": f"Created {len(saved_ids)} signposts",
    }
