from __future__ import annotations

from fastapi import APIRouter

from apps.agents.scenario_group_agent.routers.events import router as events_router
from apps.agents.scenario_group_agent.routers.multi_event_scenario_group_sync import (
    router as multi_event_scenario_group_sync_router,
)
from apps.agents.scenario_group_agent.routers.scenario_group_stream import router as scenario_group_stream_router
from apps.agents.scenario_group_agent.routers.scenario_groups import router as scenario_groups_router
from apps.agents.scenario_group_agent.routers.v1_scenario_groups import router as v1_scenario_groups_router


router = APIRouter()
router.include_router(v1_scenario_groups_router)
router.include_router(multi_event_scenario_group_sync_router)
router.include_router(scenario_groups_router)
router.include_router(scenario_group_stream_router)
router.include_router(events_router)
