from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
import json
from pathlib import Path
import re
from typing import TYPE_CHECKING, Any
import unicodedata

from apps.agents.model_parameter_agent.constants import (
    MODEL_PARAMETER_PROPOSAL_ALLOWLIST,
    PROPOSAL_SCOPE_EXCLUDED_REASON_CODE,
)
from apps.agents.model_parameter_agent.utils.proposal_capabilities import (
    EXPECTED_EXTEND7_RELEASE_ID,
    validate_v4_candidate_capability,
)
from apps.agents.model_parameter_agent.utils.runtime_cache import (
    RuntimeLruCache,
    file_signature,
    stable_digest,
)
from apps.agents.model_parameter_agent.utils.workbook_contract import (
    load_workbook_contract,
    validate_candidate_write_target,
)
from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode


if TYPE_CHECKING:
    from apps.agents.model_parameter_agent.utils.lut.catalog import LutCatalog
    from apps.agents.model_parameter_agent.utils.lut.registry import (
        ParameterSpecRegistry,
    )


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
PRESERVE_BASECASE_AXES_WITHOUT_VALUE_FIELD = "_preserve_basecase_axes_without_value"
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
PARAMETER_KNOWLEDGE_BASE_CACHE_MAX_ENTRIES = 8
BASECASE_RECORD_CACHE_MAX_ENTRIES = 32
CANDIDATE_BASECASE_CACHE_FIELDS = (
    "model_file",
    "model_sheet",
    "parameter_name",
    "canonical_parameter_name",
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
    PRESERVE_BASECASE_AXES_WITHOUT_VALUE_FIELD,
)
_PARAMETER_KB_CACHE: RuntimeLruCache[ParameterKnowledgeBase] = RuntimeLruCache(
    max_entries=PARAMETER_KNOWLEDGE_BASE_CACHE_MAX_ENTRIES,
)
_BASECASE_RECORD_CACHE: RuntimeLruCache[tuple[dict[str, Any], ...]] = RuntimeLruCache(
    max_entries=BASECASE_RECORD_CACHE_MAX_ENTRIES,
)

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
    model_param_id: int | None = None


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


@dataclass(frozen=True)
class BasecaseRuntimeCacheSummary:
    parameter_count: int
    profile_count: int
    sheet_available_count: int
    record_count: int
    warning_count: int
    warnings: tuple[str, ...] = ()


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


def _basecase_workbook_signatures(basecase_dir: Path) -> tuple[tuple[str, str, int | None, int | None], ...]:
    return tuple(
        (model_file, *signature)
        for model_file, workbook_path in sorted(_discover_basecase_workbooks(basecase_dir).items())
        for signature in (file_signature(workbook_path),)
    )


def _parameter_knowledge_base_cache_key(
    *,
    mapping_rows: list[dict[str, Any]],
    parameter_rows: list[dict[str, Any]],
    mapping_source: str,
    basecase_dir_path: str,
    allow_empty_mapping_rows: bool = False,
) -> tuple[Any, ...]:
    basecase_dir = Path(basecase_dir_path).expanduser().resolve(strict=False)
    return (
        "parameter-knowledge-base-v1",
        mapping_source,
        str(basecase_dir),
        stable_digest(mapping_rows),
        stable_digest(parameter_rows),
        allow_empty_mapping_rows,
        _basecase_workbook_signatures(basecase_dir),
    )


def _candidate_basecase_records_cache_key(
    *,
    profile: BasecaseProfile,
    candidate: dict[str, Any],
) -> tuple[Any, ...]:
    return (
        "basecase-records-v1",
        file_signature(Path(profile.workbook_path)),
        profile.sheet_name,
        stable_digest(
            {field_name: candidate.get(field_name) for field_name in CANDIDATE_BASECASE_CACHE_FIELDS},
        ),
    )


def _copy_record(record: dict[str, Any]) -> dict[str, Any]:
    copied = dict(record)
    axes = copied.get("axes")
    if isinstance(axes, dict):
        copied["axes"] = dict(axes)
    return copied


def _copy_records_for_candidate(
    records: tuple[dict[str, Any], ...],
    candidate: dict[str, Any],
) -> list[dict[str, Any]]:
    candidate_key = str(candidate.get("candidate_key") or "")
    parameter_name = str(
        candidate.get("canonical_parameter_name") or candidate.get("parameter_name") or "",
    )
    copied_records: list[dict[str, Any]] = []
    for record in records:
        copied = _copy_record(record)
        copied["candidate_key"] = candidate_key
        copied["parameter_name"] = parameter_name
        copied_records.append(copied)
    return copied_records


def clear_parameter_mapping_runtime_cache() -> None:
    _PARAMETER_KB_CACHE.clear()
    _BASECASE_RECORD_CACHE.clear()

    from apps.agents.model_parameter_agent.utils.workbook_reference import (
        clear_workbook_reference_cache,
    )

    clear_workbook_reference_cache()


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
    allow_empty_mapping_rows: bool = False,
) -> ParameterKnowledgeBase:
    basecase_dir = _resolve_basecase_dir(basecase_dir_path)
    return _build_parameter_knowledge_base_from_rows(
        mapping_rows=mapping_rows,
        parameter_rows=parameter_rows,
        mapping_source=DB_MAPPING_SOURCE,
        basecase_dir_path=str(basecase_dir),
        allow_empty_mapping_rows=allow_empty_mapping_rows,
    )


def preload_basecase_runtime_cache(
    basecase_dir_path: str | None = None,
    *,
    preload_records: bool = True,
    registry: ParameterSpecRegistry | None = None,
) -> BasecaseRuntimeCacheSummary:
    kb = get_parameter_knowledge_base(basecase_dir_path)
    candidates = _basecase_preload_candidates(kb)
    warnings = [warning for profile in kb.basecase_profiles.values() for warning in profile.warnings]
    record_count = 0

    if preload_records:
        from apps.agents.model_parameter_agent.utils.lut.runtime import (
            get_parameter_spec_registry,
        )

        active_registry = registry or get_parameter_spec_registry()
        _BASECASE_RECORD_CACHE.ensure_capacity(len(candidates))
        workbook_loader = _require_workbook_loader()
        with _WorkbookCache(workbook_loader) as workbook_cache:
            for candidate in candidates:
                profile = kb.profile_for(
                    candidate.get("model_file"),
                    candidate.get("model_sheet"),
                )
                candidate_key = str(candidate.get("candidate_key") or "")
                if profile is None or not profile.sheet_exists:
                    warnings.append(
                        f"매핑된 basecase workbook/sheet를 찾지 못했습니다: candidate_key={candidate_key}",
                    )
                    continue
                try:
                    candidate_records = _cached_extract_basecase_records(
                        workbook_cache,
                        profile=profile,
                        candidate=candidate,
                        scenario_context={},
                        registry=active_registry,
                    )
                except Exception as exc:
                    warnings.append(
                        "basecase record startup preload 중 오류가 발생했습니다: "
                        f"candidate_key={candidate_key}, error={exc}",
                    )
                    continue
                if not candidate_records:
                    warnings.append(
                        "basecase record를 startup preload하지 못했습니다: "
                        f"candidate_key={candidate_key}, sheet={profile.sheet_name}",
                    )
                    continue
                record_count += len(candidate_records)

    sheet_available_count = sum(1 for profile in kb.basecase_profiles.values() if profile.sheet_exists)
    return BasecaseRuntimeCacheSummary(
        parameter_count=len(kb.parameter_definitions),
        profile_count=len(kb.basecase_profiles),
        sheet_available_count=sheet_available_count,
        record_count=record_count,
        warning_count=len(warnings),
        warnings=tuple(warnings[:100]),
    )


def _basecase_preload_candidates(kb: ParameterKnowledgeBase) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for definition in kb.parameter_definitions.values():
        canonical = normalize_parameter_name(
            definition.canonical_parameter_name or definition.parameter_name,
        )
        candidates.append(
            {
                "candidate_key": "|".join(
                    [
                        "startup",
                        _normalize_for_key(canonical),
                        _normalize_for_key(definition.model_file),
                        _normalize_for_key(definition.model_sheet),
                    ]
                ),
                "model_file": definition.model_file,
                "model_sheet": definition.model_sheet,
                "model_table": definition.model_table,
                "parameter_name": definition.parameter_name,
                "canonical_parameter_name": canonical,
                "parameter_hint": definition.parameter_hint,
                "semantic_axes": definition.semantic_axes,
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
            }
        )
    return candidates


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
    allow_empty_mapping_rows: bool = False,
) -> ParameterKnowledgeBase:
    cache_key = _parameter_knowledge_base_cache_key(
        mapping_rows=mapping_rows,
        parameter_rows=parameter_rows,
        mapping_source=mapping_source,
        basecase_dir_path=basecase_dir_path,
        allow_empty_mapping_rows=allow_empty_mapping_rows,
    )
    return _PARAMETER_KB_CACHE.get_or_build(
        cache_key,
        builder=lambda: _build_parameter_knowledge_base_from_rows_uncached(
            mapping_rows=mapping_rows,
            parameter_rows=parameter_rows,
            mapping_source=mapping_source,
            basecase_dir_path=basecase_dir_path,
            allow_empty_mapping_rows=allow_empty_mapping_rows,
        ),
    )


def _build_parameter_knowledge_base_from_rows_uncached(
    *,
    mapping_rows: list[dict[str, Any]],
    parameter_rows: list[dict[str, Any]],
    mapping_source: str,
    basecase_dir_path: str,
    allow_empty_mapping_rows: bool = False,
) -> ParameterKnowledgeBase:
    workbook_loader = _require_workbook_loader()
    mapping_rules = _mapping_rules_from_rows(
        mapping_rows,
        source_name="tmm_mi_model_param_dimension_map",
        allow_empty=allow_empty_mapping_rows,
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


def match_parameter_candidates(  # noqa: C901
    kb: ParameterKnowledgeBase,
    scenario_context: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    scenario_group = scenario_context.get("scenario_group") or {}
    generation_strategy = str(
        scenario_group.get("generation_strategy") or "single_event_template_dimensions",
    )
    if generation_strategy == "multi_event_composite_dimensions":
        return _match_v3_parameter_candidates(kb, scenario_context)
    if (
        generation_strategy == "multi_event_model_lever_dimensions"
        and str(scenario_group.get("api_version") or "") == "v4"
    ):
        return _match_v4_parameter_candidates(kb, scenario_context)
    if generation_strategy == "multi_event_model_lever_dimensions":
        raise MIBaseError(
            ErrorCode.INVALID_REQUEST,
            detail="multi_event_model_lever_dimensions requires scenario_group.api_version=v4",
        )

    scenario = scenario_context.get("scenario") or {}
    event_type = scenario_context.get("event_type") or {}
    event_type_l2_id = _resolve_event_type_l2_id(scenario_context)
    template = scenario_context.get("dimension_template") or []
    raw_dimension_values = scenario.get("dimension_values")
    dimension_values = _normalize_dimension_values(raw_dimension_values)
    template_labels = _template_labels_by_key(template)
    warnings: list[str] = []

    if event_type_l2_id is None:
        warnings.append(
            "scenario_group.event_type_l2_id가 없어 DB dimension-parameter 매핑을 수행하지 않았습니다.",
        )
        return [], [], warnings

    scenario_dimension_keys = set(dimension_values)
    unsupported_dimension_values = raw_dimension_values is not None and not isinstance(raw_dimension_values, dict)
    if not scenario_dimension_keys and unsupported_dimension_values:
        warnings.append(
            "scenario.dimension_values가 JSON object가 아니어서 DB dimension-parameter 매핑을 수행하지 않았습니다.",
        )
        return [], [], warnings
    if not scenario_dimension_keys:
        warnings.append("시나리오 dimension key가 없어 DB dimension-parameter 매핑을 수행하지 않았습니다.")
        return [], [], warnings

    event_rules = [
        rule
        for rule in kb.mapping_rules
        if rule.event_type_l2_id == event_type_l2_id and rule.dimension_key in scenario_dimension_keys
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
        has_model_target = bool(definition and definition.model_file and definition.model_sheet and canonical)
        if rule.mapping_method not in {"direct", "routing"} or not has_model_target:
            reason = rule.comment or "수급모델 input parameter 직접 대상이 아닙니다."
            if rule.mapping_method in {"direct", "routing"} and not has_model_target:
                reason = (
                    "tmm_mi_model_param_m에 parameter_name="
                    f"{canonical or '-'} target 정보가 없어 후보에서 제외했습니다. "
                    f"{reason}"
                )
            non_inputs.append(
                {
                    "source_dimension_id": source_key,
                    "source_dimension_label": source_label or rule.dimension_label,
                    "source_dimension_value": source_value,
                    "mapping_method": rule.mapping_method,
                    "reason": reason,
                }
            )
            continue

        model_file = definition.model_file
        model_sheet = definition.model_sheet
        model_table = definition.model_table
        candidate_key = "|".join(
            [
                str(rule.event_type_l2_id),
                _normalize_for_key(rule.dimension_key),
                _normalize_for_key(canonical),
                _normalize_for_key(model_file or ""),
                _normalize_for_key(model_sheet or ""),
            ]
        )
        if candidate_key in seen:
            continue
        seen.add(candidate_key)

        profile = kb.profile_for(model_file, model_sheet)
        candidates.append(
            {
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
            }
        )

    if not candidates:
        warnings.append(
            "DB dimension-parameter 매핑 기준 직접 또는 라우팅 parameter 후보를 찾지 못했습니다.",
        )
    return candidates, non_inputs, warnings


def _v4_source_payload(
    lineage: dict[str, Any],
    lever_state: dict[str, Any],
    *,
    mapping_method: str,
    mapping_comment: str | None,
) -> dict[str, Any]:
    lever_provenance = {
        "scenario_dimension_key": lineage.get("scenario_dimension_key"),
        "scenario_dimension_value_id": lineage.get(
            "scenario_dimension_value_id",
        ),
        "source_event_ids": list(lineage.get("source_event_ids") or []),
        "source_impact_path_ids": list(
            lineage.get("source_impact_path_ids") or [],
        ),
        "source_uncertainty_ids": list(
            lineage.get("source_uncertainty_ids") or [],
        ),
        "lever_code": lever_state.get("lever_code"),
        "impact_lever_id": lever_state.get("impact_lever_id"),
        "lever_label": lever_state.get("lever_label"),
        "lever_domain": lever_state.get("lever_domain"),
        "direction": lever_state.get("direction"),
        "level": lever_state.get("level"),
        "scope": lever_state.get("scope"),
        "time_window": lever_state.get("time_window"),
        "is_primary_lever": bool(lever_state.get("is_primary_lever")),
    }
    return {
        "scenario_dimension_key": lineage.get("scenario_dimension_key"),
        "dimension_key": lineage.get("scenario_dimension_key"),
        "source_dimension_id": lineage.get("scenario_dimension_key"),
        "source_dimension_label": lineage.get("scenario_dimension_label"),
        "source_dimension_description": lineage.get(
            "scenario_dimension_description",
        ),
        "source_dimension_rationale": lineage.get(
            "scenario_dimension_rationale",
        ),
        "source_dimension_value": lineage.get("scenario_dimension_value"),
        "source_dimension_value_id": lineage.get(
            "scenario_dimension_value_id",
        ),
        "source_dimension_value_label": lineage.get(
            "scenario_dimension_value_label",
        ),
        "derivation_rationale": lineage.get("assumption_rationale"),
        "pressure_contribution": lineage.get("pressure_contribution"),
        "source_event_ids": list(lineage.get("source_event_ids") or []),
        "source_impact_path_ids": list(
            lineage.get("source_impact_path_ids") or [],
        ),
        "source_uncertainty_ids": list(
            lineage.get("source_uncertainty_ids") or [],
        ),
        "primary_lever_code": lineage.get("primary_lever_code"),
        "primary_impact_lever_id": lineage.get("primary_impact_lever_id"),
        "model_support_status": lineage.get("model_support_status"),
        "lever_code": lever_state.get("lever_code"),
        "impact_lever_id": lever_state.get("impact_lever_id"),
        "lever_label": lever_state.get("lever_label"),
        "lever_description": lever_state.get("lever_description"),
        "lever_domain": lever_state.get("lever_domain"),
        "lever_applicability_hint": lever_state.get(
            "lever_applicability_hint",
        ),
        "direction": lever_state.get("direction"),
        "level": lever_state.get("level"),
        "scope": lever_state.get("scope"),
        "time_window": lever_state.get("time_window"),
        "is_primary_lever": bool(lever_state.get("is_primary_lever")),
        "lever_provenance": [lever_provenance],
        "mapping_method": mapping_method,
        "mapping_comment": mapping_comment,
    }


def _v4_definition_fields(
    definition: ParameterDefinition,
    *,
    basecase_available: bool,
) -> dict[str, Any]:
    return {
        "model_param_id": definition.model_param_id,
        "model_file": definition.model_file,
        "model_sheet": definition.model_sheet,
        "model_table": definition.model_table,
        "parameter_name": definition.parameter_name,
        "canonical_parameter_name": definition.canonical_parameter_name,
        "parameter_hint": definition.parameter_hint,
        "semantic_axes": definition.semantic_axes,
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
        "basecase_available": basecase_available,
    }


def _v4_candidate_key(
    *,
    dimension_key: object,
    lever_code: object,
    parameter_name: object,
    model_file: object,
    model_sheet: object,
) -> str:
    return "|".join(
        [
            "v4-lever",
            _normalize_for_key(dimension_key),
            _normalize_for_key(lever_code),
            _normalize_for_key(parameter_name),
            _normalize_for_key(model_file),
            _normalize_for_key(model_sheet),
        ],
    )


def _match_v4_parameter_candidates(  # noqa: C901
    kb: ParameterKnowledgeBase,
    scenario_context: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    lineage_items = [item for item in scenario_context.get("dimension_lineage") or [] if isinstance(item, dict)]
    warnings: list[str] = []
    if not lineage_items:
        warnings.append(
            "v4 selected-value Lever lineage가 없어 model parameter 후보를 생성하지 않았습니다.",
        )
        return [], [], warnings

    candidates: list[dict[str, Any]] = []
    non_inputs: list[dict[str, Any]] = []
    seen_candidate_keys: set[str] = set()
    for lineage in lineage_items:
        for lever_state in lineage.get("lever_states") or []:
            if not isinstance(lever_state, dict):
                continue
            direction = _clean_text(lever_state.get("direction")).lower()
            domain = _clean_text(lever_state.get("lever_domain")).lower()
            raw_bindings = [
                binding for binding in lever_state.get("parameter_bindings") or [] if isinstance(binding, dict)
            ]
            common_payload = _v4_source_payload(
                lineage,
                lever_state,
                mapping_method="excluded",
                mapping_comment=None,
            )
            if direction == "unchanged":
                non_inputs.append(
                    {
                        **common_payload,
                        "mapping_method": "indirect",
                        "reason_code": "UNCHANGED_LEVER_STATE",
                        "reason": (
                            "direction=unchanged Lever state는 변화 후보가 아니라 supporting context로 사용합니다."
                        ),
                    },
                )
                continue
            if domain == "price_only":
                non_inputs.append(
                    {
                        **common_payload,
                        "reason_code": "PRICE_ONLY",
                        "reason": "price_only Lever는 수급모델 input 후보에서 제외합니다.",
                    },
                )
                continue
            if not raw_bindings:
                non_inputs.append(
                    {
                        **common_payload,
                        "reason_code": "NO_PARAMETER_BINDING",
                        "reason": "활성 Lever catalog에 model parameter binding이 없습니다.",
                    },
                )
                continue

            executable_bindings = [binding for binding in raw_bindings if binding.get("support_status") == "executable"]
            for binding in raw_bindings:
                parameter_name = normalize_parameter_name(
                    binding.get("parameter_name"),
                )
                if binding.get("support_status") != "executable":
                    non_inputs.append(
                        {
                            **common_payload,
                            "parameter_name": parameter_name or None,
                            "binding_role": binding.get("role"),
                            "binding_applicability": binding.get(
                                "applicability",
                            ),
                            "reason_code": (binding.get("unsupported_reason_code") or "CATALOG_MARKED_UNSUPPORTED"),
                            "reason": ("Lever binding이 현재 master/catalog에서 실행 가능하지 않습니다."),
                        },
                    )
                    continue

                definition = kb.definition_for(parameter_name)
                if definition is None or not definition.model_file or not definition.model_sheet:
                    non_inputs.append(
                        {
                            **common_payload,
                            "parameter_name": parameter_name or None,
                            "binding_role": binding.get("role"),
                            "binding_applicability": binding.get(
                                "applicability",
                            ),
                            "reason_code": "ACTIVE_PARAMETER_DEFINITION_MISSING",
                            "reason": ("실행 가능한 binding의 active parameter target 정의가 없습니다."),
                        },
                    )
                    continue

                mapping_method = "direct" if len(executable_bindings) == 1 else "routing"
                source_payload = _v4_source_payload(
                    lineage,
                    lever_state,
                    mapping_method=mapping_method,
                    mapping_comment=_clean_text(
                        binding.get("applicability"),
                    ),
                )
                binding_provenance = {
                    "lever_code": lever_state.get("lever_code"),
                    "impact_lever_id": lever_state.get("impact_lever_id"),
                    "parameter_name": parameter_name,
                    "role": binding.get("role") or "primary",
                    "applicability": binding.get("applicability") or "",
                    "support_status": "executable",
                }
                candidate_key = _v4_candidate_key(
                    dimension_key=lineage.get("scenario_dimension_key"),
                    lever_code=lever_state.get("lever_code"),
                    parameter_name=parameter_name,
                    model_file=definition.model_file,
                    model_sheet=definition.model_sheet,
                )
                if candidate_key in seen_candidate_keys:
                    continue
                seen_candidate_keys.add(candidate_key)
                profile = kb.profile_for(
                    definition.model_file,
                    definition.model_sheet,
                )
                candidates.append(
                    {
                        "candidate_key": candidate_key,
                        "mapping_strategy": "v4",
                        **source_payload,
                        "binding_role": binding.get("role") or "primary",
                        "binding_applicability": binding.get(
                            "applicability",
                        )
                        or "",
                        "binding_support_status": "executable",
                        "binding_provenance": [binding_provenance],
                        **_v4_definition_fields(
                            definition,
                            basecase_available=bool(
                                profile and profile.sheet_exists,
                            ),
                        ),
                    },
                )

    if not candidates:
        reason_codes = sorted(
            {str(item.get("reason_code") or "") for item in non_inputs if str(item.get("reason_code") or "")},
        )
        warnings.append(
            "v4 selected-value Lever lineage에서 실행 후보를 찾지 못했습니다: "
            + (", ".join(reason_codes) or "NO_EXECUTABLE_BINDING"),
        )
    return candidates, non_inputs, warnings


def match_v4_parameter_candidates_from_rows(
    *,
    parameter_rows: list[dict[str, Any]],
    scenario_context: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    """Run the production v4 matcher without loading Basecase workbooks.

    Callback acceptance only needs to know whether the selected Lever lineage can
    reach an active model target. Basecase availability is evaluated later by the
    graph, so this lightweight knowledge base deliberately omits profiles while
    sharing the exact candidate/exclusion predicate with graph execution.
    """
    parameter_definitions = _parameter_definitions_from_rows(
        parameter_rows,
        source_name="tmm_mi_model_param_m",
    )
    knowledge_base = ParameterKnowledgeBase(
        mapping_source=DB_MAPPING_SOURCE,
        basecase_dir_path="",
        parameter_definitions=parameter_definitions,
        mapping_rules=[],
        basecase_profiles={},
    )
    return _match_v4_parameter_candidates(knowledge_base, scenario_context)


def _v3_event_type_context(
    scenario_context: dict[str, Any],
    event_type_l2_id: int,
) -> dict[str, Any]:
    for event in scenario_context.get("events") or []:
        if not isinstance(event, dict):
            continue
        if _coerce_int(event.get("event_type_l2_id")) != event_type_l2_id:
            continue
        event_type = event.get("event_type")
        return event_type if isinstance(event_type, dict) else {}
    return {}


def _v3_source_payload(
    lineage: dict[str, Any],
    mapped_source: dict[str, Any],
    *,
    mapping_method: str,
    mapping_comment: str | None,
) -> dict[str, Any]:
    return {
        "scenario_dimension_key": lineage.get("scenario_dimension_key"),
        "dimension_key": lineage.get("scenario_dimension_key"),
        "mapping_dimension_key": mapped_source.get("mapping_dimension_key"),
        "source_dimension_id": lineage.get("scenario_dimension_key"),
        "source_dimension_label": lineage.get("scenario_dimension_label"),
        "source_dimension_description": lineage.get(
            "scenario_dimension_description",
        ),
        "source_dimension_rationale": lineage.get(
            "scenario_dimension_rationale",
        ),
        "source_dimension_value": lineage.get("scenario_dimension_value"),
        "source_dimension_value_id": lineage.get(
            "scenario_dimension_value_id",
        ),
        "source_dimension_value_label": lineage.get(
            "scenario_dimension_value_label",
        ),
        "value_description": lineage.get("value_description"),
        "derivation_rationale": lineage.get("derivation_rationale"),
        "pressure_contribution": lineage.get("pressure_contribution"),
        "event_type_l2_id": mapped_source.get("event_type_l2_id"),
        "scenario_dimension_template_id": mapped_source.get(
            "scenario_dimension_template_id",
        ),
        "source_event_ids": list(mapped_source.get("source_event_ids") or []),
        "source_refs": [dict(mapped_source.get("source_ref") or {})],
        "approved_source_projections": list(
            lineage.get("approved_source_projections") or [],
        ),
        "parameter_mapping_ready": bool(
            lineage.get("parameter_mapping_ready"),
        ),
        "is_free_value": bool(lineage.get("is_free_value")),
        "mapping_method": mapping_method,
        "mapping_comment": mapping_comment,
    }


def _v3_candidate_key(
    *,
    lineage: dict[str, Any],
    mapped_source: dict[str, Any],
    canonical_parameter_name: str,
    model_file: str,
    model_sheet: str,
) -> str:
    return "|".join(
        [
            "v3-source",
            _normalize_for_key(lineage.get("scenario_dimension_key")),
            _normalize_for_key(
                mapped_source.get("scenario_dimension_template_id"),
            ),
            _normalize_for_key(mapped_source.get("event_type_l2_id")),
            _normalize_for_key(mapped_source.get("mapping_dimension_key")),
            _normalize_for_key(canonical_parameter_name),
            _normalize_for_key(model_file),
            _normalize_for_key(model_sheet),
        ],
    )


def _match_v3_parameter_candidates(  # noqa: C901
    kb: ParameterKnowledgeBase,
    scenario_context: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    raw_lineage = scenario_context.get("dimension_lineage") or []
    lineage_items = [item for item in raw_lineage if isinstance(item, dict)]
    warnings: list[str] = []
    if not lineage_items:
        warnings.append(
            "v3 composite dimension lineage가 없어 DB dimension-parameter 매핑을 수행하지 않았습니다.",
        )
        return [], [], warnings

    candidates: list[dict[str, Any]] = []
    non_inputs: list[dict[str, Any]] = []
    seen_candidates: dict[tuple[Any, ...], dict[str, Any]] = {}
    for lineage in lineage_items:
        mapped_sources = [item for item in lineage.get("mapped_sources") or [] if isinstance(item, dict)]
        for mapped_source in mapped_sources:
            event_type_l2_id = _coerce_int(
                mapped_source.get("event_type_l2_id"),
            )
            mapping_dimension_key = _clean_text(
                mapped_source.get("mapping_dimension_key"),
            )
            if event_type_l2_id is None or not mapping_dimension_key:
                warnings.append(
                    "v3 source lineage의 event type 또는 mapping dimension이 비어 있어 제외했습니다: "
                    f"dimension={lineage.get('scenario_dimension_key')}",
                )
                continue
            source_rules = [
                rule
                for rule in kb.mapping_rules
                if rule.event_type_l2_id == event_type_l2_id and rule.dimension_key == mapping_dimension_key
            ]
            if not source_rules:
                warnings.append(
                    "v3 sourceRef에 대응하는 DB dimension-parameter 매핑이 없어 source를 제외했습니다: "
                    f"event_type_l2_id={event_type_l2_id}, "
                    f"dimension_key={mapping_dimension_key}, "
                    f"scenario_dimension={lineage.get('scenario_dimension_key')}",
                )
                continue

            event_type = _v3_event_type_context(
                scenario_context,
                event_type_l2_id,
            )
            for rule in source_rules:
                canonical = normalize_parameter_name(
                    rule.canonical_parameter_name,
                )
                definition = kb.definition_for(canonical)
                has_model_target = bool(definition and definition.model_file and definition.model_sheet and canonical)
                source_payload = _v3_source_payload(
                    lineage,
                    mapped_source,
                    mapping_method=rule.mapping_method,
                    mapping_comment=rule.comment,
                )
                if rule.mapping_method not in {"direct", "routing"} or not has_model_target:
                    reason = rule.comment or "수급모델 input parameter 직접 대상이 아닙니다."
                    if rule.mapping_method in {"direct", "routing"} and not has_model_target:
                        reason = (
                            "tmm_mi_model_param_m에 parameter_name="
                            f"{canonical or '-'} target 정보가 없어 후보에서 제외했습니다. "
                            f"{reason}"
                        )
                    non_inputs.append(
                        {
                            **source_payload,
                            "reason": reason,
                        },
                    )
                    continue

                model_file = definition.model_file
                model_sheet = definition.model_sheet
                dedupe_key = (
                    lineage.get("scenario_dimension_key"),
                    mapped_source.get("scenario_dimension_template_id"),
                    event_type_l2_id,
                    mapping_dimension_key,
                    canonical,
                    model_file,
                    model_sheet,
                    rule.mapping_method,
                )
                existing = seen_candidates.get(dedupe_key)
                if existing is not None:
                    existing["source_event_ids"] = list(
                        dict.fromkeys(
                            [
                                *(existing.get("source_event_ids") or []),
                                *(mapped_source.get("source_event_ids") or []),
                            ],
                        ),
                    )
                    continue

                profile = kb.profile_for(model_file, model_sheet)
                candidate = {
                    "candidate_key": _v3_candidate_key(
                        lineage=lineage,
                        mapped_source=mapped_source,
                        canonical_parameter_name=canonical,
                        model_file=model_file,
                        model_sheet=model_sheet,
                    ),
                    "mapping_strategy": "v3",
                    "event_type_l2_id": event_type_l2_id,
                    "level_2_code": _clean_text(event_type.get("level_2_code")),
                    "event_label": _clean_text(event_type.get("level_2_label")),
                    **source_payload,
                    "model_file": model_file,
                    "model_sheet": model_sheet,
                    "model_table": definition.model_table,
                    "parameter_name": definition.parameter_name,
                    "canonical_parameter_name": canonical,
                    "parameter_hint": definition.parameter_hint,
                    "semantic_axes": definition.semantic_axes,
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
                }
                seen_candidates[dedupe_key] = candidate
                candidates.append(candidate)

    if not candidates:
        warnings.append(
            "v3 sourceRef 역투영 결과 직접 또는 라우팅 parameter 후보를 찾지 못했습니다.",
        )
    return candidates, non_inputs, warnings


def build_basecase_records(
    kb: ParameterKnowledgeBase,
    candidates: list[dict[str, Any]],
    scenario_context: dict[str, Any],
    *,
    registry: ParameterSpecRegistry | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Return simple row/value records from each mapped basecase sheet.

    The records are intentionally flat enough for the LLM to reason over:
    Country/Plant/Year/Period live under ``axes`` and the actual cell value
    lives under ``value``. The mapped parameter area is scanned and every valid
    basecase value record is retained; if this becomes too large for the LLM
    context, the request should fail instead of silently sampling records.
    """

    if registry is None:
        from apps.agents.model_parameter_agent.utils.lut.runtime import (
            get_parameter_spec_registry,
        )

        registry = get_parameter_spec_registry()

    scenario_group = scenario_context.get("scenario_group") or {}
    if (
        str(scenario_group.get("api_version") or "") == "v4"
        and str(scenario_group.get("generation_strategy") or "") == "multi_event_model_lever_dimensions"
    ):
        from apps.agents.model_parameter_agent.utils.resource_runtime import (
            get_registered_model_parameter_resource_paths,
        )
        from apps.agents.model_parameter_agent.utils.workbook_reference import (
            extract_workbook_references,
        )

        for candidate in candidates:
            parameter_name = str(
                candidate.get("canonical_parameter_name") or candidate.get("parameter_name") or "",
            ).strip()
            registry_spec = registry.get(parameter_name)
            expected_axes = tuple(str(item) for item in candidate.get("proposal_exact_axes") or [])
            if registry_spec is None or registry_spec.key_axes != expected_axes:
                raise MIBaseError(
                    ErrorCode.INVALID_REQUEST,
                    detail=(
                        "extend7 capability and runtime exact axes differ: "
                        f"parameter={parameter_name}, capability={expected_axes}, "
                        f"runtime={registry_spec.key_axes if registry_spec is not None else None}"
                    ),
                )

        resource_paths = get_registered_model_parameter_resource_paths()
        contract = (
            resource_paths.workbook_contract
            if resource_paths is not None and resource_paths.workbook_contract is not None
            else load_workbook_contract()
        )
        bundle = extract_workbook_references(contract)
        records: list[dict[str, Any]] = []
        warnings = list(bundle.warnings)
        contract_candidates = [
            candidate
            for candidate in candidates
            if candidate.get("proposal_reference_mode") == "v4_workbook_then_lut"
        ]
        unknown_modes = [
            str(candidate.get("canonical_parameter_name") or candidate.get("parameter_name") or "")
            for candidate in candidates
            if candidate not in contract_candidates
        ]
        if unknown_modes:
            raise MIBaseError(
                ErrorCode.INVALID_REQUEST,
                detail=f"v4 proposal candidates have unknown reference modes: {sorted(unknown_modes)}",
            )
        for candidate in contract_candidates:
            parameter_contract = validate_candidate_write_target(contract, candidate)
            parameter_name = str(
                candidate.get("canonical_parameter_name") or candidate.get("parameter_name") or "",
            ).strip()
            registry_spec = registry.get(parameter_name)
            if registry_spec is None:
                raise MIBaseError(
                    ErrorCode.INVALID_REQUEST,
                    detail=f"Workbook contract parameter has no registered exact-key schema: {parameter_name}",
                )
            target = parameter_contract.write_target
            if registry_spec.key_axes != target.key_axes or registry_spec.metadata_axes != target.metadata_axes:
                raise MIBaseError(
                    ErrorCode.INVALID_REQUEST,
                    detail=(
                        "Workbook write target and LUT registry axes differ: "
                        f"parameter={parameter_name}, target_keys={target.key_axes}, "
                        f"registry_keys={registry_spec.key_axes}, "
                        f"target_metadata={target.metadata_axes}, "
                        f"registry_metadata={registry_spec.metadata_axes}"
                    ),
                )
            candidate_key = str(candidate.get("candidate_key") or "").strip()
            if not candidate_key:
                raise MIBaseError(
                    ErrorCode.INVALID_REQUEST,
                    detail=f"Workbook contract candidate_key is required: {parameter_name}",
                )
            parameter_references = bundle.records_for(parameter_name)
            records.extend(
                {
                    "candidate_key": candidate_key,
                    "parameter_name": parameter_name,
                    "reference_id": reference.reference_id,
                    "axes": {
                        **dict(reference.axes),
                        **dict(reference.metadata),
                    },
                    "value": reference.value,
                    # PowerMix is validated as a raw atomic vector by the
                    # immutable workbook reader.  Five-decimal truncation can
                    # break an otherwise valid sum-to-one vector, so retain
                    # source precision until the proposal is produced.
                    "_preserve_reference_precision": parameter_name == "PowerMix",
                    # One source train has no lifecycle label.  This source-only
                    # field is omitted without weakening any other metadata axis
                    # or the strict legacy record path.
                    **(
                        {"_allow_missing_metadata_axes": ("Life Cycle Category",)}
                        if parameter_name == "LiqUtilAdjustment"
                        else {}
                    ),
                }
                for reference in parameter_references
            )
            source_keys = {reference.canonical_key for reference in parameter_references}
            records.extend(
                {
                    "candidate_key": candidate_key,
                    "parameter_name": parameter_name,
                    "reference_id": target_slot.reference_id,
                    "axes": {
                        **dict(target_slot.axes),
                        **dict(target_slot.metadata),
                    },
                    "value": None,
                    **(
                        {"_allow_missing_metadata_axes": ("Life Cycle Category",)}
                        if parameter_name == "LiqUtilAdjustment"
                        else {}
                    ),
                }
                for target_slot in bundle.write_target_slots_for(parameter_name)
                if target_slot.canonical_key not in source_keys
            )
        return records, warnings

    return _build_legacy_basecase_records(
        kb,
        candidates,
        scenario_context,
        registry=registry,
    )


def _build_legacy_basecase_records(
    kb: ParameterKnowledgeBase,
    candidates: list[dict[str, Any]],
    scenario_context: dict[str, Any],
    *,
    registry: ParameterSpecRegistry,
) -> tuple[list[dict[str, Any]], list[str]]:
    workbook_loader = _require_workbook_loader()
    records: list[dict[str, Any]] = []
    warnings: list[str] = []
    with _WorkbookCache(workbook_loader) as workbook_cache:
        for candidate in candidates:
            profile = kb.profile_for(candidate.get("model_file"), candidate.get("model_sheet"))
            candidate_key = str(candidate.get("candidate_key") or "")
            if profile is None or not profile.sheet_exists:
                warnings.append(
                    f"매핑된 basecase workbook/sheet를 찾지 못했습니다: candidate_key={candidate_key}",
                )
                continue
            try:
                candidate_records = _cached_extract_basecase_records(
                    workbook_cache,
                    profile=profile,
                    candidate=candidate,
                    scenario_context=scenario_context,
                    registry=registry,
                )
            except Exception as exc:
                warnings.append(
                    f"basecase record 추출 중 오류가 발생했습니다: candidate_key={candidate_key}, error={exc}",
                )
                continue
            candidate_records, missing_key_axes = _filter_incomplete_registered_records(
                candidate_records,
                candidate=candidate,
                registry=registry,
            )
            if missing_key_axes:
                warnings.append(
                    "등록된 LUT exact key와 호환되지 않는 basecase record를 제외했습니다: "
                    f"candidate_key={candidate_key}, missing_key_axes={list(missing_key_axes)}; "
                    "검증된 LUT reference만 사용합니다.",
                )
            if not candidate_records:
                warnings.append(
                    f"basecase record를 추출하지 못했습니다: candidate_key={candidate_key}, sheet={profile.sheet_name}",
                )
                continue
            records.extend(candidate_records)
    return records, warnings


def build_authoritative_blocked_keys(
    candidates: list[dict[str, Any]],
    scenario_context: dict[str, Any],
    *,
    lut_catalog: LutCatalog | None = None,
) -> dict[str, frozenset[tuple[Any, ...]]]:
    """Return exact v4 source keys that must not fall back to the LUT.

    A missing or conflicting cell in the immutable authoritative workbook is a
    negative fact for that exact coordinate.  Keeping these keys separate from
    ordinary records preserves the existing ``build_basecase_records`` return
    shape while allowing the slot catalog to suppress an otherwise matching
    legacy LUT value.
    """

    scenario_group = scenario_context.get("scenario_group") or {}
    if not (
        str(scenario_group.get("api_version") or "") == "v4"
        and str(scenario_group.get("generation_strategy") or "") == "multi_event_model_lever_dimensions"
    ):
        return {}

    from apps.agents.model_parameter_agent.utils.resource_runtime import (
        get_registered_model_parameter_resource_paths,
    )
    from apps.agents.model_parameter_agent.utils.workbook_reference import (
        extract_workbook_references,
    )

    resource_paths = get_registered_model_parameter_resource_paths()
    contract = (
        resource_paths.workbook_contract
        if resource_paths is not None and resource_paths.workbook_contract is not None
        else load_workbook_contract()
    )
    bundle = extract_workbook_references(contract)
    blocked_by_candidate: dict[str, frozenset[tuple[Any, ...]]] = {}
    for candidate in candidates:
        validate_candidate_write_target(contract, candidate)
        candidate_key = str(candidate.get("candidate_key") or "").strip()
        parameter_name = str(
            candidate.get("canonical_parameter_name") or candidate.get("parameter_name") or "",
        ).strip()
        if not candidate_key:
            raise MIBaseError(
                ErrorCode.INVALID_REQUEST,
                detail=f"Workbook contract candidate_key is required: {parameter_name}",
            )
        blocked_keys = set(bundle.blocked_keys_by_parameter.get(parameter_name, frozenset()))
        target_slots = bundle.write_target_slots_for(parameter_name)
        if target_slots and lut_catalog is not None:
            writable_keys = {slot.canonical_key for slot in target_slots}
            blocked_keys.update(
                record.canonical_key
                for record in lut_catalog.records_for_parameter(parameter_name)
                if record.canonical_key not in writable_keys
            )
        blocked_by_candidate[candidate_key] = frozenset(blocked_keys)
    return blocked_by_candidate


def _filter_incomplete_registered_records(
    records: list[dict[str, Any]],
    *,
    candidate: dict[str, Any],
    registry: ParameterSpecRegistry,
) -> tuple[list[dict[str, Any]], tuple[str, ...]]:
    """Exclude workbook rows that cannot form the registered exact business key."""
    parameter_name = str(
        candidate.get("canonical_parameter_name") or candidate.get("parameter_name") or "",
    ).strip()
    spec = registry.get(parameter_name)
    if spec is None:
        return records, ()

    compatible: list[dict[str, Any]] = []
    missing_axes: set[str] = set()
    for record in records:
        raw_axes = record.get("axes")
        if not isinstance(raw_axes, dict):
            missing_axes.update(spec.key_axes)
            continue
        missing = tuple(axis_name for axis_name in spec.key_axes if axis_name not in raw_axes)
        if missing:
            missing_axes.update(missing)
            continue
        compatible.append(record)
    return compatible, tuple(axis_name for axis_name in spec.key_axes if axis_name in missing_axes)


def _cached_extract_basecase_records(
    workbook_cache: _WorkbookCache,
    *,
    profile: BasecaseProfile,
    candidate: dict[str, Any],
    scenario_context: dict[str, Any],
    registry: ParameterSpecRegistry,
) -> list[dict[str, Any]]:
    # Basecase extraction currently depends only on the workbook/profile and
    # candidate basecase mapping fields. If scenario-specific filtering is added,
    # include those fields in this cache key before reusing records across scenarios.
    _ = scenario_context
    candidate = _candidate_with_basecase_metadata_policy(candidate, registry)
    cache_key = _candidate_basecase_records_cache_key(
        profile=profile,
        candidate=candidate,
    )

    def build() -> tuple[dict[str, Any], ...]:
        records = _extract_basecase_records(
            workbook_cache,
            profile=profile,
            candidate=candidate,
            scenario_context=scenario_context,
        )
        return tuple(_copy_record(record) for record in records)

    cached_records = _BASECASE_RECORD_CACHE.get_or_build(
        cache_key,
        builder=build,
    )
    return _copy_records_for_candidate(cached_records, candidate)


def _candidate_with_basecase_metadata_policy(
    candidate: dict[str, Any],
    registry: ParameterSpecRegistry,
) -> dict[str, Any]:
    parameter_name = str(
        candidate.get("canonical_parameter_name") or candidate.get("parameter_name") or "",
    ).strip()
    spec = registry.get(parameter_name)
    return {
        **candidate,
        PRESERVE_BASECASE_AXES_WITHOUT_VALUE_FIELD: bool(
            spec is not None and spec.metadata_axes,
        ),
    }


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
    return _clean_text(value)


def is_proposal_parameter_allowed(value: Any) -> bool:
    return normalize_parameter_name(value) in MODEL_PARAMETER_PROPOSAL_ALLOWLIST


def partition_proposal_parameter_candidates(
    candidates: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split raw mapping candidates at the runtime proposal boundary."""
    allowed: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for candidate in candidates:
        parameter_name = normalize_parameter_name(
            candidate.get("canonical_parameter_name") or candidate.get("parameter_name"),
        )
        if str(candidate.get("mapping_strategy") or "").lower() == "v4":
            capability = validate_v4_candidate_capability(candidate)
            if capability is not None:
                allowed.append(
                    {
                        **candidate,
                        "proposal_capability_release_id": EXPECTED_EXTEND7_RELEASE_ID,
                        "proposal_reference_mode": capability.reference_mode,
                        "proposal_exact_axes": list(capability.exact_axes),
                        "proposal_evidence_policy": capability.evidence_policy,
                        "proposal_constraints": dict(capability.constraints),
                    },
                )
                continue
        elif parameter_name in MODEL_PARAMETER_PROPOSAL_ALLOWLIST:
            allowed.append(candidate)
            continue
        excluded.append(
            {
                **candidate,
                "reason_code": PROPOSAL_SCOPE_EXCLUDED_REASON_CODE,
                "reason": (
                    f"{parameter_name or 'unknown parameter'} is outside the runtime "
                    "model-parameter proposal allow-list."
                ),
            },
        )
    return allowed, excluded


def _mapping_rules_from_rows(
    rows: list[dict[str, Any]],
    *,
    source_name: str,
    allow_empty: bool = False,
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
                )
                or "unknown",
                comment=_none_if_dash(row_map.get("comment")),
            ),
        )
    if not rules and not allow_empty:
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
            model_param_id=_int_or_none(row_map.get("model_param_id")),
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

    value_years: set[int] = set()
    axis_only_by_year: dict[int, tuple[int, dict[str, Any]]] = {}

    def append_record(col_idx: int, descriptor: dict[str, Any], value: Any) -> None:  # noqa: ANN401
        axes = dict(static_axes)
        for axis_name in ("Year", "Month", "Period"):
            axis_value = descriptor.get(axis_name)
            if _is_meaningful_cell(axis_value):
                axes[axis_name] = axis_value
        records.append(
            {
                "candidate_key": str(candidate.get("candidate_key") or ""),
                "model_file": profile.model_file,
                "sheet_name": profile.sheet_name,
                "parameter_name": str(
                    candidate.get("canonical_parameter_name") or candidate.get("parameter_name") or "",
                ),
                "reference_id": f"{profile.model_file}:{profile.sheet_name}:R{row_idx}C{col_idx}",
                "axes": axes,
                "value_name": block.value_name,
                "value": value,
                "source_row": row_idx,
                "source_col": col_idx,
            }
        )

    for col_idx, descriptor in block.time_descriptors.items():
        value = _value_at(values, col_idx)
        time_values = _valid_basecase_time_values(descriptor)
        if not _is_record_value(value):
            if _preserves_basecase_axes_without_value(candidate) and time_values is not None:
                axis_only_by_year.setdefault(time_values[0], (col_idx, descriptor))
            continue
        if time_values is not None:
            value_years.add(time_values[0])
        append_record(col_idx, descriptor, value)

    for year, (col_idx, descriptor) in axis_only_by_year.items():
        if year not in value_years:
            append_record(col_idx, descriptor, None)


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
    axis_columns = {col_idx: role for col_idx, role in spec.column_roles.items() if col_idx != spec.value_col}
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
        values = {col_idx: _value_at(row_values, col_idx) for col_idx in read_columns}
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

        records.append(
            {
                "candidate_key": str(candidate.get("candidate_key") or ""),
                "model_file": profile.model_file,
                "sheet_name": profile.sheet_name,
                "parameter_name": str(
                    candidate.get("canonical_parameter_name") or candidate.get("parameter_name") or "",
                ),
                "reference_id": f"{profile.model_file}:{profile.sheet_name}:R{row_idx}C{spec.value_col}",
                "axes": axes,
                "value_name": spec.value_name,
                "value": value,
                "source_row": row_idx,
                "source_col": spec.value_col,
            }
        )

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
        axis_values = {col_idx: _value_at(row_values, col_idx) for col_idx in spec.axis_columns}
        if _fixed_columns_should_stop(axis_values, spec.axis_columns, spec.stop_rule):
            break

        axes = {
            axis_name: axis_values.get(col_idx)
            for col_idx, axis_name in spec.axis_columns.items()
            if _is_meaningful_cell(axis_values.get(col_idx))
        }
        if not axes:
            continue

        value_years: set[int] = set()
        axis_only_by_year: dict[int, tuple[int, dict[str, Any]]] = {}

        def append_record(col_idx: int, descriptor: dict[str, Any], value: Any) -> None:  # noqa: ANN401
            record_axes = dict(axes)
            for axis_name in ("Year", "Month", "Period"):
                axis_value = descriptor.get(axis_name)
                if _is_meaningful_cell(axis_value):
                    record_axes[axis_name] = axis_value
            records.append(
                {
                    "candidate_key": str(candidate.get("candidate_key") or ""),
                    "model_file": profile.model_file,
                    "sheet_name": profile.sheet_name,
                    "parameter_name": str(
                        candidate.get("canonical_parameter_name") or candidate.get("parameter_name") or "",
                    ),
                    "reference_id": f"{profile.model_file}:{profile.sheet_name}:R{row_idx}C{col_idx}",
                    "axes": record_axes,
                    "value_name": spec.value_name,
                    "value": value,
                    "source_row": row_idx,
                    "source_col": col_idx,
                }
            )

        for col_idx, descriptor in time_descriptors.items():
            value = _value_at(row_values, col_idx)
            time_values = _valid_basecase_time_values(descriptor)
            if not _is_record_value(value):
                if _preserves_basecase_axes_without_value(candidate) and time_values is not None:
                    axis_only_by_year.setdefault(time_values[0], (col_idx, descriptor))
                continue
            if time_values is not None:
                value_years.add(time_values[0])
            append_record(col_idx, descriptor, value)

        for year, (col_idx, descriptor) in axis_only_by_year.items():
            if year not in value_years:
                append_record(col_idx, descriptor, None)

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
        candidate.get("parameter_name") or candidate.get("canonical_parameter_name") or "",
    )


def basecase_slot_axis_names_from_candidate(candidate: dict[str, Any]) -> list[str]:
    read_mode = _clean_text(candidate.get("basecase_read_mode")).lower()
    if read_mode == "fixed_columns":
        spec = _fixed_column_spec_from_candidate(candidate)
        if spec is not None:
            return [role for col_idx, role in spec.column_roles.items() if col_idx != spec.value_col]

    axes: list[str] = []
    if read_mode == "matrix_time_columns":
        spec = _matrix_time_column_spec_from_candidate(candidate)
        if spec is not None:
            axes.extend(spec.axis_columns.values())
            configured_time_axes = {
                "Year": spec.year_row,
                "Month": spec.month_row,
                "Period": spec.period_row,
            }
        else:
            axes.extend(
                _parse_column_roles(
                    _clean_text(candidate.get("basecase_column_roles")),
                ).values(),
            )
            configured_time_axes = {
                "Year": _int_or_none(candidate.get("basecase_year_row")),
                "Month": _int_or_none(candidate.get("basecase_month_row")),
                "Period": _int_or_none(candidate.get("basecase_period_row")),
            }
        for axis_name, row_number in configured_time_axes.items():
            if row_number is not None and axis_name not in axes:
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
    row_indexes = {row_idx for row_idx in (year_row, month_row, period_row) if row_idx is not None}
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
                if start_col < col_idx < next_start and time_label_columns[col_idx].get("year") is not None
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


def _preserves_basecase_axes_without_value(candidate: dict[str, Any]) -> bool:
    return candidate.get(PRESERVE_BASECASE_AXES_WITHOUT_VALUE_FIELD) is True


def _valid_basecase_time_values(
    descriptor: dict[str, Any],
) -> tuple[int, int, int] | None:
    year = _int_or_none(descriptor.get("Year"))
    month = _int_or_none(descriptor.get("Month"))
    period = _int_or_none(descriptor.get("Period"))
    if year is None or month is None or not 1 <= month <= 12 or period is None:
        return None
    return year, month, period


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
    return {}


def _template_labels_by_key(template: list[dict[str, Any]]) -> dict[str, str]:
    labels: dict[str, str] = {}
    for item in template:
        if not isinstance(item, dict):
            continue
        key = item.get("dim_key")
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
    return _none_if_dash(row_map.get("model_table")) or _none_if_dash(row_map.get("table_name"))


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
