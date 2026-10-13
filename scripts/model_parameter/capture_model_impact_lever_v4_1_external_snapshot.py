from __future__ import annotations

# Copyright (c) 2026 SK Innovation E&S.
import argparse
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
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
    MAPPING_COLUMNS,
    MASTER_COLUMNS,
    _database_digest,
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


LOGGER = logging.getLogger("model_impact_lever_v4_1_external_snapshot")
SNAPSHOT_PATH = ROOT_DIR / "scripts/model_parameter/snapshots/external_dev_before_model_impact_lever_v4_1_20261003.json"


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Capture the configured external-development DB immediately before the "
            "side-by-side v4.1 Impact Lever rollout. The read-only evidence file is "
            "created exclusively and is never overwritten."
        ),
    )
    return parser.parse_args(argv)


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
    v4_0_rows = [
        row
        for row in normalized_levers
        if row["catalog_version"] == "v4.0" and row["use_yn"] == "Y" and row["del_yn"] == "N"
    ]
    return {
        "snapshot_version": 1,
        "snapshot_name": "external-dev-before-model-impact-lever-v4.1-20261003",
        "captured_at_utc": datetime.now(UTC).isoformat(),
        "source": (
            "configured external development metadata database (credentials, username, and host intentionally omitted)"
        ),
        "capture_mode": "read-only transaction with unconditional rollback",
        "master_count": len(normalized_master),
        "mapping_count": len(normalized_mappings),
        "impact_lever_count": len(normalized_levers),
        "v4_0_active_impact_lever_count": len(v4_0_rows),
        "scenario_dimension_template_count": len(normalized_templates),
        "table_digests": {
            "master_sha256": _semantic_digest(normalized_master),
            "dimension_mappings_sha256": _semantic_digest(normalized_mappings),
            "impact_levers_sha256": _semantic_digest(normalized_levers),
            "v4_0_active_impact_levers_sha256": _semantic_digest(v4_0_rows),
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

    snapshot = _build_snapshot(
        master_rows,
        mapping_rows,
        lever_rows,
        template_rows,
    )
    _write_snapshot_exclusive(snapshot)
    return SNAPSHOT_PATH


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    _parse_args(argv)
    try:
        output_path = capture()
    except Exception:
        LOGGER.exception("Model Impact Lever v4.1 snapshot capture failed")
        return 1
    LOGGER.info("Model Impact Lever v4.1 snapshot captured: path=%s", output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
