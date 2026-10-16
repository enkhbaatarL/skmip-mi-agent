from __future__ import annotations

# Copyright (c) 2026 SK Innovation E&S.
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[2]
SOURCE_SNAPSHOT_PATH = (
    ROOT_DIR / "scripts/model_parameter/snapshots/external_dev_before_model_impact_lever_v4_1_20261003.json"
)
LEGACY_MAPPING_PATH = ROOT_DIR / "scripts/model_parameter/model-parameter-canonical-v1.json"
OUTPUT_PATH = ROOT_DIR / "scripts/model_parameter/model-parameter-canonical-v4.1-0050.json"
AUDIT_USER = "model-parameter-canal-split-v0050"

EXPECTED_SOURCE_IDS = frozenset(range(1, 25))
EXPECTED_FINAL_IDS = frozenset(range(1, 27))
EXPECTED_ACTIVE_IDS = frozenset(
    {4, 6, 7, 8, 11, 12, 13, 14, 15, 16, 17, 18, 20, 22, 23, 24, 25, 26},
)

NEW_MASTER_ROWS: tuple[dict[str, Any], ...] = (
    {
        "model_param_id": 25,
        "use_yn": "Y",
        "parameter_name": "Suez Canal Cost",
        "parameter_hint": (
            "Suez 운하·연도별 통항료의 최종 절대값이다. value는 $/crossing "
            "단위이며 0 이상이다. ShippingCostInput의 Suez 블록만 사용한다."
        ),
        "model_file": "Trade",
        "model_sheet": "ShippingCostInput",
        "model_table": "table4",
        "semantic_axes": (
            "slot=Canal(Suez), Year(YYYY, 2026~2030); "
            "source=C:RE Base Case ($/crossing); "
            "target=F:User Input Absolute Value ($/crossing); "
            "block=Suez rows 38~46; mode=C3=Absolute"
        ),
        "basecase_read_mode": "fixed_columns",
        "basecase_header_row": 38,
        "basecase_data_start_row": 39,
        "basecase_column_roles": "A:Canal/Year Key,B:Year,C:RE Base Case ($/crossing)",
        "basecase_row_filter": None,
        "basecase_year_row": None,
        "basecase_month_row": None,
        "basecase_period_row": None,
        "basecase_value_start_col": None,
        "basecase_value_end_col": None,
        "basecase_stop_rule": "stop_when_all_key_columns_empty",
        "crt_usr_logn_id": AUDIT_USER,
        "crt_dtm": None,
        "mod_usr_logn_id": AUDIT_USER,
        "mod_dtm": None,
        "del_yn": "N",
    },
    {
        "model_param_id": 26,
        "use_yn": "Y",
        "parameter_name": "Panama Canal Cost",
        "parameter_hint": (
            "Panama 운하·연도별 통항료의 최종 절대값이다. value는 $/crossing "
            "단위이며 0 이상이다. ShippingCostInput의 Panama 블록만 사용한다."
        ),
        "model_file": "Trade",
        "model_sheet": "ShippingCostInput",
        "model_table": "table5",
        "semantic_axes": (
            "slot=Canal(Panama), Year(YYYY, 2026~2030); "
            "source=C:RE Base Case ($/crossing); "
            "target=F:User Input Absolute Value ($/crossing); "
            "block=Panama rows 49~57; mode=C3=Absolute"
        ),
        "basecase_read_mode": "fixed_columns",
        "basecase_header_row": 49,
        "basecase_data_start_row": 50,
        "basecase_column_roles": "A:Canal/Year Key,B:Year,C:RE Base Case ($/crossing)",
        "basecase_row_filter": None,
        "basecase_year_row": None,
        "basecase_month_row": None,
        "basecase_period_row": None,
        "basecase_value_start_col": None,
        "basecase_value_end_col": None,
        "basecase_stop_rule": "stop_when_all_key_columns_empty",
        "crt_usr_logn_id": AUDIT_USER,
        "crt_dtm": None,
        "mod_usr_logn_id": AUDIT_USER,
        "mod_dtm": None,
        "del_yn": "N",
    },
)


def _load_json(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        message = f"Expected JSON object: {path}"
        raise TypeError(message)
    return document


def _semantic_sha256(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_document() -> dict[str, Any]:
    snapshot = _load_json(SOURCE_SNAPSHOT_PATH)
    legacy_mapping = _load_json(LEGACY_MAPPING_PATH)
    source_master = snapshot.get("master")
    if not isinstance(source_master, list) or any(not isinstance(row, dict) for row in source_master):
        message = "v4.1 pre-release snapshot master must be an object array"
        raise TypeError(message)

    source_ids = {int(row["model_param_id"]) for row in source_master}
    if source_ids != EXPECTED_SOURCE_IDS:
        message = f"Unexpected source master IDs: {sorted(source_ids)}"
        raise ValueError(message)

    master = [dict(row) for row in source_master]
    for row in master:
        if int(row["model_param_id"]) in {13, 14}:
            row["basecase_value_end_col"] = "CL"
            row["mod_usr_logn_id"] = "model-parameter-master-v0044"
            row["mod_dtm"] = None
    master.extend(dict(row) for row in NEW_MASTER_ROWS)
    master.sort(key=lambda row: int(row["model_param_id"]))

    final_ids = {int(row["model_param_id"]) for row in master}
    if final_ids != EXPECTED_FINAL_IDS:
        message = f"Unexpected final master IDs: {sorted(final_ids)}"
        raise ValueError(message)
    active_ids = {int(row["model_param_id"]) for row in master if row.get("use_yn") == "Y" and row.get("del_yn") == "N"}
    if active_ids != EXPECTED_ACTIVE_IDS:
        message = f"Unexpected active master IDs: {sorted(active_ids)}"
        raise ValueError(message)
    names = [str(row["parameter_name"]) for row in master]
    if len(names) != len(set(names)):
        message = "Current master parameter names must be unique"
        raise ValueError(message)

    mappings = legacy_mapping.get("dimension_mappings")
    if not isinstance(mappings, list) or len(mappings) != 129:
        message = "Shared legacy mapping authority must contain 129 rows"
        raise ValueError(message)

    active_names = [
        str(row["parameter_name"]) for row in master if row.get("use_yn") == "Y" and row.get("del_yn") == "N"
    ]
    inactive_names = [
        str(row["parameter_name"]) for row in master if row.get("use_yn") == "N" and row.get("del_yn") == "N"
    ]
    return {
        "canonical_version": "model-parameter-canonical-v4.1-0050",
        "generated_from_snapshot": str(SOURCE_SNAPSHOT_PATH.relative_to(ROOT_DIR)),
        "source_snapshot_sha256": hashlib.sha256(SOURCE_SNAPSHOT_PATH.read_bytes()).hexdigest(),
        "audit_user": AUDIT_USER,
        "runtime_scope": {
            "master": "0050 authority",
            "dimension_mappings": "protected shared v1/v3 authority; unchanged by v0050",
            "dimension_mapping_authority": str(LEGACY_MAPPING_PATH.relative_to(ROOT_DIR)),
        },
        "active_parameter_names": active_names,
        "inactive_parameter_names": inactive_names,
        "master_count": len(master),
        "mapping_count": len(mappings),
        "expected_counts": {
            "master": len(master),
            "active_parameters": len(active_names),
            "inactive_parameters": len(inactive_names),
            "dimension_mappings": len(mappings),
        },
        "legacy_dimension_mapping_sha256": _semantic_sha256(mappings),
        "master": master,
        "source_migration_revision": "b4c9d2e50050",
        "source_migration": ("skmip-mi-agent-mgmt/migrations/versions/0050_split_canal_cost_parameters.py"),
    }


def main() -> None:
    OUTPUT_PATH.write_text(
        json.dumps(build_document(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
