from __future__ import annotations

# Copyright (c) 2026 SK Innovation E&S.
import argparse
from collections.abc import Mapping, Sequence
import hashlib
import json
import logging
from pathlib import Path
import sys
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from apps.persistence.model_impact_lever.service import ModelImpactLeverService  # noqa: E402
from scripts.model_parameter.apply_model_parameter_v4 import (  # noqa: E402
    MAPPING_COLUMNS,
    MASTER_COLUMNS,
    _fetch_levers,
    _fetch_mappings,
    _fetch_master,
    _fetch_templates,
    _semantic_digest,
)
from scripts.model_parameter.capture_model_parameter_v4_external_snapshot import (  # noqa: E402
    _normalize_active_templates,
    _normalize_levers,
    _normalize_rows,
)
from scripts.model_parameter.prepare_model_impact_lever_v4_1 import (  # noqa: E402
    AUDIT_USER,
    CANONICAL_PATH,
    CANONICAL_VERSION,
    SNAPSHOT_PATH,
    SOURCE_CATALOG_VERSION,
    TARGET_CATALOG_VERSION,
    TARGET_ID_BY_CODE,
)


LOGGER = logging.getLogger("apply_model_impact_lever_v4_1")
EXPECTED_SOURCE_CHECKSUM = "416017351f2b9539370963a3ca413914876da55a1db3f41e3dacd34bd466c763"

INSERT_LEVER = text(
    """
    INSERT INTO tmm_mi_model_impact_lever_m (
        impact_lever_id,
        lever_code,
        domain,
        label,
        description,
        applicability_hint,
        parent_lever_code,
        parameter_bindings,
        catalog_version,
        use_yn,
        crt_usr_logn_id,
        crt_dtm,
        mod_usr_logn_id,
        mod_dtm,
        del_yn
    ) VALUES (
        :impact_lever_id,
        :lever_code,
        :domain,
        :label,
        :description,
        :applicability_hint,
        :parent_lever_code,
        :parameter_bindings,
        :catalog_version,
        :use_yn,
        :audit_user,
        CURRENT_TIMESTAMP(6),
        :audit_user,
        CURRENT_TIMESTAMP(6),
        :del_yn
    )
    """,
)

FUNCTIONAL_COLUMNS = (
    "lever_code",
    "domain",
    "label",
    "description",
    "applicability_hint",
    "parent_lever_code",
    "parameter_bindings",
    "catalog_version",
    "use_yn",
    "del_yn",
)

TARGET_IDENTITY_COLUMNS = (
    "impact_lever_id",
    "lever_code",
    "crt_usr_logn_id",
    "mod_usr_logn_id",
)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate and insert the 21-row v4.1 Impact Lever catalog beside v4.0. "
            "The default is a transactional dry-run that always rolls back."
        ),
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--apply",
        action="store_true",
        help="Commit the verified v4.1 insert. Without this flag the transaction is rolled back.",
    )
    mode.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate canonical/snapshot files without opening a DB connection.",
    )
    parser.add_argument("--canonical", type=Path, default=CANONICAL_PATH)
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


def _canonical_functional_row(row: Mapping[str, Any]) -> dict[str, Any]:
    return {column: row.get(column) for column in FUNCTIONAL_COLUMNS}


def _functional_digest(rows: list[dict[str, Any]]) -> str:
    normalized = [_canonical_functional_row(row) for row in sorted(rows, key=lambda item: str(item["lever_code"]))]
    return hashlib.sha256(
        json.dumps(
            normalized,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8"),
    ).hexdigest()


def _validate_documents(  # noqa: C901
    canonical: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    *,
    snapshot_path: Path,
) -> tuple[list[dict[str, Any]], set[str]]:
    if canonical.get("canonical_version") != CANONICAL_VERSION:
        message = f"unexpected canonical_version: {canonical.get('canonical_version')!r}"
        raise RuntimeError(message)
    if canonical.get("catalog_version") != TARGET_CATALOG_VERSION:
        message = f"unexpected catalog_version: {canonical.get('catalog_version')!r}"
        raise RuntimeError(message)
    if canonical.get("source_catalog_version") != SOURCE_CATALOG_VERSION:
        message = "canonical source catalog version mismatch"
        raise RuntimeError(message)
    if canonical.get("audit_user") != AUDIT_USER:
        message = f"canonical audit_user must be {AUDIT_USER}"
        raise RuntimeError(message)
    snapshot_sha = hashlib.sha256(snapshot_path.read_bytes()).hexdigest()
    if canonical.get("snapshot_sha256") != snapshot_sha:
        message = "canonical snapshot SHA-256 does not match the selected immutable snapshot"
        raise RuntimeError(message)
    if canonical.get("source_catalog_checksum") != EXPECTED_SOURCE_CHECKSUM:
        message = "canonical v4.0 source checksum mismatch"
        raise RuntimeError(message)

    canonical_rows = _rows(canonical, "impact_levers")
    snapshot_rows = _rows(snapshot, "impact_levers")
    source_rows = [
        row
        for row in snapshot_rows
        if row.get("catalog_version") == SOURCE_CATALOG_VERSION
        and row.get("use_yn") == "Y"
        and row.get("del_yn") == "N"
    ]
    if len(canonical_rows) != 21 or len(source_rows) != 21:
        message = "v4.0 and v4.1 must each contain exactly 21 active Lever rows"
        raise RuntimeError(message)
    source_codes = {str(row["lever_code"]) for row in source_rows}
    target_codes = {str(row["lever_code"]) for row in canonical_rows}
    if source_codes != target_codes or target_codes != set(canonical.get("lever_full_set") or []):
        message = "v4.1 Lever Full Set differs from v4.0"
        raise RuntimeError(message)
    if any(row.get("catalog_version") != TARGET_CATALOG_VERSION for row in canonical_rows):
        message = "canonical contains a non-v4.1 row"
        raise RuntimeError(message)
    if len(target_codes) != len(canonical_rows):
        message = "canonical contains duplicate lever_code values"
        raise RuntimeError(message)
    target_ids = {int(row.get("target_impact_lever_id") or 0) for row in canonical_rows}
    if target_ids != set(TARGET_ID_BY_CODE.values()) or any(
        int(row.get("target_impact_lever_id") or 0) != TARGET_ID_BY_CODE[str(row["lever_code"])]
        for row in canonical_rows
    ):
        message = "canonical target Impact Lever IDs must be the pinned 56..76 mapping"
        raise RuntimeError(message)

    master_rows = _rows(snapshot, "master")
    master_by_name = {str(row["parameter_name"]): row for row in master_rows if row.get("del_yn") == "N"}
    conditional_count = 0
    binding_count = 0
    for row in canonical_rows:
        bindings = row.get("parameter_bindings")
        if not isinstance(bindings, list):
            message = f"parameter_bindings must be an array: {row.get('lever_code')}"
            raise TypeError(message)
        names: set[str] = set()
        for binding in bindings:
            if not isinstance(binding, dict):
                message = f"invalid binding object: {row.get('lever_code')}"
                raise TypeError(message)
            parameter_name = str(binding.get("parameter_name") or "")
            if parameter_name not in master_by_name:
                message = f"binding references unknown parameter: {parameter_name}"
                raise RuntimeError(message)
            if parameter_name in names:
                message = f"duplicate binding: {row.get('lever_code')} -> {parameter_name}"
                raise RuntimeError(message)
            names.add(parameter_name)
            if binding.get("selection_mode") == "conditional":
                conditional_count += 1
                if master_by_name[parameter_name].get("use_yn") != "Y":
                    message = f"conditional binding must target an active parameter: {parameter_name}"
                    raise RuntimeError(message)
            binding_count += 1
        if row.get("domain") == "price_only" and any(
            binding.get("selection_mode") != "conditional" for binding in bindings
        ):
            message = f"price_only binding must be conditional: {row.get('lever_code')}"
            raise RuntimeError(message)

    if binding_count != canonical.get("binding_occurrence_count"):
        message = "canonical binding count mismatch"
        raise RuntimeError(message)
    if conditional_count != canonical.get("conditional_binding_occurrence_count"):
        message = "canonical conditional binding count mismatch"
        raise RuntimeError(message)

    expected_snapshot_digests = snapshot.get("table_digests")
    actual_snapshot_digests = {
        "master_sha256": _semantic_digest(_rows(snapshot, "master")),
        "dimension_mappings_sha256": _semantic_digest(_rows(snapshot, "dimension_mappings")),
        "impact_levers_sha256": _semantic_digest(snapshot_rows),
        "v4_0_active_impact_levers_sha256": _semantic_digest(source_rows),
        "scenario_dimension_templates_sha256": _semantic_digest(
            _rows(snapshot, "scenario_dimension_templates"),
        ),
    }
    if expected_snapshot_digests != actual_snapshot_digests:
        message = "immutable snapshot table digests do not self-verify"
        raise RuntimeError(message)
    return canonical_rows, source_codes


def _assert_protected_tables_unchanged(
    session: Session,
    snapshot: Mapping[str, Any],
    *,
    lock: bool,
) -> list[dict[str, Any]]:
    master = _normalize_rows(_fetch_master(session, lock=lock), columns=MASTER_COLUMNS)
    mappings = _normalize_rows(_fetch_mappings(session, lock=lock), columns=MAPPING_COLUMNS)
    levers = _normalize_levers(_fetch_levers(session, lock=lock))
    templates = _normalize_active_templates(_fetch_templates(session, lock=lock))
    non_target_levers = [row for row in levers if row.get("catalog_version") != TARGET_CATALOG_VERSION]
    checks = {
        "master": (master, _rows(snapshot, "master")),
        "dimension mappings": (mappings, _rows(snapshot, "dimension_mappings")),
        "non-v4.1 Impact Levers": (non_target_levers, _rows(snapshot, "impact_levers")),
        "Scenario templates": (templates, _rows(snapshot, "scenario_dimension_templates")),
    }
    for label, (actual, expected) in checks.items():
        if _semantic_digest(actual) != _semantic_digest(expected):
            message = f"protected {label} drifted from the immutable pre-apply snapshot"
            raise RuntimeError(message)
    return levers


def _target_rows(levers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        row
        for row in levers
        if row.get("catalog_version") == TARGET_CATALOG_VERSION
        and row.get("use_yn") == "Y"
        and row.get("del_yn") == "N"
    ]


def _all_target_version_rows(levers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in levers if row.get("catalog_version") == TARGET_CATALOG_VERSION]


def _assert_target_matches(
    actual_rows: list[dict[str, Any]],
    canonical_rows: list[dict[str, Any]],
) -> None:
    if len(actual_rows) != len(canonical_rows):
        message = f"v4.1 row count mismatch: expected={len(canonical_rows)}, actual={len(actual_rows)}"
        raise RuntimeError(message)
    if _functional_digest(actual_rows) != _functional_digest(canonical_rows):
        message = "v4.1 functional rows differ from the canonical artifact"
        raise RuntimeError(message)


def _target_identity_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {column: row.get(column) for column in TARGET_IDENTITY_COLUMNS}
        for row in sorted(rows, key=lambda item: str(item["lever_code"]))
    ]


def _expected_target_identity_rows(
    canonical_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "impact_lever_id": int(row["target_impact_lever_id"]),
            "lever_code": row["lever_code"],
            "crt_usr_logn_id": AUDIT_USER,
            "mod_usr_logn_id": AUDIT_USER,
        }
        for row in sorted(canonical_rows, key=lambda item: str(item["lever_code"]))
    ]


def _target_identity_matches(
    actual_rows: list[dict[str, Any]],
    canonical_rows: list[dict[str, Any]],
) -> bool:
    return _target_identity_rows(actual_rows) == _expected_target_identity_rows(
        canonical_rows,
    )


def _normalize_target_identity(
    session: Session,
    canonical_rows: list[dict[str, Any]],
) -> None:
    collisions = (
        session.execute(
            text(
                """
            SELECT impact_lever_id, catalog_version, lever_code
            FROM tmm_mi_model_impact_lever_m
            WHERE impact_lever_id IN :target_ids
              AND catalog_version <> :target_version
            ORDER BY impact_lever_id
            """,
            ).bindparams(bindparam("target_ids", expanding=True)),
            {
                "target_ids": sorted(TARGET_ID_BY_CODE.values()),
                "target_version": TARGET_CATALOG_VERSION,
            },
        )
        .mappings()
        .all()
    )
    if collisions:
        message = f"pinned v4.1 Impact Lever IDs collide with other catalogs: {collisions}"
        raise RuntimeError(message)

    statement = text(
        """
        UPDATE tmm_mi_model_impact_lever_m
        SET impact_lever_id = :impact_lever_id,
            crt_usr_logn_id = :audit_user,
            mod_usr_logn_id = :audit_user,
            mod_dtm = CURRENT_TIMESTAMP(6)
        WHERE catalog_version = :catalog_version
          AND lever_code = :lever_code
        """,
    )
    for row in canonical_rows:
        result = session.execute(
            statement,
            {
                "impact_lever_id": int(row["target_impact_lever_id"]),
                "audit_user": AUDIT_USER,
                "catalog_version": TARGET_CATALOG_VERSION,
                "lever_code": row["lever_code"],
            },
        )
        if result.rowcount != 1:
            message = f"failed to normalize v4.1 identity: {row['lever_code']}"
            raise RuntimeError(message)


def _insert_rows(session: Session, canonical_rows: list[dict[str, Any]]) -> None:
    for row in canonical_rows:
        session.execute(
            INSERT_LEVER,
            {
                **_canonical_functional_row(row),
                "impact_lever_id": int(row["target_impact_lever_id"]),
                "parameter_bindings": json.dumps(
                    row["parameter_bindings"],
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                "audit_user": AUDIT_USER,
            },
        )


def _run_transaction(
    session: Session,
    *,
    canonical: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    canonical_rows: list[dict[str, Any]],
    apply: bool,
) -> dict[str, Any]:
    all_rows = _assert_protected_tables_unchanged(session, snapshot, lock=True)
    existing_target_rows = _target_rows(all_rows)
    all_target_version_rows = _all_target_version_rows(all_rows)
    inserted = False
    normalized_identity = False
    if all_target_version_rows:
        if len(existing_target_rows) != len(all_target_version_rows):
            message = "v4.1 already exists in a partial, inactive, or deleted state"
            raise RuntimeError(message)
        _assert_target_matches(existing_target_rows, canonical_rows)
        if not _target_identity_matches(existing_target_rows, canonical_rows):
            _normalize_target_identity(session, canonical_rows)
            normalized_identity = True
    else:
        _insert_rows(session, canonical_rows)
        inserted = True

    after_rows = _normalize_levers(_fetch_levers(session, lock=False))
    _assert_target_matches(_target_rows(after_rows), canonical_rows)
    if not _target_identity_matches(_target_rows(after_rows), canonical_rows):
        message = "v4.1 target IDs or audit principal differ from canonical state"
        raise RuntimeError(message)
    source_catalog, source_version, source_checksum = ModelImpactLeverService(
        session=session,
    ).load_active_catalog(catalog_version=SOURCE_CATALOG_VERSION)
    target_catalog, target_version, target_checksum = ModelImpactLeverService(
        session=session,
    ).load_active_catalog(catalog_version=TARGET_CATALOG_VERSION)
    if (
        source_version != SOURCE_CATALOG_VERSION
        or source_checksum != EXPECTED_SOURCE_CHECKSUM
        or len(source_catalog) != 21
    ):
        message = "v4.0 catalog changed during the v4.1 rollout"
        raise RuntimeError(message)
    if (
        target_version != TARGET_CATALOG_VERSION
        or target_checksum != canonical.get("hydrated_catalog_checksum")
        or len(target_catalog) != 21
    ):
        message = (
            "v4.1 hydrated read-back mismatch: "
            f"expected={canonical.get('hydrated_catalog_checksum')}, actual={target_checksum}"
        )
        raise RuntimeError(message)

    result = {
        "mode": "apply" if apply else "dry-run",
        "inserted": inserted,
        "normalized_identity": normalized_identity,
        "source_catalog_version": source_version,
        "source_catalog_checksum": source_checksum,
        "target_catalog_version": target_version,
        "target_catalog_checksum": target_checksum,
        "target_lever_count": len(target_catalog),
    }
    if apply:
        session.commit()
    else:
        session.rollback()
    return result


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = _parse_args(argv)
    try:
        canonical = _load_json(args.canonical)
        snapshot = _load_json(args.snapshot)
        canonical_rows, _ = _validate_documents(
            canonical,
            snapshot,
            snapshot_path=args.snapshot,
        )
        if args.validate_only:
            LOGGER.info(
                "v4.1 canonical validation passed: levers=%s checksum=%s",
                len(canonical_rows),
                canonical["hydrated_catalog_checksum"],
            )
            return 0

        from apps.common.configs.config import get_settings
        from apps.common.configs.database.sync_database.connection import get_sync_session

        get_settings()
        session = get_sync_session()
        try:
            result = _run_transaction(
                session,
                canonical=canonical,
                snapshot=snapshot,
                canonical_rows=canonical_rows,
                apply=args.apply,
            )
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    except Exception:
        LOGGER.exception("Model Impact Lever v4.1 rollout failed")
        return 1
    else:
        LOGGER.info("v4.1 rollout verification passed: %s", json.dumps(result, ensure_ascii=False))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
