"""interpret_price flow 조립 및 실행 진입점(sync + async).

- 동기(sync): API 요청에서 직접 graph를 invoke해 해석 결과를 즉시 반환한다
  (delivery=sync_return). `run_interpret_price` 사용.
- 비동기(async): 요청을 즉시 접수 응답하고, 백그라운드에서 동일한 interpret_price
  graph를 실행한 뒤 결과를 콜백 URL로 POST한다(delivery=callback). model_parameter_agent
  `propose_parameters/flow.py`의 prepare + run_*_background + send_callback 패턴을 따른다.
  단, 해석 결과를 저장하는 DB row가 없으므로 processing/complete/fail row 갱신은 두지 않고
  콜백 payload에 해석 결과 전체를 실어 보낸다.
"""

from __future__ import annotations

from functools import lru_cache
import time

from langchain_core.runnables import Runnable
from langgraph.graph import StateGraph

from apps.agents.interpret_agent.flows.interpret_price.api_schema import (
    PriceInterpretationCallbackItem,
    PriceInterpretationCallbackOut,
    PriceInterpretationResult,
    ScenarioComparisonOut,
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
from apps.common.logging.logger_config import logger
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
    scenario_ids: list[int] | None = None,
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


# ---------------------------------------------------------------------------
# Async(callback) delivery
# ---------------------------------------------------------------------------


def prepare_price_interpretation(
    scenario_group_id: int,
    scenario_ids: list[int],
) -> dict[str, object]:
    """비동기 요청 접수 전 경량 검증 후 백그라운드 실행에 넘길 값을 구성한다.

    무거운 해석/LLM 호출은 백그라운드로 미루고, 여기서는 접수 응답에 필요한
    식별자만 정리한다. DB 기반 사전 검증(그룹 존재/시나리오 소속)이 필요해지면
    이 지점에 추가한다.
    """
    return {
        "scenario_group_id": scenario_group_id,
        "scenario_ids": list(scenario_ids),
    }


def _resolve_callback_url(scenario_group_id: int) -> str:
    from apps.common.configs.config import get_settings

    cfg = get_settings()
    callback_path = cfg.callback_price_interpretations_path.format(
        scenario_group_id=scenario_group_id,
    )
    return cfg.callback_base_url.rstrip("/") + callback_path


def _format_interpretation_content(interpretation: ScenarioComparisonOut) -> str:
    return (
        f"# {interpretation.identity}\n\n"
        f"## 동인 및 국면\n{interpretation.driver_phase}\n\n"
        f"## 가격 특성\n{interpretation.price_character}\n\n"
        f"## 시나리오 요약\n{interpretation.summary}"
    )


def _to_callback_interpretations(
    result: PriceInterpretationResult,
) -> list[PriceInterpretationCallbackItem]:
    return [
        PriceInterpretationCallbackItem(
            scenario_id=int(interpretation.scenario_id),
            content=_format_interpretation_content(interpretation),
        )
        for interpretation in result.scenarios
    ]


async def run_price_interpretation_background(
    scenario_group_id: int,
    scenario_ids: list[int] | None = None,
) -> None:
    """백그라운드에서 interpret_price graph를 실행하고 결과를 콜백으로 전송한다."""
    from apps.connectors.callback.callback_client import send_callback

    callback_url = _resolve_callback_url(scenario_group_id)
    start = time.perf_counter()
    logger.info(
        f"[BG][interpret_price] START | group_id={scenario_group_id} "
        f"| scenario_ids={scenario_ids}"
    )
    callback_payload: PriceInterpretationCallbackOut
    try:
        result = await run_interpret_price(
            scenario_group_id=scenario_group_id,
            scenario_ids=list(scenario_ids or []),
        )
        callback_payload = PriceInterpretationCallbackOut(
            result="success",
            interpretations=_to_callback_interpretations(result),
        )
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        logger.info(
            f"[BG][interpret_price] INTERPRET_DONE | group_id={scenario_group_id} "
            f"| scenarios={len(result.scenarios)} | elapsed={elapsed_ms}ms"
        )
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        logger.error(
            f"[BG][interpret_price] FAILED | group_id={scenario_group_id} "
            f"| elapsed={elapsed_ms}ms | error={exc!r}"
        )
        callback_payload = PriceInterpretationCallbackOut(
            result="failure",
            reason=str(exc),
        )

    try:
        await send_callback(callback_url, callback_payload)
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        logger.info(
            f"[BG][interpret_price] CALLBACK_DONE | group_id={scenario_group_id} "
            f"| result={callback_payload.result} | elapsed={elapsed_ms}ms"
        )
    except Exception as callback_error:
        logger.error(
            f"[BG][interpret_price] CALLBACK_FAILED | group_id={scenario_group_id} "
            f"| error={callback_error!r}"
        )
