from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager, nullcontext
import hashlib
from typing import Any

from langgraph.runtime import Runtime

from apps.agents.scenario_group_agent.constants import AGENT_NAME
from apps.agents.scenario_group_agent.flows.validate_scenarios.state import (
    ValidateScenariosState,
    validate_scenarios_state_update,
)
from apps.agents.scenario_group_agent.flows.validate_scenarios.v4_validation import (
    V4_GENERATION_STRATEGY,
    V4AdditionalDimensionAutofillRequest,
    analyze_v4_validation_request,
    apply_v4_additional_dimension_autofill_selections,
    build_autofill_checks,
    build_restoration_checks,
    build_v4_additional_dimension_autofill_plan,
    check_counts,
    normalize_v4_probability_scores,
    rebase_v4_pressure_bands,
    render_reason_markdown,
    validate_v4_pressure_aggregate,
)
from apps.agents.scenario_group_agent.persistence.event_service import EventService
from apps.agents.scenario_group_agent.persistence.scenario_group_operation_service import (
    ScenarioGroupOperationService,
)
from apps.agents.scenario_group_agent.persistence.scenario_group_service import (
    ScenarioGroupService,
)
from apps.agents.scenario_group_agent.persistence.scenario_service import (
    ScenarioService,
)
from apps.agents.scenario_group_agent.prompts.scenario_validation import (
    V4AdditionalDimensionValueSelectionOutput,
    V4ValidationGeneratedScenariosOutput,
    build_v4_additional_dimension_value_selection_messages,
    build_v4_validation_generation_messages,
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
from apps.common.logging.logger_config import logger
from apps.common.tracing.context import TraceContext, build_langgraph_config
from apps.common.values.error_codes import ErrorCode
from apps.persistence.enums import (
    ScenarioGroupStage,
    ScenarioGroupStatus,
    ScenarioStatus,
)
from apps.persistence.scenario_group_operation.schema import (
    ValidationCheckPayload,
    ValidationGeneratedDetailPayload,
    ValidationGeneratedFieldsPayload,
    ValidationOperationResultPayload,
    ValidationResultPayload,
    ValidationScenarioChangeSetPayload,
    ValidationScenarioUpsertPayload,
)


def _model_or_dict_dump(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return dict(value)


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
    if state.scenario_group is not None and state.scenario_group.generation_strategy == V4_GENERATION_STRATEGY:
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
    if state.scenario_group is not None and state.scenario_group.generation_strategy == V4_GENERATION_STRATEGY:
        return await _run_v4_scenario_validation(state, runtime=runtime)
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


async def _invoke_v4_generated_fields(
    *,
    rows: list[dict[str, Any]],
    dimension_definitions: list[dict[str, Any]],
    events: list[dict[str, Any]],
    generation_diagnostics: dict[str, Any],
    trace_context: TraceContext | None,
) -> V4ValidationGeneratedScenariosOutput:
    from apps.common.configs.config import get_settings
    from apps.connectors.llm.llm_client import invoke_llm_structured_output

    cfg = get_settings()
    invocation = await invoke_llm_structured_output(
        V4ValidationGeneratedScenariosOutput,
        messages=build_v4_validation_generation_messages(
            rows=rows,
            dimension_definitions=dimension_definitions,
            events=events,
            generation_diagnostics=generation_diagnostics,
        ),
        trace_context=trace_context,
        stream=cfg.llm_stream_enabled,
        reasoning_effort=cfg.llm_reasoning_effort,
    )
    return invocation.result


@contextmanager
def _v4_autofill_selection_span(*, request_count: int) -> Iterator[Any | None]:
    try:
        from apps.common.configs.config import get_settings

        settings = get_settings()
        is_enabled = getattr(settings, "is_mlflow_tracing_enabled", None)
        enabled = (
            bool(is_enabled(agent_name=AGENT_NAME))
            if callable(is_enabled)
            else bool(getattr(settings, "mlflow_tracing_enabled", False))
        )
    except Exception as exc:
        logger.warning("v4 Additional Dimension value-selection span disabled | error={!r}", exc)
        with nullcontext(None) as span:
            yield span
        return
    if not enabled:
        with nullcontext(None) as span:
            yield span
        return
    try:
        import mlflow

        manager = mlflow.start_span(
            name="v4_additional_dimension_value_selection",
            span_type="CHAIN",
            attributes={"request_count": request_count, "selection_scope": "allowed_values_only"},
        )
        span = manager.__enter__()
    except Exception as exc:
        logger.warning("v4 Additional Dimension value-selection span enter failed | error={!r}", exc)
        with nullcontext(None) as fallback_span:
            yield fallback_span
        return
    try:
        yield span
    except BaseException as exc:
        try:
            manager.__exit__(type(exc), exc, exc.__traceback__)
        except Exception as span_exc:
            logger.warning("v4 Additional Dimension value-selection span exit failed | error={!r}", span_exc)
        raise
    else:
        try:
            manager.__exit__(None, None, None)
        except Exception as exc:
            logger.warning("v4 Additional Dimension value-selection span exit failed | error={!r}", exc)


async def _invoke_v4_autofill_selections(
    *,
    requests: list[V4AdditionalDimensionAutofillRequest],
    events: list[dict[str, Any]],
    generation_diagnostics: dict[str, Any],
    trace_context: TraceContext | None,
) -> dict[tuple[str, str], str]:
    from apps.common.configs.config import get_settings
    from apps.connectors.llm.llm_client import invoke_llm_structured_output

    cfg = get_settings()
    allowed_by_key = {
        (request.client_row_key, request.dimension_id): {
            str(value.get("value_id") or value.get("valueId")) for value in request.allowed_values
        }
        for request in requests
    }
    messages = build_v4_additional_dimension_value_selection_messages(
        selections=[
            {
                "clientRowKey": request.client_row_key,
                "dimensionId": request.dimension_id,
                "targetDirection": request.target_direction,
                "existingPressureScore": request.existing_pressure_score,
                "title": request.title,
                "narrative": request.narrative,
                "existingCells": request.existing_cells,
                "allowedValues": request.allowed_values,
            }
            for request in requests
        ],
        events=events,
        generation_diagnostics=generation_diagnostics,
    )
    with _v4_autofill_selection_span(request_count=len(requests)) as span:
        invocation = await invoke_llm_structured_output(
            V4AdditionalDimensionValueSelectionOutput,
            messages=messages,
            trace_context=trace_context,
            stream=cfg.llm_stream_enabled,
            reasoning_effort=cfg.llm_reasoning_effort,
        )
        items = invocation.result.items
        actual_keys = [(item.client_row_key, item.dimension_id) for item in items]
        if len(actual_keys) != len(set(actual_keys)) or set(actual_keys) != set(allowed_by_key):
            raise MIBaseError(
                ErrorCode.LLM_INVALID_RESPONSE_ERROR,
                detail=(
                    "v4 Additional Dimension value-selection 응답 key 불일치: "
                    f"누락={sorted(set(allowed_by_key) - set(actual_keys))}, "
                    f"여분={sorted(set(actual_keys) - set(allowed_by_key))}"
                ),
            )
        selections = {key: item.value_id for key, item in zip(actual_keys, items, strict=True)}
        invalid = [f"{key}={value_id}" for key, value_id in selections.items() if value_id not in allowed_by_key[key]]
        if invalid:
            raise MIBaseError(
                ErrorCode.LLM_INVALID_RESPONSE_ERROR,
                detail=f"v4 Additional Dimension value-selection 허용 범위 위반: {invalid}",
            )
        if span is not None:
            try:
                span.set_attributes({"selection_count": len(selections), "invalid_selection_count": 0})
            except Exception as exc:
                logger.warning("v4 Additional Dimension value-selection span result logging failed | error={!r}", exc)
        return selections


def _persisted_generated_fields(scenario: dict[str, Any]) -> ValidationGeneratedFieldsPayload:
    pressure_band = scenario.get("global_pressure_band") or scenario.get("pressure_band")
    pressure_rationale = scenario.get("global_pressure_rationale") or scenario.get("pressure_rationale")
    narrative = str(scenario.get("narrative") or scenario.get("description") or "").strip()
    if not narrative or not pressure_band or not pressure_rationale:
        raise MIBaseError(
            ErrorCode.SCENARIO_VALIDATION_INPUT_ERROR,
            detail=f"v4 Scenario 저장 필드가 불완전합니다: scenarioId={scenario.get('scenario_id')}",
        )
    return ValidationGeneratedFieldsPayload(
        narrative=narrative,
        probability_score=float(scenario.get("probability_score") or 0),
        probability_delta=float(scenario.get("probability_delta") or 0),
        pressure_band=str(pressure_band),
        pressure_rationale=str(pressure_rationale),
        related_markets=list(scenario.get("related_markets") or []),
    )


def _review_check_payload(check: dict[str, Any]) -> ValidationCheckPayload:
    status = str(check.get("status") or "INFO")
    return ValidationCheckPayload(
        check_id=str(check.get("check_id") or "V4_SEMANTIC_REVIEW"),
        status=status,
        blocking=status == "FAIL",
        detail=str(check.get("detail") or ""),
        offenders=[str(item) for item in check.get("offenders") or []],
        advice=[str(item) for item in check.get("advice") or []],
    )


async def _run_v4_scenario_validation(
    state: ValidateScenariosState,
    *,
    runtime: Runtime[TraceContext] | None,
) -> dict[str, object]:
    if state.scenario_group is None:
        raise MIBaseError(ErrorCode.ENTITY_NOT_FOUND, detail="Scenario group is required")
    request_table = state.request_table.model_dump() if state.request_table is not None else {}
    persisted = [_model_or_dict_dump(scenario) for scenario in state.scenarios]
    diagnostics = dict(state.generation_diagnostics or {})
    trace_context = runtime.context if runtime is not None else None
    stored_header_order = [str(item) for item in state.scenario_group.dimension_selected or []]
    autofill_plan = build_v4_additional_dimension_autofill_plan(
        request_table=request_table,
        persisted_scenarios=persisted,
        dimension_definitions=list(state.scenario_group.dimension_definitions or []),
        generation_diagnostics=diagnostics,
        stored_header_order=stored_header_order,
    )
    if autofill_plan.requests and not any(check.blocking for check in autofill_plan.checks):
        selections = await _invoke_v4_autofill_selections(
            requests=autofill_plan.requests,
            events=[_model_or_dict_dump(event) for event in state.events],
            generation_diagnostics=diagnostics,
            trace_context=trace_context,
        )
        try:
            apply_v4_additional_dimension_autofill_selections(autofill_plan, selections)
        except ValueError as exc:
            raise MIBaseError(ErrorCode.LLM_INVALID_RESPONSE_ERROR, detail=str(exc)) from exc
    request_table = autofill_plan.request_table
    analysis = analyze_v4_validation_request(
        request_table=request_table,
        persisted_scenarios=persisted,
        dimension_definitions=list(state.scenario_group.dimension_definitions or []),
        generation_diagnostics=diagnostics,
        stored_header_order=stored_header_order,
        autofilled_cells=autofill_plan.assignments,
    )
    definitions = analysis.requested_dimension_definitions
    selected_diagnostics = {
        key: value
        for key, value in diagnostics.items()
        if key
        not in {
            "additional_dimension_generation",
            "additionalDimensionGeneration",
            "additional_dimension_candidates",
            "additionalDimensionCandidates",
        }
    }
    checks = [
        *autofill_plan.checks,
        *analysis.checks,
        *build_autofill_checks(autofill_plan.assignments),
        *build_restoration_checks(autofill_plan.restorations),
    ]
    generated_details: list[ValidationGeneratedDetailPayload] = []

    semantic_rows = [
        row
        for row in analysis.changed_rows
        if row.change_type in {"NEW", "TITLE_CHANGED", "COMBINATION_CHANGED", "AUTOFILL_ONLY"}
    ]
    if not any(check.blocking and check.status == "FAIL" for check in checks) and semantic_rows:
        review_state = ScenarioReviewState(
            scenario_group_id=state.scenario_group_id,
            group=state.scenario_group.model_dump(),
            events=[_model_or_dict_dump(event) for event in state.events],
            generation_diagnostics=selected_diagnostics,
            requested_rows=[row.as_review_row() for row in analysis.canonical_rows],
            requested_headers=[{"key": key} for key in analysis.canonical_headers],
            persisted_scenarios=persisted,
            template_dims=[
                dimension.model_dump() for dimension in ScenarioService().load_group_dimension_template(definitions)
            ],
            review_scenario_ids=[row.review_scenario_id() for row in semantic_rows],
        )
        review_output = await get_scenario_review_subgraph().ainvoke(
            review_state,
            config=build_langgraph_config(trace_context) if trace_context is not None else None,
            context=trace_context,
        )
        reviewed = (
            review_output
            if isinstance(review_output, ScenarioReviewState)
            else ScenarioReviewState.model_validate(review_output)
        )
        if reviewed.error:
            raise MIBaseError(ErrorCode.LLM_INVOCATION_ERROR, detail=reviewed.error)
        if reviewed.report is None:
            raise MIBaseError(ErrorCode.LLM_INVALID_RESPONSE_ERROR, detail="Scenario review report is missing")
        checks.extend(_review_check_payload(check.to_dict()) for check in reviewed.report.checks)

    blocking = any(check.blocking and check.status == "FAIL" for check in checks)
    change_set: ValidationScenarioChangeSetPayload | None = None
    if not blocking and not analysis.unchanged:
        generation_targets = [
            row for row in analysis.changed_rows if row.change_type in {"NEW", "COMBINATION_CHANGED", "AUTOFILL_ONLY"}
        ]
        generated_by_key: dict[str, ValidationGeneratedFieldsPayload] = {}
        if generation_targets:
            generated_output = await _invoke_v4_generated_fields(
                rows=[
                    {
                        "clientRowKey": row.client_row_key,
                        "title": row.title,
                        "dimensionValues": row.dimension_values,
                    }
                    for row in generation_targets
                ],
                dimension_definitions=definitions,
                events=[_model_or_dict_dump(event) for event in state.events],
                generation_diagnostics=selected_diagnostics,
                trace_context=trace_context,
            )
            expected_keys = {row.client_row_key for row in generation_targets}
            actual_keys = {item.client_row_key for item in generated_output.items}
            if len(generated_output.items) != len(actual_keys) or actual_keys != expected_keys:
                raise MIBaseError(
                    ErrorCode.LLM_INVALID_RESPONSE_ERROR,
                    detail=(
                        "v4 Validation 생성 필드 row key 불일치: "
                        f"누락={sorted(expected_keys - actual_keys)}, 여분={sorted(actual_keys - expected_keys)}"
                    ),
                )
            for item in generated_output.items:
                fields = ValidationGeneratedFieldsPayload(
                    narrative=item.narrative,
                    probability_score=item.probability_score,
                    probability_delta=0,
                    pressure_band=item.pressure_band,
                    pressure_rationale=item.pressure_rationale,
                    related_markets=[market.model_dump() for market in item.related_markets],
                )
                generated_by_key[item.client_row_key] = fields

        persisted_by_id = {int(item["scenario_id"]): item for item in persisted}
        fields_by_key: dict[str, ValidationGeneratedFieldsPayload] = {}
        for row in analysis.canonical_rows:
            if row.scenario_id is not None:
                fields_by_key[row.client_row_key] = _persisted_generated_fields(persisted_by_id[row.scenario_id])
        for row in generation_targets:
            generated_fields = generated_by_key.get(row.client_row_key)
            if generated_fields is None:
                raise MIBaseError(
                    ErrorCode.LLM_INVALID_RESPONSE_ERROR,
                    detail=f"v4 Scenario 생성 필드가 누락되었습니다: {row.client_row_key}",
                )
            if row.change_type == "AUTOFILL_ONLY" and row.scenario_id is not None:
                persisted_fields = fields_by_key[row.client_row_key]
                generated_fields = persisted_fields.model_copy(
                    update={
                        "narrative": generated_fields.narrative,
                        "pressure_rationale": generated_fields.pressure_rationale,
                    }
                )
            fields_by_key[row.client_row_key] = generated_fields

        normalize_probabilities = bool(analysis.deleted_scenario_ids) or any(
            row.change_type in {"NEW", "COMBINATION_CHANGED"} for row in analysis.changed_rows
        )
        if normalize_probabilities:
            normalized_scores = normalize_v4_probability_scores(
                [fields_by_key[row.client_row_key].probability_score for row in analysis.canonical_rows]
            )
            for row, probability_score in zip(analysis.canonical_rows, normalized_scores, strict=True):
                fields_by_key[row.client_row_key] = fields_by_key[row.client_row_key].model_copy(
                    update={"probability_score": float(probability_score)}
                )

        # 생성 단계와 같게 pressure band는 Base 대비 상대값이다. 편집으로 Base나 조합이 바뀔 수 있으므로
        # 새 행의 LLM band를 포함해 모든 행의 band를 Base 대비로 다시 계산한다.
        baseline_row_key, rebased_bands = rebase_v4_pressure_bands(
            rows=analysis.canonical_rows,
            dimension_definitions=definitions,
            probability_scores={
                row.client_row_key: float(fields_by_key[row.client_row_key].probability_score)
                for row in analysis.canonical_rows
            },
        )
        for row in analysis.canonical_rows:
            fields_by_key[row.client_row_key] = fields_by_key[row.client_row_key].model_copy(
                update={"pressure_band": rebased_bands[row.client_row_key]}
            )
        checks.extend(
            validate_v4_pressure_aggregate(
                rows=analysis.canonical_rows,
                dimension_definitions=definitions,
                pressure_bands=rebased_bands,
                baseline_row_key=baseline_row_key,
            )
        )
        blocking = any(check.blocking and check.status == "FAIL" for check in checks)
        upserts: list[ValidationScenarioUpsertPayload] = []
        changed_by_key = {row.client_row_key: row for row in analysis.changed_rows}
        upsert_keys = set(changed_by_key)
        if normalize_probabilities:
            for row in analysis.canonical_rows:
                if row.scenario_id is None:
                    upsert_keys.add(row.client_row_key)
                    continue
                persisted_score = _persisted_generated_fields(persisted_by_id[row.scenario_id]).probability_score
                if fields_by_key[row.client_row_key].probability_score != persisted_score:
                    upsert_keys.add(row.client_row_key)
        for row in analysis.canonical_rows:
            if row.client_row_key not in upsert_keys:
                continue
            generated_fields = fields_by_key[row.client_row_key]
            change_type = row.change_type or "PROBABILITY_RENORMALIZED"
            upserts.append(
                ValidationScenarioUpsertPayload(
                    scenario_id=row.scenario_id,
                    client_row_key=row.client_row_key,
                    change_type=change_type,
                    display_order=row.display_order,
                    title=row.title,
                    dimension_values=row.dimension_values,
                    generated_fields=generated_fields,
                )
            )
            if row.client_row_key in generated_by_key:
                generated_details.append(
                    ValidationGeneratedDetailPayload(
                        client_row_key=row.client_row_key,
                        scenario_id=row.scenario_id,
                        title=row.title,
                        narrative=generated_fields.narrative,
                        probability_score=generated_fields.probability_score,
                        pressure_band=generated_fields.pressure_band,
                        pressure_rationale=generated_fields.pressure_rationale,
                        related_markets=generated_fields.related_markets,
                    )
                )
        if not blocking:
            change_set = ValidationScenarioChangeSetPayload(
                upserts=upserts,
                delete_scenario_ids=analysis.deleted_scenario_ids,
            )

    warning_count = sum(1 for check in checks if check.status == "WARN" and not check.blocking)
    can_proceed = not blocking
    if analysis.unchanged:
        reason = "변경된 내용이 없어 바로 진행할 수 있습니다."
        mode = "unchanged"
        review_skipped = True
    else:
        reason = render_reason_markdown(checks, analysis=analysis)
        mode = "blocked" if blocking else "changed"
        review_skipped = False
    validation_result = ValidationResultPayload(
        verdict="BLOCK" if blocking else "PASS_WITH_WARNINGS" if warning_count else "PASS",
        is_valid=can_proceed,
        can_proceed=can_proceed,
        review_skipped=review_skipped,
        summary=check_counts(checks),
        checks=checks,
        generated_details=generated_details,
        reason_markdown=reason,
    )
    operation_result = ValidationOperationResultPayload(
        mode=mode,
        base_scenario_fingerprint=analysis.base_scenario_fingerprint,
        dimension_definition_fingerprint=analysis.dimension_definition_fingerprint,
        base_dimension_definition_fingerprint=analysis.base_dimension_definition_fingerprint,
        requested_dimension_ids=analysis.canonical_headers,
        requested_dimension_definitions=definitions,
        promoted_dimension_ids=analysis.promoted_dimension_ids,
        candidate_source_fingerprint=analysis.candidate_source_fingerprint,
        validation_result=validation_result,
        scenario_change_set=change_set if can_proceed and mode == "changed" else None,
    )
    return validate_scenarios_state_update(
        is_valid=can_proceed,
        can_proceed=can_proceed,
        review_skipped=review_skipped,
        reason=reason,
        validation_result={
            "scenario_group_id": state.scenario_group_id,
            "scenario_count": len(analysis.canonical_rows),
            "verdict": validation_result.verdict,
            "summary": validation_result.summary,
            "checks": [check.model_dump() for check in checks],
        },
        operation_result=operation_result,
        request_table={
            "headers": request_table.get("headers") or [],
            "rows": [row.as_review_row() for row in analysis.canonical_rows],
        },
    )


def save_validation_result(state: ValidateScenariosState) -> dict[str, object]:
    if state.status == "failure" or state.scenario_group_id is None:
        return {}
    if state.scenario_group is not None and state.scenario_group.generation_strategy == V4_GENERATION_STRATEGY:
        if state.operation_id is None or state.operation_result is None or state.user_id is None:
            raise MIBaseError(
                ErrorCode.UNKNOWN_ERROR,
                detail="v4 Validation operation result is incomplete",
            )
        group = ScenarioGroupOperationService().complete_validation(
            scenario_group_id=state.scenario_group_id,
            operation_id=state.operation_id,
            result_payload=state.operation_result,
            user_id=state.user_id,
        )
        return validate_scenarios_state_update(
            scenario_group=group,
            status="success",
            message="Validation completed",
        )
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
