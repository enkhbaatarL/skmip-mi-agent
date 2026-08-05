from __future__ import annotations

# ruff: noqa: CPY001
from collections import Counter
from typing import Any

from tests.manual.multi_event_comparison.models import ApiVersion, QualityCheck


_PRESSURE_ORDER = {
    "strong_bearish": 0,
    "bearish": 1,
    "balanced": 2,
    "bullish": 3,
    "strong_bullish": 4,
}
_DIMENSION_RANGES: dict[ApiVersion, tuple[int, int]] = {
    "v2": (3, 6),
    "v3": (3, 6),
    "v4": (3, 6),
}


def run_deterministic_checks(
    version: ApiVersion,
    response: dict[str, Any],
    event_ids: list[int],
) -> list[QualityCheck]:
    data = response.get("data") if isinstance(response.get("data"), dict) else {}
    table = data.get("table") if isinstance(data.get("table"), dict) else {}
    rows = [row for row in table.get("rows", []) if isinstance(row, dict)]
    dimensions = [item for item in data.get("dimensionDefinitions", []) if isinstance(item, dict)]
    return [
        _scenario_count(rows),
        _single_baseline(rows),
        _unique_cells_and_bands(rows),
        _roles_and_extrema(rows),
        _dimension_count(version, dimensions),
        _event_lineage(dimensions, event_ids),
        _required_rationales(rows),
        _pressure_band_coverage(data, rows),
    ]


def _scenario_count(rows: list[dict[str, Any]]) -> QualityCheck:
    count = len(rows)
    return _check(
        "M-01",
        3 <= count <= 5,
        f"Scenario count={count}; expected 3..5.",
        [] if 3 <= count <= 5 else ["table.rows"],
    )


def _single_baseline(rows: list[dict[str, Any]]) -> QualityCheck:
    baseline_ids = [_row_id(row) for row in rows if _field(row, "baselineYn", "baseline_yn") == "Y"]
    return _check(
        "M-02",
        len(baseline_ids) == 1,
        f"baselineYn=Y count={len(baseline_ids)}; expected exactly one.",
        [] if len(baseline_ids) == 1 else baseline_ids or ["no baseline"],
    )


def _unique_cells_and_bands(rows: list[dict[str, Any]]) -> QualityCheck:
    combinations: list[tuple[tuple[str, str], ...]] = []
    bands: list[str] = []
    offenders: list[str] = []
    for row in rows:
        cells = row.get("cells")
        if not isinstance(cells, dict) or not cells:
            offenders.append(f"{_row_id(row)}: empty cells")
        else:
            combinations.append(tuple(sorted((str(key), repr(value)) for key, value in cells.items())))
        band = str(_field(row, "globalPressureBand", "global_pressure_band") or "")
        if not band:
            offenders.append(f"{_row_id(row)}: missing pressure band")
        else:
            bands.append(band)
    duplicate_combinations = [repr(item) for item, count in Counter(combinations).items() if count > 1]
    duplicate_bands = [item for item, count in Counter(bands).items() if count > 1]
    offenders.extend(f"duplicate cells: {item}" for item in duplicate_combinations)
    offenders.extend(f"duplicate band: {item}" for item in duplicate_bands)
    return _check(
        "M-03",
        not offenders,
        "Scenario cell combinations and pressure bands must be present and unique.",
        offenders,
    )


def _roles_and_extrema(rows: list[dict[str, Any]]) -> QualityCheck:
    by_role: dict[str, list[dict[str, Any]]] = {}
    offenders: list[str] = []
    ranked_rows: list[tuple[int, dict[str, Any]]] = []
    for row in rows:
        role = str(_field(row, "scenarioRole", "scenario_role") or "").lower()
        by_role.setdefault(role, []).append(row)
        band = str(_field(row, "globalPressureBand", "global_pressure_band") or "")
        if band in _PRESSURE_ORDER:
            ranked_rows.append((_PRESSURE_ORDER[band], row))
    offenders.extend(
        f"{role} count={len(by_role.get(role, []))}" for role in ("floor", "ceiling") if len(by_role.get(role, [])) != 1
    )
    if (
        ranked_rows
        and len(by_role.get("floor", [])) == 1
        and by_role["floor"][0] is not min(ranked_rows, key=lambda item: item[0])[1]
    ):
        offenders.append("floor is not the lowest generated pressure band")
    if (
        ranked_rows
        and len(by_role.get("ceiling", [])) == 1
        and by_role["ceiling"][0] is not max(ranked_rows, key=lambda item: item[0])[1]
    ):
        offenders.append("ceiling is not the highest generated pressure band")
    for row in by_role.get("mixed", []):
        band = str(_field(row, "globalPressureBand", "global_pressure_band") or "")
        rank = _PRESSURE_ORDER.get(band)
        if rank is not None and rank in {0, 4}:
            offenders.append(f"{_row_id(row)}: mixed uses extreme band {band}")
    return _check(
        "M-04",
        not offenders,
        "Exactly one floor/ceiling, optional mixed roles on non-extreme bands, and role/band extrema alignment.",
        offenders,
    )


def _dimension_count(version: ApiVersion, dimensions: list[dict[str, Any]]) -> QualityCheck:
    minimum, maximum = _DIMENSION_RANGES[version]
    count = len(dimensions)
    return _check(
        "M-05",
        minimum <= count <= maximum,
        f"{version} dimension count={count}; expected {minimum}..{maximum}.",
        [] if minimum <= count <= maximum else ["dimensionDefinitions"],
    )


def _event_lineage(  # noqa: C901
    dimensions: list[dict[str, Any]],
    event_ids: list[int],
) -> QualityCheck:
    covered: set[int] = set()
    for dimension in dimensions:
        for grounding in dimension.get("eventGroundings", []) or dimension.get("event_groundings", []):
            if isinstance(grounding, dict):
                value = grounding.get("eventId") or grounding.get("event_id")
                if value is not None:
                    covered.add(int(value))
        for value in dimension.get("sourceEventIds", []) or dimension.get("source_event_ids", []):
            covered.add(int(value))
        for source in dimension.get("sourceRefs", []) or dimension.get("source_refs", []):
            if isinstance(source, dict):
                value = source.get("eventId") or source.get("event_id")
                if value is not None:
                    covered.add(int(value))
        compact_source = dimension.get("sourceRef") or dimension.get("source_ref")
        if isinstance(compact_source, dict):
            value = compact_source.get("eventId") or compact_source.get("event_id")
            if value is not None:
                covered.add(int(value))
        for value_definition in dimension.get("values", []):
            if not isinstance(value_definition, dict):
                continue
            assignments = value_definition.get("sourceAssignments", []) or value_definition.get(
                "source_assignments",
                [],
            )
            for source in assignments:
                if isinstance(source, dict):
                    value = source.get("eventId") or source.get("event_id")
                    if value is not None:
                        covered.add(int(value))
    missing = sorted(set(event_ids) - covered)
    return _check(
        "M-06",
        not missing,
        f"Dimension lineage covers {sorted(covered)} of selected events {sorted(event_ids)}.",
        [str(value) for value in missing],
    )


def _required_rationales(rows: list[dict[str, Any]]) -> QualityCheck:
    offenders = [
        _row_id(row)
        for row in rows
        if not str(_field(row, "globalPressureRationale", "global_pressure_rationale") or "").strip()
    ]
    return _check(
        "M-07",
        not offenders,
        "Every Scenario must expose a non-empty global pressure rationale.",
        offenders,
    )


def _pressure_band_coverage(data: dict[str, Any], rows: list[dict[str, Any]]) -> QualityCheck:
    expected = set(_PRESSURE_ORDER)
    generated = {
        str(_field(row, "globalPressureBand", "global_pressure_band"))
        for row in rows
        if _field(row, "globalPressureBand", "global_pressure_band")
    }
    diagnostics = data.get("generationDiagnostics") if isinstance(data.get("generationDiagnostics"), dict) else {}
    excluded = {
        str(_field(item, "globalPressureBand", "global_pressure_band"))
        for item in diagnostics.get("excludedCandidates", [])
        if isinstance(item, dict) and _field(item, "globalPressureBand", "global_pressure_band")
    }
    unrepresented = {str(band) for band in diagnostics.get("unrepresentedPressureBands", []) if band}
    declared = set(diagnostics.get("targetPressureBands", []))
    missing = sorted(expected - generated - excluded - unrepresented)
    offenders = [f"unexplained band: {band}" for band in missing]
    if declared != expected:
        offenders.append(f"targetPressureBands={sorted(declared)}")
    return _check(
        "M-08",
        not offenders,
        "Generated and explicitly excluded or unrepresented bands explain all five target pressure bands.",
        offenders,
    )


def _check(
    check_id: str,
    passed: bool,  # noqa: FBT001
    detail: str,
    offenders: list[str],
) -> QualityCheck:
    return QualityCheck(
        check_id=check_id,
        status="PASS" if passed else "FAIL",
        detail=detail,
        offenders=offenders,
    )


def _row_id(row: dict[str, Any]) -> str:
    return str(_field(row, "scenarioId", "scenario_id") or row.get("title") or "unknown")


def _field(payload: dict[str, Any], *names: str) -> Any:  # noqa: ANN401
    return next((payload[name] for name in names if name in payload), None)
