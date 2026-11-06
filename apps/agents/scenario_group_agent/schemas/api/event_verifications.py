from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import ConfigDict, Field, field_validator

from apps.agents.scenario_group_agent.schemas.base import ApiModel


VerificationAspect = Literal["entity", "location", "time", "quantity", "freshness", "attribution"]
VerificationVerdict = Literal["matched", "caution", "contradicted", "outdated", "unverified", "not_applicable"]
VerificationCautionReason = Literal["as_of_limitation", "source_conflict", "insufficient_evidence", "other"]
VerificationReason = Literal[
    "verified",
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


class EventVerificationsOut(ApiModel):
    checked_at: datetime
    items: list[EventVerificationItem]
