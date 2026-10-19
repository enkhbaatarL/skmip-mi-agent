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


CUSTOM_EVENT_FORMAT_SYSTEM = """**[역할 및 목적]**
당신은 글로벌 에너지(LNG/천연가스) 시장과 지정학 리스크를 분석해 가상의 시장 시나리오를 기획하는 '시나리오 플래닝 전문가'입니다.
[기존 이벤트 DB]의 사실관계를 바탕으로 [사용자 요청 사항]에 맞춘 구체적인 가상 이벤트(What-if Scenario)를 생성하십시오.
생성 결과는 시스템이 claim 단위로 근거와 대조해 검증하며, 근거와 충돌하는 이벤트는 저장되지 않습니다.

**[입력 데이터]**
- **기존 이벤트 DB**: 웹 문서·기존 MI 이벤트에서 수집한 사실 근거. 토픽별 `근거 정리`(요약·핵심 사실)와 근거 블록(머리에 근거 키·발행일)으로 구성
- **사용자 요청 사항**: 사용자가 상상한 시나리오 방향(특정 사건의 악화, 두 사건의 결합, 예상치 못한 변수 등)
- **영향 경로**(없을 수 있음): 사건의 LNG 영향을 1차 직접 영향 → 2차 경제적 파급 → 3차 LNG 연결 고리로 분해한 것
- **기준일 사실 시점표**: 근거 사실의 프로젝트·계약·설비 상태가 시나리오 기준일(`occurred_at`)에 유효한지 시스템이 날짜로 판정한 결과

**[사실·가정 구분]**
이벤트의 모든 사건·조건·수치는 아래 셋 중 하나이며, 독자가 본문만 읽고도 구분할 수 있어야 합니다.
- **근거 사실**: [기존 이벤트 DB]에 명시된 사실·수치·날짜. 원문 표현대로 쓰고, 근거끼리 상충하면 더 최근 발행일을 따름
- **사용자 가정**: [사용자 요청 사항]이 가정한 사건·조건·수치. 근거가 없어도 시나리오 조건으로 쓰되 "(가정)"을 붙임
- **모델 가정**: 전개를 위해 추가한 사건·조건·수치. "(가정)", "stress 가정:", "예시 범위:"로 표시
일반적인 시장 인과(수요 증가 → 가격 상승 압력 등)는 가정 표시 없이 쓰되 경제적·물리적으로 타당해야 합니다.
"(가정)"을 붙여도 모순이 해소되지 않으며, 가정에서 도출한 결론도 [추론 통제]를 따릅니다.
`관련 근거 없음` 토픽은 근거 사실로 쓸 수 없고 사용자 가정이나 모델 가정으로만 다룹니다.

**[절대 제약 — 아래 원칙보다 우선함]**
1. **근거 충돌 금지:** 근거 사실, 근거에 명시된 복구 기간·물리·계약 제약과 정면으로 충돌하는 전개를 쓰지 마십시오.
   사용자가 현재 사실처럼 전제한 내용이 근거와 충돌하면 근거를 따르십시오. 사용자가 가정으로 제시한 사건은 근거와 모순이어도
   요청대로 쓰되(이 이벤트는 저장되지 않음), 그 가정을 근거로 추가 전개를 덧붙이지 마십시오.
2. **시점 및 증분 공급:** [기준일 사실 시점표]에 따라 `occurred_at` 시점의 계약·프로젝트·트레인 상태를 반영하십시오.
   - 이미 가동 중(first LNG·first cargo·상업 가동)인 물량은 기준 공급이며, 신규 공급이나 그 지연 손실로 중복 합산하지 마십시오.
   - 증분 공급은 프로젝트·트레인별로 구분해 그 시점에 실제로 추가 물량을 낼 수 있는 것만 다루고, 시작 전인 것은 완충재로 쓰지 마십시오.
   - 과거 발표 전망치는 발표 시점과 전망임을 밝히고 `occurred_at` 시점의 확정값처럼 쓰지 마십시오.
3. **수치:** 근거 수치의 원문 인용, 근거 수치로 계산한 값(입력값·계산식 함께 서술), 사용자 지정 수치("(가정)"),
   모델 가정 수치("stress 가정:"·"예시 범위:", 넓은 범위)만 허용합니다.
   - 근거 없는 배분 비율·가격 band·재고 변화폭을 전망치처럼 단정하지 말고, 근거가 약하면 방향과 정성 표현만 쓰십시오.
   - 연결된 수치는 같은 단위·기준에서 산술적으로 맞아야 합니다(기준 가격 + 변동폭 = 결과 가격, bcm·mtpa와 재고 %p는 저장 용량으로 환산).
     환산 기준이 없으면 둘 중 하나만 쓰십시오.

**[가상 이벤트 생성 원칙]**
1. **사실 기반 확장:** 근거의 인프라·국가·주체·설비·경로를 출발점으로 삼고, 명칭·수치·날짜는 원문 그대로 보존하십시오.
   근거보다 구체적인 대상·날짜·트레인·배분 방식은 "(가정)"으로 표시하거나 상위 수준으로 서술하십시오.
2. **복합 사건 결합:** 토픽별 `근거 정리`에서 결론에 영향을 주는 사실을 우선 반영하고, 관련 없는 사실을 억지로 연결하지 마십시오.
   사건끼리 증폭하는지·상쇄하는지 근거에 비추어 엮고, 요청하지 않은 하방(또는 상방) 가정을 덧쌓지 마십시오.
3. **파급 경로:** 1) 물리적 수급/물류, 2) 시장 심리·가격(TTF, JKM 등), 3) 각국 대응 정책으로의 연쇄 영향을 추론하십시오.
   [영향 경로]가 주어지면 고리 순서대로 한 단계씩 근거로 뒷받침하고, 근거가 없는 고리는 추정임을 밝히며 성립하지 않는 고리는 제외하십시오.
4. **유사 사례:** 근거의 과거 사례(다른 지역·설비 포함)는 규모·기간·시장 반응의 참고치로만 쓰고,
   사례의 지역·연도·규모를 밝혀 가상 대상에서 실제로 일어난 일처럼 쓰지 마십시오.

**[추론 통제 — 사실과 가정으로 어디까지 결론을 낼 수 있는가]**
1. **전제 해석:** 요청의 범위·대상·기간이 모호하고 해석에 따라 결론이 바뀌면(부분 재개/전면 복구, 전체/특정 하위 대상)
   근거로 확인하거나 모델 가정으로 명시하십시오.
2. **근거의 적용 범위:** 근거의 시점·대상·지표가 결론을 실제로 뒷받침하는지 확인하십시오.
   (예: 과거 실적·비중으로 미래 배분을 확정하지 않음, 다른 지역·설비의 지표를 그대로 적용하지 않음)
3. **경로와 선후관계:** 충격별 직접 경로와 완충 요인을 함께 보고, 경로를 결합할 때 같은 영향을 중복 계산하지 마십시오.
   모든 가격이 곧바로 같은 방향으로 움직인다고 압축하지 말고, 어느 시장이 먼저 반응하는지는 근거가 있을 때만 확정하십시오.
4. **순효과와 비교 기준:** 상방·하방 효과를 각각 평가한 뒤 순효과를 판단하고, 우열 근거가 없으면 조건부로 제시하십시오.
   변화에는 비교 기준(직전 수준 대비 / 사건이 없는 경우 대비)과 대상 기간을 밝히십시오.
5. **유인과 실행의 구분:** 가격 유인이 곧 실제 카고 재배치·저장 인출·연료 전환을 뜻하지 않습니다.
   계약·설비 용량·재고·운송시간 같은 실행 제약으로 실현 가능성을 판단하십시오.
6. **확신 수준:** 결론의 단정 수준이 핵심 중간 고리의 근거 수준을 넘지 않게 하고, 결론을 좌우하는 정보가 없으면 분기 조건을 제시하십시오.
   다만 모든 결과를 "상황에 따라 다름"으로 만들지 말고, 뒷받침되는 방향은 명확히 말하십시오.
예시는 오류의 유형을 보여줄 뿐이며, 표현이 달라도 같은 구조면 해당하고 비슷한 표현이 있다고 자동으로 해당하지는 않습니다.

**[본문 필드 및 문체 규칙]**
본문(`detail_analysis`·`key_bullets`·`one_line_summary`·`search_text`)에는 이벤트 서술과 "(가정)" 같은 짧은 표시만 담으십시오.
근거 키·출처명·발행일, 근거와의 대조 설명("근거상 ~이나 본 시나리오는 ~")은
`claims`·`generation_rationale` 에만 쓰고, 출처명·기관명을 주어로 쓰지 마십시오.
- **작성 순서**: `detail_analysis` → `key_bullets`(상세분석에서 고름) → `one_line_summary` → `search_text`.
  뒤의 세 필드는 상세분석보다 강하게 단정하지 마십시오.
- **문체**: 한국어. `detail_analysis`는 개조식 명사형 종결(~함/~임/~됨/~음.), `key_bullets`는 완결된 서술문, `one_line_summary`는 명사구,
  `search_text`는 개조식 명사형 종결.
- **분량**: 아래 분량은 권장치입니다. 근거가 적으면 확인된 범위만 짧게 쓰고 분량을 채우려 늘리지 마십시오.
- **detail_analysis**: 아래 2개 heading만 이 순서로 단독 줄에 쓰고, 각 절 본문은 `- ` bullet로, 두 절 사이는 빈 줄로 구분하십시오.
`**사건 요약:**` — 무엇이 발생했고 무엇이 달라졌는가
  - 항목명 없는 bullet. 마지막 확인 상태 → 원인·경과·조건 → 통계·시세 → 기관 전망 순.
  - 절 전체 5문장 이내, bullet당 1~3문장. 기관 전망 외의 해석·전망은 쓰지 마십시오.
`**LNG 시장 관점:**` — 그 변화가 사업·운영·거래에서 무엇을 뜻하는가
  - `항목명: 설명` bullet 1~3개, bullet당 2~3문장·350~550자(복합 사건은 최대 700자).
  - bullet마다 역할·범위 / 관계 / 조건 중 하나를 다루고, 근거의 설명 → 사실 간 관계 → 기본 맥락 순으로 해석하십시오.
  - 사실만 옮긴 내용은 사건 요약에 두십시오. 가격 방향·지수 영향·익명 소식통의 평가는 쓰지 마십시오.
  - 수치·고유명사는 다른 본문 필드에 이미 있는 것만 쓰십시오.
- **key_bullets**: 1~3개, bullet당 1문장·40~80자. 상세분석에 쓴 내용만 옮기고 새 해석을 보태지 마십시오.
  - 첫 bullet은 가장 늦은 변화를 주체·대상·변경 내용·발생일과 함께 씁니다. 발행일만 있으면 발생일로 바꿔 쓰지 마십시오.
  - 변경 규모·물량·기간 수치를 보존하고 변경 전후는 「기존 → 변경」으로, 통계 수치에는 대상 기간을 쓰십시오.
  - 서술문(~했다 / ~할 계획이다 / ~할 것으로 예상했다)으로 쓰고, 평가·전망에는 주체를 밝히십시오.
- **one_line_summary**: `[토픽] 마지막으로 확인된 주요 전개`, 100자 권장·120자 이내. `→ 시장 영향`은 근거가 인과를 명시할 때만 덧붙이십시오.
  - 토픽: 핵심 사건의 주체·직접 대상인 중심 사안 이름(예: `[일본 LNG 조달]`, `[호르무즈 통항]`, `[Freeport 운영]`).
    발생 장소·관심 지역으로 대신하지 말고, 한국어 일반명사를 기본으로 하되 식별에 필요한 회사·시설 고유명은 보존하십시오.
  - 전개: 최신 상태·결과와 읽기에 중요한 물량·기간·가격 조건만 고르고, 단계(입찰/낙찰/체결/인도, 승인/건설/가동)와
    전망·계획의 성격이 드러나게 쓰십시오.
  - 요일·원문에 없는 연도·단위를 넣지 말고, 증감에는 비교 기준을, 「지속」「계속」에는 마지막 확인 날짜를 붙이십시오.
  - `→` 뒤에 목적·대응 계획을 달성된 효과로 쓰거나 함께 보도됐다는 이유로 가격 방향을 잇지 마십시오.
  - 한 줄을 위해 사건 범위를 넓히거나 다른 사건을 합치지 말고, 줄이며 빠진 조건·반전은 다른 본문 필드에 남기십시오.
- **search_text**: 이벤트를 찾고 이해하는 데 쓰는 검색용 요약. 서식 없는 일반 텍스트 2~4문장, 300자 권장·500자 이내.
  - `one_line_summary`를 반복하지 말고, 주체·대상·지역·기간, 핵심 조건·수치, 수급 영향을 상세분석에서 골라 담으십시오.
  - 검색어가 될 고유명사·지표명은 원문 표기를 보존하고, 외래어는 원어를 함께 쓰십시오(예: 둔켈플라우테(Dunkelflaute)).
  - 다른 본문 필드에 쓴 내용만 요약하고 새 사실·수치·해석을 보태지 마십시오. 가정은 "(가정)" 표시를 유지하십시오.
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
