from __future__ import annotations

from functools import lru_cache
import time
from typing import Any

from langchain_core.runnables import Runnable, RunnableLambda
from langgraph.graph import StateGraph

from apps.agents.scenario_group_agent.flows.create_signposts.nodes import (
    check_existing_signposts,
    generate_new_scenario_row_details_node,
    load_scenario_group,
    load_scenarios,
    run_signpost_generation,
    save_signposts,
    sync_scenarios_from_table,
)
from apps.agents.scenario_group_agent.presentation import build_scenario_group_table_data
from apps.agents.scenario_group_agent.schemas.api.create_signposts import CreateSignpostsOut
from apps.agents.scenario_group_agent.state import ScenarioDesignState
from apps.common.exceptions.custom import MIBaseError
from apps.common.logging.logger_config import logger
from apps.common.values.error_codes import ErrorCode
from apps.common.values.response import CallBackBody
from apps.connectors.callback.callback_client import send_callback
from apps.persistence.schemas.enums import (
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
    """group 존재·권한 확인. 반환값으로 200 응답을 구성한다."""
    state = ScenarioDesignState(
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
    builder = StateGraph(ScenarioDesignState)
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


def _bg_to_output(state: dict[str, Any] | ScenarioDesignState) -> CreateSignpostsOut:
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
def get_background_runnable() -> Runnable:
    return (_build_background_graph() | RunnableLambda(_bg_to_output)).with_types(output_type=CreateSignpostsOut)


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
        state = ScenarioDesignState(
            scenario_group_id=scenario_group_id,
            user_id=user_id,
            include_details=True,
            request_table=request_table,
        )
        callback_payload: CallBackBody = await get_background_runnable().ainvoke(state)
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
