from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import ConfigDict, Field, field_validator

from apps.agents.scenario_group_agent.schemas.base import ApiModel


VerificationAspect = Literal["entity", "location", "time", "quantity", "freshness", "attribution"]
VerificationVerdict = Literal["matched", "caution", "contradicted", "outdated", "unverified", "not_applicable"]
VerificationCautionReason = Literal["as_of_limitation", "source_conflict", "insufficient_evidence", "other"]
VerificationReason = Literal[
    "verified",
    "no_contradiction",
    "review_required",
    "contradicted",
    "outdated",
    "no_evidence",
    "search_error",
    "verification_error",
]


class EventVerificationsIn(ApiModel):
    model_config = ConfigDict(extra="forbid")
    mi_event_ids: list[Annotated[int, Field(strict=True, gt=0)]] = Field(min_length=1, max_length=5)
    actor_usr_logn_id: str = Field(strict=True, min_length=1, max_length=100)

    @field_validator("actor_usr_logn_id")
    @classmethod
    def nonempty_actor(cls, value: str) -> str:
        if not value.strip():
            message = "actorUsrLognId는 공백일 수 없습니다."
            raise ValueError(message)
        return value.strip()

    @field_validator("mi_event_ids")
    @classmethod
    def unique_ids(cls, value: list[int]) -> list[int]:
        if len(value) != len(set(value)):
            message = "miEventIds에는 중복 ID를 넣을 수 없습니다."
            raise ValueError(message)
        return value


class EventVerificationCheck(ApiModel):
    aspect: VerificationAspect
    verdict: VerificationVerdict
    event_claim: str
    finding: str
    source_urls: list[str]
    caution_reason: VerificationCautionReason | None = None
    qualification_quote: str | None = None


class EventVerificationItem(ApiModel):
    mi_event_id: int
    title: str
    source_updated_at: datetime | None
    status: Literal["pass", "warning", "fail"]
    reason_code: VerificationReason
    review: str
    links: list[str]
    checks: list[EventVerificationCheck]
    verification_id: UUID | None = None
    expires_at: datetime | None = None


class EventVerificationsOut(ApiModel):
    checked_at: datetime
    items: list[EventVerificationItem]
