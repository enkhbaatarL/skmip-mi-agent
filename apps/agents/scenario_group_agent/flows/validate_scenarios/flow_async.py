from __future__ import annotations

import time
from functools import lru_cache
from typing import Any

from langchain_core.runnables import Runnable, RunnableLambda
from langgraph.graph import StateGraph

from apps.agents.scenario_group_agent.flows.validate_scenarios.nodes import (
    generate_dimension_values,
    load_scenario_group,
    load_scenarios,
    save_validation_result,
    validate_scenarios,
)
from apps.agents.scenario_group_agent.schemas.common import ScenarioTable
from apps.agents.scenario_group_agent.schemas.validate_scenarios import (
    ValidateScenariosCallBackScenarioGroup,
    ValidateScenariosOut,
)
from apps.agents.scenario_group_agent.state import ScenarioDesignState
from apps.common.logging.logger_config import logger
from apps.common.values.response import CallBackBody
from apps.connectors.callback.callback_client import send_callback


# ---------------------------------------------------------------------------
# Prepare (plain function, no LangGraph — DB only)
# ---------------------------------------------------------------------------

def prepare_validate_scenarios(
    scenario_group_id: int,
    user_id: int,
    request_table: dict[str, Any],
) -> dict[str, Any]:
    """group 존재·권한 확인. 반환값으로 200 응답을 구성한다."""
    state = ScenarioDesignState(
        scenario_group_id=scenario_group_id,
        user_id=user_id,
        request_table=request_table,
    )
    group_result = load_scenario_group(state)  # not found / 권한 오류 시 MIBaseError raise
    group = group_result["scenario_group"]
    return {
        "scenario_group_id": scenario_group_id,
        "status": group.get("status", "creating"),
        "stage": group.get("stage", "scenario_created"),
        "user_id": user_id,
        "request_table": request_table,
    }


# ---------------------------------------------------------------------------
# Background graph: load_scenario_group → load_scenarios → generate → validate → save
# ---------------------------------------------------------------------------

def _build_background_graph() -> Runnable:
    builder = StateGraph(ScenarioDesignState)
    builder.add_node("load_scenario_group", load_scenario_group)
    builder.add_node("load_scenarios", load_scenarios)
    builder.add_node("generate_dimension_values", generate_dimension_values)
    builder.add_node("validate_scenarios", validate_scenarios)
    builder.add_node("save_validation_result", save_validation_result)
    builder.set_entry_point("load_scenario_group")
    builder.add_edge("load_scenario_group", "load_scenarios")
    builder.add_edge("load_scenarios", "generate_dimension_values")
    builder.add_edge("generate_dimension_values", "validate_scenarios")
    builder.add_edge("validate_scenarios", "save_validation_result")
    builder.set_finish_point("save_validation_result")
    return builder.compile()


def _bg_to_output(state: dict[str, Any] | ScenarioDesignState) -> ValidateScenariosOut:
    data = state if isinstance(state, dict) else state.model_dump()
    group = data.get("scenario_group") or {}
    request_table = data.get("request_table")
    return ValidateScenariosOut(
        result="success",
        is_valid=data.get("is_valid"),
        reason=data.get("reason") or None,
        scenario_group=ValidateScenariosCallBackScenarioGroup(
            scenario_group_id=data.get("scenario_group_id") or 0,
            status=group.get("status") or "creating",
            stage=group.get("stage") or "scenario_created",
        ),
        table=ScenarioTable.model_validate(request_table) if request_table else None,
    )


@lru_cache(maxsize=1)
def get_background_runnable() -> Runnable:
    return (
        _build_background_graph() | RunnableLambda(_bg_to_output)
    ).with_types(output_type=ValidateScenariosOut)


# ---------------------------------------------------------------------------
# Background task function (called via FastAPI BackgroundTasks)
# ---------------------------------------------------------------------------

async def run_validate_scenarios_background(
    scenario_group_id: int,
    user_id: int,
    request_table: dict[str, Any],
) -> None:
    from apps.common.configs.settings import get_settings

    cfg = get_settings()
    callback_url = cfg.callback_base_url.rstrip("/") + cfg.callback_validate_scenarios_path

    logger.info(f"[BG][validate_scenarios] START | group_id={scenario_group_id}")
    start = time.perf_counter()
    try:
        state = ScenarioDesignState(
            scenario_group_id=scenario_group_id,
            user_id=user_id,
            request_table=request_table,
        )
        callback_payload: CallBackBody = await get_background_runnable().ainvoke(state)
        await send_callback(callback_url, callback_payload)
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        logger.info(
            f"[BG][validate_scenarios] END | group_id={scenario_group_id} | elapsed={elapsed_ms}ms"
        )
    except Exception as e:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        logger.error(
            f"[BG][validate_scenarios] FAILED | group_id={scenario_group_id}"
            f" | elapsed={elapsed_ms}ms | error={e!r}"
        )
        error_payload = CallBackBody(result="error", reason=str(e))
        try:
            await send_callback(callback_url, error_payload)
        except Exception as cb_err:
            logger.error(f"[BG][validate_scenarios] CALLBACK_FAILED | error={cb_err!r}")
