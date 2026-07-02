from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from apps.agents.scenario_group_agent.subgraphs.signpost_generation.schema import GeneratedSignpost


class SignpostGenerationState(BaseModel):
    scenario: dict[str, Any] | None = None
    base_event_summary: dict[str, str] = Field(default_factory=dict)
    labels: list[str] = Field(default_factory=list)
    stage4_assignments: list[dict[str, str]] = Field(default_factory=list)
    stage5_keyword_hints: list[list[str]] = Field(default_factory=list)
    signposts: list[GeneratedSignpost] = Field(default_factory=list)
    skip_generation: bool = False
    error: str | None = None
