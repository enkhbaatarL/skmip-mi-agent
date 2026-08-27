from __future__ import annotations

# Copyright (c) 2026 SK Innovation E&S.
import argparse
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

LOGGER = logging.getLogger("impact_lever_canonical")
CANONICAL_VERSION = "model-impact-lever-canonical-v3"
CATALOG_VERSION = "v3"
CANONICAL_PATH = ROOT_DIR / "scripts" / "model_parameter" / f"{CANONICAL_VERSION}.json"
SNAPSHOT_PATH = (
    ROOT_DIR / "scripts" / "model_parameter" / "snapshots" / "external_dev_impact_lever_before_v3_20260807.json"
)

EXPECTED_LEVER_COUNT = 16
EXPECTED_BINDING_COUNT = 14
EXPECTED_RAW_EXECUTABLE_COUNT = 14
EXPECTED_EFFECTIVE_EXECUTABLE_COUNT = 9
EXPECTED_EFFECTIVE_UNSUPPORTED_COUNT = 5
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
EXPECTED_EFFECTIVE_EXECUTABLE_NAMES = EXPECTED_ACTIVE_NAMES - {"Population"}
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
            "Validate and apply the 16-row model-impact-lever-canonical-v3 catalog. "
            "The default is a transactional dry-run that always rolls back."
        ),
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Commit the verified catalog update. Without this flag the transaction is rolled back.",
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
        message = f"JSON root must be an object: {path}"
        raise TypeError(message)
    return document


def _rows(document: Mapping[str, Any], key: str) -> list[dict[str, Any]]:
    value = document.get(key)
    if not isinstance(value, list) or not all(isinstance(row, dict) for row in value):
        message = f"{key} must be an array of objects"
        raise RuntimeError(message)
    return [dict(row) for row in value]


def _decode_bindings(value: object, *, lever_code: str) -> list[dict[str, Any]]:
    decoded = json.loads(value) if isinstance(value, str) else value
    if not isinstance(decoded, list) or not all(isinstance(item, dict) for item in decoded):
        message = f"invalid parameter_bindings: lever_code={lever_code}"
        raise RuntimeError(message)
    return [dict(item) for item in decoded]


def _normalize(value: Any, *, column: str | None = None) -> Any:  # noqa: ANN401
    if column == "parameter_bindings":
        return json.dumps(
            _decode_bindings(value, lever_code="projection"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _projection(row: Mapping[str, Any], columns: Iterable[str]) -> tuple[Any, ...]:
    return tuple(_normalize(row.get(column), column=column) for column in columns)


def _by_id(rows: Iterable[Mapping[str, Any]], id_column: str) -> dict[int, dict[str, Any]]:
    indexed: dict[int, dict[str, Any]] = {}
    for source in rows:
        row_id = int(source[id_column])
        if row_id in indexed:
            message = f"duplicate {id_column}: {row_id}"
            raise RuntimeError(message)
        indexed[row_id] = dict(source)
    return indexed


def _digest(rows: list[dict[str, Any]]) -> str:
    normalized: list[dict[str, Any]] = []
    for source in rows:
        row = {column: _normalize(source.get(column), column=column) for column in IMPACT_LEVER_COLUMNS}
        normalized.append(row)
    payload = json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _validate_documents(  # noqa: C901
    canonical: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    *,
    snapshot_path: Path,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    canonical_levers = _rows(canonical, "impact_levers")
    snapshot_levers = _rows(snapshot, "impact_levers")
    snapshot_master = _rows(snapshot, "master")
    snapshot_mappings = _rows(snapshot, "dimension_mappings")

    if canonical.get("canonical_version") != CANONICAL_VERSION:
        message = f"unexpected canonical_version: {canonical.get('canonical_version')!r}"
        raise RuntimeError(message)
    if canonical.get("catalog_version") != CATALOG_VERSION:
        message = f"unexpected catalog_version: {canonical.get('catalog_version')!r}"
        raise RuntimeError(message)
    if canonical.get("audit_user") != CANONICAL_VERSION:
        message = f"unexpected audit_user: {canonical.get('audit_user')!r}"
        raise RuntimeError(message)
    declared_snapshot = canonical.get("generated_from_snapshot")
    if not isinstance(declared_snapshot, str) or not declared_snapshot.strip():
        message = "generated_from_snapshot must be a non-empty repository-relative path"
        raise RuntimeError(message)
    if (ROOT_DIR / declared_snapshot).resolve() != snapshot_path.resolve():
        message = "canonical generated_from_snapshot does not identify the selected snapshot"
        raise RuntimeError(message)
    actual_snapshot_sha256 = hashlib.sha256(snapshot_path.read_bytes()).hexdigest()
    if canonical.get("snapshot_sha256") != actual_snapshot_sha256:
        message = "canonical snapshot_sha256 does not match the selected snapshot"
        raise RuntimeError(message)
    if len(canonical_levers) != EXPECTED_LEVER_COUNT or canonical.get("impact_lever_count") != EXPECTED_LEVER_COUNT:
        message = "canonical impact lever count must be 16"
        raise RuntimeError(message)
    if len(snapshot_levers) != EXPECTED_LEVER_COUNT or snapshot.get("impact_lever_count") != EXPECTED_LEVER_COUNT:
        message = "snapshot impact lever count must be 16"
        raise RuntimeError(message)
    if len(snapshot_master) != 21 or snapshot.get("master_count") != 21:
        message = "snapshot master count must be 21"
        raise RuntimeError(message)
    declared_mapping_count = snapshot.get("mapping_count")
    if not isinstance(declared_mapping_count, int) or len(snapshot_mappings) != declared_mapping_count:
        message = "snapshot dimension mapping count does not match its declared mapping_count"
        raise RuntimeError(message)

    canonical_by_id = _by_id(canonical_levers, "impact_lever_id")
    snapshot_by_id = _by_id(snapshot_levers, "impact_lever_id")
    if set(canonical_by_id) != set(snapshot_by_id):
        message = "canonical and snapshot impact lever IDs differ"
        raise RuntimeError(message)
    for lever_id in sorted(canonical_by_id):
        canonical_row = canonical_by_id[lever_id]
        snapshot_row = snapshot_by_id[lever_id]
        if canonical_row.get("lever_code") != snapshot_row.get("lever_code"):
            message = f"lever identity mismatch: impact_lever_id={lever_id}"
            raise RuntimeError(message)
        if snapshot_row.get("catalog_version") != "v2":
            message = f"snapshot row is not v2: impact_lever_id={lever_id}"
            raise RuntimeError(message)
        if canonical_row.get("catalog_version") != CATALOG_VERSION:
            message = f"canonical row is not v3: impact_lever_id={lever_id}"
            raise RuntimeError(message)
        if _projection(canonical_row, IMPACT_LEVER_CREATION_COLUMNS) != _projection(
            snapshot_row,
            IMPACT_LEVER_CREATION_COLUMNS,
        ):
            message = f"canonical changed creation audit: impact_lever_id={lever_id}"
            raise RuntimeError(message)

    return canonical_levers, snapshot_levers, snapshot_master, snapshot_mappings


def _fetch_master(session: Session, *, lock: bool) -> list[dict[str, Any]]:
    suffix = " FOR SHARE" if lock else ""
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


def _assert_preconditions(  # noqa: C901
    live_master: list[dict[str, Any]],
    live_mappings: list[dict[str, Any]],
    live_levers: list[dict[str, Any]],
    canonical_levers: list[dict[str, Any]],
    snapshot_levers: list[dict[str, Any]],
    snapshot_master: list[dict[str, Any]],
    snapshot_mappings: list[dict[str, Any]],
) -> None:
    if len(live_master) != 21:
        message = f"live master count must be 21, got {len(live_master)}"
        raise RuntimeError(message)
    if len(live_levers) != EXPECTED_LEVER_COUNT:
        message = f"live impact lever count must be 16, got {len(live_levers)}"
        raise RuntimeError(message)
    if len(live_mappings) != len(snapshot_mappings):
        message = (
            "live dimension mapping count must match the selected snapshot, "
            f"expected {len(snapshot_mappings)}, got {len(live_mappings)}"
        )
        raise RuntimeError(message)

    snapshot_master_by_id = _by_id(snapshot_master, "model_param_id")
    live_master_by_id = _by_id(live_master, "model_param_id")
    if set(snapshot_master_by_id) != set(live_master_by_id):
        message = "live master IDs differ from the pre-apply snapshot"
        raise RuntimeError(message)
    for model_param_id in sorted(live_master_by_id):
        if _projection(live_master_by_id[model_param_id], MASTER_COLUMNS) != _projection(
            snapshot_master_by_id[model_param_id],
            MASTER_COLUMNS,
        ):
            message = f"model parameter master changed after snapshot: model_param_id={model_param_id}"
            raise RuntimeError(message)

    snapshot_mapping_by_id = _by_id(snapshot_mappings, "model_param_dimension_map_id")
    live_mapping_by_id = _by_id(live_mappings, "model_param_dimension_map_id")
    if set(snapshot_mapping_by_id) != set(live_mapping_by_id):
        message = "live dimension mapping IDs differ from the pre-apply snapshot"
        raise RuntimeError(message)
    for mapping_id in sorted(live_mapping_by_id):
        if _projection(live_mapping_by_id[mapping_id], MAPPING_COLUMNS) != _projection(
            snapshot_mapping_by_id[mapping_id],
            MAPPING_COLUMNS,
        ):
            message = f"dimension mapping changed after snapshot: mapping_id={mapping_id}"
            raise RuntimeError(message)

    live_by_id = _by_id(live_levers, "impact_lever_id")
    canonical_by_id = _by_id(canonical_levers, "impact_lever_id")
    snapshot_by_id = _by_id(snapshot_levers, "impact_lever_id")
    if set(live_by_id) != set(canonical_by_id) or set(live_by_id) != set(snapshot_by_id):
        message = "live/canonical/snapshot impact lever IDs differ"
        raise RuntimeError(message)

    for lever_id in sorted(live_by_id):
        live = live_by_id[lever_id]
        old = snapshot_by_id[lever_id]
        final = canonical_by_id[lever_id]
        if _projection(live, IMPACT_LEVER_CREATION_COLUMNS) != _projection(
            old,
            IMPACT_LEVER_CREATION_COLUMNS,
        ):
            message = f"impact lever creation audit changed: impact_lever_id={lever_id}"
            raise RuntimeError(message)
        live_state = _projection(live, IMPACT_LEVER_STABLE_COLUMNS)
        allowed_states = {
            _projection(old, IMPACT_LEVER_STABLE_COLUMNS),
            _projection(final, IMPACT_LEVER_STABLE_COLUMNS),
        }
        if live_state not in allowed_states:
            message = f"impact lever is neither snapshot nor canonical: impact_lever_id={lever_id}"
            raise RuntimeError(message)


def _apply_levers(session: Session, canonical_levers: list[dict[str, Any]]) -> None:
    for row in canonical_levers:
        parameters = {
            "impact_lever_id": int(row["impact_lever_id"]),
            "lever_code": str(row["lever_code"]),
            "domain": str(row["domain"]),
            "label": str(row["label"]),
            "description": str(row["description"]),
            "applicability_hint": row.get("applicability_hint"),
            "parent_lever_code": row.get("parent_lever_code"),
            "parameter_bindings": json.dumps(
                _decode_bindings(
                    row.get("parameter_bindings"),
                    lever_code=str(row["lever_code"]),
                ),
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            "catalog_version": CATALOG_VERSION,
            "use_yn": str(row["use_yn"]),
            "mod_usr_logn_id": CANONICAL_VERSION,
            "del_yn": str(row["del_yn"]),
        }
        result = session.execute(IMPACT_LEVER_UPDATE, parameters)
        if result.rowcount != 1:
            message = f"impact lever update affected {result.rowcount} rows: impact_lever_id={row['impact_lever_id']}"
            raise RuntimeError(message)


def _assert_parent_graph(rows: list[dict[str, Any]]) -> None:
    parent_by_code = {
        str(row["lever_code"]): (str(row["parent_lever_code"]) if row.get("parent_lever_code") is not None else None)
        for row in rows
    }
    for code, parent in parent_by_code.items():
        if parent is not None and parent not in parent_by_code:
            message = f"orphan parent lever: lever_code={code}, parent={parent}"
            raise RuntimeError(message)
        seen = {code}
        cursor = parent
        while cursor is not None:
            if cursor in seen:
                message = f"impact lever parent cycle: lever_code={code}"
                raise RuntimeError(message)
            seen.add(cursor)
            cursor = parent_by_code[cursor]


def _assert_invariants(  # noqa: C901
    master_rows: list[dict[str, Any]],
    mapping_rows: list[dict[str, Any]],
    lever_rows: list[dict[str, Any]],
) -> None:
    if len(lever_rows) != EXPECTED_LEVER_COUNT:
        message = f"final impact lever count mismatch: {len(lever_rows)}"
        raise RuntimeError(message)
    if any(
        row.get("catalog_version") != CATALOG_VERSION or row.get("use_yn") != "Y" or row.get("del_yn") != "N"
        for row in lever_rows
    ):
        message = "all canonical impact levers must be active, non-deleted v3 rows"
        raise RuntimeError(message)
    if any(str(row.get("domain")) not in VALID_DOMAINS for row in lever_rows):
        message = "invalid impact lever domain"
        raise RuntimeError(message)

    codes = [str(row["lever_code"]) for row in lever_rows]
    if len(codes) != len(set(codes)):
        message = "duplicate impact lever code"
        raise RuntimeError(message)
    _assert_parent_graph(lever_rows)

    master_by_name = {str(row["parameter_name"]): row for row in master_rows}
    active_names = {
        name for name, row in master_by_name.items() if row.get("use_yn") == "Y" and row.get("del_yn") == "N"
    }
    if active_names != EXPECTED_ACTIVE_NAMES:
        message = f"active parameter names mismatch: {sorted(active_names)}"
        raise RuntimeError(message)

    binding_count = 0
    raw_executable_count = 0
    effective_executable_count = 0
    effective_unsupported_count = 0
    effective_executable_names: set[str] = set()
    for lever in lever_rows:
        lever_code = str(lever["lever_code"])
        bindings = _decode_bindings(
            lever.get("parameter_bindings"),
            lever_code=lever_code,
        )
        if lever.get("domain") == "price_only" and bindings:
            message = f"price_only lever has bindings: lever_code={lever_code}"
            raise RuntimeError(message)
        parameter_names: list[str] = []
        for binding in bindings:
            expected_keys = {
                "parameter_name",
                "role",
                "applicability",
                "support_status",
            }
            if set(binding) != expected_keys:
                message = f"unexpected binding schema: lever_code={lever_code}, binding={binding!r}"
                raise RuntimeError(message)
            parameter_name = str(binding["parameter_name"])
            parameter_names.append(parameter_name)
            if parameter_name not in master_by_name or master_by_name[parameter_name].get("del_yn") != "N":
                message = f"unknown/deleted parameter binding: lever_code={lever_code}, name={parameter_name}"
                raise RuntimeError(message)
            if binding.get("role") not in VALID_ROLES:
                message = f"invalid binding role: lever_code={lever_code}, name={parameter_name}"
                raise RuntimeError(message)
            if not str(binding.get("applicability") or "").strip():
                message = f"empty binding applicability: lever_code={lever_code}, name={parameter_name}"
                raise RuntimeError(message)
            if binding.get("support_status") != "executable":
                message = (
                    f"v3 raw binding must preserve catalog capability: lever_code={lever_code}, name={parameter_name}"
                )
                raise RuntimeError(message)
            binding_count += 1
            raw_executable_count += 1
            if master_by_name[parameter_name].get("use_yn") == "Y":
                effective_executable_count += 1
                effective_executable_names.add(parameter_name)
            else:
                effective_unsupported_count += 1
        if len(parameter_names) != len(set(parameter_names)):
            message = f"duplicate parameter binding: lever_code={lever_code}"
            raise RuntimeError(message)

    actual_counts = (
        binding_count,
        raw_executable_count,
        effective_executable_count,
        effective_unsupported_count,
    )
    expected_counts = (
        EXPECTED_BINDING_COUNT,
        EXPECTED_RAW_EXECUTABLE_COUNT,
        EXPECTED_EFFECTIVE_EXECUTABLE_COUNT,
        EXPECTED_EFFECTIVE_UNSUPPORTED_COUNT,
    )
    if actual_counts != expected_counts:
        message = f"binding count mismatch: actual={actual_counts}, expected={expected_counts}"
        raise RuntimeError(message)
    if effective_executable_names != EXPECTED_EFFECTIVE_EXECUTABLE_NAMES:
        message = f"effective executable names mismatch: {sorted(effective_executable_names)}"
        raise RuntimeError(message)

    active_candidate_mapping_ids = {
        int(row["model_param_id"])
        for row in mapping_rows
        if row.get("use_yn") == "Y"
        and row.get("del_yn") == "N"
        and row.get("mapping_method") in {"direct", "routing"}
        and row.get("model_param_id") is not None
    }
    expected_effective_ids = {
        int(master_by_name[name]["model_param_id"]) for name in EXPECTED_EFFECTIVE_EXECUTABLE_NAMES
    }
    if not expected_effective_ids.issubset(active_candidate_mapping_ids):
        missing = sorted(expected_effective_ids - active_candidate_mapping_ids)
        message = f"effective bindings lack active direct/routing mapping evidence: model_param_ids={missing}"
        raise RuntimeError(message)


def _assert_read_back(
    actual_levers: list[dict[str, Any]],
    canonical_levers: list[dict[str, Any]],
) -> None:
    actual_by_id = _by_id(actual_levers, "impact_lever_id")
    canonical_by_id = _by_id(canonical_levers, "impact_lever_id")
    for lever_id in sorted(canonical_by_id):
        if _projection(actual_by_id[lever_id], IMPACT_LEVER_STABLE_COLUMNS) != _projection(
            canonical_by_id[lever_id],
            IMPACT_LEVER_STABLE_COLUMNS,
        ):
            message = f"impact lever canonical read-back mismatch: impact_lever_id={lever_id}"
            raise RuntimeError(message)


def _fetch_fresh_levers() -> list[dict[str, Any]]:
    from apps.common.configs.database.sync_database.connection import get_sync_session

    verification_session = get_sync_session()
    try:
        return _fetch_levers(verification_session, lock=False)
    finally:
        verification_session.close()


def _assert_digest_equal(actual: str, expected: str, *, message: str) -> None:
    if actual != expected:
        raise RuntimeError(message)


def run(*, apply: bool, canonical_path: Path, snapshot_path: Path) -> None:
    from apps.common.configs.database.sync_database.connection import get_sync_session

    canonical = _load_json(canonical_path)
    snapshot = _load_json(snapshot_path)
    canonical_levers, snapshot_levers, snapshot_master, snapshot_mappings = _validate_documents(
        canonical,
        snapshot,
        snapshot_path=snapshot_path,
    )

    session = get_sync_session()
    try:
        live_master = _fetch_master(session, lock=True)
        live_mappings = _fetch_mappings(session, lock=True)
        live_levers = _fetch_levers(session, lock=True)
        before_digest = _digest(live_levers)
        _assert_preconditions(
            live_master,
            live_mappings,
            live_levers,
            canonical_levers,
            snapshot_levers,
            snapshot_master,
            snapshot_mappings,
        )

        _apply_levers(session, canonical_levers)
        actual_levers = _fetch_levers(session, lock=True)
        _assert_invariants(live_master, live_mappings, actual_levers)
        _assert_read_back(actual_levers, canonical_levers)
        transactional_digest = _digest(actual_levers)

        if apply:
            session.commit()
            persisted_levers = _fetch_fresh_levers()
            _assert_invariants(live_master, live_mappings, persisted_levers)
            _assert_read_back(persisted_levers, canonical_levers)
            persisted_digest = _digest(persisted_levers)
            _assert_digest_equal(
                persisted_digest,
                transactional_digest,
                message="persisted digest differs from the verified transaction digest",
            )
            LOGGER.info(
                "impact lever canonical apply committed: version=%s rows=%s before_digest=%s after_digest=%s",
                CANONICAL_VERSION,
                len(persisted_levers),
                before_digest,
                persisted_digest,
            )
        else:
            session.rollback()
            persisted_levers = _fetch_fresh_levers()
            persisted_digest = _digest(persisted_levers)
            _assert_digest_equal(
                persisted_digest,
                before_digest,
                message="dry-run rollback did not preserve the exact pre-transaction table state",
            )
            LOGGER.info(
                "impact lever canonical dry-run passed and rolled back: "
                "version=%s rows=%s before_digest=%s transactional_digest=%s "
                "rollback_digest=%s",
                CANONICAL_VERSION,
                len(actual_levers),
                before_digest,
                transactional_digest,
                persisted_digest,
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
        LOGGER.exception("impact lever canonical operation failed")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
