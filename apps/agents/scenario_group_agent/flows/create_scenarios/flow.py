from __future__ import annotations

from functools import lru_cache
import time
from typing import Any

from langchain_core.runnables import Runnable
from langgraph.graph import StateGraph

from apps.agents.scenario_group_agent.flows.create_scenarios.api_schema import CreateScenariosOut
from apps.agents.scenario_group_agent.flows.create_scenarios.nodes import (
    check_existing_scenario_group,
    create_group_record,
    load_event,
    run_scenario_generation,
    save_scenarios,
)
from apps.agents.scenario_group_agent.flows.create_scenarios.state import CreateScenariosState
from apps.agents.scenario_group_agent.presentation import build_scenario_group_table_data
from apps.common.exceptions.custom import MIBaseError
from apps.common.logging.logger_config import logger
from apps.common.values.error_codes import ErrorCode
from apps.common.values.response import CallBackBody
from apps.connectors.callback.callback_client import send_callback
from apps.persistence.enums import (
    ScenarioGroupStage,
    ScenarioGroupStatus,
)
from apps.persistence.scenario_group.schema import (
    ScenarioGroupPayload,
)


# ---------------------------------------------------------------------------
# Prepare (plain function, no LangGraph — DB only)
# ---------------------------------------------------------------------------

def prepare_create_scenarios(mi_event_id: int, user_id: int) -> dict[str, Any]:
    """event 로드 → 기존 그룹 확인 → group row INSERT. 반환값으로 200 응답을 구성한다."""
    state = CreateScenariosState(mi_event_id=mi_event_id, user_id=user_id)
    state = state.model_copy(update=load_event(state))
    existing_group_result = check_existing_scenario_group(state)  # 충돌·중복 시 MIBaseError raise
    state = state.model_copy(update=existing_group_result)
    if state.scenario_group_id is None:
        state = state.model_copy(update=create_group_record(state))
    if state.scenario_group_id is None:
        raise MIBaseError(ErrorCode.UNKNOWN_ERROR, detail="Scenario group ID not found in state")

    group = (
        ScenarioGroupPayload.model_validate(state.scenario_group)
        if state.scenario_group
        else None
    )
    return {
        "scenario_group_id": state.scenario_group_id,
        "status": group.status if group else ScenarioGroupStatus.CREATING.value,
        "stage": group.stage if group else ScenarioGroupStage.READY.value,
        "event_data": state.event_data,
        "user_id": user_id,
    }


# ---------------------------------------------------------------------------
# Background graph: run_scenario_generation → save_scenarios
# ---------------------------------------------------------------------------

def _build_background_graph() -> Runnable:
    builder = StateGraph(CreateScenariosState)
    builder.add_node("run_scenario_generation", run_scenario_generation)
    builder.add_node("save_scenarios", save_scenarios)
    builder.set_entry_point("run_scenario_generation")
    builder.add_edge("run_scenario_generation", "save_scenarios")
    builder.set_finish_point("save_scenarios")
    return builder.compile()


def _bg_to_output(state: dict[str, Any] | CreateScenariosState) -> CreateScenariosOut:
    data = state if isinstance(state, dict) else state.model_dump()
    if data.get("status") in {"failure", "error"}:
        raise MIBaseError(
            ErrorCode.UNKNOWN_ERROR,
            detail=data.get("message") or "Scenario creation failed",
        )
    group = data.get("scenario_group")
    if not group:
        raise MIBaseError(ErrorCode.UNKNOWN_ERROR, detail="Scenario group not found in state")
    table_data = build_scenario_group_table_data(group, data.get("scenarios") or [])
    return CreateScenariosOut(
        result="success",
        scenario_group=table_data.scenario_group,
        table=table_data.table,
    )


@lru_cache(maxsize=1)
def get_compiled_graph() -> Runnable:
    return _build_background_graph()


# ---------------------------------------------------------------------------
# Background task function (called via FastAPI BackgroundTasks)
# ---------------------------------------------------------------------------

async def run_create_scenarios_background(
    scenario_group_id: int,
    event_data: dict[str, Any],
    user_id: int,
) -> None:
    from apps.common.configs.config import get_settings

    cfg = get_settings()
    callback_path = cfg.callback_create_scenarios_path.format(
        scenario_group_id=scenario_group_id
    )
    callback_url = cfg.callback_base_url.rstrip("/") + callback_path

    logger.info(f"[BG][create_scenarios] START | group_id={scenario_group_id}")
    start = time.perf_counter()
    try:
        state = CreateScenariosState(
            scenario_group_id=scenario_group_id,
            event_data=event_data,
            user_id=user_id,
        )
        final_state = await get_compiled_graph().ainvoke(state)
        callback_payload: CallBackBody = _bg_to_output(final_state)
        await send_callback(callback_url, callback_payload)
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        logger.info(
            f"[BG][create_scenarios] END | group_id={scenario_group_id} | elapsed={elapsed_ms}ms"
        )
    except Exception as e:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        logger.error(
            f"[BG][create_scenarios] FAILED | group_id={scenario_group_id}"
            f" | elapsed={elapsed_ms}ms | error={e!r}"
        )
        error_payload = CallBackBody(result="failure", reason=str(e))
        try:
            await send_callback(callback_url, error_payload)
        except Exception as cb_err:
            logger.error(f"[BG][create_scenarios] CALLBACK_FAILED | error={cb_err!r}")
