"""generate_from_query flow 내부(비 API) 도메인 schema.

사용자 입력 문장 → 검색 계획(QueryPlan, 토픽 목록) → 토픽별·분기별 검색 결과(WebDocument /
ExistingEventHit, 검색 노드 내부에서만 씀) → 공통 근거(EvidenceItem) → 토픽별 근거 정리(TopicBrief) 로 이어지는 타입을 정의한다.

핵심은 `EvidenceItem` 이다. 분기별 결과를 이 타입으로 정규화하고 나면
뒷단(초안 생성 → 타입 분류 → 리뷰 → finalize)은 근거의 출처를 알 필요가 없다.
모든 검색 결과와 근거는 `topic_key` 로 자기가 속한 토픽을 들고 다니며, 토픽끼리 섞지 않는다.
API 응답 shape은 api_schema.py 에 둔다.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class SearchRoute(StrEnum):
    """classify_route 가 고르는 근거 수집 분기.

    BOTH 는 두 분기를 병렬로 함께 실행한다(웹 최신 사실관계 + 기존 이벤트 기준 사례를
    모두 근거로 써야 하는 경우).
    """

    WEB = "web"
    EXISTING_EVENT = "existing_event"
    BOTH = "both"


class EvidenceOrigin(StrEnum):
    """근거 1건의 출처."""

    WEB = "web"
    EXISTING_EVENT = "existing_event"


class SearchTopic(BaseModel):
    """요청이 다루는 사건·주제 1개와 그 주제만을 찾기 위한 검색 질의.

    병합·결합 요청("독일 한파 + 북해 풍력 둔화")은 주제마다 토픽이 하나씩 생기고,
    검색·근거 정리는 토픽 단위로 따로 이뤄진다.
    """

    topic_key: str = Field(description="요청 안에서만 쓰는 토픽 식별자(예: T1, T2)")
    label: str = Field(default="", description="사람이 읽는 토픽 이름(예: 독일 한파)")
    event_keyword: str = Field(default="", description="기존 이벤트 LIKE 검색용 핵심어 1개")
    web_queries: list[str] = Field(default_factory=list, description="이 토픽만 찾는 웹 검색 질의 목록")


class QueryPlan(BaseModel):
    """사용자 입력 문장을 검색 가능한 형태로 정규화한 계획."""

    topics: list[SearchTopic] = Field(default_factory=list, description="토픽별 검색 질의(단일 주제면 1개)")
    impact_chain: list[str] = Field(
        default_factory=list,
        description="사건 가정형 요청의 사건 → LNG 영향 경로 고리(초안 생성 시 추론 순서로 사용)",
    )
    date_from: str = Field(default="", description="조회 시작일(YYYY-MM-DD)")
    date_to: str = Field(default="", description="조회 종료일(YYYY-MM-DD)")
    scenario_date: str = Field(
        default="", description="가정된 사건이 일어나는 시나리오 기준일(YYYY-MM-DD). 없으면 빈 값"
    )


class WebDocument(BaseModel):
    """웹 검색으로 수집한 문서 1건."""

    url: str = ""
    title: str = ""
    content: str = ""
    published_at: str = ""
    source_name: str = Field(default="", description="매체/도메인명")
    score: float = 0.0
    provider: str = Field(default="", description="검색 provider 식별자")
    topic_key: str = Field(default="", description="이 문서를 찾은 토픽")


class ExistingEventHit(BaseModel):
    """기존 DB 이벤트 검색 결과 1건."""

    mi_event_id: int
    one_line_summary: str = ""
    detail_analysis: str = ""
    key_bullets: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    occurred_at: str = ""
    event_type_l2_id: int | None = None
    event_type_l2_name: str = ""
    topic_key: str = Field(default="", description="이 이벤트를 찾은 토픽(같은 이벤트가 여러 토픽에 걸릴 수 있음)")


class EvidenceItem(BaseModel):
    """출처와 무관하게 뒷단 생성 파이프라인이 소비하는 공통 근거 1건."""

    evidence_key: str = Field(description="프롬프트에서 근거를 참조할 짧은 키(예: T1-W1, T2-E3)")
    origin: EvidenceOrigin
    topic_key: str = Field(default="", description="이 근거가 속한 토픽")
    title: str = ""
    content: str = ""
    published_at: str = ""
    source_name: str = ""
    url: str = ""
    provider: str = Field(default="", description="web 근거를 찾은 검색 provider. existing_event면 빈 값")
    ref_id: int | None = Field(
        default=None,
        description="existing_event면 mi_event_id",
    )


class FactKind(StrEnum):
    """근거 사실이 실적인지, 계획·전망인지."""

    ACTUAL = "ACTUAL"  # 이미 일어난 실적·발생 사실
    STATUS = "STATUS"  # 기준 시점의 상태(가동 중, 중단 중 등)
    PLAN = "PLAN"  # 예정·계획(가동 개시 예정, 계약 개시 예정 등)
    FORECAST = "FORECAST"  # 기관·매체의 전망치


class AssetStatus(StrEnum):
    """프로젝트·설비·계약의 기준 시점 상태(해당 없으면 NOT_APPLICABLE)."""

    OPERATING = "OPERATING"  # 가동 중(first LNG·first cargo·상업 가동 포함)
    RAMP_UP = "RAMP_UP"  # 가동 개시 후 증산 중
    UNDER_CONSTRUCTION = "UNDER_CONSTRUCTION"
    PLANNED = "PLANNED"  # 개시 예정(미가동)
    OUTAGE = "OUTAGE"  # 손상·정비 등으로 중단
    NOT_APPLICABLE = "NOT_APPLICABLE"


class EvidencedFact(BaseModel):
    """근거에서 확인된 사실 1건(시점·상태 메타 포함)."""

    fact_id: str = Field(description="요청 안에서만 쓰는 사실 키(예: T1-F2)")
    topic_key: str = ""
    statement: str = Field(description="사실 서술(수치·날짜·주체 보존)")
    evidence_keys: list[str] = Field(default_factory=list, description="이 사실의 출처 근거 키")
    fact_kind: FactKind = FactKind.ACTUAL
    entity: str = Field(default="", description="사실의 주체(프로젝트·설비·국가·기관명)")
    asset_status: AssetStatus = AssetStatus.NOT_APPLICABLE
    as_of: str = Field(default="", description="사실의 기준 시점(YYYY / YYYY-MM / YYYY-MM-DD)")
    valid_from: str = Field(default="", description="상태·계약·가동이 시작되는(된) 시점")
    valid_to: str = Field(default="", description="상태·계약이 끝나는 시점, 복구 완료 예상 시점 등")


class TopicBrief(BaseModel):
    """토픽 1개에 대해 수집한 근거를 정리한 결과(summarize_topics 산출물).

    초안 생성은 원본 근거 목록이 아니라 토픽별 정리 결과와 그 토픽의 관련 근거만 본다.
    """

    topic_key: str
    label: str = ""
    found: bool = Field(default=False, description="토픽과 직접 관련된 근거를 찾았는지")
    summary: str = Field(default="", description="관련 근거로 정리한 토픽의 현재 상황 요약")
    facts: list[EvidencedFact] = Field(default_factory=list, description="근거에서 확인된 핵심 사실(시점·상태 포함)")
    evidence_keys: list[str] = Field(default_factory=list, description="토픽과 직접 관련된 근거 키(관련도 순)")
    missing_reason: str = Field(default="", description="found=False 일 때 근거가 부족한 이유")
    searched_routes: list[SearchRoute] = Field(default_factory=list, description="이 토픽을 검색한 분기(폴백 포함)")


class TopicEvidenceGroup(BaseModel):
    """초안 프롬프트에 넣을 토픽 1개 묶음(정리 결과 + 실제로 넣을 관련 근거)."""

    brief: TopicBrief
    evidences: list[EvidenceItem] = Field(default_factory=list)


class TemporalStatus(StrEnum):
    """근거 사실의 상태가 시나리오 기준일에 유효한지(코드가 날짜 비교로 판정)."""

    ACTIVE = "ACTIVE"  # 기준일에 이미 시작됐고 끝나지 않음
    NOT_YET = "NOT_YET"  # 기준일 이후에 시작(가동·개시 전)
    ENDED = "ENDED"  # 기준일 전에 종료
    UNCERTAIN = "UNCERTAIN"  # 시작·종료 시점이 기준일과 같은 기간에 걸쳐 판정 불가
    STALE = "STALE"  # 과거 시점에 관측된 일시적 상태(중단·상황)로, 종료 시점이 없어 기준일까지 지속되는지 알 수 없음
    PAST_EVENT = "PAST_EVENT"  # 기준일 전에 일어난 일회성 사건·실적(과거 사례). 기준일의 현재 상태가 아님
    UNKNOWN = "UNKNOWN"  # 시점 정보 없음


class FactTimelineEntry(BaseModel):
    """근거 사실 1건의 기준일 시점 상태."""

    fact_id: str
    entity: str = ""
    asset_status: AssetStatus = AssetStatus.NOT_APPLICABLE
    status: TemporalStatus = TemporalStatus.UNKNOWN
    reason: str = ""


class FactTimeline(BaseModel):
    """근거 사실의 시나리오 기준일 시점표(코드가 날짜 비교로 계산, LLM 없음)."""

    target_date: str = Field(default="", description="시나리오 기준일(YYYY-MM-DD)")
    entries: list[FactTimelineEntry] = Field(default_factory=list)


class BranchError(BaseModel):
    """분기 실행 중 발생했으나 flow를 중단시키지 않은 오류."""

    stage: str = Field(description="오류가 난 노드/단계 이름")
    message: str = ""
