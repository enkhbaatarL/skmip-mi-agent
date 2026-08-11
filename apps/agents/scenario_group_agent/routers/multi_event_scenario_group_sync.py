from __future__ import annotations

from fastapi import APIRouter

from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.api_schema import (
    V2CreateScenariosOut,
    VersionedCreateScenariosOut,
)
from apps.agents.scenario_group_agent.routers.versioned_scenario_generation_sync import (
    create_v2_scenarios_sync,
    create_v3_scenarios_sync,
    create_v4_scenarios_sync,
)


router = APIRouter(tags=["scenario-groups-sync-test"])
router.add_api_route(
    "/v2/scenario-groups/sync",
    create_v2_scenarios_sync,
    methods=["POST"],
    response_model=V2CreateScenariosOut,
    summary="v2 1~5개 이벤트 원본 dimension 시나리오 생성",
)
router.add_api_route(
    "/v3/scenario-groups/sync",
    create_v3_scenarios_sync,
    methods=["POST"],
    response_model=VersionedCreateScenariosOut,
    summary="v3 1~5개 이벤트 합성 dimension 시나리오 생성",
)
router.add_api_route(
    "/v4/scenario-groups/sync",
    create_v4_scenarios_sync,
    methods=["POST"],
    response_model=VersionedCreateScenariosOut,
    summary="v4 1~5개 이벤트 모델 영향 레버 시나리오 생성",
)


__all__ = ["router"]
