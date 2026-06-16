from __future__ import annotations

from fastapi import APIRouter

from apps.agents.scenario_group_agent.flows.confirm_generation.flow import (
    get_runnable_graph as get_confirm_generation_runnable,
)
from apps.agents.scenario_group_agent.flows.create_scenarios.flow import (
    get_runnable_graph as get_create_scenarios_runnable,
)
from apps.agents.scenario_group_agent.flows.create_signposts.flow import (
    get_runnable_graph as get_create_signposts_runnable,
)
from apps.agents.scenario_group_agent.flows.validate_scenarios.flow import (
    get_runnable_graph as get_validate_scenarios_runnable,
)
from apps.agents.scenario_group_agent.schemas.confirm_generation import (
    ConfirmGenerationIn,
    ConfirmGenerationOut,
)
from apps.agents.scenario_group_agent.schemas.create_scenarios import (
    CreateScenariosIn,
    CreateScenariosOut,
)
from apps.agents.scenario_group_agent.schemas.create_signposts import (
    CreateSignpostsIn,
    CreateSignpostsOut,
)
from apps.agents.scenario_group_agent.schemas.validate_scenarios import (
    ValidateScenariosIn,
    ValidateScenariosOut,
)

router = APIRouter()


@router.post("/scenario-groups", response_model=CreateScenariosOut)
async def create_scenarios(payload: CreateScenariosIn) -> CreateScenariosOut:
    result = await get_create_scenarios_runnable().ainvoke(payload.model_dump())
    return CreateScenariosOut.model_validate(result)


@router.post(
    "/scenario-groups/{scenario_group_id}/validation",
    response_model=ValidateScenariosOut,
)
async def validate_scenarios(
    scenario_group_id: int,
    payload: ValidateScenariosIn,
) -> ValidateScenariosOut:
    data = {"scenario_group_id": scenario_group_id, **payload.model_dump()}
    result = await get_validate_scenarios_runnable().ainvoke(data)
    return ValidateScenariosOut.model_validate(result)


@router.post(
    "/scenario-groups/{scenario_group_id}/signposts", response_model=CreateSignpostsOut
)
async def create_signposts(
    scenario_group_id: int,
    payload: CreateSignpostsIn,
) -> CreateSignpostsOut:
    data = {
        "scenario_group_id": scenario_group_id,
        **payload.model_dump(),
    }
    result = await get_create_signposts_runnable().ainvoke(data)
    return CreateSignpostsOut.model_validate(result)


@router.post(
    "/scenario-groups/{scenario_group_id}/confirmation",
    response_model=ConfirmGenerationOut,
)
async def confirm_generation(
    scenario_group_id: int,
    payload: ConfirmGenerationIn,
) -> ConfirmGenerationOut:
    result = await get_confirm_generation_runnable().ainvoke(
        {
            "scenario_group_id": scenario_group_id,
            **payload.model_dump(exclude_unset=True),
        }
    )
    return ConfirmGenerationOut.model_validate(result)
