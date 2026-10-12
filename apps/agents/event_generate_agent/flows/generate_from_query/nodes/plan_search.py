"""plan_search 노드 — 분기 판단 결과에 맞춰 토픽별 검색 질의·키워드와 기간을 LLM으로 구성한다.

프롬프트에는 route 에 필요한 질의 지침만 들어간다.
LLM이 채우지 못한 값만 노드에서 보정한다.

토픽:
- 요청이 다루는 사건·주제마다 SearchTopic 을 하나씩 만든다(병합·결합이면 여러 개, 단일 주제면 1개).
  검색과 근거 정리는 토픽 단위로 따로 이뤄진다.

폴백 대비:
- summarize_topics 가 관련 근거를 못 찾은 토픽은 반대 분기로 1회 재검색한다.
  이때 프롬프트에 없던 분기의 질의가 비어 있으므로, 토픽의 web_queries 는 label 로,
  event_keyword 는 label 로 채워 둔다.

기간 규칙:
- 사용자가 기간을 지정하면 그 값을 date_from/date_to 에 그대로 채운다.
- 기간 언급이 없으면 date_from 은 빈 문자열로 두고 date_to 만 오늘로 채운다.
  여기서는 "사용자가 무엇을 지정했는가"만 담고, 지정이 없을 때의 기본 구간은
  분기별로 다르므로 각 검색 노드가 정한다(search_web 은 최근 N일로 좁히고,
  search_existing_events 는 시작일 필터 없이 키워드로만 찾는다).
"""

from __future__ import annotations

from datetime import date
import re
from typing import Any

from langgraph.runtime import Runtime

from apps.agents.event_generate_agent.constants import LIGHT_REASONING_EFFORT
from apps.agents.event_generate_agent.flows.generate_from_query.schema import QueryPlan, SearchTopic
from apps.agents.event_generate_agent.flows.generate_from_query.state import GenerateFromQueryState
from apps.agents.event_generate_agent.prompts.query_analysis import search_planning as plan_prompt
from apps.common.configs.config import get_settings
from apps.common.logging.decorators import log_node
from apps.common.logging.logger_config import logger
from apps.common.tracing.context import TraceContext
from apps.common.utils.time_utils import today as today_str
from apps.common.values.enums import ModelPreference


# 웹 검색 질의 1건이 곧 Responses API 호출 1건이라, 토픽 수 x 질의 수가 검색 구간 지연을 좌우한다.
_MAX_WEB_QUERIES = 2
# 사건 가정형은 영향 경로 고리마다 사실을 확인해야 해서 질의 상한을 따로 둔다.
_MAX_WEB_QUERIES_WITH_CHAIN = 3
_MAX_IMPACT_CHAIN_STEPS = 4
# 병합 요청은 대상 이벤트(토픽)마다 검색 단위가 하나씩 필요하다.
_MAX_TOPICS = 4

# MCP 서버(mi_events_list)가 startDate/endDate 에 강제하는 형식.
_ISO_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _normalize_date(value: str, *, source: str) -> str:
    """YYYY-MM-DD 로 읽히는 값만 남기고 나머지는 빈 문자열로 떨어뜨린다.

    기간은 선택적 필터이므로, 형식이 깨진 값을 그대로 넘겨 검색 전체를 실패시키는 대신
    버리고 필터 없이 검색한다. LLM 출력과 요청값 모두 형식 보장이 없어 여기서 막는다.
    """
    candidate = value.strip()
    if not candidate:
        return ""
    if _ISO_DATE_PATTERN.match(candidate):
        try:
            date.fromisoformat(candidate)
        except ValueError:
            pass
        else:
            return candidate
    logger.warning(f"[NODE][plan_search] INVALID_DATE | source={source} | value={candidate!r} | 기간 필터에서 제외")
    return ""


def _clean(values: list[str], *, limit: int) -> list[str]:
    return [value.strip() for value in values if value.strip()][:limit]


def _to_topics(
    items: list[plan_prompt.SearchTopicLLMItem],
    *,
    fallback_label: str,
    max_web_queries: int,
) -> list[SearchTopic]:
    """LLM 토픽을 SearchTopic 으로 옮기고 비어 있는 검색 필드를 label 로 채운다.

    label 이 같은 토픽은 하나로 합친다. 토픽이 하나도 없으면 요청 전체를 토픽 1개로 본다.
    """
    topics: list[SearchTopic] = []
    seen_labels: set[str] = set()
    for item in items:
        label = item.label.strip() or item.event_keyword.strip()
        if not label or label in seen_labels:
            continue
        seen_labels.add(label)
        topics.append(
            SearchTopic(
                topic_key=f"T{len(topics) + 1}",
                label=label,
                event_keyword=item.event_keyword.strip() or label,
                web_queries=_clean(item.web_queries, limit=max_web_queries) or [label],
            ),
        )
        if len(topics) >= _MAX_TOPICS:
            break
    if not topics:
        topics.append(
            SearchTopic(
                topic_key="T1",
                label=fallback_label,
                event_keyword=fallback_label,
                web_queries=[fallback_label],
            ),
        )
    return topics


def _to_query_plan(
    llm_output: plan_prompt.SearchPlanLLMOutput,
    state: GenerateFromQueryState,
    *,
    today: str,
) -> QueryPlan:
    """LLM 검색 계획을 QueryPlan으로 옮기고, 비어 있는 값과 요청 고정값만 보정한다."""
    # 영향 경로는 사건 가정형 요청에서만 채워지도록 프롬프트가 지시한다(실제 사건이면 빈 배열).
    impact_chain = _clean(llm_output.impact_chain, limit=_MAX_IMPACT_CHAIN_STEPS)
    max_web_queries = _MAX_WEB_QUERIES_WITH_CHAIN if impact_chain else _MAX_WEB_QUERIES
    topics = _to_topics(
        llm_output.topics,
        fallback_label=" ".join(state.user_query.split()),
        max_web_queries=max_web_queries,
    )

    # 요청에서 명시한 기간이 LLM 추론보다 우선한다.
    # 양쪽 다 기간을 주지 않으면 date_from 을 비워 둔다. 이 빈 값이 곧 "지정 없음" 신호이고,
    # 그때 무엇으로 대체할지는 검색 노드가 분기 성격에 맞게 정한다.
    date_from = _normalize_date(state.date_from, source="request") or _normalize_date(
        llm_output.date_from,
        source="llm",
    )
    date_to = (
        _normalize_date(state.date_to, source="request") or _normalize_date(llm_output.date_to, source="llm") or today
    )

    return QueryPlan(
        topics=topics,
        impact_chain=impact_chain,
        date_from=date_from,
        date_to=date_to,
        scenario_date=_normalize_date(llm_output.scenario_date, source="llm_scenario"),
    )


@log_node
async def plan_search(
    state: GenerateFromQueryState,
    runtime: Runtime[TraceContext] | None = None,
) -> dict[str, Any]:
    """route + 사용자 문장 → QueryPlan(토픽별 검색 질의/영향 경로/기간)."""
    from apps.connectors.llm.llm_client import invoke_llm_structured_output

    cfg = get_settings()
    today = today_str()

    result = await invoke_llm_structured_output(
        output_schema=plan_prompt.SearchPlanLLMOutput,
        messages=[
            {
                "role": "system",
                "content": plan_prompt.build_system_prompt(state.route),
            },
            {
                "role": "user",
                "content": plan_prompt.build_user_prompt(
                    state.user_query.strip(),
                    today=today,
                    route=state.route,
                    route_reason=state.route_reason,
                ),
            },
        ],
        preference=ModelPreference.SPEED,
        temperature=0.0,
        trace_context=runtime.context if runtime is not None else None,
        stream=cfg.llm_stream_enabled,
        reasoning_effort=LIGHT_REASONING_EFFORT,
    )

    plan = _to_query_plan(result.result, state, today=today)
    logger.info(
        f"[NODE][plan_search] PLAN | route={state.route.value} | topics={len(plan.topics)} "
        f"| period={plan.date_from}~{plan.date_to} | scenario_date={plan.scenario_date or '-'} "
        f"| impact_chain_steps={len(plan.impact_chain)}",
    )
    for topic in plan.topics:
        logger.info(
            f"[NODE][plan_search] TOPIC | {topic.topic_key} | label={topic.label!r} "
            f"| event_keyword={topic.event_keyword!r} | web_queries={topic.web_queries}",
        )
    return {"query_plan": plan}
