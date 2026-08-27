# Copyright (c) 2026 SK Innovation E&S.

from __future__ import annotations

# ruff: noqa: ANN401, C901, E402, E501, EM101, EM102, PERF401, S314, SIM102, SIM108, TRY003
import argparse
import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import tempfile
from typing import Any
import xml.etree.ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
DEFAULT_APP_CONFIG = ROOT_DIR / "envs" / "config.yaml"
DEFAULT_DOTENV = ROOT_DIR / "envs" / ".env"
if DEFAULT_DOTENV.exists():
    from dotenv import load_dotenv

    load_dotenv(DEFAULT_DOTENV, override=False)
if "APP_CONFIG" not in os.environ and DEFAULT_APP_CONFIG.exists():
    os.environ["APP_CONFIG"] = str(DEFAULT_APP_CONFIG)

from openpyxl import load_workbook
from sqlalchemy import func, select

from apps.agents.model_parameter_agent.flows.propose_parameters.nodes import (
    _knowledge_base_from_context,
    filter_basecase_records_by_slots,
    finalize_empty_parameter_values,
    load_basecase_samples,
    propose_parameter_slots,
    propose_parameter_values,
    select_parameter_candidates,
    validate_parameter_candidates,
)
from apps.agents.model_parameter_agent.flows.propose_parameters.state import (
    ModelParameterProposalState,
)
from apps.agents.model_parameter_agent.flows.propose_parameters.validation import (
    _ensure_mapping_candidates,
    _ensure_proposal_parameters,
)
from apps.agents.model_parameter_agent.persistence.model_parameter_service import (
    _load_v3_context,
)
from apps.agents.model_parameter_agent.presentation import (
    _proposal_parameters_from_state,
)
from apps.agents.model_parameter_agent.utils.lut import ReferenceLoadPolicy
from apps.agents.model_parameter_agent.utils.lut.keys import canonical_axis_value
from apps.agents.model_parameter_agent.utils.parameter_mapping import (
    build_basecase_records,
)
from apps.agents.model_parameter_agent.utils.resource_bootstrap import (
    ensure_model_parameter_resource_runtime,
)
from apps.agents.model_parameter_agent.utils.resource_manifest import (
    load_model_parameter_resource_manifest,
)
from apps.agents.model_parameter_agent.utils.resource_runtime import (
    ModelParameterResourcePaths,
)
from apps.common.configs.config import CONFIG_FILE_PATH, get_settings
from apps.common.configs.database.sync_database.connection import get_sync_session
from apps.common.logging.logger_config import logger
from apps.persistence.event.repository import EventRepository
from apps.persistence.model_parameter.models import MiModelParamProposalModel
from apps.persistence.model_parameter.repository import ModelParameterRepository
from apps.persistence.scenario.repository import ScenarioRepository
from apps.persistence.scenario_group.models import MiScenarioGroupModel
from apps.persistence.scenario_group.repository import ScenarioGroupRepository


V3_API_VERSION = "v3"
V3_STRATEGY = "multi_event_composite_dimensions"
BASECASE_DIR = ROOT_DIR / "apps" / "agents" / "model_parameter_agent" / "resources" / "basecase"
DEFAULT_OUTPUT_ROOT = ROOT_DIR / "tests" / "reports" / "model_parameter_agent" / "experiments"
MODEL_WORKBOOKS = {
    "Demand": "Demand Model_Input.xlsm",
    "Supply": "Supply Model_Input.xlsm",
    "Trade": "Trade Model_Input.xlsm",
}
CELL_ELEMENT_RE = re.compile(r"<c\b[^>]*(?:/>|>.*?</c>)", re.DOTALL)
CELL_REFERENCE_RE = re.compile(r'\br="([A-Z]+[1-9][0-9]*)"')
BASECASE_REFERENCE_RE = re.compile(
    r"^(?P<model_file>[^:]+):(?P<sheet>.+):R(?P<row>[1-9][0-9]*)C(?P<column>[1-9][0-9]*)$",
)
OOXML_MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
OOXML_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


@dataclass(frozen=True, slots=True)
class V3ScenarioSource:
    scenario_group_id: int
    group_title: str
    group_status: str
    group_stage: str
    group_del_yn: str
    generation_strategy: str
    parameter_mapping_ready: bool
    scenario_id: int
    scenario_title: str
    scenario_status: str
    scenario_del_yn: str
    global_pressure_band: str
    scenario_role: str | None
    baseline_yn: str
    global_pressure_rationale: str
    context: dict[str, Any]


@dataclass(frozen=True, slots=True)
class CellPatch:
    model_file: str
    sheet_name: str
    row: int
    column: int
    parameter_name: str
    proposed_value: Decimal
    basecase_value: Any
    lut_value: Any
    coordinates: dict[str, Any]
    rationale: str
    basecase_reference_id: str

    @property
    def cell_reference(self) -> str:
        return f"{_column_name(self.column)}{self.row}"


@dataclass(frozen=True, slots=True)
class ProposalResult:
    source: V3ScenarioSource
    state: dict[str, Any]
    proposal_parameters: list[dict[str, Any]]
    patches: tuple[CellPatch, ...]


@dataclass(frozen=True, slots=True)
class WorkbookEvidence:
    filename: str
    output_sha256: str
    byte_identical: bool
    patched_cell_count: int
    replaced_formula_count: int
    removed_calc_chain_count: int
    modified_parts: tuple[str, ...]


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read exact api_version=v3 scenarios, run Model Parameter proposal nodes without persistence, "
            "and export one three-workbook model-input set per tagged scenario."
        ),
    )
    parser.add_argument(
        "--experiment-id",
        required=True,
        help="Stable experiment identifier used as the output directory name.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="Parent directory for the experiment output.",
    )
    parser.add_argument(
        "--scenario-group-id",
        type=int,
        help="Export only the exact api_version=v3 scenario group with this ID.",
    )
    return parser.parse_args(argv)


def _validate_experiment_id(experiment_id: str) -> str:
    value = experiment_id.strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{2,99}", value):
        raise ValueError(
            "experiment_id must be 3-100 characters and contain only letters, numbers, '.', '_' or '-'",
        )
    return value


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if hasattr(value, "value"):
        return value.value
    return value


def _text(value: Any) -> str:
    resolved = _json_safe(value)
    return "" if resolved is None else str(resolved)


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _database_fingerprint() -> str:
    cfg = get_settings()
    identity = "|".join(
        (
            str(cfg.METADATA_DB_TYPE),
            str(cfg.METADATA_DB_HOST),
            str(cfg.METADATA_DB_PORT),
            str(cfg.METADATA_DB_NAME),
            str(cfg.METADATA_DB_USERNAME),
        ),
    )
    return sha256(identity.encode("utf-8")).hexdigest()[:12]


def _load_v3_scenarios(scenario_group_id: int | None = None) -> list[V3ScenarioSource]:
    session = get_sync_session()
    try:
        group_statement = select(MiScenarioGroupModel).where(
            MiScenarioGroupModel.api_version == V3_API_VERSION,
        )
        if scenario_group_id is not None:
            group_statement = group_statement.where(
                MiScenarioGroupModel.scenario_group_id == scenario_group_id,
            )
        group_rows = list(
            session.execute(group_statement.order_by(MiScenarioGroupModel.scenario_group_id)).scalars().all(),
        )
        if not group_rows:
            if scenario_group_id is not None:
                raise RuntimeError(
                    f"No exact api_version=v3 scenario group was found: scenario_group_id={scenario_group_id}",
                )
            raise RuntimeError("No exact api_version=v3 scenario groups were found")

        scenario_repository = ScenarioRepository(session=session)
        group_repository = ScenarioGroupRepository(session=session)
        event_repository = EventRepository(session=session)
        mapping_rules, parameter_definitions = ModelParameterRepository(
            session=session,
        ).fetch_parameter_mapping_resources()
        sources: list[V3ScenarioSource] = []

        for group in group_rows:
            strategy = _text(group.generation_strategy)
            if strategy != V3_STRATEGY:
                raise RuntimeError(
                    f"Unsupported exact-v3 generation strategy: group={group.scenario_group_id}, strategy={strategy}",
                )
            scenarios = scenario_repository.fetch_models_by_group_id(
                int(group.scenario_group_id),
                include_deleted=True,
            )
            for scenario in scenarios:
                pressure_band = _text(scenario.global_pressure_band)
                if not pressure_band:
                    raise RuntimeError(
                        f"Tagged scenario is required but global_pressure_band is empty: scenario={scenario.scenario_id}",
                    )
                context = _load_v3_context(
                    scenario=scenario,
                    group=group,
                    scenario_repository=scenario_repository,
                    group_repository=group_repository,
                    event_repository=event_repository,
                )
                context["parameter_mapping_resources"] = {
                    "mapping_rules": mapping_rules,
                    "parameter_definitions": parameter_definitions,
                }
                sources.append(
                    V3ScenarioSource(
                        scenario_group_id=int(group.scenario_group_id),
                        group_title=_text(group.title),
                        group_status=_text(group.status),
                        group_stage=_text(group.stage),
                        group_del_yn=_text(group.del_yn),
                        generation_strategy=strategy,
                        parameter_mapping_ready=bool(group.parameter_mapping_ready),
                        scenario_id=int(scenario.scenario_id),
                        scenario_title=_text(scenario.title),
                        scenario_status=_text(scenario.status),
                        scenario_del_yn=_text(scenario.del_yn),
                        global_pressure_band=pressure_band,
                        scenario_role=_text(scenario.scenario_role) or None,
                        baseline_yn=_text(scenario.baseline_yn),
                        global_pressure_rationale=_text(scenario.global_pressure_rationale),
                        context=context,
                    ),
                )
        if not sources:
            raise RuntimeError("Exact api_version=v3 groups contain no scenarios")
        return sources
    finally:
        session.close()


def _proposal_snapshot(scenario_ids: list[int]) -> dict[str, Any]:
    session = get_sync_session()
    try:
        global_count, global_max = session.execute(
            select(
                func.count(MiModelParamProposalModel.model_param_proposal_id),
                func.max(MiModelParamProposalModel.model_param_proposal_id),
            ),
        ).one()
        target_rows = list(
            session.execute(
                select(
                    MiModelParamProposalModel.scenario_id,
                    func.count(MiModelParamProposalModel.model_param_proposal_id),
                    func.max(MiModelParamProposalModel.model_param_proposal_id),
                )
                .where(MiModelParamProposalModel.scenario_id.in_(scenario_ids))
                .group_by(MiModelParamProposalModel.scenario_id)
                .order_by(MiModelParamProposalModel.scenario_id),
            ).all(),
        )
        by_scenario = {
            int(scenario_id): {"count": int(row_count), "max_id": int(max_id) if max_id is not None else None}
            for scenario_id, row_count, max_id in target_rows
        }
        for scenario_id in scenario_ids:
            by_scenario.setdefault(scenario_id, {"count": 0, "max_id": None})
        return {
            "global_count": int(global_count or 0),
            "global_max_id": int(global_max) if global_max is not None else None,
            "by_scenario": by_scenario,
        }
    finally:
        session.close()


async def _initialize_packaged_resources() -> ModelParameterResourcePaths:
    cfg = get_settings()
    manifest = load_model_parameter_resource_manifest(
        cfg.model_parameter_resources,
        source_path=CONFIG_FILE_PATH,
    )
    storage = cfg.model_parameter_resource_storage.model_copy(
        update={"enabled": False},
    )
    paths = await ensure_model_parameter_resource_runtime(
        storage,
        manifest=manifest,
        lut_enabled=cfg.model_parameter_lut_enabled,
        lut_policy=ReferenceLoadPolicy(
            start_year=cfg.model_parameter_lut_horizon_start_year,
            end_year=cfg.model_parameter_lut_horizon_end_year,
            value_max_decimal_places=cfg.model_parameter_basecase_value_max_decimal_places,
            value_precision_mode=cfg.model_parameter_basecase_value_precision_mode,
        ),
    )
    if paths.source != "packaged":
        raise RuntimeError(f"Packaged resources were required but source={paths.source}")
    for filename in MODEL_WORKBOOKS.values():
        source_path = BASECASE_DIR / filename
        runtime_path = paths.basecase_dir / filename
        if _sha256_file(source_path) != _sha256_file(runtime_path):
            raise RuntimeError(f"Packaged runtime basecase differs from repository source: {filename}")
    return paths


def _update_state(
    state: ModelParameterProposalState,
    updates: dict[str, Any],
) -> ModelParameterProposalState:
    return state.model_copy(update=updates)


async def _run_proposal(source: V3ScenarioSource) -> ProposalResult:
    cfg = get_settings()
    state = ModelParameterProposalState(
        scenario_id=source.scenario_id,
        model_name=cfg.deeply_thinking_model_api_deployment_name,
        scenario_context=source.context,
        validation_warnings=list(source.context.get("validation_warnings") or []),
    )
    state = _update_state(
        state,
        {"parameter_knowledge_base": _knowledge_base_from_context(state, source.context)},
    )
    state = _update_state(state, select_parameter_candidates(state))
    state = _update_state(state, await validate_parameter_candidates(state))
    _ensure_mapping_candidates(state.model_dump())
    state = _update_state(state, load_basecase_samples(state))
    state = _update_state(state, await propose_parameter_slots(state))
    state = _update_state(state, filter_basecase_records_by_slots(state))
    state = _update_state(
        state,
        await propose_parameter_values(state) if state.parameter_slots else finalize_empty_parameter_values(state),
    )
    state_payload = state.model_dump()
    proposal_models = _proposal_parameters_from_state(
        state_payload,
        include_lut_value=True,
    )
    _ensure_proposal_parameters(state_payload, proposal_models)
    proposal_parameters = [proposal.model_dump(mode="json", by_alias=True) for proposal in proposal_models]
    patches = _cell_patches(state_payload)
    public_value_count = sum(len(proposal["values"]) for proposal in proposal_parameters)
    if len(patches) != public_value_count:
        raise RuntimeError(
            "Every public proposed value must resolve to one existing Basecase cell: "
            f"scenario={source.scenario_id}, public_values={public_value_count}, patches={len(patches)}",
        )
    return ProposalResult(
        source=source,
        state=state_payload,
        proposal_parameters=proposal_parameters,
        patches=tuple(patches),
    )


def _finite_decimal(value: Any) -> Decimal:
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"Proposed value is not numeric: {value!r}") from exc
    if not decimal_value.is_finite():
        raise ValueError(f"Proposed value must be finite: {value!r}")
    return decimal_value


def _parse_basecase_reference(reference: str) -> tuple[str, str, int, int]:
    match = BASECASE_REFERENCE_RE.fullmatch(reference)
    if match is None:
        raise ValueError(f"Invalid Basecase reference: {reference}")
    return (
        match.group("model_file"),
        match.group("sheet"),
        int(match.group("row")),
        int(match.group("column")),
    )


def _normalized_axis(value: Any, axis_name: str) -> Any:
    normalized = canonical_axis_value(axis_name, value)
    if isinstance(normalized, str):
        return normalized.casefold()
    return normalized


def _cell_patches(state: dict[str, Any]) -> list[CellPatch]:
    knowledge_base = _knowledge_base_from_context(
        ModelParameterProposalState(scenario_id=int(state["scenario_id"])),
        state.get("scenario_context") or {},
    )
    records = build_basecase_records(
        knowledge_base,
        state.get("candidate_mappings") or [],
        state.get("scenario_context") or {},
    )[0]
    record_by_reference = {
        _text(record.get("reference_id")): record for record in records if _text(record.get("reference_id"))
    }
    patches: list[CellPatch] = []
    seen: dict[tuple[str, str, int, int], Decimal] = {}
    for adjustment in state.get("parameter_adjustments") or []:
        if adjustment.get("selected", True) is False:
            continue
        parameter_name = _text(adjustment.get("parameter_name"))
        expected_model_file = _text(adjustment.get("model_file"))
        expected_sheet = _text(adjustment.get("model_sheet"))
        for cell in adjustment.get("value_grid") or []:
            if cell.get("proposed_value") is None:
                continue
            references = [
                _text(reference) for reference in cell.get("basecase_reference_ids") or [] if _text(reference)
            ]
            if len(references) != 1:
                raise RuntimeError(
                    "Existing-workbook export requires exactly one Basecase reference per proposed value: "
                    f"parameter={parameter_name}, references={references}",
                )
            model_file, sheet_name, row, column = _parse_basecase_reference(references[0])
            if model_file != expected_model_file or sheet_name != expected_sheet:
                raise RuntimeError(
                    "Proposal target and Basecase reference disagree: "
                    f"target={expected_model_file}/{expected_sheet}, reference={model_file}/{sheet_name}",
                )
            if model_file not in MODEL_WORKBOOKS:
                raise RuntimeError(f"Unsupported model file in Basecase reference: {model_file}")
            source_record = record_by_reference.get(references[0])
            if source_record is None:
                raise RuntimeError(f"Basecase reference is not present in the canonical parser output: {references[0]}")
            if int(source_record.get("source_row") or 0) != row or int(source_record.get("source_col") or 0) != column:
                raise RuntimeError(f"Basecase reference coordinates disagree with parser output: {references[0]}")
            source_axes = dict(source_record.get("axes") or {})
            coordinates = dict(cell.get("coordinates") or {})
            for axis_name, source_value in source_axes.items():
                if axis_name not in coordinates:
                    continue
                if _normalized_axis(coordinates[axis_name], axis_name) != _normalized_axis(source_value, axis_name):
                    raise RuntimeError(
                        "Proposal coordinates disagree with canonical Basecase axes: "
                        f"reference={references[0]}, axis={axis_name}, "
                        f"proposal={coordinates[axis_name]!r}, basecase={source_value!r}",
                    )
            proposed_value = _finite_decimal(cell.get("proposed_value"))
            key = (model_file, sheet_name, row, column)
            if key in seen:
                raise RuntimeError(
                    f"Duplicate exact-cell proposal is not allowed: {model_file}/{sheet_name}/R{row}C{column}",
                )
            seen[key] = proposed_value
            patches.append(
                CellPatch(
                    model_file=model_file,
                    sheet_name=sheet_name,
                    row=row,
                    column=column,
                    parameter_name=parameter_name,
                    proposed_value=proposed_value,
                    basecase_value=cell.get("basecase_value"),
                    lut_value=cell.get("lut_value"),
                    coordinates=coordinates,
                    rationale=_text(cell.get("rationale_ko")),
                    basecase_reference_id=references[0],
                ),
            )
    if not patches:
        raise RuntimeError("Proposal generated no exportable Basecase cell values")
    return sorted(
        patches,
        key=lambda item: (item.model_file, item.sheet_name, item.row, item.column),
    )


def _column_name(column: int) -> str:
    if column < 1:
        raise ValueError(f"Excel column must be positive: {column}")
    letters: list[str] = []
    remainder = column
    while remainder:
        remainder, index = divmod(remainder - 1, 26)
        letters.append(chr(ord("A") + index))
    return "".join(reversed(letters))


def _decimal_text(value: Decimal) -> str:
    text_value = format(value, "f")
    if "." in text_value:
        text_value = text_value.rstrip("0").rstrip(".")
    return text_value or "0"


def _sheet_part_map(archive: ZipFile) -> tuple[dict[str, str], dict[str, str]]:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    target_by_relation = {
        relation.attrib["Id"]: relation.attrib["Target"]
        for relation in relationships.findall(f"{{{PACKAGE_REL_NS}}}Relationship")
    }
    part_by_sheet: dict[str, str] = {}
    sheet_id_by_name: dict[str, str] = {}
    for sheet in workbook.findall(f".//{{{OOXML_MAIN_NS}}}sheet"):
        name = sheet.attrib["name"]
        relation_id = sheet.attrib[f"{{{OOXML_REL_NS}}}id"]
        target = target_by_relation[relation_id]
        if target.startswith("/"):
            part_name = target.lstrip("/")
        else:
            part_name = str(PurePosixPath("xl") / target)
        part_by_sheet[name] = part_name
        sheet_id_by_name[name] = sheet.attrib["sheetId"]
    return part_by_sheet, sheet_id_by_name


def _patch_sheet_xml(
    original: bytes,
    patches: list[CellPatch],
) -> tuple[bytes, set[str]]:
    xml = original.decode("utf-8")
    expected = {patch.cell_reference: patch for patch in patches}
    matches: dict[str, re.Match[str]] = {}
    for match in CELL_ELEMENT_RE.finditer(xml):
        reference_match = CELL_REFERENCE_RE.search(match.group(0))
        if reference_match is None:
            continue
        reference = reference_match.group(1)
        if reference in expected:
            if reference in matches:
                raise RuntimeError(f"Worksheet contains duplicate cell elements: {reference}")
            matches[reference] = match
    missing = sorted(set(expected).difference(matches))
    if missing:
        raise RuntimeError(f"Preformatted target cells do not exist in worksheet XML: {missing}")

    formula_cells: set[str] = set()
    replacements: list[tuple[int, int, str]] = []
    for reference, match in matches.items():
        cell_xml = match.group(0)
        if re.search(r"<f(?:\s|>)", cell_xml):
            formula_cells.add(reference)
        start_tag_end = cell_xml.find(">")
        start_tag = cell_xml[: start_tag_end + 1]
        attributes = start_tag[len("<c") : -1].rstrip()
        if attributes.endswith("/"):
            attributes = attributes[:-1].rstrip()
        attributes = re.sub(r'\s+t="[^"]*"', "", attributes)
        replacement = f"<c{attributes}><v>{_decimal_text(expected[reference].proposed_value)}</v></c>"
        replacements.append((match.start(), match.end(), replacement))

    for start, end, replacement in sorted(replacements, reverse=True):
        xml = f"{xml[:start]}{replacement}{xml[end:]}"
    return xml.encode("utf-8"), formula_cells


def _patch_calc_chain(
    original: bytes,
    targets: set[tuple[str, str]],
) -> tuple[bytes, int]:
    if not targets:
        return original, 0
    xml = original.decode("utf-8")
    removed = 0
    output: list[str] = []
    cursor = 0
    chain_cell_re = re.compile(r"<c\b[^>]*/>")
    inherited_sheet_id: str | None = None
    for match in chain_cell_re.finditer(xml):
        cell_xml = match.group(0)
        ref_match = re.search(r'\br="([A-Z]+[1-9][0-9]*)"', cell_xml)
        sheet_match = re.search(r'\bi="([0-9]+)"', cell_xml)
        if sheet_match is not None:
            inherited_sheet_id = sheet_match.group(1)
        if ref_match is None or inherited_sheet_id is None:
            continue
        key = (inherited_sheet_id, ref_match.group(1))
        if key not in targets:
            continue
        output.append(xml[cursor : match.start()])
        cursor = match.end()
        removed += 1
    if removed == 0:
        return original, 0
    output.append(xml[cursor:])
    return "".join(output).encode("utf-8"), removed


def _clone_zip_info(info: ZipInfo) -> ZipInfo:
    clone = ZipInfo(info.filename, date_time=info.date_time)
    clone.compress_type = info.compress_type if info.compress_type is not None else ZIP_DEFLATED
    clone.comment = info.comment
    clone.extra = info.extra
    clone.create_system = info.create_system
    clone.create_version = info.create_version
    clone.extract_version = info.extract_version
    clone.flag_bits = info.flag_bits
    clone.volume = info.volume
    clone.internal_attr = info.internal_attr
    clone.external_attr = info.external_attr
    return clone


def _write_workbook(
    source_path: Path,
    output_path: Path,
    patches: list[CellPatch],
) -> tuple[set[str], int, int]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not patches:
        shutil.copy2(source_path, output_path)
        return set(), 0, 0

    with ZipFile(source_path, "r") as source_archive:
        infos = source_archive.infolist()
        original_parts = {info.filename: source_archive.read(info.filename) for info in infos}
        part_by_sheet, sheet_id_by_name = _sheet_part_map(source_archive)
        archive_comment = source_archive.comment

    patches_by_sheet: dict[str, list[CellPatch]] = {}
    for patch in patches:
        patches_by_sheet.setdefault(patch.sheet_name, []).append(patch)

    changed_parts: dict[str, bytes] = {}
    formula_targets: set[tuple[str, str]] = set()
    replaced_formula_count = 0
    for sheet_name, sheet_patches in patches_by_sheet.items():
        part_name = part_by_sheet.get(sheet_name)
        sheet_id = sheet_id_by_name.get(sheet_name)
        if part_name is None or sheet_id is None:
            raise RuntimeError(f"Workbook sheet was not found: {source_path.name}/{sheet_name}")
        patched_xml, formula_cells = _patch_sheet_xml(
            original_parts[part_name],
            sheet_patches,
        )
        changed_parts[part_name] = patched_xml
        replaced_formula_count += len(formula_cells)
        formula_targets.update((sheet_id, reference) for reference in formula_cells)

    removed_calc_chain_count = 0
    calc_chain_name = "xl/calcChain.xml"
    if formula_targets and calc_chain_name in original_parts:
        patched_chain, removed_calc_chain_count = _patch_calc_chain(
            original_parts[calc_chain_name],
            formula_targets,
        )
        if patched_chain != original_parts[calc_chain_name]:
            changed_parts[calc_chain_name] = patched_chain
    if removed_calc_chain_count != replaced_formula_count:
        raise RuntimeError(
            "Every replaced formula must have exactly one calcChain entry removed: "
            f"workbook={source_path.name}, formulas={replaced_formula_count}, "
            f"removed={removed_calc_chain_count}",
        )

    with ZipFile(output_path, "w", allowZip64=True) as output_archive:
        output_archive.comment = archive_comment
        for info in infos:
            output_archive.writestr(
                _clone_zip_info(info),
                changed_parts.get(info.filename, original_parts[info.filename]),
            )
    return set(changed_parts), replaced_formula_count, removed_calc_chain_count


def _validate_workbook(
    source_path: Path,
    output_path: Path,
    patches: list[CellPatch],
    modified_parts: set[str],
    replaced_formula_count: int,
    removed_calc_chain_count: int,
) -> WorkbookEvidence:
    with ZipFile(source_path, "r") as source_archive, ZipFile(output_path, "r") as output_archive:
        if output_archive.testzip() is not None:
            raise RuntimeError(f"ZIP integrity failed: {output_path}")
        source_infos = source_archive.infolist()
        output_infos = output_archive.infolist()
        source_names = [info.filename for info in source_infos]
        output_names = [info.filename for info in output_infos]
        if source_names != output_names or len(output_names) != len(set(output_names)):
            raise RuntimeError(f"OOXML member order/set changed: {output_path}")
        if source_archive.comment != output_archive.comment:
            raise RuntimeError(f"ZIP archive comment changed: {output_path}")
        for name in source_names:
            if name in modified_parts:
                continue
            if source_archive.read(name) != output_archive.read(name):
                raise RuntimeError(f"Unexpected OOXML part change: {output_path.name}/{name}")
        if "xl/vbaProject.bin" in source_names:
            if source_archive.read("xl/vbaProject.bin") != output_archive.read("xl/vbaProject.bin"):
                raise RuntimeError(f"VBA project changed: {output_path}")

    byte_identical = _sha256_file(source_path) == _sha256_file(output_path)
    if not patches:
        if not byte_identical:
            raise RuntimeError(f"Unmodified workbook copy is not byte-identical: {output_path}")
    else:
        for data_only in (False, True):
            workbook = load_workbook(
                output_path,
                read_only=True,
                data_only=data_only,
                keep_vba=True,
                keep_links=True,
            )
            try:
                for patch in patches:
                    actual = (
                        workbook[patch.sheet_name]
                        .cell(
                            row=patch.row,
                            column=patch.column,
                        )
                        .value
                    )
                    if actual is None or _finite_decimal(actual) != patch.proposed_value:
                        raise RuntimeError(
                            "Workbook read-back differs from proposed value: "
                            f"{output_path.name}/{patch.sheet_name}!{patch.cell_reference} "
                            f"expected={patch.proposed_value}, actual={actual}",
                        )
            finally:
                workbook.close()

    return WorkbookEvidence(
        filename=output_path.name,
        output_sha256=_sha256_file(output_path),
        byte_identical=byte_identical,
        patched_cell_count=len(patches),
        replaced_formula_count=replaced_formula_count,
        removed_calc_chain_count=removed_calc_chain_count,
        modified_parts=tuple(sorted(modified_parts)),
    )


def _scenario_directory(result: ProposalResult) -> Path:
    return Path(f"group_{result.source.scenario_group_id}") / (
        f"scenario_{result.source.scenario_id}_{result.source.global_pressure_band}"
    )


def _export_workbooks(
    experiment_root: Path,
    results: list[ProposalResult],
) -> dict[int, list[WorkbookEvidence]]:
    evidence_by_scenario: dict[int, list[WorkbookEvidence]] = {}
    for result in results:
        scenario_root = experiment_root / _scenario_directory(result)
        scenario_evidence: list[WorkbookEvidence] = []
        for model_file, filename in MODEL_WORKBOOKS.items():
            source_path = BASECASE_DIR / filename
            output_path = scenario_root / filename
            patches = [patch for patch in result.patches if patch.model_file == model_file]
            modified_parts, formula_count, calc_chain_count = _write_workbook(
                source_path,
                output_path,
                patches,
            )
            scenario_evidence.append(
                _validate_workbook(
                    source_path,
                    output_path,
                    patches,
                    modified_parts,
                    formula_count,
                    calc_chain_count,
                ),
            )
        evidence_by_scenario[result.source.scenario_id] = scenario_evidence
    return evidence_by_scenario


def _short(value: Any, limit: int = 180) -> str:
    text_value = " ".join(_text(value).split())
    if len(text_value) <= limit:
        return text_value
    return f"{text_value[: limit - 3].rstrip()}..."


def _number_summary(values: list[Any]) -> str:
    numbers = [_finite_decimal(value) for value in values if value is not None]
    if not numbers:
        return "N/A"
    minimum = min(numbers)
    maximum = max(numbers)
    return _decimal_text(minimum) if minimum == maximum else f"{_decimal_text(minimum)}~{_decimal_text(maximum)}"


def _slot_preview(values: list[dict[str, Any]], limit: int = 6) -> str:
    items: list[str] = []
    for value in values[:limit]:
        axis_parts = []
        for key in ("Country", "LNG Plant", "LNG Plant Train", "Pipeline Name", "Year", "Month"):
            if key in value:
                axis_parts.append(f"{key}={value[key]}")
        items.append(f"{'/'.join(axis_parts)} → {value.get('proposedValue')}")
    suffix = f" 외 {len(values) - limit}건" if len(values) > limit else ""
    return "; ".join(items) + suffix


def _llm_usage_summary(state: dict[str, Any]) -> str:
    calls = state.get("llm_calls") or []
    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0
    elapsed = 0.0
    for call in calls:
        usage = call.get("usage") or {}
        prompt_tokens += int(usage.get("prompt_tokens") or 0)
        completion_tokens += int(usage.get("completion_tokens") or 0)
        total_tokens += int(usage.get("total_tokens") or 0)
        elapsed += float(call.get("elapsed_seconds") or 0.0)
    return (
        f"calls={len(calls)}, prompt/completion/total="
        f"{prompt_tokens}/{completion_tokens}/{total_tokens}, elapsed={elapsed:.3f}s"
    )


def _build_report(
    *,
    experiment_id: str,
    created_at: datetime,
    db_fingerprint: str,
    resource_paths: ModelParameterResourcePaths,
    source_hashes: dict[str, str],
    results: list[ProposalResult],
    evidence_by_scenario: dict[int, list[WorkbookEvidence]],
    proposal_before: dict[str, Any],
    proposal_after: dict[str, Any],
) -> str:
    groups = {result.source.scenario_group_id: result.source for result in results}
    proposal_names = sorted(
        {proposal["parameterName"] for result in results for proposal in result.proposal_parameters},
    )
    archived_group_count = sum(source.group_del_yn == "Y" for source in groups.values())
    archived_scenario_count = sum(result.source.scenario_del_yn == "Y" for result in results)
    lines = [
        "# Model Parameter v3 tag-alignment 입력 실험 요약",
        "",
        f"- Experiment ID: `{experiment_id}`",
        f"- 생성 시각: `{created_at.astimezone().isoformat(timespec='seconds')}`",
        f"- DB 대상 fingerprint: `{db_fingerprint}` (`envs/.env`, exact `api_version='v3'`, SELECT-only)",
        f"- 범위: group {len(groups)}건 / scenario {len(results)}건; archived group {archived_group_count}건 / archived scenario {archived_scenario_count}건",
        f"- 리소스: `{resource_paths.source}` / fingerprint `{resource_paths.resource_fingerprint or resource_paths.semantic_schema_hash}`",
        f"- 현 DB mapping으로 산출된 parameter: `{', '.join(proposal_names)}`",
        "- 태그 격리: `global_pressure_band`, role, tag rationale은 LLM 입력에서 제외하고 사후 정합성 판정용 holdout으로만 보존",
        "",
        "## 결과",
        "",
        "| group | scenario | pressure tag / role | proposal | 적용 셀 | 출력 세트 | 결과 |",
        "|---:|---:|---|---|---:|---|---|",
    ]
    for result in results:
        proposal_text = ", ".join(
            f"{proposal['parameterName']}({len(proposal['values'])})" for proposal in result.proposal_parameters
        )
        relative_dir = _scenario_directory(result).as_posix()
        lines.append(
            f"| {result.source.scenario_group_id} | {result.source.scenario_id} | "
            f"{result.source.global_pressure_band} / {result.source.scenario_role or '-'} | "
            f"{proposal_text} | {len(result.patches)} | `{relative_dir}` (3 XLSM) | PASS |",
        )

    lines.extend(["", "## 제안 근거 요약", ""])
    for result in results:
        lines.extend(
            [
                f"### Scenario {result.source.scenario_id} — {result.source.global_pressure_band}",
                "",
                f"- 시나리오: {_short(result.source.scenario_title)}",
                f"- 태그 근거(holdout): {_short(result.source.global_pressure_rationale)}",
            ],
        )
        for proposal in result.proposal_parameters:
            values = list(proposal["values"])
            lines.append(
                f"- `{proposal['parameterName']}` {len(values)}건: "
                f"basecase `{_number_summary([value.get('basecaseValue') for value in values])}`, "
                f"LUT `{_number_summary([value.get('lutValue') for value in values])}`, "
                f"proposed `{_number_summary([value.get('proposedValue') for value in values])}`. "
                f"근거: {_short(proposal.get('rationale'))}",
            )
            lines.append(f"- 적용 preview: {_slot_preview(values)}")
        warnings = result.state.get("validation_warnings") or []
        lines.append(f"- LLM 사용: `{_llm_usage_summary(result.state)}`; warnings `{len(warnings)}`건")
        lines.append("")

    target_unchanged = proposal_before["by_scenario"] == proposal_after["by_scenario"]
    lines.extend(
        [
            "## 검증",
            "",
            f"- DB proposal 무변경: `{'PASS' if target_unchanged else 'FAIL'}` — 대상 scenario별 count/max-id가 실행 전후 동일",
            f"- 전체 proposal 관측값: `{proposal_before['global_count']}/{proposal_before['global_max_id']}` → `{proposal_after['global_count']}/{proposal_after['global_max_id']}` (count/max-id)",
            "- 원본 Basecase 불변: `PASS` — "
            + ", ".join(f"{filename} `{digest[:12]}`" for filename, digest in source_hashes.items()),
            f"- XLSM 구조: `PASS` — {len(results) * len(MODEL_WORKBOOKS)}개 ZIP 무결성, member 순서/집합, 비수정 part, sheet/VBA 보존 및 제안 셀 dual read-back 검증",
        ],
    )
    for result in results:
        details = evidence_by_scenario[result.source.scenario_id]
        lines.append(
            f"- Scenario {result.source.scenario_id}: "
            + ", ".join(
                f"{item.filename} cells={item.patched_cell_count}, formula={item.replaced_formula_count}, "
                f"calcChain={item.removed_calc_chain_count}, sha256={item.output_sha256[:12]}"
                for item in details
            ),
        )

    lines.extend(["", "## 적용 셀", ""])
    for result in results:
        lines.append(f"### Scenario {result.source.scenario_id}")
        lines.append("")
        lines.append("| parameter | cell | coordinates | basecase | LUT | proposed |")
        lines.append("|---|---|---|---:|---:|---:|")
        for patch in result.patches:
            coordinate_text = ", ".join(f"{key}={value}" for key, value in patch.coordinates.items()).replace(
                "|",
                "\\|",
            )
            lines.append(
                f"| {patch.parameter_name} | `{patch.basecase_reference_id}` | {coordinate_text} | "
                f"{patch.basecase_value} | {patch.lut_value} | {_decimal_text(patch.proposed_value)} |",
            )
        lines.append("")

    lines.extend(
        [
            "",
            "## 해석 한계",
            "",
            (
                f"이번 실험은 exact `api_version='v3'` 대상 {len(groups)}개 group과 {len(results)}개 scenario를 "
                "SELECT로 읽고 proposal을 저장하지 않은 채 동일 Step1~3 노드를 실행했다. "
                f"soft-delete 대상은 group {archived_group_count}개, scenario {archived_scenario_count}개다. "
                "`parameter_mapping_ready=false`는 sourceRef lineage가 완전한 경우 warning으로 기록하되 "
                "XLSM export 자체를 막지는 않는다."
            ),
            "",
            "이 산출물은 수급모델 실행 입력이다. bullish/bearish tag와 실제 모델 결과 방향의 최종 align 판정은 생성된 XLSM 세트를 수급모델에 실행한 뒤 수행해야 한다.",
            "",
        ],
    )
    return "\n".join(lines)


def _prepare_experiment_paths(output_root: Path, experiment_id: str) -> tuple[Path, Path]:
    resolved_root = output_root.resolve()
    resolved_root.mkdir(parents=True, exist_ok=True)
    final_root = resolved_root / experiment_id
    if final_root.exists():
        raise FileExistsError(f"Experiment output already exists: {final_root}")
    return resolved_root, final_root


def _promote_experiment(temp_root: Path, final_root: Path) -> None:
    temp_root.rename(final_root)


async def _run(
    experiment_id: str,
    output_root: Path,
    scenario_group_id: int | None = None,
) -> Path:
    output_root, final_root = _prepare_experiment_paths(output_root, experiment_id)

    source_hashes = {filename: _sha256_file(BASECASE_DIR / filename) for filename in MODEL_WORKBOOKS.values()}
    resource_paths = await _initialize_packaged_resources()
    sources = _load_v3_scenarios(scenario_group_id)
    scenario_ids = [source.scenario_id for source in sources]
    proposal_before = _proposal_snapshot(scenario_ids)
    logger.info(
        "v3 model-input export started | experiment_id={} groups={} scenarios={} db_fingerprint={}",
        experiment_id,
        len({source.scenario_group_id for source in sources}),
        len(sources),
        _database_fingerprint(),
    )

    results: list[ProposalResult] = []
    for index, source in enumerate(sources, start=1):
        logger.info(
            "v3 proposal running | experiment_id={} progress={}/{} scenario_id={} pressure_band={}",
            experiment_id,
            index,
            len(sources),
            source.scenario_id,
            source.global_pressure_band,
        )
        results.append(await _run_proposal(source))

    proposal_after_llm = _proposal_snapshot(scenario_ids)
    if proposal_before["by_scenario"] != proposal_after_llm["by_scenario"]:
        raise RuntimeError("Target proposal rows changed during no-persistence proposal execution")
    for filename, source_hash in source_hashes.items():
        if _sha256_file(BASECASE_DIR / filename) != source_hash:
            raise RuntimeError(f"Source Basecase changed during proposal execution: {filename}")

    created_at = datetime.now(tz=UTC).astimezone()
    with tempfile.TemporaryDirectory(prefix=f".{experiment_id}-", dir=output_root) as temp_name:
        temp_root = Path(temp_name)
        evidence_by_scenario = _export_workbooks(temp_root, results)
        proposal_after = _proposal_snapshot(scenario_ids)
        if proposal_before["by_scenario"] != proposal_after["by_scenario"]:
            raise RuntimeError("Target proposal rows changed during workbook export")
        for filename, source_hash in source_hashes.items():
            if _sha256_file(BASECASE_DIR / filename) != source_hash:
                raise RuntimeError(f"Source Basecase changed during workbook export: {filename}")
        report = _build_report(
            experiment_id=experiment_id,
            created_at=created_at,
            db_fingerprint=_database_fingerprint(),
            resource_paths=resource_paths,
            source_hashes=source_hashes,
            results=results,
            evidence_by_scenario=evidence_by_scenario,
            proposal_before=proposal_before,
            proposal_after=proposal_after,
        )
        (temp_root / "parameter_proposal_summary.md").write_text(report, encoding="utf-8")
        _promote_experiment(temp_root, final_root)

    logger.info(
        "v3 model-input export completed | experiment_id={} output={} scenarios={} workbooks={}",
        experiment_id,
        final_root,
        len(results),
        len(results) * len(MODEL_WORKBOOKS),
    )
    return final_root


def main() -> None:
    args = _parse_args()
    experiment_id = _validate_experiment_id(args.experiment_id)
    asyncio.run(_run(experiment_id, args.output_root, args.scenario_group_id))


if __name__ == "__main__":
    main()
