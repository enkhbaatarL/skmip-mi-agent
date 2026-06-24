from __future__ import annotations

from pydantic import BaseModel, Field


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
