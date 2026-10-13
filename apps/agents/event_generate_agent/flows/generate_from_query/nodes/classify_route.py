"""classify_route 노드 — 사용자 입력 문장의 근거 수집 분기를 LLM으로 판단한다.

분기 판단은 키워드 매칭이 아니라 문장 전체 의도에 대한 LLM 판단으로 한다.
검색 질의 구성은 다음 노드(plan_search)가 이 판단 결과를 받아 수행한다.
"""

from __future__ import annotations

from typing import Any

from langgraph.runtime import Runtime

from apps.agents.event_generate_agent.constants import LIGHT_REASONING_EFFORT
from apps.agents.event_generate_agent.flows.generate_from_query.state import GenerateFromQueryState
from apps.agents.event_generate_agent.prompts.query_analysis import route_classification as route_prompt
from apps.common.configs.config import get_settings
from apps.common.exceptions.custom import MIBaseError
from apps.common.logging.decorators import log_node
from apps.common.logging.logger_config import logger
from apps.common.tracing.context import TraceContext
from apps.common.values.enums import ModelPreference
from apps.common.values.error_codes import ErrorCode


@log_node
async def classify_route(
    state: GenerateFromQueryState,
    runtime: Runtime[TraceContext] | None = None,
) -> dict[str, Any]:
    """사용자 문장 → route / route_reason."""
    from apps.connectors.llm.llm_client import invoke_llm_structured_output

    user_query = state.user_query.strip()
    if not user_query:
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="user_query를 입력해주세요")

    cfg = get_settings()
    result = await invoke_llm_structured_output(
        output_schema=route_prompt.RouteClassificationLLMOutput,
        messages=[
            {"role": "system", "content": route_prompt.SYSTEM_PROMPT},
            {"role": "user", "content": route_prompt.build_user_prompt(user_query)},
        ],
        preference=ModelPreference.SPEED,
        temperature=0.0,
        trace_context=runtime.context if runtime is not None else None,
        stream=cfg.llm_stream_enabled,
        reasoning_effort=LIGHT_REASONING_EFFORT,
    )

    output = result.result
    route_reason = output.route_reason.strip()
    logger.info(f"[NODE][classify_route] DECISION | route={output.route.value} | reason={route_reason!r}")
    return {"route": output.route, "route_reason": route_reason}
