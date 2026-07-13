from __future__ import annotations

from functools import lru_cache
import time
from typing import Any

from langchain_core.runnables import Runnable
from langgraph.graph import StateGraph

from apps.agents.scenario_group_agent.constants import AGENT_NAME
from apps.agents.scenario_group_agent.flows.validate_scenarios.nodes import (
    generate_dimension_values,
    load_scenario_group,
    load_scenarios,
    run_scenario_review,
    save_validation_result,
)
from apps.agents.scenario_group_agent.flows.validate_scenarios.state import ValidateScenariosState
from apps.agents.scenario_group_agent.schemas.endpoint import (
    ValidateScenariosCallBackScenarioGroup,
    ValidateScenariosOut,
)
from apps.agents.scenario_group_agent.schemas.table import ScenarioTable
from apps.common.exceptions.custom import MIBaseError
from apps.common.logging.logger_config import logger
from apps.common.tracing.context import (
    TraceContext,
    build_langgraph_config,
    mlflow_trace_context,
    new_transaction_id,
)
from apps.common.values.error_codes import ErrorCode
from apps.common.values.response import CallBackBody
from apps.connectors.callback.callback_client import send_callback
from apps.persistence.enums import (
    ScenarioGroupStage,
    ScenarioGroupStatus,
)


# ---------------------------------------------------------------------------
# Prepare (plain function, no LangGraph — DB only)
# ---------------------------------------------------------------------------


def prepare_validate_scenarios(
    scenario_group_id: int,
    user_id: int,
    request_table: dict[str, Any],
) -> dict[str, Any]:
    """Group 존재·권한 확인. 반환값으로 200 응답을 구성한다."""
    state = ValidateScenariosState(
        scenario_group_id=scenario_group_id,
        user_id=user_id,
        request_table=request_table,
    )
    group_result = load_scenario_group(state)  # not found / 권한 오류 시 MIBaseError raise
    group = group_result["scenario_group"]
    return {
        "scenario_group_id": scenario_group_id,
        "status": group.get("status", ScenarioGroupStatus.CREATING.value),
        "stage": group.get("stage", ScenarioGroupStage.SCENARIO_CREATED.value),
        "user_id": user_id,
        "request_table": request_table,
    }


# ---------------------------------------------------------------------------
# Background graph: load_scenario_group → load_scenarios → generate → validate → save
# ---------------------------------------------------------------------------


def _build_background_graph() -> Runnable:
    builder = StateGraph(ValidateScenariosState, context_schema=TraceContext)
    builder.add_node("load_scenario_group", load_scenario_group)
    builder.add_node("load_scenarios", load_scenarios)
    builder.add_node("generate_dimension_values", generate_dimension_values)
    builder.add_node("validate_scenarios", run_scenario_review)
    builder.add_node("save_validation_result", save_validation_result)
    builder.set_entry_point("load_scenario_group")
    builder.add_edge("load_scenario_group", "load_scenarios")
    builder.add_edge("load_scenarios", "generate_dimension_values")
    builder.add_edge("generate_dimension_values", "validate_scenarios")
    builder.add_edge("validate_scenarios", "save_validation_result")
    builder.set_finish_point("save_validation_result")
    return builder.compile()


def _bg_to_output(state: dict[str, Any] | ValidateScenariosState) -> ValidateScenariosOut:
    data = state if isinstance(state, dict) else state.model_dump()
    if data.get("status") in {"failure", "error"}:
        raise MIBaseError(
            ErrorCode.UNKNOWN_ERROR,
            detail=data.get("message") or "Scenario validation failed",
        )
    group = data.get("scenario_group") or {}
    request_table = data.get("request_table")
    return ValidateScenariosOut(
        result="success",
        is_valid=data.get("is_valid"),
        reason=data.get("reason") or None,
        scenario_group=ValidateScenariosCallBackScenarioGroup(
            scenario_group_id=data.get("scenario_group_id") or 0,
            status=group.get("status") or ScenarioGroupStatus.CREATING.value,
            stage=group.get("stage") or ScenarioGroupStage.SCENARIO_CREATED.value,
        ),
        table=ScenarioTable.model_validate(request_table) if request_table else None,
    )


@lru_cache(maxsize=1)
def get_compiled_graph() -> Runnable:
    return _build_background_graph()


async def run_validate_scenarios_inline(
    scenario_group_id: int,
    user_id: int,
    request_table: dict[str, Any],
) -> ValidateScenariosOut:
    """Run the background graph inline and return the callback payload."""
    from apps.common.configs.config import get_settings

    cfg = get_settings()
    agent_config = cfg.get_agent_config(AGENT_NAME)
    trace_context = TraceContext(
        transaction_id=new_transaction_id(),
        app_identifier=agent_config.aip_app_id,
        agent_name=AGENT_NAME,
        session_id=str(scenario_group_id),
    )
    state = ValidateScenariosState(
        scenario_group_id=scenario_group_id,
        user_id=user_id,
        request_table=request_table,
    )
    with mlflow_trace_context(trace_context):
        final_state = await get_compiled_graph().ainvoke(
            state,
            config=build_langgraph_config(trace_context),
            context=trace_context,
        )
    return _bg_to_output(final_state)


# ---------------------------------------------------------------------------
# Background task function (called via FastAPI BackgroundTasks)
# ---------------------------------------------------------------------------


async def run_validate_scenarios_background(
    scenario_group_id: int,
    user_id: int,
    request_table: dict[str, Any],
) -> None:
    from apps.common.configs.config import get_settings

    cfg = get_settings()
    callback_path = cfg.callback_validate_scenarios_path.format(
        scenario_group_id=scenario_group_id,
    )
    callback_url = cfg.callback_base_url.rstrip("/") + callback_path

    logger.info(f"[BG][validate_scenarios] START | group_id={scenario_group_id}")
    start = time.perf_counter()
    try:
        callback_payload: CallBackBody = await run_validate_scenarios_inline(
            scenario_group_id=scenario_group_id,
            user_id=user_id,
            request_table=request_table,
        )
        await send_callback(callback_url, callback_payload)
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        logger.info(
            f"[BG][validate_scenarios] END | group_id={scenario_group_id} | elapsed={elapsed_ms}ms",
        )
    except Exception as e:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        logger.error(
            f"[BG][validate_scenarios] FAILED | group_id={scenario_group_id} | elapsed={elapsed_ms}ms | error={e!r}",
        )
        error_payload = CallBackBody(result="failure", reason=str(e))
        try:
            await send_callback(callback_url, error_payload)
        except Exception as cb_err:
            logger.error(f"[BG][validate_scenarios] CALLBACK_FAILED | error={cb_err!r}")
