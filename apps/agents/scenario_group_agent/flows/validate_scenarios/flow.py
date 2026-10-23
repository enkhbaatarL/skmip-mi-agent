from __future__ import annotations

from functools import lru_cache
import time
from typing import Any

from langchain_core.runnables import Runnable
from langgraph.graph import StateGraph

from apps.agents.scenario_group_agent.constants import AGENT_NAME, API_IDENTIFIER_VALIDATE_SCENARIOS
from apps.agents.scenario_group_agent.flows.callback_delivery import deliver_operation_callback
from apps.agents.scenario_group_agent.flows.validate_scenarios.api_schema import (
    ValidateScenariosCallBackScenarioGroup,
    ValidateScenariosOut,
)
from apps.agents.scenario_group_agent.flows.validate_scenarios.nodes import (
    create_mapping_proposals,
    generate_dimension_values,
    load_scenario_group,
    load_scenarios,
    run_scenario_review,
    save_validation_result,
)
from apps.agents.scenario_group_agent.flows.validate_scenarios.state import ValidateScenariosState
from apps.agents.scenario_group_agent.flows.validate_scenarios.v4_validation import V4_GENERATION_STRATEGY
from apps.agents.scenario_group_agent.persistence.scenario_group_operation_service import (
    ScenarioGroupOperationService,
)
from apps.agents.scenario_group_agent.runtime import get_scenario_group_operation_task_runner
from apps.agents.scenario_group_agent.schemas.state import ScenarioTableState
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
from apps.persistence.enums import (
    ScenarioGroupStage,
    ScenarioGroupStatus,
)
from apps.persistence.scenario_group.schema import ScenarioGroupPayload


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
    operation_id: str | None = None
    if group.get("generation_strategy") == V4_GENERATION_STRATEGY:
        operation = ScenarioGroupOperationService().create_validation_operation(
            scenario_group_id=scenario_group_id,
            user_id=user_id,
        )
        operation_id = operation.operation_id
        group["stage"] = ScenarioGroupStage.SCENARIO_CREATED.value
    return {
        "scenario_group_id": scenario_group_id,
        "status": group.get("status", ScenarioGroupStatus.CREATING.value),
        "stage": group.get("stage", ScenarioGroupStage.SCENARIO_CREATED.value),
        "user_id": user_id,
        "request_table": request_table,
        "operation_id": operation_id,
    }


# ---------------------------------------------------------------------------
# Background graph: load_scenario_group → load_scenarios → generate → validate → save
# ---------------------------------------------------------------------------


def _build_background_graph() -> Runnable:
    builder = StateGraph(ValidateScenariosState, context_schema=TraceContext)
    builder.add_node("load_scenario_group", load_scenario_group)
    builder.add_node("load_scenarios", load_scenarios)
    builder.add_node("generate_dimension_values", generate_dimension_values)
    builder.add_node("create_mapping_proposals", create_mapping_proposals)
    builder.add_node("validate_scenarios", run_scenario_review)
    builder.add_node("save_validation_result", save_validation_result)
    builder.set_entry_point("load_scenario_group")
    builder.add_edge("load_scenario_group", "load_scenarios")
    builder.add_edge("load_scenarios", "generate_dimension_values")
    builder.add_edge("generate_dimension_values", "create_mapping_proposals")
    builder.add_edge("create_mapping_proposals", "validate_scenarios")
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
    operation_result = data.get("operation_result") or {}
    if hasattr(operation_result, "model_dump"):
        operation_result = operation_result.model_dump()
    result_detail = operation_result.get("validation_result") or {}
    output_table = _validation_table_for_output(request_table, group)
    return ValidateScenariosOut(
        result="success",
        verdict=result_detail.get("verdict"),
        is_valid=result_detail.get("is_valid", data.get("is_valid")),
        can_proceed=result_detail.get("can_proceed"),
        review_skipped=result_detail.get("review_skipped"),
        summary=result_detail.get("summary") or {},
        checks=result_detail.get("checks") or [],
        generated_details=result_detail.get("generated_details") or [],
        reason=data.get("reason") or None,
        scenario_group=ValidateScenariosCallBackScenarioGroup(
            scenario_group_id=data.get("scenario_group_id") or 0,
            status=group.get("status") or ScenarioGroupStatus.CREATING.value,
            stage=group.get("stage") or ScenarioGroupStage.SCENARIO_CREATED.value,
        ),
        table=ScenarioTable.model_validate(output_table) if output_table else None,
        mapping_proposals=data.get("mapping_proposals") or [],
        parameter_mapping_ready=data.get("parameter_mapping_ready"),
    )


def _validation_table_for_output(
    request_table: dict[str, Any] | ScenarioTableState | None,
    group: dict[str, Any] | ScenarioGroupPayload,
) -> dict[str, Any] | None:
    if request_table is None:
        return None
    request_table_payload = (
        request_table.model_dump() if isinstance(request_table, ScenarioTableState) else request_table
    )
    group_payload = group.model_dump() if isinstance(group, ScenarioGroupPayload) else group
    if group_payload.get("generation_strategy") != V4_GENERATION_STRATEGY:
        return request_table_payload
    return request_table_payload


@lru_cache(maxsize=1)
def get_compiled_graph() -> Runnable:
    return _build_background_graph()


async def run_validate_scenarios_inline(
    scenario_group_id: int,
    user_id: int,
    request_table: dict[str, Any],
    operation_id: str | None = None,
) -> ValidateScenariosOut:
    """Run the background graph inline and return the callback payload."""
    from apps.common.configs.config import get_settings

    cfg = get_settings()
    agent_config = cfg.get_agent_config(AGENT_NAME)
    trace_context = TraceContext(
        transaction_id=new_transaction_id(),
        app_identifier=agent_config.aip_app_id,
        agent_name=AGENT_NAME,
        api_identifier=API_IDENTIFIER_VALIDATE_SCENARIOS,
        session_id=str(scenario_group_id),
    )
    state = ValidateScenariosState(
        scenario_group_id=scenario_group_id,
        user_id=user_id,
        request_table=request_table,
        operation_id=operation_id,
    )

    async def execute() -> ValidateScenariosOut:
        try:
            if operation_id is not None:
                ScenarioGroupOperationService().start_operation(
                    scenario_group_id,
                    operation_id,
                    phase="validation",
                )
            with mlflow_trace_context(trace_context):
                final_state = await get_compiled_graph().ainvoke(
                    state,
                    config=build_langgraph_config(trace_context),
                    context=trace_context,
                )
        except Exception as exc:
            if operation_id is not None:
                ScenarioGroupOperationService().fail_validation(
                    scenario_group_id=scenario_group_id,
                    operation_id=operation_id,
                    user_id=user_id,
                    error=exc,
                )
            raise
        output = _bg_to_output(final_state)
        if operation_id is not None:
            from apps.agents.scenario_group_agent.flows.evaluate_scenarios.flow import submit_automatic_evaluation

            await submit_automatic_evaluation(scenario_group_id, operation_id)
        return output

    operation = execute()
    if operation_id is None:
        return await operation
    return await get_scenario_group_operation_task_runner().run_with_heartbeat(
        scenario_group_id,
        operation_id,
        operation,
    )


# ---------------------------------------------------------------------------
# Background task function (called via FastAPI BackgroundTasks)
# ---------------------------------------------------------------------------


async def run_validate_scenarios_background(
    scenario_group_id: int,
    user_id: int,
    request_table: dict[str, Any],
    operation_id: str | None = None,
) -> None:
    from apps.common.configs.config import get_settings

    cfg = get_settings()
    callback_path = cfg.callback_validate_scenarios_path.format(
        scenario_group_id=scenario_group_id,
    )
    callback_url = cfg.callback_base_url.rstrip("/") + callback_path

    logger.info(f"[BG][validate_scenarios] START | group_id={scenario_group_id}")
    start = time.perf_counter()
    callback_payload: CallBackBody
    try:
        callback_payload = await run_validate_scenarios_inline(
            scenario_group_id=scenario_group_id,
            user_id=user_id,
            request_table=request_table,
            operation_id=operation_id,
        )
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        logger.info(
            f"[BG][validate_scenarios] END | group_id={scenario_group_id} | elapsed={elapsed_ms}ms",
        )
    except Exception as e:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        logger.error(
            f"[BG][validate_scenarios] FAILED | group_id={scenario_group_id} | elapsed={elapsed_ms}ms | error={e!r}",
        )
        callback_payload = CallBackBody(result="failure", reason=str(e))

    await deliver_operation_callback(
        log_tag="validate_scenarios",
        callback_url=callback_url,
        payload=callback_payload,
        scenario_group_id=scenario_group_id,
        operation_id=operation_id,
    )
