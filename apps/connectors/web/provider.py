"""OpenAI Responses API의 내장 ``web_search`` 툴을 사용하는 web search provider.

역할:
- Tavily 처럼 "검색 결과 목록"을 받는 대신, 모델이 직접 웹 검색을 수행하고
  근거(url_citation)가 달린 답변 또는 구조화된 결과를 반환하도록 한다.
- 사용자의 가정을 구체화하기 위한 조사(시나리오 분기 항목 + 근거 수집)에 사용한다.

제공 기능:
- ``search()``: 자유 텍스트 답변 + 인용 URL 목록을 Tavily 유사 dict 형태로 반환
- ``search_structured()``: Pydantic 스키마로 strict JSON 강제 추출 + 인용/검색어 동반 반환

주의:
- Responses ``web_search`` 툴에는 Tavily 의 ``start_date``/``end_date``/``exclude_domains``
  같은 하드 필터가 없다. 기간·제외 도메인은 입력 프롬프트의 제약 조건으로 전달되는
  soft constraint 이며, ``include_domains`` 만 툴의 ``filters.allowed_domains`` 로 전달된다.
- 검색 결과의 relevance score 가 제공되지 않으므로 모든 인용은 동일 score(1.0)를 갖는다.
"""

from __future__ import annotations

import asyncio
import re
import time
from typing import Any, Literal

import httpx
from openai import APITimeoutError, AsyncOpenAI
from pydantic import BaseModel, Field, ValidationError

from apps.common.configs.config import get_settings
from apps.common.exceptions.custom import MIBaseError
from apps.common.logging.decorators import log_connector
from apps.common.logging.logger_config import logger
from apps.common.runtime.runtime import (
    ensure_runtime_context_ready,
    get_http_semaphore,
    get_llm_semaphore,
)
from apps.common.runtime.usage_context import accumulate_usage
from apps.common.tracing.context import TraceContext, build_aip_headers
from apps.common.values.error_codes import ErrorCode
from apps.common.values.llm_usage import LLMUsageModel
from apps.connectors.web.base import WebSearchProvider


SearchContextSize = Literal["low", "medium", "high"]
ReasoningEffortOption = Literal["none", "minimal", "low", "medium", "high", "xhigh"]

DEFAULT_CITATION_SCORE = 1.0

# 답변에 삽입된 인용 링크. 괄호로 감싼 형태 "([eia.gov](https://...))" 와 맨 링크 "[eia.gov](https://...)" 모두.
_CITATION_LINK_PATTERN = re.compile(r"\(?\[[^\]]*\]\(https?://[^)\s]*\)\)?")
# 인용 1건의 본문 구간 상한(표 한 행·문단이 길게 이어지는 경우 링크 직전 쪽을 남긴다).
_MAX_PASSAGE_CHARS = 600
# URL 1건에 모은 인용 구간 전체 상한.
_MAX_SNIPPET_CHARS = 1500

DEFAULT_INSTRUCTIONS = """
당신은 웹 검색으로 근거를 수집하는 조사 분석가다.

<조사 원칙>
1. 반드시 web_search 툴을 사용하고, 검색 스니펫만으로 단정하지 말고 원문을 확인한다.
2. 정부·기상기관·에너지기관·거래소·계통운영자·기업 공시 등 1차 자료를 우선한다.
3. 각 주장은 출처 URL 과 연결한다. 하나의 출처가 지지하지 않는 내용을 그 출처에 귀속하지 않는다.
4. 출처의 발행일, 전망 기준일, 전망 대상 기간을 구분해서 기술한다.
5. 수치·날짜·URL 을 꾸며내지 않는다. 근거가 없거나 충돌하면 추정하지 말고 그 사실을 밝힌다.
6. 사용자가 제공한 컨텍스트는 입력 사실일 뿐 검증된 사실이 아니다. 웹으로 검증된 사실과 구분해 서술한다.
</조사 원칙>
""".strip()


class WebSearchCitation(BaseModel):
    """Responses API 응답의 ``url_citation`` annotation 1건."""

    title: str = Field(default="", description="인용 문서 제목")
    url: str = Field(description="인용 문서 URL")
    snippet: str = Field(default="", description="해당 인용이 뒷받침하는 본문 구간")


class WebSearchStructuredResult[T: BaseModel](BaseModel):
    """구조화 검색 결과와 근거·사용량 메타데이터."""

    result: T
    citations: list[WebSearchCitation] = Field(default_factory=list)
    search_queries: list[str] = Field(default_factory=list)
    usage: LLMUsageModel | None = None
    model: str | None = None
    response_id: str | None = None
    response_time: float | None = None


def _get(obj: Any, key: str, default: Any = None) -> Any:  # noqa: ANN401
    """SDK 객체와 dict 응답을 동일하게 다루기 위한 접근자."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _output_items(response: Any) -> list[Any]:  # noqa: ANN401
    return list(_get(response, "output") or [])


def _response_text(response: Any) -> str:  # noqa: ANN401
    text = _get(response, "output_text")
    if isinstance(text, str) and text:
        return text

    chunks: list[str] = []
    for item in _output_items(response):
        if _get(item, "type") != "message":
            continue
        chunks.extend(
            _get(block, "text") or "" for block in _get(item, "content") or [] if _get(block, "type") == "output_text"
        )
    return "".join(chunks)


def _collect_search_queries(response: Any) -> list[str]:  # noqa: ANN401
    queries: list[str] = []
    for item in _output_items(response):
        if _get(item, "type") != "web_search_call":
            continue
        action = _get(item, "action") or {}
        candidates = [*(_get(action, "queries") or []), _get(action, "query")]
        for candidate in candidates:
            if isinstance(candidate, str) and candidate and candidate not in queries:
                queries.append(candidate)
    return queries


def _clean_passage(text: str) -> str:
    """인용 구간에서 마크다운 링크·강조·표 구분자를 걷어내고 공백을 정리한다."""
    text = _CITATION_LINK_PATTERN.sub(" ", text)
    text = text.replace("**", "").replace("|", " ")
    return " ".join(text.split()).lstrip("-*# ").strip()


def _cited_passage(text: str, start_index: int) -> str:
    """인용 링크가 뒷받침하는 본문 구간을 잡는다.

    ``url_citation`` 의 start/end 는 사실 문장이 아니라 답변에 삽입된 링크(``([eia.gov](https://...))``)
    자체를 가리킨다. 사실은 링크 바로 앞에 있으므로, 같은 줄에서 링크 앞까지를 읽되 앞선 다른 인용 링크로
    나뉜 조각 중 마지막 조각(이 링크 직전 문장)을 쓴다. 링크가 연달아 붙어 직전 조각이 비면 그 앞 조각을 쓴다.
    """
    line_start = text.rfind("\n", 0, start_index) + 1
    pieces = [_clean_passage(piece) for piece in _CITATION_LINK_PATTERN.split(text[line_start:start_index])]
    passage = next((piece for piece in reversed(pieces) if piece), "")
    return passage[-_MAX_PASSAGE_CHARS:]


def _collect_citations(response: Any, *, max_results: int) -> list[WebSearchCitation]:  # noqa: ANN401
    """답변의 url_citation 을 URL 단위로 모은다.

    같은 URL 이 여러 번 인용되면 인용 구간을 모두 snippet 에 합친다(문서 1건이 뒷받침하는 사실 전부).
    ``max_results`` 는 URL 수 상한이다.
    """
    passages_by_url: dict[str, list[str]] = {}
    titles: dict[str, str] = {}

    for item in _output_items(response):
        if _get(item, "type") != "message":
            continue
        for block in _get(item, "content") or []:
            text = _get(block, "text") or ""
            for annotation in _get(block, "annotations") or []:
                if _get(annotation, "type") != "url_citation":
                    continue
                url = _get(annotation, "url")
                if not url:
                    continue
                passages = passages_by_url.setdefault(url, [])
                titles.setdefault(url, _get(annotation, "title") or "")
                start_index = _get(annotation, "start_index")
                passage = _cited_passage(text, start_index) if isinstance(start_index, int) else ""
                if passage and passage not in passages:
                    passages.append(passage)

    citations = [
        WebSearchCitation(title=titles[url], url=url, snippet="\n".join(passages)[:_MAX_SNIPPET_CHARS])
        for url, passages in passages_by_url.items()
    ]
    if max_results > 0:
        return citations[:max_results]
    return citations


def _usage_from_response(raw_usage: Any) -> LLMUsageModel | None:  # noqa: ANN401
    """Responses API usage(input/output tokens)를 공통 usage 모델로 변환."""
    if raw_usage is None:
        return None

    model_dump = getattr(raw_usage, "model_dump", None)
    payload = model_dump() if callable(model_dump) else dict(raw_usage)
    prompt_tokens = payload.get("input_tokens", payload.get("prompt_tokens", 0)) or 0
    completion_tokens = payload.get("output_tokens", payload.get("completion_tokens", 0)) or 0
    total_tokens = payload.get("total_tokens", 0) or (prompt_tokens + completion_tokens)
    return LLMUsageModel(
        prompt_tokens=int(prompt_tokens),
        completion_tokens=int(completion_tokens),
        total_tokens=int(total_tokens),
    )


def _build_input(
    query: str,
    *,
    start_date: str | None,
    end_date: str | None,
    exclude_domains: list[str] | None,
    context: str | None,
) -> str:
    lines = [f"검색 질의: {query}"]
    if start_date or end_date:
        lines.append(
            f"대상 기간: {start_date or '제한 없음'} ~ {end_date or '제한 없음'} "
            "(해당 기간에 발행된 자료를 우선하고, 기간 밖 자료를 쓰면 그 사실을 본문에 밝힌다)",
        )
    if exclude_domains:
        lines.append(f"제외 도메인: {', '.join(exclude_domains)} (해당 도메인 자료는 근거로 사용하지 않는다)")
    if context:
        lines.append(f"추가 컨텍스트(사용자 입력이며 검증된 사실이 아님): {context}")
    return "\n".join(lines)


class ResponsesWebSearchProvider(WebSearchProvider):
    """OpenAI Responses API + ``web_search`` 툴 기반 provider.

    Example:
        provider = ResponsesWebSearchProvider(search_context_size="high")
        result = await provider.search("2026년 유럽 한파 전망", start_date="2025-10-01")
        detail = await provider.search_structured(ColdWaveForecast, "2026년 유럽 한파 전망")

    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str | None = None,
        model: str | None = None,
        instructions: str = DEFAULT_INSTRUCTIONS,
        search_context_size: SearchContextSize = "medium",
        max_results: int = 1,
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
        score_threshold: float = 0.0,
        reasoning_effort: ReasoningEffortOption | None = "medium",
        tool_choice: str = "required",
        max_tool_calls: int | None = None,
        timeout_sec: float | None = None,
        max_retries: int = 2,
        user_location: dict[str, Any] | None = None,
    ) -> None:
        """설정값을 생략하면 ``get_settings()`` 의 model endpoint/key/deployment 를 사용한다."""
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.instructions = instructions
        self.search_context_size = search_context_size
        self.max_results = max_results
        self.include_domains = include_domains or []
        self.exclude_domains = exclude_domains or []
        self._score_threshold = score_threshold
        self.reasoning_effort = reasoning_effort
        self.tool_choice = tool_choice
        self.max_tool_calls = max_tool_calls
        self.timeout_sec = timeout_sec
        self.max_retries = max_retries
        self.user_location = user_location

    @property
    def score_threshold(self) -> float:
        return self._score_threshold

    def _resolve_model(self, override: str | None = None) -> str:
        return override or self.model or get_settings().model_api_deployment_name

    def _create_client(self) -> tuple[AsyncOpenAI, httpx.AsyncClient]:
        cfg = get_settings()
        if self.base_url and not self.api_key:
            # 별도 엔드포인트를 쓰면서 전용 키가 없으면 LLM 게이트웨이 키로 폴백해 401 이 된다.
            logger.warning(
                "[CONNECTOR][WEB][responses_web_search] MISSING_API_KEY | "
                f"base_url={self.base_url} | WEB_SEARCH_API_KEY 가 비어 있어 model_api_key 로 폴백합니다.",
            )
        http_client = httpx.AsyncClient(
            verify=cfg.http_verify,
            http2=cfg.http2,
            timeout=httpx.Timeout(
                timeout=self.timeout_sec or cfg.llm_timeout_sec,
                connect=cfg.http_connect_timeout,
            ),
            limits=httpx.Limits(
                max_connections=cfg.http_max_connection,
                max_keepalive_connections=cfg.http_max_keepalive,
            ),
        )
        return (
            AsyncOpenAI(
                base_url=self.base_url or cfg.model_endpoint,
                api_key=self.api_key or cfg.model_api_key,
                http_client=http_client,
                max_retries=self.max_retries,
            ),
            http_client,
        )

    def _build_tool(self, overrides: dict[str, Any]) -> dict[str, Any]:
        tool: dict[str, Any] = {
            "type": "web_search",
            "search_context_size": overrides.pop("search_context_size", self.search_context_size),
        }
        include_domains = overrides.pop("include_domains", self.include_domains)
        if include_domains:
            tool["filters"] = {"allowed_domains": list(include_domains)}
        user_location = overrides.pop("user_location", self.user_location)
        if user_location:
            tool["user_location"] = user_location
        return tool

    def _build_request_kwargs(
        self,
        *,
        query: str,
        start_date: str | None,
        end_date: str | None,
        model: str,
        trace_context: TraceContext | None,
        overrides: dict[str, Any],
    ) -> dict[str, Any]:
        """알려진 옵션은 pop 으로 소비하고, 남은 kwargs 는 Responses API 로 그대로 전달한다."""
        tool = self._build_tool(overrides)
        request_kwargs: dict[str, Any] = {
            "model": model,
            "instructions": overrides.pop("instructions", self.instructions),
            "input": _build_input(
                query,
                start_date=start_date,
                end_date=end_date,
                exclude_domains=overrides.pop("exclude_domains", self.exclude_domains),
                context=overrides.pop("context", None),
            ),
            "tools": [tool],
            "tool_choice": overrides.pop("tool_choice", self.tool_choice),
        }

        reasoning_effort = overrides.pop("reasoning_effort", self.reasoning_effort)
        if reasoning_effort:
            request_kwargs["reasoning"] = {"effort": reasoning_effort}

        max_tool_calls = overrides.pop("max_tool_calls", self.max_tool_calls)
        if max_tool_calls:
            request_kwargs["max_tool_calls"] = max_tool_calls

        if trace_context is not None:
            request_kwargs["extra_headers"] = build_aip_headers(trace_context)

        request_kwargs.update(overrides)
        return request_kwargs

    async def _invoke(
        self,
        *,
        query: str,
        start_date: str | None,
        end_date: str | None,
        output_schema: type[BaseModel] | None,
        trace_context: TraceContext | None,
        overrides: dict[str, Any],
    ) -> tuple[Any, str, float]:
        await ensure_runtime_context_ready()

        model = self._resolve_model(overrides.pop("model", None))
        max_results = int(overrides.pop("max_results", self.max_results))
        # TLS/certificate setup is synchronous; keep concurrent searches off the event-loop thread.
        client, http_client = await asyncio.to_thread(self._create_client)
        request_kwargs = self._build_request_kwargs(
            query=query,
            start_date=start_date,
            end_date=end_date,
            model=model,
            trace_context=trace_context,
            overrides=overrides,
        )

        llm_sem = get_llm_semaphore()
        http_sem = get_http_semaphore()
        started_at = time.perf_counter()
        try:
            async with llm_sem, http_sem:
                if output_schema is not None:
                    response = await client.responses.parse(text_format=output_schema, **request_kwargs)
                else:
                    response = await client.responses.create(**request_kwargs)
        except APITimeoutError as exc:
            raise MIBaseError(ErrorCode.LLM_RESPONSE_TIMEOUT, detail=f"web_search query={query!r}") from exc
        except MIBaseError:
            raise
        except Exception as exc:
            raise MIBaseError(ErrorCode.LLM_INVOCATION_ERROR, detail=str(exc)) from exc
        finally:
            await http_client.aclose()

        elapsed = time.perf_counter() - started_at
        self._log_response(response, query=query, model=model, elapsed=elapsed)
        accumulate_usage(_usage_from_response(_get(response, "usage")))
        # max_results 는 인용 목록 절단에만 쓰이므로 호출 이후 단계로 되돌려준다.
        overrides["max_results"] = max_results
        return response, model, elapsed

    def _log_response(self, response: Any, *, query: str, model: str, elapsed: float) -> None:  # noqa: ANN401
        status = _get(response, "status")
        search_calls = sum(1 for item in _output_items(response) if _get(item, "type") == "web_search_call")
        if status and status != "completed":
            logger.warning(
                f"[CONNECTOR][WEB][responses_web_search] INCOMPLETE | status={status} | "
                f"query={query!r} | detail={_get(response, 'incomplete_details')!r}",
            )
        if search_calls == 0:
            logger.warning(
                f"[CONNECTOR][WEB][responses_web_search] NO_SEARCH_CALL | query={query!r} | model={model}",
            )
        logger.debug(
            f"[CONNECTOR][WEB][responses_web_search] DONE | query={query!r} | model={model} | "
            f"search_calls={search_calls} | elapsed={int(elapsed * 1000)}ms",
        )

    @log_connector(connector_type="WEB", name="responses_web_search", log_input=True, log_output=False)
    async def search(
        self,
        query: str,
        start_date: str | None = None,
        end_date: str | None = None,
        *,
        trace_context: TraceContext | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """웹 검색 후 근거가 달린 자유 텍스트 답변을 반환한다.

        Args:
            query: 검색 질의
            start_date: 자료 발행 시작일(YYYY-MM-DD). 프롬프트 제약으로 전달되는 soft constraint.
            end_date: 자료 발행 종료일(YYYY-MM-DD). 프롬프트 제약으로 전달되는 soft constraint.
            trace_context: 요청 단위 trace context. AIP 추적 헤더로 변환해 전달한다.
            **kwargs: ``model``, ``instructions``, ``context``, ``search_context_size``,
                ``max_results``, ``include_domains``, ``exclude_domains``, ``tool_choice``,
                ``reasoning_effort``, ``max_tool_calls``, ``user_location``.
                그 외 키는 Responses API 로 그대로 전달된다.

        Returns:
            ``answer``(본문), ``results``(인용 URL 목록), ``search_queries``, ``usage`` 등을 담은 dict

        """
        overrides = dict(kwargs)
        response, model, elapsed = await self._invoke(
            query=query,
            start_date=start_date,
            end_date=end_date,
            output_schema=None,
            trace_context=trace_context,
            overrides=overrides,
        )

        citations = _collect_citations(response, max_results=int(overrides["max_results"]))
        usage = _usage_from_response(_get(response, "usage"))
        return {
            "query": query,
            "answer": _response_text(response).strip(),
            "results": [
                {
                    "title": citation.title,
                    "url": citation.url,
                    "content": citation.snippet,
                    "score": DEFAULT_CITATION_SCORE,
                }
                for citation in citations
            ],
            "search_queries": _collect_search_queries(response),
            "response_id": _get(response, "id"),
            "model": model,
            "status": _get(response, "status"),
            "usage": usage.model_dump() if usage else None,
            "response_time": round(elapsed, 3),
        }

    @log_connector(connector_type="WEB", name="responses_web_search", log_input=True, log_output=False)
    async def search_structured[T: BaseModel](
        self,
        output_schema: type[T],
        query: str,
        start_date: str | None = None,
        end_date: str | None = None,
        *,
        trace_context: TraceContext | None = None,
        **kwargs: Any,
    ) -> WebSearchStructuredResult[T]:
        """웹 검색 결과를 ``output_schema`` 로 strict JSON 추출한다.

        Args:
            output_schema: 추출 스키마. Responses API 의 strict json_schema 로 변환된다.
            query: 검색 질의
            start_date: 자료 발행 시작일(YYYY-MM-DD)
            end_date: 자료 발행 종료일(YYYY-MM-DD)
            trace_context: 요청 단위 trace context. AIP 추적 헤더로 변환해 전달한다.
            **kwargs: ``search()`` 와 동일

        Returns:
            파싱된 결과와 인용·검색어·usage 메타데이터

        """
        overrides = dict(kwargs)
        response, model, elapsed = await self._invoke(
            query=query,
            start_date=start_date,
            end_date=end_date,
            output_schema=output_schema,
            trace_context=trace_context,
            overrides=overrides,
        )

        parsed = _get(response, "output_parsed")
        if parsed is None:
            detail = f"web_search structured output이 비어 있습니다. schema={output_schema.__name__}"
            raise MIBaseError(ErrorCode.LLM_INVALID_RESPONSE_ERROR, detail=detail)
        if not isinstance(parsed, output_schema):
            try:
                parsed = output_schema.model_validate(parsed)
            except ValidationError as exc:
                raise MIBaseError(ErrorCode.LLM_INVALID_RESPONSE_ERROR, detail=str(exc)) from exc

        usage = _usage_from_response(_get(response, "usage"))
        return WebSearchStructuredResult[T](
            result=parsed,
            citations=_collect_citations(response, max_results=int(overrides["max_results"])),
            search_queries=_collect_search_queries(response),
            usage=usage,
            model=model,
            response_id=_get(response, "id"),
            response_time=round(elapsed, 3),
        )
