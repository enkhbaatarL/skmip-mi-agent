from __future__ import annotations

import hashlib
from typing import Any

from langgraph.runtime import Runtime

from apps.agents.scenario_group_agent.flows.validate_scenarios.state import (
    ValidateScenariosState,
    validate_scenarios_state_update,
)
from apps.agents.scenario_group_agent.persistence.event_service import EventService
from apps.agents.scenario_group_agent.persistence.scenario_group_service import (
    ScenarioGroupService,
)
from apps.agents.scenario_group_agent.persistence.scenario_service import (
    ScenarioService,
)
from apps.agents.scenario_group_agent.subgraphs.scenario_review.flow import (
    get_scenario_review_subgraph,
)
from apps.agents.scenario_group_agent.subgraphs.scenario_review.nodes import (
    generate_new_dimension_values,
)
from apps.agents.scenario_group_agent.subgraphs.scenario_review.state import (
    ScenarioReviewState,
)
from apps.common.exceptions.custom import MIBaseError
from apps.common.tracing.context import TraceContext, build_langgraph_config
from apps.common.values.error_codes import ErrorCode
from apps.persistence.enums import (
    ScenarioGroupStage,
    ScenarioGroupStatus,
    ScenarioStatus,
)


def _model_or_dict_dump(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return dict(value)


def _validate_v4_request_dimension_values(
    state: ValidateScenariosState,
    headers: list[dict[str, Any]],
    rows: list[dict[str, Any]],
) -> None:
    if (
        state.scenario_group is None
        or state.scenario_group.generation_strategy
        != "multi_event_model_lever_dimensions"
    ):
        return
    try:
        scenario_service = ScenarioService()
        template_by_key = scenario_service.build_group_dimension_template_by_key(
            state.scenario_group.dimension_definitions,
            require_catalog_value_ids=True,
        )
        scenario_service.validate_complete_dimension_headers(
            template_by_key,
            headers,
        )
        for row in rows:
            scenario_service.cells_to_dimension_values_with_template(
                template_by_key,
                row.get("cells") or {},
                require_complete_catalog_values=True,
            )
    except ValueError as exc:
        raise MIBaseError(
            ErrorCode.SCENARIO_VALIDATION_INPUT_ERROR,
            detail=str(exc),
        ) from exc


def load_scenario_group(state: ValidateScenariosState) -> dict[str, object]:
    if state.scenario_group_id is None:
        raise MIBaseError(ErrorCode.ENTITY_NOT_FOUND, detail="scenario_group_id is required")
    group = ScenarioGroupService().load_by_id(state.scenario_group_id)
    if group is None:
        raise MIBaseError(ErrorCode.ENTITY_NOT_FOUND, detail=f"Scenario group not found: {state.scenario_group_id}")
    request_usr_id = group.get("request_usr_id")
    if request_usr_id is not None and request_usr_id != state.user_id:
        raise MIBaseError(
            ErrorCode.SCENARIO_GROUP_OWNERSHIP_CONFLICT,
            detail=f"이미 사용자 {request_usr_id}가 점유하고 있습니다.",
        )

    return {"scenario_group": group}


def load_scenarios(state: ValidateScenariosState) -> dict[str, object]:
    if state.status == "failure" or state.scenario_group_id is None:
        return {}
    scenarios = ScenarioService().load_by_group_id(state.scenario_group_id)
    if not scenarios:
        raise MIBaseError(ErrorCode.ENTITY_NOT_FOUND, detail="No scenarios found")
    if state.scenario_group is None:
        raise MIBaseError(ErrorCode.ENTITY_NOT_FOUND, detail="Scenario group is required")
    if state.scenario_group.dimension_definitions:
        dimension_template = ScenarioService().load_group_dimension_template(
            state.scenario_group.dimension_definitions,
        )
    else:
        try:
            dimension_template = ScenarioService().load_dimension_template(
                int(state.scenario_group.event_type_l2_id),
            )
        except (KeyError, TypeError, ValueError):
            dimension_template = []
    event_ids = ScenarioGroupService().load_event_ids(state.scenario_group_id)
    events = EventService().load_events(event_ids)
    return validate_scenarios_state_update(
        scenarios=scenarios,
        dimension_template=dimension_template,
        events=events,
        generation_diagnostics=state.scenario_group.generation_diagnostics,
    )


async def generate_dimension_values(
    state: ValidateScenariosState,
    runtime: Runtime[TraceContext] | None = None,
) -> dict[str, object]:
    if state.status == "failure":
        return {}

    def build_dimension_generation_rows(
        table_rows: list[dict[str, Any]],
        persisted_scenarios: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        persisted_by_id = {
            int(scenario["scenario_id"]): scenario
            for scenario in persisted_scenarios
            if scenario.get("scenario_id") is not None
        }
        generation_rows: list[dict[str, Any]] = []
        for row in table_rows:
            generation_row = dict(row)
            if row.get("scenario_id") is not None:
                persisted = persisted_by_id.get(int(row["scenario_id"])) or {}
                if not generation_row.get("title"):
                    generation_row["title"] = persisted.get("title") or ""
                generation_row["narrative"] = persisted.get("narrative") or ""
            generation_rows.append(generation_row)
        return generation_rows

    request_table = state.request_table.model_dump(exclude_unset=True) if state.request_table is not None else {}
    headers = request_table.get("headers") or []
    rows = request_table.get("rows") or []
    header_key_list = [str(header["key"]) for header in headers]
    header_keys = set(header_key_list)

    if state.scenario_group is None:
        raise MIBaseError(ErrorCode.ENTITY_NOT_FOUND, detail="Scenario group is required")
    if state.dimension_template:
        from apps.persistence.scenario.schema import ScenarioTemplate

        template = ScenarioTemplate(
            template_dimensions_total=len(state.dimension_template),
            dimensions=state.dimension_template,
        )
    elif state.scenario_group.event_type_l2_id is not None:
        template = ScenarioService().load_scenario_template(
            int(state.scenario_group.event_type_l2_id),
        )
    else:
        raise MIBaseError(
            ErrorCode.SCENARIO_VALIDATION_INPUT_ERROR,
            detail="Scenario group dimension definitions are missing",
        )

    # 시나리오화 템플릿(event type 기준)에서 필수 분기(required=True)와
    # 선택 분기(required=False)를 식별한다.
    required_keys = [dimension.dimension_id for dimension in template.dimensions if dimension.required]
    optional_keys = {dimension.dimension_id for dimension in template.dimensions if not dimension.required}
    label_by_key = {dimension.dimension_id: dimension.label_ko for dimension in template.dimensions}

    # 필수 분기는 화면에서 삭제가 막혀 있으므로 헤더(컬럼)에도 반드시 존재해야 한다.
    missing_required = [key for key in required_keys if key not in header_keys]
    if missing_required:
        missing_labels = ", ".join(label_by_key.get(key, key) for key in missing_required)
        raise MIBaseError(
            ErrorCode.SCENARIO_VALIDATION_INPUT_ERROR,
            detail=f"필수 분기 누락: {missing_labels}",
        )

    required_header_keys = [key for key in header_key_list if key in set(required_keys)]

    # 필수 분기(required=True) 값은 기존/신규 시나리오 여부와 무관하게 비워 둘 수 없다.
    #  - 신규 시나리오: 필수 분기 값을 반드시 입력해야 함.
    #  - 기존 시나리오: 필수 분기 값을 사용자가 null 로 비우는 것은 미허용.
    # 선택 분기(required=False)의 null 은 아래에서 Agent 가 채우므로 허용한다(부분 null 포함).
    for row in rows:
        cells = row.get("cells") or {}
        missing_required_values = [key for key in required_header_keys if cells.get(key) is None]
        if not missing_required_values:
            continue
        missing_labels = ", ".join(label_by_key.get(key, key) for key in missing_required_values)
        title = row.get("title") or "(제목 없음)"
        if row.get("scenario_id") is None:
            detail = f"새로 추가된 시나리오 '{title}'의 필수 분기 값을 모두 입력해야 합니다. 누락: {missing_labels}"
        else:
            detail = f"시나리오 '{title}'의 필수 분기 값은 비워 둘 수 없습니다. 누락: {missing_labels}"
        raise MIBaseError(
            ErrorCode.SCENARIO_VALIDATION_INPUT_ERROR,
            detail=detail,
        )

    # 선택 분기(required=False)의 null 만 Agent 가 채운다(부분 null 포함).
    # 필수 분기 null 은 위에서 이미 에러로 걸러졌다.
    fillable_dims = [
        key
        for key in header_key_list
        if key in optional_keys and any((row.get("cells") or {}).get(key) is None for row in rows)
    ]
    if fillable_dims:
        trace_context = runtime.context if runtime is not None else None
        generated = await generate_new_dimension_values(
            template,
            build_dimension_generation_rows(
                rows,
                [_model_or_dict_dump(scenario) for scenario in state.scenarios],
            ),
            fillable_dims,
            trace_context=trace_context,
        )
        for index, row in enumerate(rows):
            values = generated.get(index) or {}
            if not values:
                continue
            cells = row.get("cells")
            if cells is None:
                cells = {}
                row["cells"] = cells
            for key, value in values.items():
                if cells.get(key) is None:
                    cells[key] = value

    _validate_v4_request_dimension_values(state, headers, rows)

    return validate_scenarios_state_update(request_table=request_table)


def create_mapping_proposals(
    state: ValidateScenariosState,
) -> dict[str, object]:
    if state.status == "failure" or state.scenario_group is None:
        return {}
    if state.scenario_group.generation_strategy == "multi_event_model_lever_dimensions":
        return validate_scenarios_state_update(parameter_mapping_ready=True)
    definitions = state.scenario_group.dimension_definitions
    if not definitions:
        return validate_scenarios_state_update(parameter_mapping_ready=True)

    definition_by_id = {
        str(definition.get("dimension_id")): definition
        for definition in definitions
        if isinstance(definition, dict) and definition.get("dimension_id")
    }
    request_table = state.request_table.model_dump() if state.request_table else {}
    uses_compact_v2_sources = state.scenario_group.generation_strategy == "multi_event_source_dimensions"
    uses_compact_v3_sources = state.scenario_group.generation_strategy == "multi_event_composite_dimensions"
    all_source_refs: list[dict[str, Any]] = []
    seen_source_refs: set[tuple[object, ...]] = set()
    for definition in definition_by_id.values():
        raw_sources = (
            [definition.get("source_ref")]
            if uses_compact_v2_sources and isinstance(definition.get("source_ref"), dict)
            else definition.get("source_refs") or []
        )
        for source in raw_sources:
            if not isinstance(source, dict):
                continue
            if uses_compact_v2_sources:
                source_key = (
                    int(source.get("event_id") or 0),
                    int(source.get("scenario_dimension_template_id") or 0),
                    str(source.get("dim_key") or ""),
                )
            elif uses_compact_v3_sources:
                source_key = (
                    int(source.get("scenario_dimension_template_id") or 0),
                    str(source.get("dim_key") or ""),
                )
            else:
                source_key = (
                    int(source.get("event_id") or 0),
                    str(source.get("dim_key") or ""),
                )
            if source_key in seen_source_refs:
                continue
            seen_source_refs.add(source_key)
            all_source_refs.append(source)
    for display_order, header in enumerate(
        request_table.get("headers") or [],
        start=1,
    ):
        dimension_id = str(header.get("key") or "")
        if not dimension_id or dimension_id in definition_by_id:
            continue
        definition_by_id[dimension_id] = {
            "dimension_id": dimension_id,
            "label": header.get("label") or dimension_id,
            "description": "사용자가 Validation table에 추가한 dimension",
            "display_order": header.get("display_order") or display_order,
            "source_refs": all_source_refs,
            "values": [],
        }
    known_values = {
        dimension_id: {
            str(value.get("label"))
            for value in definition.get("values") or []
            if isinstance(value, dict) and value.get("label") is not None
        }
        | {
            str(value.get("value_id"))
            for value in definition.get("values") or []
            if isinstance(value, dict) and value.get("value_id") is not None
        }
        for dimension_id, definition in definition_by_id.items()
    }
    free_values: dict[tuple[str, str], dict[str, Any]] = {}
    for row in request_table.get("rows") or []:
        for dimension_id, raw_value in (row.get("cells") or {}).items():
            if raw_value is None or dimension_id not in definition_by_id:
                continue
            display_value = str(raw_value)
            if display_value in known_values.get(dimension_id, set()):
                continue
            free_values[(dimension_id, display_value)] = definition_by_id[dimension_id]

    proposals: list[dict[str, Any]] = []
    for (dimension_id, display_value), definition in sorted(
        free_values.items(),
    ):
        digest = hashlib.sha256(
            (f"{state.scenario_group_id}:{dimension_id}:{display_value}").encode("utf-8"),
        ).hexdigest()[:24]
        source_projections = []
        raw_sources = (
            [definition.get("source_ref")]
            if uses_compact_v2_sources and isinstance(definition.get("source_ref"), dict)
            else definition.get("source_refs") or []
        )
        for source in raw_sources:
            if not isinstance(source, dict):
                continue
            if uses_compact_v2_sources:
                source_projections.append({**source, "value": display_value})
            else:
                source_projections.append(
                    {
                        **source,
                        "value": display_value,
                        "source_type": "derived_interpretation",
                        "assumption_yn": "N",
                        "rationale": ("사용자 자유 입력 value를 기존 source dimension에 투영한 검토안이다."),
                    },
                )
        proposals.append(
            {
                "dimension_value_id": f"dv_{digest}",
                "dimension_id": dimension_id,
                "display_value": display_value,
                "source_projections": source_projections,
                "mapping_proposal": {
                    "status": "pending",
                    "dimensionLabel": definition.get("label") or dimension_id,
                    "candidateSourceDimensions": (
                        [
                            {
                                "eventId": source.get("event_id"),
                                "scenarioDimensionTemplateId": source.get(
                                    "scenario_dimension_template_id",
                                ),
                                "dimKey": source.get("dim_key"),
                            }
                            for source in source_projections
                        ]
                        if uses_compact_v2_sources
                        else [
                            {
                                "scenarioDimensionTemplateId": source.get(
                                    "scenario_dimension_template_id",
                                ),
                                "dimKey": source.get("dim_key"),
                            }
                            for source in source_projections
                        ]
                        if uses_compact_v3_sources
                        else [source.get("dim_key") for source in source_projections]
                    ),
                },
            },
        )

    saved = ScenarioService().save_mapping_proposals(
        int(state.scenario_group_id),
        proposals,
        int(state.user_id or 0),
    )
    ready = all(proposal.get("status") == "approved" for proposal in saved)
    ScenarioGroupService().set_parameter_mapping_ready(
        int(state.scenario_group_id),
        ready=ready,
        user_id=int(state.user_id or 0),
    )
    return validate_scenarios_state_update(
        mapping_proposals=saved,
        parameter_mapping_ready=ready,
    )


async def run_scenario_review(
    state: ValidateScenariosState,
    runtime: Runtime[TraceContext] | None = None,
) -> dict[str, object]:
    if state.status == "failure":
        return {}
    request_table = state.request_table.model_dump() if state.request_table is not None else {}
    subgraph_state = ScenarioReviewState(
        scenario_group_id=state.scenario_group_id,
        group=state.scenario_group.model_dump() if state.scenario_group is not None else {},
        events=[_model_or_dict_dump(event) for event in state.events],
        generation_diagnostics=state.generation_diagnostics,
        requested_rows=request_table.get("rows", []),
        requested_headers=request_table.get("headers", []),
        persisted_scenarios=[_model_or_dict_dump(scenario) for scenario in state.scenarios],
        template_dims=[_model_or_dict_dump(dimension) for dimension in state.dimension_template],
    )
    trace_context = runtime.context if runtime is not None else None
    result_state = await get_scenario_review_subgraph().ainvoke(
        subgraph_state,
        config=build_langgraph_config(trace_context) if trace_context is not None else None,
        context=trace_context,
    )
    result = (
        result_state
        if isinstance(result_state, ScenarioReviewState)
        else ScenarioReviewState.model_validate(result_state)
    )
    if result.skip_review:
        return {}
    if result.error:
        return validate_scenarios_state_update(status="failure", message=result.error, error=result.error)
    if result.report is None:
        message = "Scenario review report is missing"
        return validate_scenarios_state_update(status="failure", message=message, error=message)

    report = result.report
    validation_result = {
        "scenario_group_id": result.scenario_group_id,
        "scenario_count": len(result.requested_rows),
        "verdict": report.verdict,
        "summary": report.summary,
        "checks": [check.to_dict() for check in report.checks],
    }
    return validate_scenarios_state_update(
        is_valid=report.is_valid,
        reason=report.reason,
        validation_result=validation_result,
    )


def save_validation_result(state: ValidateScenariosState) -> dict[str, object]:
    if state.status == "failure" or state.scenario_group_id is None:
        return {}
    ScenarioService().update_status(state.scenario_group_id, ScenarioStatus.CREATING.value)
    next_stage = ScenarioGroupStage.SCENARIO_VALIDATED if state.is_valid else ScenarioGroupStage.SCENARIO_CREATED
    group = ScenarioGroupService().update_state(
        state.scenario_group_id,
        status=ScenarioGroupStatus.CREATING,
        stage=next_stage,
        user_id=state.user_id,
    )
    if group is None:
        raise MIBaseError(ErrorCode.UNKNOWN_ERROR, detail="Scenario group update failed")
    return validate_scenarios_state_update(
        scenario_group=group,
        status="success",
        message="Validation completed",
    )
