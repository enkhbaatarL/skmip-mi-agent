# ruff: noqa: F403, I001

from __future__ import annotations

from typing import Any

from apps.agents.scenario_group_agent.schemas.graph.generation import GeneratedSignpost
from apps.agents.scenario_group_agent.subgraphs.signpost_generation.generation_stages import *
from apps.agents.scenario_group_agent.subgraphs.signpost_generation.flow import (
    signpost_generation_runnable,
)


async def build_signposts_for_scenario(
    scenario: dict[str, Any],
    base_event_summary: dict[str, str],
) -> list[GeneratedSignpost]:
    output = await signpost_generation_runnable.ainvoke(
        {
            "scenario": scenario,
            "base_event_summary": base_event_summary,
        },
    )
    return list(output.get("signposts") or [])
