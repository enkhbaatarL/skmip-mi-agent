# Copyright (c) 2026 SK Innovation E&S.
# ruff: noqa: S101
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import re
from typing import Any

from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet
import yaml


ROOT_DIR = Path(__file__).resolve().parents[2]
CANONICAL_PATH = ROOT_DIR / "scripts/model_parameter/model-parameter-canonical-v1.json"
SNAPSHOT_PATH = ROOT_DIR / "scripts/model_parameter/snapshots/external_dev_before_20260807.json"
CANONICAL_DOC_PATH = ROOT_DIR / "apps/agents/model_parameter_agent/resources/Model_Parameter_Base_Case_Mapping.md"
LUT_ROOT = ROOT_DIR / "apps/agents/model_parameter_agent/resources/lut"
MAPPING_ROOT = ROOT_DIR / "apps/agents/model_parameter_agent/resources/mapping"
CURRENT_MAPPING_WORKBOOK_PATH = (
    MAPPING_ROOT / "260807_시나리오가정_MI수급모델_input_매핑_model-parameter-canonical-v1.xlsx"
)
ARCHIVED_MAPPING_WORKBOOK_NAMES = {
    "260625_시나리오가정_MI수급모델_input_매핑_vfShare_agent.xlsx",
    "260702_시나리오가정_MI수급모델_input_매핑_모델파트수정_v0.4.xlsx",
}

EXPECTED_ACTIVE_PARAMETER_NAMES = frozenset(
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
DEFERRED_SPECS = {"Coal Futures Price", "Gas Futures Price"}
EXPECTED_METHOD_COUNTS = {"direct": 35, "routing": 6, "indirect": 55, "na": 33}
EXPECTED_RESTORED_IDS = {2, 5, 9, 16, 18, 23, 66, 68, 70, 96, 97, 106, 107}


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

    assert canonical["canonical_version"] == "model-parameter-canonical-v1"
    assert canonical["generated_from_snapshot"] == (
        "scripts/model_parameter/snapshots/external_dev_before_20260807.json"
    )
    assert canonical["master_count"] == len(master) == 21
    assert canonical["mapping_count"] == len(mappings) == 129
    assert snapshot["master_count"] == len(snapshot["master"]) == 21
    assert snapshot["mapping_count"] == len(snapshot["dimension_mappings"]) == 128

    active_rows = [row for row in master if row["use_yn"] == "Y" and row["del_yn"] == "N"]
    assert {row["parameter_name"] for row in active_rows} == EXPECTED_ACTIVE_PARAMETER_NAMES
    assert set(canonical["active_parameter_names"]) == EXPECTED_ACTIVE_PARAMETER_NAMES
    assert Counter(row["mapping_method"] for row in mappings) == EXPECTED_METHOD_COUNTS

    identified = {
        row["model_param_dimension_map_id"] for row in mappings if row["model_param_dimension_map_id"] is not None
    }
    assert identified == set(range(1, 129))
    restored = {
        row["model_param_dimension_map_id"]
        for row in mappings
        if row["model_param_dimension_map_id"] in EXPECTED_RESTORED_IDS
    }
    assert restored == EXPECTED_RESTORED_IDS

    population_rows = [
        row
        for row in mappings
        if (
            row["event_type_l2_id"],
            row["dimension_key"],
            row["model_param_id"],
        )
        == (21, "economic_intensity", 11)
    ]
    assert len(population_rows) == 1
    assert population_rows[0]["mapping_method"] == "routing"
    assert "인구·이민·인구전망" in population_rows[0]["comment"]
    assert "GDP·PMI" in population_rows[0]["comment"]

    active_by_id = {row["model_param_id"]: row for row in active_rows}
    candidate_rows = [row for row in mappings if row["mapping_method"] in {"direct", "routing"}]
    assert {row["model_param_id"] for row in candidate_rows} == set(active_by_id)
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
        for dimension in json.loads(template["template_json"]):
            template_keys.add((template["event_type_l2_id"], dimension["dim_key"]))
    mapping_keys = {(row["event_type_l2_id"], row["dimension_key"]) for row in mappings}
    assert mapping_keys <= template_keys


def test_configmap_and_local_resource_manifests_match_canonical() -> None:
    canonical = _load_json(CANONICAL_PATH)
    local = _load_yaml(ROOT_DIR / "envs/config.yaml")
    configmap = _load_yaml(ROOT_DIR / "devops/k8s/configmap.yaml")
    embedded = yaml.safe_load(configmap["data"]["config.yaml"])
    assert isinstance(embedded, dict)
    document = CANONICAL_DOC_PATH.read_text(encoding="utf-8")

    local_resources = local["model_parameter_resources"]
    cluster_resources = embedded["model_parameter_resources"]
    assert local_resources == cluster_resources

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
    assert enabled_names == active_names == EXPECTED_ACTIVE_PARAMETER_NAMES
    assert disabled_names == DEFERRED_SPECS
    assert "ElectrificationRate" not in lut
    assert set(lut) <= set(master_by_name)
    for name, parameter_spec in lut.items():
        assert parameter_spec["enabled"] is (master_by_name[name]["use_yn"] == "Y")

    document_lut_rows = _parse_markdown_table(document, "## LUT canonical 명세")
    document_lut_by_name = {row["parameter"]: row for row in document_lut_rows}
    assert len(document_lut_by_name) == len(document_lut_rows)
    assert set(document_lut_by_name) == active_names

    for name in active_names:
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

    for setting_name in (
        "model_parameter_max_total_selected_slots",
        "model_parameter_max_step2_prompt_bytes",
        "model_parameter_max_step3_prompt_bytes",
    ):
        assert local[setting_name] == embedded[setting_name]
        assert local[setting_name] > 0


def test_canonical_mapping_workbook_and_archive_match_fixture() -> None:
    canonical = _load_json(CANONICAL_PATH)
    assert {path.name for path in MAPPING_ROOT.glob("*.xlsx")} == {CURRENT_MAPPING_WORKBOOK_PATH.name}
    archive_root = MAPPING_ROOT / "archive"
    assert {path.name for path in archive_root.glob("*.xlsx")} == ARCHIVED_MAPPING_WORKBOOK_NAMES
    assert (archive_root / "README.md").is_file()

    workbook = load_workbook(CURRENT_MAPPING_WORKBOOK_PATH, read_only=False, data_only=False)
    assert workbook.sheetnames == [
        "0. Canonical Overview",
        "Parameter Excel Mapping",
        "Dimension Parameter Mapping",
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
        EXPECTED_ACTIVE_PARAMETER_NAMES
    )

    parameter_names = {row["model_param_id"]: row["parameter_name"] for row in canonical["master"]}
    expected_mappings: list[dict[str, Any]] = []
    for source in canonical["dimension_mappings"]:
        expected = dict(source)
        if expected["model_param_dimension_map_id"] is None:
            expected["model_param_dimension_map_id"] = 129
        expected["parameter_name"] = parameter_names.get(expected["model_param_id"])
        expected_mappings.append(expected)

    dimension_sheet = workbook["Dimension Parameter Mapping"]
    dimension_rows = _worksheet_dicts(dimension_sheet)
    assert dimension_sheet.max_row == 130
    assert len(dimension_sheet.tables) == 1
    assert dimension_rows == expected_mappings
    assert Counter(row["mapping_method"] for row in dimension_rows) == EXPECTED_METHOD_COUNTS

    overview = workbook["0. Canonical Overview"]
    assert [overview[cell].value for cell in ("A12", "B12", "C12", "D12")] == [21, 10, 129, 10]
    lut_rows = _worksheet_dicts(workbook["LUT Resource Manifest"])
    assert {row["parameter_or_resource"] for row in lut_rows if row["classification"] == "active"} == (
        EXPECTED_ACTIVE_PARAMETER_NAMES
    )
    assert {row["parameter_or_resource"] for row in lut_rows if row["classification"] == "deferred"} == (
        DEFERRED_SPECS
    )
    assert {
        row["parameter_or_resource"] for row in lut_rows if row["classification"] == "deferred-no-lut"
    } == {"ElectrificationRate"}

    excel_error_markers = {"#NULL!", "#DIV/0!", "#VALUE!", "#REF!", "#NAME?", "#NUM!", "#N/A"}
    assert not {
        (worksheet.title, cell.coordinate, cell.value)
        for worksheet in workbook.worksheets
        for row in worksheet.iter_rows()
        for cell in row
        if cell.value in excel_error_markers
    }


def test_canonical_document_and_apply_artifacts_are_versioned_and_complete() -> None:
    canonical = _load_json(CANONICAL_PATH)
    document = CANONICAL_DOC_PATH.read_text(encoding="utf-8")
    runner = (ROOT_DIR / "scripts/model_parameter/apply_canonical.py").read_text(encoding="utf-8")
    sql = (ROOT_DIR / "scripts/model_parameter/apply_model_parameter_canonical_v1.sql").read_text(encoding="utf-8")

    assert "model-parameter-canonical-v1" in document
    assert "master: 21행, 활성 10행" in document
    assert "dimension mapping: 129행" in document
    assert "direct 35, routing 6, indirect 55, na 33" in document
    document_master_rows = _parse_markdown_table(document, "## 최종 master")
    document_master_by_id = {int(row["ID"]): row for row in document_master_rows}
    assert len(document_master_by_id) == len(document_master_rows) == canonical["master_count"]
    for canonical_row in canonical["master"]:
        document_row = document_master_by_id[canonical_row["model_param_id"]]
        assert document_row["use_yn"] == canonical_row["use_yn"]
        assert document_row["parameter_name"] == canonical_row["parameter_name"]
        assert document_row["parameter_hint"] == canonical_row["parameter_hint"]

    assert "--apply" in runner
    assert "session.rollback()" in runner
    assert "FOR UPDATE" in runner
    assert "FOR SHARE" in runner
    assert "FOR SHARE" in sql
    assert 'if column not in {"model_param_dimension_map_id", "crt_dtm"}' in runner
    assert "START TRANSACTION" in sql
    assert "DECLARE EXIT HANDLER FOR SQLEXCEPTION" in sql
    assert "ROLLBACK" in sql
    assert "ALTER TABLE" not in sql
    assert "`comment`, crt_usr_logn_id, mod_usr_logn_id, del_yn" in sql
    assert "d.dimension_label <=> '강도'" in sql
    assert "d.crt_usr_logn_id <=> 'model-parameter-canonical-v1'" in sql
    assert "AND crt_usr_logn_id = 'model-parameter-canonical-v1'" in sql
    assert "expected exactly 10 active parameters" in sql
    assert "expected 129 mappings" in sql
    assert "JSON_TABLE" in sql
    assert " unit " not in sql.lower()


def test_operator_docs_do_not_reintroduce_the_previous_five_parameter_state() -> None:
    canonical_docs = [
        ROOT_DIR / "README.md",
        ROOT_DIR / "apps/agents/model_parameter_agent/docs/01_MODEL_PARAMETER_AGENT_OVERVIEW.md",
        ROOT_DIR / "apps/agents/model_parameter_agent/docs/03_MODEL_PARAMETER_AGENT_DB_SPEC.md",
        ROOT_DIR / "apps/agents/model_parameter_agent/docs/05_MODEL_PARAMETER_AGENT_BASECASE_LUT_PARSING.md",
        ROOT_DIR / "apps/agents/model_parameter_agent/docs/06_MODEL_PARAMETER_AGENT_PARAMETER_ADDITION_GUIDE.md",
        CANONICAL_DOC_PATH,
    ]
    stale_phrases = (
        "현재 활성 5개",
        "현재 활성 항목은 다음 5개",
        "현재 연결 128건",
        "LiqProd master는 비활성",
        "현재 미사용인 `LiqProdAdjustment`",
    )
    for path in canonical_docs:
        content = path.read_text(encoding="utf-8")
        assert all(parameter_name in content for parameter_name in EXPECTED_ACTIVE_PARAMETER_NAMES)
        assert not any(phrase in content for phrase in stale_phrases)
