from __future__ import annotations

from fastapi import APIRouter

from apps.agents.scenario_group_agent.routers.events import router as events_router
from apps.agents.scenario_group_agent.routers.scenario_generation import router as scenario_generation_router
from apps.agents.scenario_group_agent.routers.scenario_generation_sync import router as scenario_generation_sync_router
from apps.agents.scenario_group_agent.routers.scenario_group_management import (
    router as scenario_group_management_router,
)


router = APIRouter()
router.include_router(scenario_generation_router)
router.include_router(scenario_generation_sync_router)
router.include_router(scenario_group_management_router)
router.include_router(events_router)
