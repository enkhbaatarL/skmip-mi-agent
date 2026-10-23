"""이벤트 초안 생성 프롬프트 및 structured output schema.

사용자 요청 문장과 토픽별로 정리한 근거(TopicEvidenceGroup)를 묶어 하나의 '이벤트'
(한줄요약/상세분석/key bullets)로 정규화한다.
프롬프트 빌더는 순수 함수(I/O 없음)로 유지한다.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from apps.agents.event_generate_agent.constants import DEFAULT_LANGUAGE, MAX_DRAFT_CLAIMS, MAX_EVENT_DRAFTS
from apps.agents.event_generate_agent.flows.generate_from_query.schema import (
    EvidenceItem,
    EvidenceOrigin,
    FactTimeline,
    TopicEvidenceGroup,
)
from apps.agents.event_generate_agent.prompts.validation_context import (
    format_claims,
    format_fact,
    format_timeline,
)
from apps.agents.event_generate_agent.schemas.domain import (
    ClaimType,
    EventDraft,
    EvidenceLink,
    IssueSeverity,
    ValidationIssue,
)


class EvidenceRefLLMItem(BaseModel):
    evidence_key: str = Field(description="참고한 근거 블록 머리의 키(예: T1-W1, T2-E3). 입력에 없는 키는 쓰지 말 것")
    evidence_title: str = Field(default="", description="참고한 근거의 제목(입력의 '제목:' 값을 그대로)")
    referenced_content: str = Field(
        default="",
        description="이 근거에서 실제로 가져온 핵심 사실·수치(원문 표현 기준 1문장, 80자 이내)",
    )
    usage: str = Field(default="", description="이 근거를 반영한 위치와 역할(짧은 구, 40자 이내)")


class DraftClaimLLMItem(BaseModel):
    claim_id: str = Field(description="이벤트 안에서 claim 을 식별하는 키(C1, C2, ...)")
    text: str = Field(
        description="본문(한 줄 요약·bullet·상세분석)에 쓴 주장 1건. 사건·상태·수치·가격 방향 단위로 쪼갤 것",
    )
    claim_type: ClaimType = Field(
        description="USER_ASSUMPTION=사용자 요청이 가정한 내용, EVIDENCED_FACT=근거로 확인된 사실, MODEL_INFERENCE=당신이 추론·가정한 내용",
    )
    evidence: list[EvidenceLink] = Field(default_factory=list, description="이 claim 과 관계된 근거와 그 역할")
    fact_ids: list[str] = Field(default_factory=list, description="참조한 근거 사실 ID(예: T1-F2). 입력에 없는 ID 금지")


class EventDraftLLMItem(BaseModel):
    # structured output 은 스키마 필드 순서대로 생성되므로, 분석을 먼저 쓰고 그 안에서 핵심요약을 고른 뒤
    # 한 줄 요약을 쓰도록
    # 상세분석 → bullet → 한 줄 요약 순으로 둔다.
    detail_analysis: str = Field(
        description="상세 분석(가장 먼저 작성). 사건 요약 → LNG 시장 관점 2개 절, 각 절은 bullet"
    )
    key_bullets: list[str] = Field(
        default_factory=list,
        description="핵심요약 1~3개. 상세 분석에 쓴 사실·설명만 골라 bullet당 1문장 서술문으로",
    )
    one_line_summary: str = Field(
        description="이벤트 한 줄 요약(제목 역할). `[토픽] 주요 전개` 형식의 명사구, 100~110자 이내. 상세 분석의 단정 수준을 넘지 말 것"
    )
    search_text: str = Field(
        default="",
        description="검색용 요약(서식 없는 일반 텍스트 2~4문장, 500자 이내). 한 줄 요약을 반복하지 말고 본문 내용만 요약할 것",
    )
    tags: list[str] = Field(default_factory=list)
    occurred_at: str = Field(default="", description="이벤트 발생 시점(YYYY-MM-DD)")
    generation_rationale: str = Field(default="", description="사용자 요청과 근거로부터 이 이벤트를 구성한 이유")
    evidence_refs: list[EvidenceRefLLMItem] = Field(default_factory=list, description="참고한 근거 목록")
    claims: list[DraftClaimLLMItem] = Field(
        default_factory=list,
        description=f"본문에서 결론을 좌우하는 핵심 주장 목록(검증 대상, 최대 {MAX_DRAFT_CLAIMS}개)",
    )


class EventDraftLLMOutput(BaseModel):
    events: list[EventDraftLLMItem] = Field(default_factory=list)


CUSTOM_EVENT_FORMAT_SYSTEM = """# [역할 및 목적]
당신은 글로벌 에너지(LNG/천연가스) 시장과 지정학 리스크를 분석해 가상의 시장 시나리오를 기획하는 '시나리오 플래닝 전문가'입니다.
[기존 이벤트 DB]의 사실관계를 바탕으로 [사용자 요청 사항]에 맞춘 구체적인 가상 이벤트(What-if Scenario)를 생성하십시오.
생성 결과는 시스템이 claim 단위로 근거와 대조해 검증하며, 근거와 충돌하는 이벤트는 저장되지 않습니다.

# [입력]
- 기존 이벤트 DB: 기존 MI 이벤트에서 수집한 사실 근거. 토픽별 근거 요약과 근거 블록(근거 키·발행일 포함)
- 사용자 요청 사항: 사용자가 가정할 사건·조건·수치와 분석 범위(특정 사건의 악화, 두 사건의 결합, 예상치 못한 변수 등)
- 영향 경로(선택): 직접 영향 → 경제적 파급 → LNG 연결 고리로 분해
- 기준일 사실 시점표: 근거 사실의 occurred_at 시점의 프로젝트·계약·설비 상태가 유효한지 날짜로 판정

# [작성 원칙]
## 1. 사실과 가정
- 근거 사실: DB에 명시된 사실·수치·날짜만 사용하며 의미와 적용 범위를 보존(원문 표현대로 작성, 근거끼리 상충 시 더 최근 발행일을 따름)
- 사용자 가정: 사용자가 가정한 사건·조건·수치에 근거가 없어도 시나리오 조건으로 쓰되 "(가정)"을 붙입니다.
- 모델 가정: 전개에 필요한 최소한의 추가 조건에 "(가정)"을 붙입니다.
- "관련 근거 없음" 토픽은 사실로 서술하지 않습니다.
- 가정 표시는 해당 내용 가까이에 붙이고, 요약 필드에서도 유지
- 추론: 사실과 가정에서 도출한 영향은 "~할 수 있음" 등 조건부 표현으로 작성합니다.
- 요청 범위 밖의 독립적인 상방·하방 사건을 추가하지 않습니다. 근거에 확인된 완충 요인과 제약은 반영합니다.

## 2. 근거와 시점
- 시점:
    - [기준일 사실 시점표]로 `occurred_at` 시점의 계약·프로젝트·트레인 상태를 반영
    - 이미 가동 중인 물량은 기준 공급으로 처리하며 신규 공급이나 지연 손실로 중복 계산하지 않습니다.
    - 과거 전망은 발표 시점과 전망이라는 성격을 밝힙니다.
- 근거 상충 금지:
    - 근거가 상충하면 대상·적용 시점이 같은지 확인한 뒤 최신 근거를 우선합니다. 해소되지 않는 충돌은 단정하지 않습니다.
    - 사용자가 사실로 제시한 전제가 근거와 충돌하면 근거에 맞게 수정하고 generation_rationale에 설명합니다.
    - 사용자가 명시적으로 가정한 사건은 가정으로 유지하되, 근거의 물리·계약·복구 제약을 무시한 추가 전개는 만들지 않습니다.
- 근거보다 구체적인 대상·날짜·트레인·배분 방식을 추가하면 모델 가정으로 표시하거나 상위 수준으로 작성합니다.
- 아직 공급을 시작하지 않은 물량은 해당 시점의 완충 공급으로 사용하지 않습니다.
- 다른 지역·설비·시기의 지표를 그대로 적용하지 않습니다. 유사 사례는 지역·연도·규모를 밝힌 참고치로만 사용합니다.

## 3. 수치
- 근거 원문 수치
- 근거 수치로 계산한 값: claims에 입력값과 계산식을 기록
- 사용자 혹은 모델이 가정한 수치: "(사용자 가정)" 혹은 "(가정·예시 stress 범위)" 또는 "(가정·예시 범위)"로 표시한 넓은 범위
- 근거 없는 배분 비율·가격 범위·재고 변화폭은 기본적으로 정성적으로 설명
- 과거 실적이나 비중으로 미래 배분을 확정하지 않습니다.

## 4. 영향 분석
- 물리적 수급·물류 → LNG 가격(TTF·JKM 등) → 정책 대응 순으로 필요한 경로만 분석
- 영향 경로가 주어지면 고리별 근거와 성립 조건을 확인합니다. 근거가 부족한 고리는 추정으로 표시하고 성립하지 않는 고리는 제외
- 부분 재개와 전면 복구 등 해석에 따라 결론이 달라지는 조건은 근거로 확인하거나 가정으로 명시합니다.
- 직접 영향과 완충 요인, 상방과 하방 효과를 함께 검토하되 같은 영향을 중복 계산하지 않습니다.
- 가격 유인만으로 카고 재배치·저장 인출·연료 전환을 확정하지 않습니다. 계약·용량·재고·운송시간을 고려합니다.
- 가격 영향에는 비교 기준(직전 수준 대비 / 사건이 없는 경우 대비)과 대상 기간을 명시합니다.
- 순효과의 우열이 불분명하면 조건별로 나누어 설명합니다.
- 결론은 핵심 중간 고리의 근거 수준보다 강하게 단정하지 않습니다.

# [본문 필드 및 작성 규칙]
- 본문은 다음 필드로 구성
    - (detail_analysis, key_bullets, one_line_summary, search_text)
## 공통
- 작성 순서: detail_analysis → key_bullets(상세분석에서 고름) → one_line_summary → search_text 
- 요약 과정에서 새로운 사실·수치·가정·인과를 추가하거나 조건을 누락하지 않습니다.
- 근거가 부족하면 짧게 작성합니다. 분량을 채우기 위해 내용을 만들지 않습니다.
- 본문에는 이벤트와 시장 영향을 작성합니다. 근거 키·출처 표기·근거 대조 설명은 claims와 generation_rationale에만 기록합니다.
- 과거 전망의 발표 시점은 시점 구분에 필요한 경우 본문에 작성
- 기관·회사는 사건의 행위자 또는 전망의 주체일 때만 본문에 명시

- ## detail_analysis: 상세 분석 
  - [구성]: 사건 요약 + LNG 시장 관점 (둘 다 필수)
  
  - 사건 요약: — 무엇이 발생했고 무엇이 달라졌는가
    - 항목명 없는 bullet
    - 순서: 마지막 확인 상태 → 원인·경과·조건 → 통계·시세 → 기관 전망
    - 절 전체 5문장 이내, bullet당 1~3문장
    - 독립 사고·별도 거래·주체가
    
  - LNG 시장 관점: — 그 변화가 사업·운영·거래에서 무엇을 뜻하는가
    - "항목명: 설명" 형식의 bullet 1~3개, bullet당 1~3문장, 350~550자 (복합 사건은 최대 700자).
    - bullet마다 역할·범위 / 관계 / 조건 중 하나를 다룰 것
    - 수급·물류 변화, 가격 영향, 완충 요인·실행 제약 중 결론에 필요한 내용을 작성
    - 영향의 원인과 성립 조건을 연결해 설명하고 사건 요약을 반복하지 않습니다.
    
  - 작성 규칙:
    - 출처: 불릿 끝에 코드가 붙임 (LLM은 본문에 출처를 쓰지 않음)
        - 뉴스: (Reuters, 2026-09-03 보도) / 리포트: (…, 발행) / 기관 발표: (CERA, … 발표)
        - 같은 매체 여러 건: (Platts 3건, 2026-09-01~09-04 보도)
        - Web·사용자 제공 출처도 매체명·발행일로 표기
    - 문체: 개조식 명사형 종결(~함/~임/~됨/~음.)
    - 줄바꿈: 출처를 뺀 본문이 100자를 넘으면 같은 불릿 안에서 문장 단위로 나눔
  
  
- ## key_bullets: 1~3개 bullet의 핵심 요약, '누구의 무엇이 어떻게 바뀌었는지'와 범위·현재 상태를 파악함
  - 근거: 상세 분석 중 출처에 명시된 사실·설명만 사용. LLM이 새로 도출한 해석·인과는 넣지 않음
  - 작성규칙:
    - bullet 구성
        - bullet당 1문장(40~80자), 한 bullet에 한 메세지 
        - 첫 불릿: 가장 늦게 확인된 변화, 주체·대상·변경내용·발생일을 담음 (발행일만 있으면 발생일로 바꿔 쓰지 마십시오.)
        - 다음 불릿: 적용 범위·제약·조건·후속 일정 중 서로 다른 핵심 정보
    - 수치
        - 변경 규모·물량·기간을 보존하고, 변경 전후는 「기존 → 변경」으로 씀
        - 가정·추론의 표시와 핵심 수치·기간을 유지할 것
        - 통계·지표 수치에는 기간을 작성
    - 문체:
        - 완결된 서술문으로 작성하고 각 bullet을 굵게 표시합니다. 소제목은 쓰지 않습니다.
    - 출처:
        - 출처명·보도일은 쓰지 않음 (상세 분석 불릿 끝에 표시)
        - 전망·평가의 주체는 생략하지 않음

- ## one_line_summary: 한줄 요약
  - [토픽] 핵심 변화 또는 결과 형식
    - 토픽: 핵심 사건의 대상, 중심 사안(이슈) 이름(예: [일본 LNG 조달], [호르무즈 통항], [Freeport 운영]).
    - 최신 상태·결과와 읽기에 중요한 물량·기간·가격 조건만 고르고, 단계(입찰/낙찰/체결/인도, 승인/건설/가동)와 전망·계획의 성격이 드러나게 작성
  - 작성 규칙:
    - 시장 영향을 나타내는 (→)은 근거(출처)가 인과를 명시할 때만 붙임.
    - 주요 조건만 남기고 사건 범위를 넓히거나 다른 사건을 합치지 말고, 빠진 조건·반전은 다른 본문 필드에 남기십시오.
    - 가격·물량 증감에는 비교 기준을 유지
    - 지속 또는 계속의 경우에는 마지막 확인 날짜를 붙이십시오.
    - 원문에 없는 날짜, 단위는 작성하지 말것.
    - 한국어 일반 명사구로 작성
    - 식별에 필요한 회사·시설 고유명은 보존
    - 100자 권장, 120자 이내

- ## search_text: 이벤트를 찾고 이해하는 데 쓰는 검색용 요약
  - 작성 규칙:
    - one_line_summary의 단순 반복을 피하고 주체·대상·지역·기간·핵심 조건·수치·수급 영향을 골라 담습니다.
    - 가정은 "(가정)" 표시를 유지, 개조식 명사형 종결
    - 서식 없는 일반 텍스트 2~4문장, 300자 권장(500자 이내)
    - 검색에 필요한 고유명사·지표명은 입력의 원문 표기를 보존합니다.
    - 검색에 필요한 전문용어는 입력에 원어가 있을 때 병기합니다.
    - 다른 본문 필드에 쓴 내용만 요약하고 새로운 사실·수치·해석을 추가 금지

"""

CUSTOM_EVENT_FORMAT_USER = """
이제 아래에 제공된 [기존 이벤트 DB]와 [사용자 요청 사항]을 읽고, 위의 규칙과 포맷에 맞춰 새로운 가상 이벤트를 JSON 형태로 생성해 주세요.

**[기존 이벤트 DB]**
{existing_event}

**[사용자 요청 사항]**
{user_query}

**[영향 경로]**
{impact_chain}

**[기준일 사실 시점표]**
{timeline}
{revision}
"""


# 근거 1건의 본문 길이 상한(프롬프트 크기 가드). 초과분은 잘라내고 말줄임표를 붙인다.
_MAX_EVIDENCE_CONTENT_CHARS = 1500

_ORIGIN_LABEL = {
    EvidenceOrigin.WEB: "웹 문서",
    EvidenceOrigin.EXISTING_EVENT: "기존 MI 이벤트",
}


def _clip(text: str, limit: int = _MAX_EVIDENCE_CONTENT_CHARS) -> str:
    body = text.strip()
    return body if len(body) <= limit else f"{body[:limit]}…"


def _format_evidence(evidence: EvidenceItem) -> str:
    """근거 1건을 프롬프트에 넣을 한 블록으로 만든다.

    `evidence_key`(T1-W1/T2-E3...)를 머리에 달아 초안이 어떤 근거에서 나왔는지
    사람이 로그만으로 되짚을 수 있게 한다.
    """
    head_parts = [f"[{evidence.evidence_key}]", _ORIGIN_LABEL.get(evidence.origin, evidence.origin.value)]
    if evidence.origin is EvidenceOrigin.EXISTING_EVENT and evidence.ref_id is not None:
        head_parts.append(f"miEventId={evidence.ref_id}")
    if evidence.source_name:
        head_parts.append(evidence.source_name)
    if evidence.published_at:
        head_parts.append(evidence.published_at)
    if evidence.url:
        head_parts.append(evidence.url)

    lines = [" | ".join(head_parts)]
    if evidence.title:
        lines.append(f"제목: {evidence.title.strip()}")
    if evidence.content:
        lines.append(f"내용: {_clip(evidence.content)}")
    return "\n".join(lines)


def format_topic_groups(groups: list[TopicEvidenceGroup]) -> str:
    """토픽별 근거 정리와 관련 근거 블록을 토픽 단위 섹션으로 만든다.

    초안 LLM 이 토픽마다 무엇이 확인되었고 무엇이 비었는지 먼저 보고 토픽을 엮도록,
    정리 결과를 근거 블록보다 앞에 둔다.
    """
    if not groups:
        return "(수집된 근거가 없습니다. 사용자 요청 사항만으로 작성하십시오.)"
    sections: list[str] = []
    for group in groups:
        brief = group.brief
        lines = [f"### [{brief.topic_key}] {brief.label}"]
        if not brief.found:
            lines.append(f"근거 정리: 관련 근거 없음 — {brief.missing_reason or '검색 결과에서 관련 근거를 찾지 못함'}")
            lines.append("주의: 이 토픽은 근거 사실로 쓸 수 없음. 다루려면 본문에 (가정) 표시 필요")
            sections.append("\n".join(lines))
            continue
        if brief.summary:
            lines.append(f"근거 정리: {brief.summary}")
        if brief.facts:
            lines.append("핵심 사실(사실 ID | 유형 | 주체 | 상태 | 시점):")
            lines.extend(f"- {format_fact(fact)}" for fact in brief.facts)
        if group.evidences:
            lines.append("관련 근거:")
            lines.append(format_evidences(group.evidences))
        sections.append("\n".join(lines))
    return "\n\n".join(sections)


def format_evidences(evidences: list[EvidenceItem]) -> str:
    if not evidences:
        return "(수집된 근거가 없습니다. 사용자 요청 사항만으로 작성하십시오.)"
    return "\n\n".join(_format_evidence(evidence) for evidence in evidences)


def _format_impact_chain(impact_chain: list[str] | None) -> str:
    """분석 단계가 분해한 사건 → LNG 영향 경로를 번호 붙은 고리 목록으로 만든다."""
    steps = [step.strip() for step in impact_chain or [] if step.strip()]
    if not steps:
        return "(주어진 영향 경로가 없습니다. 사용자 요청과 근거로부터 직접 파급 효과를 추론하십시오.)"
    return "\n".join(f"{index}. {step}" for index, step in enumerate(steps, start=1))


CLAIM_OUTPUT_RULES = f"""- `claims`: 본문(한 줄 요약·bullet·상세분석)에서 결론을 좌우하는 핵심 주장만 사건·상태·수치·가격 방향 단위로
  최대 {MAX_DRAFT_CLAIMS}개 나열하십시오. 시스템이 claim 마다 근거와 대조해 근거 지지 여부·충돌·시점을 다시 판정합니다.
  - 포함: 사용자 가정(시나리오 조건), 근거 사실로 쓴 수치·상태·날짜, 결론을 좌우하는 모델 추론·가정(수급 변화, 가격 방향, 정책 대응)
  - 제외: 같은 주장의 다른 표현(한 줄 요약·bullet·상세분석에 반복된 내용은 1건으로), 결론에 영향이 없는 배경 서술
  - `claim_type`: EVIDENCED_FACT 는 근거 사실에 직접 적힌 내용일 때만 쓰십시오. 근거 사실에서 추론하거나 수치를 늘리고 줄였으면
    MODEL_INFERENCE 이고, 사용자 요청이 가정한 내용은 USER_ASSUMPTION 입니다.
    검증 기준이 다릅니다: EVIDENCED_FACT 는 근거의 직접 지지, MODEL_INFERENCE 는 경제적·물리적 타당성,
    USER_ASSUMPTION 은 근거·물리·계약 제약과의 명백한 모순 여부만 봅니다.
  - `fact_ids`, `evidence`: 입력에 있는 ID·키만 쓰십시오. `evidence.relation` 은
    SUPPORTS_OCCURRENCE(사건·상태 발생 지지) / SUPPORTS_IMPACT(영향·파급 지지) / BACKGROUND(배경일 뿐) / CONTRADICTS(충돌) 중 하나입니다.
- 출력 직전 점검: 모든 claim 이 근거와 충돌하지 않는지, 기준일에 시점상 성립하는지, 연결된 수치끼리 산술적으로 맞는지,
  [추론 통제]를 지켰는지(반대 방향 효과·실행 제약을 고려했는지, 결론이 중간 고리보다 강하지 않은지,
  한 줄 요약의 단정 수준이 상세분석과 같은지) 확인하고 어긋나면 본문과 claim 을 함께 고쳐서 출력하십시오."""


def _build_output_rules(*, today: str, language: str, max_events: int) -> str:
    """SYSTEM_PROMPT 의 본문 필드 규칙이 다루지 않는 출력 필드만 보충한다.

    structured output 스키마(EventDraftLLMOutput)에는 있으나 본문 규칙에 없는 필드를
    비워 둔 채 반환하면 뒷단(저장·중복판정)이 쓸 값이 사라지므로 여기서 채운다.
    """
    return f"""**[출력 보충 규칙]**
- 출력은 이벤트 목록을 `events` 에 담은 객체이며, 필드명은 출력 스키마를 따르십시오.
- 오늘 날짜는 {today} 입니다. 상대적 기간 표현은 이 날짜를 기준으로 해석하십시오.
- 작성 언어: {language}
- 생성할 이벤트는 최대 {max_events}건입니다. 사용자 요청이 단일 사건이면 1건만 생성하십시오.
  서로 다른 사건으로 나눌 이유가 없다면 억지로 늘리지 마십시오.
- `occurred_at`: 가상 사건이 발생하는 시점을 YYYY-MM-DD 로 채우십시오. 판단할 수 없으면 빈 문자열로 두십시오.
- `tags`: 국가/설비/지수 등 검색에 쓸 짧은 명사구 3~5개.
- `generation_rationale`: 사용자 요청의 어떤 방향을, 어떤 근거 사실과 엮어 이 가상 이벤트로 확장했는지 1문장.
  근거와 충돌하는 전개를 rationale에서 인정하는 방식으로 넘어가지 말고, 본문을 근거에 맞게 고치십시오.
{CLAIM_OUTPUT_RULES}
- `evidence_refs`: 본문·claim 에 실제로 반영한 근거만 나열하십시오(배경으로 읽기만 한 근거 제외). 없으면 빈 배열로 두십시오.
  - `evidence_key`: [기존 이벤트 DB] 블록 머리의 키(`T1-W1`, `T2-E3` 등). 입력에 없는 키를 만들지 마십시오.
  - `evidence_title`: 해당 블록의 `제목:` 값을 그대로 옮기십시오.
  - `referenced_content`: 그 근거에서 가져온 핵심 사실·수치·날짜·주체를 원문 표현 기준 1문장(80자 이내)으로 적으십시오.
    근거에 없는 내용을 적지 마십시오.
  - `usage`: 반영한 위치와 역할을 40자 이내 짧은 구로 적으십시오(예: "상세분석 — 풍력 비중 기준값")."""


def format_revision(draft: EventDraft | None, issues: list[ValidationIssue]) -> str:
    """재작성 요청 섹션: 이전 초안과 재작성으로 고칠 error 만 보여준다(재작성 패스가 아니면 빈 문자열).

    warning 과 고칠 수 없는 error(사용자 가정 자체의 모순 등)는 넘기지 않는다. 재작성이 지적과 무관한 내용을
    덧붙이며 claim 을 늘리면 검증이 길어지고 새 이슈가 생기므로, 지적된 claim 만 삭제·완화하도록 제한한다.
    """
    targets = [issue for issue in issues if issue.severity is IssueSeverity.ERROR and issue.fixable]
    if draft is None or not targets:
        return ""
    bullets = "\n".join(f"  - {bullet}" for bullet in draft.key_bullets)
    problems = "\n".join(
        f"- [{issue.code}]{f' claim={issue.claim_id}' if issue.claim_id else ''} {issue.message}" for issue in targets
    )
    return (
        "\n**[이전 초안 검증 결과 — 재작성 요청]**\n"
        "이전 초안이 아래 error 로 검증을 통과하지 못했습니다. 이전 초안을 고쳐 쓰는 것이며 새로 쓰는 것이 아닙니다.\n"
        "- 고칠 범위: error 가 지적한 claim 과 그 claim 을 담은 본문(한 줄 요약·bullet·상세분석) 문장만 고치십시오.\n"
        "  claim 이 지정되지 않은 error 는 메시지가 가리키는 본문 문장과 그에 해당하는 claim 만 고치십시오.\n"
        "- 고치는 방법: 결론을 뒷받침하지 못하는 서술은 삭제하고(수정 방향: 연결 삭제), 필요한 연결은 조건부 표현이나\n"
        '  "(가정)" 표시로 단정 수준을 낮추십시오(수정 방향: 조건부로 완화).\n'
        "  근거와 충돌하거나 시점이 맞지 않는 서술은 근거에 맞게 고치거나 삭제하십시오.\n"
        "- 금지: 새 claim·새 사건·새 유사 사례·새 근거 연결을 추가하지 마십시오.\n"
        "  설명을 덧붙여 연결을 보강하려 하지 마십시오.\n"
        f"- claim 수는 이전 초안의 {len(draft.claims)}개 이하로 유지하십시오.\n"
        "- 지적되지 않은 claim 은 claim_id 와 문구를 그대로 유지하십시오.\n\n"
        f"### 이전 초안: {draft.one_line_summary}\n"
        f"key_bullets:\n{bullets}\n"
        f"상세 분석:\n{draft.detail_analysis}\n"
        f"claims:\n{format_claims(draft.claims)}\n"
        f"고칠 error:\n{problems}"
    )


def build_messages(
    user_query: str,
    groups: list[TopicEvidenceGroup],
    *,
    today: str,
    language: str = DEFAULT_LANGUAGE,
    max_events: int = MAX_EVENT_DRAFTS,
    impact_chain: list[str] | None = None,
    fact_timeline: FactTimeline | None = None,
    revision: str = "",
) -> list[dict[str, Any]]:
    """system/user 메시지 리스트를 구성한다(I/O 없음).

    Args:
        user_query: 사용자가 입력한 요청 문장 원문.
        groups: 토픽별 근거 정리와 프롬프트에 넣을 관련 근거(상한은 group_prompt_evidences 가 적용).
        today: 상대 기간 표현 해석 기준일(YYYY-MM-DD).
        language: 생성 언어.
        max_events: 한 요청에서 생성할 이벤트 상한.
        impact_chain: 분석 단계가 분해한 사건 → LNG 영향 경로 고리. 사건 가정형이 아니면 비어 있다.
        fact_timeline: 근거 사실의 시나리오 기준일 시점표.
        revision: 재작성 패스면 format_revision 결과, 아니면 빈 문자열.

    """
    user_content = CUSTOM_EVENT_FORMAT_USER.format(
        existing_event=format_topic_groups(groups),
        user_query=user_query.strip(),
        impact_chain=_format_impact_chain(impact_chain),
        timeline=format_timeline(fact_timeline),
        revision=revision,
    )
    return [
        {"role": "system", "content": CUSTOM_EVENT_FORMAT_SYSTEM},
        {
            "role": "user",
            "content": f"{user_content}\n{_build_output_rules(today=today, language=language, max_events=max_events)}",
        },
    ]
