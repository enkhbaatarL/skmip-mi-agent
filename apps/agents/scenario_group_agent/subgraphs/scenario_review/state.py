from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from apps.agents.scenario_group_agent.subgraphs.scenario_review.review_stages import (
    ReviewReport,
)


class ScenarioReviewState(BaseModel):
    group: dict[str, Any] = Field(default_factory=dict)
    requested_rows: list[dict[str, Any]] = Field(default_factory=list)
    requested_headers: list[dict[str, Any]] = Field(default_factory=list)
    persisted_scenarios: list[dict[str, Any]] = Field(default_factory=list)
    template_dims: list[dict[str, Any]] = Field(default_factory=list)
    scenario_group_id: int | None = None
    report: ReviewReport | None = None
    skip_review: bool = False
    error: str | None = None

