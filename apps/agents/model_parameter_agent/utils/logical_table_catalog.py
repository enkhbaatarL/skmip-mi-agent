# Copyright (c) 2026 SK Innovation E&S.

from __future__ import annotations

# ruff: noqa: EM101, EM102, TRY003
import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode


PACKAGE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_LOGICAL_TABLE_CATALOG_PATH = PACKAGE_DIR / "resources/contracts/model-parameter-logical-table-catalog-v4.json"
EXPECTED_CATALOG_VERSION = "20261016-v4-canal-split"
EXPECTED_SOURCE_WORKBOOK_SHA256 = "5fce745227c6eeada73c63070b3044776224b5e08d74af7725b019e5c712bc24"
EXPECTED_ENTRIES_SHA256 = "3bedbc3292cfc70fcc609017987d2d0f5813a4cacfb19abbcb9572966dc25383"
EXPECTED_COUNTS = {
    "entry_count": 199,
    "logical_table_count": 193,
    "mapped_entry_count": 54,
    "mapped_parameter_count": 23,
    "write_target_count": 23,
    "related_count": 9,
    "reference_count": 22,
    "screen_visible_entry_count": 105,
    "ui_visible_entry_count": 37,
}

TableRole = Literal["WRITE_TARGET", "RELATED", "REFERENCE"]
SheetStatus = Literal["VISIBLE", "HIDDEN", "NOT_IN_WORKBOOK"]
SourceType = Literal["WORKBOOK", "SERVER_LUT", "EXTERNAL_LINK"]
SummaryScreenMode = Literal["입력+조회", "조회", "미표시"]
UseYn = Literal["Y", "N"]


def _catalog_error(detail: str) -> MIBaseError:
    return MIBaseError(ErrorCode.INVALID_REQUEST, detail=detail)


def _canonical_entries_bytes(entries: tuple[LogicalTableCatalogEntry, ...]) -> bytes:
    payload = [entry.model_dump(mode="json") for entry in entries]
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class LogicalTableCatalogSource(_FrozenModel):
    workbook_name: str
    workbook_sha256: str
    sheet: Literal["catalog"]


class LogicalTableCatalogCounts(_FrozenModel):
    entry_count: int = Field(ge=1)
    logical_table_count: int = Field(ge=1)
    mapped_entry_count: int = Field(ge=1)
    mapped_parameter_count: int = Field(ge=1)
    write_target_count: int = Field(ge=1)
    related_count: int = Field(ge=0)
    reference_count: int = Field(ge=0)
    screen_visible_entry_count: int = Field(ge=0)
    ui_visible_entry_count: int = Field(ge=0)


class LogicalTableCatalogEntry(_FrozenModel):
    model_file: Literal["Demand", "Supply", "Trade", "Output"]
    parameter_code: str | None = None
    parameter_display_name: str | None = None
    model_sheet: str
    logical_table_code: str
    display_name: str
    model_table_key: str | None = None
    table_role: TableRole | None = None
    sheet_status: SheetStatus
    source_type: SourceType
    display_order: int | None = Field(default=None, ge=1)
    ui_visible: bool
    model_param_id: int | None = Field(default=None, ge=1)
    summary_screen_mode: SummaryScreenMode
    mapping_note: str
    screen_visible: bool
    parameter_use_yn: UseYn | None = None

    @model_validator(mode="after")
    def validate_mapping_shape(self) -> LogicalTableCatalogEntry:
        parameter_fields = (
            self.parameter_code,
            self.parameter_display_name,
            self.model_param_id,
            self.table_role,
            self.display_order,
            self.parameter_use_yn,
        )
        if self.model_param_id is None:
            if any(value is not None for value in parameter_fields):
                raise ValueError("unmapped logical table must not carry parameter mapping fields")
            if self.model_table_key is not None or self.ui_visible:
                raise ValueError("unmapped logical table must not carry a machine target or uiVisible=true")
            return self

        if any(value is None for value in parameter_fields):
            raise ValueError("mapped logical table must carry every parameter mapping field")
        if self.table_role == "WRITE_TARGET":
            if self.model_table_key is None:
                raise ValueError("WRITE_TARGET must carry model_table_key")
        elif self.model_table_key is not None:
            raise ValueError("RELATED/REFERENCE must not carry model_table_key")
        if self.ui_visible and (not self.screen_visible or self.parameter_use_yn != "Y"):
            raise ValueError("uiVisible=true requires screenVisible=true and parameterUseYn=Y")
        return self


class LogicalTableCatalog(_FrozenModel):
    schema_version: Literal["model-parameter-logical-table-catalog-v1"]
    catalog_version: str
    source: LogicalTableCatalogSource
    ui_hierarchy: tuple[str, str, str]
    machine_target_note: str
    expected_counts: LogicalTableCatalogCounts
    entries_sha256: str
    entries: tuple[LogicalTableCatalogEntry, ...]

    @model_validator(mode="after")
    def validate_release(self) -> LogicalTableCatalog:  # noqa: C901
        if self.catalog_version != EXPECTED_CATALOG_VERSION:
            raise ValueError(
                f"catalog_version must be {EXPECTED_CATALOG_VERSION!r}; got {self.catalog_version!r}",
            )
        if self.source.workbook_sha256 != EXPECTED_SOURCE_WORKBOOK_SHA256:
            raise ValueError("logical-table source workbook checksum differs from the reviewed v4 source input")
        if self.ui_hierarchy != ("model_file", "parameter_display_name", "display_name"):
            raise ValueError("UI hierarchy must be model file -> parameter name -> logical table display name")

        mapped_entries = [entry for entry in self.entries if entry.model_param_id is not None]
        logical_keys = {(entry.model_file, entry.model_sheet, entry.logical_table_code) for entry in self.entries}
        actual_counts = {
            "entry_count": len(self.entries),
            "logical_table_count": len(logical_keys),
            "mapped_entry_count": len(mapped_entries),
            "mapped_parameter_count": len({entry.model_param_id for entry in mapped_entries}),
            "write_target_count": sum(entry.table_role == "WRITE_TARGET" for entry in mapped_entries),
            "related_count": sum(entry.table_role == "RELATED" for entry in mapped_entries),
            "reference_count": sum(entry.table_role == "REFERENCE" for entry in mapped_entries),
            "screen_visible_entry_count": sum(entry.screen_visible for entry in self.entries),
            "ui_visible_entry_count": sum(entry.ui_visible for entry in self.entries),
        }
        declared_counts = self.expected_counts.model_dump()
        if declared_counts != EXPECTED_COUNTS or actual_counts != EXPECTED_COUNTS:
            raise ValueError(
                "logical-table catalog counts differ from the reviewed v4 release: "
                f"declared={declared_counts}, actual={actual_counts}",
            )

        actual_entries_sha256 = hashlib.sha256(_canonical_entries_bytes(self.entries)).hexdigest()
        if self.entries_sha256 != EXPECTED_ENTRIES_SHA256 or actual_entries_sha256 != EXPECTED_ENTRIES_SHA256:
            raise ValueError(
                "logical-table catalog entries checksum differs: "
                f"expected={EXPECTED_ENTRIES_SHA256}, declared={self.entries_sha256}, "
                f"actual={actual_entries_sha256}",
            )

        parameter_state: dict[int, tuple[str, str, str, UseYn]] = {}
        orders_by_parameter: dict[int, set[int]] = {}
        write_targets_by_parameter: dict[int, int] = {}
        row_signatures: set[tuple[object, ...]] = set()
        for entry in self.entries:
            signature = (
                entry.model_file,
                entry.model_sheet,
                entry.logical_table_code,
                entry.model_param_id,
                entry.table_role,
            )
            if signature in row_signatures:
                raise ValueError(f"logical-table catalog has a duplicate mapping row: {signature!r}")
            row_signatures.add(signature)
            if entry.model_param_id is None:
                continue
            if (
                entry.parameter_code is None
                or entry.parameter_display_name is None
                or entry.parameter_use_yn is None
                or entry.display_order is None
            ):
                raise ValueError(
                    f"model_param_id={entry.model_param_id} has incomplete parameter metadata",
                )
            current_state = (
                entry.model_file,
                entry.parameter_code,
                entry.parameter_display_name,
                entry.parameter_use_yn,
            )
            previous_state = parameter_state.setdefault(entry.model_param_id, current_state)
            if previous_state != current_state:
                raise ValueError(
                    f"model_param_id={entry.model_param_id} has inconsistent parameter metadata",
                )
            orders = orders_by_parameter.setdefault(entry.model_param_id, set())
            if entry.display_order in orders:
                raise ValueError(
                    f"model_param_id={entry.model_param_id} has duplicate display_order={entry.display_order}",
                )
            orders.add(entry.display_order)
            if entry.table_role == "WRITE_TARGET":
                write_targets_by_parameter[entry.model_param_id] = (
                    write_targets_by_parameter.get(entry.model_param_id, 0) + 1
                )
        if set(write_targets_by_parameter) != set(parameter_state):
            raise ValueError("every mapped parameter must have at least one WRITE_TARGET")
        return self


def load_logical_table_catalog(
    path: Path = DEFAULT_LOGICAL_TABLE_CATALOG_PATH,
) -> LogicalTableCatalog:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
        return LogicalTableCatalog.model_validate(document)
    except OSError as exc:
        raise _catalog_error(f"Unable to read logical-table catalog: {path}") from exc
    except ValueError as exc:
        raise _catalog_error(f"Invalid logical-table catalog {path}: {exc}") from exc


__all__ = [
    "DEFAULT_LOGICAL_TABLE_CATALOG_PATH",
    "EXPECTED_CATALOG_VERSION",
    "EXPECTED_ENTRIES_SHA256",
    "LogicalTableCatalog",
    "LogicalTableCatalogEntry",
    "load_logical_table_catalog",
]
