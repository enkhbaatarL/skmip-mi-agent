from __future__ import annotations

# Copyright (c) 2026 SK Innovation E&S.
import argparse
from collections import Counter
from collections.abc import Mapping, Sequence
import json
import logging
from pathlib import Path
import tempfile
from typing import Any

from openpyxl import Workbook, load_workbook
from openpyxl.cell import Cell
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.worksheet.worksheet import Worksheet
import yaml


LOGGER = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parents[2]
PARAMETER_CANONICAL_PATH = ROOT_DIR / "scripts/model_parameter/model-parameter-canonical-v4.1-0050.json"
LEGACY_MAPPING_CANONICAL_PATH = ROOT_DIR / "scripts/model_parameter/model-parameter-canonical-v1.json"
IMPACT_CANONICAL_PATH = ROOT_DIR / "scripts/model_parameter/model-impact-lever-canonical-v4.1-0050.json"
CONFIG_PATH = ROOT_DIR / "envs/config.yaml"
MAPPING_DIR = ROOT_DIR / "apps/agents/model_parameter_agent/resources/mapping"
ARCHIVE_DIR = MAPPING_DIR / "archive"
FINAL_WORKBOOK_PATH = MAPPING_DIR / "261016_시나리오가정_MI수급모델_input_매핑_model-parameter-canonical-v4.1.xlsx"
LEGACY_WORKBOOK_NAMES = (
    "260625_시나리오가정_MI수급모델_input_매핑_vfShare_agent.xlsx",
    "260702_시나리오가정_MI수급모델_input_매핑_모델파트수정_v0.4.xlsx",
    "260807_시나리오가정_MI수급모델_input_매핑_model-parameter-canonical-v1.xlsx",
    "260813_시나리오가정_MI수급모델_input_매핑_model-parameter-canonical-v4.xlsx",
)

PARAMETER_SHEET = "Parameter Excel Mapping"
DIMENSION_SHEET = "Dimension Parameter Mapping"
PARAMETER_HEADERS = (
    "model_param_id",
    "use_yn",
    "parameter_name",
    "parameter_hint",
    "model_file",
    "model_sheet",
    "model_table",
    "semantic_axes",
    "basecase_read_mode",
    "basecase_header_row",
    "basecase_data_start_row",
    "basecase_column_roles",
    "basecase_row_filter",
    "basecase_year_row",
    "basecase_month_row",
    "basecase_period_row",
    "basecase_value_start_col",
    "basecase_value_end_col",
    "basecase_stop_rule",
    "crt_usr_logn_id",
    "crt_dtm",
    "mod_usr_logn_id",
    "mod_dtm",
    "del_yn",
)
DIMENSION_HEADERS = (
    "model_param_dimension_map_id",
    "use_yn",
    "event_type_l2_id",
    "dimension_key",
    "dimension_label",
    "mapping_method",
    "model_param_id",
    "parameter_name",
    "comment",
    "crt_usr_logn_id",
    "crt_dtm",
    "mod_usr_logn_id",
    "mod_dtm",
    "del_yn",
)
LUT_HEADERS = (
    "classification",
    "parameter_or_resource",
    "enabled",
    "adapter",
    "file_role",
    "local_file",
    "object_storage_path",
    "key_axes",
)
CONFLICT_HEADERS = ("conflict", "final_decision", "evidence", "reflected_artifact")
BASECASE_ONLY_PARAMETER_NAMES = frozenset(
    {
        "User-Adjusted Gas Demand",
        "RegasAdjustment",
        "PNG Contract Volume",
        "RemainingUnrestrictedAmount",
        "ShippingCost",
        "VolumeCancelled",
        "RegionalProductionAdjustment",
        "ShippingFuelCost",
        "CanalToll",
        "Suez Canal Cost",
        "Panama Canal Cost",
    },
)
EXPECTED_LEGACY_MAPPING_COUNT = 129
EXPECTED_LEGACY_MAPPING_METHOD_COUNTS = {
    "direct": 35,
    "routing": 6,
    "indirect": 55,
    "na": 33,
}
EXPECTED_LEGACY_CANDIDATE_PARAMETER_NAMES = frozenset(
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
LEVER_BINDING_HEADERS = (
    "lever_code",
    "domain",
    "impact_lever_id",
    "parameter_name",
    "role",
    "applicability",
    "catalog_support_status",
    "effective_support_status",
)

TITLE_FILL = PatternFill("solid", fgColor="17365D")
HEADER_FILL = PatternFill("solid", fgColor="5B9BD5")
SUBHEADER_FILL = PatternFill("solid", fgColor="D9EAF7")
ACTIVE_FILL = PatternFill("solid", fgColor="E2F0D9")
DEFERRED_FILL = PatternFill("solid", fgColor="FFF2CC")
ROUTING_FILL = PatternFill("solid", fgColor="E4DFEC")
DIRECT_FILL = PatternFill("solid", fgColor="DDEBF7")
NEUTRAL_FILL = PatternFill("solid", fgColor="F2F2F2")
THIN_BORDER = Border(
    left=Side(style="thin", color="D9E2F3"),
    right=Side(style="thin", color="D9E2F3"),
    top=Side(style="thin", color="D9E2F3"),
    bottom=Side(style="thin", color="D9E2F3"),
)


def _load_json(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        msg = f"Expected a JSON object: {path}"
        raise TypeError(msg)
    return document


def _load_yaml(path: Path) -> dict[str, Any]:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        msg = f"Expected a YAML object: {path}"
        raise TypeError(msg)
    return document


def _compose_workbook_canonical(  # noqa: C901
    parameter_canonical: Mapping[str, Any],
    legacy_mapping_canonical: Mapping[str, Any],
) -> dict[str, Any]:
    """Combine the v4 master with only the approved shared v1/v3 mapping payload."""
    if parameter_canonical.get("canonical_version") != "model-parameter-canonical-v4.1-0050":
        msg = "Workbook parameter source must be model-parameter-canonical-v4.1-0050"
        raise ValueError(msg)
    if legacy_mapping_canonical.get("canonical_version") != "model-parameter-canonical-v1":
        msg = "Workbook legacy mapping source must be model-parameter-canonical-v1"
        raise ValueError(msg)

    master = parameter_canonical.get("master")
    mappings = legacy_mapping_canonical.get("dimension_mappings")
    if not isinstance(master, list) or not all(isinstance(row, dict) for row in master):
        msg = "v4 master must be an array of objects"
        raise TypeError(msg)
    if not isinstance(mappings, list) or not all(isinstance(row, dict) for row in mappings):
        msg = "shared legacy mappings must be an array of objects"
        raise TypeError(msg)
    if len(mappings) != EXPECTED_LEGACY_MAPPING_COUNT:
        msg = f"Shared legacy mapping count must be {EXPECTED_LEGACY_MAPPING_COUNT}"
        raise ValueError(msg)

    method_counts = Counter(str(row.get("mapping_method")) for row in mappings)
    if dict(method_counts) != EXPECTED_LEGACY_MAPPING_METHOD_COUNTS:
        msg = f"Shared legacy mapping methods mismatch: {dict(method_counts)}"
        raise ValueError(msg)

    active_by_id = {
        int(row["model_param_id"]): str(row["parameter_name"])
        for row in master
        if row.get("use_yn") == "Y" and row.get("del_yn") == "N"
    }
    candidate_names: set[str] = set()
    for row in mappings:
        model_param_id = row.get("model_param_id")
        if model_param_id is None:
            continue
        parameter_name = active_by_id.get(int(model_param_id))
        if parameter_name is None:
            msg = f"Shared mapping references an inactive or missing v4 master row: {model_param_id}"
            raise ValueError(msg)
        if row.get("mapping_method") in {"direct", "routing"}:
            candidate_names.add(parameter_name)
    if candidate_names != EXPECTED_LEGACY_CANDIDATE_PARAMETER_NAMES:
        msg = f"Shared legacy candidate names mismatch: {sorted(candidate_names)}"
        raise ValueError(msg)

    canonical = dict(parameter_canonical)
    canonical["generated_from_snapshot"] = parameter_canonical["generated_from_snapshot"]
    canonical["dimension_mappings"] = [dict(row) for row in mappings]
    canonical["mapping_count"] = len(mappings)
    canonical["expected_counts"] = dict(parameter_canonical["expected_counts"])
    canonical["expected_counts"]["dimension_mappings"] = len(mappings)
    canonical["expected_counts"]["mapping_methods"] = dict(method_counts)
    canonical["legacy_mapping_canonical_version"] = legacy_mapping_canonical["canonical_version"]
    canonical["legacy_mapping_generated_from_snapshot"] = legacy_mapping_canonical["generated_from_snapshot"]
    return canonical


def _write_row(worksheet: Worksheet, row_index: int, values: Sequence[object]) -> None:
    for column_index, value in enumerate(values, start=1):
        worksheet.cell(row=row_index, column=column_index, value=value)


def _style_header(worksheet: Worksheet, column_count: int) -> None:
    for cell in worksheet[1][:column_count]:
        cell.fill = HEADER_FILL
        cell.font = Font(color="FFFFFF", bold=True, size=10)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = THIN_BORDER
    worksheet.row_dimensions[1].height = 34
    worksheet.freeze_panes = "A2"
    worksheet.sheet_view.showGridLines = False


def _style_body(worksheet: Worksheet, *, text_columns: set[int]) -> None:
    for row in worksheet.iter_rows(min_row=2, max_row=worksheet.max_row):
        max_text_length = 0
        for cell in row:
            cell.border = THIN_BORDER
            cell.alignment = Alignment(
                horizontal="left" if cell.column in text_columns else "center",
                vertical="top",
                wrap_text=cell.column in text_columns,
            )
            if cell.value is not None:
                max_text_length = max(max_text_length, len(str(cell.value)))
        if max_text_length > 120:
            worksheet.row_dimensions[row[0].row].height = min(90, 30 + max_text_length // 25 * 6)
        else:
            worksheet.row_dimensions[row[0].row].height = 21


def _set_column_widths(worksheet: Worksheet, widths: Mapping[str, float]) -> None:
    for column, width in widths.items():
        worksheet.column_dimensions[column].width = width


def _add_table(worksheet: Worksheet, *, name: str) -> None:
    reference = f"A1:{worksheet.cell(row=worksheet.max_row, column=worksheet.max_column).coordinate}"
    table = Table(displayName=name, ref=reference)
    table.tableStyleInfo = TableStyleInfo(
        name="TableStyleMedium2",
        showFirstColumn=False,
        showLastColumn=False,
        showRowStripes=True,
        showColumnStripes=False,
    )
    worksheet.add_table(table)
    worksheet.auto_filter.ref = reference


def _build_overview(
    workbook: Workbook,
    canonical: Mapping[str, Any],
) -> None:
    worksheet = workbook.active
    worksheet.title = "0. Canonical Overview"
    worksheet.sheet_view.showGridLines = False
    worksheet.merge_cells("A1:D2")
    title = worksheet["A1"]
    title.value = "MI Model Parameter Mapping — Lever-native Canonical v4.1 / v0050"
    title.fill = TITLE_FILL
    title.font = Font(color="FFFFFF", bold=True, size=15)
    title.alignment = Alignment(horizontal="center", vertical="center")
    for row in worksheet["A1:D2"]:
        for cell in row:
            cell.fill = TITLE_FILL

    current_path = FINAL_WORKBOOK_PATH.relative_to(ROOT_DIR)
    metadata = (
        ("Master canonical", canonical["canonical_version"]),
        ("Legacy mapping canonical", canonical["legacy_mapping_canonical_version"]),
        (
            "DB matrix",
            (
                f"master {canonical['master_count']} / active {len(canonical['active_parameter_names'])} / "
                f"shared v1/v3 legacy dimension mapping {canonical['mapping_count']}"
            ),
        ),
        (
            "Source snapshots",
            (
                f"master={Path(str(canonical['generated_from_snapshot'])).name}\n"
                f"legacy mapping={Path(str(canonical['legacy_mapping_generated_from_snapshot'])).name}"
            ),
        ),
        ("Audit user", canonical["audit_user"]),
        ("Current workbook", f"{current_path.parent}/\n{current_path.name}"),
        ("Historical workbooks", str(ARCHIVE_DIR.relative_to(ROOT_DIR))),
    )
    for offset, (label, value) in enumerate(metadata, start=4):
        worksheet.cell(row=offset, column=1, value=label)
        worksheet.cell(row=offset, column=2, value=value)
        worksheet.merge_cells(start_row=offset, start_column=2, end_row=offset, end_column=4)
        worksheet.cell(row=offset, column=1).fill = SUBHEADER_FILL
        worksheet.cell(row=offset, column=1).font = Font(bold=True, color="17365D")
        worksheet.cell(row=offset, column=2).alignment = Alignment(wrap_text=True, vertical="top")

    cards = (
        ("A11", "A12:A13", "Master rows", canonical["master_count"]),
        ("B11", "B12:B13", "Active parameters", len(canonical["active_parameter_names"])),
        ("C11", "C12:C13", "Dimension mappings", canonical["mapping_count"]),
        ("D11", "D12:D13", "LUT", 10),
    )
    for label_address, value_range, label, value in cards:
        worksheet.merge_cells(value_range)
        label_cell = worksheet[label_address]
        value_cell = worksheet[value_range.split(":", maxsplit=1)[0]]
        label_cell.value = label
        value_cell.value = value
        label_cell.fill = HEADER_FILL
        label_cell.font = Font(color="FFFFFF", bold=True)
        label_cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        value_cell.fill = PatternFill("solid", fgColor="EAF2F8")
        value_cell.font = Font(color="17365D", bold=True, size=20)
        value_cell.alignment = Alignment(horizontal="center", vertical="center")

    worksheet.merge_cells("A16:D16")
    worksheet["A16"] = "활성 master 18개 (v4.1 proposal 17개; CanalToll은 v4.0 catalog 호환용)"
    worksheet["A16"].fill = SUBHEADER_FILL
    worksheet["A16"].font = Font(bold=True, color="17365D")
    worksheet["A16"].alignment = Alignment(horizontal="center")
    worksheet.merge_cells("A17:D18")
    active_names = canonical["active_parameter_names"]
    worksheet["A17"] = (
        ", ".join(active_names[:6])
        + "\n"
        + ", ".join(active_names[6:11])
        + "\n"
        + ", ".join(active_names[11:])
    )
    worksheet["A17"].alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    worksheet["A17"].font = Font(bold=True, color="375623", size=9)

    worksheet.merge_cells("A20:D20")
    worksheet["A20"] = "사용 기준"
    worksheet["A20"].fill = SUBHEADER_FILL
    worksheet["A20"].font = Font(bold=True, color="17365D")
    worksheet["A20"].alignment = Alignment(horizontal="center")
    worksheet.merge_cells("A21:D23")
    worksheet["A21"] = (
        "이 workbook의 Parameter/Lever Binding sheet가 v4 실행 기준이며 Dimension Mapping은 v1/v3 legacy 전용이다.\n"
        "archive 디렉터리의 이전 Excel은 역사·검토 자료이며 실행 기준으로 사용하지 않는다.\n"
        "공개 proposal/confirmation API와 payload는 변경하지 않는다."
    )
    worksheet["A21"].alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

    for row in worksheet.iter_rows(min_row=1, max_row=23, min_col=1, max_col=4):
        for cell in row:
            cell.border = THIN_BORDER
    _set_column_widths(worksheet, {"A": 24, "B": 28, "C": 28, "D": 28})
    worksheet.row_dimensions[1].height = 30
    worksheet.row_dimensions[2].height = 30
    worksheet.row_dimensions[7].height = 34
    worksheet.row_dimensions[9].height = 34
    worksheet.row_dimensions[17].height = 28
    worksheet.row_dimensions[18].height = 28
    worksheet.row_dimensions[21].height = 30
    worksheet.row_dimensions[22].height = 30
    worksheet.row_dimensions[23].height = 30
    worksheet.freeze_panes = "A4"


def _build_parameter_sheet(workbook: Workbook, canonical: Mapping[str, Any]) -> None:
    worksheet = workbook.create_sheet(PARAMETER_SHEET)
    _write_row(worksheet, 1, PARAMETER_HEADERS)
    for row_index, row in enumerate(canonical["master"], start=2):
        _write_row(worksheet, row_index, [row.get(header) for header in PARAMETER_HEADERS])
    _style_header(worksheet, len(PARAMETER_HEADERS))
    _style_body(worksheet, text_columns={3, 4, 6, 7, 8, 9, 12, 13, 19, 20, 21, 22, 23})
    _set_column_widths(
        worksheet,
        {
            "A": 13,
            "B": 9,
            "C": 27,
            "D": 62,
            "E": 12,
            "F": 25,
            "G": 14,
            "H": 48,
            "I": 22,
            "J": 18,
            "K": 22,
            "L": 55,
            "M": 22,
            "N": 18,
            "O": 19,
            "P": 19,
            "Q": 24,
            "R": 22,
            "S": 36,
            "T": 19,
            "U": 27,
            "V": 31,
            "W": 20,
            "X": 9,
        },
    )
    worksheet.conditional_formatting.add(
        f"B2:B{worksheet.max_row}",
        FormulaRule(formula=['B2="Y"'], fill=ACTIVE_FILL),
    )
    worksheet.conditional_formatting.add(
        f"B2:B{worksheet.max_row}",
        FormulaRule(formula=['B2="N"'], fill=DEFERRED_FILL),
    )
    _add_table(worksheet, name="CanonicalParameterTable")
    worksheet.print_title_rows = "1:1"
    worksheet.page_setup.orientation = "landscape"
    worksheet.page_setup.fitToWidth = 1
    worksheet.sheet_properties.pageSetUpPr.fitToPage = True


def _normalized_dimension_rows(canonical: Mapping[str, Any]) -> list[dict[str, Any]]:
    master_names = {row["model_param_id"]: row["parameter_name"] for row in canonical["master"]}
    existing_ids = [
        row["model_param_dimension_map_id"]
        for row in canonical["dimension_mappings"]
        if row["model_param_dimension_map_id"] is not None
    ]
    next_id = max(existing_ids) + 1
    normalized: list[dict[str, Any]] = []
    for source in canonical["dimension_mappings"]:
        row = dict(source)
        if row["model_param_dimension_map_id"] is None:
            row["model_param_dimension_map_id"] = next_id
            next_id += 1
        row["parameter_name"] = master_names.get(row["model_param_id"])
        normalized.append(row)
    return normalized


def _build_dimension_sheet(workbook: Workbook, canonical: Mapping[str, Any]) -> None:
    worksheet = workbook.create_sheet(DIMENSION_SHEET)
    _write_row(worksheet, 1, DIMENSION_HEADERS)
    for row_index, row in enumerate(_normalized_dimension_rows(canonical), start=2):
        _write_row(worksheet, row_index, [row.get(header) for header in DIMENSION_HEADERS])
    _style_header(worksheet, len(DIMENSION_HEADERS))
    _style_body(worksheet, text_columns={4, 5, 6, 8, 9, 10, 11, 12, 13})
    _set_column_widths(
        worksheet,
        {
            "A": 22,
            "B": 9,
            "C": 17,
            "D": 36,
            "E": 30,
            "F": 17,
            "G": 16,
            "H": 27,
            "I": 75,
            "J": 24,
            "K": 27,
            "L": 31,
            "M": 27,
            "N": 9,
        },
    )
    worksheet.conditional_formatting.add(
        f"F2:F{worksheet.max_row}",
        FormulaRule(formula=['F2="direct"'], fill=DIRECT_FILL),
    )
    worksheet.conditional_formatting.add(
        f"F2:F{worksheet.max_row}",
        FormulaRule(formula=['F2="routing"'], fill=ROUTING_FILL),
    )
    _add_table(worksheet, name="CanonicalDimensionMappingTable")
    worksheet.print_title_rows = "1:1"
    worksheet.page_setup.orientation = "landscape"
    worksheet.page_setup.fitToWidth = 1
    worksheet.sheet_properties.pageSetUpPr.fitToPage = True


def _lut_manifest_rows(
    config: Mapping[str, Any],
    canonical: Mapping[str, Any],
) -> list[list[Any]]:
    resources = config["model_parameter_resources"]
    active_names = set(canonical["active_parameter_names"])
    rows: list[list[Any]] = []
    for parameter_name, spec in resources["lut"].items():
        enabled = bool(spec.get("enabled", True))
        classification = "active" if enabled else "deferred"
        key_axes = ", ".join(spec["key_axes"])
        for file_role, file_spec in spec["files"].items():
            rows.append(
                [
                    classification,
                    parameter_name,
                    "Y" if enabled else "N",
                    spec["adapter"],
                    file_role,
                    file_spec["path"],
                    file_spec["object_storage_path"],
                    key_axes,
                ],
            )
    rows.append(["deferred-no-lut", "ElectrificationRate", "N", None, None, None, None, None])
    for parameter_name in sorted(BASECASE_ONLY_PARAMETER_NAMES):
        enabled = parameter_name in active_names
        rows.append(
            [
                "basecase-only" if enabled else "deferred-no-lut",
                parameter_name,
                "Y" if enabled else "N",
                "canonical Basecase parser" if enabled else None,
                "exact slot" if enabled else None,
                "basecase workbook" if enabled else None,
                None,
                "master semantic axes" if enabled else None,
            ],
        )
    for reference_name, spec in resources["references"].items():
        rows.append(
            [
                "reference",
                reference_name,
                "N/A",
                None,
                "reference",
                spec["path"],
                spec["object_storage_path"],
                None,
            ],
        )
    return rows


def _build_lut_sheet(workbook: Workbook, lut_rows: Sequence[Sequence[Any]]) -> None:
    worksheet = workbook.create_sheet("LUT Resource Manifest")
    _write_row(worksheet, 1, LUT_HEADERS)
    for row_index, row in enumerate(lut_rows, start=2):
        _write_row(worksheet, row_index, row)
    _style_header(worksheet, len(LUT_HEADERS))
    _style_body(worksheet, text_columns={1, 2, 4, 5, 6, 7, 8})
    _set_column_widths(
        worksheet,
        {"A": 21, "B": 30, "C": 10, "D": 25, "E": 18, "F": 52, "G": 70, "H": 45},
    )
    for row in range(2, worksheet.max_row + 1):
        classification = worksheet.cell(row=row, column=1).value
        if classification in {"active", "basecase-only"}:
            worksheet.cell(row=row, column=1).fill = ACTIVE_FILL
        elif classification in {"deferred", "deferred-no-lut"}:
            worksheet.cell(row=row, column=1).fill = DEFERRED_FILL
        else:
            worksheet.cell(row=row, column=1).fill = NEUTRAL_FILL
    _add_table(worksheet, name="LutResourceManifestTable")


def _build_conflict_sheet(workbook: Workbook, canonical: Mapping[str, Any]) -> None:
    rows = (
        (
            "초안 Markdown/Excel의 활성 상태 차이",
            "DB master 26행, 활성 18행; v4.1 proposal은 LUT 10종 + Basecase-only 7종",
            "외부개발 DB snapshot, 최종 허용 목록, LUT horizon",
            "canonical JSON/SQL/config/docs/current workbook",
        ),
        (
            "DB와 초안의 data start row·column role 차이",
            "LUT 10개는 유지하고 활성 Basecase-only 8개는 검증된 exact slot만 사용; CanalToll은 v4.0 catalog 호환 전용",
            "basecase workbook 구조 및 외부개발 DB read-back",
            "Parameter Excel Mapping 26행",
        ),
        (
            "Coal/Gas Futures 활성 여부",
            "2026년 이후 strip 제공 전 enabled=N/use_yn=N",
            "현재 CSV horizon은 2025-11까지",
            "LUT Resource Manifest/config/master",
        ),
        (
            "ElectrificationRate 활성 여부",
            "유효 Basecase·LUT·승인 mapping 부재로 보류",
            "등록 가능한 LUT spec 없음",
            "master use_yn=N, LUT manifest deferred-no-lut",
        ),
        (
            "legacy mapping 기준",
            (
                f"v1/v3 shared mapping을 canonical {canonical['mapping_count']}행으로 정비하고, "
                "v4는 legacy mapping을 조회하지 않는 경계를 유지"
            ),
            (
                "model-parameter-canonical-v1 dimension_mappings; "
                "historical pre-change v4 snapshot은 128행"
            ),
            f"Dimension Parameter Mapping {canonical['mapping_count']}행",
        ),
        (
            "이전 Excel의 상충 sheet",
            "이전 workbook 전체를 archive하고 canonical 전용 current workbook 생성",
            "사용자 승인 openpyxl fallback 및 canonical 자동 비교",
            "mapping/archive 및 현재 workbook",
        ),
    )
    worksheet = workbook.create_sheet("Conflict Resolution")
    _write_row(worksheet, 1, CONFLICT_HEADERS)
    for row_index, row in enumerate(rows, start=2):
        _write_row(worksheet, row_index, row)
    _style_header(worksheet, len(CONFLICT_HEADERS))
    _style_body(worksheet, text_columns={1, 2, 3, 4})
    _set_column_widths(worksheet, {"A": 32, "B": 48, "C": 46, "D": 44})
    _add_table(worksheet, name="ConflictResolutionTable")


def _effective_binding_status(
    binding: Mapping[str, Any],
    active_parameter_names: set[str],
) -> str:
    if binding.get("support_status") != "executable":
        return "known_unsupported"
    if str(binding.get("parameter_name") or "") not in active_parameter_names:
        return "known_unsupported:INACTIVE_MODEL_PARAMETER"
    return "executable"


def _build_lever_binding_sheet(
    workbook: Workbook,
    canonical: Mapping[str, Any],
    impact_canonical: Mapping[str, Any],
) -> None:
    worksheet = workbook.create_sheet("Impact Lever Bindings")
    _write_row(worksheet, 1, LEVER_BINDING_HEADERS)
    active_names = set(canonical["active_parameter_names"])
    row_index = 2
    for lever in impact_canonical["impact_levers"]:
        for binding in lever.get("parameter_bindings") or []:
            _write_row(
                worksheet,
                row_index,
                [
                    lever["lever_code"],
                    lever["domain"],
                    lever.get("impact_lever_id", lever.get("target_impact_lever_id")),
                    binding["parameter_name"],
                    binding["role"],
                    binding.get("applicability"),
                    binding["support_status"],
                    _effective_binding_status(binding, active_names),
                ],
            )
            row_index += 1
    _style_header(worksheet, len(LEVER_BINDING_HEADERS))
    _style_body(worksheet, text_columns={1, 2, 4, 5, 6, 7, 8})
    _set_column_widths(
        worksheet,
        {"A": 30, "B": 14, "C": 16, "D": 32, "E": 14, "F": 78, "G": 24, "H": 38},
    )
    _add_table(worksheet, name="ImpactLeverBindingTable")


def _build_workbook(
    canonical: Mapping[str, Any],
    impact_canonical: Mapping[str, Any],
    config: Mapping[str, Any],
) -> Workbook:
    workbook = Workbook()
    workbook.properties.creator = "model-parameter-canonical-v4"
    workbook.properties.title = "MI Model Parameter Canonical Mapping"
    workbook.properties.subject = (
        f"{canonical['master_count']} v4 master rows and {canonical['mapping_count']} shared v1/v3 mappings"
    )
    workbook.properties.description = (
        "v4 Model Parameter master and Lever bindings composed with the shared v1/v3 canonical mapping"
    )
    workbook.calculation.calcMode = "auto"
    workbook.calculation.fullCalcOnLoad = True
    workbook.calculation.forceFullCalc = True

    lut_rows = _lut_manifest_rows(config, canonical)
    _build_overview(workbook, canonical)
    _build_parameter_sheet(workbook, canonical)
    _build_dimension_sheet(workbook, canonical)
    _build_lever_binding_sheet(workbook, canonical, impact_canonical)
    _build_lut_sheet(workbook, lut_rows)
    _build_conflict_sheet(workbook, canonical)
    workbook.active = 0
    return workbook


def _worksheet_dicts(worksheet: Worksheet) -> list[dict[str, Any]]:
    rows = list(worksheet.iter_rows(values_only=True))
    headers = [str(value) for value in rows[0]]
    return [dict(zip(headers, row, strict=True)) for row in rows[1:]]


def _assert_equal(actual: object, expected: object, *, label: str) -> None:
    if actual != expected:
        msg = f"Workbook mismatch for {label}: actual={actual!r}, expected={expected!r}"
        raise ValueError(msg)


def validate_workbook(
    path: Path,
    canonical: Mapping[str, Any],
    impact_canonical: Mapping[str, Any],
    config: Mapping[str, Any],
) -> None:
    workbook = load_workbook(path, read_only=False, data_only=False)
    expected_sheets = [
        "0. Canonical Overview",
        PARAMETER_SHEET,
        DIMENSION_SHEET,
        "Impact Lever Bindings",
        "LUT Resource Manifest",
        "Conflict Resolution",
    ]
    _assert_equal(workbook.sheetnames, expected_sheets, label="sheet names")

    parameter_rows = _worksheet_dicts(workbook[PARAMETER_SHEET])
    _assert_equal(len(parameter_rows), canonical["master_count"], label="parameter row count")
    for actual, expected in zip(parameter_rows, canonical["master"], strict=True):
        for header in PARAMETER_HEADERS:
            _assert_equal(
                actual[header],
                expected.get(header),
                label=f"parameter {expected['model_param_id']} {header}",
            )
    active_names = {row["parameter_name"] for row in parameter_rows if row["use_yn"] == "Y"}
    _assert_equal(active_names, set(canonical["active_parameter_names"]), label="active parameter names")

    dimension_rows = _worksheet_dicts(workbook[DIMENSION_SHEET])
    expected_dimension_rows = _normalized_dimension_rows(canonical)
    _assert_equal(len(dimension_rows), canonical["mapping_count"], label="dimension mapping row count")
    for actual, expected in zip(dimension_rows, expected_dimension_rows, strict=True):
        for header in DIMENSION_HEADERS:
            _assert_equal(
                actual[header],
                expected.get(header),
                label=f"dimension mapping {expected['model_param_dimension_map_id']} {header}",
            )
    _assert_equal(
        Counter(row["mapping_method"] for row in dimension_rows),
        Counter(canonical["expected_counts"]["mapping_methods"]),
        label="mapping method counts",
    )

    lut_rows = _worksheet_dicts(workbook["LUT Resource Manifest"])
    _assert_equal(
        len(lut_rows),
        len(_lut_manifest_rows(config, canonical)),
        label="LUT manifest row count",
    )
    active_lut_names = {row["parameter_or_resource"] for row in lut_rows if row["classification"] == "active"}
    _assert_equal(
        active_lut_names,
        set(canonical["active_parameter_names"]) - BASECASE_ONLY_PARAMETER_NAMES,
        label="active LUT names",
    )
    _assert_equal(
        {row["parameter_or_resource"] for row in lut_rows if row["classification"] == "basecase-only"},
        BASECASE_ONLY_PARAMETER_NAMES & set(canonical["active_parameter_names"]),
        label="Basecase-only parameter names",
    )
    _assert_equal(
        {row["parameter_or_resource"] for row in lut_rows if row["classification"] == "deferred"},
        {"Coal Futures Price", "Gas Futures Price"},
        label="deferred LUT names",
    )
    lever_rows = _worksheet_dicts(workbook["Impact Lever Bindings"])
    expected_binding_count = sum(
        len(lever.get("parameter_bindings") or []) for lever in impact_canonical["impact_levers"]
    )
    _assert_equal(len(lever_rows), expected_binding_count, label="Lever binding row count")
    _assert_equal(
        expected_binding_count,
        impact_canonical["binding_occurrence_count"],
        label="v4.1 raw Lever binding count",
    )
    _assert_equal(
        sum(row["effective_support_status"] == "executable" for row in lever_rows),
        impact_canonical["effective_executable_binding_occurrence_count"],
        label="v4.1 executable Lever binding count",
    )

    for worksheet in workbook.worksheets:
        for row in worksheet.iter_rows():
            for cell in row:
                if isinstance(cell, Cell) and isinstance(cell.value, str) and cell.value.startswith("#"):
                    msg = f"Workbook contains a formula error marker: {worksheet.title}!{cell.coordinate}={cell.value}"
                    raise ValueError(msg)

    if len(workbook[PARAMETER_SHEET].tables) != 1 or len(workbook[DIMENSION_SHEET].tables) != 1:
        msg = "Canonical data sheets must each contain one filterable Excel table"
        raise ValueError(msg)


def _archive_legacy_workbooks() -> None:
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    for name in LEGACY_WORKBOOK_NAMES:
        source = MAPPING_DIR / name
        destination = ARCHIVE_DIR / name
        if not source.exists():
            if not destination.exists():
                msg = f"Legacy workbook is missing from both current and archive paths: {name}"
                raise FileNotFoundError(msg)
            continue
        if destination.exists():
            msg = f"Refusing to overwrite existing archived workbook: {destination}"
            raise FileExistsError(msg)
        source.replace(destination)


def sync_workbook() -> Path:
    canonical = _compose_workbook_canonical(
        _load_json(PARAMETER_CANONICAL_PATH),
        _load_json(LEGACY_MAPPING_CANONICAL_PATH),
    )
    impact_canonical = _load_json(IMPACT_CANONICAL_PATH)
    config = _load_yaml(CONFIG_PATH)
    workbook = _build_workbook(canonical, impact_canonical, config)
    MAPPING_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix=".model-parameter-canonical-v4-",
        suffix=".xlsx",
        dir=MAPPING_DIR,
        delete=False,
    ) as temporary_file:
        temporary_path = Path(temporary_file.name)
    try:
        workbook.save(temporary_path)
        validate_workbook(temporary_path, canonical, impact_canonical, config)
        _archive_legacy_workbooks()
        temporary_path.replace(FINAL_WORKBOOK_PATH)
    finally:
        temporary_path.unlink(missing_ok=True)
    validate_workbook(FINAL_WORKBOOK_PATH, canonical, impact_canonical, config)
    return FINAL_WORKBOOK_PATH


def main() -> None:
    parser = argparse.ArgumentParser(description="Build or validate the canonical Model Parameter mapping workbook.")
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Validate the current workbook and archive without rewriting files.",
    )
    args = parser.parse_args()
    canonical = _compose_workbook_canonical(
        _load_json(PARAMETER_CANONICAL_PATH),
        _load_json(LEGACY_MAPPING_CANONICAL_PATH),
    )
    impact_canonical = _load_json(IMPACT_CANONICAL_PATH)
    config = _load_yaml(CONFIG_PATH)
    if args.check_only:
        validate_workbook(FINAL_WORKBOOK_PATH, canonical, impact_canonical, config)
        missing_archive = [name for name in LEGACY_WORKBOOK_NAMES if not (ARCHIVE_DIR / name).is_file()]
        if missing_archive:
            msg = f"Archived workbooks are missing: {missing_archive}"
            raise FileNotFoundError(msg)
        LOGGER.info("canonical mapping workbook validation passed: %s", FINAL_WORKBOOK_PATH)
        return
    output = sync_workbook()
    LOGGER.info("canonical mapping workbook synchronized: %s", output)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
