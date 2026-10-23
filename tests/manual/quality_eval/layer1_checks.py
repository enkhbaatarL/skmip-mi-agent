from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from apps.agents.scenario_group_agent.utils.claim_kind import (
    forecast_values_stated_as_fact,
    split_rationale_fields,
)

if TYPE_CHECKING:
    from quality_eval.artifacts import RunArtifacts


CheckStatus = Literal["PASS", "WARN", "FAIL", "SKIP"]
_DIRECTION_CODES = {"SUP"}
_STRENGTHS = {"VERYSTRONG", "STRONG", "MEDIUM", "WEAK", "VERYWEAK"}
_IMPACT_SCORES = {0.10, 0.25, 0.50, 1.00, 1.25}


@dataclass(frozen=True)
class CheckResult:
    check_id: str
    status: CheckStatus
    detail: str
    offenders: list[str]


def run_layer1_checks(run: RunArtifacts) -> list[CheckResult]:
    """Run deterministic structural checks without judging scenario meaning."""
    scenario_table = _table_from(run.step2) or _table_from(run.step1)
    baseline_table = _table_from(run.step1) or _table_from(run.step3) or scenario_table
    signpost_table = _table_from(run.step3)
    return [
        _check_required_callback_fields(run),
        _check_single_baseline(baseline_table),
        _check_cells(scenario_table, _table_from(run.step1)),
        _check_template_enums(scenario_table, run.event_detail),
        _check_duplicate_combinations(scenario_table),
        _check_scenario_count(scenario_table, _group_from(run.step1) or _group_from(run.step2)),
        _check_signposts(signpost_table),
        _check_common_signposts(signpost_table),
        _check_validation_stage(run.step2),
        _check_forecast_stated_as_fact(run.group_detail),
    ]


def _check_required_callback_fields(run: RunArtifacts) -> CheckResult:
    offenders: list[str] = []
    for name, payload in (("step1", run.step1), ("step2", run.step2), ("step3", run.step3)):
        if not isinstance(payload, dict):
            offenders.append(f"{name}: callback missing")
            continue
        if not isinstance(_group_from(payload), dict):
            offenders.append(f"{name}: scenarioGroup missing")
        table = _table_from(payload)
        if not isinstance(table, dict):
            offenders.append(f"{name}: table missing")
            continue
        if not isinstance(table.get("headers"), list):
            offenders.append(f"{name}: table.headers missing")
        rows = table.get("rows")
        if not isinstance(rows, list):
            offenders.append(f"{name}: table.rows missing")
        elif any(not isinstance(row, dict) or not isinstance(row.get("cells"), dict) for row in rows):
            offenders.append(f"{name}: rows[].cells missing")
    return _result("R-01", offenders, "All generation callbacks expose scenarioGroup/table/headers/rows/cells.")


def _check_single_baseline(table: dict[str, Any] | None) -> CheckResult:
    if table is None:
        return _skip("R-02", "missing scenario table")
    rows = _rows(table)
    baselines = [str(_field(row, "scenarioId", "scenario_id") or index) for index, row in enumerate(rows) if _field(row, "baselineYn", "baseline_yn") == "Y"]
    if len(baselines) == 1:
        return _pass("R-02", "Exactly one baseline row.")
    return _fail("R-02", f"Expected exactly one baselineYn=Y, found {len(baselines)}.", baselines or ["no baseline"])


def _check_cells(
    table: dict[str, Any] | None,
    create_table: dict[str, Any] | None,
) -> CheckResult:
    if table is None:
        return _skip("R-03", "missing scenario table")
    header_keys = {str(header.get("key")) for header in table.get("headers", []) if isinstance(header, dict) and header.get("key")}
    if not header_keys:
        return _fail("R-03", "No usable header keys.", ["headers"])
    create_header_keys = _header_keys(create_table)
    validation_generated_keys = header_keys - create_header_keys if create_header_keys else set()
    offenders: list[str] = []
    for index, row in enumerate(_rows(table), start=1):
        cells = row.get("cells")
        row_id = _row_id(row, index)
        if not isinstance(cells, dict):
            offenders.append(f"{row_id}: cells missing")
            continue
        keys = set(map(str, cells))
        required_keys = header_keys - validation_generated_keys
        if not required_keys <= keys or not keys <= header_keys:
            offenders.append(f"{row_id}: cell keys={sorted(keys)} required_headers={sorted(required_keys)}")
        for key in required_keys:
            value = cells.get(key)
            if value is None or (isinstance(value, str) and not value.strip()):
                offenders.append(f"{row_id}: empty {key}")
    generated_detail = (
        f" Validation-generated dimensions exempted: {sorted(validation_generated_keys)}."
        if validation_generated_keys
        else ""
    )
    return _result("R-03", offenders, "Every row has non-empty cells for required headers." + generated_detail)


def _check_template_enums(table: dict[str, Any] | None, event_detail: dict[str, Any] | None) -> CheckResult:
    if table is None:
        return _skip("R-04", "missing scenario table")
    if event_detail is None:
        return _skip("R-04", "missing event_detail")
    enums = _template_enums(event_detail)
    if not enums:
        return _skip("R-04", "missing event_detail.scenarioTemplate value enums")
    offenders: list[str] = []
    for index, row in enumerate(_rows(table), start=1):
        cells = row.get("cells") or {}
        if not isinstance(cells, dict):
            continue
        for key, allowed in enums.items():
            if key in cells and cells[key] not in allowed:
                offenders.append(f"{_row_id(row, index)}: {key}={cells[key]!r} not in {sorted(map(str, allowed))}")
    return _result("R-04", offenders, "Cell values conform to event scenario-template enums.")


def _check_duplicate_combinations(table: dict[str, Any] | None) -> CheckResult:
    if table is None:
        return _skip("R-05", "missing scenario table")
    seen: dict[tuple[tuple[str, str], ...], str] = {}
    offenders: list[str] = []
    for index, row in enumerate(_rows(table), start=1):
        cells = row.get("cells")
        if not isinstance(cells, dict):
            continue
        combination = tuple(sorted((str(key), repr(value)) for key, value in cells.items()))
        row_id = _row_id(row, index)
        if combination in seen:
            offenders.append(f"{seen[combination]} == {row_id}")
        else:
            seen[combination] = row_id
    return _result("R-05", offenders, "Scenario dimension-value combinations are unique.")


def _check_scenario_count(table: dict[str, Any] | None, group: dict[str, Any] | None) -> CheckResult:
    if table is None:
        return _skip("R-06", "missing scenario table")
    actual = len(_rows(table))
    expected = _field(group or {}, "scenarioCount", "scenario_count")
    if expected is not None:
        try:
            expected_count = int(expected)
        except (TypeError, ValueError):
            return _warn("R-06", f"Invalid configured scenarioCount={expected!r}.", ["scenarioCount"])
        if actual == expected_count:
            return _pass("R-06", f"Scenario count {actual} matches configured count.")
        return _fail("R-06", f"Scenario count {actual} does not match configured {expected_count}.", ["rows"])
    if 5 <= actual <= 7:
        return _pass("R-06", f"Scenario count {actual} is in default operating range 5..7.")
    return _warn("R-06", f"Scenario count {actual} is outside default operating range 5..7.", ["rows"])


def _check_signposts(table: dict[str, Any] | None) -> CheckResult:
    if table is None:
        return _skip("R-07", "missing signpost callback table")
    offenders: list[str] = []
    for index, row in enumerate(_rows(table), start=1):
        row_id = _row_id(row, index)
        signposts = row.get("signposts")
        if not isinstance(signposts, list) or not signposts:
            offenders.append(f"{row_id}: no signposts")
            continue
        for signpost_index, signpost in enumerate(signposts, start=1):
            if not isinstance(signpost, dict):
                offenders.append(f"{row_id}: signpost {signpost_index} is invalid")
                continue
            signpost_id = _field(signpost, "signpostId", "signpost_id")
            label = signpost.get("label")
            strength = signpost.get("strength")
            score = _field(signpost, "probabilityImpactScore", "probability_impact_score")
            direction = _field(signpost, "probabilityDirectionCode", "probability_direction_code")
            prefix = f"{row_id}: signpost {signpost_index}"
            if signpost_id is None or not str(label or "").strip() or not str(strength or "").strip():
                offenders.append(f"{prefix}: id/label/strength missing")
            if str(strength or "").upper() not in _STRENGTHS:
                offenders.append(f"{prefix}: invalid strength={strength!r}")
            try:
                valid_score = float(score) in _IMPACT_SCORES
            except (TypeError, ValueError):
                valid_score = False
            if not valid_score:
                offenders.append(f"{prefix}: invalid probabilityImpactScore={score!r}")
            if str(direction or "").upper() not in _DIRECTION_CODES:
                offenders.append(f"{prefix}: invalid direction={direction!r}")
    return _result("R-07", offenders, "Each scenario has valid signpost identifiers, labels, strengths, score and direction.")


def _check_common_signposts(table: dict[str, Any] | None) -> CheckResult:
    if table is None:
        return _skip("R-08", "missing signpost callback table")
    rows = _rows(table)
    if not rows:
        return _fail("R-08", "No scenario rows available for signpost discriminativeness.", ["rows"])
    labels_by_row = [
        {str(item.get("label")).strip() for item in row.get("signposts", []) if isinstance(item, dict) and str(item.get("label") or "").strip()}
        for row in rows
    ]
    common = set.intersection(*labels_by_row) if labels_by_row else set()
    if common:
        return _warn("R-08", f"Common signpost labels have 100% coverage ({len(rows)}/{len(rows)}).", sorted(common))
    return _pass("R-08", "No signpost label appears in every scenario.")


def _check_validation_stage(payload: dict[str, Any] | None) -> CheckResult:
    if payload is None:
        return _skip("R-09", "missing validation callback")
    is_valid = _field(payload, "isValid", "is_valid")
    stage = _field(_group_from(payload) or {}, "stage")
    if not isinstance(is_valid, bool):
        return _fail("R-09", "validation callback isValid missing or non-boolean.", ["isValid"])
    expected = "scenario_validated" if is_valid else "scenario_created"
    if stage == expected:
        return _pass("R-09", f"isValid={is_valid} matches stage={stage}.")
    return _fail("R-09", f"isValid={is_valid} requires stage={expected}, got {stage!r}.", ["stage"])


def _check_forecast_stated_as_fact(group_detail: dict[str, Any] | None) -> CheckResult:
    """R-10: Choice why의 사실 칸에 Event 전망값이 전망 표시 없이 들어갔는지 확인한다."""
    group = _group_from(group_detail) or group_detail or {}
    definitions = _field(group, "dimensionDefinitions", "dimension_definitions")
    diagnostics = _field(group, "generationDiagnostics", "generation_diagnostics")
    if not isinstance(definitions, list) or not isinstance(diagnostics, dict):
        return _skip("R-10", "missing group detail dimensionDefinitions/generationDiagnostics")
    claims = _field(diagnostics, "forecastClaims", "forecast_claims")
    if not isinstance(claims, list):
        return _skip("R-10", "generationDiagnostics.forecastClaims missing (generated before claim classification)")
    anchors = [
        str(anchor)
        for claim in claims
        if isinstance(claim, dict) and _field(claim, "claimKind", "claim_kind") == "forecast"
        for anchor in _field(claim, "anchors") or []
    ]
    offenders = []
    for definition in definitions:
        for value in _field(definition, "values") or []:
            why = str(_field(value, "assumptionRationale", "assumption_rationale") or "")
            stated = forecast_values_stated_as_fact(split_rationale_fields(why).get("사실", ""), anchors)
            if stated:
                offenders.append(f"{_field(value, 'valueId', 'value_id')}: {', '.join(stated)}")
    if offenders:
        return _warn("R-10", "Forecast values are stated as facts in Choice why.", offenders)
    return _pass("R-10", f"No forecast value stated as fact ({len(anchors)} forecast anchors checked).")


def _template_enums(event_detail: dict[str, Any] | None) -> dict[str, set[Any]]:
    template = _field(event_detail or {}, "scenarioTemplate", "scenario_template")
    if isinstance(template, dict):
        template = _field(template, "dimensions", "items", "template") or template.get("value") or _field(
            template,
            "rawTemplateJson",
            "raw_template_json",
        )
    if not isinstance(template, list):
        nested = (event_detail or {}).get("data")
        template = _field(nested, "scenarioTemplate", "scenario_template") if isinstance(nested, dict) else None
    if not isinstance(template, list):
        return {}
    enums: dict[str, set[Any]] = {}
    for dimension in template:
        if not isinstance(dimension, dict):
            continue
        key = _field(dimension, "dimKey", "dim_key", "key")
        values = _field(dimension, "enumValues", "enum_values", "valueEnums", "value_enums", "values", "enum")
        if key and isinstance(values, list) and values:
            enums[str(key)] = set(values)
    return enums


def _group_from(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    group = _field(payload or {}, "scenarioGroup", "scenario_group")
    return group if isinstance(group, dict) else None


def _table_from(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    table = (payload or {}).get("table")
    return table if isinstance(table, dict) else None


def _rows(table: dict[str, Any]) -> list[dict[str, Any]]:
    rows = table.get("rows")
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def _header_keys(table: dict[str, Any] | None) -> set[str]:
    return {
        str(header.get("key"))
        for header in (table or {}).get("headers", [])
        if isinstance(header, dict) and header.get("key")
    }


def _field(payload: dict[str, Any], *names: str) -> Any:
    return next((payload[name] for name in names if name in payload), None)


def _row_id(row: dict[str, Any], index: int) -> str:
    return str(_field(row, "scenarioId", "scenario_id") or f"row-{index}")


def _pass(check_id: str, detail: str) -> CheckResult:
    return CheckResult(check_id, "PASS", detail, [])


def _warn(check_id: str, detail: str, offenders: list[str]) -> CheckResult:
    return CheckResult(check_id, "WARN", detail, offenders)


def _fail(check_id: str, detail: str, offenders: list[str]) -> CheckResult:
    return CheckResult(check_id, "FAIL", detail, offenders)


def _skip(check_id: str, detail: str) -> CheckResult:
    return CheckResult(check_id, "SKIP", detail, [])


def _result(check_id: str, offenders: list[str], success_detail: str) -> CheckResult:
    return _fail(check_id, success_detail, offenders) if offenders else _pass(check_id, success_detail)
