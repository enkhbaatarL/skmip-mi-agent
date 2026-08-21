from __future__ import annotations

# ruff: noqa: COM812, CPY001
from copy import deepcopy
from dataclasses import dataclass, field
from decimal import Decimal
import hashlib
import json
import re
from typing import Any
import unicodedata

from apps.agents.scenario_group_agent.flows.add_dimension.nodes import filter_available_candidates
from apps.agents.scenario_group_agent.utils.dimension_values import (
    build_dimension_value_catalog,
    canonicalize_dimension_value,
)
from apps.persistence.scenario_group_operation.schema import ValidationCheckPayload


V4_GENERATION_STRATEGY = "multi_event_model_lever_dimensions"


def _get(payload: dict[str, Any], snake_key: str, camel_key: str) -> object:
    return payload.get(snake_key, payload.get(camel_key))


def _json_default(value: object) -> str:
    if isinstance(value, Decimal):
        return format(value, "f")
    message = f"Unsupported canonical JSON value: {type(value).__name__}"
    raise TypeError(message)


def _fingerprint(payload: object) -> str:
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        default=_json_default,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def normalize_title(value: object) -> str:
    normalized = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return "".join(
        character
        for character in normalized
        if not character.isspace() and not unicodedata.category(character).startswith("P")
    )


def scenario_fingerprint(scenarios: list[dict[str, Any]]) -> str:
    rows = [
        {
            "scenarioId": int(_get(scenario, "scenario_id", "scenarioId")),
            "displayOrder": int(_get(scenario, "display_order", "displayOrder") or 0),
            "title": str(scenario.get("title") or ""),
            "narrative": _get(scenario, "narrative", "narrative"),
            "dimensionValues": _get(scenario, "dimension_values", "dimensionValues") or {},
            "probabilityScore": _get(scenario, "probability_score", "probabilityScore"),
            "probabilityDelta": _get(scenario, "probability_delta", "probabilityDelta"),
            "baselineYn": _get(scenario, "baseline_yn", "baselineYn"),
            "pressureBand": _get(scenario, "global_pressure_band", "globalPressureBand"),
            "scenarioRole": _get(scenario, "scenario_role", "scenarioRole"),
            "pressureRationale": _get(
                scenario,
                "global_pressure_rationale",
                "globalPressureRationale",
            ),
            "relatedMarkets": _get(scenario, "related_markets", "relatedMarkets") or [],
        }
        for scenario in scenarios
    ]
    rows.sort(key=lambda item: (item["scenarioId"], item["displayOrder"]))
    return _fingerprint(rows)


def dimension_definition_fingerprint(definitions: list[dict[str, Any]]) -> str:
    return _fingerprint(definitions)


@dataclass(frozen=True)
class CanonicalScenarioRow:
    scenario_id: int | None
    client_row_key: str
    row_index: int
    display_order: int
    title: str
    dimension_values: dict[str, str]
    change_type: str | None = None
    autofilled_dimension_values: dict[str, str] = field(default_factory=dict)

    def review_scenario_id(self) -> int:
        return self.scenario_id if self.scenario_id is not None else -self.row_index

    def as_review_row(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "row_index": self.row_index,
            "display_order": self.display_order,
            "title": self.title,
            "cells": dict(self.dimension_values),
        }


@dataclass
class V4ValidationAnalysis:
    canonical_headers: list[str]
    canonical_rows: list[CanonicalScenarioRow]
    changed_rows: list[CanonicalScenarioRow]
    deleted_scenario_ids: list[int]
    checks: list[ValidationCheckPayload] = field(default_factory=list)
    base_scenario_fingerprint: str = ""
    dimension_definition_fingerprint: str = ""
    base_dimension_definition_fingerprint: str = ""
    requested_dimension_definitions: list[dict[str, Any]] = field(default_factory=list)
    added_dimension_ids: list[str] = field(default_factory=list)
    removed_dimension_ids: list[str] = field(default_factory=list)
    promoted_dimension_ids: list[str] = field(default_factory=list)
    candidate_source_fingerprint: str | None = None

    @property
    def blocking(self) -> bool:
        return any(check.blocking and check.status == "FAIL" for check in self.checks)

    @property
    def unchanged(self) -> bool:
        return not self.blocking and not self.changed_rows and not self.deleted_scenario_ids


@dataclass(frozen=True)
class V4AdditionalDimensionAutofillRequest:
    row_index: int
    client_row_key: str
    scenario_id: int | None
    dimension_id: str
    target_direction: str
    existing_pressure_score: int
    allowed_values: list[dict[str, Any]]
    title: str
    narrative: str
    existing_cells: dict[str, object]


@dataclass
class V4AdditionalDimensionAutofillPlan:
    request_table: dict[str, Any]
    requests: list[V4AdditionalDimensionAutofillRequest] = field(default_factory=list)
    assignments: dict[tuple[str, str], str] = field(default_factory=dict)
    restorations: dict[tuple[str, str], str] = field(default_factory=dict)
    checks: list[ValidationCheckPayload] = field(default_factory=list)


def _check(
    check_id: str,
    *,
    status: str,
    blocking: bool,
    detail: str,
    offenders: list[str] | None = None,
    advice: list[str] | None = None,
) -> ValidationCheckPayload:
    return ValidationCheckPayload(
        check_id=check_id,
        status=status,
        blocking=blocking,
        detail=detail,
        offenders=offenders or [],
        advice=advice or [],
    )


def _definition_indexes(
    definitions: list[dict[str, Any]],
) -> tuple[list[str], dict[str, dict[str, str]], dict[str, dict[str, str | None]]]:
    ordered = sorted(
        definitions,
        key=lambda item: (
            int(_get(item, "display_order", "displayOrder") or 999999),
            str(_get(item, "dimension_id", "dimensionId") or ""),
        ),
    )
    dimension_ids: list[str] = []
    value_ids_by_dimension: dict[str, dict[str, str]] = {}
    labels_by_dimension: dict[str, dict[str, str | None]] = {}
    for definition in ordered:
        dimension_id = str(_get(definition, "dimension_id", "dimensionId") or "").strip()
        if not dimension_id:
            continue
        dimension_ids.append(dimension_id)
        id_map: dict[str, str] = {}
        label_candidates: dict[str, list[str]] = {}
        for raw_value in definition.get("values") or []:
            if not isinstance(raw_value, dict):
                continue
            value_id = str(_get(raw_value, "value_id", "valueId") or "").strip()
            label = str(raw_value.get("label") or "").strip()
            if not value_id:
                continue
            id_map[value_id] = value_id
            if label:
                label_candidates.setdefault(label, []).append(value_id)
        value_ids_by_dimension[dimension_id] = id_map
        labels_by_dimension[dimension_id] = {
            label: value_ids[0] if len(value_ids) == 1 else None for label, value_ids in label_candidates.items()
        }
    return dimension_ids, value_ids_by_dimension, labels_by_dimension


def _canonical_value(
    dimension_id: str,
    raw_value: object,
    value_ids_by_dimension: dict[str, dict[str, str]],
    labels_by_dimension: dict[str, dict[str, str | None]],
) -> str | None:
    if raw_value is None or (isinstance(raw_value, str) and not raw_value.strip()):
        return None
    text = str(raw_value)
    direct = value_ids_by_dimension.get(dimension_id, {}).get(text)
    if direct is not None:
        return direct
    return labels_by_dimension.get(dimension_id, {}).get(text)


def _canonical_persisted_cells(
    scenario: dict[str, Any],
    header_ids: list[str],
    value_ids_by_dimension: dict[str, dict[str, str]],
    labels_by_dimension: dict[str, dict[str, str | None]],
) -> dict[str, str]:
    raw_cells = _get(scenario, "dimension_values", "dimensionValues") or {}
    if not isinstance(raw_cells, dict):
        return {}
    result: dict[str, str] = {}
    for dimension_id in header_ids:
        canonical = _canonical_value(
            dimension_id,
            raw_cells.get(dimension_id),
            value_ids_by_dimension,
            labels_by_dimension,
        )
        if canonical is not None:
            result[dimension_id] = canonical
    return result


def _available_definition_sets(
    *,
    dimension_definitions: list[dict[str, Any]],
    generation_diagnostics: dict[str, Any],
    stored_header_order: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    formal_definitions = [item for item in dimension_definitions if isinstance(item, dict)]
    generation = (
        _get(
            generation_diagnostics,
            "additional_dimension_generation",
            "additionalDimensionGeneration",
        )
        or {}
    )
    raw_candidates = (
        _get(
            generation_diagnostics,
            "additional_dimension_candidates",
            "additionalDimensionCandidates",
        )
        or []
    )
    candidates = (
        filter_available_candidates(
            [item for item in raw_candidates if isinstance(item, dict)],
            dimension_selected=stored_header_order,
            active_definitions=formal_definitions,
        )
        if isinstance(generation, dict) and generation.get("status") == "ready"
        else []
    )
    return formal_definitions, candidates


def _definition_id(definition: dict[str, Any]) -> str:
    return str(_get(definition, "dimension_id", "dimensionId") or "").strip()


def _is_additional_dimension_id(dimension_id: str) -> bool:
    return dimension_id.startswith("ad_")


def _value_id(value: dict[str, Any]) -> str:
    return str(_get(value, "value_id", "valueId") or "").strip()


def _definition_label(definition: dict[str, Any], dimension_id: str) -> str:
    return str(definition.get("label") or definition.get("name") or dimension_id).strip()


def _pressure_contribution(value: dict[str, Any]) -> str | None:
    contribution = str(_get(value, "pressure_contribution", "pressureContribution") or "").strip()
    return contribution if contribution in {"bullish", "balanced", "bearish"} else None


def _row_key(raw_row: dict[str, Any], index: int) -> tuple[int | None, str]:
    raw_id = _get(raw_row, "scenario_id", "scenarioId")
    scenario_id = int(raw_id) if raw_id is not None else None
    return scenario_id, f"scenario:{scenario_id}" if scenario_id is not None else f"new:{index}"


def _collapsed_pressure_direction(pressure_band: object) -> str | None:
    value = str(pressure_band or "")
    if value in {"strong_bullish", "bullish"}:
        return "bullish"
    if value in {"strong_bearish", "bearish"}:
        return "bearish"
    if value == "balanced":
        return "balanced"
    return None


def _canonical_contribution_score(
    *,
    cells: dict[str, object],
    definitions: list[dict[str, Any]],
) -> tuple[int, bool]:
    catalog = build_dimension_value_catalog(definitions)
    score_by_contribution = {"bullish": 1, "balanced": 0, "bearish": -1}
    score = 0
    for definition in definitions:
        dimension_id = _definition_id(definition)
        if not dimension_id or dimension_id not in cells:
            continue
        raw_value = cells.get(dimension_id)
        if raw_value is None or (isinstance(raw_value, str) and not raw_value.strip()):
            continue
        try:
            canonical = canonicalize_dimension_value(
                catalog,
                dimension_id,
                raw_value,
                allow_label_compatibility=True,
            )
        except ValueError:
            return score, False
        selected = next(
            (
                value
                for value in definition.get("values") or []
                if isinstance(value, dict) and _value_id(value) == canonical
            ),
            None,
        )
        if selected is None or (contribution := _pressure_contribution(selected)) is None:
            return score, False
        score += score_by_contribution[contribution]
    return score, True


def _allowed_autofill_values(
    *,
    definition: dict[str, Any],
    target_direction: str,
    existing_pressure_score: int,
) -> list[dict[str, Any]]:
    values = [
        value
        for value in definition.get("values") or []
        if isinstance(value, dict) and _value_id(value) and _pressure_contribution(value) is not None
    ]
    same_direction = [value for value in values if _pressure_contribution(value) == target_direction]
    if same_direction:
        return same_direction
    if target_direction in {"bullish", "bearish"}:
        return [value for value in values if _pressure_contribution(value) == "balanced"]

    contribution_score = {"bullish": 1, "balanced": 0, "bearish": -1}
    if not values:
        return []
    minimum_distance = min(
        abs(existing_pressure_score + contribution_score[str(_pressure_contribution(value))]) for value in values
    )
    return [
        value
        for value in values
        if abs(existing_pressure_score + contribution_score[str(_pressure_contribution(value))]) == minimum_distance
    ]


def build_v4_additional_dimension_autofill_plan(
    *,
    request_table: dict[str, Any],
    persisted_scenarios: list[dict[str, Any]],
    dimension_definitions: list[dict[str, Any]],
    generation_diagnostics: dict[str, Any],
    stored_header_order: list[str] | None = None,
) -> V4AdditionalDimensionAutofillPlan:
    """Fill deterministic null cells and describe only the ambiguous choices for a constrained LLM call."""
    stored_headers = [str(item) for item in (stored_header_order or [])]
    formal_definitions, candidates = _available_definition_sets(
        dimension_definitions=dimension_definitions,
        generation_diagnostics=generation_diagnostics,
        stored_header_order=stored_headers,
    )
    formal_by_id = {_definition_id(item): item for item in formal_definitions}
    candidate_by_id = {_definition_id(item): item for item in candidates}
    header_ids = [
        str(header.get("key") or "").strip()
        for header in request_table.get("headers") or []
        if isinstance(header, dict)
    ]
    autofill_by_id = {
        **{item: definition for item, definition in formal_by_id.items() if _is_additional_dimension_id(item)},
        **{item: definition for item, definition in candidate_by_id.items() if _is_additional_dimension_id(item)},
    }
    autofill_ids = [item for item in header_ids if item in autofill_by_id]
    plan = V4AdditionalDimensionAutofillPlan(request_table=deepcopy(request_table))
    persisted_by_id = {
        int(_get(scenario, "scenario_id", "scenarioId")): scenario
        for scenario in persisted_scenarios
        if _get(scenario, "scenario_id", "scenarioId") is not None
    }
    rows = plan.request_table.get("rows") or []
    if not autofill_ids:
        return plan

    effective_definitions = [
        *formal_definitions,
        *[candidate_by_id[item] for item in autofill_ids if item not in formal_by_id],
    ]
    effective_catalog = build_dimension_value_catalog(effective_definitions)
    for index, raw_row in enumerate(rows, start=1):
        if not isinstance(raw_row, dict):
            continue
        scenario_id, client_row_key = _row_key(raw_row, index)
        cells = raw_row.get("cells")
        if not isinstance(cells, dict):
            continue
        persisted = persisted_by_id.get(scenario_id) if scenario_id is not None else None
        title = str(raw_row.get("title") or "").strip()
        scenario_label = f"'{title}' 시나리오" if title else f"{index}번째 시나리오"
        existing_score, contribution_valid = _canonical_contribution_score(
            cells=cells,
            definitions=effective_definitions,
        )
        target_direction = (
            _collapsed_pressure_direction(_get(persisted, "global_pressure_band", "globalPressureBand"))
            if persisted is not None
            else "bullish"
            if existing_score > 0
            else "bearish"
            if existing_score < 0
            else "balanced"
        )
        for dimension_id in autofill_ids:
            raw_value = cells.get(dimension_id)
            if raw_value is not None and (not isinstance(raw_value, str) or raw_value.strip()):
                continue
            definition = autofill_by_id[dimension_id]
            dimension_label = _definition_label(definition, dimension_id)
            if not contribution_valid or target_direction is None:
                plan.checks.append(
                    _check(
                        "V4_ADDITIONAL_DIMENSION_AUTOFILL",
                        status="FAIL",
                        blocking=True,
                        detail="기존 분기 값만으로 새 분기 값을 자동 선택할 수 없습니다.",
                        offenders=[f"{scenario_label} · {dimension_label}"],
                    )
                )
                continue
            allowed_values = _allowed_autofill_values(
                definition=definition,
                target_direction=target_direction,
                existing_pressure_score=existing_score,
            )
            if not allowed_values:
                plan.checks.append(
                    _check(
                        "V4_ADDITIONAL_DIMENSION_AUTOFILL",
                        status="FAIL",
                        blocking=True,
                        detail="현재 시나리오 방향을 유지할 수 있는 새 분기 값이 없습니다.",
                        offenders=[f"{scenario_label} · {dimension_label}"],
                    )
                )
                continue
            persisted_cells = _get(persisted, "dimension_values", "dimensionValues") if persisted is not None else None
            try:
                stored_value_id = canonicalize_dimension_value(
                    effective_catalog,
                    dimension_id,
                    persisted_cells.get(dimension_id) if isinstance(persisted_cells, dict) else None,
                    allow_label_compatibility=True,
                )
            except ValueError:
                stored_value_id = None
            allowed_value_ids = {_value_id(value) for value in allowed_values}
            if stored_value_id in allowed_value_ids:
                cells[dimension_id] = stored_value_id
                plan.restorations[(client_row_key, dimension_id)] = stored_value_id
                continue
            if len(allowed_values) == 1:
                selected_value_id = _value_id(allowed_values[0])
                cells[dimension_id] = selected_value_id
                plan.assignments[(client_row_key, dimension_id)] = selected_value_id
                continue
            plan.requests.append(
                V4AdditionalDimensionAutofillRequest(
                    row_index=index - 1,
                    client_row_key=client_row_key,
                    scenario_id=scenario_id,
                    dimension_id=dimension_id,
                    target_direction=target_direction,
                    existing_pressure_score=existing_score,
                    allowed_values=deepcopy(allowed_values),
                    title=title,
                    narrative=str((_get(persisted, "narrative", "narrative") if persisted is not None else "") or ""),
                    existing_cells=deepcopy(cells),
                )
            )
    return plan


def apply_v4_additional_dimension_autofill_selections(
    plan: V4AdditionalDimensionAutofillPlan,
    selections: dict[tuple[str, str], str],
) -> None:
    requests_by_key = {(item.client_row_key, item.dimension_id): item for item in plan.requests}
    if set(selections) != set(requests_by_key):
        missing = sorted(set(requests_by_key) - set(selections))
        extra = sorted(set(selections) - set(requests_by_key))
        message = f"Additional Dimension selection key mismatch: missing={missing}, extra={extra}"
        raise ValueError(message)
    rows = plan.request_table.get("rows") or []
    for key, selected_value_id in selections.items():
        request = requests_by_key[key]
        allowed_ids = {_value_id(value) for value in request.allowed_values}
        if selected_value_id not in allowed_ids:
            message = f"Additional Dimension selection is outside allowed values: {key}={selected_value_id}"
            raise ValueError(message)
        row = rows[request.row_index]
        row["cells"][request.dimension_id] = selected_value_id
        plan.assignments[key] = selected_value_id


def build_autofill_checks(
    assignments: dict[tuple[str, str], str],
) -> list[ValidationCheckPayload]:
    return [
        _check(
            "V4_ADDITIONAL_DIMENSION_AUTOFILL",
            status="INFO",
            blocking=False,
            detail="Additional Dimension의 빈 cell을 pressure 방향과 의미 적합성에 따라 자동 배정했습니다.",
            offenders=[f"row={row_key}, dimension={dimension_id}, value={value_id}"],
        )
        for (row_key, dimension_id), value_id in assignments.items()
    ]


def build_restoration_checks(
    restorations: dict[tuple[str, str], str],
) -> list[ValidationCheckPayload]:
    return [
        _check(
            "V4_EXISTING_DIMENSION_VALUE_RESTORED",
            status="INFO",
            blocking=False,
            detail="화면에서 비어 있던 기존 분기 값을 저장된 값으로 복원했습니다.",
            offenders=[f"row={row_key}, dimension={dimension_id}, value={value_id}"],
        )
        for (row_key, dimension_id), value_id in restorations.items()
    ]


def analyze_v4_validation_request(  # noqa: C901
    *,
    request_table: dict[str, Any],
    persisted_scenarios: list[dict[str, Any]],
    dimension_definitions: list[dict[str, Any]],
    generation_diagnostics: dict[str, Any],
    stored_header_order: list[str] | None = None,
    autofilled_cells: dict[tuple[str, str], str] | None = None,
) -> V4ValidationAnalysis:
    stored_headers = [str(item) for item in (stored_header_order or [])]
    formal_definitions, candidates = _available_definition_sets(
        dimension_definitions=dimension_definitions,
        generation_diagnostics=generation_diagnostics,
        stored_header_order=stored_headers,
    )
    generation = (
        _get(
            generation_diagnostics,
            "additional_dimension_generation",
            "additionalDimensionGeneration",
        )
        or {}
    )
    effective_by_id = {
        str(_get(item, "dimension_id", "dimensionId")): item for item in [*formal_definitions, *candidates]
    }
    base_fingerprint = scenario_fingerprint(persisted_scenarios)
    analysis = V4ValidationAnalysis(
        canonical_headers=[],
        canonical_rows=[],
        changed_rows=[],
        deleted_scenario_ids=[],
        base_scenario_fingerprint=base_fingerprint,
        base_dimension_definition_fingerprint=dimension_definition_fingerprint(formal_definitions),
        candidate_source_fingerprint=(
            str(generation.get("source_fingerprint") or generation.get("sourceFingerprint"))
            if isinstance(generation, dict)
            and (generation.get("source_fingerprint") or generation.get("sourceFingerprint"))
            else None
        ),
    )
    raw_headers = request_table.get("headers") or []
    header_ids = [str(header.get("key") or "").strip() for header in raw_headers if isinstance(header, dict)]
    requested_header_labels = {
        str(header.get("key") or "").strip(): str(header.get("label") or "").strip()
        for header in raw_headers
        if isinstance(header, dict)
    }
    analysis.canonical_headers = header_ids
    requested_definitions = [effective_by_id[item] for item in header_ids if item in effective_by_id]
    analysis.requested_dimension_definitions = requested_definitions
    analysis.dimension_definition_fingerprint = dimension_definition_fingerprint(requested_definitions)
    candidate_ids = {str(_get(item, "dimension_id", "dimensionId")) for item in candidates}
    stored_header_set = set(stored_headers)
    analysis.added_dimension_ids = [
        item for item in header_ids if item in effective_by_id and item not in stored_header_set
    ]
    analysis.removed_dimension_ids = [item for item in stored_headers if item not in set(header_ids)]
    analysis.promoted_dimension_ids = [item for item in header_ids if item in candidate_ids]
    _requested_headers, value_ids_by_dimension, labels_by_dimension = _definition_indexes(requested_definitions)
    requested_catalog = build_dimension_value_catalog(requested_definitions)
    if len(header_ids) != len(set(header_ids)):
        analysis.checks.append(
            _check(
                "V4_INPUT_HEADERS",
                status="FAIL",
                blocking=True,
                detail="Dimension header가 중복되었습니다.",
            )
        )
    unknown_headers = [header for header in header_ids if header not in effective_by_id]
    required_headers = stored_headers
    missing_headers = [header for header in required_headers if header not in set(header_ids)]
    if unknown_headers or missing_headers:
        unknown_labels = [requested_header_labels.get(item) or "선택할 수 없는 분기" for item in unknown_headers]
        missing_labels = [
            _definition_label(effective_by_id[item], item) if item in effective_by_id else "기존 분기"
            for item in missing_headers
        ]
        analysis.checks.append(
            _check(
                "V4_INPUT_HEADERS",
                status="FAIL",
                blocking=True,
                detail="추가할 수 없는 분기가 있거나 기존 분기가 표에서 빠졌습니다.",
                offenders=[
                    *[f"추가할 수 없음: {item}" for item in unknown_labels],
                    *[f"표에서 빠짐: {item}" for item in missing_labels],
                ],
            )
        )

    rows = request_table.get("rows") or []
    if not 2 <= len(rows) <= 7:
        analysis.checks.append(
            _check(
                "V4_SCENARIO_COUNT",
                status="FAIL",
                blocking=True,
                detail=f"최종 Scenario 수는 2~7개여야 합니다. 현재 {len(rows)}개입니다.",
            )
        )

    persisted_by_id = {
        int(_get(scenario, "scenario_id", "scenarioId")): scenario
        for scenario in persisted_scenarios
        if _get(scenario, "scenario_id", "scenarioId") is not None
    }
    seen_ids: set[int] = set()
    title_keys: dict[str, str] = {}
    combinations: dict[tuple[tuple[str, str], ...], str] = {}
    for index, raw_row in enumerate(rows, start=1):
        if not isinstance(raw_row, dict):
            analysis.checks.append(
                _check(
                    "V4_INPUT_ROW",
                    status="FAIL",
                    blocking=True,
                    detail=f"{index}번째 Scenario row 형식이 올바르지 않습니다.",
                )
            )
            continue
        scenario_id, client_row_key = _row_key(raw_row, index)
        display_order = int(_get(raw_row, "display_order", "displayOrder") or index)
        title = str(raw_row.get("title") or "").strip()
        scenario_label = f"'{title}' 시나리오" if title else f"{display_order}번째 시나리오"
        if scenario_id is not None:
            if scenario_id in seen_ids:
                analysis.checks.append(
                    _check(
                        "V4_SCENARIO_ID",
                        status="FAIL",
                        blocking=True,
                        detail=f"{scenario_label}가 중복되었습니다.",
                        offenders=[scenario_label],
                    )
                )
            seen_ids.add(scenario_id)
            if scenario_id not in persisted_by_id:
                analysis.checks.append(
                    _check(
                        "V4_SCENARIO_ID",
                        status="FAIL",
                        blocking=True,
                        detail=f"{scenario_label}는 현재 표에 속한 시나리오가 아닙니다.",
                        offenders=[scenario_label],
                    )
                )
        title_key = normalize_title(title)
        if not title_key:
            analysis.checks.append(
                _check(
                    "V4_TITLE_REQUIRED",
                    status="FAIL",
                    blocking=True,
                    detail=f"{display_order}번째 Scenario 제목이 비어 있습니다.",
                    offenders=[client_row_key],
                )
            )
        elif title_key in title_keys:
            analysis.checks.append(
                _check(
                    "V4_TITLE_DUPLICATE",
                    status="FAIL",
                    blocking=True,
                    detail="공백·문장부호·대소문자를 제외하면 같은 Scenario 제목이 있습니다.",
                    offenders=[title_keys[title_key], client_row_key],
                )
            )
        else:
            title_keys[title_key] = client_row_key

        raw_cells = raw_row.get("cells") or {}
        if not isinstance(raw_cells, dict) or set(raw_cells) != set(header_ids):
            analysis.checks.append(
                _check(
                    "V4_INPUT_CELLS",
                    status="FAIL",
                    blocking=True,
                    detail=f"{client_row_key}의 cell key가 header와 일치하지 않습니다.",
                    offenders=[client_row_key],
                )
            )
            raw_cells = raw_cells if isinstance(raw_cells, dict) else {}
        canonical_cells: dict[str, str] = {}
        invalid_cells: list[str] = []
        for dimension_id in header_ids:
            raw_value = raw_cells.get(dimension_id)
            if (
                _is_additional_dimension_id(dimension_id)
                and dimension_id in effective_by_id
                and (raw_value is None or (isinstance(raw_value, str) and not raw_value.strip()))
            ):
                continue
            try:
                canonical = canonicalize_dimension_value(
                    requested_catalog,
                    dimension_id,
                    raw_value,
                    allow_label_compatibility=True,
                )
            except ValueError:
                definition = effective_by_id.get(dimension_id, {})
                dimension_label = _definition_label(definition, dimension_id)
                value_status = "값 없음" if raw_value is None or not str(raw_value).strip() else "선택할 수 없는 값"
                invalid_cells.append(f"{dimension_label}: {value_status}")
            else:
                canonical_cells[dimension_id] = canonical
        if invalid_cells:
            analysis.checks.append(
                _check(
                    "V4_VALUE_ENUM",
                    status="FAIL",
                    blocking=True,
                    detail=f"{scenario_label}에 비어 있거나 선택할 수 없는 분기 값이 있습니다.",
                    offenders=invalid_cells,
                )
            )
        combination = tuple((header, canonical_cells[header]) for header in header_ids if header in canonical_cells)
        if len(combination) == len(header_ids):
            if combination in combinations:
                analysis.checks.append(
                    _check(
                        "V4_COMBINATION_DUPLICATE",
                        status="FAIL",
                        blocking=True,
                        detail="동일한 canonical Dimension value 조합이 중복되었습니다.",
                        offenders=[combinations[combination], client_row_key],
                    )
                )
            else:
                combinations[combination] = client_row_key

        persisted = persisted_by_id.get(scenario_id) if scenario_id is not None else None
        row_autofilled = {
            dimension_id: value_id
            for (row_key, dimension_id), value_id in (autofilled_cells or {}).items()
            if row_key == client_row_key
        }
        change_type: str | None = None
        if persisted is None:
            change_type = "NEW"
        else:
            stored_cells = _canonical_persisted_cells(
                persisted,
                stored_headers,
                value_ids_by_dimension,
                labels_by_dimension,
            )
            requested_stored_cells = {
                dimension_id: canonical_cells[dimension_id]
                for dimension_id in stored_headers
                if dimension_id in canonical_cells
            }
            requested_user_stored_cells = {
                dimension_id: value_id
                for dimension_id, value_id in requested_stored_cells.items()
                if dimension_id not in row_autofilled
            }
            explicit_added_values = [
                dimension_id
                for dimension_id in analysis.added_dimension_ids
                if dimension_id in canonical_cells and dimension_id not in row_autofilled
            ]
            if stored_cells != requested_user_stored_cells or explicit_added_values:
                change_type = "COMBINATION_CHANGED"
            elif row_autofilled:
                change_type = "AUTOFILL_ONLY"
            elif normalize_title(persisted.get("title")) != normalize_title(title):
                change_type = "TITLE_CHANGED"
            elif int(_get(persisted, "display_order", "displayOrder") or 0) != display_order:
                change_type = "REORDERED"
        row = CanonicalScenarioRow(
            scenario_id=scenario_id,
            client_row_key=client_row_key,
            row_index=index,
            display_order=display_order,
            title=title,
            dimension_values=canonical_cells,
            change_type=change_type,
            autofilled_dimension_values=row_autofilled,
        )
        analysis.canonical_rows.append(row)
        if change_type is not None:
            analysis.changed_rows.append(row)

    analysis.deleted_scenario_ids = sorted(set(persisted_by_id) - seen_ids)
    preserved_existing_order = [item for item in header_ids if item in set(stored_headers)]
    if preserved_existing_order != stored_headers:
        analysis.checks.append(
            _check(
                "V4_HEADER_ORDER",
                status="FAIL",
                blocking=True,
                detail="기존 Dimension header의 상대 순서가 저장된 순서와 일치하지 않습니다.",
                offenders=header_ids,
            )
        )

    excluded_candidates = _get(generation_diagnostics, "excluded_candidates", "excludedCandidates") or []
    final_combinations = {
        tuple(sorted(row.dimension_values.items())): row.client_row_key
        for row in analysis.canonical_rows
        if len(row.dimension_values) == len(header_ids)
    }
    for candidate in excluded_candidates:
        if not isinstance(candidate, dict):
            continue
        reason_code = str(_get(candidate, "reason_code", "reasonCode") or "")
        raw_values = _get(candidate, "dimension_values", "dimensionValues") or {}
        if reason_code != "LOW_PROBABILITY" or not isinstance(raw_values, dict):
            continue
        canonical_values: dict[str, str] = {}
        for dimension_id, raw_value in raw_values.items():
            canonical = _canonical_value(
                str(dimension_id),
                raw_value,
                value_ids_by_dimension,
                labels_by_dimension,
            )
            if canonical is not None:
                canonical_values[str(dimension_id)] = canonical
        row_key = final_combinations.get(tuple(sorted(canonical_values.items())))
        if row_key is None:
            continue
        reason = str(candidate.get("reason") or "Create에서 낮은 가능성으로 제외한 조합입니다.")
        analysis.checks.append(
            _check(
                "V4_LOW_PROBABILITY_REINTRODUCED",
                status="WARN",
                blocking=False,
                detail=reason,
                offenders=[row_key],
                advice=["낮은 가능성 조합임을 확인한 뒤 그대로 진행할 수 있습니다."],
            )
        )
    return analysis


def check_counts(checks: list[ValidationCheckPayload]) -> dict[str, int]:
    return {status: sum(1 for check in checks if check.status == status) for status in ("PASS", "WARN", "FAIL", "INFO")}


def normalize_v4_probability_scores(scores: list[float]) -> list[int]:
    """Normalize relative weights to integer percentages using the largest-remainder method."""
    if not scores:
        return []
    weights = [Decimal(str(score)) for score in scores]
    total = sum(weights)
    if total <= 0:
        weights = [Decimal(1)] * len(weights)
        total = Decimal(len(weights))
    exact = [weight * Decimal(100) / total for weight in weights]
    floors = [int(value) for value in exact]
    deficit = 100 - sum(floors)
    remainder_order = sorted(
        range(len(exact)),
        key=lambda index: (-(exact[index] - Decimal(floors[index])), index),
    )
    for index in remainder_order[:deficit]:
        floors[index] += 1
    return floors


def validate_v4_pressure_aggregate(  # noqa: C901
    *,
    rows: list[CanonicalScenarioRow],
    dimension_definitions: list[dict[str, Any]],
    pressure_bands: dict[str, str],
) -> list[ValidationCheckPayload]:
    contribution_score = {"bullish": 1, "balanced": 0, "bearish": -1}
    contribution_by_value: dict[tuple[str, str], int] = {}
    for definition in dimension_definitions:
        dimension_id = _definition_id(definition)
        for value in definition.get("values") or []:
            if not isinstance(value, dict):
                continue
            contribution = _pressure_contribution(value)
            if dimension_id and (value_id := _value_id(value)) and contribution is not None:
                contribution_by_value[(dimension_id, value_id)] = contribution_score[contribution]

    pressure_rank = {
        "strong_bearish": 0,
        "bearish": 1,
        "balanced": 2,
        "bullish": 3,
        "strong_bullish": 4,
    }
    scored: list[tuple[CanonicalScenarioRow, str, int]] = []
    for row in rows:
        band = pressure_bands.get(row.client_row_key)
        if band not in pressure_rank:
            continue
        score = sum(
            contribution_by_value.get((dimension_id, value_id), 0)
            for dimension_id, value_id in row.dimension_values.items()
        )
        scored.append((row, band, score))

    checks: list[ValidationCheckPayload] = []
    extreme_offenders = [
        f"{row.client_row_key}:{band}={score}"
        for row, band, score in scored
        if (band == "strong_bullish" and score <= 0) or (band == "strong_bearish" and score >= 0)
    ]
    if extreme_offenders:
        checks.append(
            _check(
                "V4_PRESSURE_EXTREME_SIGN",
                status="FAIL",
                blocking=True,
                detail="strong pressureBand의 부호가 Dimension pressureContribution 합과 일치하지 않습니다.",
                offenders=extreme_offenders,
            )
        )

    order_offenders: list[str] = []
    for lower_row, lower_band, lower_score in scored:
        for higher_row, higher_band, higher_score in scored:
            if pressure_rank[lower_band] >= pressure_rank[higher_band] or lower_score <= higher_score:
                continue
            order_offenders.append(
                f"{lower_row.client_row_key}:{lower_band}={lower_score} > "
                f"{higher_row.client_row_key}:{higher_band}={higher_score}"
            )
    if order_offenders:
        checks.append(
            _check(
                "V4_PRESSURE_AGGREGATE_ORDER",
                status="FAIL",
                blocking=True,
                detail="pressureBand 순서가 Dimension pressureContribution 합계 순서와 역전되었습니다.",
                offenders=order_offenders,
            )
        )
    return checks


def _major_change_items(analysis: V4ValidationAnalysis) -> list[str]:
    added_scenarios = sum(row.scenario_id is None for row in analysis.canonical_rows)
    changes = [
        (len(analysis.added_dimension_ids), "분기 추가"),
        (len(analysis.removed_dimension_ids), "분기 삭제"),
        (added_scenarios, "시나리오 추가"),
        (len(analysis.deleted_scenario_ids), "시나리오 삭제"),
    ]
    return [f"{count}개의 {label}" for count, label in changes if count]


def _display_reason_text(value: str, analysis: V4ValidationAnalysis) -> str:
    row_labels = {
        row.client_row_key: f"'{row.title}' 시나리오" if row.title else f"{row.display_order}번째 시나리오"
        for row in analysis.canonical_rows
    }
    rendered = value
    for row_key in sorted(row_labels, key=len, reverse=True):
        rendered = rendered.replace(row_key, row_labels[row_key])
    return rendered


def render_reason_markdown(
    checks: list[ValidationCheckPayload],
    *,
    analysis: V4ValidationAnalysis,
) -> str:
    notable = [check for check in checks if check.status in {"FAIL", "WARN"}]
    major_changes = _major_change_items(analysis)
    if not notable:
        if major_changes:
            return f"[주요 변경] {', '.join(major_changes)}"
        return "변경한 내용을 검토했으며 적용할 수 있습니다."
    lines: list[str] = []
    blocking = sum(1 for check in notable if check.blocking)
    warnings = sum(1 for check in notable if not check.blocking)
    lines.append(f"검토 결과 — 차단 {blocking}건, 경고 {warnings}건")
    for check in notable:
        label = "차단" if check.blocking else "경고"
        lines.append(f"- [{label}] {_display_reason_text(check.detail, analysis)}")
        if check.offenders:
            offenders = [_display_reason_text(item, analysis) for item in check.offenders[:5]]
            lines.append(f"  - 대상: {', '.join(offenders)}")
        lines.extend(f"  - 안내: {_display_reason_text(advice, analysis)}" for advice in check.advice[:3])
    if major_changes:
        lines.append(f"[주요 변경] {', '.join(major_changes)}")
    return "\n".join(lines)


def slug_client_row_key(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9:_-]", "_", value)
