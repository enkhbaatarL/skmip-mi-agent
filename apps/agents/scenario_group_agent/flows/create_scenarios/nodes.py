from __future__ import annotations

from langgraph.runtime import Runtime

from apps.agents.scenario_group_agent.flows.create_scenarios.state import (
    CreateScenariosState,
    create_scenarios_state_update,
)
from apps.agents.scenario_group_agent.persistence.event_service import EventService
from apps.agents.scenario_group_agent.persistence.scenario_group_service import (
    ScenarioGroupService,
)
from apps.agents.scenario_group_agent.persistence.scenario_service import (
    ScenarioService,
)
from apps.agents.scenario_group_agent.subgraphs.scenario_generation.flow import (
    get_scenario_generation_subgraph,
)
from apps.agents.scenario_group_agent.subgraphs.scenario_generation.schema import (
    ScenarioTemplate,
)
from apps.agents.scenario_group_agent.subgraphs.scenario_generation.state import (
    ScenarioGenerationState,
)
from apps.common.exceptions.custom import MIBaseError
from apps.common.tracing.context import TraceContext, build_langgraph_config
from apps.common.values.error_codes import ErrorCode
from apps.persistence.enums import (
    ScenarioGroupStage,
    ScenarioGroupStatus,
)


def load_event(state: CreateScenariosState) -> dict[str, object]:
    if state.mi_event_id is None:
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="mi_event_id is required")
    event = EventService().load_event(state.mi_event_id)
    if event is None:
        raise MIBaseError(ErrorCode.ENTITY_NOT_FOUND, detail=f"Event not found for mi_event_id={state.mi_event_id}")
    return {"event_data": event}


def check_existing_scenario_group(state: CreateScenariosState) -> dict[str, object]:
    if state.status == "failure" or state.mi_event_id is None:
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="mi_event_id is required")
    existing = ScenarioGroupService().load_by_mi_event_id(state.mi_event_id)
    if existing is None:
        # 새로 생성
        return {}
    if existing.stage == ScenarioGroupStage.READY.value:
        if existing.request_usr_id != state.user_id:
            raise MIBaseError(
                ErrorCode.SCENARIO_GROUP_OWNERSHIP_CONFLICT,
                detail=f"시나리오 작성자: {existing.request_usr_id}, 시나리오 그룹 ID: {existing.scenario_group_id}",
            )
        return {
            "scenario_group_id": existing.scenario_group_id,
            "scenario_group": existing,
        }
    if existing.status == ScenarioGroupStatus.CREATING.value:
        if existing.request_usr_id == state.user_id:
            return {
                "scenario_group_id": existing.scenario_group_id,
                "scenario_group": existing,
            }
        raise MIBaseError(
            ErrorCode.SCENARIO_GROUP_OWNERSHIP_CONFLICT,
            detail=f"시나리오 작성자: {existing.request_usr_id}, 시나리오 그룹 ID: {existing.scenario_group_id}",
        )
    raise MIBaseError(
        ErrorCode.SCENARIO_GROUP_ALREADY_CREATED,
        detail=f"시나리오 그룹 ID: {existing.scenario_group_id}",
    )

    # scenarios = ScenarioService().load_by_group_id(existing["scenario_group_id"])
    # return {
    #     "scenario_group_id": existing["scenario_group_id"],
    #     "scenario_group": existing,
    #     "scenarios": scenarios,
    #     "status": "already_exist",
    #     "message": "Scenario group already exists",
    # }


def create_group_record(state: CreateScenariosState) -> dict[str, object]:
    """Prepare 단계: agent 실행 전 group row를 미리 INSERT해 scenarioGroupId를 확보한다."""
    if state.event_data is None:
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="event_data is required")
    if state.user_id is None:
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="user_id is required")
    payload = {
        "mi_event_id": int(state.event_data["mi_event_id"]),
        "event_type_l2_id": int(state.event_data["event_type_l2_id"]),
        "request_usr_id": state.user_id,
        "title": (state.event_data.get("event_title_ko") or f"Scenario group {state.event_data['mi_event_id']}")[:255],
        "summary": state.event_data.get("one_line_summary"),
        "description": None,  # initialize
        "dimension_selected": [],
        "scenario_count": 0,
        "status": ScenarioGroupStatus.CREATING.value,
        "stage": ScenarioGroupStage.READY.value,
        "api_version": "v1",
        "generation_strategy": "single_event_template_dimensions",
        "comparison_run_id": None,
        "parameter_mapping_ready": True,
        "dimension_definitions": [],
        "generation_diagnostics": {},
        "crt_usr_logn_id": state.user_id,
        "mod_usr_logn_id": state.user_id,
    }
    scenario_group_id = ScenarioGroupService().create_group(payload)
    group = ScenarioGroupService().load_by_id(scenario_group_id)
    if group is None:
        raise MIBaseError(
            ErrorCode.UNKNOWN_ERROR,
            detail="Scenario group not found after creation",
        )
    return {
        "scenario_group_id": scenario_group_id,
        "scenario_group": group,
    }


async def run_scenario_generation(
    state: CreateScenariosState,
    runtime: Runtime[TraceContext] | None = None,
) -> dict[str, object]:
    if state.status in {"failure", "already_exist"}:
        return {}
    if state.event_data is None:
        return create_scenarios_state_update(
            status="failure",
            error="event_data is required",
            message="event_data is required",
        )

    event_type_l2_id = int(state.event_data.get("event_type_l2_id") or 0)
    persistence_template = ScenarioService().load_pipeline_template(event_type_l2_id)
    template = ScenarioTemplate.model_validate(persistence_template.model_dump())
    subgraph_state = ScenarioGenerationState(
        event_data=state.event_data,
        template=template,
    )
    trace_context = runtime.context if runtime is not None else None
    result_state = await get_scenario_generation_subgraph().ainvoke(
        subgraph_state,
        config=build_langgraph_config(trace_context) if trace_context is not None else None,
        context=trace_context,
    )
    result = (
        result_state
        if isinstance(result_state, ScenarioGenerationState)
        else ScenarioGenerationState.model_validate(result_state)
    )
    if result.error:
        return create_scenarios_state_update(
            status="failure",
            error=result.error,
            message=result.error,
        )
    return create_scenarios_state_update(
        scenario_result=result.scenario_result,
        template_data=persistence_template.model_dump(),
    )


def save_scenario_group(state: CreateScenariosState) -> dict[str, object]:
    if state.status in {"failure", "already_exist"}:
        return {}
    if state.event_data is None or state.scenario_result is None:
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="scenario_result is required")
    if state.user_id is None:
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="user_id is required")

    stage2 = state.scenario_result.get("stage2_dimension_selection", {}) or {}
    stage4 = state.scenario_result.get("stage4_scenario_synthesis", {}) or {}
    scenario_group_metadata = state.scenario_result.get("scenario_group_metadata", {}) or {}
    selected_dimensions = stage2.get("selected_dimensions", []) or []
    dimension_selected = [
        item.get("dim_key") for item in selected_dimensions if isinstance(item, dict) and item.get("dim_key")
    ]
    payload = {
        "mi_event_id": int(state.event_data["mi_event_id"]),
        "event_type_l2_id": int(state.event_data["event_type_l2_id"]),
        "request_usr_id": state.user_id,
        "title": (
            scenario_group_metadata.get("title")
            or state.event_data.get("event_title_ko")
            or f"Scenario group {state.event_data['mi_event_id']}"
        )[:255],
        "summary": state.event_data.get("one_line_summary"),
        "description": (scenario_group_metadata.get("description") or state.event_data.get("detail_analysis")),
        "dimension_selected": dimension_selected,
        "scenario_count": len(stage4.get("scenarios", []) or []),
        "status": ScenarioGroupStatus.CREATING.value,
        "stage": ScenarioGroupStage.READY.value,
        "crt_usr_logn_id": state.user_id,
        "mod_usr_logn_id": state.user_id,
    }
    if state.scenario_group_id is not None:
        scenario_group_id = state.scenario_group_id
    else:
        scenario_group_id = ScenarioGroupService().create_group(payload)
    scenario_result = state.scenario_result.model_dump()
    scenario_result["scenario_group_id"] = scenario_group_id
    return create_scenarios_state_update(
        scenario_group_id=scenario_group_id,
        scenario_result=scenario_result,
    )


def save_scenarios(state: CreateScenariosState) -> dict[str, object]:
    if state.status in {"failure", "already_exist"}:
        return {}
    if state.scenario_group_id is None or state.scenario_result is None:
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="scenario_group_id is required")
    if state.user_id is None:
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="user_id is required")

    stage2 = state.scenario_result.get("stage2_dimension_selection", {}) or {}
    scenario_group_metadata = state.scenario_result.get("scenario_group_metadata", {}) or {}
    selected_dimensions = stage2.get("selected_dimensions", []) or []
    dimension_selected = [
        item.get("dim_key") for item in selected_dimensions if isinstance(item, dict) and item.get("dim_key")
    ]

    scenario_group_service = ScenarioGroupService()
    if scenario_group_service.load_by_id(state.scenario_group_id) is None:
        raise MIBaseError(
            ErrorCode.ENTITY_NOT_FOUND,
            detail=f"Fail to save scenarios because scenario group is deleted: {state.scenario_group_id}.",
        )

    saved_ids = ScenarioService().save_generated_scenarios(
        state.scenario_group_id,
        state.scenario_result.model_dump(),
        state.user_id,
    )
    scenario_group_service.update_scenario_count(
        state.scenario_group_id,
        len(saved_ids),
    )
    group = scenario_group_service.update_state(
        state.scenario_group_id,
        status=ScenarioGroupStatus.CREATING,
        stage=ScenarioGroupStage.SCENARIO_CREATED,
        dimension_selected=dimension_selected,
        title=scenario_group_metadata.get("title"),
        description=scenario_group_metadata.get("description"),
        user_id=state.user_id,
    )
    template_data = state.template_data or {}
    template_id = template_data.get("scenario_dimension_template_id")
    template_checksum = str(template_data.get("template_checksum") or "")
    if template_id is not None and template_checksum:
        definitions = _build_single_event_dimension_definitions(
            event_id=int(state.event_data["mi_event_id"]),
            event_type_l2_id=int(state.event_data["event_type_l2_id"]),
            template_data=template_data,
            selected_dimension_keys=dimension_selected,
        )
        scenario_group_service.save_single_event_template_usage(
            scenario_group_id=state.scenario_group_id,
            event_id=int(state.event_data["mi_event_id"]),
            event_type_l2_id=int(state.event_data["event_type_l2_id"]),
            scenario_dimension_template_id=int(template_id),
            template_checksum=template_checksum,
            dimension_definitions=definitions,
            user_id=state.user_id,
        )
        group = scenario_group_service.load_by_id(state.scenario_group_id) or group
    scenarios = ScenarioService().load_by_group_id(state.scenario_group_id)
    return create_scenarios_state_update(
        saved_scenario_ids=saved_ids,
        scenario_group=group,
        scenarios=scenarios,
        status="success",
        message=f"Created {len(saved_ids)} scenarios",
    )


def _build_single_event_dimension_definitions(
    *,
    event_id: int,
    event_type_l2_id: int,
    template_data: dict[str, object],
    selected_dimension_keys: list[str],
) -> list[dict[str, object]]:
    definitions: list[dict[str, object]] = []
    dimension_by_key = {
        str(dimension.get("dim_key")): dimension
        for dimension in template_data.get("dimensions", [])  # type: ignore[union-attr]
        if isinstance(dimension, dict) and dimension.get("dim_key")
    }
    for display_order, dimension_key in enumerate(
        selected_dimension_keys,
        start=1,
    ):
        dimension = dimension_by_key.get(dimension_key) or {}
        source = {
            "event_id": event_id,
            "event_type_l2_id": event_type_l2_id,
            "dim_key": dimension_key,
            "value": None,
            "source_type": "template_domain_knowledge",
            "assumption_yn": "N",
            "rationale": "단일 Event Type Template의 원본 dimension을 사용한다.",
        }
        definitions.append(
            {
                "dimension_id": dimension_key,
                "label": dimension.get("label") or dimension_key,
                "description": (dimension.get("description") or dimension.get("label") or dimension_key),
                "required": bool(dimension.get("required", False)),
                "display_order": display_order,
                "source_refs": [source],
                "values": [
                    {
                        "value_id": str(value),
                        "label": str(value),
                        "global_pressure_contribution": None,
                        "source_assignments": [
                            {
                                **source,
                                "value": str(value),
                            },
                        ],
                    }
                    for value in dimension.get("value_enums") or []
                ],
            },
        )
    return definitions
