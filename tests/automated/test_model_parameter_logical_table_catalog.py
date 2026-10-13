# Copyright (c) 2026 SK Innovation E&S.
# ruff: noqa: S101

from __future__ import annotations

from pathlib import Path

from fastapi.routing import APIRoute
from openpyxl import load_workbook

from apps.agents.model_parameter_agent.api import router
from apps.agents.model_parameter_agent.presentation import build_logical_table_catalog_data
from apps.agents.model_parameter_agent.utils.logical_table_catalog import (
    EXPECTED_CATALOG_VERSION,
    EXPECTED_COUNTS,
    EXPECTED_ENTRIES_SHA256,
    EXPECTED_SOURCE_WORKBOOK_SHA256,
    load_logical_table_catalog,
)
from apps.agents.model_parameter_agent.utils.proposal_capabilities import (
    load_proposal_capability_contract,
)


RESOURCE_DIR = Path(__file__).resolve().parents[2] / "apps/agents/model_parameter_agent/resources"
FINAL_WORKBOOK_DIR = RESOURCE_DIR / "basecase_v4/new-bc-v2"


def test_reviewed_logical_table_catalog_is_checksum_and_count_pinned() -> None:
    catalog = load_logical_table_catalog()

    assert catalog.catalog_version == EXPECTED_CATALOG_VERSION
    assert catalog.source.workbook_sha256 == EXPECTED_SOURCE_WORKBOOK_SHA256
    assert catalog.entries_sha256 == EXPECTED_ENTRIES_SHA256
    assert catalog.expected_counts.model_dump() == EXPECTED_COUNTS
    assert catalog.ui_hierarchy == ("model_file", "parameter_display_name", "display_name")


def test_final_workbook_summaries_match_catalog_table_names_and_visibility() -> None:
    catalog = load_logical_table_catalog()
    expected_counts = {"Demand": 80, "Supply": 31, "Trade": 64}

    for model_file in ("Demand", "Supply", "Trade"):
        path = FINAL_WORKBOOK_DIR / f"{model_file} Model_Input.xlsm"
        workbook = load_workbook(path, read_only=True, data_only=True, keep_links=False)
        try:
            rows = list(workbook["SUMMARY"].iter_rows(values_only=True))
        finally:
            workbook.close()

        header_index = next(
            index
            for index, row in enumerate(rows)
            if row[:3] == ("시트", "영문 표 이름", "화면")
        )
        summary_rows: set[tuple[str, str, bool]] = set()
        for row in rows[header_index + 1 :]:
            model_sheet, display_name, screen_mode = row[:3]
            if not model_sheet or not display_name:
                continue
            model_sheets = str(model_sheet).split(" / ")
            summary_rows.update(
                (sheet, str(display_name), str(screen_mode) != "미표시")
                for sheet in model_sheets
            )

        catalog_rows = {
            (entry.model_sheet, entry.display_name, entry.screen_visible)
            for entry in catalog.entries
            if entry.model_file == model_file
        }
        assert len(summary_rows) == expected_counts[model_file]
        assert summary_rows == catalog_rows


def test_ui_hierarchy_uses_formal_names_and_retains_machine_keys() -> None:
    data = build_logical_table_catalog_data()

    assert data.hierarchy == ["modelFile", "parameterName", "tables.displayName"]
    assert [item.model_file for item in data.files] == ["Demand", "Supply", "Trade"]
    assert [len(item.parameters) for item in data.files] == [11, 7, 4]
    assert [sum(len(parameter.tables) for parameter in item.parameters) for item in data.files] == [28, 20, 6]

    parameters = {
        parameter.parameter_name: parameter for model_file in data.files for parameter in model_file.parameters
    }
    power_mix = parameters["PowerMix"]
    assert [(table.display_name, table.model_table_key) for table in power_mix.tables] == [
        ("Annual Power Mix Adjustment", "table1"),
        ("Monthly Power Mix Adjustment", None),
        ("Power Generation Data", None),
    ]
    canal_toll = parameters["CanalToll"]
    assert [(table.display_name, table.model_table_key) for table in canal_toll.tables] == [
        ("Suez Canal Cost", "table4"),
        ("Panama Canal Cost", "table4"),
    ]


def test_catalog_joins_parameters_by_model_param_id_not_parameter_code() -> None:
    data = build_logical_table_catalog_data()
    by_id = {
        parameter.model_param_id: (parameter.parameter_code, parameter.parameter_name)
        for model_file in data.files
        for parameter in model_file.parameters
    }

    assert by_id[2] == ("CoalFuturesPrice", "Coal Futures Price")
    assert by_id[3] == ("GasFuturesPrice", "Gas Futures Price")
    assert by_id[9] == ("UserAdjustedGasDemand", "User-Adjusted Gas Demand")
    assert by_id[18] == ("PNGContractVolume", "PNG Contract Volume")


def test_proposal_machine_targets_are_covered_by_catalog_write_targets() -> None:
    catalog = load_logical_table_catalog()
    capability = load_proposal_capability_contract()
    write_targets = {
        (
            entry.model_param_id,
            entry.model_file,
            entry.model_sheet,
            entry.model_table_key,
        )
        for entry in catalog.entries
        if entry.table_role == "WRITE_TARGET"
    }

    for parameter in capability.parameters:
        target = parameter.model_target
        assert (
            parameter.model_param_id,
            target.model_file,
            target.model_sheet,
            target.model_table,
        ) in write_targets


def test_logical_table_catalog_route_is_registered_with_camel_case_response() -> None:
    route = next(
        item
        for item in router.routes
        if isinstance(item, APIRoute) and item.path == "/model-parameters/logical-table-catalog"
    )
    assert route.methods == {"GET"}

    payload = route.response_model(data=build_logical_table_catalog_data()).model_dump(
        mode="json",
        by_alias=True,
    )
    assert payload["status"] == "success"
    assert payload["data"]["files"][0]["modelFile"] == "Demand"
    assert payload["data"]["files"][0]["parameters"][0]["parameterName"] == "GDP"
    assert payload["data"]["files"][0]["parameters"][0]["tables"][0]["displayName"] == ("GDP Adjustment")
