from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel


class ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class ScenarioGroupPayload(ApiModel):
    scenario_group_id: int
    mi_event_id: int
    event_type_l2_id: int
    request_usr_id: int | None = None
    title: str
    summary: str | None = None
    description: str | None = None
    dimension_selected: list[str] = Field(default_factory=list)
    scenario_count: int = 0
    status: str = "creating"
    stage: str = "ready"


class ScenarioHeader(ApiModel):
    key: str
    label: str
    display_order: int


class ScenarioMetrics(ApiModel):
    probability_score: Decimal | None = None
    probability_delta: Decimal | None = Field(default=Decimal("0.0"))

    @model_validator(mode="after")
    def _coerce_delta(self) -> ScenarioMetrics:
        if self.probability_delta is None:
            self.probability_delta = Decimal("0.0")
        return self


class ScenarioImpact(ApiModel):
    jkm: str | None = None
    ttf: str | None = None
    hh: str | None = None


class SignpostPayload(ApiModel):
    signpost_id: int
    label: str
    probability_direction_code: str | None = None
    probability_impact_score: Decimal | None = None
    signpost_reason: str | None = None
    display_order: int = 0
    strength: str | None = None
    use_yn: str | None = None
    keyword_hints: list[str] = Field(default_factory=list)


class ScenarioRow(ApiModel):
    scenario_id: int | None = None
    display_order: int = 0
    title: str = ""
    narrative: str | None = None
    cells: dict[str, Any] = Field(default_factory=dict)
    metrics: ScenarioMetrics | None = None
    impact: ScenarioImpact | None = None
    baseline_yn: str | None = None
    signposts: list[SignpostPayload] = Field(default_factory=list)


class ScenarioTable(ApiModel):
    headers: list[ScenarioHeader]
    rows: list[ScenarioRow]


class ScenarioGroupTableData(ApiModel):
    scenario_group: ScenarioGroupPayload
    table: ScenarioTable


class ScenarioGroupQueryPayload(ScenarioGroupPayload):
    del_yn: str = "N"


class SignpostQueryPayload(SignpostPayload):
    del_yn: str = "N"


class ScenarioQueryRow(ScenarioRow):
    del_yn: str = "N"
    signposts: list[SignpostQueryPayload] = Field(default_factory=list)


class ScenarioQueryTable(ApiModel):
    headers: list[ScenarioHeader]
    rows: list[ScenarioQueryRow]


class ScenarioGroupAcceptedData(ApiModel):
    """동기 처리 완료 직후 반환하는 최소 상태 정보."""

    scenario_group_id: int
    status: str
    stage: str


class ScenarioGroupAcceptedOut(BaseModel):
    """Callback API 전환 후 3개 비동기 엔드포인트의 HTTP 200 응답 스키마."""

    status: str = "success"
    message: str = "성공"
    data: ScenarioGroupAcceptedData


class ScenarioTemplateEnum(BaseModel):
    id: str
    label: str
    tail: bool = False


class ScenarioTemplateDimension(BaseModel):
    dimension_id: str
    label_ko: str
    description: str
    required: bool = False
    enum: list[ScenarioTemplateEnum] = Field(default_factory=list)


class ScenarioTemplate(BaseModel):
    template_dimensions_total: int = 0
    dimensions: list[ScenarioTemplateDimension] = Field(default_factory=list)
