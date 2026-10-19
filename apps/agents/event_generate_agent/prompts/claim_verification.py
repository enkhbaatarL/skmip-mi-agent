"""생성 이벤트 claim 검증 프롬프트 및 structured output schema (validate_claims 노드, 생성 후 검증).

생성 LLM 이 스스로 붙인 claim 표시를 믿지 않고, claim 마다 claim_type 별 기준으로 다시 판정한다.
근거 사실은 직접 지지 여부, 모델 추론은 경제적·물리적 타당성, 사용자 가정은 명백한 모순 여부만 본다. 본문에 있는데 claim 목록에서 빠진 주장 중 문제가 있는 것,
연결된 수치 간 산술 불일치, 가정인데 본문에서 가정 표시가 없는 서술, claim 사이의 추론 연결이 성립하지 않는 곳도 함께 찾는다.
판정 결과를 저장 차단 여부로 바꾸는 규칙은 코드(tools/claim_rules.py)가 정한다.
프롬프트 빌더는 순수 함수(I/O 없음)로 유지한다.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from apps.agents.event_generate_agent.flows.generate_from_query.schema import FactTimeline, TopicEvidenceGroup
from apps.agents.event_generate_agent.prompts.event_draft import format_topic_groups
from apps.agents.event_generate_agent.prompts.validation_context import (
    format_claims,
    format_timeline,
)
from apps.agents.event_generate_agent.schemas.domain import (
    ClaimType,
    EventDraft,
    EvidenceLink,
    InferencePlausibility,
    ReasoningIssue,
    SupportStatus,
)


class ClaimVerdictLLMItem(BaseModel):
    claim_id: str = Field(description="[검증할 claim] 의 claim ID")
    support: SupportStatus = Field(description="근거가 claim 을 직접 지지하는 정도(모든 claim_type 공통, 참고 정보)")
    plausibility: InferencePlausibility | None = Field(
        default=None,
        description="MODEL_INFERENCE 만: PLAUSIBLE | WEAK | CONTRADICTED. 다른 claim_type 은 null",
    )
    hard_conflict: bool = Field(
        default=False,
        description="USER_ASSUMPTION 만: 근거 사실·물리·계약 제약과 명백히 양립 불가하면 true. 다른 claim_type 은 false",
    )
    evidence: list[EvidenceLink] = Field(default_factory=list, description="판정에 쓴 근거와 그 역할")
    temporal_ok: bool = Field(description="기준일 시점에 claim 이 시점상 성립하면 true")
    reason: str = Field(
        default="",
        description=(
            "문제가 있는 판정(SUPPORTED·PLAUSIBLE 이 아님, hard_conflict=true, temporal_ok=false)만 이유 한 문장"
            "(충돌·시점 불일치면 근거 사실 ID를 밝힐 것). 문제가 없으면 빈 문자열"
        ),
    )


class UntrackedClaimLLMItem(BaseModel):
    text: str = Field(description="본문에 있으나 [검증할 claim] 에 없는 주장")
    claim_type: ClaimType
    support: SupportStatus
    plausibility: InferencePlausibility | None = None
    hard_conflict: bool = False
    evidence: list[EvidenceLink] = Field(default_factory=list)
    temporal_ok: bool = True
    reason: str = ""


class ClaimVerificationLLMOutput(BaseModel):
    claims: list[ClaimVerdictLLMItem] = Field(default_factory=list, description="[검증할 claim] 전부에 대한 판정")
    untracked_claims: list[UntrackedClaimLLMItem] = Field(
        default_factory=list,
        description="본문의 주장 중 claim 목록에 빠졌고, 판정하면 문제가 드러나는 것만(문제없는 누락 주장은 적지 말 것)",
    )
    quantitative_issues: list[str] = Field(
        default_factory=list,
        description="서로 연결된 수치끼리 산술적으로 맞지 않는 곳(어떤 수치끼리, 왜 안 맞는지)",
    )
    unmarked_assumptions: list[str] = Field(
        default_factory=list,
        description="가정한 사건·조건·구체 수치인데 본문에 '(가정)' 등 가정 표시 없이 확정 사실처럼 쓴 서술(일반적 시장 인과 서술은 제외)",
    )
    reasoning_issues: list[ReasoningIssue] = Field(
        default_factory=list,
        description=(
            "claim 사이의 연결이 성립하지 않는 곳(중복 계산, 반대 방향 효과 누락, 한 줄 요약이 본문보다 단정적 등)."
            " 걸린 claim ID·이유·수정 방향(REMOVE|QUALIFY)을 함께 적을 것"
        ),
    )


SYSTEM_PROMPT = """**[역할 및 목적]**
당신은 글로벌 에너지(LNG/천연가스) 시장 MI 시스템의 사실 검증 담당자입니다.
생성된 가상 이벤트 1건의 주장(claim)을 수집 근거와 대조해 판정합니다.
가상 시나리오는 본래 근거에 없는 조건과 추론을 담습니다. 근거가 없다는 것 자체는 문제가 아니며,
claim 의 종류(claim_type)마다 아래의 서로 다른 기준으로 판정해야 합니다.
생성 단계가 붙인 claim_type 이 내용과 맞지 않으면(예: 근거에 없는 내용을 EVIDENCED_FACT 로 표시) 표시된 claim_type 기준으로 판정해 그 문제가 드러나게 하십시오.

**[공통: support — 근거가 claim 을 직접 지지하는 정도]**
모든 claim 에 채우십시오. EVIDENCED_FACT 에서만 판정 기준이 되고, 나머지 claim_type 에서는 참고 정보입니다.
- SUPPORTED: 근거 본문·근거 사실이 claim 을 직접 지지(수치·시점까지 일치)
- PARTIAL: 사건의 존재·방향은 지지하나 수치·시점·규모는 근거에 없음
- UNSUPPORTED: 직접 다루는 근거 없음
- CONTRADICTED: 근거와 정면 충돌

**[EVIDENCED_FACT — 근거 사실]**
- 근거로 확인된 사실이라고 표시한 claim 이므로 support 가 SUPPORTED 여야 합니다.
- 과거 시점에 나온 전망치를 기준일의 확정값처럼 쓴 claim 은 PARTIAL 입니다.
- [기준일 사실 시점표]에서 "지속 여부 미확인(STALE)"인 과거 상태를 기준일에도 계속되는 사실로 단정하면 PARTIAL 입니다.

**[MODEL_INFERENCE — 모델 추론: plausibility]**
직접 인용 근거가 있는지가 아니라, 경제적·물리적으로 타당한지를 판정하십시오.
- PLAUSIBLE: 표준적인 시장 전달 경로와 물리 제약에 비추어 타당함.
  (예: 유럽 가스 수요 급증 → TTF 상승 압력, 공급 차질 → 재고 인출 압력,
  아시아 카고 확보 경쟁 → JKM 상승 압력)
- WEAK: 성립은 가능하나 인과 고리가 약하거나 빠져 있고, 크기·방향·확신 수준이 과장됨. 다음의 경우 WEAK으로 판정.
  - 근거 없는 정밀 수치 범위를 시장 전망치처럼 단정
  - 모호한 사용자 전제를 근거 없이 특정 범위·대상·기간으로 확정(예: 부분 재개를 전면 복구로, 일부 대상의 변화를 전체 또는 특정 하위 대상의 변화로 해석)
  - 근거의 시점·대상·지표가 결론과 다른데 그대로 적용(예: 과거 실적·비중을 미래 배분·전망으로 확정, 다른 지역·설비의 지표를 대상에 그대로 적용)
  - 시장 간 반응 순서를 근거 없이 필연적 순서로 단정하거나, 모든 가격이 동시에 같은 방향으로 움직인다고 압축
  - 가격·수요·공급 변화의 비교 기준(직전 대비 / 사건이 없는 경우 대비)이 불명확한 채 결론을 냄
  - 경제적 유인을 실제 실행과 동일시(계약·설비 용량·재고·운송시간 제약 없이 물량이 즉시 이동·인출된다고 단정)
- CONTRADICTED: 근거 사실이나 물리·계약 제약과 모순
  (예: 근거상 복구 기간보다 짧은 기간에 정상화된다고 추론)
- 근거 문구 유무나 "(가정)" 표시 여부와 관계없이 경제적·물리적 타당성으로 판정하십시오.
  근거 문구가 없다는 이유만으로 WEAK·CONTRADICTED 로 판정하지 말고, 가정 표시가 있어도 그 가정에서 도출한 결론의 타당성은 따로 판정하십시오.

**[USER_ASSUMPTION — 사용자 가정: hard_conflict]**
사용자가 시나리오 조건으로 설정한 내용입니다(미래 한파, 프로젝트 지연, 해협 봉쇄·정상화 등).
- 근거가 없거나 현재 상태와 다른 것은 정상입니다. 시나리오는 상태 변화를 가정하는 것이기 때문입니다.
  (예: 근거 "현재 X 차질" vs 가정 "X 정상화" → 상태 변화 가정이므로 hard_conflict=false)
- hard_conflict=true 는 근거 사실·물리·계약 제약과 명백히 양립할 수 없을 때만입니다.
  (예: 아직 FID 전·미착공 프로젝트가 수개월 뒤 상업 생산, 설비 용량을 넘는 생산, 근거상 이미 일어난 사실의 부정)
- 근거상 일정과 다르지만 일어날 수는 있는 조건(예: 프로젝트 조기 가동·지연)은 hard_conflict=false 이고 temporal_ok=false 로만 표시하십시오.

**[시점 판정(temporal_ok)]**
- [기준일 사실 시점표]를 기준으로 판정하십시오. 시점표는 시스템이 날짜로 계산한 결과이므로 우선합니다.
- "아직 시작 전"인 프로젝트·계약의 물량을 기준일의 공급·완충재로 쓰면 false
- 이미 가동 중(first LNG·first cargo 포함)인 프로젝트를 아직 공급이 시작되지 않은 것처럼 쓰면 false
- "기준일 전에 종료"된 계약·상태를 기준일에 유효한 것처럼 쓰면 false
- 시점과 무관한 claim 은 true

**[누락 claim(untracked_claims)]**
- [검증할 claim] 은 결론을 좌우하는 핵심 주장만 담으므로, 본문의 모든 주장이 claim 으로 나열되어 있지 않은 것은 정상입니다.
- 한 줄 요약·bullet·상세분석의 사건·상태·수치·가격 방향 주장 중 [검증할 claim] 어디에도 해당하지 않으면서, 위 기준으로 판정했을 때
  문제가 드러나는 것(EVIDENCED_FACT 로 볼 서술인데 SUPPORTED 가 아님, MODEL_INFERENCE 인데 WEAK·CONTRADICTED, hard_conflict, temporal_ok=false)만
  claim_type 을 정해 적으십시오. 문제가 없는 누락 주장은 적지 마십시오.

**[수치 정합성(quantitative_issues)]**
- 서로 연결된 수치가 산술적으로 맞는지 확인하십시오.
  (예: 가격 변동폭과 결과 수준을 함께 쓰면 기준 가격 + 변동폭 = 결과 수준, 저장 인출 bcm 과 재고 %p 변화는 저장 용량 기준 환산이 맞아야 함)
- 기준값이 없어 확인할 수 없는 경우는 문제로 적지 마십시오. 명백히 맞지 않는 경우만 적으십시오.

**[가정 표시 누락(unmarked_assumptions)]**
- 가정한 사건·조건·구체 수치(사용자 가정, 근거 없는 모델 수치)를 본문이 "(가정)", "~ 가정 시" 같은 표시 없이 확정 사실처럼 쓴 곳만 적으십시오.
- 일반적인 시장 인과 서술(예: "TTF 상승 압력")은 가정 표시 대상이 아닙니다.

**[추론 연결(reasoning_issues)]**
개별 claim 의 판정과 별개로, claim 사이의 연결이 결론을 실제로 뒷받침하는지 확인해 성립하지 않는 곳만 적으십시오.
한 claim 안에서 완결되는 문제는 plausibility 로 판정하고, 여러 claim 에 걸친 문제만 여기에 적으십시오.
- 같은 영향을 여러 경로로 중복 계산함
- 상방·하방 효과가 함께 있는데 한쪽만 반영해 순효과를 결론냄
- 결론이 의존하는 핵심 중간 고리가 가정·약한 추론인데 결론을 확정적으로 서술함
- 한 줄 요약·bullet 의 단정 수준이 상세분석에서 밝힌 조건·완충 효과보다 강함
방향이 충분히 뒷받침되는 결론을 명확히 말한 것은 문제가 아닙니다. 모든 결론을 조건부로 만들라는 뜻이 아닙니다.
사용자 요청이 쓴 용어가 정의상 포함하는 조건은 사용자 전제로 보고, 별도 근거가 필요한 중간 고리로 보지 마십시오.
(예: 사용자가 "둔켈플라우테(Dunkelflaute)"라고 쓰면 정의상 저풍·저일사 동반이므로, 요청이 풍력 하락만 수치로 밝혔더라도
태양광 저발전 동반 서술은 추론 공백이 아님. 반대로 용어 정의를 넘어선 규모·기간·지역 확장은 여전히 판정 대상임)
각 항목에는 재작성이 어디를 어떻게 고칠지 알 수 있도록 아래를 함께 적으십시오.
- `claim_ids`: 연결이 성립하지 않는 claim ID(결론 claim 과 그 결론이 기대는 중간 고리 claim). 한 줄 요약·bullet 문제면 그 내용을 담은 claim ID
- `message`: 어떤 연결이 왜 결론을 뒷받침하지 못하는지 한 문장
- `fix`: REMOVE(그 연결이 시나리오에 꼭 필요하지 않아 삭제하면 해소됨) / QUALIFY(연결은 필요하나 조건부·가정 표시로 단정 수준을 낮추면 해소됨).
  중간 고리를 새로 덧붙여야만 성립하는 연결은 REMOVE 로 표시하십시오.

**[작성 규칙]**
- [검증할 claim] 의 모든 claim ID 에 대해 판정을 하나씩 내십시오.
- `evidence` 에는 입력에 있는 근거 키만 쓰십시오.
- `reason` 은 문제가 있는 판정에만 개조식 명사형 종결어미(~함, ~임, ~됨, ~음)로 한 문장 쓰고, 문제가 없으면 빈 문자열로 두십시오.
"""


USER_PROMPT = """[사용자 요청 사항]
{user_query}

[수집 근거(토픽별)]
{evidences}

[기준일 사실 시점표]
{timeline}

[검증할 이벤트]
한 줄 요약: {summary}
key_bullets:
{bullets}
상세 분석:
{detail}

[검증할 claim]
{claims}

위 이벤트의 claim 을 근거와 대조해 판정해 주세요."""


def build_messages(
    user_query: str,
    draft: EventDraft,
    groups: list[TopicEvidenceGroup],
    *,
    fact_timeline: FactTimeline | None,
) -> list[dict[str, Any]]:
    """system/user 메시지 리스트를 구성한다(I/O 없음).

    Args:
        user_query: 사용자 요청 문장 원문.
        draft: 검증할 초안 1건(생성 LLM 이 밝힌 claims 포함).
        groups: 초안 생성에 넣은 토픽별 근거.
        fact_timeline: 초안의 발생 시점(occurred_at) 기준으로 다시 계산한 사실 시점표.

    """
    user_content = USER_PROMPT.format(
        user_query=user_query.strip(),
        evidences=format_topic_groups(groups),
        timeline=format_timeline(fact_timeline),
        summary=draft.one_line_summary,
        bullets="\n".join(f"- {bullet}" for bullet in draft.key_bullets) or "(없음)",
        detail=draft.detail_analysis,
        claims=format_claims(draft.claims),
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
