"""flow 내부(비 API) 도메인 schema.

노드 간 전달용 중간 산출물과 외부에서 읽어온 원천 데이터를 정의한다.
API 응답 shape은 schemas/api/ 에 둔다.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class ExistingEventOperation(StrEnum):
    """existing_event 분기에서 기존 이벤트를 새 이벤트로 바꾸는 방식.

    MERGE 는 기존 이벤트 n개를 하나로 합치고, MODIFY 는 기존 이벤트 1개의
    수치·조건(기간, 규모, 가격 등)만 바꾼다.
    """

    MERGE = "merge"
    MODIFY = "modify"


class ClaimType(StrEnum):
    """이벤트 claim·시나리오 전제가 어디서 왔는지."""

    USER_ASSUMPTION = "USER_ASSUMPTION"  # 사용자 요청이 직접 가정한 사건·조건
    EVIDENCED_FACT = "EVIDENCED_FACT"  # 근거로 확인된 사실
    MODEL_INFERENCE = "MODEL_INFERENCE"  # 근거·요청에 없는데 모델이 추론·가정한 내용


class SupportStatus(StrEnum):
    """claim·전제가 수집한 근거에 의해 지지되는 정도."""

    SUPPORTED = "SUPPORTED"  # 근거가 직접 지지
    PARTIAL = "PARTIAL"  # 일부(방향·주체)만 지지, 수치·시점 등은 근거 없음
    UNSUPPORTED = "UNSUPPORTED"  # 관련 근거 없음
    CONTRADICTED = "CONTRADICTED"  # 근거와 정면 충돌


class InferencePlausibility(StrEnum):
    """MODEL_INFERENCE claim 의 경제적·물리적 타당성(직접 인용 근거 유무와는 별개)."""

    PLAUSIBLE = "PLAUSIBLE"  # 표준적인 시장 전달 경로·물리 제약에 비추어 타당
    WEAK = "WEAK"  # 성립은 가능하나 인과가 약하거나 크기·방향이 과장됨
    CONTRADICTED = "CONTRADICTED"  # 근거 사실이나 물리·계약 제약과 모순


class EvidenceRelation(StrEnum):
    """근거 1건이 claim·전제에 대해 맡는 역할."""

    SUPPORTS_OCCURRENCE = "SUPPORTS_OCCURRENCE"  # 사건·상태가 발생/존재함을 지지
    SUPPORTS_IMPACT = "SUPPORTS_IMPACT"  # 사건의 영향·파급 경로를 지지
    BACKGROUND = "BACKGROUND"  # 배경 정보일 뿐 claim 자체를 지지하지 않음
    CONTRADICTS = "CONTRADICTS"  # claim 과 충돌


class EvidenceLink(BaseModel):
    """claim·전제와 근거 1건의 관계."""

    evidence_key: str = Field(description="근거 키(예: T1-W1)")
    relation: EvidenceRelation = Field(description="이 근거가 claim 에 대해 맡는 역할")


class ReasoningFix(StrEnum):
    """claim 사이 추론 연결 문제를 재작성에서 고치는 방향. 재작성이 설명을 덧붙이지 않도록 삭제·완화만 둔다."""

    REMOVE = "REMOVE"  # 결론을 뒷받침하지 못하는 연결(claim·본문 서술)을 삭제
    QUALIFY = "QUALIFY"  # 연결은 두되 조건부·가정 표시로 단정 수준을 낮춤


class ReasoningIssue(BaseModel):
    """검증기가 찾은 claim 사이 추론 연결 문제 1건."""

    claim_ids: list[str] = Field(default_factory=list, description="연결이 성립하지 않는 claim ID(예: C3, C5)")
    message: str = Field(description="어떤 연결이 왜 결론을 뒷받침하지 못하는지")
    fix: ReasoningFix = Field(
        default=ReasoningFix.QUALIFY,
        description="REMOVE=그 연결을 삭제, QUALIFY=조건부·가정 표시로 단정 수준을 낮춤",
    )


class FeasibilityStatus(StrEnum):
    """시나리오가 수집한 근거와 모순 없이 성립하는지."""

    CONSISTENT = "CONSISTENT"  # 근거와 충돌하는 claim 없음
    CONFLICTS_WITH_EVIDENCE = "CONFLICTS_WITH_EVIDENCE"  # 근거와 충돌하는 claim 이 있음
    UNVERIFIED = "UNVERIFIED"  # 검증 단계가 실패해 판정하지 못함


class EventClaim(BaseModel):
    """이벤트 본문을 이루는 주장 1건과 그 출처·근거 판정.

    claim_type 마다 판정 기준이 다르다.
    - EVIDENCED_FACT: support(근거가 직접 지지하는지)
    - MODEL_INFERENCE: plausibility(경제적·물리적으로 타당한지). 직접 인용 근거는 요구하지 않는다.
    - USER_ASSUMPTION: hard_conflict(근거 사실·물리·계약 제약과 명백히 양립 불가한지). 근거 없음은 정상이다.
    """

    claim_id: str = Field(description="초안 안에서 claim 을 식별하는 키(예: C1)")
    text: str = Field(description="본문에 쓴 주장(사건·상태·수치·가격 방향)")
    claim_type: ClaimType
    support: SupportStatus | None = Field(default=None, description="검증기의 근거 지지 판정(None=미검증)")
    plausibility: InferencePlausibility | None = Field(default=None, description="MODEL_INFERENCE 타당성 판정")
    hard_conflict: bool = Field(default=False, description="USER_ASSUMPTION 이 근거·물리·계약 제약과 명백히 모순인지")
    evidence: list[EvidenceLink] = Field(default_factory=list)
    fact_ids: list[str] = Field(default_factory=list, description="참조한 근거 사실 ID(예: T1-F2)")
    temporal_ok: bool = Field(default=True, description="이벤트 발생 시점에 claim 이 시점상 성립하는지")
    reason: str = Field(default="", description="판정 이유")


class DraftEvidenceUsage(BaseModel):
    """초안이 참고한 근거 1건과 그 근거를 어디에 썼는지(저장하지 않는 설명용 값)."""

    evidence_key: str = Field(description="프롬프트에 넣은 근거 키(예: W1, E3)")
    referenced_content: str = Field(default="", description="이 근거에서 가져온 사실·수치·주장")
    usage: str = Field(default="", description="이 근거를 초안의 어느 부분에 어떻게 반영했는지")


class EventDraft(BaseModel):
    """LLM이 생성한 이벤트 초안 1건(확정 전 상태)."""

    one_line_summary: str = ""
    # tmm_mi_mievent_m.search_text(검색용 요약)에만 저장하고 API 응답에는 넣지 않는다. 비면 one_line_summary 로 대신한다.
    search_text: str = ""
    detail_analysis: str = ""
    key_bullets: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    occurred_at: str = ""
    # existing_event 분기(병합·수치 수정)에서만 채워진다. 다른 분기에서는 None / 빈 목록이다.
    operation: ExistingEventOperation | None = Field(default=None, description="기존 이벤트 편집 방식")
    source_mi_event_ids: list[int] = Field(default_factory=list, description="병합·수정의 원본 기존 이벤트 ID")
    # 아래 두 필드는 응답으로만 보여주고 DB에는 저장하지 않는다.
    generation_rationale: str = Field(default="", description="이 이벤트를 이렇게 구성한 이유")
    evidence_usages: list[DraftEvidenceUsage] = Field(default_factory=list)
    # 생성 LLM 의 자기 판정이다. 최종 판정은 validate_claims 의 EventValidation 이 정한다.
    claims: list[EventClaim] = Field(default_factory=list, description="생성 LLM 이 밝힌 본문 claim 목록")


class EventTypeCatalogItem(BaseModel):
    """event type 분류 시 LLM 이 고를 수 있는 후보 1건(tmm_mi_event_type_l2_m 활성 행)."""

    event_type_l2_id: int = Field(description="event_type_l2_id. tmm_mi_mievent_m.event_type_l2_id 에 저장할 값")
    code: str = Field(default="", description="level_2_code")
    label: str = Field(default="", description="level_2_label(L2 한글명)")


class EventTypeAssignment(BaseModel):
    """이벤트 초안에 대한 event type L2 분류 결과."""

    event_type_l2_id: int | None = None
    rationale: str = ""


class IssueSeverity(StrEnum):
    WARNING = "warning"
    ERROR = "error"


class ValidationIssue(BaseModel):
    """검증 단계에서 발견한 이슈 1건. error 가 하나라도 있으면 그 초안은 저장하지 않는다."""

    severity: IssueSeverity = IssueSeverity.WARNING
    code: str = Field(description="이슈 유형 코드(예: CONTRADICTS_EVIDENCE)")
    message: str = ""
    claim_id: str = Field(default="", description="이슈가 걸린 claim(없으면 빈 문자열)")
    fixable: bool = Field(default=False, description="초안 재작성으로 고칠 수 있는 이슈인지")


class EventValidation(BaseModel):
    """초안 1건의 최종 검증 결과(validate_claims 산출물, DB 미저장)."""

    feasibility_status: FeasibilityStatus = FeasibilityStatus.UNVERIFIED
    claims: list[EventClaim] = Field(default_factory=list, description="검증기가 다시 판정한 claim 목록")
    issues: list[ValidationIssue] = Field(default_factory=list)

    @property
    def blocked(self) -> bool:
        """Error 이슈가 하나라도 있으면 저장하지 않는다."""
        return any(issue.severity is IssueSeverity.ERROR for issue in self.issues)
