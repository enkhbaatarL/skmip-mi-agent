from __future__ import annotations

import argparse
from pathlib import Path
import re
from typing import Any

from openpyxl import load_workbook

from apps.agents.scenario_group_agent.persistence.scenario_service import (
    ScenarioService,
)


_COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "event_type_l2_id": (
        "eventtypel2id",
        "이벤트유형l2id",
        "event유형l2id",
    ),
    "event_type_definition": (
        "eventtypedefinition",
        "이벤트유형정의",
        "정의",
    ),
    "lng_price_impact_examples": (
        "lngpriceimpactexamples",
        "lng가격영향대표사례",
        "lng가격영향",
        "대표사례",
    ),
    "dim_key": ("dimkey", "dimensionid", "분기키"),
    "label": ("label", "항목", "분기항목"),
    "description": ("description", "설명"),
    "criteria": ("기준", "criteria"),
    "reference": ("참고", "reference"),
    "required": ("required", "필수여부", "필수"),
    "value_enums": ("valueenums", "값예시", "value예시"),
    "display_order": ("displayorder", "표시순서", "순서"),
}


def _normalize_header(value: object) -> str:
    return re.sub(r"[\s_\-()/·]+", "", str(value or "")).lower()


def _column_map(headers: list[object]) -> dict[str, int]:
    normalized = {_normalize_header(header): index for index, header in enumerate(headers) if str(header or "").strip()}
    resolved: dict[str, int] = {}
    for field, aliases in _COLUMN_ALIASES.items():
        for alias in aliases:
            index = normalized.get(_normalize_header(alias))
            if index is not None:
                resolved[field] = index
                break
    return resolved


def _cell(row: tuple[object, ...], columns: dict[str, int], field: str) -> object:
    index = columns.get(field)
    return row[index] if index is not None and index < len(row) else None


def _text(value: object) -> str:
    return str(value or "").strip()


def _split_values(value: object) -> list[str]:
    if isinstance(value, (list, tuple)):
        return [_text(item) for item in value if _text(item)]
    return [item.strip() for item in re.split(r"[\n,|]+", _text(value)) if item.strip()]


def _as_bool(value: object) -> bool:
    return _text(value).lower() in {"y", "yes", "true", "1", "필수"}


def load_template_updates(workbook_path: Path) -> list[dict[str, Any]]:
    workbook = load_workbook(workbook_path, read_only=True, data_only=True)
    updates: dict[int, dict[str, Any]] = {}
    for worksheet in workbook.worksheets:
        rows = worksheet.iter_rows(values_only=True)
        headers = list(next(rows, ()))
        columns = _column_map(headers)
        if "event_type_l2_id" not in columns:
            continue
        for row in rows:
            raw_event_type_l2_id = _cell(
                row,
                columns,
                "event_type_l2_id",
            )
            if raw_event_type_l2_id in {None, ""}:
                continue
            event_type_l2_id = int(raw_event_type_l2_id)
            update = updates.setdefault(
                event_type_l2_id,
                {
                    "event_type_l2_id": event_type_l2_id,
                    "event_type_definition": "",
                    "lng_price_impact_examples": "",
                    "template_json": [],
                },
            )
            definition = _text(
                _cell(row, columns, "event_type_definition"),
            )
            examples = _text(
                _cell(row, columns, "lng_price_impact_examples"),
            )
            if definition:
                update["event_type_definition"] = definition
            if examples:
                update["lng_price_impact_examples"] = examples

            dim_key = _text(_cell(row, columns, "dim_key"))
            if not dim_key:
                continue
            label = _text(_cell(row, columns, "label")) or dim_key
            explicit_description = _text(
                _cell(row, columns, "description"),
            )
            description_parts = [
                label,
                _text(_cell(row, columns, "criteria")),
                _text(_cell(row, columns, "reference")),
            ]
            description = explicit_description or " - ".join(part for part in description_parts if part)
            raw_order = _cell(row, columns, "display_order")
            update["template_json"].append(
                {
                    "dim_key": dim_key,
                    "label": label,
                    "description": description,
                    "required": _as_bool(
                        _cell(row, columns, "required"),
                    ),
                    "value_enums": _split_values(
                        _cell(row, columns, "value_enums"),
                    ),
                    "display_order": (
                        int(raw_order) if raw_order not in {None, ""} else len(update["template_json"]) + 1
                    ),
                },
            )
    return list(updates.values())


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scenario Template Excel domain knowledge migration",
    )
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--user-id", type=int, default=0)
    args = parser.parse_args()

    updates = load_template_updates(args.workbook)
    if not updates:
        raise ValueError("No Scenario Template rows were found in the workbook")
    service = ScenarioService()
    for update in updates:
        service.update_template_domain_knowledge(
            event_type_l2_id=update["event_type_l2_id"],
            event_type_definition=update["event_type_definition"],
            lng_price_impact_examples=update["lng_price_impact_examples"],
            template_json=update["template_json"],
            user_id=args.user_id,
        )


if __name__ == "__main__":
    main()
