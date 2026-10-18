"""기존 이벤트 편집(병합·수치 수정) 프롬프트 및 structured output schema.

existing_event 분기에서만 쓴다. 근거는 MI DB 의 기존 이벤트이고, 새 사건을 상상하는
event_draft 프롬프트와 달리 원본 이벤트의 사실을 최대한 보존한 채
- merge : 기존 이벤트 n개를 하나의 이벤트로 합치거나
- modify: 기존 이벤트 1개의 수치·조건(기간, 규모, 가격 등)만 바꾼다.
어느 쪽인지와 원본 이벤트 ID 는 LLM 이 사용자 요청과 근거를 보고 함께 밝힌다.
프롬프트 빌더는 순수 함수(I/O 없음)로 유지한다.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from apps.agents.event_generate_agent.constants import DEFAULT_LANGUAGE, MAX_EVENT_DRAFTS
from apps.agents.event_generate_agent.flows.generate_from_query.schema import FactTimeline, TopicEvidenceGroup
from apps.agents.event_generate_agent.prompts.event_draft import (
    CLAIM_OUTPUT_RULES,
    EventDraftLLMItem,
    format_topic_groups,
)
from apps.agents.event_generate_agent.prompts.validation_context import format_timeline
from apps.agents.event_generate_agent.schemas.domain import ExistingEventOperation


class ExistingEventEditLLMItem(EventDraftLLMItem):
    operation: ExistingEventOperation = Field(
        description="'merge'=기존 이벤트 2개 이상을 하나로 합침, 'modify'=기존 이벤트 1개의 수치·조건만 바꿈",
    )
    source_mi_event_ids: list[int] = Field(
        default_factory=list,
        description="병합·수정의 원본 이벤트 ID(근거 블록 머리의 miEventId 값). modify면 1개, merge면 2개 이상",
    )


class ExistingEventEditLLMOutput(BaseModel):
    events: list[ExistingEventEditLLMItem] = Field(default_factory=list)


SYSTEM_PROMPT = """**[역할 및 목적]**
당신은 글로벌 에너지(LNG/천연가스) 시장 MI(Market Intelligence) 시스템의 이벤트 편집자입니다.
[기존 이벤트 DB]에 이미 등록된 이벤트를 [사용자 요청 사항]에 맞춰 하나의 새 이벤트로 재구성합니다.
새로운 사건을 상상해 덧붙이는 것이 아니라, 원본 이벤트의 사실을 보존하면서 요청된 부분만 바꾸는 것이 목표입니다.

**[편집 방식(operation) 판단]**
- **merge (병합)**: 사용자가 기존 이벤트 2개 이상을 하나로 합치라고 요청한 경우입니다.
- **modify (수치 수정)**: 사용자가 기존 이벤트 1개의 기간·규모·물량·가격 수준 등 수치나 조건만 바꾸라고 요청한 경우입니다.
  (예: "호르무즈 해협 1개월 봉쇄" → "호르무즈 해협 6개월 봉쇄")

**[원본 이벤트(source_mi_event_ids) 식별]**
- [기존 이벤트 DB]는 사용자 요청이 지칭하는 이벤트(토픽)별로 나뉘어 있고, 토픽마다 `근거 정리`와 관련 근거 블록이 있습니다.
- 각 토픽에서 사용자 요청이 지칭하는 이벤트를 골라 근거 블록 머리의 `miEventId` 값을 적으십시오. 입력에 없는 ID를 만들지 마십시오.
- modify는 원본 1개, merge는 토픽마다 원본 1개씩(총 2개 이상)입니다. 한 토픽에 후보가 여러 건이면 사용자 요청과 가장 일치하는 이벤트를 고르십시오.
- `관련 근거 없음`으로 표시된 토픽이 있어도 결과를 비우지 마십시오. 찾은 토픽의 원본으로 편집하고,
  빠진 토픽은 사용자 요청 문장의 범위에서만 반영하되 근거 없이 반영했음을 `generation_rationale`에 밝히십시오.

**[modify 작성 원칙]**
1. 원본 이벤트의 구조·사실·주체·표현을 최대한 그대로 유지하십시오.
2. 요청된 수치와, 그 수치에 직접 종속되는 서술(지속 기간에 따른 누적 물량, 영향 강도, 가격 반응의 크기·지속성, 대응 정책의 수위)만 일관되게 조정하십시오.
3. 바뀐 수치가 원본의 다른 문장과 모순되지 않도록 한 줄 요약·bullet·상세분석 전체를 함께 고치십시오.
4. 수치 변경과 무관한 새 사실·새 주체·새 사건을 추가하지 마십시오.

**[merge 작성 원칙]**
1. 토픽별 `근거 정리`의 핵심 사실을 빠짐없이 반영하고, 원본 이벤트들의 중복 사실은 하나로 통합하되 각 원본의 핵심 사실·수치·날짜는 보존하십시오.
2. 사실이 서로 상충하면 더 최근 근거를 우선하고, 상충이 남으면 그 차이를 명시하십시오.
3. 사건 간 상호작용(연쇄·증폭·상쇄)을 원본에 근거해 서술하고, 원본에 없는 사실은 추가하지 마십시오.
4. 한 줄 요약은 병합된 사건 전체를 대표하도록 작성하십시오.

**[출력 필드 및 문체 규칙]**
- 모든 출력은 한국어로 작성하며, 반드시 개조식 명사형 종결어미(ex.~함, ~임,~됨, ~음)만 사용하십시오. (~한다, ~이다, ~했다 사용 금지)
- **one_line_summary**: 이벤트 제목으로 쓰이는 한 줄 요약. `[토픽] 마지막으로 확인된 주요 전개` 형식, 100자 권장·120자 이내.
  - 원본 이벤트 제목에 `[토픽]`이 있으면 그 토픽을 유지하고, 없으면 핵심 사건의 주체·직접 대상인 중심 사안 이름으로 붙이십시오.
    (예: `[GAIL LNG 조달]`, `[호르무즈 통항]`, `[Freeport 운영]`)
  - 병합이면 병합된 사건 전체를 대표하는 토픽 하나를 쓰십시오. 출처 정보는 넣지 마십시오.
- **search_text**: 편집된 이벤트의 검색용 요약. 서식 없는 일반 텍스트 2~4문장, 500자 이내.
  `one_line_summary`를 반복하지 말고 주체·대상·기간·핵심 수치를 담되, 다른 출력 필드에 쓴 내용만 요약하십시오.
- **key_bullets**: 핵심 포인트 3~5개. 전체 항목 안에 아래 세 관점이 모두 포함되도록 작성하십시오.(최소 1개)
    - **(A) 사건의 상태·전개** — 날짜, 주체, 발생 사실
    - **(B) Fundamental 영향** — 실물 수급·설비·물동량
    - **(C) 가격 방향** — Premium, Forward 변화, 가격 Band
- **detail_analysis**: `one_line_summary`의 핵심 사건을 상세히 풀어쓴 설명. 아래 2개의 지정된 제목을 사용하여 두 문단으로 작성하십시오.
  문단 제목에는 Bullet을 붙이지 않고, 각 문단은 Bullet 없이 하나의 통글로 작성하며, 두 문단 사이는 줄바꿈 2번(`\\n\\n`)으로 띄우십시오.
    - **사건 요약 :** (병합·수정된 사건을 구체적으로 묘사)
    - **LNG 시장 관점 :** (공급망, 물류, 가격 프리미엄 등에 미치는 파급 효과 분석)
"""

USER_PROMPT = """
아래 [기존 이벤트 DB]와 [사용자 요청 사항]을 읽고, 위의 규칙에 맞춰 편집된 이벤트를 생성해 주세요.

**[기존 이벤트 DB]**
{existing_event}

**[사용자 요청 사항]**
{user_query}

**[기준일 사실 시점표]**
{timeline}
{revision}
"""


def _build_output_rules(*, today: str, language: str, max_events: int) -> str:
    return f"""**[출력 보충 규칙]**
- 오늘 날짜는 {today} 입니다. 작성 언어: {language}
- 생성할 이벤트는 최대 {max_events}건입니다. 병합이든 수정이든 결과는 보통 1건입니다.
- `operation`, `source_mi_event_ids`: 위 판단 기준에 따라 채우십시오.
- `occurred_at`: modify면 원본 이벤트의 발생 시점을, merge면 원본 중 가장 이른 발생 시점을 YYYY-MM-DD 로 채우십시오.
  판단할 수 없으면 빈 문자열로 두십시오.
- `tags`: 국가/설비/지수 등 검색에 쓸 짧은 명사구 3~5개.
- `generation_rationale`: 2~3문장으로 작성하십시오.
  - modify: 바꾼 수치를 "원래 값 → 새 값" 형태로 모두 밝히고, 그에 따라 함께 조정한 서술을 설명하십시오.
  - merge: 각 원본 이벤트에서 무엇을 가져와 어떻게 엮었는지 설명하십시오.
- `evidence_refs`: 실제로 참고한 근거만 나열하십시오.
  - `evidence_key`: 근거 블록 머리의 키(`T1-E1`, `T2-E3` 등). 입력에 없는 키를 만들지 마십시오.
  - `evidence_title`: 해당 블록의 `제목:` 값을 그대로 옮기십시오.
  - `referenced_content`: 그 근거에서 가져온 핵심 사실·수치·날짜·주체를 원문 표현 기준 1문장(80자 이내)으로 적으십시오.
  - `usage`: 반영한 위치와 역할을 40자 이내 짧은 구로 적으십시오.
- 바꾼 수치·조건은 USER_ASSUMPTION claim 으로, 원본 이벤트에서 그대로 가져온 사실은 EVIDENCED_FACT claim 으로 표시하십시오.
  근거와의 대조 설명은 본문에 쓰지 마십시오.
{CLAIM_OUTPUT_RULES}"""


def build_messages(
    user_query: str,
    groups: list[TopicEvidenceGroup],
    *,
    today: str,
    language: str = DEFAULT_LANGUAGE,
    max_events: int = MAX_EVENT_DRAFTS,
    fact_timeline: FactTimeline | None = None,
    revision: str = "",
) -> list[dict[str, Any]]:
    """system/user 메시지 리스트를 구성한다(I/O 없음).

    Args:
        user_query: 사용자가 입력한 요청 문장 원문.
        groups: 토픽별 근거 정리와 프롬프트에 넣을 기존 이벤트 근거(상한은 group_prompt_evidences 가 적용).
        today: 상대 기간 표현 해석 기준일(YYYY-MM-DD).
        language: 생성 언어.
        max_events: 한 요청에서 생성할 이벤트 상한.
        fact_timeline: 근거 사실의 시나리오 기준일 시점표.
        revision: 재작성 패스면 event_draft.format_revision 결과, 아니면 빈 문자열.

    """
    user_content = USER_PROMPT.format(
        existing_event=format_topic_groups(groups),
        user_query=user_query.strip(),
        timeline=format_timeline(fact_timeline),
        revision=revision,
    )
    rules = _build_output_rules(today=today, language=language, max_events=max_events)
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"{user_content}\n{rules}"},
    ]
