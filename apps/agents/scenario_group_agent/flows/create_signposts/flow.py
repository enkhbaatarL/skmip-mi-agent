from __future__ import annotations

from functools import lru_cache
import time
from typing import Any

from langchain_core.runnables import Runnable
from langgraph.graph import StateGraph

from apps.agents.scenario_group_agent.constants import AGENT_NAME, API_IDENTIFIER_CREATE_SIGNPOSTS
from apps.agents.scenario_group_agent.flows.create_signposts.nodes import (
    check_existing_signposts,
    generate_new_scenario_row_details_node,
    load_scenario_group,
    load_scenarios,
    run_signpost_generation,
    save_signposts,
    sync_scenarios_from_table,
)
from apps.agents.scenario_group_agent.flows.create_signposts.state import CreateSignpostsState
from apps.agents.scenario_group_agent.presentation import build_scenario_group_table_data
from apps.agents.scenario_group_agent.schemas.endpoint import CreateSignpostsOut
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


def prepare_create_signposts(
    scenario_group_id: int,
    user_id: int,
    request_table: dict[str, Any],
) -> dict[str, Any]:
    """Group 존재·권한 확인. 반환값으로 200 응답을 구성한다."""
    state = CreateSignpostsState(
        scenario_group_id=scenario_group_id,
        user_id=user_id,
        include_details=True,
        request_table=request_table,
    )
    group_result = load_scenario_group(state)  # not found / 권한 오류 시 MIBaseError raise
    group = group_result["scenario_group"]
    return {
        "scenario_group_id": scenario_group_id,
        "status": group.get("status", ScenarioGroupStatus.CREATING.value),
        "stage": group.get("stage", ScenarioGroupStage.SCENARIO_VALIDATED.value),
        "user_id": user_id,
        "request_table": request_table,
    }


# ---------------------------------------------------------------------------
# Background graph: load_scenario_group → generate_new_row_details → sync → load → check → generate → save
# ---------------------------------------------------------------------------


def _build_background_graph() -> Runnable:
    builder = StateGraph(CreateSignpostsState, context_schema=TraceContext)
    builder.add_node("load_scenario_group", load_scenario_group)
    builder.add_node(
        "generate_new_scenario_row_details",
        generate_new_scenario_row_details_node,
    )
    builder.add_node("sync_scenarios_from_table", sync_scenarios_from_table)
    builder.add_node("load_scenarios", load_scenarios)
    builder.add_node("check_existing_signposts", check_existing_signposts)
    builder.add_node("run_signpost_generation", run_signpost_generation)
    builder.add_node("save_signposts", save_signposts)
    builder.set_entry_point("load_scenario_group")
    builder.add_edge("load_scenario_group", "generate_new_scenario_row_details")
    builder.add_edge("generate_new_scenario_row_details", "sync_scenarios_from_table")
    builder.add_edge("sync_scenarios_from_table", "load_scenarios")
    builder.add_edge("load_scenarios", "check_existing_signposts")
    builder.add_edge("check_existing_signposts", "run_signpost_generation")
    builder.add_edge("run_signpost_generation", "save_signposts")
    builder.set_finish_point("save_signposts")
    return builder.compile()


def _bg_to_output(state: dict[str, Any] | CreateSignpostsState) -> CreateSignpostsOut:
    data = state if isinstance(state, dict) else state.model_dump()
    if data.get("status") in {"failure", "error"}:
        raise MIBaseError(
            ErrorCode.UNKNOWN_ERROR,
            detail=data.get("message") or "Signpost creation failed",
        )
    group = data.get("scenario_group")
    if not group:
        raise MIBaseError(ErrorCode.UNKNOWN_ERROR, detail="Scenario group not found in state")
    table_data = build_scenario_group_table_data(
        group,
        data.get("scenarios") or [],
        data.get("signposts") or [],
    )
    return CreateSignpostsOut(
        result="success",
        scenario_group=table_data.scenario_group,
        table=table_data.table,
    )


@lru_cache(maxsize=1)
def get_compiled_graph() -> Runnable:
    return _build_background_graph()


async def run_create_signposts_inline(
    scenario_group_id: int,
    user_id: int,
    request_table: dict[str, Any],
) -> CreateSignpostsOut:
    """Run the background graph inline and return the callback payload."""
    from apps.common.configs.config import get_settings

    cfg = get_settings()
    agent_config = cfg.get_agent_config(AGENT_NAME)
    trace_context = TraceContext(
        transaction_id=new_transaction_id(),
        app_identifier=agent_config.aip_app_id,
        agent_name=AGENT_NAME,
        api_identifier=API_IDENTIFIER_CREATE_SIGNPOSTS,
        session_id=str(scenario_group_id),
    )
    state = CreateSignpostsState(
        scenario_group_id=scenario_group_id,
        user_id=user_id,
        include_details=True,
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


async def run_create_signposts_background(
    scenario_group_id: int,
    user_id: int,
    request_table: dict[str, Any],
) -> None:
    from apps.common.configs.config import get_settings

    cfg = get_settings()
    callback_path = cfg.callback_create_signposts_path.format(scenario_group_id=scenario_group_id)
    callback_url = cfg.callback_base_url.rstrip("/") + callback_path

    logger.info(f"[BG][create_signposts] START | group_id={scenario_group_id}")
    start = time.perf_counter()
    try:
        callback_payload: CallBackBody = await run_create_signposts_inline(
            scenario_group_id=scenario_group_id,
            user_id=user_id,
            request_table=request_table,
        )
        await send_callback(callback_url, callback_payload)
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        logger.info(f"[BG][create_signposts] END | group_id={scenario_group_id} | elapsed={elapsed_ms}ms")
    except Exception as e:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        logger.error(
            f"[BG][create_signposts] FAILED | group_id={scenario_group_id} | elapsed={elapsed_ms}ms | error={e!r}",
        )
        error_payload = CallBackBody(result="failure", reason=str(e))
        try:
            await send_callback(callback_url, error_payload)
        except Exception as cb_err:
            logger.error(f"[BG][create_signposts] CALLBACK_FAILED | error={cb_err!r}")
