from __future__ import annotations

from typing import Literal

from pydantic import Field

from apps.agents.model_parameter_agent.schemas.api.parameters import (
    ProposalParameter,
)
from apps.persistence.schema_base import ApiModel


class ConfirmParametersDataIn(ApiModel):
    confirmation_parameters: list[ProposalParameter] = Field(default_factory=list)


class ConfirmParametersIn(ApiModel):
    data: ConfirmParametersDataIn


class ConfirmParametersDataOut(ApiModel):
    model_param_proposal_id: int
    status: Literal["CONFIRMED"] = "CONFIRMED"


class ConfirmParametersOut(ApiModel):
    status: Literal["success", "error"] = "success"
    message: str = "model parameter proposal confirmed"
    data: ConfirmParametersDataOut
