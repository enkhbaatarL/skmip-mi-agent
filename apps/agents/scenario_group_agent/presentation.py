from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from decimal import Decimal
import html
import re
from typing import Any

from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.v4_enums import (
    StateDirection,
)
from apps.agents.scenario_group_agent.flows.validate_scenarios.api_schema import ValidateScenariosIn
from apps.agents.scenario_group_agent.persistence.scenario_service import (
    ScenarioService,
)
from apps.agents.scenario_group_agent.schemas.api.manage_scenario_groups import (
    ScenarioGroupDetailOut,
    ScenarioGroupTableViewGroup,
    ScenarioGroupTableViewOut,
)
from apps.agents.scenario_group_agent.schemas.api.presentation_followup_requests import (
    PresentationFollowUpRequestBodiesOut,
)
from apps.agents.scenario_group_agent.schemas.api.scenario_group_presentation import (
    PresentationCellEvidence,
    PresentationDimensionDefinition,
    PresentationDimensionDefinitions,
    PresentationDimensionValue,
    PresentationMarkdownSection,
    PresentationOperation,
    PresentationScenarioDesign,
    PresentationScenarioHeader,
    PresentationScenarioRow,
    PresentationScenarioTable,
    PresentationSections,
    ScenarioGroupPresentationOut,
)
from apps.agents.scenario_group_agent.schemas.endpoint import CreateSignpostsIn
from apps.agents.scenario_group_agent.schemas.table import (
    ScenarioGroupQueryPayload,
    ScenarioGroupTableData,
    ScenarioHeader,
    ScenarioMetrics,
    ScenarioQueryRow,
    ScenarioQueryTable,
    ScenarioRow,
    ScenarioTable,
    SignpostBasePayload,
    SignpostQueryPayload,
)
from apps.agents.scenario_group_agent.utils.dimension_values import (
    find_scenario_pressure_breakdown,
)
from apps.persistence.event.schema import EventPayload
from apps.persistence.scenario_group.schema import (
    ScenarioGroupPayload,
)
from apps.persistence.scenario_group_operation.schema import ScenarioGroupOperationPayload


PRESENTATION_RENDERER_VERSION = "v7"


def build_presentation_follow_up_request_bodies(
    presentation: ScenarioGroupPresentationOut,
    *,
    user_id: int,
) -> PresentationFollowUpRequestBodiesOut:
    """Build initial Validation and Signpost request bodies from a Presentation read model."""
    scenario_table = presentation.sections.scenario_design.scenario_table
    operation_id = presentation.operation.operation_id if presentation.operation is not None else None
    if scenario_table.status != "ready":
        return PresentationFollowUpRequestBodiesOut(
            scenario_group_id=presentation.scenario_group_id,
            operation_id=operation_id,
            scenario_table_status=scenario_table.status,
            ready=False,
            reason="scenarioTable.status가 ready가 아니므로 후속 요청 body를 생성할 수 없습니다.",
        )

    table = {
        "headers": [
            {
                "key": header.key,
                "label": header.label,
                "display_order": header.display_order,
            }
            for header in scenario_table.headers
        ],
        "rows": [
            {
                "scenario_id": row.scenario_id,
                "display_order": row.display_order,
                "title": row.title,
                "cells": dict(row.cells),
            }
            for row in scenario_table.rows
        ],
    }
    validation_request = ValidateScenariosIn(user_id=user_id, table=table)
    signpost_request = CreateSignpostsIn(user_id=user_id, table=table)
    return PresentationFollowUpRequestBodiesOut(
        scenario_group_id=presentation.scenario_group_id,
        operation_id=operation_id,
        scenario_table_status=scenario_table.status,
        ready=True,
        validation_request_body=validation_request,
        signpost_request_body=signpost_request,
    )


def build_scenario_group_table_data(
    group: dict[str, Any],
    scenarios: list[dict[str, Any]],
    signposts: list[dict[str, Any]] | None = None,
) -> ScenarioGroupTableData:
    template_by_key, selected_keys, headers = _build_headers(group)
    signposts_by_scenario_id = _group_signposts(signposts)
    pressure_target = _pressure_target(group)

    rows: list[ScenarioRow] = []
    for scenario in scenarios:
        scenario_id = int(scenario["scenario_id"])
        rows.append(
            ScenarioRow(
                **_row_common_payload(scenario, template_by_key, selected_keys, pressure_target),
                signposts=[
                    SignpostBasePayload(
                        signpost_id=int(signpost["signpost_id"]),
                        label=signpost.get("label") or "",
                        probability_direction_code=signpost.get("probability_direction_code"),
                        probability_impact_score=signpost.get("probability_impact_score"),
                        signpost_reason=signpost.get("signpost_reason"),
                        display_order=int(signpost.get("display_order") or 0),
                        strength=signpost.get("strength"),
                        use_yn=signpost.get("use_yn"),
                        keyword_hints=signpost.get("keyword_hints") or [],
                    )
                    for signpost in signposts_by_scenario_id.get(scenario_id, [])
                ],
            )
        )

    return ScenarioGroupTableData(
        scenario_group=ScenarioGroupPayload.model_validate(group),
        table=ScenarioTable(headers=headers, rows=rows),
    )


def build_scenario_group_query_data(
    group: dict[str, Any],
    scenarios: list[dict[str, Any]],
    signposts: list[dict[str, Any]] | None = None,
) -> ScenarioGroupDetailOut:
    template_by_key, selected_keys, headers = _build_headers(group)
    signposts_by_scenario_id = _group_signposts(signposts)
    pressure_target = _pressure_target(group)

    rows: list[ScenarioQueryRow] = []
    for scenario in scenarios:
        scenario_id = int(scenario["scenario_id"])
        rows.append(
            ScenarioQueryRow(
                **_row_common_payload(scenario, template_by_key, selected_keys, pressure_target),
                del_yn=scenario.get("del_yn") or "N",
                signposts=[
                    SignpostQueryPayload(
                        signpost_id=int(signpost["signpost_id"]),
                        label=signpost.get("label") or "",
                        probability_direction_code=signpost.get("probability_direction_code"),
                        probability_impact_score=signpost.get("probability_impact_score"),
                        signpost_reason=signpost.get("signpost_reason"),
                        display_order=int(signpost.get("display_order") or 0),
                        strength=signpost.get("strength"),
                        use_yn=signpost.get("use_yn"),
                        keyword_hints=signpost.get("keyword_hints") or [],
                        del_yn=signpost.get("del_yn") or "N",
                    )
                    for signpost in signposts_by_scenario_id.get(scenario_id, [])
                ],
            )
        )

    signposts_list = signposts or []
    return ScenarioGroupDetailOut(
        scenario_group=ScenarioGroupQueryPayload.model_validate(group),
        table=ScenarioQueryTable(headers=headers, rows=rows),
        scenario_count=sum(1 for scenario in scenarios if scenario.get("del_yn") != "Y"),
        signpost_count=sum(1 for signpost in signposts_list if signpost.get("del_yn") != "Y"),
        deleted_scenario_count=sum(1 for scenario in scenarios if scenario.get("del_yn") == "Y"),
        deleted_signpost_count=sum(1 for signpost in signposts_list if signpost.get("del_yn") == "Y"),
    )


def build_common_scenario_group_query_data(
    *,
    group: dict[str, Any],
    scenarios: list[dict[str, Any]],
    signposts: list[dict[str, Any]],
    events: list[EventPayload],
    latest_operation: ScenarioGroupOperationPayload | None,
) -> ScenarioGroupDetailOut:
    detail = build_scenario_group_query_data(group, scenarios, signposts)
    latest_payload = latest_operation.model_dump(mode="json", by_alias=True) if latest_operation is not None else None
    detail.latest_operation = latest_payload
    detail.active_operation = (
        latest_payload if latest_operation is not None and latest_operation.status in {"queued", "running"} else None
    )
    scenario_group = detail.scenario_group
    legacy = scenario_group.api_version == "v1"
    presentation_snapshot: dict[str, Any] = {
        "schemaVersion": "v1",
        "apiVersion": scenario_group.api_version,
        "generationStrategy": scenario_group.generation_strategy,
        "impactCatalogVersion": scenario_group.impact_catalog_version,
        "legacy": legacy,
        "warnings": (["legacy v1 데이터에는 상세 근거가 저장되지 않았습니다"] if legacy else []),
        "scenarioGroup": scenario_group.model_dump(mode="json", by_alias=True),
        "events": [event.model_dump(mode="json", by_alias=True) for event in events],
        "dimensionDefinitions": scenario_group.dimension_definitions,
        "table": detail.table.model_dump(mode="json", by_alias=True),
        "generationDiagnostics": scenario_group.generation_diagnostics,
    }
    if latest_operation is not None and latest_operation.presentation_snapshot:
        stored_snapshot = dict(latest_operation.presentation_snapshot)
        stored_snapshot.pop("events", None) # events는 operation 완료 시점이 아니라, 그룹 생성 시점에 고정된 mi_event_snapshot_id 기반 값을 항상 우선한다
        presentation_snapshot.update(stored_snapshot)
    detail.presentation_snapshot = presentation_snapshot
    return detail


def build_scenario_group_table_view_data(detail: ScenarioGroupDetailOut) -> ScenarioGroupTableViewOut:
    scenario_group = detail.scenario_group
    labels_by_key = {header.key: header.label for header in detail.table.headers}
    dimension_selected = [
        f"{dimension_key}|{labels_by_key[dimension_key]}" if labels_by_key.get(dimension_key) else dimension_key
        for dimension_key in scenario_group.dimension_selected
    ]
    return ScenarioGroupTableViewOut(
        scenario_group=ScenarioGroupTableViewGroup(
            del_yn=scenario_group.del_yn,
            scenario_group_id=scenario_group.scenario_group_id,
            mi_event_id=scenario_group.mi_event_id,
            event_type_l2_id=scenario_group.event_type_l2_id,
            request_usr_id=scenario_group.request_usr_id,
            title=scenario_group.title,
            summary=scenario_group.summary,
            description=scenario_group.description,
            dimension_selected=dimension_selected,
            scenario_count=scenario_group.scenario_count,
            status=scenario_group.status,
            stage=scenario_group.stage,
            api_version=scenario_group.api_version,
        ),
        table=detail.table,
    )


def _build_headers(
    group: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], list[str], list[ScenarioHeader]]:
    dimension_definitions = group.get("dimension_definitions") or []
    if dimension_definitions:
        template_by_key: dict[str, dict[str, Any]] = {}
        for index, item in enumerate(dimension_definitions, start=1):
            if not isinstance(item, dict):
                continue
            dimension_id = item.get("dimension_id", item.get("dimensionId"))
            if not dimension_id:
                continue
            values = item.get("values") or []
            template_by_key[str(dimension_id)] = {
                "dim_key": dimension_id,
                "label": item.get("label"),
                "description": item.get("description"),
                "required": item.get("required", False),
                "display_order": item.get("display_order", item.get("displayOrder", index)),
                "value_enums": [
                    value.get("label") for value in values if isinstance(value, dict) and value.get("label")
                ],
                "value_labels_by_id": _value_labels_by_id(values),
                "value_ids_by_label": _value_ids_by_unique_label(values),
            }
    else:
        event_type_l2_id = group.get("event_type_l2_id")
        template_json = (
            ScenarioService()._load_template_json_from_db(
                int(event_type_l2_id),
            )
            if event_type_l2_id is not None
            else []
        )
        template_by_key = {
            str(item.get("dim_key")): item for item in template_json if isinstance(item, dict) and item.get("dim_key")
        }
    selected_keys = [str(key) for key in group.get("dimension_selected") or []]
    headers = [
        ScenarioHeader(
            key=key,
            label=str(template_by_key.get(key, {}).get("label") or key),
            display_order=index,
        )
        for index, key in enumerate(selected_keys, start=1)
    ]
    return template_by_key, selected_keys, headers


def _group_signposts(
    signposts: list[dict[str, Any]] | None,
) -> dict[int, list[dict[str, Any]]]:
    signposts_by_scenario_id: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for signpost in signposts or []:
        signposts_by_scenario_id[int(signpost["scenario_id"])].append(signpost)
    return signposts_by_scenario_id


def _row_common_payload(
    scenario: dict[str, Any],
    template_by_key: dict[str, dict[str, Any]],
    selected_keys: list[str],
    pressure_target: str | None,
) -> dict[str, Any]:
    raw_values = scenario.get("dimension_values") or {}
    cells = {key: _canonical_cell_value(raw_values.get(key), template_by_key.get(key)) for key in selected_keys}
    return {
        "scenario_id": int(scenario["scenario_id"]),
        "display_order": int(scenario.get("display_order") or 0),
        "title": scenario.get("title") or "",
        "narrative": scenario.get("narrative"),
        "cells": cells,
        "metrics": ScenarioMetrics(
            probability_score=scenario.get("probability_score"),
            probability_delta=scenario.get("probability_delta"),
        ),
        "baseline_yn": scenario.get("baseline_yn"),
        "pressure_target": pressure_target,
        "pressure_band": scenario.get("global_pressure_band"),
        "scenario_role": scenario.get("scenario_role"),
        "probability_score": scenario.get("probability_score"),
        "pressure_rationale": scenario.get("global_pressure_rationale"),
        "related_markets": [
            item
            for item in (scenario.get("related_markets") or [])
            if isinstance(item, dict) and item.get("market") in {"TTF", "HH"}
        ],
    }


def _pressure_target(group: dict[str, Any]) -> str | None:
    return "JKM" if group.get("api_version") in {"v2", "v3", "v4"} else None


def _canonical_cell_value(value: Any, template: dict[str, Any] | None) -> Any:
    if value is None or not template:
        return value
    text = str(value)
    if text in (template.get("value_labels_by_id") or {}):
        return text
    return (template.get("value_ids_by_label") or {}).get(text, value)


def _value_labels_by_id(values: Any) -> dict[str, str]:
    if not isinstance(values, list):
        return {}
    labels: dict[str, str] = {}
    for value in values:
        if not isinstance(value, dict):
            continue
        value_id = value.get("value_id", value.get("valueId"))
        label = value.get("label")
        if value_id is not None and label:
            labels[str(value_id)] = str(label)
    return labels


def _value_ids_by_unique_label(values: Any) -> dict[str, str]:
    candidates: dict[str, list[str]] = defaultdict(list)
    for value in values or []:
        if not isinstance(value, dict):
            continue
        value_id = value.get("value_id", value.get("valueId"))
        label = value.get("label")
        if value_id is not None and label:
            candidates[str(label)].append(str(value_id))
    return {label: ids[0] for label, ids in candidates.items() if len(ids) == 1}


def build_scenario_group_presentation(
    *,
    hide_price_pressure: bool,
    group: dict[str, Any],
    scenarios: list[dict[str, Any]],
    signposts: list[dict[str, Any]],
    events: list[EventPayload],
    operation: ScenarioGroupOperationPayload | None,
    lever_labels: dict[str, str] | None = None,
    legacy_template_dimensions: list[dict[str, Any]] | None = None,
    current_template_dimensions: list[dict[str, Any]] | None = None,
) -> ScenarioGroupPresentationOut:
    """Build the screen read model only from committed, validated data."""
    del signposts  # Presentation v1 does not render Signposts.
    engine_version = str(group.get("api_version") or (operation.engine_version if operation else "v1"))
    legacy = engine_version == "v1"
    snapshot = operation.presentation_snapshot if operation is not None else {}
    source_events = _presentation_events(events, snapshot, prefer_snapshot=legacy)
    diagnostics = group.get("generation_diagnostics") or _presentation_source(
        snapshot,
        "generationDiagnostics",
        "generation_diagnostics",
    )
    raw_definitions = group.get("dimension_definitions") or []
    if not raw_definitions and not legacy:
        raw_definitions = _presentation_source(
            snapshot,
            "dimensionDefinitions",
            "dimension_definitions",
        )
    warnings: list[str] = []
    if legacy:
        warnings.append("기존 v1 데이터에는 상세 생성 근거가 저장되지 않았습니다.")

    selected_order = [str(item) for item in group.get("dimension_selected") or []]
    if isinstance(raw_definitions, list) and selected_order:
        raw_definition_by_id = {
            str(_field(item, "dimension_id") or ""): item
            for item in raw_definitions
            if isinstance(item, dict) and _field(item, "dimension_id")
        }
        selected_raw_definitions: Any = [
            raw_definition_by_id[dimension_id]
            for dimension_id in selected_order
            if dimension_id in raw_definition_by_id
        ]
    else:
        selected_raw_definitions = raw_definitions
    definitions = build_presentation_dimension_definitions(
        selected_raw_definitions,
        engine_version=engine_version,
    )
    if legacy and not definitions:
        definitions = _legacy_dimension_definitions(
            group=group,
            scenarios=scenarios,
            trusted_template_dimensions=legacy_template_dimensions or [],
            current_template_dimensions=current_template_dimensions or [],
        )
        if any(definition.source == "legacy_observed" for definition in definitions):
            warnings.append("Dimension 정의를 저장된 Scenario 관찰값에서 제한적으로 복원했습니다.")

    headers, rows, cell_warnings = _presentation_table(
        group=group,
        scenarios=scenarios,
        definitions=definitions,
        engine_version=engine_version,
        hide_price_pressure=hide_price_pressure,
    )
    warnings.extend(cell_warnings)
    dimension_status = "ready" if definitions else _nonready_status(operation)
    table_status = "ready" if rows else _nonready_status(operation)
    if dimension_status == "ready" and table_status == "ready":
        scenario_design_status = "ready"
    elif dimension_status == "ready" or table_status == "ready":
        scenario_design_status = "partial"
    elif operation is None or operation.status in {"succeeded", "failed", "interrupted"}:
        scenario_design_status = "unavailable"
    else:
        scenario_design_status = "pending"

    event_markdown, event_status, event_evidence = _event_analysis_markdown(
        engine_version=engine_version,
        group=group,
        events=source_events,
        diagnostics=diagnostics,
        operation=operation,
    )
    role_section: PresentationMarkdownSection | None = None
    if not hide_price_pressure:
        role_markdown, role_status, role_evidence, role_warnings = _role_rationale_markdown(
            engine_version=engine_version,
            headers=headers,
            rows=rows,
            dimension_definitions=[definition.model_dump(by_alias=True) for definition in definitions],
            diagnostics=diagnostics,
            operation=operation,
            lever_labels=lever_labels or {},
        )
        warnings.extend(role_warnings)
        role_section = PresentationMarkdownSection(
            status=role_status,
            evidence_level=role_evidence,
            markdown=role_markdown,
        )
    operation_out = (
        PresentationOperation(
            operation_id=operation.operation_id,
            status=operation.status,
            current_phase=operation.current_phase,
            latest_sequence=operation.latest_sequence,
            snapshot_revision=operation.snapshot_revision,
        )
        if operation is not None
        else None
    )
    return ScenarioGroupPresentationOut(
        renderer_version=PRESENTATION_RENDERER_VERSION,
        scenario_group_id=int(group["scenario_group_id"]),
        engine_version=engine_version,
        legacy=legacy,
        warnings=list(dict.fromkeys(warnings)),
        operation=operation_out,
        sections=PresentationSections(
            event_analysis=PresentationMarkdownSection(
                status=event_status,
                evidence_level=event_evidence,
                markdown=event_markdown,
            ),
            scenario_design=PresentationScenarioDesign(
                status=scenario_design_status,
                evidence_level="limited" if legacy else ("full" if definitions else "none"),
                dimension_definitions=PresentationDimensionDefinitions(
                    status=dimension_status,
                    items=definitions,
                ),
                scenario_table=PresentationScenarioTable(
                    status=table_status,
                    headers=headers,
                    rows=rows,
                ),
            ),
            role_selection_rationale=role_section,
        ),
    )


def _presentation_source(snapshot: dict[str, Any], camel_key: str, snake_key: str) -> Any:
    direct = snapshot.get(camel_key, snapshot.get(snake_key))
    if direct:
        return direct
    sections = snapshot.get("sections") or {}
    for section_key in ("eventAnalysis", "event_analysis", "analysis", "interaction", "scenarioDesign"):
        section = sections.get(section_key) or {}
        value = section.get(camel_key, section.get(snake_key))
        if value:
            return value
    return direct or {}


def _presentation_events(
    events: list[EventPayload],
    snapshot: dict[str, Any],
    *,
    prefer_snapshot: bool,
) -> list[dict[str, Any]]:
    raw_events = _presentation_source(snapshot, "events", "events")
    snapshot_events = [item for item in raw_events if isinstance(item, dict)] if isinstance(raw_events, list) else []
    if prefer_snapshot and snapshot_events:
        return snapshot_events
    if events:
        return [event.model_dump(mode="json", by_alias=True) for event in events]
    return snapshot_events


def _field(value: dict[str, Any], snake_key: str, camel_key: str | None = None, default: Any = None) -> Any:
    if snake_key in value:
        return value[snake_key]
    return value.get(camel_key or _camel_key(snake_key), default)


def _camel_key(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part[:1].upper() + part[1:] for part in tail)


def build_presentation_dimension_definitions(
    raw_definitions: Any,
    *,
    engine_version: str,
) -> list[PresentationDimensionDefinition]:
    if not isinstance(raw_definitions, list):
        return []
    normalized: list[PresentationDimensionDefinition] = []
    for raw_dimension in raw_definitions:
        if not isinstance(raw_dimension, dict):
            continue
        dimension_id = str(_field(raw_dimension, "dimension_id") or "").strip()
        if not dimension_id:
            continue
        values: list[PresentationDimensionValue] = []
        for raw_value in _field(raw_dimension, "values", default=[]) or []:
            if not isinstance(raw_value, dict):
                continue
            value_id = str(_field(raw_value, "value_id") or _field(raw_value, "label") or "").strip()
            label = str(_field(raw_value, "label") or value_id).strip()
            if not value_id or not label:
                continue
            description = _optional_text(_field(raw_value, "description"))
            if engine_version == "v4":
                rationale = str(_field(raw_value, "assumption_rationale") or "")
                lever_states = _field(raw_value, "lever_states", default=[]) or []
                if description is None:
                    description = _v4_value_description(lever_states)
            elif engine_version == "v3":
                rationale = str(_field(raw_value, "derivation_rationale") or description or "")
                lever_states = []
            else:
                rationale = str(_field(raw_value, "rationale") or "")
                lever_states = []
            values.append(
                PresentationDimensionValue(
                    value_id=value_id,
                    label=label,
                    description=description,
                    rationale=rationale,
                    pressure_contribution=_optional_text(_field(raw_value, "pressure_contribution")),
                    lever_states=[item for item in lever_states if isinstance(item, dict)],
                )
            )
        normalized.append(
            PresentationDimensionDefinition(
                dimension_id=dimension_id,
                label=str(_field(raw_dimension, "label") or dimension_id),
                description=_optional_text(_field(raw_dimension, "description")),
                rationale=_optional_text(_field(raw_dimension, "rationale")),
                source_event_ids=[
                    int(item)
                    for item in (_field(raw_dimension, "source_event_ids", default=[]) or [])
                    if str(item).isdigit()
                ],
                model_support_status=_optional_text(_field(raw_dimension, "model_support_status")),
                values=values,
            )
        )
    return normalized


def _v4_value_description(raw_states: Any) -> str | None:
    if not isinstance(raw_states, list):
        return None
    sentences: list[str] = []
    for raw_state in raw_states:
        if not isinstance(raw_state, dict):
            continue
        level = _optional_text(_field(raw_state, "level"))
        scope = _optional_text(_field(raw_state, "scope"))
        time_window = _optional_text(_field(raw_state, "time_window"))
        raw_direction = _field(raw_state, "direction")
        if not level or not scope or not time_window or raw_direction is None:
            continue
        try:
            direction = (
                raw_direction
                if isinstance(raw_direction, StateDirection)
                else StateDirection(str(raw_direction).strip())
            )
        except ValueError:
            continue
        sentences.append(
            f"{time_window} 기준 {scope}에서는 {level} 상태가 전개된다(변화 방향: {direction.label_ko}).",
        )
    return " ".join(sentences) or None


def _current_legacy_template_labels(current_template_dimensions: list[dict[str, Any]]) -> dict[str, str]:
    return {
        str(_field(item, "dim_key")): str(_field(item, "label") or _field(item, "dim_key"))
        for item in current_template_dimensions
        if isinstance(item, dict) and _field(item, "dim_key") and _field(item, "label")
    }


def _legacy_dimension_definitions(
    *,
    group: dict[str, Any],
    scenarios: list[dict[str, Any]],
    trusted_template_dimensions: list[dict[str, Any]],
    current_template_dimensions: list[dict[str, Any]],
) -> list[PresentationDimensionDefinition]:
    selected = [str(item) for item in group.get("dimension_selected") or []]
    observed_by_key: dict[str, list[str]] = defaultdict(list)
    for scenario in scenarios:
        for key, value in (scenario.get("dimension_values") or {}).items():
            text = str(value)
            if text not in observed_by_key[str(key)]:
                observed_by_key[str(key)].append(text)
    if not selected:
        selected = list(observed_by_key)
    template_by_key = {
        str(_field(item, "dim_key")): item
        for item in trusted_template_dimensions
        if isinstance(item, dict) and _field(item, "dim_key")
    }
    current_labels_by_key = _current_legacy_template_labels(current_template_dimensions)
    definitions: list[PresentationDimensionDefinition] = []
    for key in selected:
        template = template_by_key.get(key)
        if template is not None:
            raw_values = _field(template, "value_enums", default=[]) or []
            values = []
            for raw_value in raw_values:
                if isinstance(raw_value, dict):
                    value_id = str(raw_value.get("id") or raw_value.get("label") or "")
                    label = str(raw_value.get("label") or value_id)
                else:
                    value_id = label = str(raw_value)
                if value_id:
                    values.append(PresentationDimensionValue(value_id=value_id, label=label))
            definitions.append(
                PresentationDimensionDefinition(
                    dimension_id=key,
                    label=str(_field(template, "label") or key),
                    description=_optional_text(_field(template, "description")),
                    source="legacy_template_checksum_match",
                    values=values,
                )
            )
            continue
        definitions.append(
            PresentationDimensionDefinition(
                dimension_id=key,
                label=current_labels_by_key.get(key, key),
                source=("legacy_template_current_label" if key in current_labels_by_key else "legacy_observed"),
                values=[
                    PresentationDimensionValue(value_id=value, label=value) for value in observed_by_key.get(key, [])
                ],
            )
        )
    return definitions


def _presentation_table(
    *,
    group: dict[str, Any],
    scenarios: list[dict[str, Any]],
    definitions: list[PresentationDimensionDefinition],
    engine_version: str,
    hide_price_pressure: bool,
) -> tuple[list[PresentationScenarioHeader], list[PresentationScenarioRow], list[str]]:
    headers = [
        PresentationScenarioHeader(key=definition.dimension_id, label=definition.label, display_order=index)
        for index, definition in enumerate(definitions, start=1)
    ]
    definition_by_id = {definition.dimension_id: definition for definition in definitions}
    warnings: list[str] = []
    rows: list[PresentationScenarioRow] = []
    for scenario in scenarios:
        raw_cells = scenario.get("dimension_values") or scenario.get("cells") or {}
        cells: dict[str, Any] = {}
        evidence: dict[str, PresentationCellEvidence] = {}
        for header in headers:
            raw_cell = raw_cells.get(header.key)
            raw_text = "" if raw_cell is None else str(raw_cell)
            value = _match_dimension_value(definition_by_id[header.key], raw_text)
            cells[header.key] = value.value_id if value is not None else raw_cell
            evidence[header.key] = PresentationCellEvidence(
                value_id=value.value_id if value is not None else raw_text,
                value_label=value.label if value is not None else raw_text,
                rationale=value.rationale if value is not None else "",
                pressure_contribution=value.pressure_contribution if value is not None else None,
                evidence_level=("full" if value is not None and engine_version != "v1" else "none"),
            )
            if raw_cell is not None and value is None:
                warnings.append(f"Scenario cell 근거를 찾지 못했습니다: {header.key}={raw_text}")
        probability = scenario.get("probability_score")
        if isinstance(probability, Decimal):
            probability = float(probability)
        rows.append(
            PresentationScenarioRow(
                scenario_id=_optional_int(scenario.get("scenario_id", scenario.get("scenarioId"))),
                display_order=int(scenario.get("display_order", scenario.get("displayOrder")) or 0),
                title=str(scenario.get("title") or ""),
                narrative=_optional_text(scenario.get("narrative")),
                scenario_role=(
                    None
                    if hide_price_pressure
                    else _optional_text(scenario.get("scenario_role", scenario.get("scenarioRole")))
                ),
                baseline_yn=_optional_text(scenario.get("baseline_yn", scenario.get("baselineYn"))),
                pressure_target=(
                    None if hide_price_pressure else ("JKM" if engine_version in {"v2", "v3", "v4"} else None)
                ),
                pressure_band=(
                    None
                    if hide_price_pressure
                    else _optional_text(
                        scenario.get(
                            "global_pressure_band",
                            scenario.get("pressure_band", scenario.get("pressureBand")),
                        )
                    )
                ),
                probability_score=float(probability) if probability is not None else None,
                pressure_rationale=(
                    None
                    if hide_price_pressure
                    else _optional_text(
                        scenario.get(
                            "global_pressure_rationale",
                            scenario.get("pressure_rationale", scenario.get("pressureRationale")),
                        )
                    )
                ),
                cells=cells,
                cell_evidence=evidence,
            )
        )
    return headers, rows, warnings


def _match_dimension_value(
    definition: PresentationDimensionDefinition,
    raw_cell: str,
) -> PresentationDimensionValue | None:
    for value in definition.values:
        if value.value_id == raw_cell:
            return value
    for value in definition.values:
        if value.label == raw_cell:
            return value
    return None


def _event_analysis_markdown(
    *,
    engine_version: str,
    group: dict[str, Any],
    events: list[dict[str, Any]],
    diagnostics: dict[str, Any],
    operation: ScenarioGroupOperationPayload | None,
) -> tuple[str, str, str]:
    if engine_version == "v1":
        return _legacy_event_markdown(group, events), "ready", "limited"
    if not diagnostics:
        return "", _nonready_status(operation), "none"
    if engine_version == "v4":
        markdown = _v4_event_markdown(events, diagnostics)
        status = "ready" if _v4_interaction_is_ready(operation, diagnostics) else "partial"
    else:
        markdown = _v3_event_markdown(events, diagnostics)
        status = "ready"
    return markdown, status, "full"


def _legacy_event_markdown(group: dict[str, Any], events: list[dict[str, Any]]) -> str:
    lines = [
        "## Event 및 Scenario Group 설명",
        "",
        "> 기존 v1 데이터에는 생성 당시의 상세 Event 영향 경로가 저장되지 않았습니다.",
        "",
        "### Event",
        "",
        "- 데이터 기준: 현재 Event 레코드 기준",
    ]
    if events:
        event = events[0]
        lines.extend(
            [
                f"- 제목: {_escape(_field(event, 'event_title_ko') or '')}",
                f"- 요약: {_escape(_field(event, 'one_line_summary') or '')}",
                f"- 발생 시각: {_escape(_field(event, 'occurred_at') or '')}",
            ]
        )
    lines.extend(
        [
            "",
            "### 저장된 Scenario Group 설명",
            "",
            f"- 제목: {_escape(group.get('title') or '')}",
            f"- 요약: {_escape(group.get('summary') or '')}",
            f"- 설명: {_escape(group.get('description') or '')}",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _v3_event_markdown(events: list[dict[str, Any]], diagnostics: dict[str, Any]) -> str:
    shocks = _field(diagnostics, "event_shocks", default=[]) or []
    shock_by_event = {
        int(_field(item, "event_id")): item
        for item in shocks
        if isinstance(item, dict) and str(_field(item, "event_id") or "").isdigit()
    }
    selections = _field(diagnostics, "template_dimension_selections", default=[]) or []
    lines = ["## Event 분석"]
    for event in events:
        event_id = int(_field(event, "mi_event_id"))
        lines.extend(["", f"### {_escape(_field(event, 'event_title_ko') or f'Event {event_id}')}"])
        shock = shock_by_event.get(event_id)
        lines.extend(
            ["", "#### 예상 충격", "", _escape(_field(shock or {}, "shock_summary") or "저장된 충격 요약 없음")]
        )
        observed = [
            item
            for item in selections
            if isinstance(item, dict) and _optional_int(_field(item, "event_id")) == event_id
        ]
        lines.extend(["", "#### 관찰 근거"])
        if observed:
            for item in sorted(observed, key=_v3_selection_sort_key):
                lines.append(f"- {_escape(_field(item, 'observed_basis') or '')}")
        else:
            lines.append("- 저장된 관찰 근거 없음")
    lines.extend(["", "## Event 간 상호작용"])
    interactions = _field(diagnostics, "event_interactions", default=[]) or []
    if interactions:
        for item in sorted((item for item in interactions if isinstance(item, dict)), key=_interaction_sort_key):
            lines.append(f"- {_escape(_field(item, 'rationale') or _field(item, 'mechanism') or '')}")
    else:
        lines.append("- 저장된 Event 상호작용 없음")
    return "\n".join(lines).rstrip() + "\n"


def _exclusion_label(exclusion: dict[str, Any]) -> str:
    if _field(exclusion, "reason_type") == "catalog_condition_unmet":
        return "분석 제외(Catalog 조건 미충족)"
    return "분석 제외"


def _v4_event_markdown(events: list[dict[str, Any]], diagnostics: dict[str, Any]) -> str:
    facts = _field(diagnostics, "event_facts", default=[]) or []
    exclusions = _field(diagnostics, "event_exclusions", default=[]) or []
    paths = _field(diagnostics, "impact_paths", default=[]) or []
    uncertainties = _field(diagnostics, "path_uncertainties", default=[]) or []
    lines = ["## Event 분석"]
    event_labels: dict[int, str] = {}
    for display_order, event in enumerate(events, start=1):
        event_id = int(_field(event, "mi_event_id"))
        title = _field(event, "event_title_ko") or f"Event {event_id}"
        event_labels[event_id] = f"Event {display_order} · {_escape(title)}"
        event_facts = [
            item for item in facts if isinstance(item, dict) and _optional_int(_field(item, "event_id")) == event_id
        ]
        event_exclusions = [
            item
            for item in exclusions
            if isinstance(item, dict) and _optional_int(_field(item, "event_id")) == event_id
        ]
        event_paths = [
            item for item in paths if isinstance(item, dict) and _optional_int(_field(item, "event_id")) == event_id
        ]
        path_ids = {str(_field(item, "impact_path_id")) for item in event_paths}
        event_uncertainties = [
            item
            for item in uncertainties
            if isinstance(item, dict)
            and path_ids.intersection(str(path_id) for path_id in (_field(item, "impact_path_ids", default=[]) or []))
        ]
        if display_order > 1:
            lines.extend(["", "---"])
        lines.extend(["", f"### Event {display_order} · {_escape(title)}", "", "### 확인된 사실"])
        if event_facts:
            for item in sorted(event_facts, key=lambda value: str(_field(value, "fact_id") or "")):
                lines.append(f"- {_escape(_field(item, 'observed_basis') or '')}")
            for item in event_exclusions:
                lines.append(f"- {_exclusion_label(item)}: {_escape(_field(item, 'reason') or '')}")
        else:
            for item in event_exclusions:
                lines.append(f"- {_exclusion_label(item)}: {_escape(_field(item, 'reason') or '')}")
            if not event_exclusions:
                lines.append("- 저장된 사실 없음")
        lines.extend(["", "### LNG·JKM 영향 경로"])
        if event_paths:
            for item in sorted(event_paths, key=lambda value: str(_field(value, "impact_path_id") or "")):
                lines.append(f"- {_escape(_field(item, 'mechanism') or '')}")
        else:
            lines.append("- 저장된 영향 경로 없음")
        lines.extend(["", "### 주요 불확실성"])
        if event_uncertainties:
            for item in sorted(event_uncertainties, key=lambda value: str(_field(value, "uncertainty_id") or "")):
                lines.append(f"- {_escape(_field(item, 'subject') or _field(item, 'reason') or '')}")
        else:
            lines.append("- 저장된 주요 불확실성 없음")
    lines.extend(["", "---", "", "## Event 간 상호작용"])
    interactions = _field(diagnostics, "event_interactions", default=[]) or []
    interaction_uncertainties = _field(diagnostics, "interaction_uncertainties", default=[]) or []
    rendered_uncertainty_ids: set[str] = set()
    if interactions:
        for display_order, item in enumerate(
            sorted((item for item in interactions if isinstance(item, dict)), key=_interaction_sort_key),
            start=1,
        ):
            event_ids = [
                event_id
                for raw_event_id in (_field(item, "event_ids", default=[]) or [])
                if (event_id := _optional_int(raw_event_id)) is not None
            ]
            mechanism = _escape(_field(item, "mechanism") or _field(item, "rationale") or "")
            lines.extend(
                [
                    "",
                    f"### Interaction {display_order}",
                    "",
                ]
            )
            if event_ids:
                lines.append("#### 관련 Event")
                for event_id in event_ids:
                    lines.append(f"- **{event_labels.get(event_id, f'Event ID {event_id}')}**")
                lines.append("")
            lines.extend(["#### 상호작용 내용", f"- {mechanism}"])
            interaction_id = str(_field(item, "interaction_id") or "")
            related_uncertainties = [
                uncertainty
                for uncertainty in interaction_uncertainties
                if isinstance(uncertainty, dict)
                and str(_field(uncertainty, "interaction_id") or "") == interaction_id
            ]
            if related_uncertainties:
                lines.extend(["", "#### 상호작용 불확실성"])
                for uncertainty in sorted(
                    related_uncertainties,
                    key=lambda value: str(_field(value, "uncertainty_id") or ""),
                ):
                    lines.append(f"- {_escape(_field(uncertainty, 'subject') or _field(uncertainty, 'reason') or '')}")
                    rendered_uncertainty_ids.add(str(_field(uncertainty, "uncertainty_id") or ""))
    else:
        lines.append("- 저장된 Event 상호작용 없음")
    unlinked_uncertainties = [
        item
        for item in interaction_uncertainties
        if isinstance(item, dict) and str(_field(item, "uncertainty_id") or "") not in rendered_uncertainty_ids
    ]
    if unlinked_uncertainties:
        lines.extend(["", "### 기타 상호작용 불확실성"])
        for item in sorted(
            unlinked_uncertainties,
            key=lambda value: str(_field(value, "uncertainty_id") or ""),
        ):
            lines.append(f"- {_escape(_field(item, 'subject') or _field(item, 'reason') or '')}")
    return "\n".join(lines).rstrip() + "\n"


def _role_rationale_markdown(
    *,
    engine_version: str,
    headers: Sequence[PresentationScenarioHeader],
    rows: list[PresentationScenarioRow],
    dimension_definitions: Sequence[Mapping[str, Any]],
    diagnostics: dict[str, Any],
    operation: ScenarioGroupOperationPayload | None,
    lever_labels: dict[str, str],
) -> tuple[str, str, str, list[str]]:
    role_rows = {row.scenario_role: row for row in rows if row.scenario_role in {"ceiling", "mixed", "floor"}}
    if not role_rows:
        return "", ("unavailable" if engine_version == "v1" else _nonready_status(operation)), "none", []
    warnings: list[str] = []
    lines = ["## 대표 Scenario 선택 근거"]
    role_labels = {"ceiling": "Ceiling", "mixed": "Mixed", "floor": "Floor"}
    criteria = {
        "ceiling": "생성된 Scenario 중 JKM 압력대가 가장 높은 Scenario",
        "mixed": "상승·하락 기여를 동시에 가진 내부 Scenario 중 Balanced에 가장 가까운 Scenario",
        "floor": "생성된 Scenario 중 JKM 압력대가 가장 낮은 Scenario",
    }
    lever_code_pattern = _lever_code_pattern(lever_labels)
    display_order_by_dimension_id = {header.key: header.display_order for header in headers}
    for role in ("ceiling", "mixed", "floor"):
        row = role_rows.get(role)
        if row is None:
            if role == "mixed" and engine_version == "v4":
                lines.extend(["", "### Mixed", "", "선정 가능한 Mixed Scenario 없음"])
            continue
        lines.extend(
            [
                "",
                f"### {role_labels[role]} — {_escape(row.title)}",
                "",
                f"- 선택 기준: {criteria[role]}",
                f"- Pressure Band: {_display_enum(row.pressure_band)}",
                f"- 발생 가능성: {_format_probability(row.probability_score)}",
                f"- 종합 근거: {_escape_lever_labels(row.pressure_rationale, lever_labels, lever_code_pattern)}",
            ]
        )
        if row.baseline_yn == "Y":
            lines.append("- Baseline: 생성된 Scenario 중 발생 가능성이 가장 높음")
        if not row.pressure_rationale:
            warnings.append(f"{role_labels[role]} Scenario에 저장된 종합 근거가 없습니다.")
        breakdown = _presentation_pressure_breakdown(
            engine_version=engine_version,
            row=row,
            dimension_definitions=dimension_definitions,
            diagnostics=diagnostics,
        )
        raw_breakdown = _field(breakdown or {}, "pressure_breakdown", default={}) or {}
        if isinstance(raw_breakdown, dict) and raw_breakdown:
            lines.extend(["", "#### 분기 기준 설명"])
            for key, label in (
                ("common_impact", "공통 영향"),
                ("value_delta", "분기 상세 설명"),
                ("interaction_effect", "이벤트 간 상호작용 효과"),
            ):
                value = _field(raw_breakdown, key)
                if value:
                    lines.append(f"- {label}: {_escape_lever_labels(value, lever_labels, lever_code_pattern)}")
        lines.extend(["", "#### 분기별 선택 값 설명"])
        if row.cell_evidence:
            for dimension_id, cell in row.cell_evidence.items():
                lines.extend(
                    [
                        f"- {display_order_by_dimension_id.get(dimension_id, '')} — {_escape(cell.value_label)}",
                        f"  - 근거: {_escape_lever_labels(cell.rationale, lever_labels, lever_code_pattern)}",
                        f"  - 압력 기여: {_display_enum(cell.pressure_contribution)}",
                    ]
                )
        else:
            lines.append("- 저장된 Dimension 근거 없음")
    evidence = "limited" if engine_version == "v1" else "full"
    return "\n".join(lines).rstrip() + "\n", "ready", evidence, warnings


def _presentation_pressure_breakdown(
    *,
    engine_version: str,
    row: PresentationScenarioRow,
    dimension_definitions: Sequence[Mapping[str, Any]],
    diagnostics: dict[str, Any],
) -> Mapping[str, Any] | None:
    if engine_version == "v4":
        return find_scenario_pressure_breakdown(
            row.cells,
            dimension_definitions=dimension_definitions,
            generation_diagnostics=diagnostics,
        )
    breakdowns = _field(diagnostics, "scenario_pressure_breakdowns", default=[]) or []
    return next(
        (item for item in breakdowns if isinstance(item, dict) and str(_field(item, "title") or "") == row.title),
        None,
    )


def _v4_interaction_is_ready(
    operation: ScenarioGroupOperationPayload | None,
    diagnostics: dict[str, Any],
) -> bool:
    if operation is None or operation.status in {"succeeded", "failed", "interrupted"}:
        return True
    sections = operation.presentation_snapshot.get("sections") or {}
    interaction = sections.get("interaction") or sections.get("eventInteraction") or {}
    event_analysis = sections.get("eventAnalysis") or {}
    return interaction.get("status") == "ready" or event_analysis.get("status") == "ready"


def _nonready_status(operation: ScenarioGroupOperationPayload | None) -> str:
    if operation is not None and operation.status in {"queued", "running"}:
        return "pending"
    return "unavailable"


def _v3_selection_sort_key(value: dict[str, Any]) -> tuple[int, str]:
    return int(_field(value, "scenario_dimension_template_id") or 0), str(_field(value, "dim_key") or "")


def _interaction_sort_key(value: dict[str, Any]) -> tuple[str, str]:
    return str(_field(value, "interaction_id") or ""), ",".join(
        str(item) for item in (_field(value, "event_ids", default=[]) or [])
    )


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _optional_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _escape(value: Any) -> str:
    return html.escape(str(value), quote=False)


def _lever_code_pattern(lever_labels: dict[str, str]) -> re.Pattern[str] | None:
    codes = sorted(
        (code for code, label in lever_labels.items() if code and label),
        key=lambda code: (-len(code), code),
    )
    if not codes:
        return None
    alternatives = "|".join(re.escape(code) for code in codes)
    return re.compile(rf"(?<![A-Za-z0-9_])(?:{alternatives})(?![A-Za-z0-9_])")


def _escape_lever_labels(
    value: Any,
    lever_labels: dict[str, str],
    pattern: re.Pattern[str] | None,
) -> str:
    text = str(value or "")
    if pattern is not None:
        text = pattern.sub(lambda match: lever_labels.get(match.group(0), match.group(0)), text)
    return _escape(text)


def _display_enum(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(part.capitalize() for part in value.split("_"))


def _format_probability(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:g}%"
