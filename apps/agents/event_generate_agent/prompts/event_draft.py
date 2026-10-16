"""이벤트 초안 생성 프롬프트 및 structured output schema.

사용자 요청 문장과 토픽별로 정리한 근거(TopicEvidenceGroup)를 묶어 하나의 '이벤트'
(한줄요약/상세분석/key bullets)로 정규화한다.
프롬프트 빌더는 순수 함수(I/O 없음)로 유지한다.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from apps.agents.event_generate_agent.constants import DEFAULT_LANGUAGE, MAX_EVENT_DRAFTS
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
    ScenarioSeverity,
    ValidationIssue,
)


class EvidenceRefLLMItem(BaseModel):
    evidence_key: str = Field(description="참고한 근거 블록 머리의 키(예: T1-W1, T2-E3). 입력에 없는 키는 쓰지 말 것")
    evidence_title: str = Field(default="", description="참고한 근거의 제목(입력의 '제목:' 값을 그대로)")
    referenced_content: str = Field(
        default="",
        description="이 근거에서 실제로 가져온 사실·수치·주장(원문 표현 기준 1~2문장)",
    )
    usage: str = Field(default="", description="이 근거를 이벤트의 어느 부분에 어떻게 반영했는지 한 문장")


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
    shock_cluster: str = Field(
        default="",
        description="이 claim 이 시나리오의 충격 동인(악재·호재 사건)이면 독립 충격 묶음 이름. 충격이 아니면 빈 문자열",
    )


class EventDraftLLMItem(BaseModel):
    # structured output 은 스키마 필드 순서대로 생성되므로, 분석을 먼저 쓰고 그 단정 수준에 맞춰 한 줄 요약을 쓰도록
    # 상세분석 → bullet → 한 줄 요약 순으로 둔다.
    detail_analysis: str = Field(description="상세 분석(가장 먼저 작성)")
    key_bullets: list[str] = Field(default_factory=list, description="핵심 포인트 목록")
    one_line_summary: str = Field(
        description="이벤트 한 줄 요약(제목 역할, 서식 없는 일반 텍스트 한 문장). 상세 분석의 단정 수준을 넘지 말 것"
    )
    tags: list[str] = Field(default_factory=list)
    occurred_at: str = Field(default="", description="이벤트 발생 시점(YYYY-MM-DD)")
    generation_rationale: str = Field(default="", description="사용자 요청과 근거로부터 이 이벤트를 구성한 이유")
    evidence_refs: list[EvidenceRefLLMItem] = Field(default_factory=list, description="참고한 근거 목록")
    claims: list[DraftClaimLLMItem] = Field(default_factory=list, description="본문을 이루는 주장 목록(검증 대상)")
    scenario_severity: ScenarioSeverity = Field(
        default=ScenarioSeverity.BASE,
        description="시나리오 강도. BASE | PLAUSIBLE_STRESS | SEVERE_STRESS | TAIL_RISK",
    )


class EventDraftLLMOutput(BaseModel):
    events: list[EventDraftLLMItem] = Field(default_factory=list)


CUSTOM_EVENT_FORMAT_SYSTEM = """**[역할 및 목적]**
당신은 글로벌 에너지(LNG/천연가스) 시장과 지정학 리스크를 분석해 가상의 시장 시나리오를 기획하는 '시나리오 플래닝 전문가'입니다.
[기존 이벤트 DB]의 사실관계를 바탕으로 [사용자 요청 사항]에 맞춘 구체적인 가상 이벤트(What-if Scenario)를 생성하십시오.
생성 결과는 시스템이 claim 단위로 근거와 대조해 검증하며, 근거와 충돌하는 이벤트는 저장되지 않습니다.

**[입력 데이터]**
- **기존 이벤트 DB**: 웹 문서·기존 MI 이벤트에서 수집한 사실 근거. 사용자 요청의 토픽(사건·주제)별로 `근거 정리`(요약·핵심 사실)와
  관련 근거 블록이 있으며, 각 근거 블록 머리에 근거 키와 발행일이 있습니다.
- **사용자 요청 사항**: 특정 사건의 악화, 두 사건의 결합, 예상치 못한 변수 등 사용자가 상상한 시나리오 방향
- **영향 경로**(없을 수 있음): 사건의 LNG 영향을 1차 직접 영향 → 2차 경제적 파급 → 3차 LNG 연결 고리로 분해한 것
- **기준일 사실 시점표**: 근거 사실의 프로젝트·계약·설비 상태가 시나리오 기준일(`occurred_at`)에 유효한지 시스템이 날짜로 판정한 결과

**[사실·가정 구분]**
이벤트의 모든 사건·조건·수치는 아래 셋 중 하나이며, 독자가 본문만 읽고도 구분할 수 있어야 합니다.
- **근거 사실**: [기존 이벤트 DB]에 명시된 사실·수치·날짜. 원문 표현대로 사실로 서술. 근거끼리 상충하면 더 최근 발행일의 근거를 따름
- **사용자 가정**: [사용자 요청 사항]이 가정한 사건·조건·수치. 근거가 없어도 시나리오 조건으로 쓰되 "(가정)"을 붙임
- **모델 가정**: 근거에도 사용자 요청에도 없지만 전개를 위해 추가한 사건·조건·수치. "(가정)", "stress 가정:", "예시 범위:"로 표시
일반적인 시장 인과(수요 증가 → 가격 상승 압력 등) 추론은 가정 표시 대상이 아니며, 경제적·물리적으로 타당하기만 하면 됩니다.
가정 표시와 추론의 타당성은 별개입니다. "(가정)"을 붙여도 물리적 모순이 해소되지 않고, 그 가정에서 도출한 결론도 [추론 통제]를 따라야 합니다.
`관련 근거 없음`으로 표시된 토픽은 근거 사실로 쓸 수 없고, 사용자 요청에 있으면 사용자 가정으로, 없으면 모델 가정으로만 다룹니다.

**[절대 제약 — 아래 원칙보다 우선함]**
1. **근거 충돌 금지:** 근거 사실, 근거에 명시된 복구 기간·물리·계약 제약과 정면으로 충돌하는 전개를 쓰지 마십시오.
   - 사용자가 현재 사실처럼 전제한 내용이 근거 사실과 충돌하면 근거 사실을 따르십시오.
   - 예외: 사용자가 가정으로 제시한 사건·조건은 근거와 모순이어도 요청대로 쓰십시오(이 이벤트는 저장되지 않음).
     단, 그 모순된 가정을 근거로 추가 전개를 덧붙이지 마십시오.
2. **시점 및 증분 공급:** [기준일 사실 시점표]에 따라 `occurred_at` 시점의 계약·프로젝트·트레인 상태를 반영하십시오.
   - 이미 가동 중(first LNG·first cargo·상업 가동)인 물량은 기준 공급입니다. 아직 공급 전인 것처럼 쓰거나, 그 지연을 신규 공급 손실로 중복 합산하지 마십시오.
   - 신규 프로젝트를 하나의 완충재로 묶지 말고 프로젝트·트레인별로 구분해, 그 시점에 실제로 추가 물량을 낼 수 있는 것만 증분 공급으로 다루십시오.
     "아직 시작 전"인 프로젝트·계약은 공급 완충재로 쓰지 마십시오.
   - 과거에 발표된 전망치는 발표 시점과 전망임을 밝히고, `occurred_at` 시점의 확정값처럼 쓰지 마십시오.
3. **수치:** 다음만 허용합니다.
   - 근거 수치의 원문 인용 / 근거 수치로 계산한 값(입력값과 계산식을 함께 서술) / 사용자가 지정한 수치("(가정)" 표시) /
     모델 가정 수치("stress 가정:", "예시 범위:" 표시, 정밀한 점 추정 대신 넓은 범위)
   - 근거 없는 배분 비율·가격 band·재고 변화폭을 전망치처럼 단정하지 마십시오. 근거가 약하면 방향과 정성 표현만 쓰십시오.
   - 연결된 수치는 같은 단위·기준에서 산술적으로 맞아야 합니다(기준 가격 + 변동폭 = 결과 가격, 물량(bcm·mtpa)과 재고 %p는
     저장 용량 등 같은 기준으로 환산). 환산 기준이 없으면 둘 중 하나만 쓰십시오.

**[가상 이벤트 생성 원칙]**
1. **사실 기반 확장:** 근거에 있는 인프라·국가·주체·설비·경로를 출발점으로 삼고, 명칭·수치·날짜는 원문 그대로 보존하십시오.
   근거가 뒷받침하는 수준까지만 구체화하십시오. 근거보다 구체적인 대상·날짜·트레인·배분 방식은 "(가정)"으로 표시하거나 상위 수준으로 서술하십시오.
2. **복합 사건 결합:** 토픽이 여러 개이면 토픽별 `근거 정리`에서 결론에 영향을 주는 사실을 우선 반영하고, 결론과 직접 관련 없는 사실을 억지로 연결하지 마십시오.
   사건끼리 증폭하는지·상쇄(완충)하는지 근거에 비추어 엮으십시오.
   사용자 요청이 요구하지 않은 하방(또는 상방) 가정을 덧쌓지 마십시오.
3. **파급 경로:** 사건이 1) 물리적 수급/물류, 2) 시장 심리·가격(TTF, JKM 등), 3) 각국 대응 정책에 미치는 연쇄 영향을 추론하십시오.
   [영향 경로]가 주어지면 한 번에 결론 내리지 말고 고리 순서대로 한 단계씩 추론하며 각 고리를 근거로 뒷받침하십시오.
   근거가 없는 고리는 추정임을 밝히고, 근거에 비추어 성립하지 않는 고리는 제외하십시오.
4. **유사 사례:** 근거에 비슷한 과거 사례(다른 지역·설비 포함)가 있으면 규모·지속 기간·시장 반응의 참고치로 쓰되,
   사례의 지역·연도·규모·기간을 밝혀 가상 대상에서 실제로 일어난 일처럼 쓰지 마십시오.

**[추론 통제 — 사실과 가정으로 어디까지 결론을 낼 수 있는가]**
개별 사실의 정확한 인용과 별개로, 그 사실과 가정에서 도출하는 결론의 범위를 아래 원칙으로 통제하십시오.
1. **전제 해석:** 사용자가 고정한 조건과 아직 정해지지 않은 조건을 구분하십시오. 요청의 범위·대상·기간이 모호하고 그 해석에 따라
   결론이 바뀌면(예: 부분 재개인지 전면 복구인지, 변화가 전체에 미치는지 특정 하위 대상에만 미치는지) 근거로 확인하거나 모델 가정으로 명시하십시오.
2. **근거의 적용 범위:** 근거의 시점·대상·지표·적용 범위가 해당 결론을 실제로 뒷받침하는지 확인하십시오.
   (예: 과거 실적·비중으로 미래 배분·전망을 확정하지 않음, 다른 지역·설비의 지표를 대상에 그대로 적용하지 않음)
3. **경로와 선후관계:** 충격별 직접 경로와 이를 제한·완충하는 요인을 함께 확인하고, 경로를 결합할 때 같은 영향을 중복 계산하지 마십시오.
   충격이 모든 가격을 곧바로 같은 방향으로 움직인다고 압축하지 말고, 어느 시장이 먼저 반응하는지는 근거가 있을 때만 확정하십시오.
   복합 충격에서는 동시 반응·역순 반응도 가능합니다.
4. **순효과와 비교 기준:** 상방·하방 효과를 각각 평가한 뒤 순효과를 판단하고, 우열을 판단할 근거가 없으면 순효과를 조건부로 제시하십시오.
   가격·수요·공급 변화는 비교 기준(직전 수준 대비 / 사건이 없는 경우 대비)과 대상 기간을 밝히십시오.
5. **유인과 실행의 구분:** 가격 유인이 곧 실제 이동·인출을 뜻하지 않습니다. 카고 재배치·저장 인출·연료 전환은 계약·설비 용량·재고·운송시간 같은
   실행 제약을 거쳐 실현 가능성을 판단하십시오.
6. **확신 수준:** 최종 결론의 단정 수준이 핵심 중간 고리의 근거 수준을 넘지 않게 하십시오. 결론을 좌우하는 정보가 없으면 가장 중요한 분기 조건을 제시하십시오.
7. **명확성 유지:** 모든 결과를 "상황에 따라 다름"으로 만들지 마십시오. 방향이 충분히 뒷받침되는 부분은 명확히 말하고,
   배분·순서·규모처럼 추가 조건이 필요한 부분만 조건부로 제한하십시오.
예시는 오류의 유형을 보여주기 위한 것입니다. 표현이 달라도 같은 구조면 해당하고, 예시와 비슷한 표현이 있다고 자동으로 해당하지는 않습니다.

**[시나리오 강도와 충격 묶음]**
- 강도는 "근거와 충돌하는가"가 아니라 "얼마나 일어나기 어려운가"입니다. 근거와 충돌하는 내용을 TAIL_RISK 로 표시해 넘어가지 마십시오.
- 충격 묶음: 근거로 아직 확인되지 않은 충격(악재·호재 사건)을 원인이 같은 것끼리 묶은 단위입니다.
  (예: 북서유럽 한파 + Dunkelflaute 는 "북서유럽 기상" 한 묶음, "호르무즈 통항 차질"은 원인이 달라 별도 묶음)
- BASE: 확인되지 않은 충격 묶음 없음(근거상 현재 경로의 연장)
- PLAUSIBLE_STRESS: 독립 충격 묶음 1~2개
- SEVERE_STRESS: 독립 충격 묶음 3개 이상이 동시에 발생
- TAIL_RISK: 근거상 가능성이 매우 낮은 조합이나 극단값
시스템은 claim 의 충격 묶음 수로 최소 강도를 다시 계산하므로, 묶음을 실제보다 적게 잡지 마십시오.

**[본문과 검증 정보의 분리]**
본문(한 줄 요약·bullet·상세분석)에는 이벤트 서술과 "(가정)", "stress 가정:" 같은 짧은 표시만 담으십시오.
근거 키·출처, 근거와의 대조 설명("근거상 ~이나 본 시나리오는 ~"), 강도·충격 묶음 설명은 본문에 쓰지 말고
`claims`, `scenario_severity`, `generation_rationale` 에만 담으십시오. 근거와의 차이는 시스템이 검증 결과로 따로 보여줍니다.

**[본문 필드 및 문체 규칙]**
- 한국어로 작성하고, 본문 서술 문장은 개조식 명사형 종결어미(~함, ~임, ~됨, ~음)만 사용하십시오.
- **one_line_summary**: [토픽] 최근 에피소드 → 시장 영향/방향 (100자이내)
  - 핵심 사건과 직접 시장 영향만 요약하고 출처명·기관명·리포트명을 주어로 사용하지 마십시오.
  - `→`는 확인 가능한 인과 또는 영향 관계를 압축하는 경우에만 사용하십시오.
- **key_bullets**: 3~5개. 전체 항목 안에 아래 세 관점이 각각 1개 이상 포함되도록 하고, 중복 정보는 통합하십시오.
  - **(A) 사건의 최근 상태·업데이트** — 날짜, 주체, 발생 사실
  - **(B) Fundamental 영향** — 실물 수급·설비·물동량
  - **(C) 가격 방향** — 어느 지수(TTF, JKM, spread)가 어느 방향으로 움직이는지
- **작성 순서**: `detail_analysis`로 분석을 먼저 정리한 뒤 `key_bullets`, `one_line_summary`를 쓰십시오.
  상세분석에서 확인한 조건·완충 효과·불확실성을 한 줄 요약·bullet에도 같은 단정 수준으로 반영하고, 분석보다 강하게 단정하지 마십시오.
- **detail_analysis**: 가상 사건과 그 시장 영향을 풀어쓴 설명입니다. 확인된 LNG 수급·가격·운송 영향 경로, 시장 반응과 시사점을 통합하십시오.
  반드시 다음 2개 heading만 아래 순서로 사용하십시오.
`**사건 요약:**`
- 사건 이해에 필요한 핵심 원인과 직접 전달 경로는 포함하되 해석·전망은 쓰지 마십시오.
`**LNG 시장 관점:**`
- heading은 단독 줄에 쓰고 Bullet Point를 붙이지 마십시오.
- 각 heading 아래 본문은 Bullet Point 없는 하나의 문단으로 작성하십시오.
- 두 문단 사이는 줄바꿈 2번(`\n\n`)으로 구분하십시오.
- 중간 근거 없이 수급·물류·가격 방향으로 확대하지 마십시오.
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
근거 사실의 프로젝트·계약·설비 상태가 시나리오 기준일에 유효한지 시스템이 날짜로 판정한 결과입니다.
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


CLAIM_OUTPUT_RULES = """- `claims`: 본문(한 줄 요약·bullet·상세분석)의 주장을 사건·상태·수치·가격 방향 단위로 빠짐없이 쪼개 나열하십시오.
  시스템이 claim 마다 근거와 대조해 근거 지지 여부·충돌·시점을 다시 판정합니다.
  - `claim_type`: EVIDENCED_FACT 는 근거 사실에 직접 적힌 내용일 때만 쓰십시오. 근거 사실에서 추론하거나 수치를 늘리고 줄였으면
    MODEL_INFERENCE 이고, 사용자 요청이 가정한 내용은 USER_ASSUMPTION 입니다.
    검증 기준이 다릅니다: EVIDENCED_FACT 는 근거의 직접 지지, MODEL_INFERENCE 는 경제적·물리적 타당성,
    USER_ASSUMPTION 은 근거·물리·계약 제약과의 명백한 모순 여부만 봅니다.
  - `fact_ids`, `evidence`: 입력에 있는 ID·키만 쓰십시오. `evidence.relation` 은
    SUPPORTS_OCCURRENCE(사건·상태 발생 지지) / SUPPORTS_IMPACT(영향·파급 지지) / BACKGROUND(배경일 뿐) / CONTRADICTS(충돌) 중 하나입니다.
  - `shock_cluster`: 근거로 아직 확인되지 않은 충격 claim 에만 독립 충격 묶음 이름을 붙이십시오.
- `scenario_severity`: [시나리오 강도와 충격 묶음] 기준으로 고르십시오.
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
- `generation_rationale`: 사용자 요청의 어떤 방향을, 어떤 근거 사실과 엮어 이 가상 이벤트로 확장했는지 2~3문장.
  근거와 충돌하는 전개를 rationale에서 인정하는 방식으로 넘어가지 말고, 본문을 근거에 맞게 고치십시오.
{CLAIM_OUTPUT_RULES}
- `evidence_refs`: 실제로 참고한 근거만 나열하십시오. 참고한 근거가 없으면 빈 배열로 두십시오.
  - `evidence_key`: [기존 이벤트 DB] 블록 머리의 키(`T1-W1`, `T2-E3` 등). 입력에 없는 키를 만들지 마십시오.
  - `evidence_title`: 해당 블록의 `제목:` 값을 그대로 옮기십시오.
  - `referenced_content`: 그 근거에서 가져온 구체적 사실·수치·날짜·주체를 원문 표현 기준 1~2문장으로 적으십시오.
    근거에 없는 내용을 적지 마십시오.
  - `usage`: 그 내용을 이벤트의 어느 부분(한 줄 요약/bullet/상세분석)에 어떻게 반영했는지 한 문장으로 적으십시오."""


def format_revision(draft: EventDraft | None, issues: list[ValidationIssue]) -> str:
    """재작성 요청 섹션: 이전 초안과 검증에서 걸린 이슈를 보여준다(재작성 패스가 아니면 빈 문자열)."""
    if draft is None or not issues:
        return ""
    bullets = "\n".join(f"  - {bullet}" for bullet in draft.key_bullets)
    problems = "\n".join(
        f"- [{issue.severity.value}/{issue.code}]{f' {issue.claim_id}' if issue.claim_id else ''} {issue.message}"
        for issue in issues
    )
    return (
        "\n**[이전 초안 검증 결과 — 재작성 요청]**\n"
        "이전 초안이 아래 이슈로 검증을 통과하지 못했습니다. 이슈가 걸린 claim 과 본문 서술을 근거에 맞게 고치거나 빼고,\n"
        "이슈가 없는 부분은 유지해 이벤트를 다시 작성하십시오. 사용자 가정 자체가 근거와 충돌하는 이슈는 고칠 필요가 없습니다.\n\n"
        f"### 이전 초안: {draft.one_line_summary}\n"
        f"key_bullets:\n{bullets}\n"
        f"상세 분석:\n{draft.detail_analysis}\n"
        f"claims:\n{format_claims(draft.claims)}\n"
        f"검증 이슈:\n{problems}"
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
