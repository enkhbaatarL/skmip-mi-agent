from __future__ import annotations

from typing import Any

from apps.agents.scenario_group_agent.subgraphs.scenario_review.review_stages import (
    build_context,
    run_review,
)
from apps.agents.scenario_group_agent.subgraphs.scenario_review.state import (
    ScenarioReviewState,
)


async def run_review_node(state: ScenarioReviewState) -> dict[str, Any]:
    if state.skip_review or state.error:
        return {}
    context = build_context(
        group=state.group,
        requested_rows=state.requested_rows,
        persisted_scenarios=state.persisted_scenarios,
        template_dims=state.template_dims,
        requested_headers=state.requested_headers,
    )
    return {"report": await run_review(context)}

