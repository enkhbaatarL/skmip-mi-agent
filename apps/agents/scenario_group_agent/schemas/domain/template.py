from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator


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
