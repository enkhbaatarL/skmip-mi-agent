from __future__ import annotations

from typing import Literal

from pydantic import Field

from apps.persistence.schema_base import ApiModel
from apps.agents.model_parameter_agent.schemas.api.parameters import ProposalParameter


class ProposeParametersIn(ApiModel):
    basecase_dir_path: str | None = Field(default=None)
    max_candidates: int = Field(default=8, ge=1, le=30)
    max_basecase_sample_rows: int = Field(default=5, ge=1, le=20)
    max_basecase_cols: int = Field(default=18, ge=6, le=60)
    allow_llm_fallback: bool = Field(default=False)
    model_name: str | None = Field(default=None)


class ProposeParametersRequest(ApiModel):
    user_id: int | None = Field(default=None)


class ProposeParametersData(ApiModel):
    model_param_proposal_id: int | None = None
    scenario_id: int | None = None
    scenario_group_id: int | None = None
    event_id: int | None = None
    proposal_parameters: list[ProposalParameter] = Field(default_factory=list)


class ProposeParametersOut(ApiModel):
    status: Literal["success", "error"] = "success"
    message: str = "model parameter proposal completed"
    data: ProposeParametersData


class ProposeParametersAcceptedData(ApiModel):
    model_param_proposal_id: int
    status: Literal["PROCESSING"] = "PROCESSING"


class ProposeParametersAcceptedOut(ApiModel):
    status: Literal["success", "error"] = "success"
    message: str = "accepted"
    data: ProposeParametersAcceptedData


class ProposeParametersCallbackData(ApiModel):
    model_param_proposal_id: int | None = None
    scenario_id: int | None = None
    scenario_group_id: int | None = None
    event_id: int | None = None
    status: Literal["PROPOSED", "FAILED"]


class ProposeParametersCallbackOut(ApiModel):
    status: Literal["success", "error"] = "success"
    message: str
    data: ProposeParametersCallbackData | None = None
