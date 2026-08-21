from __future__ import annotations

# Copyright (c) 2026 SK Innovation E&S.
import argparse
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from datetime import date, datetime
import hashlib
import json
import logging
from pathlib import Path
import sys
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

LOGGER = logging.getLogger("model_parameter_v4")
MODEL_PARAMETER_VERSION = "model-parameter-canonical-v4"
IMPACT_LEVER_VERSION = "model-impact-lever-canonical-v4"
CATALOG_VERSION = "v4"
MODEL_PARAMETER_CANONICAL_PATH = ROOT_DIR / "scripts/model_parameter/model-parameter-canonical-v4.json"
IMPACT_LEVER_CANONICAL_PATH = ROOT_DIR / "scripts/model_parameter/model-impact-lever-canonical-v4.json"
SNAPSHOT_PATH = ROOT_DIR / "scripts/model_parameter/snapshots/external_dev_before_model_parameter_v4_20260813.json"

EXPECTED_MASTER_COUNT = 21
EXPECTED_IMPACT_LEVER_COUNT = 16
EXPECTED_BINDING_COUNT = 20
EXPECTED_EFFECTIVE_EXECUTABLE_COUNT = 18
EXPECTED_EFFECTIVE_UNSUPPORTED_COUNT = 2
EXPECTED_EFFECTIVE_UNIQUE_PARAMETER_COUNT = 16
EXPECTED_PARAMETER_NAMES = {
    1: "CDD",
    2: "Coal Futures Price",
    3: "Gas Futures Price",
    4: "GDP",
    5: "HDD",
    6: "PMI",
    7: "PowerMix",
    8: "Temperature",
    9: "User-Adjusted Gas Demand",
    10: "ElectrificationRate",
    11: "Population",
    12: "HurricaneIntensity",
    13: "LiqProdAdjustment",
    14: "LiqUtilAdjustment",
    15: "PipelineAdjustment",
    16: "RegasAdjustment",
    17: "SupplyDisruption",
    18: "PNG Contract Volume",
    19: "RemainingUnrestrictedAmount",
    20: "ShippingCost",
    21: "VolumeCancelled",
}
EXPECTED_ACTIVE_NAMES = {
    "GDP",
    "PMI",
    "PowerMix",
    "Temperature",
    "Population",
    "User-Adjusted Gas Demand",
    "HurricaneIntensity",
    "LiqProdAdjustment",
    "LiqUtilAdjustment",
    "PipelineAdjustment",
    "RegasAdjustment",
    "SupplyDisruption",
    "PNG Contract Volume",
    "RemainingUnrestrictedAmount",
    "ShippingCost",
    "VolumeCancelled",
}
EXPECTED_INACTIVE_NAMES = {
    "CDD",
    "Coal Futures Price",
    "Gas Futures Price",
    "HDD",
    "ElectrificationRate",
}
EXPECTED_INACTIVE_BOUND_NAMES = {"CDD", "HDD"}
EXPECTED_LEVER_CODES = {
    "weather_demand",
    "power_generation_mix",
    "economic_activity",
    "direct_gas_demand",
    "upstream_production",
    "liquefaction_availability",
    "regasification_capacity",
    "natural_disaster_disruption",
    "pipeline_capacity",
    "shipping_cost",
    "route_disruption",
    "contract_volume",
    "trade_restriction",
    "inventory_condition",
    "regional_price_spread",
    "financial_market_sentiment",
}
VALID_DOMAINS = {"demand", "supply", "trade", "price_only"}
VALID_ROLES = {"primary", "alternative"}
MASTER_COLUMNS = (
    "model_param_id",
    "use_yn",
    "parameter_name",
    "parameter_hint",
    "model_file",
    "model_sheet",
    "model_table",
    "semantic_axes",
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
    "crt_usr_logn_id",
    "crt_dtm",
    "mod_usr_logn_id",
    "mod_dtm",
    "del_yn",
)
MASTER_DOMAIN_COLUMNS = (
    "use_yn",
    "parameter_name",
    "parameter_hint",
    "model_file",
    "model_sheet",
    "model_table",
    "semantic_axes",
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
    "mod_usr_logn_id",
    "del_yn",
)
MASTER_STABLE_COLUMNS = tuple(column for column in MASTER_COLUMNS if column != "mod_dtm")
MASTER_CREATION_COLUMNS = ("model_param_id", "crt_usr_logn_id", "crt_dtm")

MAPPING_COLUMNS = (
    "model_param_dimension_map_id",
    "use_yn",
    "event_type_l2_id",
    "dimension_key",
    "dimension_label",
    "mapping_method",
    "model_param_id",
    "comment",
    "crt_usr_logn_id",
    "crt_dtm",
    "mod_usr_logn_id",
    "mod_dtm",
    "del_yn",
)
MAPPING_STABLE_COLUMNS = tuple(column for column in MAPPING_COLUMNS if column != "mod_dtm")

IMPACT_LEVER_COLUMNS = (
    "impact_lever_id",
    "lever_code",
    "domain",
    "label",
    "description",
    "applicability_hint",
    "parent_lever_code",
    "parameter_bindings",
    "catalog_version",
    "use_yn",
    "crt_usr_logn_id",
    "crt_dtm",
    "mod_usr_logn_id",
    "mod_dtm",
    "del_yn",
)
IMPACT_LEVER_STABLE_COLUMNS = tuple(column for column in IMPACT_LEVER_COLUMNS if column != "mod_dtm")
IMPACT_LEVER_CREATION_COLUMNS = (
    "impact_lever_id",
    "lever_code",
    "crt_usr_logn_id",
    "crt_dtm",
)

MASTER_UPDATE = text(
    """
    UPDATE tmm_mi_model_param_m
       SET use_yn = :use_yn,
           parameter_name = :parameter_name,
           parameter_hint = :parameter_hint,
           model_file = :model_file,
           model_sheet = :model_sheet,
           model_table = :model_table,
           semantic_axes = :semantic_axes,
           basecase_read_mode = :basecase_read_mode,
           basecase_header_row = :basecase_header_row,
           basecase_data_start_row = :basecase_data_start_row,
           basecase_column_roles = :basecase_column_roles,
           basecase_row_filter = :basecase_row_filter,
           basecase_year_row = :basecase_year_row,
           basecase_month_row = :basecase_month_row,
           basecase_period_row = :basecase_period_row,
           basecase_value_start_col = :basecase_value_start_col,
           basecase_value_end_col = :basecase_value_end_col,
           basecase_stop_rule = :basecase_stop_rule,
           mod_usr_logn_id = :mod_usr_logn_id,
           mod_dtm = CURRENT_TIMESTAMP(6),
           del_yn = :del_yn
     WHERE model_param_id = :model_param_id
       AND parameter_name = :parameter_name
    """,
)
IMPACT_LEVER_UPDATE = text(
    """
    UPDATE tmm_mi_model_impact_lever_m
       SET domain = :domain,
           label = :label,
           description = :description,
           applicability_hint = :applicability_hint,
           parent_lever_code = :parent_lever_code,
           parameter_bindings = :parameter_bindings,
           catalog_version = :catalog_version,
           use_yn = :use_yn,
           mod_usr_logn_id = :mod_usr_logn_id,
           mod_dtm = CURRENT_TIMESTAMP(6),
           del_yn = :del_yn
     WHERE impact_lever_id = :impact_lever_id
       AND lever_code = :lever_code
    """,
)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate and atomically apply the Model Parameter v4 master and Impact Lever v4 catalog. "
            "The default is a transactional dry-run that always rolls back."
        ),
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--apply",
        action="store_true",
        help="Commit the verified master and Impact Lever update. Without this flag, roll back.",
    )
    mode.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate the canonical JSON and snapshot without opening a database connection.",
    )
    parser.add_argument(
        "--model-parameter-canonical",
        type=Path,
        default=MODEL_PARAMETER_CANONICAL_PATH,
    )
    parser.add_argument(
        "--impact-lever-canonical",
        type=Path,
        default=IMPACT_LEVER_CANONICAL_PATH,
    )
    parser.add_argument("--snapshot", type=Path, default=SNAPSHOT_PATH)
    return parser.parse_args(argv)


def _load_json(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        message = f"JSON root must be an object: {path}"
        raise TypeError(message)
    return document


def _rows(document: Mapping[str, Any], key: str) -> list[dict[str, Any]]:
    value = document.get(key)
    if not isinstance(value, list) or not all(isinstance(row, dict) for row in value):
        message = f"{key} must be an array of objects"
        raise RuntimeError(message)
    return [dict(row) for row in value]


def _decode_json_array(value: object, *, label: str) -> list[dict[str, Any]]:
    decoded = json.loads(value) if isinstance(value, str) else value
    if not isinstance(decoded, list) or not all(isinstance(item, dict) for item in decoded):
        message = f"{label} must be a JSON array of objects"
        raise RuntimeError(message)
    return [dict(item) for item in decoded]


def _normalize(value: Any, *, column: str | None = None) -> Any:  # noqa: ANN401
    if column == "parameter_bindings":
        return json.dumps(
            _decode_json_array(value, label="parameter_bindings"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    if isinstance(value, date | datetime):
        return value.isoformat()
    return value


def _projection(
    row: Mapping[str, Any],
    columns: Iterable[str],
) -> tuple[Any, ...]:
    return tuple(_normalize(row.get(column), column=column) for column in columns)


def _by_id(
    rows: Iterable[Mapping[str, Any]],
    id_column: str,
) -> dict[int, dict[str, Any]]:
    indexed: dict[int, dict[str, Any]] = {}
    for source in rows:
        raw_id = source.get(id_column)
        if raw_id is None:
            continue
        row_id = int(raw_id)
        if row_id in indexed:
            message = f"duplicate {id_column}: {row_id}"
            raise RuntimeError(message)
        indexed[row_id] = dict(source)
    return indexed


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _semantic_digest(rows: list[dict[str, Any]]) -> str:
    payload = json.dumps(
        rows,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _database_digest(
    master_rows: list[dict[str, Any]],
    mapping_rows: list[dict[str, Any]],
    lever_rows: list[dict[str, Any]],
) -> str:
    payload = {
        "master": [
            {column: _normalize(row.get(column), column=column) for column in MASTER_COLUMNS} for row in master_rows
        ],
        "mappings": [
            {column: _normalize(row.get(column), column=column) for column in MAPPING_COLUMNS} for row in mapping_rows
        ],
        "impact_levers": [
            {column: _normalize(row.get(column), column=column) for column in IMPACT_LEVER_COLUMNS}
            for row in lever_rows
        ],
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_snapshot_provenance(snapshot: Mapping[str, Any]) -> None:  # noqa: C901
    sources = snapshot.get("source_artifacts")
    if sources is None:
        if snapshot.get("capture_mode") != "read-only transaction with unconditional rollback":
            message = "external snapshot must come from a read-only transaction with unconditional rollback"
            raise RuntimeError(message)
        if not str(snapshot.get("captured_at_utc") or "").strip():
            message = "external snapshot captured_at_utc is required"
            raise RuntimeError(message)
        core_digest = str(snapshot.get("core_database_sha256") or "")
        if len(core_digest) != 64:
            message = "external snapshot core_database_sha256 is required"
            raise RuntimeError(message)
        return
    if not isinstance(sources, list) or not sources:
        message = "snapshot source_artifacts must be a non-empty array when present"
        raise RuntimeError(message)
    for source in sources:
        if not isinstance(source, dict):
            message = "snapshot source_artifacts items must be objects"
            raise TypeError(message)
        relative_path = source.get("path")
        expected_sha256 = source.get("sha256")
        if not isinstance(relative_path, str) or not relative_path.strip():
            message = "snapshot source artifact path is required"
            raise RuntimeError(message)
        path = (ROOT_DIR / relative_path).resolve()
        if not path.is_relative_to(ROOT_DIR) or not path.is_file():
            message = f"snapshot source artifact is unavailable: {relative_path}"
            raise RuntimeError(message)
        if expected_sha256 != _sha256(path):
            message = f"snapshot source artifact checksum mismatch: {relative_path}"
            raise RuntimeError(message)


def _validate_generated_from(
    document: Mapping[str, Any],
    *,
    expected_version: str,
    snapshot_path: Path,
) -> None:
    if document.get("canonical_version") != expected_version:
        message = f"unexpected canonical_version: {document.get('canonical_version')!r}"
        raise RuntimeError(message)
    if document.get("audit_user") != expected_version:
        message = f"unexpected audit_user: {document.get('audit_user')!r}"
        raise RuntimeError(message)
    declared_snapshot = document.get("generated_from_snapshot")
    if not isinstance(declared_snapshot, str) or (ROOT_DIR / declared_snapshot).resolve() != snapshot_path.resolve():
        message = f"{expected_version} does not identify the selected snapshot"
        raise RuntimeError(message)
    if document.get("snapshot_sha256") != _sha256(snapshot_path):
        message = f"{expected_version} snapshot_sha256 mismatch"
        raise RuntimeError(message)
    generated_from = document.get("generated_from_canonical")
    source_sha256 = document.get("source_canonical_sha256")
    if not isinstance(generated_from, str) or not generated_from.strip():
        message = f"{expected_version} generated_from_canonical is required"
        raise RuntimeError(message)
    source_path = (ROOT_DIR / generated_from).resolve()
    if not source_path.is_relative_to(ROOT_DIR) or not source_path.is_file():
        message = f"{expected_version} source canonical is unavailable"
        raise RuntimeError(message)
    if source_sha256 != _sha256(source_path):
        message = f"{expected_version} source canonical checksum mismatch"
        raise RuntimeError(message)


def _mapping_index(rows: Iterable[Mapping[str, Any]]) -> dict[int, dict[str, Any]]:
    indexed: dict[int, dict[str, Any]] = {}
    for source in rows:
        raw_id = source.get("model_param_dimension_map_id")
        if raw_id is None:
            message = "AS-IS legacy mapping must have a primary key"
            raise RuntimeError(message)
        row_id = int(raw_id)
        if row_id in indexed:
            message = f"duplicate dimension mapping identity: {row_id}"
            raise RuntimeError(message)
        indexed[row_id] = dict(source)
    return indexed


def _mapping_projection(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return _projection(row, MAPPING_COLUMNS)


def _assert_mapping_unchanged(
    actual_rows: list[dict[str, Any]],
    expected_rows: list[dict[str, Any]],
) -> None:
    if not expected_rows or len(actual_rows) != len(expected_rows):
        message = (
            "legacy dimension mapping must match the AS-IS snapshot: "
            f"actual={len(actual_rows)}, expected={len(expected_rows)}"
        )
        raise RuntimeError(message)
    actual = _mapping_index(actual_rows)
    expected = _mapping_index(expected_rows)
    if set(actual) != set(expected):
        message = "legacy dimension mapping identities changed"
        raise RuntimeError(message)
    for key in sorted(actual):
        if _mapping_projection(actual[key]) != _mapping_projection(expected[key]):
            message = f"legacy dimension mapping changed from AS-IS snapshot: identity={key}"
            raise RuntimeError(message)


def _assert_parent_graph(rows: list[dict[str, Any]]) -> None:
    parent_by_code = {
        str(row["lever_code"]): (str(row["parent_lever_code"]) if row.get("parent_lever_code") is not None else None)
        for row in rows
    }
    for code, parent in parent_by_code.items():
        if parent is not None and parent not in parent_by_code:
            message = f"orphan parent Lever: lever_code={code}, parent={parent}"
            raise RuntimeError(message)
        seen = {code}
        cursor = parent
        while cursor is not None:
            if cursor in seen:
                message = f"Impact Lever parent cycle: lever_code={code}"
                raise RuntimeError(message)
            seen.add(cursor)
            cursor = parent_by_code[cursor]


def _binding_counts(  # noqa: C901
    master_rows: list[dict[str, Any]],
    lever_rows: list[dict[str, Any]],
) -> tuple[int, int, int, set[str], set[str]]:
    master_by_name = {str(row["parameter_name"]): row for row in master_rows}
    binding_count = 0
    effective_count = 0
    unsupported_count = 0
    effective_names: set[str] = set()
    inactive_bound_names: set[str] = set()
    for lever in lever_rows:
        lever_code = str(lever["lever_code"])
        bindings = _decode_json_array(
            lever.get("parameter_bindings"),
            label=f"{lever_code}.parameter_bindings",
        )
        if lever.get("domain") == "price_only" and bindings:
            message = f"price_only Lever has parameter bindings: lever_code={lever_code}"
            raise RuntimeError(message)
        seen_names: set[str] = set()
        for binding in bindings:
            if set(binding) != {"parameter_name", "role", "applicability", "support_status"}:
                message = f"unexpected raw binding schema: lever_code={lever_code}, binding={binding!r}"
                raise RuntimeError(message)
            parameter_name = str(binding["parameter_name"])
            if parameter_name in seen_names:
                message = f"duplicate parameter binding: lever_code={lever_code}, name={parameter_name}"
                raise RuntimeError(message)
            seen_names.add(parameter_name)
            parameter = master_by_name.get(parameter_name)
            if parameter is None or parameter.get("del_yn") != "N":
                message = f"unknown/deleted parameter binding: lever_code={lever_code}, name={parameter_name}"
                raise RuntimeError(message)
            if binding.get("role") not in VALID_ROLES:
                message = f"invalid binding role: lever_code={lever_code}, name={parameter_name}"
                raise RuntimeError(message)
            if not str(binding.get("applicability") or "").strip():
                message = f"empty binding applicability: lever_code={lever_code}, name={parameter_name}"
                raise RuntimeError(message)
            if binding.get("support_status") != "executable":
                message = f"v4 raw binding must preserve catalog capability: lever_code={lever_code}"
                raise RuntimeError(message)
            binding_count += 1
            if parameter.get("use_yn") == "Y":
                effective_count += 1
                effective_names.add(parameter_name)
            else:
                unsupported_count += 1
                inactive_bound_names.add(parameter_name)
    return binding_count, effective_count, unsupported_count, effective_names, inactive_bound_names


def _hydrated_catalog_checksum(
    master_rows: list[dict[str, Any]],
    lever_rows: list[dict[str, Any]],
) -> str:
    active_names = {
        str(row["parameter_name"]) for row in master_rows if row.get("use_yn") == "Y" and row.get("del_yn") == "N"
    }
    payload: list[dict[str, Any]] = []
    for lever in sorted(lever_rows, key=lambda row: (str(row["domain"]), str(row["lever_code"]))):
        bindings: list[dict[str, Any]] = []
        for raw_binding in _decode_json_array(
            lever.get("parameter_bindings"),
            label=f"{lever.get('lever_code')}.parameter_bindings",
        ):
            binding = dict(raw_binding)
            parameter_name = str(binding["parameter_name"])
            requested_status = str(binding.get("support_status") or "known_unsupported")
            if requested_status == "executable" and parameter_name in active_names:
                support_status = "executable"
                unsupported_reason_code = None
            elif (
                requested_status == "executable" or binding.get("unsupported_reason_code") == "INACTIVE_MODEL_PARAMETER"
            ):
                support_status = "known_unsupported"
                unsupported_reason_code = "INACTIVE_MODEL_PARAMETER"
            else:
                support_status = "known_unsupported"
                unsupported_reason_code = "CATALOG_MARKED_UNSUPPORTED"
            bindings.append(
                {
                    "parameter_name": parameter_name,
                    "role": binding.get("role") or "primary",
                    "applicability": binding.get("applicability") or "",
                    "support_status": support_status,
                    "unsupported_reason_code": unsupported_reason_code,
                },
            )
        payload.append(
            {
                "lever_code": lever["lever_code"],
                "domain": lever["domain"],
                "label": lever["label"],
                "description": lever["description"],
                "applicability_hint": lever.get("applicability_hint"),
                "parent_lever_code": lever.get("parent_lever_code"),
                "parameter_bindings": bindings,
                "catalog_version": lever["catalog_version"],
            },
        )
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_documents(  # noqa: C901
    model_parameter: Mapping[str, Any],
    impact_lever: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    *,
    snapshot_path: Path,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    _validate_generated_from(
        model_parameter,
        expected_version=MODEL_PARAMETER_VERSION,
        snapshot_path=snapshot_path,
    )
    _validate_generated_from(
        impact_lever,
        expected_version=IMPACT_LEVER_VERSION,
        snapshot_path=snapshot_path,
    )
    if impact_lever.get("catalog_version") != CATALOG_VERSION:
        message = f"unexpected catalog_version: {impact_lever.get('catalog_version')!r}"
        raise RuntimeError(message)
    if snapshot.get("snapshot_name") != "external-dev-before-model-parameter-v4-20260813":
        message = f"unexpected snapshot_name: {snapshot.get('snapshot_name')!r}"
        raise RuntimeError(message)
    _validate_snapshot_provenance(snapshot)

    canonical_master = _rows(model_parameter, "master")
    canonical_mappings = _rows(model_parameter, "dimension_mappings")
    canonical_levers = _rows(impact_lever, "impact_levers")
    snapshot_master = _rows(snapshot, "master")
    snapshot_mappings = _rows(snapshot, "dimension_mappings")
    snapshot_levers = _rows(snapshot, "impact_levers")
    snapshot_templates = _rows(snapshot, "scenario_dimension_templates")
    counts = (
        len(canonical_master),
        len(canonical_mappings),
        len(canonical_levers),
        len(snapshot_master),
        len(snapshot_mappings),
        len(snapshot_levers),
    )
    if (
        len(canonical_master) != EXPECTED_MASTER_COUNT
        or len(canonical_levers) != EXPECTED_IMPACT_LEVER_COUNT
        or len(snapshot_master) != EXPECTED_MASTER_COUNT
        or len(snapshot_levers) != EXPECTED_IMPACT_LEVER_COUNT
        or not canonical_mappings
        or len(canonical_mappings) != len(snapshot_mappings)
    ):
        message = f"canonical/snapshot row counts mismatch: {counts}"
        raise RuntimeError(message)
    declared_snapshot_counts = (
        snapshot.get("master_count"),
        snapshot.get("mapping_count"),
        snapshot.get("impact_lever_count"),
        snapshot.get("scenario_dimension_template_count"),
    )
    if declared_snapshot_counts != (
        EXPECTED_MASTER_COUNT,
        len(snapshot_mappings),
        EXPECTED_IMPACT_LEVER_COUNT,
        len(snapshot_templates),
    ):
        message = f"snapshot declared counts mismatch: {declared_snapshot_counts}"
        raise RuntimeError(message)
    declared_canonical_counts = (
        model_parameter.get("master_count"),
        model_parameter.get("mapping_count"),
    )
    if declared_canonical_counts != (EXPECTED_MASTER_COUNT, len(snapshot_mappings)):
        message = f"model parameter canonical declared counts mismatch: {declared_canonical_counts}"
        raise RuntimeError(message)
    expected_digests = snapshot.get("table_digests")
    if not isinstance(expected_digests, dict):
        message = "snapshot table_digests are required"
        raise TypeError(message)
    actual_digests = {
        "master_sha256": _semantic_digest(snapshot_master),
        "dimension_mappings_sha256": _semantic_digest(snapshot_mappings),
        "impact_levers_sha256": _semantic_digest(snapshot_levers),
        "scenario_dimension_templates_sha256": _semantic_digest(snapshot_templates),
    }
    if expected_digests != actual_digests:
        message = "snapshot table_digests mismatch"
        raise RuntimeError(message)

    canonical_identity = {int(row["model_param_id"]): str(row["parameter_name"]) for row in canonical_master}
    snapshot_identity = {int(row["model_param_id"]): str(row["parameter_name"]) for row in snapshot_master}
    if canonical_identity != EXPECTED_PARAMETER_NAMES or snapshot_identity != EXPECTED_PARAMETER_NAMES:
        message = "canonical/snapshot 21-row model parameter identity mismatch"
        raise RuntimeError(message)
    active_names = {
        str(row["parameter_name"]) for row in canonical_master if row.get("use_yn") == "Y" and row.get("del_yn") == "N"
    }
    inactive_names = {
        str(row["parameter_name"]) for row in canonical_master if row.get("use_yn") == "N" and row.get("del_yn") == "N"
    }
    if active_names != EXPECTED_ACTIVE_NAMES or inactive_names != EXPECTED_INACTIVE_NAMES:
        message = f"v4 active/inactive master set mismatch: active={sorted(active_names)}"
        raise RuntimeError(message)
    if set(model_parameter.get("active_parameter_names") or []) != EXPECTED_ACTIVE_NAMES:
        message = "model parameter canonical declared active set mismatch"
        raise RuntimeError(message)
    if set(impact_lever.get("active_parameter_names") or []) != EXPECTED_ACTIVE_NAMES:
        message = "Impact Lever canonical declared active set mismatch"
        raise RuntimeError(message)

    snapshot_master_by_id = _by_id(snapshot_master, "model_param_id")
    canonical_master_by_id = _by_id(canonical_master, "model_param_id")
    for model_param_id in sorted(EXPECTED_PARAMETER_NAMES):
        if _projection(
            snapshot_master_by_id[model_param_id],
            MASTER_CREATION_COLUMNS,
        ) != _projection(canonical_master_by_id[model_param_id], MASTER_CREATION_COLUMNS):
            message = f"canonical changed master creation audit: model_param_id={model_param_id}"
            raise RuntimeError(message)

    _assert_mapping_unchanged(canonical_mappings, snapshot_mappings)
    mapping_payload = json.dumps(
        canonical_mappings,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    mapping_sha256 = hashlib.sha256(mapping_payload.encode("utf-8")).hexdigest()
    if model_parameter.get("legacy_dimension_mapping_sha256") != mapping_sha256:
        message = "legacy dimension mapping checksum mismatch"
        raise RuntimeError(message)
    expected_counts = model_parameter.get("expected_counts")
    if not isinstance(expected_counts, dict):
        message = "model parameter canonical expected_counts are required"
        raise TypeError(message)
    actual_method_counts = Counter(str(row.get("mapping_method")) for row in canonical_mappings)
    if expected_counts.get("dimension_mappings") != len(snapshot_mappings) or expected_counts.get(
        "mapping_methods",
    ) != dict(actual_method_counts):
        message = "AS-IS legacy dimension mapping counts differ from canonical metadata"
        raise RuntimeError(message)

    canonical_lever_by_id = _by_id(canonical_levers, "impact_lever_id")
    snapshot_lever_by_id = _by_id(snapshot_levers, "impact_lever_id")
    if set(canonical_lever_by_id) != set(snapshot_lever_by_id) or set(canonical_lever_by_id) != set(range(1, 17)):
        message = "canonical/snapshot Impact Lever IDs mismatch"
        raise RuntimeError(message)
    if {str(row["lever_code"]) for row in canonical_levers} != EXPECTED_LEVER_CODES:
        message = "canonical Impact Lever codes mismatch"
        raise RuntimeError(message)
    for lever_id in sorted(canonical_lever_by_id):
        old = snapshot_lever_by_id[lever_id]
        final = canonical_lever_by_id[lever_id]
        if _projection(old, IMPACT_LEVER_CREATION_COLUMNS) != _projection(
            final,
            IMPACT_LEVER_CREATION_COLUMNS,
        ):
            message = f"canonical changed Impact Lever creation audit: impact_lever_id={lever_id}"
            raise RuntimeError(message)
        if final.get("catalog_version") != CATALOG_VERSION:
            message = f"canonical Impact Lever row is not v4: impact_lever_id={lever_id}"
            raise RuntimeError(message)

    _assert_cross_table_invariants(canonical_master, canonical_mappings, canonical_levers, snapshot_templates)
    expected_checksum = impact_lever.get("hydrated_catalog_checksum")
    actual_checksum = _hydrated_catalog_checksum(canonical_master, canonical_levers)
    if expected_checksum != actual_checksum:
        message = (
            f"canonical hydrated catalog checksum mismatch: expected={expected_checksum}, actual={actual_checksum}"
        )
        raise RuntimeError(message)
    return (
        canonical_master,
        canonical_mappings,
        canonical_levers,
        snapshot_master,
        snapshot_mappings,
        snapshot_levers,
        snapshot_templates,
    )


def _fetch_master(session: Session, *, lock: bool) -> list[dict[str, Any]]:
    suffix = " FOR UPDATE" if lock else ""
    query = (
        f"SELECT {', '.join(MASTER_COLUMNS)} FROM tmm_mi_model_param_m "  # noqa: S608
        f"ORDER BY model_param_id{suffix}"
    )
    return [dict(row) for row in session.execute(text(query)).mappings().all()]


def _fetch_mappings(session: Session, *, lock: bool) -> list[dict[str, Any]]:
    suffix = " FOR SHARE" if lock else ""
    columns = ", ".join(f"`{column}`" if column == "comment" else column for column in MAPPING_COLUMNS)
    query = (
        f"SELECT {columns} FROM tmm_mi_model_param_dimension_map "  # noqa: S608
        f"ORDER BY model_param_dimension_map_id{suffix}"
    )
    return [dict(row) for row in session.execute(text(query)).mappings().all()]


def _fetch_levers(session: Session, *, lock: bool) -> list[dict[str, Any]]:
    suffix = " FOR UPDATE" if lock else ""
    query = (
        f"SELECT {', '.join(IMPACT_LEVER_COLUMNS)} FROM tmm_mi_model_impact_lever_m "  # noqa: S608
        f"ORDER BY impact_lever_id{suffix}"
    )
    return [dict(row) for row in session.execute(text(query)).mappings().all()]


def _fetch_templates(session: Session, *, lock: bool) -> list[dict[str, Any]]:
    suffix = " FOR SHARE" if lock else ""
    query = (
        "SELECT scenario_dimension_template_id, event_type_l2_id, template_json, del_yn "  # noqa: S608
        "FROM tmm_mi_scenario_dimension_template_m "
        f"ORDER BY scenario_dimension_template_id{suffix}"
    )
    return [dict(row) for row in session.execute(text(query)).mappings().all()]


def _assert_preconditions(
    live_master: list[dict[str, Any]],
    live_mappings: list[dict[str, Any]],
    live_levers: list[dict[str, Any]],
    canonical_master: list[dict[str, Any]],
    canonical_mappings: list[dict[str, Any]],
    canonical_levers: list[dict[str, Any]],
    snapshot_master: list[dict[str, Any]],
    snapshot_mappings: list[dict[str, Any]],
    snapshot_levers: list[dict[str, Any]],
) -> None:
    if len(live_master) != EXPECTED_MASTER_COUNT or len(live_levers) != EXPECTED_IMPACT_LEVER_COUNT:
        message = (
            f"live master/Impact Lever count mismatch: master={len(live_master)}, impact_levers={len(live_levers)}"
        )
        raise RuntimeError(message)
    _assert_mapping_unchanged(live_mappings, snapshot_mappings)
    _assert_mapping_unchanged(live_mappings, canonical_mappings)

    live_master_by_id = _by_id(live_master, "model_param_id")
    old_master_by_id = _by_id(snapshot_master, "model_param_id")
    final_master_by_id = _by_id(canonical_master, "model_param_id")
    live_identity = {model_param_id: str(row["parameter_name"]) for model_param_id, row in live_master_by_id.items()}
    if live_identity != EXPECTED_PARAMETER_NAMES:
        message = f"live model parameter identity mismatch: {live_identity!r}"
        raise RuntimeError(message)
    for model_param_id in sorted(EXPECTED_PARAMETER_NAMES):
        live = live_master_by_id[model_param_id]
        old = old_master_by_id[model_param_id]
        final = final_master_by_id[model_param_id]
        if _projection(live, MASTER_CREATION_COLUMNS) != _projection(old, MASTER_CREATION_COLUMNS):
            message = f"master creation audit changed: model_param_id={model_param_id}"
            raise RuntimeError(message)
        live_state = _projection(live, MASTER_STABLE_COLUMNS)
        allowed_states = {
            _projection(old, MASTER_STABLE_COLUMNS),
            _projection(final, MASTER_STABLE_COLUMNS),
        }
        if live_state not in allowed_states:
            message = f"master row is neither pre-v4 nor canonical-v4: model_param_id={model_param_id}"
            raise RuntimeError(message)

    live_lever_by_id = _by_id(live_levers, "impact_lever_id")
    old_lever_by_id = _by_id(snapshot_levers, "impact_lever_id")
    final_lever_by_id = _by_id(canonical_levers, "impact_lever_id")
    if set(live_lever_by_id) != set(old_lever_by_id) or set(live_lever_by_id) != set(final_lever_by_id):
        message = "live/pre-v4/canonical-v4 Impact Lever IDs differ"
        raise RuntimeError(message)
    for lever_id in sorted(live_lever_by_id):
        live = live_lever_by_id[lever_id]
        old = old_lever_by_id[lever_id]
        final = final_lever_by_id[lever_id]
        if _projection(live, IMPACT_LEVER_CREATION_COLUMNS) != _projection(
            old,
            IMPACT_LEVER_CREATION_COLUMNS,
        ):
            message = f"Impact Lever creation audit changed: impact_lever_id={lever_id}"
            raise RuntimeError(message)
        live_state = _projection(live, IMPACT_LEVER_STABLE_COLUMNS)
        allowed_states = {
            _projection(old, IMPACT_LEVER_STABLE_COLUMNS),
            _projection(final, IMPACT_LEVER_STABLE_COLUMNS),
        }
        if live_state not in allowed_states:
            message = f"Impact Lever row is neither pre-v4 nor canonical-v4: impact_lever_id={lever_id}"
            raise RuntimeError(message)


def _apply_master(session: Session, canonical_master: list[dict[str, Any]]) -> None:
    for row in canonical_master:
        parameters = {column: row.get(column) for column in MASTER_DOMAIN_COLUMNS}
        parameters["model_param_id"] = int(row["model_param_id"])
        result = session.execute(MASTER_UPDATE, parameters)
        if result.rowcount != 1:
            message = f"master update affected {result.rowcount} rows: model_param_id={row['model_param_id']}"
            raise RuntimeError(message)


def _apply_levers(session: Session, canonical_levers: list[dict[str, Any]]) -> None:
    for row in canonical_levers:
        bindings = _decode_json_array(
            row.get("parameter_bindings"),
            label=f"{row.get('lever_code')}.parameter_bindings",
        )
        parameters = {
            "impact_lever_id": int(row["impact_lever_id"]),
            "lever_code": str(row["lever_code"]),
            "domain": str(row["domain"]),
            "label": str(row["label"]),
            "description": str(row["description"]),
            "applicability_hint": row.get("applicability_hint"),
            "parent_lever_code": row.get("parent_lever_code"),
            "parameter_bindings": json.dumps(
                bindings,
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            "catalog_version": CATALOG_VERSION,
            "use_yn": str(row["use_yn"]),
            "mod_usr_logn_id": IMPACT_LEVER_VERSION,
            "del_yn": str(row["del_yn"]),
        }
        result = session.execute(IMPACT_LEVER_UPDATE, parameters)
        if result.rowcount != 1:
            message = f"Impact Lever update affected {result.rowcount} rows: impact_lever_id={row['impact_lever_id']}"
            raise RuntimeError(message)


def _parse_template_json(value: object, *, event_type_l2_id: int) -> list[dict[str, Any]]:
    decoded = json.loads(value) if isinstance(value, str) else value
    if not isinstance(decoded, list) or not all(isinstance(item, dict) for item in decoded):
        message = f"invalid active scenario dimension template: event_type_l2_id={event_type_l2_id}"
        raise RuntimeError(message)
    return [dict(item) for item in decoded]


def _assert_cross_table_invariants(  # noqa: C901
    master_rows: list[dict[str, Any]],
    mapping_rows: list[dict[str, Any]],
    lever_rows: list[dict[str, Any]],
    template_rows: list[dict[str, Any]],
) -> None:
    if len(master_rows) != EXPECTED_MASTER_COUNT or len(lever_rows) != EXPECTED_IMPACT_LEVER_COUNT:
        message = (
            "final row counts mismatch: "
            f"master={len(master_rows)}, mappings={len(mapping_rows)}, impact_levers={len(lever_rows)}"
        )
        raise RuntimeError(message)
    master_by_id = _by_id(master_rows, "model_param_id")
    identity = {model_param_id: str(row["parameter_name"]) for model_param_id, row in master_by_id.items()}
    if identity != EXPECTED_PARAMETER_NAMES:
        message = "final model parameter identity mismatch"
        raise RuntimeError(message)
    active_names = {
        str(row["parameter_name"]) for row in master_rows if row.get("use_yn") == "Y" and row.get("del_yn") == "N"
    }
    if active_names != EXPECTED_ACTIVE_NAMES:
        message = f"final active parameter names mismatch: {sorted(active_names)}"
        raise RuntimeError(message)
    if any(row.get("use_yn") != "Y" or row.get("del_yn") != "N" for row in mapping_rows):
        message = "all AS-IS legacy mappings must remain active and non-deleted"
        raise RuntimeError(message)
    natural_keys = [
        (
            int(row["event_type_l2_id"]),
            str(row["dimension_key"]),
            int(row["model_param_id"]),
        )
        for row in mapping_rows
        if row.get("model_param_id") is not None
    ]
    if len(natural_keys) != len(set(natural_keys)):
        message = "duplicate non-null legacy mapping natural key"
        raise RuntimeError(message)
    for row in mapping_rows:
        raw_model_param_id = row.get("model_param_id")
        if raw_model_param_id is None:
            continue
        parameter = master_by_id.get(int(raw_model_param_id))
        if parameter is None or parameter.get("use_yn") != "Y" or parameter.get("del_yn") != "N":
            message = (
                "legacy mapping references an inactive/deleted parameter: "
                f"mapping_id={row.get('model_param_dimension_map_id')}"
            )
            raise RuntimeError(message)

    if any(
        row.get("catalog_version") != CATALOG_VERSION or row.get("use_yn") != "Y" or row.get("del_yn") != "N"
        for row in lever_rows
    ):
        message = "all 16 Impact Levers must be active, non-deleted v4 rows"
        raise RuntimeError(message)
    if any(str(row.get("domain")) not in VALID_DOMAINS for row in lever_rows):
        message = "invalid Impact Lever domain"
        raise RuntimeError(message)
    codes = [str(row["lever_code"]) for row in lever_rows]
    if set(codes) != EXPECTED_LEVER_CODES or len(codes) != len(set(codes)):
        message = "Impact Lever code set is incomplete or duplicated"
        raise RuntimeError(message)
    _assert_parent_graph(lever_rows)
    binding_count, effective_count, unsupported_count, effective_names, inactive_bound_names = _binding_counts(
        master_rows,
        lever_rows,
    )
    actual_binding_counts = (
        binding_count,
        effective_count,
        unsupported_count,
        len(effective_names),
    )
    expected_binding_counts = (
        EXPECTED_BINDING_COUNT,
        EXPECTED_EFFECTIVE_EXECUTABLE_COUNT,
        EXPECTED_EFFECTIVE_UNSUPPORTED_COUNT,
        EXPECTED_EFFECTIVE_UNIQUE_PARAMETER_COUNT,
    )
    if actual_binding_counts != expected_binding_counts:
        message = (
            f"Impact Lever binding counts mismatch: actual={actual_binding_counts}, expected={expected_binding_counts}"
        )
        raise RuntimeError(message)
    if effective_names != EXPECTED_ACTIVE_NAMES:
        message = f"active masters and executable Lever names differ: {sorted(effective_names)}"
        raise RuntimeError(message)
    if inactive_bound_names != EXPECTED_INACTIVE_BOUND_NAMES:
        message = f"inactive catalog capability names mismatch: {sorted(inactive_bound_names)}"
        raise RuntimeError(message)

    template_keys: set[tuple[int, str]] = set()
    for row in template_rows:
        if row.get("del_yn") != "N":
            continue
        event_type_l2_id = int(row["event_type_l2_id"])
        for dimension in _parse_template_json(
            row.get("template_json"),
            event_type_l2_id=event_type_l2_id,
        ):
            dimension_key = str(dimension.get("dim_key") or "").strip()
            if dimension_key:
                template_keys.add((event_type_l2_id, dimension_key))
    mapping_keys = {(int(row["event_type_l2_id"]), str(row["dimension_key"])) for row in mapping_rows}
    missing_template_keys = sorted(mapping_keys - template_keys)
    if missing_template_keys:
        message = f"legacy mapping keys missing from active scenario templates: {missing_template_keys}"
        raise RuntimeError(message)


def _assert_read_back(
    actual_master: list[dict[str, Any]],
    actual_mappings: list[dict[str, Any]],
    actual_levers: list[dict[str, Any]],
    canonical_master: list[dict[str, Any]],
    canonical_mappings: list[dict[str, Any]],
    canonical_levers: list[dict[str, Any]],
    *,
    expected_catalog_checksum: str,
) -> str:
    actual_master_by_id = _by_id(actual_master, "model_param_id")
    canonical_master_by_id = _by_id(canonical_master, "model_param_id")
    for model_param_id in sorted(EXPECTED_PARAMETER_NAMES):
        if _projection(actual_master_by_id[model_param_id], MASTER_STABLE_COLUMNS) != _projection(
            canonical_master_by_id[model_param_id],
            MASTER_STABLE_COLUMNS,
        ):
            message = f"master canonical read-back mismatch: model_param_id={model_param_id}"
            raise RuntimeError(message)
    _assert_mapping_unchanged(actual_mappings, canonical_mappings)
    actual_lever_by_id = _by_id(actual_levers, "impact_lever_id")
    canonical_lever_by_id = _by_id(canonical_levers, "impact_lever_id")
    for lever_id in sorted(canonical_lever_by_id):
        if _projection(
            actual_lever_by_id[lever_id],
            IMPACT_LEVER_STABLE_COLUMNS,
        ) != _projection(canonical_lever_by_id[lever_id], IMPACT_LEVER_STABLE_COLUMNS):
            message = f"Impact Lever canonical read-back mismatch: impact_lever_id={lever_id}"
            raise RuntimeError(message)
    actual_checksum = _hydrated_catalog_checksum(actual_master, actual_levers)
    if actual_checksum != expected_catalog_checksum:
        message = (
            "hydrated Impact Lever catalog checksum mismatch: "
            f"expected={expected_catalog_checksum}, actual={actual_checksum}"
        )
        raise RuntimeError(message)
    return actual_checksum


def _fetch_fresh_state() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    from apps.common.configs.database.sync_database.connection import get_sync_session

    session = get_sync_session()
    try:
        return (
            _fetch_master(session, lock=False),
            _fetch_mappings(session, lock=False),
            _fetch_levers(session, lock=False),
        )
    finally:
        session.close()


def _assert_digest_equal(actual: str, expected: str, *, message: str) -> None:
    if actual != expected:
        raise RuntimeError(message)


def validate_artifacts(
    *,
    model_parameter_canonical_path: Path,
    impact_lever_canonical_path: Path,
    snapshot_path: Path,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    """Validate v4 artifacts without importing application DB configuration."""
    model_parameter = _load_json(model_parameter_canonical_path)
    impact_lever = _load_json(impact_lever_canonical_path)
    snapshot = _load_json(snapshot_path)
    return _validate_documents(
        model_parameter,
        impact_lever,
        snapshot,
        snapshot_path=snapshot_path,
    )


def run(
    *,
    apply: bool,
    model_parameter_canonical_path: Path,
    impact_lever_canonical_path: Path,
    snapshot_path: Path,
) -> None:
    from apps.common.configs.database.sync_database.connection import get_sync_session

    (
        canonical_master,
        canonical_mappings,
        canonical_levers,
        snapshot_master,
        snapshot_mappings,
        snapshot_levers,
        _,
    ) = validate_artifacts(
        model_parameter_canonical_path=model_parameter_canonical_path,
        impact_lever_canonical_path=impact_lever_canonical_path,
        snapshot_path=snapshot_path,
    )
    impact_lever = _load_json(impact_lever_canonical_path)
    expected_catalog_checksum = str(impact_lever["hydrated_catalog_checksum"])

    session = get_sync_session()
    before_digest: str | None = None
    transaction_committed = False
    try:
        live_master = _fetch_master(session, lock=True)
        live_mappings = _fetch_mappings(session, lock=True)
        live_levers = _fetch_levers(session, lock=True)
        templates = _fetch_templates(session, lock=True)
        before_digest = _database_digest(live_master, live_mappings, live_levers)
        _assert_preconditions(
            live_master,
            live_mappings,
            live_levers,
            canonical_master,
            canonical_mappings,
            canonical_levers,
            snapshot_master,
            snapshot_mappings,
            snapshot_levers,
        )

        _apply_master(session, canonical_master)
        _apply_levers(session, canonical_levers)
        actual_master = _fetch_master(session, lock=True)
        actual_mappings = _fetch_mappings(session, lock=True)
        actual_levers = _fetch_levers(session, lock=True)
        _assert_cross_table_invariants(
            actual_master,
            actual_mappings,
            actual_levers,
            templates,
        )
        catalog_checksum = _assert_read_back(
            actual_master,
            actual_mappings,
            actual_levers,
            canonical_master,
            canonical_mappings,
            canonical_levers,
            expected_catalog_checksum=expected_catalog_checksum,
        )
        transactional_digest = _database_digest(actual_master, actual_mappings, actual_levers)

        if apply:
            session.commit()
            transaction_committed = True
            persisted_master, persisted_mappings, persisted_levers = _fetch_fresh_state()
            _assert_cross_table_invariants(
                persisted_master,
                persisted_mappings,
                persisted_levers,
                templates,
            )
            _assert_read_back(
                persisted_master,
                persisted_mappings,
                persisted_levers,
                canonical_master,
                canonical_mappings,
                canonical_levers,
                expected_catalog_checksum=expected_catalog_checksum,
            )
            persisted_digest = _database_digest(
                persisted_master,
                persisted_mappings,
                persisted_levers,
            )
            _assert_digest_equal(
                persisted_digest,
                transactional_digest,
                message="persisted digest differs from the verified transaction digest",
            )
            LOGGER.info(
                "Model Parameter v4 apply committed: master=%s mappings=%s impact_levers=%s "
                "catalog_checksum=%s before_digest=%s after_digest=%s",
                len(persisted_master),
                len(persisted_mappings),
                len(persisted_levers),
                catalog_checksum,
                before_digest,
                persisted_digest,
            )
        else:
            session.rollback()
            persisted_master, persisted_mappings, persisted_levers = _fetch_fresh_state()
            rollback_digest = _database_digest(
                persisted_master,
                persisted_mappings,
                persisted_levers,
            )
            _assert_digest_equal(
                rollback_digest,
                before_digest,
                message="dry-run rollback did not preserve the exact pre-transaction table state",
            )
            LOGGER.info(
                "Model Parameter v4 dry-run passed and rolled back: master=%s mappings=%s "
                "impact_levers=%s catalog_checksum=%s before_digest=%s "
                "transactional_digest=%s rollback_digest=%s",
                len(actual_master),
                len(actual_mappings),
                len(actual_levers),
                catalog_checksum,
                before_digest,
                transactional_digest,
                rollback_digest,
            )
    except Exception:
        session.rollback()
        if before_digest is not None and not transaction_committed:
            persisted_master, persisted_mappings, persisted_levers = _fetch_fresh_state()
            rollback_digest = _database_digest(
                persisted_master,
                persisted_mappings,
                persisted_levers,
            )
            _assert_digest_equal(
                rollback_digest,
                before_digest,
                message=("failed operation rollback did not preserve the exact pre-transaction table state"),
            )
            LOGGER.info(
                "Model Parameter v4 failed operation rolled back exactly: before_digest=%s rollback_digest=%s",
                before_digest,
                rollback_digest,
            )
        raise
    finally:
        session.close()


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = _parse_args(argv)
    try:
        if args.validate_only:
            validated = validate_artifacts(
                model_parameter_canonical_path=args.model_parameter_canonical.resolve(),
                impact_lever_canonical_path=args.impact_lever_canonical.resolve(),
                snapshot_path=args.snapshot.resolve(),
            )
            LOGGER.info(
                "Model Parameter v4 artifacts validated without DB access: "
                "master=%s mappings=%s impact_levers=%s snapshot_templates=%s",
                len(validated[0]),
                len(validated[1]),
                len(validated[2]),
                len(validated[6]),
            )
            return 0
        run(
            apply=bool(args.apply),
            model_parameter_canonical_path=args.model_parameter_canonical.resolve(),
            impact_lever_canonical_path=args.impact_lever_canonical.resolve(),
            snapshot_path=args.snapshot.resolve(),
        )
    except Exception:
        LOGGER.exception("Model Parameter v4 canonical operation failed")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
