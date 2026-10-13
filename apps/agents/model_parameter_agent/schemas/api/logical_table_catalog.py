# Copyright (c) 2026 SK Innovation E&S.

from __future__ import annotations

from typing import Literal

from pydantic import Field

from apps.persistence.schema_base import ApiModel


class LogicalTableItem(ApiModel):
    logical_table_code: str
    display_name: str
    model_sheet: str
    model_table_key: str | None = None
    table_role: Literal["WRITE_TARGET", "RELATED", "REFERENCE"]
    sheet_status: Literal["VISIBLE", "HIDDEN", "NOT_IN_WORKBOOK"]
    source_type: Literal["WORKBOOK", "SERVER_LUT", "EXTERNAL_LINK"]
    display_order: int
    ui_visible: bool
    screen_visible: bool
    summary_screen_mode: Literal["입력+조회", "조회", "미표시"]
    mapping_note: str


class LogicalTableParameter(ApiModel):
    model_param_id: int
    parameter_code: str
    parameter_name: str
    use_yn: Literal["Y", "N"]
    tables: list[LogicalTableItem] = Field(default_factory=list)


class LogicalTableFile(ApiModel):
    model_file: Literal["Demand", "Supply", "Trade"]
    parameters: list[LogicalTableParameter] = Field(default_factory=list)


class LogicalTableCatalogData(ApiModel):
    catalog_version: str
    hierarchy: list[str] = Field(default_factory=list)
    source_workbook_sha256: str
    entry_count: int
    logical_table_count: int
    mapped_entry_count: int
    parameter_count: int
    files: list[LogicalTableFile] = Field(default_factory=list)


class LogicalTableCatalogOut(ApiModel):
    status: Literal["success", "error"] = "success"
    message: str = "model parameter logical table catalog retrieved"
    data: LogicalTableCatalogData


__all__ = [
    "LogicalTableCatalogData",
    "LogicalTableCatalogOut",
    "LogicalTableFile",
    "LogicalTableItem",
    "LogicalTableParameter",
]
