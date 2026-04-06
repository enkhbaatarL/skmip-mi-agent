from __future__ import annotations

from collections.abc import AsyncIterator, Iterator, Sequence
import time
from typing import Any

from fastapi import HTTPException
from langchain_core.runnables import Runnable

from apps.agents.mi_agent.flows.mari_agent_adapters import to_output, to_state
from apps.agents.mi_agent.flows.mari_agent_graph import _mari_agent
from apps.agents.mi_agent.flows.mari_agent_runtime import ensure_runtime
from apps.agents.mi_agent.schemas.mari_agent_input import MariAgentInput
from apps.agents.mi_agent.schemas.mari_agent_output import MariAgentOutput
from apps.common.configs.settings import get_settings
from apps.common.exceptions.custom import MIBaseError
from apps.common.logging.logger_config import logger


class MariAgentRunnable(Runnable):
    """mi agent runnable with custom streaming events and a final complete payload."""

    def __init__(self, graph: Runnable, stream_modes: Sequence[str] | str | None = None) -> None:
        self._graph = graph
        self._stream_modes = stream_modes

    def invoke(self, input: Any, config: dict | None = None, **kwargs: Any) -> Any:
        msg = "MariAgentRunnable는 async 전용입니다. ainvoke/astream을 사용하세요."
        raise RuntimeError(msg)

    async def ainvoke(self, input: Any, config: dict | None = None, **kwargs: Any) -> Any:
        # Agent 입력 로깅
        user_query = input.user_query if hasattr(input, "user_query") else input.get("user_query", "")
        search_sources = input.search_sources if hasattr(input, "search_sources") else input.get("search_sources", [])
        logger.info(
            f"[AGENT][MariAgent] START | user_query={user_query[:100] if user_query else ''} | "
            f"search_sources={search_sources}",
        )

        t0 = time.perf_counter()
        state = to_state(input, **kwargs)
        await ensure_runtime(state, **kwargs)
        try:
            final_state = await self._graph.ainvoke(state, config=config)
        except MIBaseError as exc:
            raise HTTPException(
                status_code=500,
                detail={"error_code": exc.error_code.name, "error_message": exc.error_message},
            ) from exc
        output = to_output(final_state)

        # Agent 출력 로깅
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        summary = output.answer.analysis_summary[:100] if output.answer.analysis_summary else ""
        usage_info = (
            f"prompt={output.usage.prompt_tokens}, completion={output.usage.completion_tokens}"
            if output.usage
            else "N/A"
        )
        logger.info(
            f"[AGENT][MariAgent] END | elapsed={elapsed_ms}ms | usage={usage_info} | summary={summary}",
        )

        return output

    async def astream(self, input: Any, config: dict | None = None, **kwargs: Any) -> AsyncIterator[Any]:
        # Agent 입력 로깅
        user_query = input.user_query if hasattr(input, "user_query") else input.get("user_query", "")
        search_sources = input.search_sources if hasattr(input, "search_sources") else input.get("search_sources", [])
        logger.info(
            f"[AGENT][MariAgent] STREAM_START | user_query={user_query[:100] if user_query else ''} | "
            f"search_sources={search_sources}",
        )

        t0 = time.perf_counter()
        state = to_state(input, **kwargs)
        await ensure_runtime(state, **kwargs)

        requested_stream_mode = kwargs.pop("stream_mode", None)
        stream_modes = _normalize_stream_modes(requested_stream_mode or self._stream_modes)
        if "custom" not in stream_modes:
            stream_modes.append("custom")
        if "values" not in stream_modes:
            stream_modes.append("values")

        last_state: dict[str, Any] | None = None
        try:
            async for chunk in self._graph.astream(state, config=config, stream_mode=stream_modes):
                mode, data = _split_stream_chunk(chunk)
                if mode == "custom":
                    yield data
                    continue
                if mode == "values":
                    if isinstance(data, dict):
                        last_state = data
                    continue

                # pass through other stream modes as progress payloads
                yield {"state": "progress", "data": "chunk", "value": data}
        except MIBaseError as exc:
            raise HTTPException(
                status_code=500,
                detail={"error_code": exc.error_code.name, "error_message": exc.error_message},
            ) from exc

        if last_state is not None:
            output = to_output(last_state)
            total_latency_ms = int((time.perf_counter() - t0) * 1000)
            for event in _emit_final_events(output, total_latency_ms):
                yield event


def _emit_final_events(output: MariAgentOutput, latency_ms: int) -> Iterator[dict[str, Any]]:
    """최종 결과를 단일 SSE 이벤트로 생성합니다."""
    # Agent 출력 로깅
    summary = output.answer.analysis_summary[:100] if output.answer.analysis_summary else ""
    usage_info = (
        f"prompt={output.usage.prompt_tokens}, completion={output.usage.completion_tokens}" if output.usage else "N/A"
    )
    logger.info(
        f"[AGENT][MariAgent] STREAM_END | elapsed={latency_ms}ms | usage={usage_info} | summary={summary}",
    )

    node = "analysis"

    # segment 데이터 구성
    segment_data: dict[str, Any] = {}

    # 1. sources - 검색 출처
    sources = output.evidence.model_dump(exclude_none=True)
    if isinstance(sources.get("rdb"), dict) and not sources["rdb"].get("charts"):
        sources["rdb"].pop("charts", None)
    segment_data["sources"] = sources

    # 2. timeseries_insights - 시계열 인사이트
    if output.answer.timeseries_insights:
        segment_data["timeseries_insights"] = output.answer.timeseries_insights.model_dump(
            exclude_none=True,
        )

    # 3. chart_summaries - 차트 요약 (charts에서 생성)
    if output.evidence.rdb and output.evidence.rdb.charts:
        segment_data["chart_summaries"] = [c.model_dump() for c in output.evidence.rdb.charts]

    # 4. suggestions - 추천 질문
    segment_data["suggestions"] = output.answer.suggested_questions

    # 5. usage - 토큰 사용량 (있는 경우에만)
    if output.usage:
        segment_data["usage"] = output.usage.model_dump(exclude_none=True)

    # value: analysis_summary + content 결합
    value_parts = []
    if output.answer.analysis_summary:
        value_parts.append(output.answer.analysis_summary)
    if output.answer.content:
        value_parts.append(output.answer.content)
    combined_value = "\n\n".join(value_parts) if value_parts else ""

    # 단일 complete 이벤트로 모든 데이터 전달
    yield {
        "state": "complete",
        "data": "message",
        "node": node,
        "value": combined_value,
        "segment": segment_data,
        "latency_ms": latency_ms,
    }


def _normalize_stream_modes(stream_modes: Sequence[str] | str | None) -> list[str]:
    if stream_modes is None:
        return []
    if isinstance(stream_modes, str):
        return [stream_modes]
    return list(stream_modes)


def _split_stream_chunk(chunk: Any) -> tuple[str | None, Any]:
    if isinstance(chunk, tuple) and len(chunk) == 2 and isinstance(chunk[0], str):
        return chunk[0], chunk[1]
    return None, chunk


def build_runnable_graph(stream_modes: Sequence[str] | str | None = None) -> Runnable:
    runnable: Runnable = MariAgentRunnable(_mari_agent, stream_modes=stream_modes)
    return runnable.with_types(input_type=MariAgentInput, output_type=MariAgentOutput)


# settings에서 streaming_mode를 읽어 적용
runnable_graph: Runnable = build_runnable_graph(stream_modes=get_settings().streaming_mode)
