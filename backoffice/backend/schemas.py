from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


JsonObject = dict[str, Any]


def to_camel(value: str) -> str:
    parts = value.split("_")
    return parts[0] + "".join(part[:1].upper() + part[1:] for part in parts[1:])


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="allow")


class StrictApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class RunLifecycleState(StrEnum):
    IDLE = "idle"
    CREATING = "creating"
    GENERATION_WAITING_CALLBACK = "generation_waiting_callback"
    SCENARIO_CREATED = "scenario_created"
    VALIDATING = "validating"
    VALIDATION_WAITING_CALLBACK = "validation_waiting_callback"
    SCENARIO_VALIDATED = "scenario_validated"
    CREATING_SIGNPOSTS = "creating_signposts"
    SIGNPOST_WAITING_CALLBACK = "signpost_waiting_callback"
    SIGNPOST_CREATED = "signpost_created"
    CONFIRMING = "confirming"
    CONFIRMED = "confirmed"
    FAILED = "failed"


class CallbackType(StrEnum):
    GENERATION = "generation"
    VALIDATION = "validation"
    SIGNPOSTS = "signposts"


class SseEventType(StrEnum):
    ACCEPTED = "accepted"
    CALLBACK = "callback"
    DETAIL_REFRESHED = "detail_refreshed"
    VALIDATION_RESULT = "validation_result"
    NORMALIZED_MODEL_UPDATED = "normalized_model_updated"
    ERROR = "error"


class ScenarioHeader(ApiModel):
    key: str
    label: str
    display_order: int = 0


class SignpostModel(ApiModel):
    signpost_id: int | None = None
    label: str = ""
    probability_direction_code: str | None = None
    probability_impact_score: float | None = None
    signpost_reason: str | None = None
    display_order: int = 0
    strength: str | None = None
    use_yn: str | None = None
    keyword_hints: list[str] = Field(default_factory=list)
    evidence: str | None = None
    raw: JsonObject = Field(default_factory=dict)


class ScenarioRow(ApiModel):
    scenario_id: int | None = None
    display_order: int = 0
    title: str = ""
    narrative: str | None = None
    cells: JsonObject = Field(default_factory=dict)
    metrics: JsonObject | None = None
    impact: JsonObject | None = None
    baseline_yn: str | None = None
    signposts: list[SignpostModel] = Field(default_factory=list)
    raw: JsonObject = Field(default_factory=dict)


class ScenarioTable(ApiModel):
    headers: list[ScenarioHeader] = Field(default_factory=list)
    rows: list[ScenarioRow] = Field(default_factory=list)


class ScenarioGroupModel(ApiModel):
    scenario_group_id: int | None = None
    mi_event_id: int | None = None
    event_type_l2_id: int | None = None
    title: str | None = None
    summary: str | None = None
    description: str | None = None
    dimension_selected: list[str] = Field(default_factory=list)
    scenario_count: int | None = None
    status: str | None = None
    stage: str | None = None
    raw: JsonObject = Field(default_factory=dict)


class NormalizedScenarioDesign(ApiModel):
    event_list: JsonObject = Field(default_factory=lambda: {"events": []})
    branch_criteria_draft: JsonObject | None = None
    one_view_draft: JsonObject | None = None
    scenario_group_detail: JsonObject | None = None
    scenario_group: ScenarioGroupModel | None = None
    table: ScenarioTable = Field(default_factory=ScenarioTable)
    validation: JsonObject | None = None
    signpost_count: int = 0
    raw_source: JsonObject | None = None


class CreateRunIn(StrictApiModel):
    agent_base_url: str = Field(min_length=1)
    mi_event_id: int
    user_id: int

    @field_validator("agent_base_url")
    @classmethod
    def normalize_agent_base_url(cls, value: str) -> str:
        return value.rstrip("/")


class ValidationRunIn(ApiModel):
    user_id: int | None = None
    table: ScenarioTable


class SignpostsRunIn(ApiModel):
    user_id: int | None = None
    table: ScenarioTable


class ConfirmationRunIn(ApiModel):
    user_id: int | None = None
    scenario_group: JsonObject
    table: ScenarioTable


class TimelineEvent(ApiModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    type: str
    message: str
    data: JsonObject | None = None


class ErrorRecord(ApiModel):
    at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    step: str
    message: str
    status_code: int | None = None
    body: Any = None


class RunRecord(ApiModel):
    run_id: str
    mi_event_id: int
    user_id: int
    agent_base_url: str
    scenario_group_id: int | None = None
    lifecycle_state: RunLifecycleState = RunLifecycleState.IDLE
    agent_status: str | None = None
    agent_stage: str | None = None
    accepted: dict[str, JsonObject] = Field(default_factory=dict)
    callbacks: dict[str, JsonObject] = Field(default_factory=dict)
    detail: JsonObject | None = None
    latest_requests: dict[str, JsonObject] = Field(default_factory=dict)
    latest_agent_requests: dict[str, JsonObject] = Field(default_factory=dict)
    normalized: NormalizedScenarioDesign = Field(default_factory=NormalizedScenarioDesign)
    timeline: list[TimelineEvent] = Field(default_factory=list)
    errors: list[ErrorRecord] = Field(default_factory=list)


class RunOut(ApiModel):
    run: RunRecord


class OAuthTokenOut(BaseModel):
    access_token: str = "backoffice-local-token"
    expires_in: int = 3600


class AgentHttpError(Exception):
    def __init__(self, step: str, status_code: int, body: Any) -> None:
        self.step = step
        self.status_code = status_code
        self.body = body
        super().__init__(f"Agent {step} request failed with status {status_code}")
