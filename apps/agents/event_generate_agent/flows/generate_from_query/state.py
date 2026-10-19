"""generate_from_query flow LangGraph state."""

from __future__ import annotations

import operator
from typing import Annotated

from pydantic import BaseModel, Field

from apps.agents.event_generate_agent.constants import DEFAULT_LANGUAGE
from apps.agents.event_generate_agent.flows.generate_from_query.api_schema import (
    GenerateFromQueryResult,
)
from apps.agents.event_generate_agent.flows.generate_from_query.schema import (
    BranchError,
    EvidenceItem,
    FactTimeline,
    QueryPlan,
    SearchRoute,
    SearchTopic,
    TopicBrief,
)
from apps.agents.event_generate_agent.schemas.domain import (
    EventDraft,
    EventTypeAssignment,
    EventValidation,
)


class GenerateFromQueryState(BaseModel):
    # --- input ---
    user_query: str = ""
    date_from: str = ""
    date_to: str = ""
    language: str = DEFAULT_LANGUAGE
    user_id: str | None = None

    # --- classify_route / plan_search ---
    # route: classify_route 가 고른 1차 검색 분기(폴백해도 바뀌지 않는다. 폴백 분기는 fallback_route)
    route: SearchRoute = SearchRoute.WEB
    route_reason: str = ""
    query_plan: QueryPlan | None = None

    # --- 토픽 단위 폴백 제어 ---
    # summarize_topics 가 관련 근거를 못 찾은 토픽만 반대 분기로 1회 재검색한다.
    # pending_fallback 동안 검색 노드는 fallback_topic_keys 의 토픽만 검색해 기존 결과 뒤에 덧붙인다.
    fallback_used: bool = False
    pending_fallback: bool = False
    fallback_route: SearchRoute | None = None
    fallback_topic_keys: list[str] = Field(default_factory=list)

    # --- 공통 뒷단 ---
    # 검색 노드가 토픽별 근거를 바로 덧붙인다(both 분기는 두 검색 노드가 병렬로 쓰므로 누적 reducer).
    evidences: Annotated[list[EvidenceItem], operator.add] = Field(default_factory=list)
    topic_briefs: list[TopicBrief] = Field(default_factory=list)
    # build_fact_timeline 이 시나리오 기준일로 만들고, validate_claims 가 초안 발생 시점 기준으로 다시 계산해 덮어쓴다.
    fact_timeline: FactTimeline | None = None
    # 한 요청은 이벤트 초안 1건을 만든다(생성 실패 시 None).
    draft: EventDraft | None = None
    # validate_claims: 초안의 최종 검증 결과. error 가 있으면 저장하지 않는다.
    validation: EventValidation | None = None
    # 고칠 수 있는 error 가 나오면 draft_events 를 다시 실행한다(MAX_DRAFT_REVISIONS 회까지).
    revision_count: int = 0
    pending_revision: bool = False
    type_assignment: EventTypeAssignment | None = None

    # 분기 실패는 flow를 중단시키지 않고 여기 쌓아 meta.warnings로 노출한다.
    branch_errors: Annotated[list[BranchError], operator.add] = Field(default_factory=list)
    warnings: Annotated[list[str], operator.add] = Field(default_factory=list)

    # --- persist ---
    # persist_events 가 저장에 성공했을 때만 채워진다.
    saved_event_id: int | None = None

    # --- output ---
    result: GenerateFromQueryResult | None = None

    def topics_to_search(self) -> list[SearchTopic]:
        """이번 검색 패스가 다룰 토픽. 폴백 중이면 재검색 대상 토픽만, 아니면 전체 토픽."""
        topics = self.query_plan.topics if self.query_plan else []
        if self.pending_fallback:
            return [topic for topic in topics if topic.topic_key in self.fallback_topic_keys]
        return list(topics)
