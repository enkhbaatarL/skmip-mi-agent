# Copyright (c) 2026 SK Innovation E&S.

from __future__ import annotations

# ruff: noqa: C901, EM101, EM102, TRY003, TRY004
import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from openpyxl import load_workbook


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_PATH = (
    ROOT_DIR / "apps/agents/model_parameter_agent/resources/contracts/model-parameter-logical-table-catalog-v3.json"
)
CATALOG_SHEET = "catalog"
EXPECTED_HEADERS = (
    "catalogVersion",
    "modelFile",
    "parameterCode",
    "parameterDisplayName",
    "modelSheet",
    "logicalTableCode",
    "displayName",
    "modelTableKey",
    "tableRole",
    "sheetStatus",
    "sourceType",
    "displayOrder",
    "uiVisible",
    "modelParamId",
    "summaryScreenMode",
    "mappingNote",
    "screenVisible",
    "parameterUseYn",
)
FIELD_MAP = {
    "modelFile": "model_file",
    "parameterCode": "parameter_code",
    "parameterDisplayName": "parameter_display_name",
    "modelSheet": "model_sheet",
    "logicalTableCode": "logical_table_code",
    "displayName": "display_name",
    "modelTableKey": "model_table_key",
    "tableRole": "table_role",
    "sheetStatus": "sheet_status",
    "sourceType": "source_type",
    "displayOrder": "display_order",
    "uiVisible": "ui_visible",
    "modelParamId": "model_param_id",
    "summaryScreenMode": "summary_screen_mode",
    "mappingNote": "mapping_note",
    "screenVisible": "screen_visible",
    "parameterUseYn": "parameter_use_yn",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _boolean(value: object, *, field_name: str, row_number: int) -> bool:
    normalized = str(value or "").strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise ValueError(f"catalog row {row_number} has invalid {field_name}: {value!r}")


def _integer_or_none(value: object, *, field_name: str, row_number: int) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"catalog row {row_number} has invalid {field_name}: {value!r}")
    return value


def _text_or_none(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _canonical_entries_bytes(entries: list[dict[str, Any]]) -> bytes:
    return json.dumps(
        entries,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _catalog_rows(source_path: Path) -> tuple[str, list[dict[str, Any]]]:
    workbook = load_workbook(source_path, data_only=True, read_only=True)
    if CATALOG_SHEET not in workbook.sheetnames:
        raise ValueError(f"source workbook is missing the {CATALOG_SHEET!r} sheet")
    worksheet = workbook[CATALOG_SHEET]
    rows = worksheet.iter_rows(values_only=True)
    headers = tuple(next(rows))
    if headers != EXPECTED_HEADERS:
        raise ValueError(f"catalog headers differ: expected={EXPECTED_HEADERS!r}, actual={headers!r}")

    catalog_version: str | None = None
    entries: list[dict[str, Any]] = []
    for row_number, values in enumerate(rows, start=2):
        row = dict(zip(headers, values, strict=True))
        if all(value is None for value in values):
            continue
        if row["displayName"] is None:
            raise ValueError(f"catalog row {row_number} has no displayName")
        row_catalog_version = _text_or_none(row["catalogVersion"])
        if row_catalog_version is None:
            raise ValueError(f"catalog row {row_number} has no catalogVersion")
        if catalog_version is None:
            catalog_version = row_catalog_version
        elif row_catalog_version != catalog_version:
            raise ValueError(
                f"catalog row {row_number} has catalogVersion={row_catalog_version!r}; expected {catalog_version!r}",
            )

        entry: dict[str, Any] = {}
        for source_field, target_field in FIELD_MAP.items():
            raw_value = row[source_field]
            if source_field in {"uiVisible", "screenVisible"}:
                entry[target_field] = _boolean(
                    raw_value,
                    field_name=source_field,
                    row_number=row_number,
                )
            elif source_field in {"displayOrder", "modelParamId"}:
                entry[target_field] = _integer_or_none(
                    raw_value,
                    field_name=source_field,
                    row_number=row_number,
                )
            else:
                entry[target_field] = _text_or_none(raw_value)
        entries.append(entry)

    if catalog_version is None:
        raise ValueError("catalog sheet has no data rows")
    return catalog_version, entries


def build_catalog_document(source_path: Path) -> dict[str, Any]:
    catalog_version, entries = _catalog_rows(source_path)
    logical_keys = {(entry["model_file"], entry["model_sheet"], entry["logical_table_code"]) for entry in entries}
    mapped_entries = [entry for entry in entries if entry["model_param_id"] is not None]
    role_counts = {
        role: sum(entry["table_role"] == role for entry in mapped_entries)
        for role in ("WRITE_TARGET", "RELATED", "REFERENCE")
    }
    expected_counts = {
        "entry_count": len(entries),
        "logical_table_count": len(logical_keys),
        "mapped_entry_count": len(mapped_entries),
        "mapped_parameter_count": len({entry["model_param_id"] for entry in mapped_entries}),
        "write_target_count": role_counts["WRITE_TARGET"],
        "related_count": role_counts["RELATED"],
        "reference_count": role_counts["REFERENCE"],
        "screen_visible_entry_count": sum(entry["screen_visible"] for entry in entries),
        "ui_visible_entry_count": sum(entry["ui_visible"] for entry in entries),
    }
    return {
        "schema_version": "model-parameter-logical-table-catalog-v1",
        "catalog_version": catalog_version,
        "source": {
            "workbook_name": source_path.name,
            "workbook_sha256": _sha256(source_path),
            "sheet": CATALOG_SHEET,
        },
        "ui_hierarchy": ["model_file", "parameter_display_name", "display_name"],
        "machine_target_note": (
            "Join catalog.model_param_id to tmm_mi_model_param_m.model_param_id. "
            "Keep model_table_key as the machine write-target key and render display_name in the UI."
        ),
        "expected_counts": expected_counts,
        "entries_sha256": hashlib.sha256(_canonical_entries_bytes(entries)).hexdigest(),
        "entries": entries,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert the reviewed logical-table workbook to canonical JSON")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args()

    source_path = args.source.expanduser().resolve()
    output_path = args.output.expanduser().resolve()
    document = build_catalog_document(source_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
