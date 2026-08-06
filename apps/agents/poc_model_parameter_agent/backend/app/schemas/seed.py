from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator


class SeedDocument(BaseModel):
    levers: dict[str, dict[str, Any]]
    parameters: dict[str, dict[str, Any]]
    mappings: list[dict[str, Any]]
    dimension_rules: dict[str, dict[str, Any]] = Field(alias="dimensionRules")
    domain_rules: list[dict[str, Any]] = Field(alias="domainRules")
    pressure_bands: list[dict[str, Any]] = Field(alias="pressureBands")
    flow_profile: dict[str, Any] = Field(alias="flowProfile")
    memory_v1: str = Field(alias="memoryV1")
    memory_v2: str = Field(alias="memoryV2")
    skill_v1: str = Field(alias="skillV1")
    example1_meta: dict[str, Any] = Field(alias="example1Meta")
    example1: dict[str, Any]
    example2_meta: dict[str, Any] = Field(alias="example2Meta")
    example2: dict[str, Any]

    @model_validator(mode="after")
    def validate_catalog_references(self) -> SeedDocument:
        lever_keys = set(self.levers)
        parameter_keys = set(self.parameters)
        for mapping in self.mappings:
            if mapping.get("leverCode") not in lever_keys:
                raise ValueError(f"Mapping lever가 Catalog에 없습니다: {mapping.get('leverCode')}")
            if mapping.get("parameterCode") not in parameter_keys:
                raise ValueError(f"Mapping parameter가 Catalog에 없습니다: {mapping.get('parameterCode')}")
        if len(self.flow_profile.get("steps", [])) != 9:
            raise ValueError("Flow Profile은 정확히 9개 step이어야 합니다.")
        return self
