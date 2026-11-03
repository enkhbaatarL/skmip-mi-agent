from __future__ import annotations

# ruff: noqa: CPY001
from typing import Literal, Self

from pydantic import ConfigDict, Field, JsonValue, model_validator

from apps.persistence.scenario_group_operation.schema import ScenarioGroupOperationPayload
from apps.persistence.schema_base import ApiModel


JUDGE_IDS = ("J-01", "J-02", "J-03", "J-04", "J-05", "J-06", "J-11")
QualityVerdict = Literal["PASS", "WARN", "FAIL", "NEEDS_FACT"]


class QualityFactCheck(ApiModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    claim: str = Field(min_length=1, description="입력에서 추출한 검증 대상 주장. 전망·조건·주장 주체를 보존한다.")
    verification_question: str = Field(min_length=1, description="외부 자료로 확인할 구체적인 질문")
    entity: str | None = Field(description="입력에서 확인되는 대상 설비·기업·기관 등. 불명확하면 null")
    region: str | None = Field(description="입력에서 확인되는 대상 지역. 불명확하면 null")
    target_period: str | None = Field(description="입력에서 확인되는 주장의 대상 기간. 불명확하면 null")


class QualityIssue(ApiModel):
    model_config = ConfigDict(extra="forbid")

    scenario_ids: list[int] = Field(min_length=1)
    evidence_path: str = Field(min_length=1, description="JSON pointer into inputSnapshot")
    evidence: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    suggested_fix: str = Field(min_length=1)
    fact_dependency: Literal["NONE", "EVENT_PAYLOAD_ONLY", "EXTERNAL_FACT_REQUIRED"]
    fact_check: QualityFactCheck | None = Field(
        default=None,
        description="EXTERNAL_FACT_REQUIRED인 신규 평가에서 생성하는 검증 계획. 그 외에는 null",
    )


class QualityItem(ApiModel):
    model_config = ConfigDict(extra="forbid")

    judge_id: Literal["J-01", "J-02", "J-03", "J-04", "J-05", "J-06", "J-11"]
    score: int = Field(ge=1, le=5)
    verdict: Literal["PASS", "WARN", "FAIL"]
    violations: list[QualityIssue]

    @model_validator(mode="after")
    def require_evidence(self) -> Self:
        if self.verdict != "PASS" and not self.violations:
            msg = "WARN/FAIL requires evidence-backed violations"
            raise ValueError(msg)
        return self


class ScenarioQualityJudgment(ApiModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1)
    items: list[QualityItem] = Field(min_length=7, max_length=7)

    @model_validator(mode="after")
    def require_seven_rubrics(self) -> Self:
        if sorted(item.judge_id for item in self.items) != sorted(JUDGE_IDS):
            msg = "Each scenario rubric must occur exactly once"
            raise ValueError(msg)
        return self


class ScenarioQualityEvaluationPayload(ScenarioGroupOperationPayload):
    request_id: str
    input_snapshot: dict[str, JsonValue]
    input_hash: str
    prompt_version: str
    result: ScenarioQualityJudgment | None = None
    verdict: QualityVerdict | None = None
    average_score: float | None = None
    llm_metadata: dict[str, JsonValue] | None = None
