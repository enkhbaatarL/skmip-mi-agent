from __future__ import annotations

from pydantic import Field

from apps.persistence.enums import (
    ScenarioGroupStage,
    ScenarioGroupStatus,
)
from apps.persistence.scenario_group.models import MiScenarioGroupModel
from apps.persistence.schema_base import ApiModel


class ScenarioGroupPayload(ApiModel):
    scenario_group_id: int
    mi_event_id: int | None = None
    event_type_l2_id: int | None = None
    request_usr_id: int | None = None
    title: str = ""
    summary: str | None = None
    description: str | None = None
    dimension_selected: list[str] = Field(default_factory=list)
    scenario_count: int = 0
    status: str = ScenarioGroupStatus.CREATING.value
    stage: str = ScenarioGroupStage.READY.value
    api_version: str = "v1"
    generation_strategy: str = "single_event_template_dimensions"
    comparison_run_id: str | None = None
    target_market: str | None = None
    impact_catalog_version: str | None = None
    impact_catalog_checksum: str | None = None
    template_checksum: str | None = None
    parameter_mapping_ready: bool = False
    dimension_definitions: list[dict[str, object]] = Field(default_factory=list)
    generation_diagnostics: dict[str, object] = Field(default_factory=dict)

    @classmethod
    def from_model(cls, model: MiScenarioGroupModel) -> ScenarioGroupPayload:
        return cls.model_validate(
            {
                "scenario_group_id": model.scenario_group_id,
                "mi_event_id": model.mi_event_id,
                "event_type_l2_id": model.event_type_l2_id,
                "request_usr_id": model.request_usr_id,
                "title": model.title,
                "summary": model.summary,
                "description": model.description,
                "dimension_selected": model.dimension_selected or [],
                "scenario_count": model.scenario_count,
                "status": model.status,
                "stage": model.stage,
                "api_version": getattr(model, "api_version", None) or "v1",
                "generation_strategy": (
                    getattr(model, "generation_strategy", None) or "single_event_template_dimensions"
                ),
                "comparison_run_id": getattr(
                    model,
                    "comparison_run_id",
                    None,
                ),
                "target_market": getattr(model, "target_market", None),
                "impact_catalog_version": getattr(
                    model,
                    "impact_catalog_version",
                    None,
                ),
                "impact_catalog_checksum": getattr(
                    model,
                    "impact_catalog_checksum",
                    None,
                ),
                "template_checksum": getattr(
                    model,
                    "template_checksum",
                    None,
                ),
                "parameter_mapping_ready": bool(
                    getattr(model, "parameter_mapping_ready", False),
                ),
                "dimension_definitions": (getattr(model, "dimension_definitions", None) or []),
                "generation_diagnostics": (getattr(model, "generation_diagnostics", None) or {}),
            }
        )
