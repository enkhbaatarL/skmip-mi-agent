# Copyright (c) 2026 SK Innovation E&S.
# ruff: noqa: ANN401, B904, C901, E402, E501, EM101, EM102, T201, TRY003

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import struct
import sys
import time
from typing import Any, Literal
import zlib


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

from sqlalchemy import select

from apps.common.configs.database.sync_database.connection import get_sync_session
from apps.persistence.scenario.models import MiScenarioModel
from apps.persistence.scenario_group.models import (
    MiScenarioGroupEventModel,
    MiScenarioGroupModel,
)
from tests.manual.model_parameter_agent.runner_common import (
    execute_proposal_and_confirmation,
    json_safe,
)


REPORT_DIR = ROOT_DIR / "tests" / "reports" / "model_parameter_agent"
V3_STRATEGY = "multi_event_composite_dimensions"
V4_STRATEGY = "multi_event_model_lever_dimensions"
MIN_COMPARISON_EVENT_COUNT = 2
MAX_COMPARISON_EVENT_COUNT = 5
Version = Literal["v3", "v4"]
Verdict = Literal["PASS", "FAIL", "NOT_EXECUTED"]


class ComparisonScopeError(RuntimeError):
    pass


@dataclass(frozen=True)
class ScenarioSnapshot:
    scenario_id: int
    title: str
    display_order: int
    scenario_role: str | None
    pressure_band: str | None
    baseline_yn: str
    status: str
    dimension_values: dict[str, Any] | tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class GroupSnapshot:
    scenario_group_id: int
    api_version: Version
    generation_strategy: str
    title: str
    status: str
    stage: str
    request_usr_id: int | None
    ordered_event_ids: tuple[int, ...]
    event_type_l2_ids: tuple[int, ...]
    scenarios: tuple[ScenarioSnapshot, ...]
    impact_catalog_version: str | None = None
    impact_catalog_checksum: str | None = None


@dataclass(frozen=True)
class ScenarioMatch:
    v3_scenario: ScenarioSnapshot | None
    v4_scenario: ScenarioSnapshot | None
    basis: str


def _enum_text(value: Any) -> str:
    raw = getattr(value, "value", value)
    return str(raw) if raw is not None else ""


def _has_valid_ordered_event_ids(group: GroupSnapshot) -> bool:
    event_ids = group.ordered_event_ids
    event_count = len(event_ids)
    return (
        MIN_COMPARISON_EVENT_COUNT <= event_count <= MAX_COMPARISON_EVENT_COUNT and len(set(event_ids)) == event_count
    )


def _has_matching_ordered_event_ids(v3_group: GroupSnapshot, v4_group: GroupSnapshot) -> bool:
    return (
        _has_valid_ordered_event_ids(v3_group)
        and _has_valid_ordered_event_ids(v4_group)
        and v3_group.ordered_event_ids == v4_group.ordered_event_ids
    )


def _scenario_snapshot(model: MiScenarioModel) -> ScenarioSnapshot:
    raw_dimensions = model.dimension_values
    if isinstance(raw_dimensions, Mapping):
        dimension_values: dict[str, Any] | tuple[dict[str, Any], ...] = json_safe(dict(raw_dimensions))
    elif isinstance(raw_dimensions, list):
        dimension_values = tuple(json_safe(dict(item)) for item in raw_dimensions if isinstance(item, Mapping))
    else:
        dimension_values = {}
    return ScenarioSnapshot(
        scenario_id=int(model.scenario_id),
        title=str(model.title or ""),
        display_order=int(model.display_order),
        scenario_role=(str(model.scenario_role) if model.scenario_role else None),
        pressure_band=(str(model.global_pressure_band) if model.global_pressure_band else None),
        baseline_yn=str(model.baseline_yn or "N"),
        status=_enum_text(model.status),
        dimension_values=dimension_values,
    )


def load_group_snapshots(session: Any) -> list[GroupSnapshot]:
    groups = (
        session.execute(
            select(MiScenarioGroupModel)
            .where(
                MiScenarioGroupModel.del_yn == "N",
                (
                    (
                        (MiScenarioGroupModel.api_version == "v3")
                        & (MiScenarioGroupModel.generation_strategy == V3_STRATEGY)
                    )
                    | (
                        (MiScenarioGroupModel.api_version == "v4")
                        & (MiScenarioGroupModel.generation_strategy == V4_STRATEGY)
                    )
                ),
            )
            .order_by(MiScenarioGroupModel.scenario_group_id.desc()),
        )
        .scalars()
        .all()
    )
    snapshots: list[GroupSnapshot] = []
    for group in groups:
        group_id = int(group.scenario_group_id)
        relations = (
            session.execute(
                select(MiScenarioGroupEventModel)
                .where(
                    MiScenarioGroupEventModel.scenario_group_id == group_id,
                    MiScenarioGroupEventModel.del_yn == "N",
                )
                .order_by(
                    MiScenarioGroupEventModel.display_order,
                    MiScenarioGroupEventModel.scenario_group_event_id,
                ),
            )
            .scalars()
            .all()
        )
        scenarios = (
            session.execute(
                select(MiScenarioModel)
                .where(
                    MiScenarioModel.scenario_group_id == group_id,
                    MiScenarioModel.del_yn == "N",
                )
                .order_by(MiScenarioModel.display_order, MiScenarioModel.scenario_id),
            )
            .scalars()
            .all()
        )
        snapshots.append(
            GroupSnapshot(
                scenario_group_id=group_id,
                api_version=str(group.api_version),
                generation_strategy=str(group.generation_strategy),
                title=str(group.title or ""),
                status=_enum_text(group.status),
                stage=_enum_text(group.stage),
                request_usr_id=(int(group.request_usr_id) if group.request_usr_id is not None else None),
                ordered_event_ids=tuple(int(row.mi_event_id) for row in relations),
                event_type_l2_ids=tuple(int(row.event_type_l2_id) for row in relations),
                scenarios=tuple(_scenario_snapshot(row) for row in scenarios),
                impact_catalog_version=(str(group.impact_catalog_version) if group.impact_catalog_version else None),
                impact_catalog_checksum=(str(group.impact_catalog_checksum) if group.impact_catalog_checksum else None),
            ),
        )
    return snapshots


def select_group_pair(
    groups: Sequence[GroupSnapshot],
    *,
    v3_group_id: int | None = None,
    v4_group_id: int | None = None,
) -> tuple[GroupSnapshot, GroupSnapshot]:
    by_id = {group.scenario_group_id: group for group in groups}
    explicit_v3 = by_id.get(v3_group_id) if v3_group_id is not None else None
    explicit_v4 = by_id.get(v4_group_id) if v4_group_id is not None else None
    if v3_group_id is not None and explicit_v3 is None:
        raise ComparisonScopeError(f"v3 scenario group을 찾을 수 없습니다: {v3_group_id}")
    if v4_group_id is not None and explicit_v4 is None:
        raise ComparisonScopeError(f"v4 scenario group을 찾을 수 없습니다: {v4_group_id}")
    if explicit_v3 is not None and explicit_v3.api_version != "v3":
        raise ComparisonScopeError(f"scenario_group_id={v3_group_id}는 v3가 아닙니다")
    if explicit_v4 is not None and explicit_v4.api_version != "v4":
        raise ComparisonScopeError(f"scenario_group_id={v4_group_id}는 v4가 아닙니다")

    v3_groups = [
        group
        for group in groups
        if group.api_version == "v3" and group.generation_strategy == V3_STRATEGY and group.scenarios
    ]
    v4_groups = [
        group
        for group in groups
        if group.api_version == "v4" and group.generation_strategy == V4_STRATEGY and group.scenarios
    ]
    if explicit_v3 is not None:
        v3_groups = [explicit_v3]
    if explicit_v4 is not None:
        v4_groups = [explicit_v4]

    pairs = [
        (v3_group, v4_group)
        for v3_group in v3_groups
        for v4_group in v4_groups
        if _has_matching_ordered_event_ids(v3_group, v4_group)
    ]
    if not pairs:
        detail = []
        if explicit_v3 is not None:
            detail.append(f"v3={explicit_v3.scenario_group_id}, events={list(explicit_v3.ordered_event_ids)}")
        if explicit_v4 is not None:
            detail.append(f"v4={explicit_v4.scenario_group_id}, events={list(explicit_v4.ordered_event_ids)}")
        suffix = f" ({'; '.join(detail)})" if detail else ""
        raise ComparisonScopeError(
            f"동일 원천 Event 집합을 가진 v3/v4 그룹 쌍이 없습니다 (요건: 표시 순서 일치, 중복 없이 2~5개){suffix}",
        )
    return max(
        pairs,
        key=lambda pair: (
            max(pair[0].scenario_group_id, pair[1].scenario_group_id),
            pair[0].scenario_group_id,
            pair[1].scenario_group_id,
        ),
    )


def match_scenarios(v3_group: GroupSnapshot, v4_group: GroupSnapshot) -> list[ScenarioMatch]:
    unmatched_v3 = list(v3_group.scenarios)
    unmatched_v4 = list(v4_group.scenarios)
    matches: list[ScenarioMatch] = []

    def consume(field_name: str, basis: str) -> None:
        for v3_scenario in list(unmatched_v3):
            key = getattr(v3_scenario, field_name)
            if not key:
                continue
            v4_scenario = next(
                (candidate for candidate in unmatched_v4 if getattr(candidate, field_name) == key),
                None,
            )
            if v4_scenario is None:
                continue
            unmatched_v3.remove(v3_scenario)
            unmatched_v4.remove(v4_scenario)
            matches.append(ScenarioMatch(v3_scenario, v4_scenario, f"{basis}={key}"))

    consume("scenario_role", "scenarioRole")
    consume("pressure_band", "pressureBand")
    v3_baseline = next((item for item in unmatched_v3 if item.baseline_yn == "Y"), None)
    v4_baseline = next((item for item in unmatched_v4 if item.baseline_yn == "Y"), None)
    if v3_baseline is not None and v4_baseline is not None:
        unmatched_v3.remove(v3_baseline)
        unmatched_v4.remove(v4_baseline)
        matches.append(ScenarioMatch(v3_baseline, v4_baseline, "baselineYn=Y"))
    while unmatched_v3 and unmatched_v4:
        matches.append(ScenarioMatch(unmatched_v3.pop(0), unmatched_v4.pop(0), "displayOrder"))
    matches.extend(ScenarioMatch(item, None, "v3-only") for item in unmatched_v3)
    matches.extend(ScenarioMatch(None, item, "v4-only") for item in unmatched_v4)
    return matches


async def create_counterpart(
    source: GroupSnapshot,
    *,
    target_version: Version,
    user_id: int,
) -> int:
    if not source.ordered_event_ids:
        raise ComparisonScopeError("counterpart 생성에 사용할 원천 Event가 없습니다")
    if target_version == "v3":
        from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.api_schema import (
            MultiEventCreateScenariosIn,
        )
        from apps.agents.scenario_group_agent.routers.versioned_scenario_generation_sync import (
            create_v3_scenarios_sync,
        )

        output = await create_v3_scenarios_sync(
            MultiEventCreateScenariosIn(mi_event_ids=list(source.ordered_event_ids), user_id=user_id),
        )
    else:
        from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.api_schema import (
            V4MultiEventCreateScenariosSyncIn,
        )
        from apps.agents.scenario_group_agent.routers.versioned_scenario_generation_sync import (
            create_v4_scenarios_sync,
        )

        output = await create_v4_scenarios_sync(
            V4MultiEventCreateScenariosSyncIn(mi_event_ids=list(source.ordered_event_ids), user_id=user_id),
        )
    if output.status != "success" or output.data is None:
        raise ComparisonScopeError(
            f"{target_version} counterpart 생성 실패: status={output.status}, message={output.message}",
        )
    group_id = output.data.scenario_group.scenario_group_id
    if group_id is None:
        raise ComparisonScopeError(f"{target_version} counterpart 응답에 scenario_group_id가 없습니다")
    return int(group_id)


async def _execute_scenario(scenario_id: int, *, retries: int) -> dict[str, Any]:
    started = time.perf_counter()
    attempts: list[dict[str, Any]] = []
    for attempt_index in range(retries + 1):
        attempt_started = time.perf_counter()
        try:
            record = await execute_proposal_and_confirmation(scenario_id)
        except Exception as exc:
            attempts.append(
                {
                    "attempt": attempt_index + 1,
                    "status": "FAIL",
                    "elapsed_seconds": time.perf_counter() - attempt_started,
                    "error": " ".join(str(exc).split())[:1000],
                },
            )
            if attempt_index < retries:
                await asyncio.sleep(2.0 * (attempt_index + 1))
                continue
            return {
                "scenario_id": scenario_id,
                "error": attempts[-1]["error"],
                "attempts": attempts,
                "elapsed_seconds": time.perf_counter() - started,
                "llm_calls": [],
            }
        attempts.append(
            {
                "attempt": attempt_index + 1,
                "status": "PASS",
                "elapsed_seconds": time.perf_counter() - attempt_started,
            },
        )
        record["attempts"] = attempts
        record["elapsed_seconds"] = time.perf_counter() - started
        return record
    raise AssertionError("unreachable")


async def execute_pair(
    v3_group: GroupSnapshot,
    v4_group: GroupSnapshot,
    *,
    retries: int,
) -> tuple[dict[int, dict[str, Any]], dict[str, Any]]:
    from tests.manual.model_parameter_agent.evaluate_event_type_proposals import (
        _run_invalid_status_confirmation,
    )
    from tests.manual.model_parameter_agent.evaluate_proposals import (
        _ensure_model_parameter_test_resource_runtime,
    )

    await _ensure_model_parameter_test_resource_runtime()
    records: dict[int, dict[str, Any]] = {}
    for group in (v3_group, v4_group):
        for scenario in group.scenarios:
            records[scenario.scenario_id] = await _execute_scenario(
                scenario.scenario_id,
                retries=retries,
            )
    successful_records = [record for record in records.values() if not record.get("error")]
    invalid_status = await _run_invalid_status_confirmation(successful_records)
    return records, invalid_status


def _proposal_parameters(record: Mapping[str, Any]) -> list[dict[str, Any]]:
    row = record.get("proposal_db_row") or {}
    parameters = row.get("proposal_parameters") if isinstance(row, Mapping) else None
    return [dict(item) for item in parameters or [] if isinstance(item, Mapping)]


def _parameter_names(record: Mapping[str, Any]) -> set[str]:
    return {
        str(parameter.get("parameterName") or parameter.get("parameter_name") or "")
        for parameter in _proposal_parameters(record)
        if parameter.get("parameterName") or parameter.get("parameter_name")
    }


def _slot_values(record: Mapping[str, Any]) -> dict[tuple[str, str, str, str], Any]:
    result: dict[tuple[str, str, str, str], Any] = {}
    for parameter in _proposal_parameters(record):
        parameter_name = str(parameter.get("parameterName") or parameter.get("parameter_name") or "")
        target = parameter.get("modelTarget") or parameter.get("model_target") or {}
        if not isinstance(target, Mapping):
            target = {}
        axes = target.get("slotAxesFieldNames") or target.get("slot_axes_field_names") or []
        model_file = str(target.get("modelFile") or target.get("model_file") or "")
        model_sheet = str(target.get("modelSheet") or target.get("model_sheet") or "")
        for value in parameter.get("values") or []:
            if not isinstance(value, Mapping):
                continue
            coordinates = {str(axis): json_safe(value.get(str(axis))) for axis in axes}
            coordinate_key = json.dumps(coordinates, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            result[(parameter_name, model_file, model_sheet, coordinate_key)] = value.get(
                "proposedValue",
                value.get("proposed_value"),
            )
    return result


def _usage_metrics(record: Mapping[str, Any]) -> dict[str, int | None]:
    calls = [item for item in record.get("llm_calls") or [] if isinstance(item, Mapping)]
    if not calls:
        return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "call_count": 0}
    totals = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    for call in calls:
        usage = call.get("usage") or {}
        if not isinstance(usage, Mapping):
            return {**dict.fromkeys(totals), "call_count": len(calls)}
        for key in totals:
            raw = usage.get(key)
            if raw is None:
                return {**dict.fromkeys(totals), "call_count": len(calls)}
            totals[key] += int(raw)
    return {**totals, "call_count": len(calls)}


def _record_passes(
    record: Mapping[str, Any],
    *,
    scenario_id: int | None = None,
    scenario_group_id: int | None = None,
) -> bool:
    row = record.get("proposal_db_row") or {}
    confirmation = record.get("confirmation") or {}
    elapsed = record.get("elapsed_seconds")
    row_identity_matches = bool(
        isinstance(row, Mapping)
        and (scenario_id is None or row.get("scenario_id") == scenario_id)
        and (scenario_group_id is None or row.get("scenario_group_id") == scenario_group_id),
    )
    return bool(
        not record.get("error")
        and row_identity_matches
        and row.get("status") == "CONFIRMED"
        and _proposal_parameters(record)
        and isinstance(confirmation, Mapping)
        and confirmation.get("status") == "PASS"
        and isinstance(elapsed, int | float)
        and elapsed <= 180,
    )


def _version_metrics(group: GroupSnapshot, records: Mapping[int, Mapping[str, Any]]) -> dict[str, Any]:
    selected = [(item, records.get(item.scenario_id) or {}) for item in group.scenarios]
    elapsed_values = [
        float(record["elapsed_seconds"])
        for _, record in selected
        if isinstance(record.get("elapsed_seconds"), int | float)
    ]
    token_values = [_usage_metrics(record)["total_tokens"] for _, record in selected]
    complete_tokens = [int(value) for value in token_values if value is not None]
    return {
        "scenario_count": len(selected),
        "pass_count": sum(
            _record_passes(
                record,
                scenario_id=scenario.scenario_id,
                scenario_group_id=group.scenario_group_id,
            )
            for scenario, record in selected
        ),
        "parameter_count": sum(len(_proposal_parameters(record)) for _, record in selected),
        "elapsed_seconds": sum(elapsed_values),
        "average_elapsed_seconds": (sum(elapsed_values) / len(elapsed_values) if elapsed_values else None),
        "total_tokens": (sum(complete_tokens) if len(complete_tokens) == len(selected) else None),
    }


def _comparison_metrics(
    match: ScenarioMatch,
    records: Mapping[int, Mapping[str, Any]],
) -> dict[str, Any]:
    v3_record = records.get(match.v3_scenario.scenario_id) or {} if match.v3_scenario is not None else {}
    v4_record = records.get(match.v4_scenario.scenario_id) or {} if match.v4_scenario is not None else {}
    v3_parameters = _parameter_names(v3_record)
    v4_parameters = _parameter_names(v4_record)
    v3_slots = _slot_values(v3_record)
    v4_slots = _slot_values(v4_record)
    common_slot_keys = set(v3_slots) & set(v4_slots)
    return {
        "v3_parameters": v3_parameters,
        "v4_parameters": v4_parameters,
        "common_parameters": v3_parameters & v4_parameters,
        "v3_only_parameters": v3_parameters - v4_parameters,
        "v4_only_parameters": v4_parameters - v3_parameters,
        "common_slots": len(common_slot_keys),
        "different_common_slot_values": sum(v3_slots[key] != v4_slots[key] for key in common_slot_keys),
    }


def overall_verdict(
    *,
    execute: bool,
    v3_group: GroupSnapshot,
    v4_group: GroupSnapshot,
    records: Mapping[int, Mapping[str, Any]],
    invalid_status: Mapping[str, Any] | None,
) -> Verdict:
    if not execute:
        return "NOT_EXECUTED"
    versioned_scenarios = [
        *[(v3_group, scenario) for scenario in v3_group.scenarios],
        *[(v4_group, scenario) for scenario in v4_group.scenarios],
    ]
    proposal_ids: list[Any] = []
    for _, scenario in versioned_scenarios:
        row = (records.get(scenario.scenario_id) or {}).get("proposal_db_row") or {}
        proposal_ids.append(row.get("model_param_proposal_id") if isinstance(row, Mapping) else None)
    invalid_status_ok = bool(invalid_status and invalid_status.get("status") == "PASS")
    if (
        _has_matching_ordered_event_ids(v3_group, v4_group)
        and versioned_scenarios
        and all(proposal_id is not None for proposal_id in proposal_ids)
        and len(set(proposal_ids)) == len(proposal_ids)
        and all(
            _record_passes(
                records.get(scenario.scenario_id) or {},
                scenario_id=scenario.scenario_id,
                scenario_group_id=group.scenario_group_id,
            )
            for group, scenario in versioned_scenarios
        )
        and invalid_status_ok
    ):
        return "PASS"
    return "FAIL"


_FONT_5X7: dict[str, tuple[str, ...]] = {
    " ": ("00000",) * 7,
    "%": ("11001", "11010", "00100", "01000", "10110", "00110", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "00110", "00110"),
    ",": ("00000", "00000", "00000", "00000", "00110", "00110", "00100"),
    "/": ("00001", "00010", "00100", "01000", "10000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    ":": ("00000", "00110", "00110", "00000", "00110", "00110", "00000"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "10000", "11110", "00001", "00001", "11110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01110"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "10010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
}


def _fill_rect(
    pixels: bytearray,
    *,
    width: int,
    height: int,
    x: int,
    y: int,
    rect_width: int,
    rect_height: int,
    color: tuple[int, int, int],
) -> None:
    left = max(0, x)
    top = max(0, y)
    right = min(width, x + rect_width)
    bottom = min(height, y + rect_height)
    row_color = bytes(color) * max(0, right - left)
    for row in range(top, bottom):
        offset = (row * width + left) * 3
        pixels[offset : offset + len(row_color)] = row_color


def _draw_text(
    pixels: bytearray,
    *,
    width: int,
    height: int,
    x: int,
    y: int,
    text: str,
    scale: int,
    color: tuple[int, int, int],
) -> None:
    cursor = x
    for character in text.upper():
        pattern = _FONT_5X7.get(character, _FONT_5X7[" "])
        for row_index, row in enumerate(pattern):
            for column_index, bit in enumerate(row):
                if bit == "1":
                    _fill_rect(
                        pixels,
                        width=width,
                        height=height,
                        x=cursor + column_index * scale,
                        y=y + row_index * scale,
                        rect_width=scale,
                        rect_height=scale,
                        color=color,
                    )
        cursor += 6 * scale


def _png_chunk(chunk_type: bytes, payload: bytes) -> bytes:
    checksum = zlib.crc32(chunk_type)
    checksum = zlib.crc32(payload, checksum)
    return struct.pack(">I", len(payload)) + chunk_type + payload + struct.pack(">I", checksum & 0xFFFFFFFF)


def _write_rgb_png(path: Path, *, width: int, height: int, pixels: bytearray) -> None:
    scanlines = b"".join(b"\x00" + bytes(pixels[row * width * 3 : (row + 1) * width * 3]) for row in range(height))
    payload = b"".join(
        (
            b"\x89PNG\r\n\x1a\n",
            _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)),
            _png_chunk(b"IDAT", zlib.compress(scanlines, level=9)),
            _png_chunk(b"IEND", b""),
        ),
    )
    path.write_bytes(payload)


def render_dashboard(
    *,
    output_path: Path,
    v3_metrics: Mapping[str, Any],
    v4_metrics: Mapping[str, Any],
) -> None:
    width, height = 1200, 760
    pixels = bytearray((248, 250, 252)) * width * height
    ink = (31, 45, 61)
    muted = (103, 116, 130)
    panel = (255, 255, 255)
    border = (214, 222, 231)
    colors = ((49, 90, 125), (43, 122, 103))
    _draw_text(
        pixels,
        width=width,
        height=height,
        x=88,
        y=34,
        text="MODEL PARAMETER AGENT V3 / V4 E2E COMPARISON",
        scale=3,
        color=ink,
    )
    metrics = [v3_metrics, v4_metrics]
    panels = (
        ("E2E PASS RATE %", [100 * item["pass_count"] / max(1, item["scenario_count"]) for item in metrics]),
        ("PROPOSAL PARAMETER COUNT", [item["parameter_count"] for item in metrics]),
        ("AVERAGE ELAPSED SEC", [item["average_elapsed_seconds"] or 0 for item in metrics]),
        ("TOTAL TOKENS", [item["total_tokens"] or 0 for item in metrics]),
    )
    for panel_index, (title, values) in enumerate(panels):
        column = panel_index % 2
        row = panel_index // 2
        panel_x = 60 + column * 570
        panel_y = 112 + row * 310
        _fill_rect(
            pixels,
            width=width,
            height=height,
            x=panel_x,
            y=panel_y,
            rect_width=510,
            rect_height=270,
            color=border,
        )
        _fill_rect(
            pixels,
            width=width,
            height=height,
            x=panel_x + 2,
            y=panel_y + 2,
            rect_width=506,
            rect_height=266,
            color=panel,
        )
        _draw_text(
            pixels,
            width=width,
            height=height,
            x=panel_x + 24,
            y=panel_y + 20,
            text=title,
            scale=2,
            color=ink,
        )
        baseline = panel_y + 224
        _fill_rect(
            pixels,
            width=width,
            height=height,
            x=panel_x + 38,
            y=baseline,
            rect_width=434,
            rect_height=2,
            color=border,
        )
        maximum = max(float(value) for value in values) or 1.0
        for version_index, value in enumerate(values):
            bar_height = int(138 * float(value) / maximum)
            bar_x = panel_x + 118 + version_index * 190
            _fill_rect(
                pixels,
                width=width,
                height=height,
                x=bar_x,
                y=baseline - bar_height,
                rect_width=86,
                rect_height=bar_height,
                color=colors[version_index],
            )
            value_label = f"{float(value):,.1f}" if isinstance(value, float) else f"{int(value):,}"
            _draw_text(
                pixels,
                width=width,
                height=height,
                x=bar_x - 5,
                y=max(panel_y + 58, baseline - bar_height - 22),
                text=value_label,
                scale=2,
                color=muted,
            )
            _draw_text(
                pixels,
                width=width,
                height=height,
                x=bar_x + 28,
                y=baseline + 14,
                text=f"V{version_index + 3}",
                scale=2,
                color=ink,
            )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _write_rgb_png(output_path, width=width, height=height, pixels=pixels)


def _md(value: Any) -> str:
    return str(value if value is not None else "-").replace("|", "\\|").replace("\n", " ")


def _set_text(values: set[str]) -> str:
    return ", ".join(sorted(values)) if values else "-"


def _duration(value: Any) -> str:
    return f"{float(value):,.3f}s" if isinstance(value, int | float) else "N/A"


def _tokens_text(metrics: Mapping[str, Any]) -> str:
    values = (metrics.get("prompt_tokens"), metrics.get("completion_tokens"), metrics.get("total_tokens"))
    if any(value is None for value in values):
        return "N/A"
    return " / ".join(f"{int(value):,}" for value in values)


def render_report(
    *,
    started_at: datetime,
    finished_at: datetime,
    execute: bool,
    v3_group: GroupSnapshot,
    v4_group: GroupSnapshot,
    records: Mapping[int, Mapping[str, Any]],
    invalid_status: Mapping[str, Any] | None,
    dashboard_name: str,
    created_group_ids: Sequence[int] = (),
) -> tuple[str, Verdict]:
    matches = match_scenarios(v3_group, v4_group)
    v3_metrics = _version_metrics(v3_group, records)
    v4_metrics = _version_metrics(v4_group, records)
    verdict = overall_verdict(
        execute=execute,
        v3_group=v3_group,
        v4_group=v4_group,
        records=records,
        invalid_status=invalid_status,
    )
    lines = [
        "# Model Parameter Agent v3/v4 비교 검증 보고서",
        "",
        f"- 문서 상태: **{verdict}**",
        f"- 검증 시작: {started_at.isoformat(timespec='seconds')}",
        f"- 검증 종료: {finished_at.isoformat(timespec='seconds')}",
        f"- 실행 모드: {'proposal + confirmation E2E' if execute else 'read-only scope verification'}",
        "- 데이터베이스 경계: v3/v4가 동일 DB를 사용하며 proposal 행은 공통 테이블에 저장",
        f"- 본 실행에서 생성한 scenario group: {list(created_group_ids) if created_group_ids else '없음'}",
        "- 산출물 형식: Markdown 및 PNG만 생성",
        "",
        "## 1. 종합 판정",
        "",
        (
            "동일 원천 Event 집합을 가진 v3/v4 그룹에 대해 모든 proposal·confirmation·DB read-back 계약이 "
            "충족되었습니다."
            if verdict == "PASS"
            else (
                "대상 그룹의 동등성은 확인했으며 실제 proposal·confirmation은 실행하지 않았습니다."
                if verdict == "NOT_EXECUTED"
                else "한 개 이상의 proposal·confirmation·DB read-back 계약이 충족되지 않았습니다."
            )
        ),
        "",
        f"![v3/v4 비교 요약]({dashboard_name})",
        "",
        "| 버전 | 그룹 ID | 시나리오 | E2E PASS | 제안 파라미터 | 평균 소요시간 | Token 합계 |",
        "|---|---:|---:|---:|---:|---:|---:|",
        (
            f"| v3 | {v3_group.scenario_group_id} | {v3_metrics['scenario_count']} | "
            f"{v3_metrics['pass_count']} | {v3_metrics['parameter_count']} | "
            f"{_duration(v3_metrics['average_elapsed_seconds'])} | "
            f"{v3_metrics['total_tokens'] if v3_metrics['total_tokens'] is not None else 'N/A'} |"
        ),
        (
            f"| v4 | {v4_group.scenario_group_id} | {v4_metrics['scenario_count']} | "
            f"{v4_metrics['pass_count']} | {v4_metrics['parameter_count']} | "
            f"{_duration(v4_metrics['average_elapsed_seconds'])} | "
            f"{v4_metrics['total_tokens'] if v4_metrics['total_tokens'] is not None else 'N/A'} |"
        ),
        "",
        "## 2. 비교 대상 및 동등성 통제",
        "",
        f"- 원천 Event 순서: `{list(v3_group.ordered_event_ids)}`",
        (f"- Event 순서·구성 일치: **{'PASS' if _has_matching_ordered_event_ids(v3_group, v4_group) else 'FAIL'}**"),
        (
            "- Event ID 제약(중복 없음, 2~5개): "
            f"**{'PASS' if _has_valid_ordered_event_ids(v3_group) and _has_valid_ordered_event_ids(v4_group) else 'FAIL'}**"
        ),
        (
            "- Event 표시 순서 일치: "
            f"**{'PASS' if v3_group.ordered_event_ids == v4_group.ordered_event_ids else 'REVIEW'}** "
            f"(v3={list(v3_group.ordered_event_ids)}, v4={list(v4_group.ordered_event_ids)})"
        ),
        (
            "- 비교 원칙: 생성 엔진이 서로 다른 두 그룹을 Event 집합으로 고정하고, scenarioRole → pressureBand → "
            "baseline → displayOrder 순으로 시나리오를 대응"
        ),
        (
            "- 해석 원칙: v3와 v4의 Dimension 체계가 다르므로 동일 parameter/slot 여부는 결과 동등성 판정이 아니라 "
            "차이 분석 지표로 사용"
        ),
        "",
        "| 항목 | v3 | v4 |",
        "|---|---|---|",
        f"| scenario_group_id | {v3_group.scenario_group_id} | {v4_group.scenario_group_id} |",
        f"| generation_strategy | `{v3_group.generation_strategy}` | `{v4_group.generation_strategy}` |",
        f"| status / stage | {_md(v3_group.status)} / {_md(v3_group.stage)} | {_md(v4_group.status)} / {_md(v4_group.stage)} |",
        f"| title | {_md(v3_group.title)} | {_md(v4_group.title)} |",
        f"| Impact Lever catalog | N/A | {_md(v4_group.impact_catalog_version)} / `{_md(v4_group.impact_catalog_checksum)}` |",
        "",
        "## 3. Proposal 및 Confirmation E2E 결과",
        "",
        "| 버전 | scenario_id | 역할 / 압력 | proposal_id | DB 상태 | 파라미터 | Confirmation | 소요시간 | Token (입력/출력/합계) | 판정 |",
        "|---|---:|---|---:|---|---|---|---:|---:|---|",
    ]
    for version, group in (("v3", v3_group), ("v4", v4_group)):
        for scenario in group.scenarios:
            record = records.get(scenario.scenario_id) or {}
            row = record.get("proposal_db_row") or {}
            confirmation = record.get("confirmation") or {}
            proposal_id = row.get("model_param_proposal_id", "-") if isinstance(row, Mapping) else "-"
            db_status = row.get("status", "-") if isinstance(row, Mapping) else "-"
            lines.append(
                f"| {version} | {scenario.scenario_id} | {_md(scenario.scenario_role)} / "
                f"{_md(scenario.pressure_band)} | {proposal_id} | {_md(db_status)} | "
                f"{_md(_set_text(_parameter_names(record)))} | {_md(confirmation.get('status', 'N/A'))} | "
                f"{_duration(record.get('elapsed_seconds'))} | {_tokens_text(_usage_metrics(record))} | "
                f"{'PASS' if _record_passes(record, scenario_id=scenario.scenario_id, scenario_group_id=group.scenario_group_id) else ('NOT RUN' if not execute else 'FAIL')} |",
            )
    lines.extend(
        [
            "",
            f"- Invalid-status confirmation rollback: `{(invalid_status or {}).get('status', 'NOT RUN')}`",
            "",
            "## 4. v3/v4 결과 비교",
            "",
            "| 대응 근거 | v3 scenario | v4 scenario | 공통 파라미터 | v3 전용 | v4 전용 | 공통 exact slot | 값 상이 slot |",
            "|---|---:|---:|---|---|---|---:|---:|",
        ],
    )
    for match in matches:
        comparison = _comparison_metrics(match, records)
        lines.append(
            f"| {_md(match.basis)} | "
            f"{match.v3_scenario.scenario_id if match.v3_scenario else '-'} | "
            f"{match.v4_scenario.scenario_id if match.v4_scenario else '-'} | "
            f"{_md(_set_text(comparison['common_parameters']))} | "
            f"{_md(_set_text(comparison['v3_only_parameters']))} | "
            f"{_md(_set_text(comparison['v4_only_parameters']))} | "
            f"{comparison['common_slots']} | {comparison['different_common_slot_values']} |",
        )
    lines.extend(
        [
            "",
            "## 5. 성능 및 사용량 증적",
            "",
            "| 버전 | scenario_id | LLM 호출 수 | 입력 Token | 출력 Token | 합계 Token | 전체 소요시간 | 재시도 |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ],
    )
    for version, group in (("v3", v3_group), ("v4", v4_group)):
        for scenario in group.scenarios:
            record = records.get(scenario.scenario_id) or {}
            usage = _usage_metrics(record)
            attempts = record.get("attempts") or []
            retries = max(0, len(attempts) - 1) if isinstance(attempts, list) else 0
            lines.append(
                f"| {version} | {scenario.scenario_id} | {usage['call_count']} | "
                f"{usage['prompt_tokens'] if usage['prompt_tokens'] is not None else 'N/A'} | "
                f"{usage['completion_tokens'] if usage['completion_tokens'] is not None else 'N/A'} | "
                f"{usage['total_tokens'] if usage['total_tokens'] is not None else 'N/A'} | "
                f"{_duration(record.get('elapsed_seconds'))} | {retries} |",
            )
    lines.extend(
        [
            "",
            "## 6. 공용 DB 저장 증적",
            "",
            (
                "v3와 v4의 proposal은 동일한 `tmm_mi_model_param_proposal_m`에 저장됩니다. 아래 read-back은 "
                "scenario/group FK, 최종 상태, proposal/confirmation payload를 포함합니다."
            ),
            "",
        ],
    )
    for version, group in (("v3", v3_group), ("v4", v4_group)):
        for scenario in group.scenarios:
            record = records.get(scenario.scenario_id) or {}
            lines.extend(
                [
                    f"### {version} · scenario {scenario.scenario_id}",
                    "",
                    f"- 제목: {_md(scenario.title)}",
                    f"- scenario role / pressure band: `{scenario.scenario_role}` / `{scenario.pressure_band}`",
                    f"- baselineYn: `{scenario.baseline_yn}`",
                    f"- dimension values: `{json.dumps(json_safe(scenario.dimension_values), ensure_ascii=False)}`",
                ],
            )
            if record.get("error"):
                lines.append(f"- 실행 오류: {_md(record['error'])}")
            lines.extend(
                [
                    "",
                    "```json",
                    json.dumps(json_safe(record.get("proposal_db_row") or {}), ensure_ascii=False, indent=2),
                    "```",
                    "",
                ],
            )
    lines.extend(
        [
            "## 7. 결론 및 해석 한계",
            "",
            (
                "- 최종 결론: v3와 v4가 동일 Event 집합 및 공용 DB 조건에서 모두 proposal·confirmation E2E "
                "계약을 충족했습니다."
                if verdict == "PASS"
                else (
                    "- 최종 결론: 대상 그룹 쌍의 비교 범위만 확정되었으며 실행 결과 판정은 보류합니다."
                    if verdict == "NOT_EXECUTED"
                    else "- 최종 결론: v3/v4 중 하나 이상이 E2E 계약을 충족하지 못했습니다."
                )
            ),
            "- v3/v4 시나리오는 동일 Event에서 독립 생성되므로 문장과 Dimension 조합이 완전히 같다는 가정은 하지 않습니다.",
            (
                "- 공통 exact slot이 없는 경우는 비교 불능이지 자동 실패가 아닙니다. 각 버전의 candidate·slot 정책 차이를 "
                "파라미터 집합 및 전용 항목으로 제시합니다."
            ),
            "- LLM 결과는 비결정적일 수 있으므로 본 보고서는 단일 실행 시점의 운영 증적입니다.",
            "",
        ],
    )
    return "\n".join(lines), verdict


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compare v3 fixed-mapping and v4 Lever-native Model Parameter E2E results "
            "on scenario groups backed by the same source Event set."
        ),
    )
    parser.add_argument("--v3-group-id", type=int)
    parser.add_argument("--v4-group-id", type=int)
    parser.add_argument(
        "--create-missing-counterpart",
        action="store_true",
        help="Opt in to creating exactly one missing versioned group with the selected group's ordered Event IDs.",
    )
    parser.add_argument("--user-id", type=int, help="Required for --create-missing-counterpart.")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Run proposal, confirmation, reconfirmation, and DB read-back for every scenario in both groups.",
    )
    parser.add_argument("--retries", type=int, default=0)
    parser.add_argument("--report-path", type=Path)
    return parser


def _load_groups() -> list[GroupSnapshot]:
    session = get_sync_session()
    try:
        return load_group_snapshots(session)
    finally:
        session.close()


async def run(args: argparse.Namespace) -> tuple[Path, Path, Verdict]:
    if args.report_path is not None and args.report_path.suffix.lower() != ".md":
        raise ComparisonScopeError("--report-path는 .md 파일이어야 합니다")
    if args.create_missing_counterpart and args.user_id is None:
        raise ComparisonScopeError("--create-missing-counterpart에는 --user-id가 필요합니다")
    if args.create_missing_counterpart and args.v3_group_id is None and args.v4_group_id is None:
        raise ComparisonScopeError("counterpart 생성 시 기준 --v3-group-id 또는 --v4-group-id가 필요합니다")

    started_at = datetime.now(UTC)
    groups = _load_groups()
    created_group_ids: list[int] = []
    try:
        v3_group, v4_group = select_group_pair(
            groups,
            v3_group_id=args.v3_group_id,
            v4_group_id=args.v4_group_id,
        )
    except ComparisonScopeError:
        if not args.create_missing_counterpart:
            raise
        by_id = {group.scenario_group_id: group for group in groups}
        if args.v3_group_id is not None and args.v4_group_id is None:
            source = by_id.get(args.v3_group_id)
            target_version: Version = "v4"
        elif args.v4_group_id is not None and args.v3_group_id is None:
            source = by_id.get(args.v4_group_id)
            target_version = "v3"
        else:
            raise ComparisonScopeError("counterpart 생성에는 한 버전의 그룹 ID만 지정해야 합니다")
        if source is None:
            raise ComparisonScopeError("counterpart 생성 기준 그룹을 찾을 수 없습니다")
        created_id = await create_counterpart(source, target_version=target_version, user_id=args.user_id)
        created_group_ids.append(created_id)
        groups = _load_groups()
        v3_group, v4_group = select_group_pair(
            groups,
            v3_group_id=(args.v3_group_id if target_version == "v4" else created_id),
            v4_group_id=(args.v4_group_id if target_version == "v3" else created_id),
        )

    if args.execute:
        records, invalid_status = await execute_pair(
            v3_group,
            v4_group,
            retries=max(0, args.retries),
        )
    else:
        records = {}
        invalid_status = {"status": "NOT RUN", "message": "read-only mode"}
    finished_at = datetime.now(UTC)

    if args.report_path is None:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        stamp = started_at.strftime("%Y%m%d_%H%M%S")
        report_path = REPORT_DIR / f"model_parameter_v3_v4_comparison_{stamp}.md"
    else:
        report_path = args.report_path
        report_path.parent.mkdir(parents=True, exist_ok=True)
    dashboard_path = report_path.with_name(f"{report_path.stem}_summary.png")
    report, verdict = render_report(
        started_at=started_at,
        finished_at=finished_at,
        execute=args.execute,
        v3_group=v3_group,
        v4_group=v4_group,
        records=records,
        invalid_status=invalid_status,
        dashboard_name=dashboard_path.name,
        created_group_ids=created_group_ids,
    )
    render_dashboard(
        output_path=dashboard_path,
        v3_metrics=_version_metrics(v3_group, records),
        v4_metrics=_version_metrics(v4_group, records),
    )
    report_path.write_text(report, encoding="utf-8")
    return report_path, dashboard_path, verdict


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report_path, dashboard_path, verdict = asyncio.run(run(args))
    print(
        json.dumps(
            {
                "report": str(report_path),
                "dashboard": str(dashboard_path),
                "verdict": verdict,
            },
            ensure_ascii=False,
        ),
    )
    return 1 if verdict == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
