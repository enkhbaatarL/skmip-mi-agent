from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from apps.agents.model_parameter_agent.schemas.api.parameters import ProposalParameter


class ConfirmParametersState(BaseModel):
    model_param_proposal_id: int
    user_id: int | None = None
    confirmation_parameters: list[ProposalParameter] = Field(default_factory=list)
    result: dict[str, Any] | None = None
