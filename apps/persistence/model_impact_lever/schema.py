from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from apps.persistence.schema_base import ApiModel


KnownUnsupportedReasonCode = Literal[
    "NO_PARAMETER_BINDING",
    "INACTIVE_MODEL_PARAMETER",
    "CATALOG_MARKED_UNSUPPORTED",
]
ModelSupportIssueReasonCode = Literal[
    "NO_PARAMETER_BINDING",
    "INACTIVE_MODEL_PARAMETER",
    "CATALOG_MARKED_UNSUPPORTED",
    "PRICE_ONLY",
]


class ModelImpactLeverParameterBinding(ApiModel):
    parameter_name: str
    role: Literal["primary", "alternative"] = "primary"
    applicability: str = ""
    support_status: Literal["executable", "known_unsupported"]
    unsupported_reason_code: (
        Literal[
            "INACTIVE_MODEL_PARAMETER",
            "CATALOG_MARKED_UNSUPPORTED",
        ]
        | None
    ) = None

    @model_validator(mode="after")
    def _validate_unsupported_reason(self) -> ModelImpactLeverParameterBinding:
        if self.support_status == "executable" and self.unsupported_reason_code is not None:
            message = "executable binding must not define unsupportedReasonCode"
            raise ValueError(message)
        if self.support_status == "known_unsupported" and self.unsupported_reason_code is None:
            message = "known_unsupported binding requires unsupportedReasonCode"
            raise ValueError(message)
        return self


class ModelImpactLeverPayload(ApiModel):
    impact_lever_id: int
    lever_code: str
    domain: Literal["demand", "supply", "trade", "price_only"]
    label: str
    description: str
    applicability_hint: str | None = None
    parent_lever_code: str | None = None
    parameter_bindings: list[ModelImpactLeverParameterBinding] = Field(default_factory=list)
    catalog_version: str

    @model_validator(mode="after")
    def _validate_bindings(self) -> ModelImpactLeverPayload:
        names = [binding.parameter_name for binding in self.parameter_bindings]
        if len(names) != len(set(names)):
            message = f"duplicate parameter binding: leverCode={self.lever_code}"
            raise ValueError(message)
        if self.domain == "price_only" and self.parameter_bindings:
            message = "price_only lever must not define parameter bindings"
            raise ValueError(message)
        return self


class ModelImpactLeverSupportIssue(ApiModel):
    lever_code: str
    reason_code: ModelSupportIssueReasonCode
    parameter_name: str | None = None
