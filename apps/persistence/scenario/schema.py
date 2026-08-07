from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from apps.persistence.enums import ScenarioStatus
from apps.persistence.scenario.models import MiScenarioModel
from apps.persistence.schema_base import ApiModel


class RelatedMarket(ApiModel):
    market: Literal["TTF", "HH"]
    rationale: str = Field(min_length=1)

    @field_validator("rationale")
    @classmethod
    def _normalize_rationale(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("related market rationale must not be blank")
        return normalized


class ScenarioPayload(ApiModel):
    scenario_id: int
    scenario_group_id: int = 0
    display_order: int = 0
    title: str = ""
    description: str = ""
    narrative: str | None = None
    dimension_values: dict[str, Any] = Field(default_factory=dict)
    probability_score: Decimal | None = None
    probability_delta: Decimal | None = Decimal("0.0")
    baseline_yn: str | None = "N"
    global_pressure_band: str | None = None
    scenario_role: str | None = None
    global_pressure_rationale: str | None = None
    related_markets: list[RelatedMarket] = Field(default_factory=list)
    status: str = ScenarioStatus.CREATING.value
    del_yn: str | None = None

    @classmethod
    def from_model(cls, model: MiScenarioModel) -> ScenarioPayload:
        return cls.model_validate(
            {
                "scenario_id": model.scenario_id,
                "scenario_group_id": model.scenario_group_id,
                "display_order": model.display_order,
                "title": model.title,
                "description": model.narrative or "",
                "narrative": model.narrative,
                "dimension_values": model.dimension_values or {},
                "probability_score": model.probability_score,
                "probability_delta": model.probability_delta,
                "baseline_yn": model.baseline_yn,
                "global_pressure_band": model.global_pressure_band,
                "scenario_role": model.scenario_role,
                "global_pressure_rationale": model.global_pressure_rationale,
                "related_markets": [
                    item
                    for item in (getattr(model, "related_markets", None) or [])
                    if isinstance(item, dict) and item.get("market") in {"TTF", "HH"}
                ],
                "status": model.status,
                "del_yn": getattr(model, "del_yn", None),
            }
        )


class NewScenarioGeneratedDetails(ApiModel):
    model_config = ConfigDict(frozen=True)

    narrative: str
    probability_weight: Decimal
    probability_delta: Decimal


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

    @model_validator(mode="before")
    @classmethod
    def _coerce_legacy_dimension_shape(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        if "dimension_id" in value:
            return value

        dim_key = str(value.get("dim_key", "")).strip()
        if not dim_key:
            return value
        label = str(value.get("label", "")).strip() or dim_key
        raw_enums = value.get("value_enums") or []
        enum_items: list[dict[str, Any]] = []
        for item in raw_enums:
            if isinstance(item, dict):
                enum_id = str(item.get("id", item.get("label", ""))).strip()
                enum_label = str(item.get("label", item.get("id", ""))).strip()
                if not enum_id:
                    continue
                enum_items.append(
                    {
                        "id": enum_id,
                        "label": enum_label or enum_id,
                        "tail": bool(item.get("tail", False)),
                    }
                )
                continue
            enum_label = str(item).strip()
            if enum_label:
                enum_items.append({"id": enum_label, "label": enum_label, "tail": False})

        return {
            "dimension_id": dim_key,
            "label_ko": label,
            "description": str(value.get("description", "")).strip() or label,
            "required": bool(value.get("required", False)),
            "enum": enum_items,
        }


class ScenarioTemplate(BaseModel):
    template_dimensions_total: int = 0
    dimensions: list[ScenarioTemplateDimension] = Field(default_factory=list)


class ScenarioPipelineTemplateDimension(BaseModel):
    label: str = Field(description="Dimension 표시명")
    dim_key: str = Field(description="Dimension key")
    required: bool = Field(default=False, description="필수 여부")
    value_enums: list[str] = Field(
        default_factory=list,
        description="Dimension 값 후보 목록",
    )
    display_order: int = Field(default=999999, description="표시 순서")
    description: str = Field(default="", description="Dimension 의미 설명")

    @model_validator(mode="after")
    def _validate_template_dimension(self) -> "ScenarioPipelineTemplateDimension":
        dim_key = str(self.dim_key).strip()
        if not dim_key:
            raise ValueError("dim_key is required.")
        enums = [str(value).strip() for value in self.value_enums if str(value).strip()]
        if len(enums) == 1:
            raise ValueError(f"value_enums must be empty or include at least two values: dim_key={dim_key}")
        if len(set(enums)) != len(enums):
            raise ValueError(f"value_enums contains duplicates: dim_key={dim_key}")
        self.dim_key = dim_key
        self.label = str(self.label).strip() or dim_key
        self.description = str(self.description).strip() or self.label
        self.value_enums = enums
        return self

    def enum_items(self) -> list[dict[str, Any]]:
        return [
            {
                "id": enum_label,
                "label": enum_label,
                "tail": False,
            }
            for enum_label in self.value_enums
        ]

    def to_runtime_dimension(self) -> dict[str, Any]:
        return {
            "dim_key": self.dim_key,
            "label_ko": self.label,
            "description": self.description,
            "enum": self.enum_items(),
        }


class ScenarioPipelineTemplate(BaseModel):
    scenario_dimension_template_id: int | None = None
    event_type_l2_id: int | None = None
    event_type_definition: str = ""
    lng_price_impact_examples: str = ""
    template_checksum: str = ""
    label_ko: str = Field(default="", description="템플릿 라벨")
    template_dimensions_total: int | None = Field(
        default=None,
        description="템플릿 전체 Dimension 수",
    )
    dimensions: list[ScenarioPipelineTemplateDimension] = Field(
        default_factory=list,
        description="Dimension 템플릿 정의",
    )
    compatibility_rules: list[dict[str, Any]] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_template(self) -> "ScenarioPipelineTemplate":
        self.dimensions = self.ordered_dimensions()
        if len(self.dimensions) < 3:
            raise ValueError("template must include at least three dimensions.")
        dim_keys = [dimension.dim_key for dimension in self.dimensions]
        if len(set(dim_keys)) != len(dim_keys):
            raise ValueError("template contains duplicate dim_key.")
        if self.template_dimensions_total is None:
            self.template_dimensions_total = len(self.dimensions)
        if self.template_dimensions_total != len(self.dimensions):
            raise ValueError(
                "template_dimensions_total must match dimensions length "
                f"({self.template_dimensions_total} != {len(self.dimensions)})"
            )
        return self

    def ordered_dimensions(self) -> list[ScenarioPipelineTemplateDimension]:
        return sorted(
            self.dimensions,
            key=lambda dimension: (dimension.display_order, dimension.dim_key),
        )

    def resolved_total(self) -> int:
        return self.template_dimensions_total or len(self.dimensions)


SourceType = Literal[
    "event_fact",
    "template_domain_knowledge",
    "scenario_assumption",
    "derived_interpretation",
]

SelectionCriterion = Literal[
    "direct_event_fact",
    "lng_impact_path",
    "both",
    "none",
]


class SourceLineage(ApiModel):
    event_id: int
    event_type_l2_id: int
    scenario_dimension_template_id: int | None = None
    template_checksum: str | None = None
    dim_key: str = Field(min_length=1)
    value: str | None = None
    source_type: SourceType
    assumption_yn: Literal["Y", "N"]
    rationale: str = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_assumption_contract(self) -> SourceLineage:
        expected = "Y" if self.source_type == "scenario_assumption" else "N"
        if self.assumption_yn != expected:
            raise ValueError(
                "assumption_yn must be Y only for source_type=scenario_assumption",
            )
        return self


class DimensionValueDefinition(ApiModel):
    value_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    pressure_contribution: str | None = None
    source_assignments: list[SourceLineage] = Field(default_factory=list)


class ImpactLeverReference(ApiModel):
    # LLM output selects a stable lever code. The v4 finalizer hydrates the
    # catalog PK and rejects unresolved references before persistence.
    impact_lever_id: int | None = Field(default=None, gt=0)
    lever_code: str = Field(min_length=1)
    source_fact_ids: list[str] = Field(default_factory=list)
    mapping_rationale: str = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_source_fact_ids(self) -> ImpactLeverReference:
        normalized = [fact_id.strip() for fact_id in self.source_fact_ids]
        if any(not fact_id for fact_id in normalized):
            raise ValueError("impact lever sourceFactIds must not contain blanks")
        if len(normalized) != len(set(normalized)):
            raise ValueError("impact lever sourceFactIds must be unique")
        self.source_fact_ids = normalized
        self.lever_code = self.lever_code.strip()
        self.mapping_rationale = self.mapping_rationale.strip()
        return self


class DimensionDefinition(ApiModel):
    dimension_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    description: str = Field(min_length=1)
    required: bool = False
    display_order: int
    dimension_type: (
        Literal[
            "magnitude",
            "scope",
            "timing",
            "recovery",
            "mitigation",
            "interaction",
        ]
        | None
    ) = None
    value_kind: Literal["categorical", "numeric_range", "temporal"] | None = None
    unit: str | None = None
    selection_criterion: SelectionCriterion | None = None
    selection_rationale: str | None = None
    source_event_ids: list[int] = Field(default_factory=list)
    source_fact_ids: list[str] = Field(default_factory=list)
    lever_refs: list[str] = Field(default_factory=list)
    impact_lever_refs: list[ImpactLeverReference] = Field(default_factory=list)
    model_support_status: (
        Literal[
            "full",
            "partial",
            "none",
            "price_only",
        ]
        | None
    ) = None
    source_refs: list[SourceLineage] = Field(default_factory=list)
    values: list[DimensionValueDefinition] = Field(default_factory=list)
