from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from apps.persistence.enums import ScenarioStatus
from apps.persistence.scenario.models import MiScenarioModel
from apps.persistence.schema_base import ApiModel


class ScenarioPayload(ApiModel):
    scenario_id: int
    scenario_group_id: int = 0
    display_order: int = 0
    title: str = ""
    description: str = ""
    narrative: str | None = None
    dimension_values: dict[str, Any] = Field(default_factory=dict)
    price_direction: dict[str, Any] = Field(default_factory=dict)
    probability_score: Decimal | None = None
    probability_delta: Decimal | None = Decimal("0.0")
    impact_jkm: str | None = None
    impact_ttf: str | None = None
    impact_hh: str | None = None
    baseline_yn: str | None = "N"
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
                "price_direction": {
                    "jkm": model.impact_jkm,
                    "ttf": model.impact_ttf,
                    "hh": model.impact_hh,
                },
                "probability_score": model.probability_score,
                "probability_delta": model.probability_delta,
                "impact_jkm": model.impact_jkm,
                "impact_ttf": model.impact_ttf,
                "impact_hh": model.impact_hh,
                "baseline_yn": model.baseline_yn,
                "status": model.status,
                "del_yn": getattr(model, "del_yn", None),
            }
        )


class NewScenarioGeneratedDetails(ApiModel):
    model_config = ConfigDict(frozen=True)

    narrative: str
    probability_weight: Decimal
    probability_delta: Decimal
    impact_jkm: str | None
    impact_ttf: str | None
    impact_hh: str | None


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

    @model_validator(mode="after")
    def _validate_template_dimension(self) -> "ScenarioPipelineTemplateDimension":
        dim_key = str(self.dim_key).strip()
        if not dim_key:
            raise ValueError("dim_key is required.")
        enums = [str(value).strip() for value in self.value_enums if str(value).strip()]
        if len(enums) < 2:
            raise ValueError(f"value_enums must include at least two values: dim_key={dim_key}")
        if len(set(enums)) != len(enums):
            raise ValueError(f"value_enums contains duplicates: dim_key={dim_key}")
        self.dim_key = dim_key
        self.label = str(self.label).strip() or dim_key
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
            "description": self.label,
            "enum": self.enum_items(),
        }


class ScenarioPipelineTemplate(BaseModel):
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
