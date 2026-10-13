"""search_web 노드 — 웹 검색으로 이벤트 생성 근거를 수집한다.

검색 자체는 WebSearchProviderFactory 가 설정(`web_search_provider`)으로 고른 provider
(Responses API / Tavily)들이 수행하고, 이 노드는 질의 x provider fan-out 과 flow 도메인
타입(WebDocument → EvidenceItem) 변환만 담당한다. provider 응답은 범용 dict 이므로 flow 전용 schema 로의
변환은 이 층에 둔다.

`web_search_provider` 에 provider 를 여러 개 나열하면 같은 질의를 각 provider 로 모두
검색하고 결과를 한 목록으로 합친다.

검색은 토픽 단위다. 토픽마다 자기 web_queries 로 검색하고, 결과 문서에 topic_key 를 달아
dedup·상한도 토픽 안에서만 적용한다(다른 토픽 문서가 상한을 독점하지 않게).

검색은 2단계다. 먼저 source registry 의 공식·1차 출처 도메인으로 제한해 검색하고,
거기서 채택할 문서가 한 건도 없는 토픽만 도메인 제한 없이(provider 기본 설정으로) 다시 검색한다.
"""

from __future__ import annotations

import asyncio
from collections import Counter
from datetime import date, timedelta
from itertools import zip_longest
import time
from typing import Any, NamedTuple
from urllib.parse import urlparse

from langgraph.runtime import Runtime

from apps.agents.event_generate_agent.constants import (
    DEFAULT_SEARCH_LOOKBACK_DAYS,
    MAX_WEB_DOCUMENTS,
    WEB_SEARCH_MAX_TOOL_CALLS,
    WEB_SEARCH_REASONING_EFFORT,
)
from apps.agents.event_generate_agent.flows.generate_from_query.schema import (
    BranchError,
    QueryPlan,
    SearchTopic,
    WebDocument,
)
from apps.agents.event_generate_agent.flows.generate_from_query.state import GenerateFromQueryState
from apps.agents.event_generate_agent.flows.generate_from_query.tools.evidence import web_documents_to_evidences
from apps.agents.event_generate_agent.flows.generate_from_query.tools.source_registry import registry_domains
from apps.common.logging.decorators import log_node
from apps.common.logging.logger_config import logger
from apps.common.tracing.context import TraceContext
from apps.common.utils.time_utils import today as today_str
from apps.connectors.web.base import WebSearchProvider
from apps.connectors.web.factory import WebSearchProviderFactory
from apps.connectors.web.provider import ResponsesWebSearchProvider


def _dedup_queries(queries: list[str]) -> list[str]:
    """공백을 정리하고 빈 질의·중복 질의를 제거한다. 원래 순서는 유지한다.

    Args:
        queries: QueryPlan.web_queries 원본 질의 목록.

    """
    seen: set[str] = set()
    unique: list[str] = []
    for raw_query in queries:
        query = raw_query.strip()
        if not query or query in seen:
            continue
        seen.add(query)
        unique.append(query)
    return unique


def _search_period(plan: QueryPlan) -> tuple[str, str]:
    """웹 검색에 적용할 기간(date_from, date_to)을 정한다.

    지정이 없으면 최근 DEFAULT_SEARCH_LOOKBACK_DAYS=90일을 기본값으로 쓴다.

    Args:
        plan: 검색 계획. date_from/date_to(YYYY-MM-DD)가 비어 있으면 기본 기간을 적용한다.

    """
    date_to = plan.date_to or today_str()
    if plan.date_from:
        return plan.date_from, date_to
    lookback_from = (date.fromisoformat(date_to) - timedelta(days=DEFAULT_SEARCH_LOOKBACK_DAYS)).isoformat()
    logger.info(
        f"[NODE][search_web] DEFAULT_PERIOD | {lookback_from}~{date_to} | lookback_days={DEFAULT_SEARCH_LOOKBACK_DAYS}",
    )
    return lookback_from, date_to


def _source_name(url: str) -> str:
    """URL 에서 매체명 대용으로 쓸 도메인을 뽑는다.

    Args:
        url: 검색 결과 문서 URL.

    """
    return urlparse(url).netloc.removeprefix("www.")


def _to_documents(
    payload: dict[str, Any],
    *,
    query: str,
    provider_name: str,
    score_threshold: float,
) -> list[WebDocument]:
    """Provider 응답 1건을 WebDocument 목록으로 정규화한다.

    Responses API provider 는 인용(url_citation) 단위로 결과를 주므로 문서 1건 =
    인용된 URL 1건이며, content 는 그 URL 이 뒷받침하는 본문 구간이다. Tavily 는 검색
    결과 1건이 곧 문서 1건이다. score 기준은 provider 마다 달라 각자의 임계값을 쓴다.

    Args:
        payload: provider.search() 응답. `results`(문서 목록)와 `answer`(요약 본문)를 읽는다.
        query: 이 응답을 만든 검색 질의. 인용 없는 요약 문서의 제목으로도 쓴다.
        provider_name: 응답을 만든 provider 키(예: "responses", "tavily").
        score_threshold: 이 값보다 score 가 낮은 결과는 버린다.

    """
    answer = str(payload.get("answer") or "").strip()
    documents: list[WebDocument] = []

    for item in payload.get("results") or []:
        url = str(item.get("url") or "").strip()
        if not url:
            continue
        score = float(item.get("score") or 0.0)
        if score < score_threshold:
            continue
        documents.append(
            WebDocument(
                url=url,
                title=str(item.get("title") or "").strip(),
                content=str(item.get("content") or "").strip(),
                # Responses provider 는 발행일을 주지 않는다. Tavily 는 줄 때만 채워진다.
                published_at=str(item.get("published_date") or "").strip(),
                source_name=_source_name(url),
                score=score,
                provider=provider_name,
            ),
        )

    if not documents and answer:
        # 인용 없이 본문만 온 경우. 출처 없는 요약이라도 남겨 뒷단이 빈손이 되지 않게 한다.
        logger.warning(
            f"[NODE][search_web] NO_CITATION | provider={provider_name} | query={query!r} | answer_len={len(answer)}",
        )
        documents.append(
            WebDocument(title=query, content=answer, source_name="web_search", provider=provider_name),
        )
    return documents


def _interleave(groups: list[list[WebDocument]]) -> list[WebDocument]:
    """(질의 x provider) 그룹에서 한 건씩 번갈아 뽑아 하나의 목록으로 만든다.

    그냥 이어 붙이면 결과를 많이 주는 provider 하나가 MAX_WEB_DOCUMENTS 를 독점해
    다른 provider 결과가 통째로 잘린다. 라운드로빈으로 섞어 모든 그룹이 상한 안에
    최소 1건씩 들어가게 한다.

    Args:
        groups: (질의 x provider) 검색 1건마다의 문서 목록. 앞선 그룹이 우선순위가 높다.

    """
    merged: list[WebDocument] = []
    for row in zip_longest(*groups):
        merged.extend(document for document in row if document is not None)
    return merged


def _dedup_documents(documents: list[WebDocument]) -> list[WebDocument]:
    """URL 기준 dedup. 앞선 항목이 곧 우선순위이므로 먼저 찾은 문서를 남긴다.

    같은 URL 을 두 provider 가 함께 찾는 경우가 흔하며, 이때 먼저 나온 provider 의
    문서가 살아남는다. provider 간 중복률은 검색 품질 판단에 쓰이므로 어느 쪽이
    남고 어느 쪽이 버려졌는지 DEBUG 로 남긴다.

    Args:
        documents: 우선순위 순으로 정렬된 문서 목록. URL 이 없으면 제목으로 비교한다.

    """
    kept_by_key: dict[str, str] = {}
    deduped: list[WebDocument] = []
    for document in documents:
        key = document.url or f"#{document.title}"
        kept_provider = kept_by_key.get(key)
        if kept_provider is not None:
            logger.debug(
                f"[NODE][search_web] DUPLICATE | kept={kept_provider} | dropped={document.provider} | url={key}",
            )
            continue
        kept_by_key[key] = document.provider
        deduped.append(document)
    return deduped


def _branch_error(message: str) -> dict[str, Any]:
    """오류 사유만 담은 state 업데이트를 만든다(이미 수집한 다른 토픽 문서는 건드리지 않음).

    Args:
        message: branch_errors 에 남길 오류 설명.

    """
    return {"branch_errors": [BranchError(stage="search_web", message=message)]}


def _provider_overrides(provider: WebSearchProvider, include_domains: list[str] | None) -> dict[str, Any]:
    """검색 1건에 넘길 provider 별 호출 단위 override 를 만든다.

    Responses API 웹 검색은 질의 1건 안에서 모델이 검색을 반복하는 에이전트 루프라 반복 횟수와
    reasoning effort 를 이 flow 에서만 제한한다. Tavily 는 남은 kwargs 를 요청 바디로 그대로 보내므로
    Responses 전용 옵션을 넘기지 않는다.
    """
    overrides: dict[str, Any] = {} if include_domains is None else {"include_domains": include_domains}
    if isinstance(provider, ResponsesWebSearchProvider):
        overrides["max_tool_calls"] = WEB_SEARCH_MAX_TOOL_CALLS
        overrides["reasoning_effort"] = WEB_SEARCH_REASONING_EFFORT
    return overrides


# 검색 범위 라벨(로그용). registry: 공식·1차 출처 도메인 제한, open: 도메인 제한 없음.
_SCOPE_REGISTRY = "registry"
_SCOPE_OPEN = "open"


class _SearchOutcome(NamedTuple):
    """(질의 x provider) 검색 1건의 결과. 어느 토픽·provider 산출물인지 끝까지 붙여 다닌다."""

    topic_key: str
    query: str
    provider_name: str
    scope: str
    documents: list[WebDocument]
    raw_count: int
    error: BaseException | None


async def _search_one(
    *,
    topic_key: str,
    provider_name: str,
    provider: WebSearchProvider,
    query: str,
    date_from: str | None,
    date_to: str | None,
    trace_context: TraceContext | None,
    include_domains: list[str] | None,
) -> _SearchOutcome:
    """질의 1건을 provider 1개로 검색한다.

    provider 별 성능·품질을 로그만으로 비교할 수 있도록 소요 시간, 원본 결과 수,
    임계값 통과 수를 검색 단위로 남긴다. 실패는 여기서 삼켜 나머지 검색을 살린다.

    Args:
        topic_key: 이 질의가 속한 토픽. 로그와 WebDocument.topic_key 에 남긴다.
        provider_name: provider 키. 로그와 WebDocument.provider 에 남긴다.
        provider: 실제 검색을 수행할 provider 인스턴스.
        query: 검색 질의.
        date_from: 조회 시작일(YYYY-MM-DD). None 이면 제한 없음.
        date_to: 조회 종료일(YYYY-MM-DD). None 이면 제한 없음.
        trace_context: 요청 단위 trace context. 지원하는 provider 만 추적 헤더로 쓴다.
        include_domains: 검색을 제한할 도메인 목록. None 이면 provider 기본 설정
            (settings 의 include_domains)을 그대로 쓴다.

    """
    scope = _SCOPE_OPEN if include_domains is None else _SCOPE_REGISTRY
    overrides = _provider_overrides(provider, include_domains)
    started_at = time.perf_counter()
    try:
        payload = await provider.search(query, date_from, date_to, trace_context=trace_context, **overrides)
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        logger.warning(
            f"[NODE][search_web] SEARCH_FAILED | topic={topic_key} | provider={provider_name} | scope={scope} "
            f"| query={query!r} | elapsed={elapsed_ms}ms | error={exc!r}",
        )
        return _SearchOutcome(topic_key, query, provider_name, scope, [], 0, exc)

    elapsed_ms = int((time.perf_counter() - started_at) * 1000)
    raw_count = len(payload.get("results") or [])
    documents = [
        document.model_copy(update={"topic_key": topic_key})
        for document in _to_documents(
            payload,
            query=query,
            provider_name=provider_name,
            score_threshold=provider.score_threshold,
        )
    ]
    logger.info(
        f"[NODE][search_web] SEARCH_DONE | topic={topic_key} | provider={provider_name} | scope={scope} "
        f"| query={query!r} "
        f"| elapsed={elapsed_ms}ms | results={raw_count} | kept={len(documents)} "
        f"| threshold={provider.score_threshold}",
    )
    return _SearchOutcome(topic_key, query, provider_name, scope, documents, raw_count, None)


async def _search_all(
    *,
    queries: list[tuple[str, str]],
    providers: list[tuple[str, WebSearchProvider]],
    date_from: str | None,
    date_to: str | None,
    trace_context: TraceContext | None,
    include_domains: list[str] | None,
) -> list[_SearchOutcome]:
    """(토픽, 질의) x provider 전부를 같은 검색 범위로 동시에 검색한다.

    질의 우선, provider 차순. 뒤의 라운드로빈 병합이 이 순서를 우선순위로 쓴다.
    질의별·provider별 검색은 서로 독립이다. 동시 실행 상한은 커넥터의 세마포어가 관리한다.

    Args:
        queries: (topic_key, 질의) 목록. 토픽 안에서 질의는 중복 제거되어 있다.
        providers: (provider 키, provider 인스턴스) 목록. 나열 순서가 병합 우선순위다.
        date_from: 조회 시작일(YYYY-MM-DD). None 이면 제한 없음.
        date_to: 조회 종료일(YYYY-MM-DD). None 이면 제한 없음.
        trace_context: 요청 단위 trace context.
        include_domains: 모든 검색에 공통으로 적용할 도메인 목록. None 이면 도메인 제한 없음.

    """
    return list(
        await asyncio.gather(
            *(
                _search_one(
                    topic_key=topic_key,
                    provider_name=provider_name,
                    provider=provider,
                    query=query,
                    date_from=date_from,
                    date_to=date_to,
                    trace_context=trace_context,
                    include_domains=include_domains,
                )
                for topic_key, query in queries
                for provider_name, provider in providers
            ),
        ),
    )


def _topics_without_documents(outcomes: list[_SearchOutcome], topic_keys: list[str]) -> list[str]:
    """채택 가능한 문서가 한 건도 없는 토픽을 고른다(순서 유지).

    Args:
        outcomes: _search_all 이 돌려준 검색 결과 목록.
        topic_keys: 이번 검색 패스의 토픽 목록.

    """
    found = {outcome.topic_key for outcome in outcomes if outcome.documents}
    return [topic_key for topic_key in topic_keys if topic_key not in found]


def _topic_queries(topics: list[SearchTopic]) -> list[tuple[str, str]]:
    """토픽별 web_queries 를 (topic_key, 질의) 목록으로 편다. 중복 제거는 토픽 안에서만 한다."""
    return [(topic.topic_key, query) for topic in topics for query in _dedup_queries(list(topic.web_queries))]


def _select_documents(outcomes: list[_SearchOutcome], topic_keys: list[str]) -> list[WebDocument]:
    """토픽마다 provider 결과를 라운드로빈으로 섞고 URL dedup 후 MAX_WEB_DOCUMENTS 로 자른다.

    상한을 토픽 안에서 적용해, 결과가 많은 토픽이 다른 토픽 문서를 밀어내지 않게 한다.
    """
    selected: list[WebDocument] = []
    for topic_key in topic_keys:
        groups = [outcome.documents for outcome in outcomes if outcome.topic_key == topic_key]
        selected.extend(_dedup_documents(_interleave(groups))[:MAX_WEB_DOCUMENTS])
    return selected


@log_node
async def search_web(
    state: GenerateFromQueryState,
    runtime: Runtime[TraceContext] | None = None,
) -> dict[str, Any]:
    """토픽별 web_queries 를 설정된 provider 전부로 검색해 state.evidences 에 근거(T1-W1 …)로 덧붙인다.

    웹 검색은 외부 의존이므로 실패해도 flow를 중단하지 않고 branch_errors에 남긴다.
    provider 한쪽만 실패하면 나머지 provider 결과로 계속 진행하고, 관련 근거가 없는 토픽은
    summarize_topics 가 반대 분기로 1회 폴백한다.
    폴백 패스(pending_fallback)에서는 재검색 대상 토픽만 검색해 기존 결과 뒤에 덧붙인다.

    1차로 source registry 도메인만 검색하고, 채택할 문서가 없는 토픽만 도메인 제한 없이 재검색한다.

    Args:
        state: flow state. query_plan 의 topics, date_from, date_to 를 읽는다.
        runtime: LangGraph runtime. context 의 TraceContext 를 provider 추적 헤더로 넘긴다.

    """
    plan = state.query_plan
    topics = state.topics_to_search()
    queries = _topic_queries(topics)
    if plan is None or not queries:
        logger.warning("[NODE][search_web] NO_QUERIES")
        return _branch_error("검색할 웹 질의가 없습니다.")

    topic_keys = [topic.topic_key for topic in topics]
    date_from, date_to = _search_period(plan)

    domains = registry_domains()

    try:
        providers = WebSearchProviderFactory.create_all_from_settings()
        search_kwargs: dict[str, Any] = {
            "providers": providers,
            "date_from": date_from,
            "date_to": date_to,
            "trace_context": runtime.context if runtime is not None else None,
        }
        # registry 를 읽지 못해 도메인이 비었으면 곧바로 제한 없는 검색이 된다.
        outcomes = await _search_all(queries=queries, **search_kwargs, include_domains=domains or None)
        empty_topics = _topics_without_documents(outcomes, topic_keys) if domains else []
        if empty_topics:
            logger.warning(
                f"[NODE][search_web] REGISTRY_EMPTY | topics={empty_topics} | domains={len(domains)} "
                "| 공식·1차 출처에서 근거를 찾지 못한 토픽만 도메인 제한 없이 재검색합니다.",
            )
            retry_queries = [(topic_key, query) for topic_key, query in queries if topic_key in empty_topics]
            outcomes += await _search_all(queries=retry_queries, **search_kwargs, include_domains=None)
    except Exception as exc:
        # 외부 의존의 예상 못 한 실패로 전체 flow가 중단되지 않게 한다.
        logger.exception(f"[NODE][search_web] UNEXPECTED_FAILED | queries={queries}")
        return _branch_error(f"웹 검색 중 오류가 발생했습니다: {exc!r}")

    failures = [outcome for outcome in outcomes if outcome.error is not None]
    if len(failures) == len(outcomes):
        failed_by_provider = Counter(outcome.provider_name for outcome in failures)
        return _branch_error(
            f"웹 검색 {len(failures)}건이 모두 실패했습니다(provider별 {dict(failed_by_provider)}). "
            f"첫 오류: {failures[0].error!r}",
        )

    successes = [outcome for outcome in outcomes if outcome.error is None]
    deduped = _select_documents(successes, topic_keys)

    # provider별 수집량과 최종 채택량을 나눠 남긴다. 둘의 차이가 곧 중복·상한으로 잘린 양이다.
    searched: Counter[str] = Counter()
    collected: Counter[str] = Counter()
    scopes = sorted({outcome.scope for outcome in outcomes})
    for outcome in successes:
        searched[outcome.provider_name] += outcome.raw_count
        collected[outcome.provider_name] += len(outcome.documents)
    adopted = Counter(document.provider for document in deduped)
    failed_by_provider = Counter(outcome.provider_name for outcome in failures)

    logger.info(
        f"[NODE][search_web] DONE | topics={topic_keys} | fallback={state.pending_fallback} "
        f"| queries={len(queries)} | providers={[name for name, _ in providers]} "
        f"| scopes={scopes} "
        f"| searches={len(outcomes)} | failed={len(failures)}{f' {dict(failed_by_provider)}' if failures else ''} "
        f"| searched={dict(searched)} | collected={dict(collected)} | adopted={dict(adopted)} "
        f"| documents={len(deduped)} | by_topic={dict(Counter(document.topic_key for document in deduped))}",
    )
    for index, document in enumerate(deduped, start=1):
        logger.debug(
            f"[NODE][search_web] DOC | {document.topic_key} #{index} | provider={document.provider} "
            f"| score={document.score:.3f} "
            f"| source={document.source_name} | url={document.url}",
        )
    # evidences 는 누적 reducer 라 반환한 근거가 기존 근거 뒤에 덧붙는다(폴백 패스도 동일).
    return {"evidences": web_documents_to_evidences(deduped, state.evidences)}
