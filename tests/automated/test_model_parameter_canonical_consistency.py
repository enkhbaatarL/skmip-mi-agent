# Copyright (c) 2026 SK Innovation E&S.
# ruff: noqa: S101
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet
import pytest
import yaml

from scripts.model_parameter.apply_model_parameter_v4 import (
    _validate_documents,
)


ROOT_DIR = Path(__file__).resolve().parents[2]
CANONICAL_PATH = ROOT_DIR / "scripts/model_parameter/model-parameter-canonical-v4.json"
LEGACY_MAPPING_CANONICAL_PATH = ROOT_DIR / "scripts/model_parameter/model-parameter-canonical-v1.json"
IMPACT_CANONICAL_PATH = ROOT_DIR / "scripts/model_parameter/model-impact-lever-canonical-v4.json"
CURRENT_CANONICAL_PATH = ROOT_DIR / "scripts/model_parameter/model-parameter-canonical-v4-0032.json"
CURRENT_IMPACT_CANONICAL_PATH = ROOT_DIR / "scripts/model_parameter/model-impact-lever-canonical-v4-0032.json"
SNAPSHOT_PATH = ROOT_DIR / "scripts/model_parameter/snapshots/external_dev_before_model_parameter_v4_20260813.json"
CANONICAL_DOC_PATH = ROOT_DIR / "apps/agents/model_parameter_agent/resources/Model_Parameter_Base_Case_Mapping.md"
LUT_ROOT = ROOT_DIR / "apps/agents/model_parameter_agent/resources/lut"
MAPPING_ROOT = ROOT_DIR / "apps/agents/model_parameter_agent/resources/mapping"
CURRENT_MAPPING_WORKBOOK_PATH = (
    MAPPING_ROOT / "260813_시나리오가정_MI수급모델_input_매핑_model-parameter-canonical-v4.xlsx"
)
ARCHIVED_V1_WORKBOOK_PATH = (
    MAPPING_ROOT / "archive/260807_시나리오가정_MI수급모델_input_매핑_model-parameter-canonical-v1.xlsx"
)
ARCHIVED_MAPPING_WORKBOOK_NAMES = {
    "260625_시나리오가정_MI수급모델_input_매핑_vfShare_agent.xlsx",
    "260702_시나리오가정_MI수급모델_input_매핑_모델파트수정_v0.4.xlsx",
    "260807_시나리오가정_MI수급모델_input_매핑_model-parameter-canonical-v1.xlsx",
}

EXPECTED_ACTIVE_PARAMETER_NAMES = frozenset(
    {
        "GDP",
        "PMI",
        "PowerMix",
        "Temperature",
        "Population",
        "User-Adjusted Gas Demand",
        "HurricaneIntensity",
        "LiqProdAdjustment",
        "LiqUtilAdjustment",
        "PipelineAdjustment",
        "RegasAdjustment",
        "SupplyDisruption",
        "PNG Contract Volume",
        "RemainingUnrestrictedAmount",
        "ShippingCost",
        "VolumeCancelled",
    },
)
EXPECTED_CURRENT_ACTIVE_PARAMETER_NAMES = EXPECTED_ACTIVE_PARAMETER_NAMES - {
    "RemainingUnrestrictedAmount",
    "VolumeCancelled",
}
EXPECTED_LUT_BACKED_PARAMETER_NAMES = frozenset(
    {
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
    },
)
EXPECTED_BASECASE_ONLY_PARAMETER_NAMES = frozenset(
    {
        "User-Adjusted Gas Demand",
        "RegasAdjustment",
        "PNG Contract Volume",
        "RemainingUnrestrictedAmount",
        "ShippingCost",
        "VolumeCancelled",
    },
)
EXPECTED_INACTIVE_PARAMETER_NAMES = frozenset(
    {
        "CDD",
        "Coal Futures Price",
        "Gas Futures Price",
        "HDD",
        "ElectrificationRate",
    },
)
DEFERRED_SPECS = {"Coal Futures Price", "Gas Futures Price"}
EXPECTED_V4_SNAPSHOT_METHOD_COUNTS = {"direct": 25, "routing": 2, "indirect": 55, "na": 46}
EXPECTED_V4_SNAPSHOT_CANDIDATE_PARAMETER_NAMES = {
    "GDP",
    "PMI",
    "PowerMix",
    "Temperature",
    "LiqUtilAdjustment",
}
EXPECTED_SHARED_METHOD_COUNTS = {"direct": 35, "routing": 6, "indirect": 55, "na": 33}
EXPECTED_SHARED_CANDIDATE_PARAMETER_NAMES = {
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
EXPECTED_SHARED_MAPPING_SHA256 = "1c365c37184eb8a4141a996d2d298072bc8be58b22bc8d86c4116e0fc1f23dc4"


def _load_json(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    return document


def _load_yaml(path: Path) -> dict[str, Any]:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    return document


def _parse_markdown_table(document: str, heading: str) -> list[dict[str, str]]:
    lines = document.splitlines()
    try:
        heading_index = lines.index(heading)
    except ValueError as exc:
        message = f"Markdown heading not found: {heading}"
        raise AssertionError(message) from exc

    table_lines: list[str] = []
    for line in lines[heading_index + 1 :]:
        stripped = line.strip()
        if stripped.startswith("#") and not table_lines:
            break
        if stripped.startswith("|"):
            table_lines.append(stripped)
        elif table_lines:
            break

    assert len(table_lines) >= 2, f"Markdown table not found after heading: {heading}"
    header = [cell.strip() for cell in table_lines[0].strip("|").split("|")]
    separator = [cell.strip() for cell in table_lines[1].strip("|").split("|")]
    assert len(header) == len(separator)
    assert all(re.fullmatch(r":?-+:?", cell) for cell in separator)

    rows: list[dict[str, str]] = []
    for table_line in table_lines[2:]:
        values = [cell.strip() for cell in table_line.strip("|").split("|")]
        assert len(values) == len(header), f"Malformed Markdown row: {table_line}"
        rows.append(dict(zip(header, values, strict=True)))
    return rows


def _split_adapter_label(adapter_label: str) -> tuple[str, str | None]:
    match = re.fullmatch(r"(?P<adapter>[^()]+?)(?:\((?P<layout>[^()]+)\))?", adapter_label)
    assert match is not None, f"Malformed adapter label: {adapter_label}"
    return match.group("adapter"), match.group("layout")


def _expand_documented_file_names(file_label: str) -> set[str]:
    expanded: list[str] = []
    for raw_name in file_label.split("+"):
        name = raw_name.strip()
        assert name.endswith(".csv"), f"Malformed LUT file label: {file_label}"
        if re.fullmatch(r"t\d+\.csv", name):
            assert expanded, f"Shorthand LUT file has no preceding file: {file_label}"
            expanded_name = re.sub(r"t\d+\.csv$", name, expanded[-1])
            assert expanded_name != expanded[-1], f"Cannot expand LUT file shorthand: {file_label}"
            name = expanded_name
        expanded.append(name)
    assert len(expanded) == len(set(expanded)), f"Duplicate LUT file in Markdown: {file_label}"
    return set(expanded)


def _expected_object_storage_path(model_file: str, local_file: str) -> str:
    directories = {
        "Demand": "demand",
        "Supply": "supply/supply_bc",
    }
    assert model_file in directories, f"No LUT Object Storage directory for model_file={model_file}"
    return f"fundamental_model_artifact/LUT/{directories[model_file]}/{local_file}"


def _worksheet_dicts(worksheet: Worksheet) -> list[dict[str, Any]]:
    rows = list(worksheet.iter_rows(values_only=True))
    headers = [str(value) for value in rows[0]]
    return [dict(zip(headers, row, strict=True)) for row in rows[1:]]


def test_canonical_master_and_dimension_mapping_invariants() -> None:
    canonical = _load_json(CANONICAL_PATH)
    snapshot = _load_json(SNAPSHOT_PATH)
    master = canonical["master"]
    mappings = canonical["dimension_mappings"]

    assert canonical["canonical_version"] == "model-parameter-canonical-v4"
    assert canonical["generated_from_snapshot"] == (
        "scripts/model_parameter/snapshots/external_dev_before_model_parameter_v4_20260813.json"
    )
    assert canonical["master_count"] == len(master) == 21
    assert canonical["mapping_count"] == len(mappings) == 128
    assert snapshot["master_count"] == len(snapshot["master"]) == 21
    assert snapshot["mapping_count"] == len(snapshot["dimension_mappings"]) == 128
    assert mappings == snapshot["dimension_mappings"]
    mapping_payload = json.dumps(
        mappings,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    assert (
        canonical["legacy_dimension_mapping_sha256"]
        == hashlib.sha256(
            mapping_payload,
        ).hexdigest()
    )

    active_rows = [row for row in master if row["use_yn"] == "Y" and row["del_yn"] == "N"]
    inactive_rows = [row for row in master if row["use_yn"] == "N" and row["del_yn"] == "N"]
    assert {row["parameter_name"] for row in active_rows} == EXPECTED_ACTIVE_PARAMETER_NAMES
    assert set(canonical["active_parameter_names"]) == EXPECTED_ACTIVE_PARAMETER_NAMES
    assert {row["parameter_name"] for row in inactive_rows} == EXPECTED_INACTIVE_PARAMETER_NAMES
    assert set(canonical["inactive_parameter_names"]) == EXPECTED_INACTIVE_PARAMETER_NAMES
    assert EXPECTED_ACTIVE_PARAMETER_NAMES == (
        EXPECTED_LUT_BACKED_PARAMETER_NAMES | EXPECTED_BASECASE_ONLY_PARAMETER_NAMES
    )
    assert not (EXPECTED_LUT_BACKED_PARAMETER_NAMES & EXPECTED_BASECASE_ONLY_PARAMETER_NAMES)
    assert Counter(row["mapping_method"] for row in mappings) == EXPECTED_V4_SNAPSHOT_METHOD_COUNTS

    identified = {
        row["model_param_dimension_map_id"] for row in mappings if row["model_param_dimension_map_id"] is not None
    }
    assert identified == set(range(1, 129))

    active_by_id = {row["model_param_id"]: row for row in active_rows}
    candidate_rows = [row for row in mappings if row["mapping_method"] in {"direct", "routing"}]
    assert {
        active_by_id[row["model_param_id"]]["parameter_name"] for row in candidate_rows
    } == EXPECTED_V4_SNAPSHOT_CANDIDATE_PARAMETER_NAMES
    basecase_only_ids = {
        row["model_param_id"] for row in active_rows if row["parameter_name"] in EXPECTED_BASECASE_ONLY_PARAMETER_NAMES
    }
    assert not {row["model_param_id"] for row in candidate_rows} & basecase_only_ids
    assert not [
        row
        for row in mappings
        if row["model_param_id"] in basecase_only_ids and row["mapping_method"] in {"direct", "routing"}
    ]
    assert all(row["model_param_id"] in active_by_id for row in candidate_rows)
    assert all(row["model_param_id"] is None or row["model_param_id"] in active_by_id for row in mappings)
    assert all(row["use_yn"] == "Y" and row["del_yn"] == "N" for row in mappings)

    non_null_keys = [
        (row["event_type_l2_id"], row["dimension_key"], row["model_param_id"])
        for row in mappings
        if row["model_param_id"] is not None
    ]
    assert len(non_null_keys) == len(set(non_null_keys))

    template_keys: set[tuple[int, str]] = set()
    for template in snapshot["scenario_dimension_templates"]:
        if template["del_yn"] != "N":
            continue
        template_json = template["template_json"]
        dimensions = json.loads(template_json) if isinstance(template_json, str) else template_json
        for dimension in dimensions:
            template_keys.add((template["event_type_l2_id"], dimension["dim_key"]))
    mapping_keys = {(row["event_type_l2_id"], row["dimension_key"]) for row in mappings}
    assert mapping_keys <= template_keys


def test_shared_v1_v3_mapping_invariants_against_v4_master() -> None:
    parameter_canonical = _load_json(CANONICAL_PATH)
    mapping_canonical = _load_json(LEGACY_MAPPING_CANONICAL_PATH)
    snapshot = _load_json(SNAPSHOT_PATH)
    master = parameter_canonical["master"]
    mappings = mapping_canonical["dimension_mappings"]

    assert mapping_canonical["canonical_version"] == "model-parameter-canonical-v1"
    assert mapping_canonical["mapping_count"] == len(mappings) == 129
    assert Counter(row["mapping_method"] for row in mappings) == EXPECTED_SHARED_METHOD_COUNTS
    assert all(row["use_yn"] == "Y" and row["del_yn"] == "N" for row in mappings)

    mapping_payload = json.dumps(
        mappings,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    assert hashlib.sha256(mapping_payload).hexdigest() == EXPECTED_SHARED_MAPPING_SHA256

    identified = {
        row["model_param_dimension_map_id"] for row in mappings if row["model_param_dimension_map_id"] is not None
    }
    assert identified == set(range(1, 129))
    assert sum(row["model_param_dimension_map_id"] is None for row in mappings) == 1

    active_by_id = {row["model_param_id"]: row for row in master if row["use_yn"] == "Y" and row["del_yn"] == "N"}
    candidate_rows = [row for row in mappings if row["mapping_method"] in {"direct", "routing"}]
    assert {
        active_by_id[row["model_param_id"]]["parameter_name"] for row in candidate_rows
    } == EXPECTED_SHARED_CANDIDATE_PARAMETER_NAMES
    assert all(row["model_param_id"] is None or row["model_param_id"] in active_by_id for row in mappings)

    basecase_only_ids = {
        row["model_param_id"]
        for row in active_by_id.values()
        if row["parameter_name"] in EXPECTED_BASECASE_ONLY_PARAMETER_NAMES
    }
    assert not {row["model_param_id"] for row in candidate_rows} & basecase_only_ids

    non_null_keys = [
        (row["event_type_l2_id"], row["dimension_key"], row["model_param_id"])
        for row in mappings
        if row["model_param_id"] is not None
    ]
    assert len(non_null_keys) == len(set(non_null_keys))

    template_keys: set[tuple[int, str]] = set()
    for template in snapshot["scenario_dimension_templates"]:
        if template["del_yn"] != "N":
            continue
        template_json = template["template_json"]
        dimensions = json.loads(template_json) if isinstance(template_json, str) else template_json
        for dimension in dimensions:
            template_keys.add((template["event_type_l2_id"], dimension["dim_key"]))
    mapping_keys = {(row["event_type_l2_id"], row["dimension_key"]) for row in mappings}
    assert mapping_keys <= template_keys


def test_configmap_and_local_resource_manifests_match_canonical() -> None:
    canonical = _load_json(CURRENT_CANONICAL_PATH)
    local = _load_yaml(ROOT_DIR / "envs/config.yaml")
    configmap = _load_yaml(ROOT_DIR / "devops/k8s/configmap.yaml")
    embedded = yaml.safe_load(configmap["data"]["config.yaml"])
    assert isinstance(embedded, dict)
    document = CANONICAL_DOC_PATH.read_text(encoding="utf-8")

    local_resources = local["model_parameter_resources"]
    cluster_resources = embedded["model_parameter_resources"]
    assert local_resources == cluster_resources
    local_storage = local["model_parameter_resource_storage"]
    cluster_storage = embedded["model_parameter_resource_storage"]
    assert set(local_storage) == set(cluster_storage)
    environment_specific_storage_fields = {
        "endpoint_url",
        "access_key_id",
        "secret_access_key",
    }
    for field_name in set(local_storage) - environment_specific_storage_fields:
        assert local_storage[field_name] == cluster_storage[field_name]

    master_by_name = {row["parameter_name"]: row for row in canonical["master"]}
    assert len(master_by_name) == canonical["master_count"]
    active_names = {name for name, row in master_by_name.items() if row["use_yn"] == "Y" and row["del_yn"] == "N"}

    document_master_rows = _parse_markdown_table(document, "## 최종 master")
    document_master_by_name = {row["parameter_name"]: row for row in document_master_rows}
    assert len(document_master_by_name) == len(document_master_rows) == canonical["master_count"]
    assert set(document_master_by_name) == set(master_by_name)
    for name, canonical_row in master_by_name.items():
        document_row = document_master_by_name[name]
        assert int(document_row["ID"]) == canonical_row["model_param_id"]
        assert document_row["use_yn"] == canonical_row["use_yn"]

    lut = local_resources["lut"]
    enabled_names = {name for name, spec in lut.items() if spec.get("enabled", True)}
    disabled_names = {name for name, spec in lut.items() if not spec.get("enabled", True)}
    assert active_names == EXPECTED_CURRENT_ACTIVE_PARAMETER_NAMES
    assert enabled_names == EXPECTED_LUT_BACKED_PARAMETER_NAMES
    assert active_names >= EXPECTED_BASECASE_ONLY_PARAMETER_NAMES - {
        "RemainingUnrestrictedAmount",
        "VolumeCancelled",
    }
    assert not (EXPECTED_BASECASE_ONLY_PARAMETER_NAMES & set(lut))
    assert disabled_names == DEFERRED_SPECS
    assert {"CDD", "HDD", "ElectrificationRate"}.isdisjoint(lut)
    assert set(lut) <= set(master_by_name)
    for name, parameter_spec in lut.items():
        assert parameter_spec["enabled"] is (master_by_name[name]["use_yn"] == "Y")

    document_lut_rows = _parse_markdown_table(document, "## LUT canonical 명세")
    document_lut_by_name = {row["parameter"]: row for row in document_lut_rows}
    assert len(document_lut_by_name) == len(document_lut_rows)
    assert set(document_lut_by_name) == EXPECTED_LUT_BACKED_PARAMETER_NAMES

    document_basecase_rows = _parse_markdown_table(
        document,
        "### Basecase-only canonical",
    )
    document_basecase_by_name = {row["parameter"]: row for row in document_basecase_rows}
    assert len(document_basecase_by_name) == len(document_basecase_rows) == 6
    assert set(document_basecase_by_name) == EXPECTED_BASECASE_ONLY_PARAMETER_NAMES

    for name in EXPECTED_LUT_BACKED_PARAMETER_NAMES:
        parameter_spec = lut[name]
        document_spec = document_lut_by_name[name]
        documented_adapter, documented_layout = _split_adapter_label(document_spec["adapter"])
        documented_key_axes = [axis.strip() for axis in document_spec["exact key axes"].split(",")]
        documented_files = _expand_documented_file_names(document_spec["file"])
        configured_files = {file_spec["path"] for file_spec in parameter_spec["files"].values()}

        assert parameter_spec["enabled"] is True
        assert documented_adapter == parameter_spec["adapter"]
        assert documented_layout == parameter_spec.get("layout")
        assert documented_key_axes == parameter_spec["key_axes"]
        assert documented_files == configured_files

        for file_spec in parameter_spec["files"].values():
            local_file = file_spec["path"]
            assert (LUT_ROOT / local_file).is_file()
            assert file_spec["object_storage_path"] == _expected_object_storage_path(
                master_by_name[name]["model_file"],
                local_file,
            )

    for name in DEFERRED_SPECS:
        assert lut[name]["adapter"] == "futures_price"
        assert lut[name]["enabled"] is False
        for file_spec in lut[name]["files"].values():
            local_file = file_spec["path"]
            assert (LUT_ROOT / local_file).is_file()
            assert file_spec["object_storage_path"] == _expected_object_storage_path(
                master_by_name[name]["model_file"],
                local_file,
            )

    references = local_resources["references"]
    assert set(references) == {"demand_general_country_list"}
    assert references["demand_general_country_list"]["path"] == ("Demand_Model_LUT_General_value_based_t6.csv")

    declared_files = {
        file_spec["path"] for parameter_spec in lut.values() for file_spec in parameter_spec["files"].values()
    } | {reference["path"] for reference in references.values()}
    actual_files = {path.name for path in LUT_ROOT.glob("*.csv")}
    assert declared_files == actual_files

    for reference in references.values():
        assert (LUT_ROOT / reference["path"]).is_file()
        assert reference["object_storage_path"] == _expected_object_storage_path(
            "Demand",
            reference["path"],
        )

    assert (
        local["model_parameter_proposal_flow_release"] == embedded["model_parameter_proposal_flow_release"] == "v4.1.7"
    )
    assert (
        local["scenario_group_v4_impact_catalog_version"]
        == embedded["scenario_group_v4_impact_catalog_version"]
        == "v4.1"
    )
    for setting_name in (
        "model_parameter_transient_retry_max_attempts",
        "model_parameter_transient_retry_base_delay_seconds",
        "model_parameter_transient_retry_max_jitter_seconds",
        "model_parameter_max_total_selected_slots",
        "model_parameter_max_step2_prompt_bytes",
        "model_parameter_max_step3_prompt_bytes",
        "model_parameter_max_routing_candidates_per_dimension",
        "model_parameter_v4_max_routing_candidates_per_dimension",
        "model_parameter_max_conditional_parameters_per_scenario",
    ):
        assert local[setting_name] == embedded[setting_name]
        assert local[setting_name] > 0
    assert local["model_parameter_variation_mode"] == embedded["model_parameter_variation_mode"] == "balanced"
    for setting_name in (
        "model_parameter_variation_profile_enabled",
        "model_parameter_grounded_slot_recovery_enabled",
    ):
        assert local[setting_name] is embedded[setting_name] is True


def test_canonical_mapping_workbook_and_archive_match_fixture() -> None:
    canonical = _load_json(CURRENT_CANONICAL_PATH)
    mapping_canonical = _load_json(LEGACY_MAPPING_CANONICAL_PATH)
    impact_canonical = _load_json(CURRENT_IMPACT_CANONICAL_PATH)
    assert {path.name for path in MAPPING_ROOT.glob("*.xlsx")} == {CURRENT_MAPPING_WORKBOOK_PATH.name}
    archive_root = MAPPING_ROOT / "archive"
    assert {path.name for path in archive_root.glob("*.xlsx")} == ARCHIVED_MAPPING_WORKBOOK_NAMES
    assert ARCHIVED_V1_WORKBOOK_PATH.is_file()
    assert (archive_root / "README.md").is_file()

    workbook = load_workbook(CURRENT_MAPPING_WORKBOOK_PATH, read_only=False, data_only=False)
    assert workbook.sheetnames == [
        "0. Canonical Overview",
        "Parameter Excel Mapping",
        "Dimension Parameter Mapping",
        "Impact Lever Bindings",
        "LUT Resource Manifest",
        "Conflict Resolution",
    ]
    assert "Parameter Excel Mapping (모델파트)" not in workbook.sheetnames

    parameter_sheet = workbook["Parameter Excel Mapping"]
    parameter_rows = _worksheet_dicts(parameter_sheet)
    assert parameter_sheet.max_row == 22
    assert len(parameter_sheet.tables) == 1
    assert parameter_rows == canonical["master"]
    assert {row["parameter_name"] for row in parameter_rows if row["use_yn"] == "Y"} == (
        EXPECTED_CURRENT_ACTIVE_PARAMETER_NAMES
    )

    parameter_names = {row["model_param_id"]: row["parameter_name"] for row in canonical["master"]}
    expected_mappings: list[dict[str, Any]] = []
    next_mapping_id = (
        max(
            row["model_param_dimension_map_id"]
            for row in mapping_canonical["dimension_mappings"]
            if row["model_param_dimension_map_id"] is not None
        )
        + 1
    )
    for source in mapping_canonical["dimension_mappings"]:
        expected = dict(source)
        if expected["model_param_dimension_map_id"] is None:
            expected["model_param_dimension_map_id"] = next_mapping_id
            next_mapping_id += 1
        expected["parameter_name"] = parameter_names.get(expected["model_param_id"])
        expected_mappings.append(expected)

    dimension_sheet = workbook["Dimension Parameter Mapping"]
    dimension_rows = _worksheet_dicts(dimension_sheet)
    assert dimension_sheet.max_row == 130
    assert len(dimension_sheet.tables) == 1
    assert dimension_rows == expected_mappings
    assert Counter(row["mapping_method"] for row in dimension_rows) == EXPECTED_SHARED_METHOD_COUNTS

    overview = workbook["0. Canonical Overview"]
    assert [overview[cell].value for cell in ("A12", "B12", "C12", "D12")] == [21, 14, 129, 10]
    lut_rows = _worksheet_dicts(workbook["LUT Resource Manifest"])
    assert {row["parameter_or_resource"] for row in lut_rows if row["classification"] == "active"} == (
        EXPECTED_LUT_BACKED_PARAMETER_NAMES
    )
    assert {row["parameter_or_resource"] for row in lut_rows if row["classification"] == "basecase-only"} == (
        EXPECTED_BASECASE_ONLY_PARAMETER_NAMES
    )
    assert {row["parameter_or_resource"] for row in lut_rows if row["classification"] == "deferred"} == (DEFERRED_SPECS)
    assert {row["parameter_or_resource"] for row in lut_rows if row["classification"] == "deferred-no-lut"} == {
        "ElectrificationRate",
    }

    lever_rows = _worksheet_dicts(workbook["Impact Lever Bindings"])
    assert len(lever_rows) == impact_canonical["expected_counts"]["binding_occurrences"] == 16
    assert Counter(row["effective_support_status"] for row in lever_rows) == {
        "executable": 14,
        "known_unsupported:INACTIVE_MODEL_PARAMETER": 2,
    }
    assert {
        row["parameter_name"] for row in lever_rows if row["effective_support_status"] == "executable"
    } == EXPECTED_CURRENT_ACTIVE_PARAMETER_NAMES
    assert {row["parameter_name"] for row in lever_rows if row["effective_support_status"] != "executable"} == {
        "CDD",
        "HDD",
    }
    assert len(workbook["Impact Lever Bindings"].tables) == 1

    archived_v1 = load_workbook(
        ARCHIVED_V1_WORKBOOK_PATH,
        read_only=False,
        data_only=False,
    )
    assert "Impact Lever Bindings" not in archived_v1.sheetnames
    archived_overview = archived_v1["0. Canonical Overview"]
    assert [archived_overview[cell].value for cell in ("A12", "B12", "C12", "D12")] == [
        21,
        10,
        129,
        10,
    ]

    excel_error_markers = {"#NULL!", "#DIV/0!", "#VALUE!", "#REF!", "#NAME?", "#NUM!", "#N/A"}
    assert not {
        (worksheet.title, cell.coordinate, cell.value)
        for worksheet in workbook.worksheets
        for row in worksheet.iter_rows()
        for cell in row
        if cell.value in excel_error_markers
    }


def test_canonical_document_and_combined_apply_runner_are_versioned_and_complete() -> None:
    canonical = _load_json(CURRENT_CANONICAL_PATH)
    document = CANONICAL_DOC_PATH.read_text(encoding="utf-8")
    runner_path = ROOT_DIR / "scripts/model_parameter/apply_model_parameter_v4.py"
    runner = runner_path.read_text(encoding="utf-8")

    assert "model-parameter-canonical-v4" in document
    assert "model-impact-lever-canonical-v4" in document
    assert "master 21행·활성 14개" in document
    assert "shared legacy dimension mapping: 129행" in document
    assert "direct 35, routing 6, indirect 55, na 33" in document
    assert "LUT-backed 10개, Basecase-only 4개 활성" in document
    assert "binding occurrence 16개" in document
    document_master_rows = _parse_markdown_table(document, "## 최종 master")
    document_master_by_id = {int(row["ID"]): row for row in document_master_rows}
    assert len(document_master_by_id) == len(document_master_rows) == canonical["master_count"]
    for canonical_row in canonical["master"]:
        document_row = document_master_by_id[canonical_row["model_param_id"]]
        assert document_row["use_yn"] == canonical_row["use_yn"]
        assert document_row["parameter_name"] == canonical_row["parameter_name"]
        assert document_row["parameter_hint"] == canonical_row["parameter_hint"]

    assert runner_path.is_file()
    assert 'MODEL_PARAMETER_VERSION = "model-parameter-canonical-v4"' in runner
    assert 'IMPACT_LEVER_VERSION = "model-impact-lever-canonical-v4"' in runner
    assert "EXPECTED_BINDING_COUNT = 20" in runner
    assert "EXPECTED_EFFECTIVE_EXECUTABLE_COUNT = 18" in runner
    assert "EXPECTED_EFFECTIVE_UNIQUE_PARAMETER_COUNT = 16" in runner
    assert "def _assert_mapping_unchanged(" in runner
    assert "def _assert_cross_table_invariants(" in runner
    assert "def _assert_read_back(" in runner
    assert "--model-parameter-canonical" in runner
    assert "--impact-lever-canonical" in runner
    assert "--snapshot" in runner
    assert "--apply" in runner
    assert "session.rollback()" in runner
    assert "FOR UPDATE" in runner
    assert "FOR SHARE" in runner
    assert "dry-run rollback did not preserve the exact pre-transaction table state" in runner

    historical_canonical = _load_json(CANONICAL_PATH)
    historical_impact_canonical = _load_json(IMPACT_CANONICAL_PATH)
    snapshot = _load_json(SNAPSHOT_PATH)
    validated = _validate_documents(
        historical_canonical,
        historical_impact_canonical,
        snapshot,
        snapshot_path=SNAPSHOT_PATH,
    )
    assert tuple(len(rows) for rows in validated) == (21, 128, 16, 21, 128, 16, 21)

    invalid_impact = deepcopy(historical_impact_canonical)
    invalid_impact["impact_levers"][0]["parameter_bindings"][0]["parameter_name"] = "UnknownParameter"
    with pytest.raises(RuntimeError):
        _validate_documents(
            historical_canonical,
            invalid_impact,
            snapshot,
            snapshot_path=SNAPSHOT_PATH,
        )


def test_operator_docs_do_not_reintroduce_pre_v4_active_or_legacy_mapping_state() -> None:
    canonical_docs = [
        ROOT_DIR / "docs/agents/model_parameter_agent/01_MODEL_PARAMETER_AGENT_OVERVIEW.md",
        ROOT_DIR / "docs/agents/model_parameter_agent/03_MODEL_PARAMETER_AGENT_DB_SPEC.md",
        ROOT_DIR / "docs/agents/model_parameter_agent/05_MODEL_PARAMETER_AGENT_BASECASE_LUT_PARSING.md",
        ROOT_DIR / "docs/agents/model_parameter_agent/06_MODEL_PARAMETER_AGENT_PARAMETER_ADDITION_GUIDE.md",
        CANONICAL_DOC_PATH,
    ]
    stale_phrases = (
        "현재 활성 5개",
        "현재 활성 항목은 다음 5개",
        "master: 21행, 활성 10행",
        "LiqProd master는 비활성",
        "현재 미사용인 `LiqProdAdjustment`",
    )
    for path in [ROOT_DIR / "README.md", *canonical_docs]:
        content = path.read_text(encoding="utf-8")
        assert not any(phrase in content for phrase in stale_phrases)

    canonical_summary = CANONICAL_DOC_PATH.read_text(encoding="utf-8")
    assert "master 21행·활성 14개" in canonical_summary
    assert all(parameter_name in canonical_summary for parameter_name in EXPECTED_BASECASE_ONLY_PARAMETER_NAMES)
    for path in canonical_docs:
        content = path.read_text(encoding="utf-8")
        assert all(parameter_name in content for parameter_name in EXPECTED_CURRENT_ACTIVE_PARAMETER_NAMES)
