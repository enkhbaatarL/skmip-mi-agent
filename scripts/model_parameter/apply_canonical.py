from __future__ import annotations

# Copyright (c) 2026 SK Innovation E&S.
import argparse
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from datetime import date, datetime
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

LOGGER = logging.getLogger("model_parameter_canonical")
CANONICAL_PATH = ROOT_DIR / "scripts" / "model_parameter" / "model-parameter-canonical-v1.json"
SNAPSHOT_PATH = ROOT_DIR / "scripts" / "model_parameter" / "snapshots" / "external_dev_before_20260807.json"

EXPECTED_MASTER_COUNT = 21
EXPECTED_MAPPING_COUNT = 129
EXPECTED_METHOD_COUNTS = {
    "direct": 35,
    "routing": 6,
    "indirect": 55,
    "na": 33,
}
EXPECTED_ACTIVE_NAMES = {
    "GDP",
    "PMI",
    "PowerMix",
    "Temperature",
    "Population",
    "HurricaneIntensity",
    "LiqProdAdjustment",
    "LiqUtilAdjustment",
    "PipelineAdjustment",
    "SupplyDisruption",
}
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
RESTORED_MAPPING_IDS = frozenset({2, 5, 9, 16, 18, 23, 66, 68, 70, 96, 97, 106, 107})
BASE_MAPPING_IDS = frozenset(range(1, 129))
POPULATION_NATURAL_KEY = (21, "economic_intensity", 11)

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
    "mod_dtm",
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
MAPPING_CREATION_COLUMNS = (
    "model_param_dimension_map_id",
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
    """,
)
MAPPING_UPDATE = text(
    """
    UPDATE tmm_mi_model_param_dimension_map
       SET use_yn = :use_yn,
           event_type_l2_id = :event_type_l2_id,
           dimension_key = :dimension_key,
           dimension_label = :dimension_label,
           mapping_method = :mapping_method,
           model_param_id = :model_param_id,
           comment = :comment,
           mod_usr_logn_id = :mod_usr_logn_id,
           mod_dtm = CURRENT_TIMESTAMP(6),
           del_yn = :del_yn
     WHERE model_param_dimension_map_id = :model_param_dimension_map_id
    """,
)
POPULATION_UPSERT = text(
    """
    INSERT INTO tmm_mi_model_param_dimension_map (
        use_yn,
        event_type_l2_id,
        dimension_key,
        dimension_label,
        mapping_method,
        model_param_id,
        comment,
        crt_usr_logn_id,
        mod_usr_logn_id,
        del_yn
    ) VALUES (
        :use_yn,
        :event_type_l2_id,
        :dimension_key,
        :dimension_label,
        :mapping_method,
        :model_param_id,
        :comment,
        :crt_usr_logn_id,
        :mod_usr_logn_id,
        :del_yn
    )
    ON DUPLICATE KEY UPDATE
        use_yn = VALUES(use_yn),
        dimension_label = VALUES(dimension_label),
        mapping_method = VALUES(mapping_method),
        comment = VALUES(comment),
        mod_usr_logn_id = VALUES(mod_usr_logn_id),
        mod_dtm = CURRENT_TIMESTAMP(6),
        del_yn = VALUES(del_yn)
    """,
)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate and apply the model-parameter-canonical-v1 matrix. "
            "The default is a transactional dry-run that always rolls back."
        ),
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Commit the verified canonical update. Without this flag the transaction is rolled back.",
    )
    parser.add_argument(
        "--canonical",
        type=Path,
        default=CANONICAL_PATH,
        help=f"Canonical JSON path (default: {CANONICAL_PATH.relative_to(ROOT_DIR)}).",
    )
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=SNAPSHOT_PATH,
        help=f"Pre-apply snapshot JSON path (default: {SNAPSHOT_PATH.relative_to(ROOT_DIR)}).",
    )
    return parser.parse_args(argv)


def _load_json(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        msg = f"JSON root must be an object: {path}"
        raise TypeError(msg)
    return document


def _as_rows(document: Mapping[str, Any], key: str) -> list[dict[str, Any]]:
    value = document.get(key)
    if not isinstance(value, list) or not all(isinstance(row, dict) for row in value):
        msg = f"{key} must be an array of objects"
        raise RuntimeError(msg)
    return [dict(row) for row in value]


def _normalize(value: Any) -> Any:  # noqa: ANN401
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _projection(row: Mapping[str, Any], columns: Iterable[str]) -> tuple[Any, ...]:
    return tuple(_normalize(row.get(column)) for column in columns)


def _by_int_id(rows: Iterable[Mapping[str, Any]], column: str) -> dict[int, dict[str, Any]]:
    indexed: dict[int, dict[str, Any]] = {}
    for source in rows:
        raw_id = source.get(column)
        if raw_id is None:
            continue
        row_id = int(raw_id)
        if row_id in indexed:
            msg = f"duplicate {column}: {row_id}"
            raise RuntimeError(msg)
        indexed[row_id] = dict(source)
    return indexed


def _population_row(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any] | None:
    matches = [
        dict(row)
        for row in rows
        if (
            int(row.get("event_type_l2_id") or 0),
            str(row.get("dimension_key") or ""),
            int(row.get("model_param_id") or 0),
        )
        == POPULATION_NATURAL_KEY
    ]
    if len(matches) > 1:
        msg = f"duplicate Population mapping rows: {len(matches)}"
        raise RuntimeError(msg)
    return matches[0] if matches else None


def _validate_documents(  # noqa: C901
    canonical: Mapping[str, Any],
    snapshot: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    canonical_master = _as_rows(canonical, "master")
    canonical_mappings = _as_rows(canonical, "dimension_mappings")
    snapshot_master = _as_rows(snapshot, "master")
    snapshot_mappings = _as_rows(snapshot, "dimension_mappings")

    if canonical.get("canonical_version") != "model-parameter-canonical-v1":
        msg = f"unexpected canonical_version: {canonical.get('canonical_version')!r}"
        raise RuntimeError(msg)
    if len(canonical_master) != EXPECTED_MASTER_COUNT or canonical.get("master_count") != EXPECTED_MASTER_COUNT:
        msg = "canonical master count must be 21"
        raise RuntimeError(msg)
    if len(canonical_mappings) != EXPECTED_MAPPING_COUNT or canonical.get("mapping_count") != EXPECTED_MAPPING_COUNT:
        msg = "canonical mapping count must be 129"
        raise RuntimeError(msg)
    if len(snapshot_master) != EXPECTED_MASTER_COUNT or snapshot.get("master_count") != EXPECTED_MASTER_COUNT:
        msg = "snapshot master count must be 21"
        raise RuntimeError(msg)
    if len(snapshot_mappings) != 128 or snapshot.get("mapping_count") != 128:
        msg = "snapshot mapping count must be 128"
        raise RuntimeError(msg)

    canonical_identity = {int(row["model_param_id"]): str(row["parameter_name"]) for row in canonical_master}
    snapshot_identity = {int(row["model_param_id"]): str(row["parameter_name"]) for row in snapshot_master}
    if canonical_identity != EXPECTED_PARAMETER_NAMES or snapshot_identity != EXPECTED_PARAMETER_NAMES:
        msg = "canonical/snapshot 21-row ID and parameter_name matrix does not match the approved identity"
        raise RuntimeError(msg)

    active_names = {str(row["parameter_name"]) for row in canonical_master if row.get("use_yn") == "Y"}
    declared_active_names = set(canonical.get("active_parameter_names") or [])
    if active_names != EXPECTED_ACTIVE_NAMES or declared_active_names != EXPECTED_ACTIVE_NAMES:
        msg = f"canonical active names mismatch: {sorted(active_names)}"
        raise RuntimeError(msg)

    method_counts = Counter(str(row.get("mapping_method")) for row in canonical_mappings)
    if dict(method_counts) != EXPECTED_METHOD_COUNTS:
        msg = f"canonical mapping method counts mismatch: {dict(method_counts)}"
        raise RuntimeError(msg)

    canonical_mapping_by_id = _by_int_id(canonical_mappings, "model_param_dimension_map_id")
    snapshot_mapping_by_id = _by_int_id(snapshot_mappings, "model_param_dimension_map_id")
    if set(canonical_mapping_by_id) != BASE_MAPPING_IDS or set(snapshot_mapping_by_id) != BASE_MAPPING_IDS:
        msg = "canonical/snapshot must contain mapping IDs 1..128 exactly once"
        raise RuntimeError(msg)
    if _population_row(canonical_mappings) is None:
        msg = "canonical Population routing mapping is missing"
        raise RuntimeError(msg)

    return canonical_master, canonical_mappings, snapshot_master, snapshot_mappings


def _fetch_locked_master(session: Session) -> list[dict[str, Any]]:
    columns = ", ".join(MASTER_COLUMNS)
    query = f"SELECT {columns} FROM tmm_mi_model_param_m ORDER BY model_param_id FOR UPDATE"  # noqa: S608
    return [dict(row) for row in session.execute(text(query)).mappings().all()]


def _fetch_locked_mappings(session: Session) -> list[dict[str, Any]]:
    columns = ", ".join(MAPPING_COLUMNS)
    query = (
        f"SELECT {columns} FROM tmm_mi_model_param_dimension_map "  # noqa: S608
        "ORDER BY model_param_dimension_map_id FOR UPDATE"
    )
    return [dict(row) for row in session.execute(text(query)).mappings().all()]


def _fetch_templates(session: Session) -> list[dict[str, Any]]:
    query = """
        SELECT scenario_dimension_template_id, event_type_l2_id, template_json, del_yn
          FROM tmm_mi_scenario_dimension_template_m
         ORDER BY scenario_dimension_template_id
           FOR SHARE
    """
    return [dict(row) for row in session.execute(text(query)).mappings().all()]


def _assert_preconditions(  # noqa: C901
    live_master: list[dict[str, Any]],
    live_mappings: list[dict[str, Any]],
    canonical_master: list[dict[str, Any]],
    canonical_mappings: list[dict[str, Any]],
    snapshot_master: list[dict[str, Any]],
    snapshot_mappings: list[dict[str, Any]],
) -> None:
    if len(live_master) != EXPECTED_MASTER_COUNT:
        msg = f"live master count must be 21, got {len(live_master)}"
        raise RuntimeError(msg)
    if len(live_mappings) not in {128, 129}:
        msg = f"live mapping count must be 128 or 129, got {len(live_mappings)}"
        raise RuntimeError(msg)

    live_master_by_id = _by_int_id(live_master, "model_param_id")
    canonical_master_by_id = _by_int_id(canonical_master, "model_param_id")
    snapshot_master_by_id = _by_int_id(snapshot_master, "model_param_id")
    live_identity = {row_id: str(row["parameter_name"]) for row_id, row in live_master_by_id.items()}
    if live_identity != EXPECTED_PARAMETER_NAMES:
        msg = f"live 21-row ID/name matrix mismatch: {live_identity!r}"
        raise RuntimeError(msg)

    for model_param_id in sorted(EXPECTED_PARAMETER_NAMES):
        live = live_master_by_id[model_param_id]
        old = snapshot_master_by_id[model_param_id]
        final = canonical_master_by_id[model_param_id]
        if _projection(live, MASTER_CREATION_COLUMNS) != _projection(old, MASTER_CREATION_COLUMNS):
            msg = f"master creation-audit snapshot precondition failed: model_param_id={model_param_id}"
            raise RuntimeError(msg)
        live_state = _projection(live, MASTER_STABLE_COLUMNS)
        if live_state not in {
            _projection(old, MASTER_STABLE_COLUMNS),
            _projection(final, MASTER_STABLE_COLUMNS),
        }:
            msg = f"master row is neither snapshot nor canonical state: model_param_id={model_param_id}"
            raise RuntimeError(msg)

    live_mapping_by_id = _by_int_id(live_mappings, "model_param_dimension_map_id")
    canonical_mapping_by_id = _by_int_id(canonical_mappings, "model_param_dimension_map_id")
    snapshot_mapping_by_id = _by_int_id(snapshot_mappings, "model_param_dimension_map_id")
    if not BASE_MAPPING_IDS.issubset(live_mapping_by_id):
        missing = sorted(BASE_MAPPING_IDS - set(live_mapping_by_id))
        msg = f"live mapping snapshot IDs 1..128 are incomplete: missing={missing}"
        raise RuntimeError(msg)

    for mapping_id in sorted(BASE_MAPPING_IDS):
        live = live_mapping_by_id[mapping_id]
        old = snapshot_mapping_by_id[mapping_id]
        final = canonical_mapping_by_id[mapping_id]
        if _projection(live, MAPPING_CREATION_COLUMNS) != _projection(old, MAPPING_CREATION_COLUMNS):
            msg = f"mapping creation-audit snapshot precondition failed: mapping_id={mapping_id}"
            raise RuntimeError(msg)
        live_state = _projection(live, MAPPING_STABLE_COLUMNS)
        allowed = {_projection(old, MAPPING_STABLE_COLUMNS)}
        if mapping_id in RESTORED_MAPPING_IDS:
            allowed.add(_projection(final, MAPPING_STABLE_COLUMNS))
        if live_state not in allowed:
            qualifier = "old-or-final" if mapping_id in RESTORED_MAPPING_IDS else "snapshot"
            msg = f"mapping {qualifier} precondition failed: mapping_id={mapping_id}"
            raise RuntimeError(msg)

    live_population = _population_row(live_mappings)
    canonical_population = _population_row(canonical_mappings)
    if len(live_mappings) == 128 and live_population is not None:
        msg = "128-row live mapping unexpectedly contains the Population natural key"
        raise RuntimeError(msg)
    if len(live_mappings) == 129:
        if live_population is None or canonical_population is None:
            msg = "129-row live mapping must contain the canonical Population natural key"
            raise RuntimeError(msg)
        population_columns = tuple(
            column
            for column in MAPPING_STABLE_COLUMNS
            if column not in {"model_param_dimension_map_id", "crt_dtm"}
        )
        if _projection(live_population, population_columns) != _projection(
            canonical_population,
            population_columns,
        ):
            msg = "existing Population mapping is not in canonical final state"
            raise RuntimeError(msg)


def _apply_master(session: Session, canonical_master: list[dict[str, Any]]) -> None:
    for row in canonical_master:
        parameters = {column: row.get(column) for column in MASTER_DOMAIN_COLUMNS}
        parameters["model_param_id"] = int(row["model_param_id"])
        result = session.execute(MASTER_UPDATE, parameters)
        if result.rowcount != 1:
            msg = f"master update affected {result.rowcount} rows: model_param_id={row['model_param_id']}"
            raise RuntimeError(msg)


def _apply_mappings(session: Session, canonical_mappings: list[dict[str, Any]]) -> None:
    canonical_mapping_by_id = _by_int_id(canonical_mappings, "model_param_dimension_map_id")
    for mapping_id in sorted(RESTORED_MAPPING_IDS):
        row = canonical_mapping_by_id[mapping_id]
        result = session.execute(MAPPING_UPDATE, row)
        if result.rowcount != 1:
            msg = f"mapping update affected {result.rowcount} rows: mapping_id={mapping_id}"
            raise RuntimeError(msg)

    population = _population_row(canonical_mappings)
    if population is None:
        msg = "canonical Population mapping is missing"
        raise RuntimeError(msg)
    session.execute(POPULATION_UPSERT, population)


def _parse_template_json(raw: Any, *, event_type_l2_id: int) -> list[dict[str, Any]]:  # noqa: ANN401
    value = json.loads(raw) if isinstance(raw, str) else raw
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        msg = f"invalid active scenario dimension template: event_type_l2_id={event_type_l2_id}"
        raise RuntimeError(msg)
    return [dict(item) for item in value]


def _assert_invariants(  # noqa: C901
    master_rows: list[dict[str, Any]],
    mapping_rows: list[dict[str, Any]],
    template_rows: list[dict[str, Any]],
) -> None:
    if len(master_rows) != EXPECTED_MASTER_COUNT or len(mapping_rows) != EXPECTED_MAPPING_COUNT:
        msg = f"final counts mismatch: master={len(master_rows)}, mapping={len(mapping_rows)}"
        raise RuntimeError(msg)

    master_by_id = _by_int_id(master_rows, "model_param_id")
    active_names = {
        str(row["parameter_name"]) for row in master_rows if row.get("use_yn") == "Y" and row.get("del_yn") == "N"
    }
    if active_names != EXPECTED_ACTIVE_NAMES:
        msg = f"final active parameter names mismatch: {sorted(active_names)}"
        raise RuntimeError(msg)

    if any(row.get("use_yn") != "Y" or row.get("del_yn") != "N" for row in mapping_rows):
        msg = "all 129 canonical mapping rows must be use_yn=Y and del_yn=N"
        raise RuntimeError(msg)
    method_counts = Counter(str(row.get("mapping_method")) for row in mapping_rows)
    if dict(method_counts) != EXPECTED_METHOD_COUNTS:
        msg = f"final mapping method counts mismatch: {dict(method_counts)}"
        raise RuntimeError(msg)

    mapping_ids = [int(row["model_param_dimension_map_id"]) for row in mapping_rows]
    if len(mapping_ids) != len(set(mapping_ids)):
        msg = "duplicate mapping primary keys found"
        raise RuntimeError(msg)

    non_null_natural_keys = [
        (
            int(row["event_type_l2_id"]),
            str(row["dimension_key"]),
            int(row["model_param_id"]),
        )
        for row in mapping_rows
        if row.get("model_param_id") is not None
    ]
    if len(non_null_natural_keys) != len(set(non_null_natural_keys)):
        msg = "duplicate non-null mapping natural keys found"
        raise RuntimeError(msg)

    for row in mapping_rows:
        raw_model_param_id = row.get("model_param_id")
        if raw_model_param_id is None:
            continue
        model_param_id = int(raw_model_param_id)
        parameter = master_by_id.get(model_param_id)
        if parameter is None:
            msg = f"orphan parameter FK: mapping_id={row['model_param_dimension_map_id']}"
            raise RuntimeError(msg)
        if parameter.get("use_yn") != "Y" or parameter.get("del_yn") != "N":
            msg = (
                "active mapping references an inactive/deleted parameter: "
                f"mapping_id={row['model_param_dimension_map_id']}, model_param_id={model_param_id}"
            )
            raise RuntimeError(msg)

    candidate_rows = [row for row in mapping_rows if row.get("mapping_method") in {"direct", "routing"}]
    referenced_active_ids: set[int] = set()
    for row in candidate_rows:
        raw_model_param_id = row.get("model_param_id")
        if raw_model_param_id is None:
            msg = f"active direct/routing mapping has no parameter: mapping_id={row['model_param_dimension_map_id']}"
            raise RuntimeError(msg)
        model_param_id = int(raw_model_param_id)
        referenced_active_ids.add(model_param_id)

    expected_active_ids = {
        model_param_id
        for model_param_id, row in master_by_id.items()
        if row.get("use_yn") == "Y" and row.get("del_yn") == "N"
    }
    if referenced_active_ids != expected_active_ids:
        msg = (
            "every active master must have at least one direct/routing mapping: "
            f"expected={sorted(expected_active_ids)}, actual={sorted(referenced_active_ids)}"
        )
        raise RuntimeError(msg)

    active_template_rows = [row for row in template_rows if row.get("del_yn") == "N"]
    template_keys: set[tuple[int, str]] = set()
    for row in active_template_rows:
        event_type_l2_id = int(row["event_type_l2_id"])
        dimensions = _parse_template_json(
            row.get("template_json"),
            event_type_l2_id=event_type_l2_id,
        )
        for dimension in dimensions:
            dimension_key = str(dimension.get("dim_key") or "").strip()
            if dimension_key:
                template_keys.add((event_type_l2_id, dimension_key))

    missing_template_keys = sorted(
        {(int(row["event_type_l2_id"]), str(row["dimension_key"])) for row in mapping_rows} - template_keys,
    )
    if missing_template_keys:
        msg = f"mapping keys missing from active scenario dimension templates: {missing_template_keys}"
        raise RuntimeError(msg)


def _assert_read_back(
    actual_master: list[dict[str, Any]],
    actual_mappings: list[dict[str, Any]],
    canonical_master: list[dict[str, Any]],
    canonical_mappings: list[dict[str, Any]],
) -> None:
    actual_master_by_id = _by_int_id(actual_master, "model_param_id")
    canonical_master_by_id = _by_int_id(canonical_master, "model_param_id")
    for model_param_id in sorted(EXPECTED_PARAMETER_NAMES):
        if _projection(actual_master_by_id[model_param_id], MASTER_STABLE_COLUMNS) != _projection(
            canonical_master_by_id[model_param_id],
            MASTER_STABLE_COLUMNS,
        ):
            msg = f"master canonical read-back mismatch: model_param_id={model_param_id}"
            raise RuntimeError(msg)

    actual_mapping_by_id = _by_int_id(actual_mappings, "model_param_dimension_map_id")
    canonical_mapping_by_id = _by_int_id(canonical_mappings, "model_param_dimension_map_id")
    for mapping_id in sorted(BASE_MAPPING_IDS):
        if _projection(actual_mapping_by_id[mapping_id], MAPPING_STABLE_COLUMNS) != _projection(
            canonical_mapping_by_id[mapping_id],
            MAPPING_STABLE_COLUMNS,
        ):
            msg = f"mapping canonical read-back mismatch: mapping_id={mapping_id}"
            raise RuntimeError(msg)

    actual_population = _population_row(actual_mappings)
    canonical_population = _population_row(canonical_mappings)
    if actual_population is None or canonical_population is None:
        msg = "Population mapping missing during canonical read-back"
        raise RuntimeError(msg)
    population_columns = tuple(
        column
        for column in MAPPING_STABLE_COLUMNS
        if column not in {"model_param_dimension_map_id", "crt_dtm"}
    )
    if _projection(actual_population, population_columns) != _projection(
        canonical_population,
        population_columns,
    ):
        msg = "Population canonical read-back mismatch"
        raise RuntimeError(msg)


def run(*, apply: bool, canonical_path: Path, snapshot_path: Path) -> None:
    from apps.common.configs.database.sync_database.connection import (
        get_sync_session,
    )

    canonical = _load_json(canonical_path)
    snapshot = _load_json(snapshot_path)
    canonical_master, canonical_mappings, snapshot_master, snapshot_mappings = _validate_documents(
        canonical,
        snapshot,
    )

    session = get_sync_session()
    try:
        live_master = _fetch_locked_master(session)
        live_mappings = _fetch_locked_mappings(session)
        _assert_preconditions(
            live_master,
            live_mappings,
            canonical_master,
            canonical_mappings,
            snapshot_master,
            snapshot_mappings,
        )

        _apply_master(session, canonical_master)
        _apply_mappings(session, canonical_mappings)

        actual_master = _fetch_locked_master(session)
        actual_mappings = _fetch_locked_mappings(session)
        templates = _fetch_templates(session)
        _assert_invariants(actual_master, actual_mappings, templates)
        _assert_read_back(
            actual_master,
            actual_mappings,
            canonical_master,
            canonical_mappings,
        )

        if apply:
            session.commit()
            LOGGER.info(
                "canonical apply committed: version=%s, master=%s, mappings=%s",
                canonical["canonical_version"],
                len(actual_master),
                len(actual_mappings),
            )
        else:
            session.rollback()
            LOGGER.info(
                "canonical dry-run passed and rolled back: version=%s, master=%s, mappings=%s",
                canonical["canonical_version"],
                len(actual_master),
                len(actual_mappings),
            )
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = _parse_args(argv)
    try:
        run(
            apply=bool(args.apply),
            canonical_path=args.canonical.resolve(),
            snapshot_path=args.snapshot.resolve(),
        )
    except Exception:
        LOGGER.exception("model parameter canonical operation failed")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
