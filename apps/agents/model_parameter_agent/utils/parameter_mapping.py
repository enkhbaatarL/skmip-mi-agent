from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
import json
from pathlib import Path
import re
from typing import Any
import unicodedata

from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode


PACKAGE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_DIR = PACKAGE_DIR / "resources"
DEFAULT_BASECASE_DIR = DEFAULT_INPUT_DIR / "basecase"
DB_MAPPING_SOURCE = "db:tmm_mi_model_param_m,tmm_mi_model_param_dimension_map"
BASECASE_HEADER_SCAN_ROWS = 20
BASECASE_AXIS_LABELS = {
    "country",
    "fromcountry",
    "tocountry",
    "lngplant",
    "lngplanttrain",
    "plant",
    "train",
    "region",
    "route",
    "contract",
    "lifecategory",
    "lifecyclecategory",
    "nameplatecapacitymtpa",
}
BASECASE_TIME_LABELS = {"year", "month", "period"}
BASECASE_BAD_VALUES = {"#ref!", "#n/a", "#value!", "#div/0!"}
BASECASE_SPEC_COLUMNS = {
    "basecase_read_mode",
    "basecase_header_row",
    "basecase_data_start_row",
    "basecase_column_roles",
    "basecase_row_filter",
    "basecase_year_row",
    "basecase_month_row",
    "basecase_period_row",
    "basecase_value_start_col",
    "basecase_value_end_col",
    "basecase_stop_rule",
}
PARAMETER_ALIASES = {
    "Gas Demand[BCM/Mt]": "User-Adjusted Gas Demand",
    "Gas Demand [BCM/Mt]": "User-Adjusted Gas Demand",
    "VolumeCancelled": "VolumeCancelled",
    "Volume Cancelled": "VolumeCancelled",
    "RemainingUnrestrictedAmount": "RemainingUnrestrictedAmount",
    "ShippingCost (Charter/Fuel)": "ShippingCost",
    "ShippingCost (Suez/Panama Crossing·Disruption)": "ShippingCost",
    "ShippingCost": "ShippingCost",
    "PNG Contract Volume": "PNG Contract Volume",
}

MODEL_FILE_MARKERS = {
    "Demand": "Demand Model_Input",
    "Supply": "Supply Model_Input",
    "Trade": "Trade Model_Input",
}

@dataclass(frozen=True)
class ParameterDefinition:
    canonical_parameter_name: str
    parameter_hint: str | None
    model_file: str
    model_sheet: str
    model_table: str | None
    parameter_name: str
    semantic_axes: str | None
    basecase_read_mode: str | None
    basecase_header_row: int | None
    basecase_data_start_row: int | None
    basecase_column_roles: str | None
    basecase_row_filter: str | None
    basecase_year_row: int | None
    basecase_month_row: int | None
    basecase_period_row: int | None
    basecase_value_start_col: str | None
    basecase_value_end_col: str | None
    basecase_stop_rule: str | None


@dataclass(frozen=True)
class MappingRule:
    event_type_l2_id: int
    dimension_key: str
    dimension_label: str
    canonical_parameter_name: str
    mapping_method: str
    comment: str | None


@dataclass(frozen=True)
class BasecaseProfile:
    model_file: str
    workbook_path: str
    sheet_name: str
    sheet_exists: bool
    row_count: int = 0
    column_count: int = 0
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class BasecaseMatrixBlock:
    header_row: int
    start_col: int
    time_label_col: int
    time_start_col: int
    year_row: int | None
    month_row: int | None
    period_row: int | None
    axis_columns: dict[int, str]
    value_name: str | None
    section: str
    time_descriptors: dict[int, dict[str, Any]] = field(default_factory=dict)


@dataclass(frozen=True)
class FixedColumnSpec:
    header_row: int | None
    data_start_row: int
    column_roles: dict[int, str]
    value_col: int
    value_name: str
    row_filter: dict[int, str]
    stop_rule: str | None


@dataclass(frozen=True)
class MatrixTimeColumnSpec:
    header_row: int | None
    data_start_row: int
    axis_columns: dict[int, str]
    year_row: int | None
    month_row: int | None
    period_row: int | None
    value_start_col: int
    value_end_col: int | None
    value_name: str
    stop_rule: str | None


@dataclass(frozen=True)
class ParameterKnowledgeBase:
    mapping_source: str
    basecase_dir_path: str
    parameter_definitions: dict[str, ParameterDefinition]
    mapping_rules: list[MappingRule]
    basecase_profiles: dict[str, BasecaseProfile]

    def profile_for(self, model_file: str | None, model_sheet: str | None) -> BasecaseProfile | None:
        if not model_file or not model_sheet:
            return None
        return self.basecase_profiles.get(_profile_key(model_file, model_sheet))

    def definition_for(self, parameter_name: str) -> ParameterDefinition | None:
        return self.parameter_definitions.get(normalize_parameter_name(parameter_name))


class _WorkbookCache:
    def __init__(self, workbook_loader: Any) -> None:
        self._workbook_loader = workbook_loader
        self._workbooks: dict[Path, Any] = {}

    def __enter__(self) -> "_WorkbookCache":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close_all()

    def open(self, workbook_path: Path) -> Any:
        key = Path(workbook_path).resolve(strict=False)
        workbook = self._workbooks.get(key)
        if workbook is None:
            workbook = self._workbook_loader(
                key,
                read_only=True,
                data_only=True,
                keep_vba=False,
            )
            self._workbooks[key] = workbook
        return workbook

    def close_all(self) -> None:
        for workbook in self._workbooks.values():
            close = getattr(workbook, "close", None)
            if close is not None:
                close()
        self._workbooks.clear()


def get_parameter_knowledge_base(
    basecase_dir_path: str | None = None,
) -> ParameterKnowledgeBase:
    basecase_dir = _resolve_basecase_dir(basecase_dir_path)
    return _load_parameter_knowledge_base_from_db(
        str(basecase_dir),
    )


def get_parameter_knowledge_base_from_resources(
    *,
    mapping_rows: list[dict[str, Any]],
    parameter_rows: list[dict[str, Any]],
    basecase_dir_path: str | None = None,
) -> ParameterKnowledgeBase:
    basecase_dir = _resolve_basecase_dir(basecase_dir_path)
    return _build_parameter_knowledge_base_from_rows(
        mapping_rows=mapping_rows,
        parameter_rows=parameter_rows,
        mapping_source=DB_MAPPING_SOURCE,
        basecase_dir_path=str(basecase_dir),
    )


def _load_parameter_knowledge_base_from_db(
    basecase_dir_path: str,
) -> ParameterKnowledgeBase:
    mapping_rows, parameter_rows = _load_db_mapping_resources()
    return _build_parameter_knowledge_base_from_rows(
        mapping_rows=mapping_rows,
        parameter_rows=parameter_rows,
        mapping_source=DB_MAPPING_SOURCE,
        basecase_dir_path=basecase_dir_path,
    )


def _build_parameter_knowledge_base_from_rows(
    *,
    mapping_rows: list[dict[str, Any]],
    parameter_rows: list[dict[str, Any]],
    mapping_source: str,
    basecase_dir_path: str,
) -> ParameterKnowledgeBase:
    workbook_loader = _require_workbook_loader()
    mapping_rules = _mapping_rules_from_rows(
        mapping_rows,
        source_name="tmm_mi_model_param_dimension_map",
    )
    parameter_definitions = _parameter_definitions_from_rows(
        parameter_rows,
        source_name="tmm_mi_model_param_m",
    )
    with _WorkbookCache(workbook_loader) as workbook_cache:
        basecase_profiles = _load_basecase_profiles(
            workbook_cache,
            Path(basecase_dir_path),
            parameter_definitions,
        )
    return ParameterKnowledgeBase(
        mapping_source=mapping_source,
        basecase_dir_path=basecase_dir_path,
        parameter_definitions=parameter_definitions,
        mapping_rules=mapping_rules,
        basecase_profiles=basecase_profiles,
    )


def _load_db_mapping_resources() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    from apps.agents.model_parameter_agent.persistence.model_parameter_service import (
        ModelParameterService,
    )

    return ModelParameterService().load_parameter_mapping_resources()


def match_parameter_candidates(
    kb: ParameterKnowledgeBase,
    scenario_context: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    scenario = scenario_context.get("scenario") or {}
    event_type = scenario_context.get("event_type") or {}
    event_type_l2_id = _resolve_event_type_l2_id(scenario_context)
    template = scenario_context.get("dimension_template") or []
    dimension_values = _normalize_dimension_values(scenario.get("dimension_values"))
    template_labels = _template_labels_by_key(template)
    warnings: list[str] = []

    if event_type_l2_id is None:
        warnings.append(
            "scenario_group.event_type_l2_id가 없어 DB dimension-parameter 매핑을 수행하지 않았습니다.",
        )
        return [], [], warnings

    scenario_dimension_keys = set(dimension_values)
    if not scenario_dimension_keys and template_labels:
        scenario_dimension_keys = set(template_labels)
    if not scenario_dimension_keys:
        warnings.append("시나리오 dimension key가 없어 DB dimension-parameter 매핑을 수행하지 않았습니다.")
        return [], [], warnings

    event_rules = [
        rule for rule in kb.mapping_rules
        if rule.event_type_l2_id == event_type_l2_id
        and rule.dimension_key in scenario_dimension_keys
    ]

    mapped_dimension_keys = {rule.dimension_key for rule in event_rules}
    missing_dimension_keys = sorted(scenario_dimension_keys - mapped_dimension_keys)
    if missing_dimension_keys:
        warnings.append(
            "DB dimension-parameter 매핑에 없는 dimension_key가 있어 제외했습니다: "
            f"event_type_l2_id={event_type_l2_id}, dimension_keys={missing_dimension_keys}",
        )

    candidates: list[dict[str, Any]] = []
    non_inputs: list[dict[str, Any]] = []
    seen: set[str] = set()

    for rule in event_rules:
        source_key = rule.dimension_key
        source_value = dimension_values.get(source_key)
        source_label = template_labels.get(source_key, rule.dimension_label)

        canonical = normalize_parameter_name(rule.canonical_parameter_name)
        definition = kb.definition_for(canonical)
        has_model_target = bool(
            definition
            and definition.model_file
            and definition.model_sheet
            and canonical
        )
        if rule.mapping_method not in {"direct", "routing"} or not has_model_target:
            reason = rule.comment or "수급모델 input parameter 직접 대상이 아닙니다."
            if rule.mapping_method in {"direct", "routing"} and not has_model_target:
                reason = (
                    "tmm_mi_model_param_m에 parameter_name="
                    f"{canonical or '-'} target 정보가 없어 후보에서 제외했습니다. "
                    f"{reason}"
                )
            non_inputs.append({
                "source_dimension_id": source_key,
                "source_dimension_label": source_label or rule.dimension_label,
                "source_dimension_value": source_value,
                "mapping_method": rule.mapping_method,
                "reason": reason,
            })
            continue

        model_file = definition.model_file
        model_sheet = definition.model_sheet
        model_table = definition.model_table
        candidate_key = "|".join([
            str(rule.event_type_l2_id),
            _normalize_for_key(rule.dimension_key),
            _normalize_for_key(canonical),
            _normalize_for_key(model_file or ""),
            _normalize_for_key(model_sheet or ""),
        ])
        if candidate_key in seen:
            continue
        seen.add(candidate_key)

        profile = kb.profile_for(model_file, model_sheet)
        candidates.append({
            "candidate_key": candidate_key,
            "event_type_l2_id": rule.event_type_l2_id,
            "level_2_code": _clean_text(event_type.get("level_2_code")),
            "event_label": _clean_text(event_type.get("level_2_label")),
            "source_dimension_id": source_key,
            "dimension_key": rule.dimension_key,
            "source_dimension_label": source_label or rule.dimension_label,
            "source_dimension_value": source_value,
            "mapping_method": rule.mapping_method,
            "model_file": model_file,
            "model_sheet": model_sheet,
            "model_table": model_table,
            "parameter_name": definition.parameter_name,
            "canonical_parameter_name": canonical,
            "parameter_hint": definition.parameter_hint,
            "semantic_axes": definition.semantic_axes,
            "mapping_comment": rule.comment,
            "basecase_read_mode": definition.basecase_read_mode,
            "basecase_header_row": definition.basecase_header_row,
            "basecase_data_start_row": definition.basecase_data_start_row,
            "basecase_column_roles": definition.basecase_column_roles,
            "basecase_row_filter": definition.basecase_row_filter,
            "basecase_year_row": definition.basecase_year_row,
            "basecase_month_row": definition.basecase_month_row,
            "basecase_period_row": definition.basecase_period_row,
            "basecase_value_start_col": definition.basecase_value_start_col,
            "basecase_value_end_col": definition.basecase_value_end_col,
            "basecase_stop_rule": definition.basecase_stop_rule,
            "basecase_available": bool(profile and profile.sheet_exists),
        })

    if not candidates:
        warnings.append(
            "DB dimension-parameter 매핑 기준 직접 또는 라우팅 parameter 후보를 찾지 못했습니다.",
        )
    return candidates, non_inputs, warnings


def build_basecase_records(
    kb: ParameterKnowledgeBase,
    candidates: list[dict[str, Any]],
    scenario_context: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Return simple row/value records from each mapped basecase sheet.

    The records are intentionally flat enough for the LLM to reason over:
    Country/Plant/Year/Period live under ``axes`` and the actual cell value
    lives under ``value``. The mapped parameter area is scanned and every valid
    basecase value record is retained; if this becomes too large for the LLM
    context, the request should fail instead of silently sampling records.
    """

    workbook_loader = _require_workbook_loader()
    records: list[dict[str, Any]] = []
    warnings: list[str] = []
    with _WorkbookCache(workbook_loader) as workbook_cache:
        for candidate in candidates:
            profile = kb.profile_for(candidate.get("model_file"), candidate.get("model_sheet"))
            candidate_key = str(candidate.get("candidate_key") or "")
            if profile is None or not profile.sheet_exists:
                warnings.append(
                    "매핑된 basecase workbook/sheet를 찾지 못했습니다: "
                    f"candidate_key={candidate_key}",
                )
                continue
            try:
                candidate_records = _extract_basecase_records(
                    workbook_cache,
                    profile=profile,
                    candidate=candidate,
                    scenario_context=scenario_context,
                )
            except Exception as exc:
                warnings.append(
                    "basecase record 추출 중 오류가 발생했습니다: "
                    f"candidate_key={candidate_key}, error={exc}",
                )
                continue
            if not candidate_records:
                warnings.append(
                    "basecase record를 추출하지 못했습니다: "
                    f"candidate_key={candidate_key}, sheet={profile.sheet_name}",
                )
                continue
            records.extend(candidate_records)
    return records, warnings


def build_llm_prompt_packet(
    scenario_context: dict[str, Any],
    candidates: list[dict[str, Any]],
    non_inputs: list[dict[str, Any]],
    basecase_records: list[dict[str, Any]],
) -> dict[str, Any]:
    scenario = scenario_context.get("scenario") or {}
    group = scenario_context.get("scenario_group") or {}
    event = scenario_context.get("event") or {}
    event_type = scenario_context.get("event_type") or {}
    return {
        "scenario_context": {
            "scenario": scenario,
            "scenario_group": {
                key: group.get(key)
                for key in (
                    "scenario_group_id",
                    "mi_event_id",
                    "event_type_l2_id",
                    "title",
                    "summary",
                    "description",
                )
            },
            "event_type": event_type,
            "event": {
                key: event.get(key)
                for key in (
                    "mi_event_id",
                    "event_title_ko",
                    "one_line_summary",
                    "key_bullets",
                    "detail_analysis",
                    "occurred_at",
                    "tags",
                )
            },
            "dimension_template": scenario_context.get("dimension_template") or [],
        },
        "candidate_mappings": candidates,
        "non_input_items": non_inputs,
        "basecase_records": basecase_records,
    }


def normalize_parameter_name(value: Any) -> str:
    text = _clean_text(value)
    return PARAMETER_ALIASES.get(text, text)


def _mapping_rules_from_rows(
    rows: list[dict[str, Any]],
    *,
    source_name: str,
) -> list[MappingRule]:
    rules: list[MappingRule] = []
    for row_map in rows:
        if "enabled" in row_map and not _bool_from_cell(row_map.get("enabled"), default=True):
            continue
        event_type_l2_id = _int_or_none(row_map.get("event_type_l2_id"))
        dimension_key = _clean_text(row_map.get("dimension_key"))
        if event_type_l2_id is None or not dimension_key:
            continue
        parameter = _none_if_dash(row_map.get("parameter_name")) or ""
        canonical = normalize_parameter_name(
            _none_if_dash(row_map.get("canonical_parameter_name")) or parameter,
        )
        rules.append(
            MappingRule(
                event_type_l2_id=event_type_l2_id,
                dimension_key=dimension_key,
                dimension_label=_clean_text(row_map.get("dimension_label")),
                canonical_parameter_name=canonical,
                mapping_method=_normalize_mapping_method(
                    row_map.get("mapping_method"),
                ) or "unknown",
                comment=_none_if_dash(row_map.get("comment")),
            ),
        )
    if not rules:
        raise MIBaseError(
            ErrorCode.INVALID_REQUEST,
            detail=f"{source_name} active mapping rows not found",
        )
    return rules


def _parameter_definitions_from_rows(
    rows: list[dict[str, Any]],
    *,
    source_name: str,
) -> dict[str, ParameterDefinition]:
    definitions: dict[str, ParameterDefinition] = {}
    for row_map in rows:
        if "enabled" in row_map and not _bool_from_cell(row_map.get("enabled"), default=True):
            continue
        canonical = normalize_parameter_name(
            row_map.get("canonical_parameter_name") or row_map.get("parameter_name"),
        )
        if not canonical:
            continue
        if canonical in definitions:
            raise MIBaseError(
                ErrorCode.INVALID_REQUEST,
                detail=f"{source_name} duplicate parameter_name: {canonical}",
            )
        definitions[canonical] = ParameterDefinition(
            canonical_parameter_name=canonical,
            parameter_hint=_none_if_dash(row_map.get("parameter_hint")),
            model_file=_clean_text(row_map.get("model_file")),
            model_sheet=_clean_text(row_map.get("model_sheet")),
            model_table=_model_table_from_row(row_map),
            parameter_name=_clean_text(row_map.get("parameter_name")) or canonical,
            semantic_axes=_none_if_dash(row_map.get("semantic_axes")),
            basecase_read_mode=_none_if_dash(row_map.get("basecase_read_mode")),
            basecase_header_row=_int_or_none(row_map.get("basecase_header_row")),
            basecase_data_start_row=_int_or_none(row_map.get("basecase_data_start_row")),
            basecase_column_roles=_none_if_dash(row_map.get("basecase_column_roles")),
            basecase_row_filter=_none_if_dash(row_map.get("basecase_row_filter")),
            basecase_year_row=_int_or_none(row_map.get("basecase_year_row")),
            basecase_month_row=_int_or_none(row_map.get("basecase_month_row")),
            basecase_period_row=_int_or_none(row_map.get("basecase_period_row")),
            basecase_value_start_col=_none_if_dash(row_map.get("basecase_value_start_col")),
            basecase_value_end_col=_none_if_dash(row_map.get("basecase_value_end_col")),
            basecase_stop_rule=_none_if_dash(row_map.get("basecase_stop_rule")),
        )
    if not definitions:
        raise MIBaseError(
            ErrorCode.INVALID_REQUEST,
            detail=f"{source_name} active parameter rows not found",
    )
    return definitions


def _load_basecase_profiles(
    workbook_cache: _WorkbookCache,
    basecase_dir: Path,
    parameter_definitions: dict[str, ParameterDefinition],
) -> dict[str, BasecaseProfile]:
    workbook_paths = _discover_basecase_workbooks(basecase_dir)
    profile_targets = {
        _profile_key(definition.model_file, sheet): (definition.model_file, sheet)
        for definition in parameter_definitions.values()
        for sheet in _split_sheet_names(definition.model_sheet)
        if definition.model_file in MODEL_FILE_MARKERS
    }
    profiles: dict[str, BasecaseProfile] = {}
    for key, (model_file, sheet_name) in profile_targets.items():
        workbook_path = workbook_paths.get(model_file)
        if workbook_path is None:
            profiles[key] = BasecaseProfile(
                model_file=model_file,
                workbook_path="",
                sheet_name=sheet_name,
                sheet_exists=False,
                warnings=[f"{model_file} basecase workbook을 찾지 못했습니다."],
            )
            continue
        profiles[key] = _profile_basecase_sheet(
            workbook_cache,
            model_file=model_file,
            workbook_path=workbook_path,
            sheet_name=sheet_name,
        )
    return profiles


def _profile_basecase_sheet(
    workbook_cache: _WorkbookCache,
    *,
    model_file: str,
    workbook_path: Path,
    sheet_name: str,
) -> BasecaseProfile:
    wb = workbook_cache.open(workbook_path)
    actual_sheet_name = _find_sheet_name(wb.sheetnames, sheet_name)
    if actual_sheet_name is None:
        return BasecaseProfile(
            model_file=model_file,
            workbook_path=str(workbook_path),
            sheet_name=sheet_name,
            sheet_exists=False,
            warnings=[f"sheet not found: {sheet_name}"],
        )

    ws = wb[actual_sheet_name]
    return BasecaseProfile(
        model_file=model_file,
        workbook_path=str(workbook_path),
        sheet_name=actual_sheet_name,
        sheet_exists=True,
        row_count=int(ws.max_row or 0),
        column_count=int(ws.max_column or 0),
    )


def _extract_basecase_records(
    workbook_cache: _WorkbookCache,
    *,
    profile: BasecaseProfile,
    candidate: dict[str, Any],
    scenario_context: dict[str, Any],
) -> list[dict[str, Any]]:
    _ = scenario_context
    workbook_path = Path(profile.workbook_path)
    wb = workbook_cache.open(workbook_path)
    actual_sheet_name = _find_sheet_name(wb.sheetnames, profile.sheet_name)
    if actual_sheet_name is None:
        return []

    ws = wb[actual_sheet_name]
    fixed_spec = _fixed_column_spec_from_candidate(candidate)
    if fixed_spec is not None:
        return _extract_fixed_column_records(
            ws,
            profile=profile,
            candidate=candidate,
            scenario_context=scenario_context,
            spec=fixed_spec,
        )
    matrix_spec = _matrix_time_column_spec_from_candidate(candidate)
    if matrix_spec is not None:
        return _extract_matrix_time_column_records(
            ws,
            profile=profile,
            candidate=candidate,
            scenario_context=scenario_context,
            spec=matrix_spec,
        )

    early_rows: dict[int, list[Any]] = {}
    blocks: list[BasecaseMatrixBlock] | None = None
    records: list[dict[str, Any]] = []

    def consume_row(row_idx: int, values: list[Any]) -> None:
        if blocks is None:
            return
        for block in blocks:
            if row_idx <= block.header_row:
                continue
            _append_matrix_records_for_row(
                records=records,
                values=values,
                row_idx=row_idx,
                block=block,
                candidate=candidate,
                profile=profile,
            )

    for row_idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
        values = [_cell_to_json(value) for value in row]
        if row_idx <= BASECASE_HEADER_SCAN_ROWS:
            early_rows[row_idx] = values
        if row_idx == BASECASE_HEADER_SCAN_ROWS:
            blocks = _detect_basecase_matrix_blocks(early_rows)
            for buffered_idx, buffered_values in early_rows.items():
                consume_row(buffered_idx, buffered_values)
            continue
        if blocks is not None:
            consume_row(row_idx, values)

    if blocks is None:
        blocks = _detect_basecase_matrix_blocks(early_rows)
        for buffered_idx, buffered_values in early_rows.items():
            consume_row(buffered_idx, buffered_values)

    return records


def _append_matrix_records_for_row(
    *,
    records: list[dict[str, Any]],
    values: list[Any],
    row_idx: int,
    block: BasecaseMatrixBlock,
    candidate: dict[str, Any],
    profile: BasecaseProfile,
) -> None:
    static_axes = {
        axis_name: _value_at(values, col_idx)
        for col_idx, axis_name in block.axis_columns.items()
        if _is_meaningful_cell(_value_at(values, col_idx))
    }
    if not static_axes:
        return

    for col_idx, descriptor in block.time_descriptors.items():
        year = descriptor.get("Year")
        month = descriptor.get("Month")
        period = descriptor.get("Period")

        value = _value_at(values, col_idx)
        if not _is_record_value(value):
            continue

        axes = dict(static_axes)
        if _is_meaningful_cell(year):
            axes["Year"] = year
        if _is_meaningful_cell(month):
            axes["Month"] = month
        if _is_meaningful_cell(period):
            axes["Period"] = period

        records.append({
            "candidate_key": str(candidate.get("candidate_key") or ""),
            "model_file": profile.model_file,
            "sheet_name": profile.sheet_name,
            "parameter_name": str(
                candidate.get("canonical_parameter_name")
                or candidate.get("parameter_name")
                or "",
            ),
            "reference_id": f"{profile.model_file}:{profile.sheet_name}:R{row_idx}C{col_idx}",
            "axes": axes,
            "value_name": block.value_name,
            "value": value,
            "source_row": row_idx,
            "source_col": col_idx,
        })


def _extract_fixed_column_records(
    ws: Any,
    *,
    profile: BasecaseProfile,
    candidate: dict[str, Any],
    scenario_context: dict[str, Any],
    spec: FixedColumnSpec,
) -> list[dict[str, Any]]:
    _ = scenario_context
    records: list[dict[str, Any]] = []
    axis_columns = {
        col_idx: role
        for col_idx, role in spec.column_roles.items()
        if col_idx != spec.value_col
    }
    read_columns = set(spec.column_roles) | set(spec.row_filter)
    max_col = max(read_columns, default=0)
    row_iter_kwargs: dict[str, Any] = {
        "min_row": spec.data_start_row,
        "values_only": True,
    }
    max_row = int(ws.max_row or 0)
    if max_row:
        row_iter_kwargs["max_row"] = max_row
    if max_col:
        row_iter_kwargs["max_col"] = max_col

    for row_idx, row in enumerate(ws.iter_rows(**row_iter_kwargs), start=spec.data_start_row):
        row_values = [_cell_to_json(value) for value in row]
        values = {
            col_idx: _value_at(row_values, col_idx)
            for col_idx in read_columns
        }
        if _fixed_columns_should_stop(values, axis_columns, spec.stop_rule):
            break
        if not _row_matches_filter(values, spec.row_filter):
            continue

        value = values.get(spec.value_col)
        if not _is_record_value(value):
            continue

        axes = {
            axis_name: values.get(col_idx)
            for col_idx, axis_name in axis_columns.items()
            if _is_meaningful_cell(values.get(col_idx))
        }
        if not axes:
            continue

        records.append({
            "candidate_key": str(candidate.get("candidate_key") or ""),
            "model_file": profile.model_file,
            "sheet_name": profile.sheet_name,
            "parameter_name": str(
                candidate.get("canonical_parameter_name")
                or candidate.get("parameter_name")
                or "",
            ),
            "reference_id": f"{profile.model_file}:{profile.sheet_name}:R{row_idx}C{spec.value_col}",
            "axes": axes,
            "value_name": spec.value_name,
            "value": value,
            "source_row": row_idx,
            "source_col": spec.value_col,
        })

    return records


def _extract_matrix_time_column_records(
    ws: Any,
    *,
    profile: BasecaseProfile,
    candidate: dict[str, Any],
    scenario_context: dict[str, Any],
    spec: MatrixTimeColumnSpec,
) -> list[dict[str, Any]]:
    _ = scenario_context
    records: list[dict[str, Any]] = []
    sheet_max_col = int(ws.max_column or 0)
    max_col = sheet_max_col
    if spec.value_end_col is not None:
        max_col = min(sheet_max_col, spec.value_end_col) if sheet_max_col else spec.value_end_col
    time_descriptors = _build_matrix_time_descriptors(
        ws,
        value_start_col=spec.value_start_col,
        max_col=max_col,
        year_row=spec.year_row,
        month_row=spec.month_row,
        period_row=spec.period_row,
    )

    row_iter_kwargs: dict[str, Any] = {
        "min_row": spec.data_start_row,
        "values_only": True,
    }
    max_row = int(ws.max_row or 0)
    if max_row:
        row_iter_kwargs["max_row"] = max_row
    row_iter_kwargs["max_col"] = max(
        max(spec.axis_columns, default=0),
        max_col,
    )

    for row_idx, row in enumerate(ws.iter_rows(**row_iter_kwargs), start=spec.data_start_row):
        row_values = [_cell_to_json(value) for value in row]
        axis_values = {
            col_idx: _value_at(row_values, col_idx)
            for col_idx in spec.axis_columns
        }
        if _fixed_columns_should_stop(axis_values, spec.axis_columns, spec.stop_rule):
            break

        axes = {
            axis_name: axis_values.get(col_idx)
            for col_idx, axis_name in spec.axis_columns.items()
            if _is_meaningful_cell(axis_values.get(col_idx))
        }
        if not axes:
            continue

        for col_idx, descriptor in time_descriptors.items():
            year = descriptor.get("Year")

            value = _value_at(row_values, col_idx)
            if not _is_record_value(value):
                continue

            record_axes = dict(axes)
            month = descriptor.get("Month")
            period = descriptor.get("Period")
            if _is_meaningful_cell(year):
                record_axes["Year"] = year
            if _is_meaningful_cell(month):
                record_axes["Month"] = month
            if _is_meaningful_cell(period):
                record_axes["Period"] = period

            records.append({
                "candidate_key": str(candidate.get("candidate_key") or ""),
                "model_file": profile.model_file,
                "sheet_name": profile.sheet_name,
                "parameter_name": str(
                    candidate.get("canonical_parameter_name")
                    or candidate.get("parameter_name")
                    or "",
                ),
                "reference_id": f"{profile.model_file}:{profile.sheet_name}:R{row_idx}C{col_idx}",
                "axes": record_axes,
                "value_name": spec.value_name,
                "value": value,
                "source_row": row_idx,
                "source_col": col_idx,
            })

    return records


def _fixed_column_spec_from_candidate(candidate: dict[str, Any]) -> FixedColumnSpec | None:
    if _clean_text(candidate.get("basecase_read_mode")).lower() != "fixed_columns":
        return None
    roles_text = _clean_text(candidate.get("basecase_column_roles"))
    column_roles = _parse_column_roles(roles_text)
    if not column_roles:
        return None

    canonical = _normalize_for_key(
        candidate.get("canonical_parameter_name") or candidate.get("parameter_name"),
    )
    value_col: int | None = None
    for col_idx, role in column_roles.items():
        if _normalize_for_key(role) == canonical:
            value_col = col_idx
            break
    if value_col is None:
        for col_idx, role in column_roles.items():
            role_key = _normalize_for_key(role)
            if role_key not in BASECASE_AXIS_LABELS and role_key not in BASECASE_TIME_LABELS:
                value_col = col_idx
    if value_col is None:
        return None

    return FixedColumnSpec(
        header_row=_int_or_none(candidate.get("basecase_header_row")),
        data_start_row=_int_or_none(candidate.get("basecase_data_start_row")) or 1,
        column_roles=column_roles,
        value_col=value_col,
        value_name=column_roles[value_col],
        row_filter=_parse_row_filter(_clean_text(candidate.get("basecase_row_filter"))),
        stop_rule=_none_if_dash(candidate.get("basecase_stop_rule")),
    )


def basecase_value_field_name_from_candidate(candidate: dict[str, Any]) -> str:
    read_mode = _clean_text(candidate.get("basecase_read_mode")).lower()
    if read_mode == "fixed_columns":
        spec = _fixed_column_spec_from_candidate(candidate)
        if spec is not None:
            return spec.value_name
    return _clean_text(
        candidate.get("parameter_name")
        or candidate.get("canonical_parameter_name")
        or "",
    )


def basecase_slot_axis_names_from_candidate(candidate: dict[str, Any]) -> list[str]:
    read_mode = _clean_text(candidate.get("basecase_read_mode")).lower()
    if read_mode == "fixed_columns":
        spec = _fixed_column_spec_from_candidate(candidate)
        if spec is not None:
            return [
                role
                for col_idx, role in spec.column_roles.items()
                if col_idx != spec.value_col
            ]

    axes: list[str] = []
    if read_mode == "matrix_time_columns":
        spec = _matrix_time_column_spec_from_candidate(candidate)
        if spec is not None:
            axes.extend(spec.axis_columns.values())
        else:
            axes.extend(
                _parse_column_roles(
                    _clean_text(candidate.get("basecase_column_roles")),
                ).values(),
            )
        for axis_name in ("Year", "Month", "Period"):
            if axis_name not in axes:
                axes.append(axis_name)
        return axes

    value_field_key = _normalize_for_key(
        basecase_value_field_name_from_candidate(candidate),
    )
    for role_name in _parse_column_roles(
        _clean_text(candidate.get("basecase_column_roles")),
    ).values():
        if _normalize_for_key(role_name) == value_field_key:
            continue
        if role_name not in axes:
            axes.append(role_name)
    return axes


def _matrix_time_column_spec_from_candidate(
    candidate: dict[str, Any],
) -> MatrixTimeColumnSpec | None:
    if _clean_text(candidate.get("basecase_read_mode")).lower() != "matrix_time_columns":
        return None
    axis_columns = _parse_column_roles(_clean_text(candidate.get("basecase_column_roles")))
    value_start_col = _excel_column_to_index(candidate.get("basecase_value_start_col"))
    value_end_col = _excel_column_to_index(candidate.get("basecase_value_end_col"))
    if not axis_columns or value_start_col is None:
        return None
    if value_end_col is not None and value_end_col < value_start_col:
        return None

    value_name = (
        _none_if_dash(candidate.get("canonical_parameter_name"))
        or _none_if_dash(candidate.get("parameter_name"))
        or "Value"
    )
    return MatrixTimeColumnSpec(
        header_row=_int_or_none(candidate.get("basecase_header_row")),
        data_start_row=_int_or_none(candidate.get("basecase_data_start_row")) or 1,
        axis_columns=axis_columns,
        year_row=_int_or_none(candidate.get("basecase_year_row")),
        month_row=_int_or_none(candidate.get("basecase_month_row")),
        period_row=_int_or_none(candidate.get("basecase_period_row")),
        value_start_col=value_start_col,
        value_end_col=value_end_col,
        value_name=value_name,
        stop_rule=_none_if_dash(candidate.get("basecase_stop_rule")),
    )


def _build_matrix_time_descriptors(
    ws: Any,
    *,
    value_start_col: int,
    max_col: int,
    year_row: int | None,
    month_row: int | None,
    period_row: int | None,
) -> dict[int, dict[str, Any]]:
    row_indexes = {
        row_idx
        for row_idx in (year_row, month_row, period_row)
        if row_idx is not None
    }
    if not row_indexes:
        return {}

    header_rows: dict[int, list[Any]] = {}
    for row_idx, row in enumerate(
        ws.iter_rows(
            min_row=min(row_indexes),
            max_row=max(row_indexes),
            values_only=True,
        ),
        start=min(row_indexes),
    ):
        if row_idx in row_indexes:
            header_rows[row_idx] = [_cell_to_json(value) for value in row]

    descriptors: dict[int, dict[str, Any]] = {}
    max_col = max(max_col, max((len(row) for row in header_rows.values()), default=0))
    for col_idx in range(value_start_col, max_col + 1):
        descriptor = {
            "Year": _value_at(header_rows.get(year_row or -1, []), col_idx),
            "Month": _value_at(header_rows.get(month_row or -1, []), col_idx),
            "Period": _value_at(header_rows.get(period_row or -1, []), col_idx),
        }
        if any(_is_meaningful_cell(value) for value in descriptor.values()):
            descriptors[col_idx] = descriptor
    return descriptors


def _parse_column_roles(raw: str) -> dict[int, str]:
    result: dict[int, str] = {}
    for part in raw.split(","):
        if ":" not in part:
            continue
        column, role = part.split(":", 1)
        col_idx = _excel_column_to_index(column)
        role_name = _clean_text(role)
        if col_idx is not None and role_name:
            result[col_idx] = role_name
    return result


def _parse_row_filter(raw: str) -> dict[int, str]:
    result: dict[int, str] = {}
    for part in raw.split(","):
        if "=" not in part:
            continue
        column, expected = part.split("=", 1)
        col_idx = _excel_column_to_index(column)
        expected_value = _clean_text(expected)
        if col_idx is not None and expected_value:
            result[col_idx] = expected_value
    return result


def _row_matches_filter(values: dict[int, Any], row_filter: dict[int, str]) -> bool:
    if not row_filter:
        return True
    for col_idx, expected in row_filter.items():
        actual = _clean_text(values.get(col_idx))
        if actual.lower() != expected.lower():
            return False
    return True


def _excel_column_to_index(raw: Any) -> int | None:
    text = re.sub(r"[^A-Za-z]", "", _clean_text(raw)).upper()
    if not text:
        return None
    value = 0
    for char in text:
        value = value * 26 + (ord(char) - ord("A") + 1)
    return value


def _fixed_columns_should_stop(
    values: dict[int, Any],
    axis_columns: dict[int, str],
    stop_rule: str | None,
) -> bool:
    if stop_rule != "stop_when_all_key_columns_empty":
        return False
    return not any(_is_meaningful_cell(values.get(col_idx)) for col_idx in axis_columns)


def _detect_basecase_matrix_blocks(
    early_rows: dict[int, list[Any]],
) -> list[BasecaseMatrixBlock]:
    blocks: list[BasecaseMatrixBlock] = []
    time_label_columns = _time_label_columns(early_rows)
    if not time_label_columns:
        return []

    for header_row_idx, row in sorted(early_rows.items()):
        starts = [
            col_idx
            for col_idx, value in enumerate(row, start=1)
            if _normalize_for_key(value) in {"country", "fromcountry", "tocountry"}
        ]
        for index, start_col in enumerate(starts):
            next_start = starts[index + 1] if index + 1 < len(starts) else 10**9
            candidate_label_cols = [
                col_idx
                for col_idx in time_label_columns
                if start_col < col_idx < next_start
                and time_label_columns[col_idx].get("year") is not None
            ]
            if not candidate_label_cols:
                continue
            time_label_col = min(candidate_label_cols)
            time_start_col = time_label_col + 1
            axis_columns = {
                col_idx: _clean_text(_value_at(row, col_idx))
                for col_idx in range(start_col, time_label_col + 1)
                if _is_meaningful_cell(_value_at(row, col_idx))
            }
            if not axis_columns:
                continue
            label_rows = time_label_columns[time_label_col]
            section = _detect_block_section(
                early_rows,
                start_col=start_col,
                time_label_col=time_label_col,
                header_row=header_row_idx,
            )
            blocks.append(
                BasecaseMatrixBlock(
                    header_row=header_row_idx,
                    start_col=start_col,
                    time_label_col=time_label_col,
                    time_start_col=time_start_col,
                    year_row=label_rows.get("year"),
                    month_row=label_rows.get("month"),
                    period_row=label_rows.get("period"),
                    axis_columns=axis_columns,
                    value_name=_clean_text(_value_at(row, time_start_col)) or None,
                    section=section,
                    time_descriptors=_build_time_descriptors(
                        early_rows,
                        time_start_col=time_start_col,
                        year_row=label_rows.get("year"),
                        month_row=label_rows.get("month"),
                        period_row=label_rows.get("period"),
                    ),
                ),
            )

    basecase_blocks = [block for block in blocks if block.section == "basecase"]
    if basecase_blocks:
        return basecase_blocks
    if len(blocks) > 1:
        return [max(blocks, key=lambda block: block.start_col)]
    return blocks


def _build_time_descriptors(
    early_rows: dict[int, list[Any]],
    *,
    time_start_col: int,
    year_row: int | None,
    month_row: int | None,
    period_row: int | None,
) -> dict[int, dict[str, Any]]:
    descriptors: dict[int, dict[str, Any]] = {}
    max_col = max((len(row) for row in early_rows.values()), default=0)
    for col_idx in range(time_start_col, max_col + 1):
        descriptor = {
            "Year": _value_at(early_rows.get(year_row or -1, []), col_idx),
            "Month": _value_at(early_rows.get(month_row or -1, []), col_idx),
            "Period": _value_at(early_rows.get(period_row or -1, []), col_idx),
        }
        if any(_is_meaningful_cell(value) for value in descriptor.values()):
            descriptors[col_idx] = descriptor
    return descriptors


def _time_label_columns(early_rows: dict[int, list[Any]]) -> dict[int, dict[str, int]]:
    columns: dict[int, dict[str, int]] = defaultdict(dict)
    for row_idx, row in early_rows.items():
        for col_idx, value in enumerate(row, start=1):
            label = _normalize_for_key(value)
            if label in BASECASE_TIME_LABELS:
                columns[col_idx][label] = row_idx
    return dict(columns)


def _detect_block_section(
    early_rows: dict[int, list[Any]],
    *,
    start_col: int,
    time_label_col: int,
    header_row: int,
) -> str:
    for row_idx, row in early_rows.items():
        if row_idx > header_row:
            continue
        for col_idx in range(max(1, start_col - 2), min(len(row), time_label_col + 2) + 1):
            text = _clean_text(_value_at(row, col_idx)).lower()
            if "base case" in text:
                return "basecase"
            if "user input" in text:
                return "user_input"
    return "unknown"


def _value_at(values: list[Any], col_idx: int) -> Any:
    if col_idx <= 0 or col_idx > len(values):
        return None
    return values[col_idx - 1]


def _is_record_value(value: Any) -> bool:
    if not _is_meaningful_cell(value):
        return False
    if isinstance(value, str) and value.strip().lower() in BASECASE_BAD_VALUES:
        return False
    return True


def _resolve_basecase_dir(path: str | None) -> Path:
    if path:
        resolved = Path(path).expanduser()
        if not resolved.is_dir():
            raise MIBaseError(ErrorCode.INVALID_REQUEST, detail=f"Basecase directory not found: {path}")
        return resolved
    if not DEFAULT_INPUT_DIR.is_dir():
        raise MIBaseError(
            ErrorCode.INVALID_REQUEST,
            detail=f"Excel resource directory not found: {DEFAULT_INPUT_DIR}",
        )
    if DEFAULT_BASECASE_DIR.is_dir():
        return DEFAULT_BASECASE_DIR
    raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="Basecase directory not found")


def _discover_basecase_workbooks(basecase_dir: Path) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for child in basecase_dir.iterdir():
        if not child.is_file() or child.name.startswith("~$") or child.suffix.lower() != ".xlsm":
            continue
        normalized = _normalize_unicode(child.name)
        for model_file, marker in MODEL_FILE_MARKERS.items():
            if marker in normalized:
                result[model_file] = child
    return result


def _require_workbook_loader() -> Any:
    try:
        from openpyxl import load_workbook
    except ImportError as exc:
        raise MIBaseError(
            ErrorCode.INVALID_REQUEST,
            detail="openpyxl is required to read model parameter basecase Excel files",
        ) from exc
    return load_workbook


def _resolve_event_type_l2_id(scenario_context: dict[str, Any]) -> int | None:
    group = scenario_context.get("scenario_group") or {}
    event_type = scenario_context.get("event_type") or {}
    for raw in (
        group.get("event_type_l2_id"),
        event_type.get("event_type_l2_id"),
        event_type.get("id"),
    ):
        event_type_l2_id = _int_or_none(raw)
        if event_type_l2_id is not None:
            return event_type_l2_id
    return None


def _bool_from_cell(value: Any, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = _clean_text(value).lower()
    if not text:
        return default
    if text in {"true", "t", "yes", "y", "1", "사용", "사용함"}:
        return True
    if text in {"false", "f", "no", "n", "0", "미사용", "사용안함"}:
        return False
    return default


def _int_or_none(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    text = _clean_text(value)
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def _coerce_int(value: Any) -> int | None:
    return _int_or_none(value)


def _json_list_from_cell(value: Any) -> list[str]:
    text = _clean_text(value)
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return [part.strip() for part in text.split(",") if part.strip()]
    if isinstance(parsed, list):
        return [str(item) for item in parsed]
    return []


def _normalize_dimension_values(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return {str(key): value for key, value in raw.items() if str(key).strip()}
    if isinstance(raw, list):
        return {
            str(item.get("dim_key")): item.get("value")
            for item in raw
            if isinstance(item, dict) and item.get("dim_key")
        }
    return {}


def _template_labels_by_key(template: list[dict[str, Any]]) -> dict[str, str]:
    labels: dict[str, str] = {}
    for item in template:
        if not isinstance(item, dict):
            continue
        key = item.get("dim_key") or item.get("dimension_id") or item.get("id")
        if not key:
            continue
        labels[str(key)] = _clean_text(
            item.get("label") or item.get("label_ko") or item.get("description") or key,
        )
    return labels


def _normalize_mapping_method(raw: Any) -> str:
    text = _clean_text(raw).lower()
    if "직접" in text:
        return "direct"
    if "라우팅" in text or "routing" in text:
        return "routing"
    if "간접" in text:
        return "indirect"
    if "n/a" in text or text in {"na", "해당 없음"}:
        return "na"
    return text


def _split_sheet_names(raw: str) -> list[str]:
    text = _clean_text(raw)
    if " / " not in text:
        return [text]
    return [part.strip() for part in text.split("/") if part.strip()]


def _profile_key(model_file: str, sheet_name: str) -> str:
    return f"{_normalize_for_key(model_file)}::{_normalize_for_key(sheet_name)}"


def _find_sheet_name(sheetnames: list[str], requested: str) -> str | None:
    requested_key = _normalize_for_key(requested)
    for sheet_name in sheetnames:
        if _normalize_for_key(sheet_name) == requested_key:
            return sheet_name
    return None


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return _normalize_unicode(str(value)).strip()


def _none_if_dash(value: Any) -> str | None:
    text = _clean_text(value)
    if not text or text in {"-", "—"}:
        return None
    return text


def _model_table_from_row(row_map: dict[str, Any]) -> str | None:
    return (
        _none_if_dash(row_map.get("model_table"))
        or _none_if_dash(row_map.get("table_name"))
    )


def _normalize_unicode(value: str) -> str:
    return unicodedata.normalize("NFC", value)


def _normalize_for_key(value: Any) -> str:
    text = _clean_text(value).lower()
    return re.sub(r"[^0-9a-z가-힣]+", "", text)


def _cell_to_json(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, (int, float, str, bool)):
        if isinstance(value, str):
            return _normalize_unicode(value)
        return value
    return str(value)


def _is_meaningful_cell(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def to_compact_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, default=str, separators=(",", ":"))
