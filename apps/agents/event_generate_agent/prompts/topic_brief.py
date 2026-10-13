"""토픽별 근거 정리 프롬프트 및 structured output schema (summarize_topics 노드).

토픽 1개와 그 토픽으로 검색한 근거만 받아
- 토픽과 직접 관련된 근거를 고르고(검색 결과에 섞인 무관한 결과 제거)
- 관련 근거로 확인되는 토픽의 현재 상황과 핵심 사실을 정리하며
- 관련 근거가 없으면 그 사실과 이유를 밝힌다.
초안 생성은 이 정리 결과를 토픽 단위로 받아 하나의 이벤트로 엮는다.
프롬프트 빌더는 순수 함수(I/O 없음)로 유지한다.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from apps.agents.event_generate_agent.constants import DEFAULT_LANGUAGE
from apps.agents.event_generate_agent.flows.generate_from_query.schema import (
    AssetStatus,
    EvidenceItem,
    FactKind,
    SearchTopic,
)
from apps.agents.event_generate_agent.prompts.event_draft import format_evidences


class FactLLMItem(BaseModel):
    statement: str = Field(description="근거에서 확인된 사실 1건(수치·날짜·주체 원문 보존, 근거 키는 적지 말 것)")
    evidence_keys: list[str] = Field(description="이 사실의 출처 근거 키(예: T1-W2). 입력에 없는 키는 쓰지 말 것")
    fact_kind: FactKind = Field(
        description="ACTUAL=이미 일어난 실적·사건, STATUS=기준 시점의 상태, PLAN=예정·계획, FORECAST=기관·매체 전망치",
    )
    entity: str = Field(default="", description="사실의 주체(프로젝트·트레인·설비·계약·국가·기관명)")
    asset_status: AssetStatus = Field(
        default=AssetStatus.NOT_APPLICABLE,
        description=(
            "프로젝트·설비·계약이면 기준 시점 상태. OPERATING=가동 중(first LNG·first cargo 포함), "
            "RAMP_UP=개시 후 증산 중, UNDER_CONSTRUCTION, PLANNED=개시 예정, OUTAGE=손상·중단. 그 외 NOT_APPLICABLE"
        ),
    )
    as_of: str = Field(
        default="",
        description="사실의 기준 시점(본문 기준 시점, 없으면 근거 발행일). YYYY-MM-DD/YYYY-MM/YYYY",
    )
    valid_from: str = Field(
        default="",
        description="가동·계약·상태가 시작되는(된) 시점. 근거에 없으면 빈 문자열. YYYY-MM-DD/YYYY-MM/YYYY",
    )
    valid_to: str = Field(
        default="",
        description="상태·계약 종료 시점, 복구 완료 예상 시점. 근거에 없으면 빈 문자열. YYYY-MM-DD/YYYY-MM/YYYY",
    )


class TopicBriefLLMOutput(BaseModel):
    relevant_evidence_keys: list[str] = Field(
        default_factory=list,
        description="토픽과 직접 관련된 근거 블록 머리의 키(예: T1-E2). 관련도 높은 순. 입력에 없는 키는 쓰지 말 것",
    )
    found: bool = Field(description="토픽과 직접 관련된 근거가 1건 이상 있으면 true")
    summary: str = Field(
        default="",
        description="관련 근거로 확인되는 토픽의 현재 상황 2~3문장. found=false면 빈 문자열",
    )
    facts: list[FactLLMItem] = Field(
        default_factory=list,
        description="관련 근거에서 확인된 핵심 사실 3~6개(시점·상태 포함). found=false면 빈 배열",
    )
    missing_reason: str = Field(
        default="",
        description="found=false 일 때 관련 근거가 없다고 본 이유 한 문장(어떤 결과가 왜 무관했는지)",
    )


SYSTEM_PROMPT = """**[역할 및 목적]**
당신은 글로벌 에너지(LNG/천연가스) 시장 MI(Market Intelligence) 시스템의 근거 정리 담당자입니다.
사용자 요청은 여러 토픽(사건·주제)으로 나뉘어 토픽마다 따로 검색되었습니다.
당신은 그중 [정리할 토픽] 하나에 대해 수집된 [토픽 근거]만 보고, 이 토픽의 근거를 정리합니다.
정리 결과는 이후 다른 토픽의 정리 결과와 함께 하나의 이벤트를 만드는 데 쓰입니다.

**[관련 근거 판정]**
- 검색은 키워드를 단어 단위로 쪼개 하나라도 맞으면 가져오는 방식이라, 토픽과 무관한 결과가 많이 섞여 있습니다.
- 토픽이 가리키는 사건·현상을 직접 다루는 근거만 관련 근거로 고르십시오.
  (예: 토픽 "북해 풍력 발전 둔화" → 풍속 저하·풍력 발전량 감소·그로 인한 가스 발전 수요 증가를 다루는 근거는 관련,
  유럽 가스 가격·LNG 화물 흐름만 다루고 풍력을 언급하지 않는 근거는 무관)
- 같은 지역·같은 시장이라는 이유만으로 관련 근거로 고르지 마십시오. 토픽의 핵심 현상이 근거 본문에 있어야 합니다.
- 사용자 요청이 아직 발생하지 않은 사건을 가정하는 경우, 토픽의 기준 사건·같은 주제의 과거 사례·가정 대상의 현재 상태를 보여주는 근거도 관련 근거입니다.
- 관련 근거가 하나도 없으면 found=false 로 두고, relevant_evidence_keys·summary·facts 는 비우고 missing_reason 을 적으십시오.
  억지로 무관한 근거를 끌어와 정리하지 마십시오. 관련 근거가 없다는 판단이 다음 단계의 재검색 신호가 됩니다.

**[정리 원칙]**
- 관련 근거에 있는 사실만 정리하십시오. 근거에 없는 내용을 추론해 덧붙이지 마십시오.
- 수치·날짜·기관명·국가명·설비명은 원문 표현대로 보존하십시오.
- 근거끼리 사실이 상충하면 더 최근 근거를 앞세우고 상충 사실도 함께 남기십시오.
- 다른 토픽과의 관계는 판단하지 마십시오. 이 토픽 자체의 상황만 정리합니다.
- 개조식 명사형 종결어미(~함, ~임, ~됨, ~음)를 사용하십시오.
- `facts` 의 각 사실은 근거 1건 이상에 직접 적혀 있어야 하며, `evidence_keys` 에 그 근거 키를 적으십시오.
- `facts` 에는 시점 정보를 보존하십시오. 시나리오 생성 단계가 이 값으로 "이벤트 시점에 이 사실이 유효한가"를 판정합니다.
  - 실적·상태인지, 계획·예정인지, 전망치인지 `fact_kind` 로 구분하십시오. 과거에 나온 전망치는 FORECAST 이고 `as_of` 는 전망 발표 시점입니다.
  - 프로젝트·트레인·설비·계약은 하나씩 따로 사실로 만들고 `asset_status` 와 `valid_from`(가동·개시 시점), `valid_to`(종료·복구 완료 시점)를 채우십시오.
    (예: "NFS 2028년 가동 개시 예정" → fact_kind=PLAN, asset_status=PLANNED, valid_from=2028)
    (예: "Golden Pass Train 1 2026-03 first LNG 생산" → fact_kind=ACTUAL, asset_status=OPERATING, valid_from=2026-03)
    (예: "손상 설비 복구에 3~5년 소요 전망" → fact_kind=FORECAST, asset_status=OUTAGE, valid_to=복구 완료 예상 시점)
  - 근거에 없는 시점은 지어내지 말고 빈 문자열로 두십시오.
"""


USER_PROMPT = """[사용자 요청 사항]
{user_query}

[정리할 토픽]
{topic_key}: {label}

[토픽 근거]
{evidences}

[작성 언어]
{language}

위 토픽 근거 중 [정리할 토픽]과 직접 관련된 근거를 고르고 정리해 주세요."""


def build_messages(
    user_query: str,
    topic: SearchTopic,
    evidences: list[EvidenceItem],
    *,
    language: str = DEFAULT_LANGUAGE,
) -> list[dict[str, Any]]:
    """system/user 메시지 리스트를 구성한다(I/O 없음).

    Args:
        user_query: 사용자가 입력한 요청 문장 원문. 토픽이 요청 안에서 맡은 역할을 알려준다.
        topic: 정리할 토픽.
        evidences: 이 토픽으로 검색한 근거만. 다른 토픽 근거는 넣지 않는다.
        language: 작성 언어.

    """
    user_content = USER_PROMPT.format(
        user_query=user_query.strip(),
        topic_key=topic.topic_key,
        label=topic.label,
        evidences=format_evidences(evidences),
        language=language,
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
