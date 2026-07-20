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


class ScenarioGroupListRow(ApiModel):
    scenario_group_id: int
    title: str
    base_event_title: str | None = None
    mi_event_id: int | None = None
    status: str | None = None
    stage: str | None = None
    scenario_count: int = 0
    signpost_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted: bool = False
    del_yn: str = "N"
    latest_run_id: str | None = None
    source: str = "backoffice_memory"
    raw: JsonObject = Field(default_factory=dict)


class ScenarioGroupListMeta(ApiModel):
    source: str
    total: int
    returned: int
    include_deleted: bool = False
    fallback_reason: str | None = None


class ScenarioGroupListOut(ApiModel):
    rows: list[ScenarioGroupListRow] = Field(default_factory=list)
    meta: ScenarioGroupListMeta
    raw_source: JsonObject | None = None


class EventTypeInfo(ApiModel):
    id: int | None = None
    code: str = ""
    label: str = ""


class RelatedScenarioGroupSummary(ApiModel):
    scenario_group_id: int | None = None
    status: str | None = None
    stage: str | None = None
    deleted: bool = False
    del_yn: str = "N"
    scenario_count: int = 0
    signpost_count: int = 0
    title: str | None = None


class EventActionState(ApiModel):
    type: str = "create"
    label: str = "생성하기"
    disabled: bool = False
    reason: str | None = None


class EventListRow(ApiModel):
    mi_event_id: int
    title: str = ""
    one_line_summary: str = ""
    event_time: str = ""
    occurred_at: str = ""
    latest_record_first_created: str = ""
    oldest_record_first_created: str = ""
    category: str = ""
    event_type_l1: EventTypeInfo = Field(default_factory=EventTypeInfo)
    event_type_l2: EventTypeInfo = Field(default_factory=EventTypeInfo)
    new_yn: str = "Y"
    signal_yn: str = "N"
    signal_confidence: float | None = None
    signal_reason: str | None = None
    scenario_suggest_yn: str = "N"
    scenario_suggest_reason: str | None = None
    tags: list[str] = Field(default_factory=list)
    related_scenario_group: RelatedScenarioGroupSummary | None = None
    scenario_action_state: EventActionState = Field(default_factory=EventActionState)
    raw: JsonObject = Field(default_factory=dict)


class EventPagination(ApiModel):
    page: int = 1
    page_size: int = 20
    total: int = 0
    has_previous: bool = False
    has_next: bool = False


class EventListMeta(ApiModel):
    source: str = "backoffice_empty"
    fallback_reason: str | None = None


class EventListOut(ApiModel):
    rows: list[EventListRow] = Field(default_factory=list)
    pagination: EventPagination = Field(default_factory=EventPagination)
    meta: EventListMeta = Field(default_factory=EventListMeta)
    raw_source: JsonObject | None = None


class EventDetailEvent(EventListRow):
    key_bullets: list[str] = Field(default_factory=list)
    detail_analysis: str = ""
    source_mi_record_ids: list[int] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    language: str = "ko"


class EventDetailOut(ApiModel):
    event: EventDetailEvent
    scenario_template: JsonObject = Field(default_factory=dict)
    meta: EventListMeta = Field(default_factory=EventListMeta)
    raw_source: JsonObject | None = None


class DeleteScenarioGroupIn(StrictApiModel):
    agent_base_url: str = Field(min_length=1)
    user_id: int
    delete_authorization: str = Field(min_length=1)

    @field_validator("agent_base_url")
    @classmethod
    def normalize_agent_base_url(cls, value: str) -> str:
        return value.rstrip("/")


class DeleteScenarioGroupOut(ApiModel):
    scenario_group_id: int
    deleted: bool
    source: str = "agent_soft_delete_proxy"
    raw_response: JsonObject = Field(default_factory=dict)


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
