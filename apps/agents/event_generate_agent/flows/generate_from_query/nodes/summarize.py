"""summarize_topics 노드 — 토픽별로 근거를 정리하고, 근거가 없는 토픽만 반대 분기로 폴백한다.

토픽마다 그 토픽의 근거만 LLM 에 넘겨 관련 근거 선별 + 핵심 사실 정리를 병렬로 수행한다.
초안 생성은 원본 근거 전체가 아니라 이 정리 결과(TopicBrief)와 토픽별 관련 근거를 본다.

폴백:
- 1차 패스에서 관련 근거를 못 찾은 토픽만 반대 분기(web ↔ existing_event)로 1회 재검색한다.
  `fallback_used` 로 재진입은 1회로 제한되고, BOTH 는 이미 양쪽을 다 돌았으므로 폴백하지 않는다.
- 폴백 패스에서는 재검색한 토픽만 다시 정리하고, 나머지 토픽의 정리 결과는 그대로 둔다.
"""

from __future__ import annotations

import asyncio
from typing import Any

from langgraph.runtime import Runtime

from apps.agents.event_generate_agent.constants import LIGHT_REASONING_EFFORT
from apps.agents.event_generate_agent.flows.generate_from_query.schema import (
    EvidencedFact,
    EvidenceItem,
    SearchRoute,
    SearchTopic,
    TopicBrief,
)
from apps.agents.event_generate_agent.flows.generate_from_query.state import GenerateFromQueryState
from apps.agents.event_generate_agent.prompts import topic_brief as brief_prompt
from apps.common.configs.config import get_settings
from apps.common.logging.decorators import log_node
from apps.common.logging.logger_config import logger
from apps.common.tracing.context import TraceContext
from apps.common.values.enums import ModelPreference


_OPPOSITE_ROUTE = {
    SearchRoute.WEB: SearchRoute.EXISTING_EVENT,
    SearchRoute.EXISTING_EVENT: SearchRoute.WEB,
}

_ROUTES_SEARCHED = {
    SearchRoute.WEB: [SearchRoute.WEB],
    SearchRoute.EXISTING_EVENT: [SearchRoute.EXISTING_EVENT],
    SearchRoute.BOTH: [SearchRoute.WEB, SearchRoute.EXISTING_EVENT],
}


def _clean_keys(raw_keys: list[str], known_keys: set[str], *, topic_key: str) -> list[str]:
    """입력에 있는 근거 키만 순서대로 남긴다(괄호 제거, 중복 제거)."""
    keys: list[str] = []
    for raw_key in raw_keys:
        key = raw_key.strip().strip("[]")
        if key not in known_keys:
            logger.warning(f"[NODE][summarize_topics] UNKNOWN_EVIDENCE | topic={topic_key} | key={raw_key!r}")
            continue
        if key not in keys:
            keys.append(key)
    return keys


def _to_facts(
    items: list[brief_prompt.FactLLMItem],
    topic_key: str,
    relevant_keys: list[str],
) -> list[EvidencedFact]:
    """LLM 이 뽑은 사실에 fact_id 를 붙인다. 관련 근거에 출처가 없는 사실은 근거 사실이 아니므로 버린다."""
    facts: list[EvidencedFact] = []
    for item in items:
        statement = item.statement.strip()
        keys = _clean_keys(item.evidence_keys, set(relevant_keys), topic_key=topic_key)
        if not statement or not keys:
            logger.warning(f"[NODE][summarize_topics] DROP_FACT | topic={topic_key} | statement={statement!r}")
            continue
        facts.append(
            EvidencedFact(
                fact_id=f"{topic_key}-F{len(facts) + 1}",
                topic_key=topic_key,
                statement=statement,
                evidence_keys=keys,
                fact_kind=item.fact_kind,
                entity=item.entity.strip(),
                asset_status=item.asset_status,
                as_of=item.as_of.strip(),
                valid_from=item.valid_from.strip(),
                valid_to=item.valid_to.strip(),
            ),
        )
    return facts


def _to_brief(
    output: brief_prompt.TopicBriefLLMOutput,
    topic: SearchTopic,
    evidences: list[EvidenceItem],
) -> TopicBrief:
    """LLM 정리 결과를 TopicBrief 로 옮긴다. 입력에 없는 근거 키는 버린다.

    found=true 인데 유효한 키가 하나도 없으면, 초안이 쓸 근거가 없으므로 found=false 로 본다.
    """
    known_keys = {evidence.evidence_key for evidence in evidences}
    keys = _clean_keys(output.relevant_evidence_keys, known_keys, topic_key=topic.topic_key)

    if not output.found or not keys:
        reason = output.missing_reason.strip() or "토픽과 직접 관련된 근거를 고르지 못했습니다."
        return TopicBrief(topic_key=topic.topic_key, label=topic.label, found=False, missing_reason=reason)
    facts = _to_facts(output.facts, topic.topic_key, keys)
    return TopicBrief(
        topic_key=topic.topic_key,
        label=topic.label,
        found=True,
        summary=output.summary.strip(),
        facts=facts,
        evidence_keys=keys,
    )


async def _summarize_topic(
    state: GenerateFromQueryState,
    topic: SearchTopic,
    evidences: list[EvidenceItem],
    *,
    trace_context: TraceContext | None,
) -> tuple[TopicBrief, str | None]:
    """토픽 1개의 근거를 정리한다. (정리 결과, 경고 문구 또는 None)을 돌려준다."""
    from apps.connectors.llm.llm_client import invoke_llm_structured_output

    if not evidences:
        return TopicBrief(
            topic_key=topic.topic_key,
            label=topic.label,
            found=False,
            missing_reason="검색 결과가 없습니다.",
        ), None

    cfg = get_settings()
    try:
        result = await invoke_llm_structured_output(
            output_schema=brief_prompt.TopicBriefLLMOutput,
            messages=brief_prompt.build_messages(state.user_query, topic, evidences, language=state.language),
            preference=ModelPreference.SPEED,
            temperature=0.0,
            trace_context=trace_context,
            stream=cfg.llm_stream_enabled,
            reasoning_effort=LIGHT_REASONING_EFFORT,
        )
    except Exception as exc:
        # 정리 실패로 수집한 근거까지 잃지 않도록, 관련 판정 없이 토픽 근거 전부를 넘긴다.
        logger.exception(f"[NODE][summarize_topics] FAILED | topic={topic.topic_key} | evidences={len(evidences)}")
        brief = TopicBrief(
            topic_key=topic.topic_key,
            label=topic.label,
            found=True,
            evidence_keys=[evidence.evidence_key for evidence in evidences],
        )
        return brief, f"'{topic.label}' 토픽 근거 정리에 실패해 수집한 근거를 그대로 사용했습니다: {exc!r}"
    return _to_brief(result.result, topic, evidences), None


@log_node
async def summarize_topics(
    state: GenerateFromQueryState,
    runtime: Runtime[TraceContext] | None = None,
) -> dict[str, Any]:
    """이번 패스의 토픽마다 근거를 정리하고, 관련 근거가 없는 토픽의 폴백 여부를 정한다."""
    topics = state.topics_to_search()
    searched_route = (state.fallback_route if state.pending_fallback else None) or state.route
    trace_context = runtime.context if runtime is not None else None

    outcomes = await asyncio.gather(
        *(
            _summarize_topic(
                state,
                topic,
                [evidence for evidence in state.evidences if evidence.topic_key == topic.topic_key],
                trace_context=trace_context,
            )
            for topic in topics
        ),
    )

    # 앞 패스의 정리 결과는 유지하고, 이번 패스에 다시 정리한 토픽만 교체한다.
    previous = {brief.topic_key: brief for brief in state.topic_briefs}
    current: dict[str, TopicBrief] = {}
    warnings: list[str] = []
    for brief, warning in outcomes:
        routes = [*previous.get(brief.topic_key, brief).searched_routes, *_ROUTES_SEARCHED[searched_route]]
        current[brief.topic_key] = brief.model_copy(update={"searched_routes": list(dict.fromkeys(routes))})
        if warning:
            warnings.append(warning)
    all_topics = state.query_plan.topics if state.query_plan else topics
    briefs = [
        current.get(topic.topic_key) or previous[topic.topic_key]
        for topic in all_topics
        if topic.topic_key in current or topic.topic_key in previous
    ]

    for brief in current.values():
        logger.info(
            f"[NODE][summarize_topics] TOPIC | {brief.topic_key} | label={brief.label!r} | found={brief.found} "
            f"| routes={[route.value for route in brief.searched_routes]} | evidences={brief.evidence_keys} "
            f"| facts={len(brief.facts)}{f' | missing={brief.missing_reason!r}' if not brief.found else ''}",
        )

    update: dict[str, Any] = {"topic_briefs": briefs, "pending_fallback": False}
    missing = [brief for brief in current.values() if not brief.found]
    if missing and not state.fallback_used and state.route is not SearchRoute.BOTH:
        fallback_route = _OPPOSITE_ROUTE[state.route]
        logger.warning(
            f"[NODE][summarize_topics] TOPIC_FALLBACK | topics={[brief.topic_key for brief in missing]} "
            f"| route={state.route.value} → fallback={fallback_route.value}",
        )
        update.update(
            {
                "fallback_used": True,
                "pending_fallback": True,
                "fallback_route": fallback_route,
                "fallback_topic_keys": [brief.topic_key for brief in missing],
            },
        )
        warnings.extend(
            f"'{brief.label}' 토픽은 '{state.route.value}' 분기에서 관련 근거를 찾지 못해 "
            f"'{fallback_route.value}' 분기로 재검색했습니다({brief.missing_reason})."
            for brief in missing
        )
    else:
        warnings.extend(
            f"'{brief.label}' 토픽의 관련 근거를 찾지 못했습니다({brief.missing_reason})." for brief in missing
        )

    logger.info(
        f"[NODE][summarize_topics] DONE | topics={len(briefs)} | found={sum(brief.found for brief in briefs)} "
        f"| pending_fallback={update['pending_fallback']}",
    )
    if warnings:
        update["warnings"] = warnings
    return update
