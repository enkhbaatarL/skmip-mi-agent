from __future__ import annotations

from decimal import Decimal
from typing import Any

from apps.agents.scenario_group_agent.schemas.domain.event import EventPayload
from apps.agents.scenario_group_agent.schemas.domain.scenario import (
    NewScenarioGeneratedDetails,
)
from apps.agents.scenario_group_agent.subgraphs.scenario_generation.generation_stages import (
    stage1_build_context_pack,
    stage4_synthesize_fixed_scenarios,
    stage6_validate,
)


_LIKELIHOOD_WEIGHTS: dict[str, int] = {
    "very_low": 5,
    "low": 10,
    "medium": 20,
    "high": 35,
    "very_high": 50,
}


async def generate_new_scenario_row_details(
    event_data: EventPayload | dict[str, Any],
    dimension_values_list: list[dict[str, Any]],
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
    )
    stage6 = await stage6_validate(pack, stage4)
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
