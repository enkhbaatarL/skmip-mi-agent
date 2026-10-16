"""generate_from_query flow 전용 API request/response schema.

응답 events[] 는 tmm_mi_mievent_m 저장 값(공용 `GeneratedEventOut`)에 편집 정보·참고 근거·저장 ID 를 덧붙인다.
검증 이슈·토픽별 사실·시점표·claim 판정 등 생성 과정 정보는 응답에 담지 않고 로그로만 남긴다.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from apps.agents.event_generate_agent.schemas.api.event import GeneratedEventOut
from apps.agents.event_generate_agent.schemas.base import ApiModel


class GenerateFromQueryIn(ApiModel):
    """사용자 입력 문장 기반 이벤트 생성 요청 body."""

    user_query: str = Field(description="이벤트를 만들고 싶은 주제를 담은 사용자 입력 문장")
    date_from: str | None = Field(default=None, description="조회 시작일(YYYY-MM-DD)")
    date_to: str | None = Field(default=None, description="조회 종료일(YYYY-MM-DD)")


class GeneratedEventEvidenceOut(ApiModel):
    """초안이 참고한 근거 1건(응답 전용, DB에 저장하지 않음)."""

    evidence_key: str = Field(description="프롬프트 근거 키(예: T1-W1, T2-E3)")
    origin: Literal["web", "existing_event"]
    title: str = ""
    source_name: str = ""
    published_at: str = ""
    url: str = ""
    provider: str = Field(default="", description="web 근거를 찾은 검색 provider. existing_event면 빈 값")
    ref_id: int | None = Field(default=None, description="existing_event면 mi_event_id")
    referenced_content: str = Field(default="", description="LLM이 밝힌, 이 근거에서 가져온 사실·수치·주장")
    usage: str = Field(default="", description="LLM이 밝힌 이 근거의 반영 위치/방식")


class GeneratedFromQueryEventOut(GeneratedEventOut):
    """생성된 이벤트 1건(tmm_mi_mievent_m 저장 값) + 기존 이벤트 편집 정보·참고 근거 + 저장 ID.

    generation_rationale / evidences 는 사용자 확인용 설명이라 공용 GeneratedEventOut
    (persistence 입력 shape)이 아닌 이 응답 schema에만 둔다.
    """

    operation: Literal["merge", "modify"] | None = Field(
        default=None,
        description="기존 이벤트 편집 방식(existing_event 분기만, 그 외 null). merge=병합, modify=수치 수정",
    )
    source_mi_event_ids: list[int] = Field(
        default_factory=list,
        description="병합·수정의 원본 기존 이벤트 ID(DB 미저장)",
    )
    generation_rationale: str = Field(default="", description="이 이벤트를 이렇게 생성한 이유(DB 미저장)")
    evidences: list[GeneratedEventEvidenceOut] = Field(
        default_factory=list,
        description="생성 시 참고한 근거 목록(DB 미저장)",
    )
    mi_event_id: int | None = Field(
        default=None,
        description="tmm_mi_mievent_m 에 저장된 이벤트 ID(저장되지 않았으면 null)",
    )


class GenerateFromQueryMetaOut(ApiModel):
    """생성 결과 메타(어느 분기를 왜 탔는지, 저장 결과, 처리 경고)."""

    route: Literal["web", "existing_event", "both"] = Field(
        default="web",
        description="classify_route가 처음 고른 분기(both면 두 검색을 병렬 실행)",
    )
    route_reason: str = Field(default="", description="route 선택 근거")
    persisted_count: int = Field(default=0, description="tmm_mi_mievent_m 에 실제 저장된 이벤트 수")
    warnings: list[str] = Field(
        default_factory=list,
        description="검색 실패·분류 실패·저장 여부 등 처리 경고. 검증 이슈 내용은 로그에만 남는다",
    )


class GenerateFromQueryResult(ApiModel):
    """생성 결과 본문."""

    meta: GenerateFromQueryMetaOut
    events: list[GeneratedFromQueryEventOut] = Field(default_factory=list)


class GenerateFromQueryOut(ApiModel):
    """응답 envelope."""

    status: Literal["success", "error"] = "success"
    message: str = ""
    data: GenerateFromQueryResult | None = None
