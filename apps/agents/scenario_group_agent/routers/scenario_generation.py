from __future__ import annotations

# Compatibility exports for the pre-split Scenario Group router module.
from fastapi import APIRouter

from apps.agents.scenario_group_agent.persistence.scenario_group_service import ScenarioGroupService
from apps.agents.scenario_group_agent.persistence.scenario_service import ScenarioService
from apps.agents.scenario_group_agent.routers.scenario_groups import (
    approve_dimension_mappings,
    confirm_generation,
    create_signposts,
    create_v4_scenarios_compatibility,
    router as scenario_groups_router,
    validate_scenarios,
)


router = APIRouter()
router.include_router(scenario_groups_router)


__all__ = [
    "ScenarioGroupService",
    "ScenarioService",
    "approve_dimension_mappings",
    "confirm_generation",
    "create_signposts",
    "create_v4_scenarios_compatibility",
    "router",
    "validate_scenarios",
]
