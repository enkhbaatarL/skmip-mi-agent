from __future__ import annotations

# ruff: noqa: CPY001
from uuid import UUID

from pydantic import ConfigDict, Field

from apps.persistence.scenario_quality_evaluation.schema import ScenarioQualityEvaluationPayload
from apps.persistence.schema_base import ApiModel


class CreateQualityEvaluationIn(ApiModel):
    model_config = ConfigDict(extra="forbid")

    user_id: int = Field(gt=0)
    request_id: UUID


class QualityEvaluationOut(ApiModel):
    data: ScenarioQualityEvaluationPayload
