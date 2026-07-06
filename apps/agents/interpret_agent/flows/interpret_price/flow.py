"""interpret_price flow 조립 및 동기(sync) 실행 진입점.

API 요청에서 직접 graph를 invoke해 해석 결과를 즉시 반환한다(delivery=sync_return).
"""

from __future__ import annotations

from functools import lru_cache

from langchain_core.runnables import Runnable
from langgraph.graph import StateGraph

from apps.agents.interpret_agent.flows.interpret_price.api_schema import (
    PriceInterpretationResult,
)
from apps.agents.interpret_agent.flows.interpret_price.nodes import (
    extract_diffs,
    finalize,
    interpret_scenarios,
    load_input,
    synthesize_group,
)
from apps.agents.interpret_agent.flows.interpret_price.state import InterpretPriceState
from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode


@lru_cache(maxsize=1)
def get_compiled_graph() -> Runnable:
    builder = StateGraph(InterpretPriceState)
    builder.add_node("load_input", load_input)
    builder.add_node("extract_diffs", extract_diffs)
    builder.add_node("interpret_scenarios", interpret_scenarios)
    builder.add_node("synthesize_group", synthesize_group)
    builder.add_node("finalize", finalize)

    builder.set_entry_point("load_input")
    builder.add_edge("load_input", "extract_diffs")
    builder.add_edge("extract_diffs", "interpret_scenarios")
    builder.add_edge("interpret_scenarios", "synthesize_group")
    builder.add_edge("synthesize_group", "finalize")
    builder.set_finish_point("finalize")
    return builder.compile()


async def run_interpret_price(
    scenario_group_id: int | None,
    scenario_ids: list[str] | None = None,
) -> PriceInterpretationResult:
    state = InterpretPriceState(
        scenario_group_id=scenario_group_id,
        scenario_ids=list(scenario_ids or []),
    )
    final_state = await get_compiled_graph().ainvoke(state)
    if isinstance(final_state, InterpretPriceState):
        result = final_state.result
    elif isinstance(final_state, dict):
        result = final_state.get("result")
    else:
        result = getattr(final_state, "result", None)
    if result is None:
        raise MIBaseError(
            ErrorCode.UNKNOWN_ERROR,
            detail="해석 결과 생성에 실패했습니다.",
        )
    return result
