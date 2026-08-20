from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from apps.persistence.schema_base import ApiModel


OperationType = Literal["create", "validation", "signpost", "confirmation"]
OperationStatus = Literal["queued", "running", "succeeded", "failed", "interrupted"]
TERMINAL_OPERATION_STATUSES = frozenset({"succeeded", "failed", "interrupted"})
TERMINAL_EVENT_TYPES = frozenset({"completed", "failed", "interrupted"})


class ScenarioGroupOperationPayload(ApiModel):
    operation_id: str
    scenario_group_id: int
    operation_type: OperationType
    engine_version: str
    source: str = "api"
    status: OperationStatus
    current_phase: str | None = None
    retry_summary: dict[str, Any] = Field(default_factory=dict)
    presentation_snapshot: dict[str, Any] = Field(default_factory=dict)
    snapshot_revision: int = 0
    latest_sequence: int = 0
    last_error: dict[str, Any] | None = None
    mlflow_trace_id: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    heartbeat_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


ValidationVerdict = Literal["PASS", "PASS_WITH_WARNINGS", "BLOCK"]
ValidationCheckStatus = Literal["PASS", "WARN", "FAIL", "INFO"]
ValidationChangeType = Literal["NEW", "TITLE_CHANGED", "REORDERED", "COMBINATION_CHANGED"]


class ValidationCheckPayload(ApiModel):
    check_id: str
    status: ValidationCheckStatus
    blocking: bool
    detail: str
    offenders: list[str] = Field(default_factory=list)
    advice: list[str] = Field(default_factory=list)


class ValidationGeneratedFieldsPayload(ApiModel):
    narrative: str
    probability_score: float = Field(ge=0, le=100)
    probability_delta: float = 0
    pressure_band: Literal[
        "strong_bullish",
        "bullish",
        "balanced",
        "bearish",
        "strong_bearish",
    ]
    pressure_rationale: str
    related_markets: list[dict[str, Any]] = Field(default_factory=list)


class ValidationScenarioUpsertPayload(ApiModel):
    scenario_id: int | None = None
    client_row_key: str
    change_type: ValidationChangeType
    display_order: int
    title: str
    dimension_values: dict[str, str]
    generated_fields: ValidationGeneratedFieldsPayload


class ValidationScenarioChangeSetPayload(ApiModel):
    upserts: list[ValidationScenarioUpsertPayload] = Field(default_factory=list)
    delete_scenario_ids: list[int] = Field(default_factory=list)


class ValidationGeneratedDetailPayload(ApiModel):
    client_row_key: str
    scenario_id: int | None = None
    title: str
    narrative: str
    probability_score: float
    pressure_band: str
    pressure_rationale: str
    related_markets: list[dict[str, Any]] = Field(default_factory=list)


class ValidationResultPayload(ApiModel):
    verdict: ValidationVerdict
    is_valid: bool
    can_proceed: bool
    review_skipped: bool = False
    summary: dict[str, int] = Field(default_factory=dict)
    checks: list[ValidationCheckPayload] = Field(default_factory=list)
    generated_details: list[ValidationGeneratedDetailPayload] = Field(default_factory=list)
    reason_markdown: str


class ValidationApplicationPayload(ApiModel):
    applied_at: datetime
    applied_scenario_fingerprint: str
    new_scenario_id_map: dict[str, int] = Field(default_factory=dict)


class ValidationOperationResultPayload(ApiModel):
    schema_version: Literal["v1"] = "v1"
    mode: Literal["unchanged", "changed", "blocked"]
    base_scenario_fingerprint: str
    dimension_definition_fingerprint: str
    base_dimension_definition_fingerprint: str | None = None
    requested_dimension_ids: list[str] = Field(default_factory=list)
    requested_dimension_definitions: list[dict[str, Any]] = Field(default_factory=list)
    promoted_dimension_ids: list[str] = Field(default_factory=list)
    candidate_source_fingerprint: str | None = None
    validation_result: ValidationResultPayload
    scenario_change_set: ValidationScenarioChangeSetPayload | None = None
    application: ValidationApplicationPayload | None = None


class ScenarioGroupOperationInternalPayload(ApiModel):
    operation_id: str
    scenario_group_id: int
    operation_type: OperationType
    status: OperationStatus
    result_payload: ValidationOperationResultPayload | dict[str, Any] | None = None


class ScenarioGroupOperationEventPayload(ApiModel):
    operation_id: str
    scenario_group_id: int
    sequence: int
    event_type: str
    phase: str | None = None
    title: str
    message_markdown: str
    payload: dict[str, Any] = Field(default_factory=dict)
    snapshot_revision: int = 0
    mlflow_trace_id: str | None = None
    created_at: datetime | None = None
