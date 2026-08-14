from __future__ import annotations

# ruff: noqa: COM812, CPY001
from dataclasses import dataclass, field
from decimal import Decimal
import hashlib
import json
import re
from typing import Any
import unicodedata

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
    display_order: int
    title: str
    dimension_values: dict[str, str]
    change_type: str | None = None

    def review_scenario_id(self) -> int:
        return self.scenario_id if self.scenario_id is not None else -self.display_order

    def as_review_row(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
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

    @property
    def blocking(self) -> bool:
        return any(check.blocking and check.status == "FAIL" for check in self.checks)

    @property
    def unchanged(self) -> bool:
        return not self.blocking and not self.changed_rows and not self.deleted_scenario_ids


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


def analyze_v4_validation_request(  # noqa: C901
    *,
    request_table: dict[str, Any],
    persisted_scenarios: list[dict[str, Any]],
    dimension_definitions: list[dict[str, Any]],
    generation_diagnostics: dict[str, Any],
    stored_header_order: list[str] | None = None,
) -> V4ValidationAnalysis:
    expected_headers, value_ids_by_dimension, labels_by_dimension = _definition_indexes(dimension_definitions)
    base_fingerprint = scenario_fingerprint(persisted_scenarios)
    definition_fingerprint = dimension_definition_fingerprint(dimension_definitions)
    analysis = V4ValidationAnalysis(
        canonical_headers=[],
        canonical_rows=[],
        changed_rows=[],
        deleted_scenario_ids=[],
        base_scenario_fingerprint=base_fingerprint,
        dimension_definition_fingerprint=definition_fingerprint,
    )
    raw_headers = request_table.get("headers") or []
    header_ids = [str(header.get("key") or "").strip() for header in raw_headers if isinstance(header, dict)]
    analysis.canonical_headers = header_ids
    if len(header_ids) != len(set(header_ids)):
        analysis.checks.append(
            _check(
                "V4_INPUT_HEADERS",
                status="FAIL",
                blocking=True,
                detail="Dimension header가 중복되었습니다.",
            )
        )
    unknown_headers = [header for header in header_ids if header not in value_ids_by_dimension]
    missing_headers = [header for header in expected_headers if header not in set(header_ids)]
    if unknown_headers or missing_headers or len(header_ids) != len(expected_headers):
        analysis.checks.append(
            _check(
                "V4_INPUT_HEADERS",
                status="FAIL",
                blocking=True,
                detail="현재 Dimension definition과 header 구성이 일치하지 않습니다.",
                offenders=[
                    *[f"unknown:{item}" for item in unknown_headers],
                    *[f"missing:{item}" for item in missing_headers],
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
        raw_id = _get(raw_row, "scenario_id", "scenarioId")
        scenario_id = int(raw_id) if raw_id is not None else None
        display_order = int(_get(raw_row, "display_order", "displayOrder") or index)
        client_row_key = f"scenario:{scenario_id}" if scenario_id is not None else f"new:{display_order}"
        if scenario_id is not None:
            if scenario_id in seen_ids:
                analysis.checks.append(
                    _check(
                        "V4_SCENARIO_ID",
                        status="FAIL",
                        blocking=True,
                        detail=f"scenarioId {scenario_id}가 중복되었습니다.",
                        offenders=[str(scenario_id)],
                    )
                )
            seen_ids.add(scenario_id)
            if scenario_id not in persisted_by_id:
                analysis.checks.append(
                    _check(
                        "V4_SCENARIO_ID",
                        status="FAIL",
                        blocking=True,
                        detail=f"현재 그룹에 속하지 않는 scenarioId입니다: {scenario_id}",
                        offenders=[str(scenario_id)],
                    )
                )
        title = str(raw_row.get("title") or "").strip()
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
            canonical = _canonical_value(
                dimension_id,
                raw_cells.get(dimension_id),
                value_ids_by_dimension,
                labels_by_dimension,
            )
            if canonical is None:
                invalid_cells.append(f"{dimension_id}={raw_cells.get(dimension_id)!r}")
            else:
                canonical_cells[dimension_id] = canonical
        if invalid_cells:
            analysis.checks.append(
                _check(
                    "V4_VALUE_ENUM",
                    status="FAIL",
                    blocking=True,
                    detail=f"{client_row_key}에 허용되지 않거나 비어 있는 Dimension value가 있습니다.",
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
        change_type: str | None = None
        if persisted is None:
            change_type = "NEW"
        else:
            stored_cells = _canonical_persisted_cells(
                persisted,
                header_ids,
                value_ids_by_dimension,
                labels_by_dimension,
            )
            if stored_cells != canonical_cells:
                change_type = "COMBINATION_CHANGED"
            elif normalize_title(persisted.get("title")) != normalize_title(title):
                change_type = "TITLE_CHANGED"
            elif int(_get(persisted, "display_order", "displayOrder") or 0) != display_order:
                change_type = "REORDERED"
        row = CanonicalScenarioRow(
            scenario_id=scenario_id,
            client_row_key=client_row_key,
            display_order=display_order,
            title=title,
            dimension_values=canonical_cells,
            change_type=change_type,
        )
        analysis.canonical_rows.append(row)
        if change_type is not None:
            analysis.changed_rows.append(row)

    analysis.deleted_scenario_ids = sorted(set(persisted_by_id) - seen_ids)
    expected_order = stored_header_order or expected_headers
    if header_ids != expected_order:
        analysis.checks.append(
            _check(
                "V4_HEADER_ORDER",
                status="FAIL",
                blocking=True,
                detail="Dimension header 순서가 Create 결과와 일치하지 않습니다.",
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


def render_reason_markdown(checks: list[ValidationCheckPayload], *, generated_count: int = 0) -> str:
    notable = [check for check in checks if check.status in {"FAIL", "WARN"}]
    if not notable and generated_count == 0:
        return "모든 시나리오 검토 항목을 통과했습니다."
    lines: list[str] = []
    blocking = sum(1 for check in notable if check.blocking)
    warnings = sum(1 for check in notable if not check.blocking)
    lines.append(f"검토 결과 — 차단 {blocking}건, 경고 {warnings}건")
    for check in notable:
        label = "차단" if check.blocking else "경고"
        lines.append(f"- [{label}] {check.detail}")
        if check.offenders:
            lines.append(f"  - 대상: {', '.join(check.offenders[:5])}")
        lines.extend(f"  - 안내: {advice}" for advice in check.advice[:3])
    if generated_count:
        lines.append(f"- [반영 예정] {generated_count}개 Scenario의 저장 필드를 생성했습니다.")
    return "\n".join(lines)


def slug_client_row_key(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9:_-]", "_", value)
