from __future__ import annotations

# Copyright (c) 2026 SK Innovation E&S.
import argparse
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
import json
import logging
from pathlib import Path
import sys
from typing import Any

from sqlalchemy import text


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.model_parameter.apply_model_parameter_v4 import (  # noqa: E402
    IMPACT_LEVER_COLUMNS,
    MAPPING_COLUMNS,
    MASTER_COLUMNS,
    _database_digest,
    _decode_json_array,
    _fetch_levers,
    _fetch_mappings,
    _fetch_master,
    _fetch_templates,
    _normalize,
    _parse_template_json,
    _semantic_digest,
)


LOGGER = logging.getLogger("model_parameter_v4_external_snapshot")
SNAPSHOT_PATH = ROOT_DIR / "scripts/model_parameter/snapshots/external_dev_before_model_parameter_v4_20260813.json"
TEMPLATE_COLUMNS = (
    "scenario_dimension_template_id",
    "event_type_l2_id",
    "template_json",
    "del_yn",
)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Capture the configured external development database's pre-v4 Model Parameter state in a read-only "
            "transaction. The dated evidence file is created exclusively and is never overwritten."
        ),
    )
    return parser.parse_args(argv)


def _normalize_json_value(value: Any, *, column: str | None = None) -> Any:  # noqa: ANN401
    normalized = _normalize(value, column=column)
    if isinstance(normalized, date | datetime):
        return normalized.isoformat()
    if isinstance(normalized, Mapping):
        return {str(key): _normalize_json_value(item) for key, item in normalized.items()}
    if isinstance(normalized, list | tuple):
        return [_normalize_json_value(item) for item in normalized]
    return normalized


def _normalize_rows(
    rows: list[dict[str, Any]],
    *,
    columns: Sequence[str],
) -> list[dict[str, Any]]:
    return [{column: _normalize_json_value(row.get(column), column=column) for column in columns} for row in rows]


def _normalize_levers(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized_rows = _normalize_rows(rows, columns=IMPACT_LEVER_COLUMNS)
    for row in normalized_rows:
        lever_code = str(row["lever_code"])
        row["parameter_bindings"] = _decode_json_array(
            row.get("parameter_bindings"),
            label=f"{lever_code}.parameter_bindings",
        )
    return normalized_rows


def _normalize_active_templates(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    active_rows = [row for row in rows if str(row.get("del_yn")) == "N"]
    normalized_rows = _normalize_rows(active_rows, columns=TEMPLATE_COLUMNS)
    for row in normalized_rows:
        event_type_l2_id = int(row["event_type_l2_id"])
        row["template_json"] = _parse_template_json(
            row.get("template_json"),
            event_type_l2_id=event_type_l2_id,
        )
    return normalized_rows


def _build_snapshot(
    master_rows: list[dict[str, Any]],
    mapping_rows: list[dict[str, Any]],
    lever_rows: list[dict[str, Any]],
    template_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    normalized_master = _normalize_rows(master_rows, columns=MASTER_COLUMNS)
    normalized_mappings = _normalize_rows(mapping_rows, columns=MAPPING_COLUMNS)
    normalized_levers = _normalize_levers(lever_rows)
    normalized_templates = _normalize_active_templates(template_rows)
    return {
        "snapshot_version": 2,
        "snapshot_name": "external-dev-before-model-parameter-v4-20260813",
        "captured_at_utc": datetime.now(UTC).isoformat(),
        "source": (
            "configured external development metadata database (credentials, username, and host intentionally omitted)"
        ),
        "capture_mode": "read-only transaction with unconditional rollback",
        "master_count": len(normalized_master),
        "mapping_count": len(normalized_mappings),
        "impact_lever_count": len(normalized_levers),
        "scenario_dimension_template_count": len(normalized_templates),
        "table_digests": {
            "master_sha256": _semantic_digest(normalized_master),
            "dimension_mappings_sha256": _semantic_digest(normalized_mappings),
            "impact_levers_sha256": _semantic_digest(normalized_levers),
            "scenario_dimension_templates_sha256": _semantic_digest(normalized_templates),
        },
        "core_database_sha256": _database_digest(
            normalized_master,
            normalized_mappings,
            normalized_levers,
        ),
        "master": normalized_master,
        "dimension_mappings": normalized_mappings,
        "impact_levers": normalized_levers,
        "scenario_dimension_templates": normalized_templates,
    }


def _write_snapshot_exclusive(snapshot: Mapping[str, Any]) -> None:
    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SNAPSHOT_PATH.open("x", encoding="utf-8") as output:
        json.dump(snapshot, output, ensure_ascii=False, indent=2)
        output.write("\n")


def capture() -> Path:
    """Capture the configured database without retaining a transaction or connection."""
    if SNAPSHOT_PATH.exists():
        message = f"refusing to overwrite existing external DB evidence: {SNAPSHOT_PATH}"
        raise FileExistsError(message)

    from apps.common.configs.config import get_settings
    from apps.common.configs.database.sync_database.connection import get_sync_session

    get_settings()
    session = get_sync_session()
    try:
        session.execute(text("SET TRANSACTION READ ONLY"))
        master_rows = _fetch_master(session, lock=False)
        mapping_rows = _fetch_mappings(session, lock=False)
        lever_rows = _fetch_levers(session, lock=False)
        template_rows = _fetch_templates(session, lock=False)
    finally:
        try:
            session.rollback()
        finally:
            session.close()

    snapshot = _build_snapshot(master_rows, mapping_rows, lever_rows, template_rows)
    _write_snapshot_exclusive(snapshot)
    return SNAPSHOT_PATH


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    _parse_args(argv)
    try:
        output_path = capture()
    except Exception:
        LOGGER.exception("Model Parameter v4 external development snapshot capture failed")
        return 1
    LOGGER.info("Model Parameter v4 external development snapshot captured: path=%s", output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
