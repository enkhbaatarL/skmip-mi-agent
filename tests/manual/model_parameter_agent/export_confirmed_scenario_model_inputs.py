# Copyright (c) 2026 SK Innovation E&S.

"""Export LNG engine inputs from persisted, confirmed Model Parameter values.

This utility is intentionally deterministic and read-only with respect to the
metadata DB.  It does not invoke any proposal LLM node: the latest CONFIRMED
payload for every live scenario in one exact v3/v4 group is resolved back to a
single canonical Basecase cell, then applied to copies of the three model input
workbooks.
"""

from __future__ import annotations

# ruff: noqa: ANN401, ASYNC240, C901, E402, E501, EM101, EM102, TRY003
import argparse
import asyncio
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any


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
from sqlalchemy import select
from sqlalchemy.sql import Select

from apps.agents.model_parameter_agent.flows.propose_parameters.nodes import (
    _knowledge_base_from_context,
)
from apps.agents.model_parameter_agent.flows.propose_parameters.state import (
    ModelParameterProposalState,
)
from apps.agents.model_parameter_agent.persistence.model_parameter_service import (
    ModelParameterService,
)
from apps.agents.model_parameter_agent.utils.lut.catalog import LutCatalog
from apps.agents.model_parameter_agent.utils.lut.domain import (
    build_basecase_index,
    resolve_effective_reference,
)
from apps.agents.model_parameter_agent.utils.lut.models import (
    BasecaseReference,
    EffectiveReference,
    ReferenceLoadPolicy,
)
from apps.agents.model_parameter_agent.utils.lut.runtime import get_lut_catalog
from apps.agents.model_parameter_agent.utils.parameter_mapping import (
    _build_matrix_time_descriptors,
    _matrix_time_column_spec_from_candidate,
    basecase_slot_axis_names_from_candidate,
    basecase_value_field_name_from_candidate,
    build_basecase_records,
    match_parameter_candidates,
)
from apps.common.configs.config import get_settings
from apps.common.configs.database.sync_database.connection import get_sync_session
from apps.persistence.model_parameter.models import MiModelParamProposalModel
from apps.persistence.scenario.repository import ScenarioRepository
from apps.persistence.scenario_group.models import MiScenarioGroupModel
from tests.manual.model_parameter_agent.export_v3_scenario_model_inputs import (
    BASECASE_DIR,
    MODEL_WORKBOOKS,
    CellPatch,
    WorkbookEvidence,
    _database_fingerprint,
    _decimal_text,
    _finite_decimal,
    _initialize_packaged_resources,
    _normalized_axis,
    _parse_basecase_reference,
    _sha256_file,
    _text,
    _validate_workbook,
    _write_workbook,
)


SUPPORTED_GROUP_STRATEGIES = {
    "v3": "multi_event_composite_dimensions",
    "v4": "multi_event_model_lever_dimensions",
}
PRESSURE_TAGS = {
    "strong_bullish",
    "bullish",
    "balanced",
    "bearish",
    "strong_bearish",
}
PAYLOAD_VALUE_FIELDS = {
    "basecaseValue",
    "lutValue",
    "proposedValue",
    "rationale",
}
LUT_MATRIX_EXPORT_PARAMETERS = {"LiqProdAdjustment"}
MATRIX_TIME_AXES = ("Year", "Month", "Period")


@dataclass(frozen=True, slots=True)
class ConfirmedScenarioSource:
    api_version: str
    generation_strategy: str
    scenario_group_id: int
    group_title: str
    scenario_id: int
    scenario_title: str
    display_order: int
    global_pressure_band: str
    scenario_role: str | None
    model_param_proposal_id: int
    confirmed_dtm: str
    proposal_parameters: tuple[dict[str, Any], ...]
    proposal_payload_sha256: str
    context: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ConfirmedProposalResult:
    source: ConfirmedScenarioSource
    patches: tuple[CellPatch, ...]


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Export one exact v3/v4 scenario group's latest CONFIRMED Model Parameter values "
            "to three-workbook LNG engine input sets without LLM calls or DB writes."
        ),
    )
    parser.add_argument("--scenario-group-id", type=int, required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="New group directory to create; existing paths are rejected.",
    )
    return parser.parse_args(argv)


def _canonical_json_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
        allow_nan=False,
    ).encode("utf-8")
    return sha256(payload).hexdigest()


def _confirmed_rows_snapshot(scenario_group_id: int) -> dict[str, Any]:
    session = get_sync_session()
    try:
        rows = list(
            session.execute(
                select(MiModelParamProposalModel)
                .where(
                    MiModelParamProposalModel.scenario_group_id == scenario_group_id,
                    MiModelParamProposalModel.status == "CONFIRMED",
                    MiModelParamProposalModel.del_yn == "N",
                )
                .order_by(
                    MiModelParamProposalModel.scenario_id,
                    MiModelParamProposalModel.model_param_proposal_id,
                ),
            )
            .scalars()
            .all(),
        )
        items = [
            {
                "model_param_proposal_id": int(row.model_param_proposal_id),
                "scenario_id": int(row.scenario_id),
                "status": str(row.status),
                "confirmation_parameters_sha256": _canonical_json_sha256(
                    row.confirmation_parameters,
                ),
                "confirmed_dtm": row.confirmed_dtm.isoformat() if row.confirmed_dtm else None,
                "del_yn": str(row.del_yn),
            }
            for row in rows
        ]
        return {
            "row_count": len(items),
            "max_id": max(
                (item["model_param_proposal_id"] for item in items),
                default=None,
            ),
            "rows": items,
            "semantic_sha256": _canonical_json_sha256(items),
        }
    finally:
        session.close()


def _latest_confirmed_by_scenario(
    rows: Sequence[MiModelParamProposalModel],
) -> dict[int, MiModelParamProposalModel]:
    latest_by_scenario: dict[int, MiModelParamProposalModel] = {}
    for row in rows:
        scenario_id = int(row.scenario_id)
        current = latest_by_scenario.get(scenario_id)
        if current is None or int(row.model_param_proposal_id) > int(
            current.model_param_proposal_id,
        ):
            latest_by_scenario[scenario_id] = row
    return latest_by_scenario


def _validated_confirmation_parameters(
    proposal: MiModelParamProposalModel,
) -> tuple[dict[str, Any], ...]:
    parameters = proposal.confirmation_parameters
    if not isinstance(parameters, list) or not parameters:
        raise RuntimeError(
            "Latest CONFIRMED proposal must contain non-empty confirmation_parameters: "
            f"model_param_proposal_id={proposal.model_param_proposal_id}",
        )
    if any(not isinstance(parameter, dict) for parameter in parameters):
        raise RuntimeError(
            "Latest CONFIRMED confirmation_parameters must contain JSON objects only: "
            f"model_param_proposal_id={proposal.model_param_proposal_id}",
        )
    return tuple(dict(parameter) for parameter in parameters)


def _confirmed_proposals_statement(
    scenario_group_id: int,
) -> Select[tuple[MiModelParamProposalModel]]:
    return (
        select(MiModelParamProposalModel)
        .where(
            MiModelParamProposalModel.scenario_group_id == scenario_group_id,
            MiModelParamProposalModel.status == "CONFIRMED",
            MiModelParamProposalModel.del_yn == "N",
        )
        .order_by(
            MiModelParamProposalModel.scenario_id,
            MiModelParamProposalModel.model_param_proposal_id,
        )
    )


def _load_confirmed_group(scenario_group_id: int) -> list[ConfirmedScenarioSource]:
    session = get_sync_session()
    try:
        group = (
            session.execute(
                select(MiScenarioGroupModel).where(
                    MiScenarioGroupModel.scenario_group_id == scenario_group_id,
                    MiScenarioGroupModel.del_yn == "N",
                ),
            )
            .scalars()
            .one_or_none()
        )
        if group is None:
            raise RuntimeError(
                f"Live scenario group was not found: scenario_group_id={scenario_group_id}",
            )
        api_version = _text(group.api_version)
        generation_strategy = _text(group.generation_strategy)
        expected_strategy = SUPPORTED_GROUP_STRATEGIES.get(api_version)
        if expected_strategy is None or generation_strategy != expected_strategy:
            raise RuntimeError(
                "Only exact v3/v4 groups are supported: "
                f"scenario_group_id={scenario_group_id}, api_version={api_version or '-'}, "
                f"generation_strategy={generation_strategy or '-'}",
            )

        scenarios = ScenarioRepository(session=session).fetch_models_by_group_id(
            scenario_group_id,
        )
        if not scenarios:
            raise RuntimeError(
                f"Scenario group contains no live scenarios: scenario_group_id={scenario_group_id}",
            )
        rows = list(
            session.execute(
                _confirmed_proposals_statement(scenario_group_id),
            )
            .scalars()
            .all(),
        )
        latest_by_scenario = _latest_confirmed_by_scenario(rows)
        live_ids = {int(scenario.scenario_id) for scenario in scenarios}
        missing = sorted(live_ids.difference(latest_by_scenario))
        unexpected = sorted(set(latest_by_scenario).difference(live_ids))
        if missing or unexpected:
            raise RuntimeError(
                "Latest CONFIRMED proposal coverage must exactly match live group scenarios: "
                f"missing={missing}, unexpected={unexpected}",
            )

        group_title = _text(group.title)
        rows_to_resolve = []
        for scenario in scenarios:
            proposal = latest_by_scenario[int(scenario.scenario_id)]
            parameters = _validated_confirmation_parameters(proposal)
            rows_to_resolve.append((scenario, proposal, parameters))
    finally:
        session.close()

    service = ModelParameterService()
    sources: list[ConfirmedScenarioSource] = []
    for scenario, proposal, parameters in rows_to_resolve:
        pressure_band = _text(scenario.global_pressure_band)
        if pressure_band not in PRESSURE_TAGS:
            raise RuntimeError(
                "LNG engine scenario tag must be one of the supported pressure bands: "
                f"scenario_id={scenario.scenario_id}, global_pressure_band={pressure_band or '-'}",
            )
        context = service.load_context(int(scenario.scenario_id))
        context_group = context.get("scenario_group") or {}
        if (
            _text(context_group.get("api_version")) != api_version
            or _text(context_group.get("generation_strategy")) != generation_strategy
        ):
            raise RuntimeError(
                f"Loaded production context disagrees with the selected group: scenario_id={scenario.scenario_id}",
            )
        sources.append(
            ConfirmedScenarioSource(
                api_version=api_version,
                generation_strategy=generation_strategy,
                scenario_group_id=scenario_group_id,
                group_title=group_title,
                scenario_id=int(scenario.scenario_id),
                scenario_title=_text(scenario.title),
                display_order=int(scenario.display_order or 0),
                global_pressure_band=pressure_band,
                scenario_role=_text(scenario.scenario_role) or None,
                model_param_proposal_id=int(proposal.model_param_proposal_id),
                confirmed_dtm=(proposal.confirmed_dtm.isoformat() if proposal.confirmed_dtm else ""),
                proposal_parameters=parameters,
                proposal_payload_sha256=_canonical_json_sha256(parameters),
                context=context,
            ),
        )
    return sources


def _candidate_signature(candidate: Mapping[str, Any]) -> tuple[Any, ...]:
    return tuple(
        candidate.get(field_name)
        for field_name in (
            "model_file",
            "model_sheet",
            "model_table",
            "parameter_name",
            "canonical_parameter_name",
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
        )
    )


def _candidate_for_parameter(
    parameter: Mapping[str, Any],
    candidates: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    parameter_name = _text(parameter.get("parameterName"))
    target = parameter.get("modelTarget")
    if not parameter_name or not isinstance(target, Mapping):
        raise RuntimeError("Confirmed parameterName and modelTarget are required")
    model_file = _text(target.get("modelFile"))
    model_sheet = _text(target.get("modelSheet"))
    table_name = _text(target.get("tableName"))
    matching = [
        candidate
        for candidate in candidates
        if _text(
            candidate.get("canonical_parameter_name") or candidate.get("parameter_name"),
        )
        == parameter_name
        and _text(candidate.get("model_file")) == model_file
        and _text(candidate.get("model_sheet")) == model_sheet
        and _text(candidate.get("model_table")) == table_name
    ]
    unique = {_candidate_signature(candidate): candidate for candidate in matching}
    if len(unique) != 1:
        raise RuntimeError(
            "Confirmed parameter must resolve to one production candidate definition: "
            f"parameter={parameter_name}, target={model_file}/{model_sheet}/{table_name}, "
            f"matches={len(unique)}",
        )
    candidate = dict(next(iter(unique.values())))

    value_fields = target.get("valueFieldNames")
    slot_axes = target.get("slotAxesFieldNames")
    if not isinstance(value_fields, list) or not value_fields:
        raise RuntimeError(f"valueFieldNames must be a non-empty array: parameter={parameter_name}")
    if not isinstance(slot_axes, list) or not slot_axes:
        raise RuntimeError(f"slotAxesFieldNames must be a non-empty array: parameter={parameter_name}")
    if len(value_fields) != len(set(map(str, value_fields))):
        raise RuntimeError(f"valueFieldNames contains duplicates: parameter={parameter_name}")
    if len(slot_axes) != len(set(map(str, slot_axes))):
        raise RuntimeError(f"slotAxesFieldNames contains duplicates: parameter={parameter_name}")
    expected_value_field = basecase_value_field_name_from_candidate(candidate)
    if [str(value) for value in value_fields] != [expected_value_field]:
        raise RuntimeError(
            "Confirmed valueFieldNames disagrees with the canonical Basecase parser: "
            f"parameter={parameter_name}, confirmed={value_fields}, expected={[expected_value_field]}",
        )
    expected_axes = basecase_slot_axis_names_from_candidate(candidate)
    if set(map(str, slot_axes)) != set(expected_axes):
        raise RuntimeError(
            "Confirmed slotAxesFieldNames disagrees with the canonical Basecase parser: "
            f"parameter={parameter_name}, confirmed={slot_axes}, expected={expected_axes}",
        )
    return candidate


def _match_basecase_reference(
    *,
    parameter_name: str,
    slot_axes: Sequence[str],
    value: Mapping[str, Any],
    records: Sequence[BasecaseReference],
) -> tuple[BasecaseReference, dict[str, Any]]:
    coordinates = _validated_confirmed_coordinates(
        parameter_name=parameter_name,
        slot_axes=slot_axes,
        value=value,
    )
    matches: list[BasecaseReference] = []
    for record in records:
        record_coordinates = {**dict(record.axes), **dict(record.metadata)}
        if all(
            axis_name in record_coordinates
            and _normalized_axis(coordinates[axis_name], axis_name)
            == _normalized_axis(record_coordinates[axis_name], axis_name)
            for axis_name in slot_axes
        ):
            matches.append(record)
    if len(matches) != 1:
        raise RuntimeError(
            "Confirmed value must resolve to one exact canonical Basecase reference: "
            f"parameter={parameter_name}, coordinates={coordinates}, matches={len(matches)}",
        )
    reference = matches[0]
    if value.get("basecaseValue") is None or reference.value is None:
        raise RuntimeError(
            "Confirmed engine input requires a non-null canonical Basecase value: "
            f"parameter={parameter_name}, reference={reference.reference_id}",
        )
    confirmed_basecase = _finite_decimal(value.get("basecaseValue"))
    canonical_basecase = _finite_decimal(reference.value)
    if confirmed_basecase != canonical_basecase:
        raise RuntimeError(
            "Confirmed basecaseValue disagrees with the canonical Basecase cell: "
            f"parameter={parameter_name}, reference={reference.reference_id}, "
            f"confirmed={confirmed_basecase}, canonical={canonical_basecase}",
        )
    _finite_decimal(value.get("proposedValue"))
    return reference, coordinates


def _validated_confirmed_coordinates(
    *,
    parameter_name: str,
    slot_axes: Sequence[str],
    value: Mapping[str, Any],
) -> dict[str, Any]:
    missing_axes = [axis_name for axis_name in slot_axes if axis_name not in value]
    if missing_axes:
        raise RuntimeError(
            f"Confirmed value is missing slot coordinates: parameter={parameter_name}, missing={missing_axes}",
        )
    unexpected_axes = sorted(
        set(value).difference(PAYLOAD_VALUE_FIELDS).difference(slot_axes),
    )
    if unexpected_axes:
        raise RuntimeError(
            "Confirmed value contains coordinates not declared by slotAxesFieldNames: "
            f"parameter={parameter_name}, unexpected={unexpected_axes}",
        )
    return {axis_name: value[axis_name] for axis_name in slot_axes}


def _matrix_time_column_index(
    *,
    candidate: Mapping[str, Any],
) -> dict[tuple[Any, Any, Any], int]:
    parameter_name = _text(
        candidate.get("canonical_parameter_name") or candidate.get("parameter_name"),
    )
    model_file = _text(candidate.get("model_file"))
    sheet_name = _text(candidate.get("model_sheet"))
    filename = MODEL_WORKBOOKS.get(model_file)
    if filename is None:
        raise RuntimeError(
            f"Unsupported model file for LUT-backed matrix export: parameter={parameter_name}, model={model_file}",
        )
    spec = _matrix_time_column_spec_from_candidate(dict(candidate))
    if spec is None:
        raise RuntimeError(
            f"LUT-backed engine export requires a canonical matrix_time_columns target: parameter={parameter_name}",
        )

    source_path = BASECASE_DIR / filename
    workbook = load_workbook(
        source_path,
        read_only=True,
        data_only=True,
        keep_vba=False,
        keep_links=True,
    )
    try:
        if sheet_name not in workbook.sheetnames:
            raise RuntimeError(
                f"Canonical matrix sheet was not found: parameter={parameter_name}, sheet={sheet_name}",
            )
        worksheet = workbook[sheet_name]
        sheet_max_col = int(worksheet.max_column or 0)
        max_col = sheet_max_col
        if spec.value_end_col is not None:
            max_col = min(sheet_max_col, spec.value_end_col) if sheet_max_col else spec.value_end_col
        descriptors = _build_matrix_time_descriptors(
            worksheet,
            value_start_col=spec.value_start_col,
            max_col=max_col,
            year_row=spec.year_row,
            month_row=spec.month_row,
            period_row=spec.period_row,
        )
    finally:
        workbook.close()

    index: dict[tuple[Any, Any, Any], int] = {}
    for column, descriptor in descriptors.items():
        if spec.value_end_col is not None and column > spec.value_end_col:
            continue
        if any(descriptor.get(axis_name) is None for axis_name in MATRIX_TIME_AXES):
            continue
        key = tuple(_normalized_axis(descriptor[axis_name], axis_name) for axis_name in MATRIX_TIME_AXES)
        if key in index:
            raise RuntimeError(
                "Canonical matrix headers contain a duplicate Year/Month/Period slot: "
                f"parameter={parameter_name}, key={key}",
            )
        index[key] = column
    if not index:
        raise RuntimeError(
            f"Canonical matrix headers contain no exact time slots: parameter={parameter_name}",
        )
    return index


def _match_lut_backed_matrix_reference(
    *,
    parameter_name: str,
    candidate: Mapping[str, Any],
    slot_axes: Sequence[str],
    value: Mapping[str, Any],
    records: Sequence[BasecaseReference],
    effective_reference: EffectiveReference,
    time_columns: Mapping[tuple[Any, Any, Any], int],
) -> tuple[BasecaseReference, dict[str, Any]]:
    coordinates = _validated_confirmed_coordinates(
        parameter_name=parameter_name,
        slot_axes=slot_axes,
        value=value,
    )
    candidate_key = _text(candidate.get("candidate_key"))
    if effective_reference.candidate_key != candidate_key or effective_reference.parameter_name != parameter_name:
        raise RuntimeError(
            "Resolved LUT reference disagrees with the confirmed candidate: "
            f"parameter={parameter_name}, candidate={candidate_key}",
        )
    if effective_reference.effective_source != "lut" or effective_reference.actual_basecase_value is not None:
        raise RuntimeError(
            "Null-basecase matrix export requires an exact LUT-backed effective reference: "
            f"parameter={parameter_name}, source={effective_reference.effective_source}",
        )
    if value.get("basecaseValue") is not None:
        raise RuntimeError(
            f"LUT-backed matrix export requires basecaseValue=null: parameter={parameter_name}",
        )
    canonical_lut_value = effective_reference.lut_default_value
    if canonical_lut_value is None:
        raise RuntimeError(
            f"LUT-backed matrix export requires a non-null canonical LUT value: parameter={parameter_name}",
        )
    if "lutValue" in value and (
        value.get("lutValue") is None
        or _finite_decimal(value.get("lutValue"))
        != _finite_decimal(
            canonical_lut_value,
        )
    ):
        raise RuntimeError(
            f"Confirmed lutValue disagrees with the canonical exact LUT slot: parameter={parameter_name}",
        )
    _finite_decimal(value.get("proposedValue"))

    effective_coordinates = {
        **dict(effective_reference.axes),
        **dict(effective_reference.metadata),
    }
    coordinate_mismatches = [
        axis_name
        for axis_name, axis_value in coordinates.items()
        if axis_name not in effective_coordinates
        or _normalized_axis(axis_value, axis_name) != _normalized_axis(effective_coordinates[axis_name], axis_name)
    ]
    if coordinate_mismatches:
        raise RuntimeError(
            "Confirmed coordinates disagree with the canonical exact LUT slot: "
            f"parameter={parameter_name}, axes={coordinate_mismatches}",
        )

    metadata_reference_id = effective_reference.basecase_reference_id
    metadata_matches = [
        record
        for record in records
        if metadata_reference_id is not None and record.reference_id == metadata_reference_id
    ]
    if len(metadata_matches) != 1:
        raise RuntimeError(
            "LUT-backed matrix export requires one canonical same-row Basecase metadata reference: "
            f"parameter={parameter_name}, reference={metadata_reference_id or '-'}, "
            f"matches={len(metadata_matches)}",
        )
    metadata_reference = metadata_matches[0]
    metadata_coordinates = {
        **dict(metadata_reference.axes),
        **dict(metadata_reference.metadata),
    }
    static_mismatches = [
        axis_name
        for axis_name, axis_value in coordinates.items()
        if axis_name not in MATRIX_TIME_AXES
        and (
            axis_name not in metadata_coordinates
            or _normalized_axis(axis_value, axis_name) != _normalized_axis(metadata_coordinates[axis_name], axis_name)
        )
    ]
    if static_mismatches:
        raise RuntimeError(
            "Confirmed LUT slot disagrees with the canonical Basecase matrix row: "
            f"parameter={parameter_name}, axes={static_mismatches}",
        )

    model_file, sheet_name, row, _ = _parse_basecase_reference(
        metadata_reference.reference_id,
    )
    if model_file != _text(candidate.get("model_file")) or sheet_name != _text(candidate.get("model_sheet")):
        raise RuntimeError(
            "Canonical Basecase metadata reference disagrees with the candidate target: "
            f"parameter={parameter_name}, reference={metadata_reference.reference_id}",
        )
    time_key = tuple(_normalized_axis(coordinates[axis_name], axis_name) for axis_name in MATRIX_TIME_AXES)
    column = time_columns.get(time_key)
    if column is None:
        raise RuntimeError(
            "Confirmed LUT slot has no exact Year/Month/Period column in the Basecase matrix: "
            f"parameter={parameter_name}, key={time_key}",
        )
    target_reference_id = f"{model_file}:{sheet_name}:R{row}C{column}"
    return (
        BasecaseReference(
            candidate_key=candidate_key,
            parameter_name=parameter_name,
            canonical_key=effective_reference.canonical_slot_key,
            axes=effective_reference.axes,
            value=None,
            metadata=effective_reference.metadata,
            reference_id=target_reference_id,
        ),
        coordinates,
    )


def _patches_from_confirmed_source(
    source: ConfirmedScenarioSource,
    *,
    registry: Any,
) -> tuple[CellPatch, ...]:
    state = ModelParameterProposalState(
        scenario_id=source.scenario_id,
        scenario_context=source.context,
    )
    knowledge_base = _knowledge_base_from_context(state, source.context)
    candidates, _, warnings = match_parameter_candidates(
        knowledge_base,
        source.context,
    )
    if not candidates:
        raise RuntimeError(
            "Production candidate selector returned no candidates for confirmed scenario: "
            f"scenario_id={source.scenario_id}, warnings={warnings}",
        )
    settings = get_settings()
    policy = ReferenceLoadPolicy(
        start_year=settings.model_parameter_lut_horizon_start_year,
        end_year=settings.model_parameter_lut_horizon_end_year,
        value_max_decimal_places=settings.model_parameter_basecase_value_max_decimal_places,
        value_precision_mode=settings.model_parameter_basecase_value_precision_mode,
    )
    patches: list[CellPatch] = []
    seen_parameters: set[str] = set()
    seen_references: set[str] = set()
    lut_catalog: LutCatalog | None = None
    for parameter in source.proposal_parameters:
        parameter_name = _text(parameter.get("parameterName"))
        if parameter_name in seen_parameters:
            raise RuntimeError(
                f"Duplicate confirmed parameter is not allowed: parameter={parameter_name}",
            )
        seen_parameters.add(parameter_name)
        candidate = _candidate_for_parameter(parameter, candidates)
        basecase_records, basecase_warnings = build_basecase_records(
            knowledge_base,
            [candidate],
            source.context,
            registry=registry,
        )
        if not basecase_records:
            raise RuntimeError(
                "Canonical Basecase parser returned no records for confirmed parameter: "
                f"parameter={parameter_name}, warnings={basecase_warnings}",
            )
        basecase_index = build_basecase_index(
            basecase_records,
            [candidate],
            policy=policy,
            registry=registry,
        )
        candidate_key = _text(candidate.get("candidate_key"))
        references = list(basecase_index.records_for_candidate(candidate_key))
        target = parameter["modelTarget"]
        slot_axes = [str(value) for value in target["slotAxesFieldNames"]]
        values = parameter.get("values")
        if not isinstance(values, list) or not values:
            raise RuntimeError(
                f"Confirmed parameter values must be a non-empty array: parameter={parameter_name}",
            )
        time_columns: dict[tuple[Any, Any, Any], int] | None = None
        for value in values:
            if not isinstance(value, Mapping):
                raise TypeError(
                    f"Confirmed parameter values must contain objects: parameter={parameter_name}",
                )
            if parameter_name in LUT_MATRIX_EXPORT_PARAMETERS and value.get("basecaseValue") is None:
                if lut_catalog is None:
                    lut_catalog = get_lut_catalog(policy, registry=registry)
                effective_reference = resolve_effective_reference(
                    candidate_key,
                    value,
                    basecase_index,
                    lut_catalog,
                )
                if effective_reference is None:
                    raise RuntimeError(
                        "Confirmed LUT-backed value is absent from the canonical exact Basecase/LUT union: "
                        f"parameter={parameter_name}",
                    )
                if time_columns is None:
                    time_columns = _matrix_time_column_index(candidate=candidate)
                reference, coordinates = _match_lut_backed_matrix_reference(
                    parameter_name=parameter_name,
                    candidate=candidate,
                    slot_axes=slot_axes,
                    value=value,
                    records=references,
                    effective_reference=effective_reference,
                    time_columns=time_columns,
                )
            else:
                reference, coordinates = _match_basecase_reference(
                    parameter_name=parameter_name,
                    slot_axes=slot_axes,
                    value=value,
                    records=references,
                )
            if reference.reference_id in seen_references:
                raise RuntimeError(
                    f"Duplicate exact-cell confirmation is not allowed: {reference.reference_id}",
                )
            seen_references.add(reference.reference_id)
            model_file, sheet_name, row, column = _parse_basecase_reference(
                reference.reference_id,
            )
            if model_file != _text(target.get("modelFile")) or sheet_name != _text(target.get("modelSheet")):
                raise RuntimeError(
                    "Confirmed modelTarget disagrees with matched Basecase reference: "
                    f"target={target}, reference={reference.reference_id}",
                )
            if model_file not in MODEL_WORKBOOKS:
                raise RuntimeError(f"Unsupported model file in Basecase reference: {model_file}")
            patches.append(
                CellPatch(
                    model_file=model_file,
                    sheet_name=sheet_name,
                    row=row,
                    column=column,
                    parameter_name=parameter_name,
                    proposed_value=_finite_decimal(value.get("proposedValue")),
                    basecase_value=value.get("basecaseValue"),
                    lut_value=value.get("lutValue"),
                    coordinates=coordinates,
                    rationale=_text(value.get("rationale")),
                    basecase_reference_id=reference.reference_id,
                ),
            )
    if not patches:
        raise RuntimeError(
            f"CONFIRMED proposal generated no exportable Basecase cells: scenario_id={source.scenario_id}",
        )
    return tuple(
        sorted(
            patches,
            key=lambda patch: (
                patch.model_file,
                patch.sheet_name,
                patch.row,
                patch.column,
            ),
        ),
    )


def _scenario_directory(result: ConfirmedProposalResult) -> Path:
    return Path(
        f"scenario_{result.source.scenario_id}_{result.source.global_pressure_band}",
    )


def _export_workbooks(
    group_dir: Path,
    results: Sequence[ConfirmedProposalResult],
) -> dict[int, list[WorkbookEvidence]]:
    evidence_by_scenario: dict[int, list[WorkbookEvidence]] = {}
    for result in results:
        scenario_dir = group_dir / _scenario_directory(result)
        scenario_evidence: list[WorkbookEvidence] = []
        for model_file, filename in MODEL_WORKBOOKS.items():
            source_path = BASECASE_DIR / filename
            output_path = scenario_dir / filename
            workbook_patches = [patch for patch in result.patches if patch.model_file == model_file]
            modified_parts, formula_count, calc_chain_count = _write_workbook(
                source_path,
                output_path,
                workbook_patches,
            )
            scenario_evidence.append(
                _validate_workbook(
                    source_path,
                    output_path,
                    workbook_patches,
                    modified_parts,
                    formula_count,
                    calc_chain_count,
                ),
            )
        evidence_by_scenario[result.source.scenario_id] = scenario_evidence
    return evidence_by_scenario


def _report(
    *,
    created_at: datetime,
    results: Sequence[ConfirmedProposalResult],
    evidence_by_scenario: Mapping[int, Sequence[WorkbookEvidence]],
    source_hashes: Mapping[str, str],
    snapshot_before: Mapping[str, Any],
    snapshot_after: Mapping[str, Any],
    resource_fingerprint: str,
) -> str:
    first = results[0].source
    unchanged = snapshot_before == snapshot_after
    parameter_names = sorted(
        {patch.parameter_name for result in results for patch in result.patches},
    )
    lines = [
        "# Confirmed Model Parameter LNG 엔진 입력 Export 증적",
        "",
        f"- 생성 시각: `{created_at.astimezone().isoformat(timespec='seconds')}`",
        f"- 그룹: `{first.scenario_group_id}` / `{first.api_version}` / `{first.generation_strategy}`",
        f"- DB fingerprint: `{_database_fingerprint()}` (SELECT-only)",
        "- 원천 정책: live scenario별 `status='CONFIRMED' AND del_yn='N'` 중 최신 ID 1건의 `confirmation_parameters`만 사용",
        "- LLM 호출: `0` — 저장된 확정값을 재산정하지 않음",
        f"- 리소스 fingerprint: `{resource_fingerprint}`",
        f"- 현 DB mapping으로 산출된 parameter: `{', '.join(parameter_names)}`",
        "",
        "## Scenario 및 확정 payload",
        "",
        "| order | scenario | pressure tag / role | proposal ID | confirmed at | payload SHA-256 | cells |",
        "|---:|---:|---|---:|---|---|---:|",
    ]
    for result in results:
        source = result.source
        lines.append(
            f"| {source.display_order} | {source.scenario_id} | {source.global_pressure_band} / "
            f"{source.scenario_role or '-'} | {source.model_param_proposal_id} | "
            f"{source.confirmed_dtm or '-'} | `{source.proposal_payload_sha256}` | {len(result.patches)} |",
        )

    lines.extend(
        [
            "",
            "## 적용 셀",
            "",
            "| parameter | scenario | Basecase reference | coordinates | basecase | proposed |",
            "|---|---:|---|---|---:|---:|",
        ],
    )
    for result in results:
        for patch in result.patches:
            coordinate_text = ", ".join(f"{key}={value}" for key, value in patch.coordinates.items()).replace(
                "|",
                "\\|",
            )
            lines.append(
                f"| {patch.parameter_name} | {result.source.scenario_id} | "
                f"`{patch.basecase_reference_id}` | {coordinate_text} | "
                f"{patch.basecase_value} | {_decimal_text(patch.proposed_value)} |",
            )

    lines.extend(
        [
            "",
            "## 검증",
            "",
            f"- DB proposal 무변경: `{'PASS' if unchanged else 'FAIL'}` — confirmed row snapshot SHA-256 `{snapshot_before['semantic_sha256']}`",
            f"- 전체 proposal 관측값: `{snapshot_before['row_count']}/{snapshot_before['max_id']}` → `{snapshot_after['row_count']}/{snapshot_after['max_id']}` (confirmed row count/max-id)",
            "- 원본 Basecase 불변: `PASS` — "
            + ", ".join(f"{filename} `{digest}`" for filename, digest in source_hashes.items()),
            f"- XLSM 구조: `PASS` — {len(results) * len(MODEL_WORKBOOKS)}개 ZIP/member/VBA/비수정 part 및 제안 셀 dual read-back 검증",
        ],
    )
    for result in results:
        workbook_evidence = evidence_by_scenario[result.source.scenario_id]
        lines.append(
            f"- Scenario {result.source.scenario_id}: "
            + ", ".join(
                f"{item.filename} cells={item.patched_cell_count}, sha256={item.output_sha256}"
                for item in workbook_evidence
            ),
        )
    lines.extend(
        [
            "",
            "모든 `Year=YYYY` 좌표는 위 적용 셀 표에 명시되어 있으며, 이 파일은 LNG 엔진 evidence collector의 focus year 입력으로 사용할 수 있다.",
            "",
        ],
    )
    if not unchanged:
        raise RuntimeError("Confirmed proposal rows changed during SELECT-only export")
    return "\n".join(lines)


def _export_manifest(
    *,
    results: Sequence[ConfirmedProposalResult],
    evidence_by_scenario: Mapping[int, Sequence[WorkbookEvidence]],
    source_hashes: Mapping[str, str],
    snapshot: Mapping[str, Any],
    resource_fingerprint: str,
) -> dict[str, Any]:
    first = results[0].source
    return {
        "schema_version": "model-parameter-confirmed-engine-input-v1",
        "scenario_group": {
            "scenario_group_id": first.scenario_group_id,
            "api_version": first.api_version,
            "generation_strategy": first.generation_strategy,
        },
        "source_policy": "latest CONFIRMED confirmation_parameters per live scenario",
        "llm_call_count": 0,
        "resource_fingerprint": resource_fingerprint,
        "confirmed_snapshot_sha256": snapshot["semantic_sha256"],
        "basecase_workbooks": [
            {"filename": filename, "sha256": digest} for filename, digest in sorted(source_hashes.items())
        ],
        "scenarios": [
            {
                "scenario_id": result.source.scenario_id,
                "tag": result.source.global_pressure_band,
                "proposal_id": result.source.model_param_proposal_id,
                "proposal_payload_sha256": result.source.proposal_payload_sha256,
                "patches": [
                    {
                        "parameter_name": patch.parameter_name,
                        "basecase_reference_id": patch.basecase_reference_id,
                        "coordinates": patch.coordinates,
                        "basecase_value": patch.basecase_value,
                        "proposed_value": float(patch.proposed_value),
                    }
                    for patch in result.patches
                ],
                "workbooks": [
                    {
                        "filename": item.filename,
                        "sha256": item.output_sha256,
                        "patched_cell_count": item.patched_cell_count,
                        "byte_identical": item.byte_identical,
                    }
                    for item in evidence_by_scenario[result.source.scenario_id]
                ],
            }
            for result in results
        ],
    }


async def _run(scenario_group_id: int, output_dir: Path) -> Path:
    final_dir = output_dir.expanduser().resolve()
    if final_dir.exists():
        raise FileExistsError(f"Output directory already exists: {final_dir}")
    final_dir.parent.mkdir(parents=True, exist_ok=True)
    source_hashes = {filename: _sha256_file(BASECASE_DIR / filename) for filename in MODEL_WORKBOOKS.values()}
    resource_paths = await _initialize_packaged_resources()
    snapshot_before = _confirmed_rows_snapshot(scenario_group_id)
    sources = _load_confirmed_group(scenario_group_id)
    results = [
        ConfirmedProposalResult(
            source=source,
            patches=_patches_from_confirmed_source(
                source,
                registry=resource_paths.lut_registry,
            ),
        )
        for source in sources
    ]
    with tempfile.TemporaryDirectory(
        prefix=f".group-{scenario_group_id}-confirmed-",
        dir=final_dir.parent,
    ) as temp_name:
        temp_dir = Path(temp_name)
        evidence_by_scenario = _export_workbooks(temp_dir, results)
        snapshot_after = _confirmed_rows_snapshot(scenario_group_id)
        for filename, source_hash in source_hashes.items():
            if _sha256_file(BASECASE_DIR / filename) != source_hash:
                raise RuntimeError(
                    f"Source Basecase changed during confirmed export: {filename}",
                )
        resource_fingerprint = str(
            resource_paths.resource_fingerprint or resource_paths.semantic_schema_hash or "",
        )
        report = _report(
            created_at=datetime.now(tz=UTC),
            results=results,
            evidence_by_scenario=evidence_by_scenario,
            source_hashes=source_hashes,
            snapshot_before=snapshot_before,
            snapshot_after=snapshot_after,
            resource_fingerprint=resource_fingerprint,
        )
        (temp_dir / "parameter_proposal_summary.md").write_text(
            report,
            encoding="utf-8",
        )
        manifest = _export_manifest(
            results=results,
            evidence_by_scenario=evidence_by_scenario,
            source_hashes=source_hashes,
            snapshot=snapshot_before,
            resource_fingerprint=resource_fingerprint,
        )
        (temp_dir / "export_manifest.json").write_text(
            json.dumps(
                manifest,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
                allow_nan=False,
            )
            + "\n",
            encoding="utf-8",
        )
        temp_dir.rename(final_dir)
    return final_dir


def main() -> None:
    args = _parse_args()
    asyncio.run(_run(args.scenario_group_id, args.output_dir))


if __name__ == "__main__":
    main()
