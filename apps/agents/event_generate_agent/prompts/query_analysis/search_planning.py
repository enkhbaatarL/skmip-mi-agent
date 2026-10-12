"""검색 계획 프롬프트 및 structured output schema (plan_search 노드).

classify_route 가 정한 route 를 받아, 그 분기에 필요한 질의 지침만 조립해
요청을 토픽(사건·주제)별로 나눠 토픽마다 검색 질의·키워드를, 요청 전체에 기간을 만든다. 섹션 본문은 _sections.py 에 둔다.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from apps.agents.event_generate_agent.flows.generate_from_query.schema import SearchRoute
from apps.agents.event_generate_agent.prompts.query_analysis import _sections


_WEB_ROUTES = frozenset({SearchRoute.WEB, SearchRoute.BOTH})
_EVENT_ROUTES = frozenset({SearchRoute.EXISTING_EVENT, SearchRoute.BOTH})


class SearchTopicLLMItem(BaseModel):
    label: str = Field(description="토픽 이름. 요청이 다루는 사건·주제 하나를 가리키는 짧은 명사구")
    web_queries: list[str] = Field(
        default_factory=list,
        description="이 토픽만 찾는 웹 검색 질의. 시스템 프롬프트에 웹 검색 질의 지침이 없으면 빈 배열",
    )
    event_keyword: str = Field(
        default="",
        description="이 토픽의 기존 이벤트를 찾을 핵심어 1개. 시스템 프롬프트에 기존 이벤트 키워드 지침이 없으면 빈 문자열",
    )


class SearchPlanLLMOutput(BaseModel):
    topics: list[SearchTopicLLMItem] = Field(
        default_factory=list,
        description="요청이 다루는 사건·주제별 검색 단위. 단일 주제면 1개, 병합·결합 요청이면 주제마다 1개",
    )
    impact_chain: list[str] = Field(
        default_factory=list,
        description="사건 → LNG 영향 경로의 '원인 → 결과' 고리 2~4개. 시스템 프롬프트에 영향 경로 지침이 없으면 빈 배열",
    )
    date_from: str = Field(default="", description="검색 시작일 YYYY-MM-DD. 기간 언급이 없으면 빈 문자열")
    date_to: str = Field(default="", description="검색 종료일 YYYY-MM-DD. 기간 언급이 없으면 빈 문자열")
    scenario_date: str = Field(
        default="",
        description="가정된 사건이 일어나는 시점 YYYY-MM-DD. 사건 가정형이 아니거나 시점 언급이 없으면 빈 문자열",
    )


def build_system_prompt(route: SearchRoute) -> str:
    """route 에 필요한 섹션만 골라 시스템 프롬프트를 조립한다.

    사건 가정형 섹션은 적용 조건(가정된 사건이 있는 요청)을 섹션 본문에 담고 있어,
    가정 여부는 LLM 이 문장을 보고 판단한다.
    """
    sections = [
        _sections.ROLE,
        _sections.TOPICS,
        _sections.DATE_RULES,
        _sections.HYPOTHETICAL_DATE_RULES,
    ]
    if route in _WEB_ROUTES:
        sections += [_sections.WEB_QUERY, _sections.HYPOTHETICAL_WEB_QUERY, _sections.IMPACT_CHAIN]
    if route in _EVENT_ROUTES:
        sections += [_sections.EVENT_KEYWORD, _sections.HYPOTHETICAL_EVENT_KEYWORD]
    return "\n\n".join(sections)


def build_user_prompt(user_query: str, *, today: str, route: SearchRoute, route_reason: str) -> str:
    """분석 대상 문장, 오늘 날짜, 앞 단계 분기 판단 결과를 담은 user 프롬프트를 만든다.

    Args:
        user_query: 사용자가 입력한 문장 원문.
        today: 상대 기간 표현을 절대 날짜로 바꿀 때 기준이 되는 오늘 날짜(YYYY-MM-DD).
        route: classify_route 가 고른 분기.
        route_reason: classify_route 의 판단 근거. 각 분기에서 무엇을 찾아야 하는지 알려준다.

    """
    return f"""[사용자 입력 문장]
{user_query}

[오늘 날짜]
{today}

[분기 판단 결과]
- route: {route.value}
- route_reason: {route_reason}

분기 판단 결과에 맞춰 토픽을 나누고, 토픽별 검색 질의·키워드와 기간을 구성하세요."""
