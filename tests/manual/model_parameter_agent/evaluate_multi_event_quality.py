# Copyright (c) 2026 SK Innovation E&S.
# ruff: noqa: ANN401, C901, E402, T201

"""Evidence-bound quality runner for v4 Model Parameter scenarios.

The default mode only reads metadata and writes a Markdown report. ``--execute``
is the sole path that invokes the existing proposal/confirmation workflow.
"""

from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any, Literal


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

from sqlalchemy import inspect, select

from apps.agents.model_parameter_agent.constants import (
    MODEL_PARAMETER_PROPOSAL_ALLOWLIST,
    PROPOSAL_SCOPE_EXCLUDED_REASON_CODE,
)
from apps.agents.model_parameter_agent.persistence.model_parameter_service import (
    ModelParameterService,
)
from apps.agents.model_parameter_agent.presentation import (
    _proposal_parameters_from_state,
)
from apps.agents.model_parameter_agent.utils.parameter_mapping import (
    match_v4_parameter_candidates_from_rows,
    partition_proposal_parameter_candidates,
)
from apps.common.configs.database.sync_database.connection import get_sync_session
from apps.persistence.model_impact_lever.models import MiModelImpactLeverModel
from apps.persistence.model_parameter.models import (
    MiModelParamModel,
    MiModelParamProposalModel,
)
from apps.persistence.scenario.models import MiScenarioModel
from apps.persistence.scenario_group.models import (
    MiScenarioGroupEventModel,
    MiScenarioGroupModel,
)
from tests.manual.model_parameter_agent.runner_common import (
    execute_proposal_and_confirmation,
    json_safe,
    runner_record_from_exception,
)


V4_API_VERSION = "v4"
V4_STRATEGY = "multi_event_model_lever_dimensions"
MIN_EVENT_COUNT = 1
MAX_EVENT_COUNT = 5
DEFAULT_DISCOVERY_LIMIT = 5
DISCOVERY_SCAN_MULTIPLIER = 10
MAX_DISCOVERY_SCAN = 100
DEFAULT_CORE_SMOKE_TIMEOUT_SECONDS = 180
MAX_EXECUTION_SECONDS = 180.0
REPORT_DIR = ROOT_DIR / "tests" / "reports" / "model_parameter_agent"
CORE_SMOKE_COMMAND = (
    sys.executable,
    "-m",
    "pytest",
    "-q",
    "-m",
    "model_parameter_core",
    "tests/automated/test_model_parameter_agent_contract.py",
    "tests/automated/test_model_parameter_multi_event_quality.py",
    "tests/automated/test_model_parameter_runner_common.py",
)

Verdict = Literal["PASS", "REVIEW", "FAIL", "COVERAGE LIMIT"]
_VERDICT_PRIORITY: dict[Verdict, int] = {
    "COVERAGE LIMIT": 0,
    "PASS": 1,
    "REVIEW": 2,
    "FAIL": 3,
}


@dataclass(frozen=True)
class SchemaPreflight:
    verdict: Verdict
    checks: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class CoreSmokeEvidence:
    status: Literal["NOT RUN", "PASS", "FAIL"]
    command: tuple[str, ...] = CORE_SMOKE_COMMAND
    return_code: int | None = None
    elapsed_seconds: float | None = None
    output_tail: str = ""
    message: str = ""


@dataclass
class ScenarioEvidence:
    scenario_group_id: int
    scenario_id: int
    group_title: str
    scenario_title: str
    api_version: str
    generation_strategy: str
    ordered_events: tuple[dict[str, Any], ...] = ()
    stored_catalog_version: str = ""
    stored_catalog_checksum: str = ""
    active_catalog_version: str = ""
    active_catalog_checksum: str = ""
    dimension_lineage: tuple[dict[str, Any], ...] = ()
    impact_levers: tuple[dict[str, Any], ...] = ()
    parameter_definitions: tuple[dict[str, Any], ...] = ()
    raw_candidates: tuple[dict[str, Any], ...] = ()
    runtime_candidates: tuple[dict[str, Any], ...] = ()
    blocked_candidates: tuple[dict[str, Any], ...] = ()
    matcher_non_inputs: tuple[dict[str, Any], ...] = ()
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    @property
    def ordered_event_ids(self) -> tuple[int, ...]:
        return tuple(
            event_id
            for event in self.ordered_events
            if (event_id := _int_or_none(event.get("mi_event_id"))) is not None
        )


@dataclass(frozen=True)
class ExecutionAssessment:
    scenario_id: int
    verdict: Verdict
    failures: tuple[str, ...] = ()
    reviews: tuple[str, ...] = ()
    raw_candidate_keys: tuple[str, ...] = ()
    runtime_candidate_keys: tuple[str, ...] = ()
    selected_parameter_names: tuple[str, ...] = ()
    proposed_parameter_names: tuple[str, ...] = ()
    confirmed_parameter_names: tuple[str, ...] = ()


@dataclass(frozen=True)
class CoverageRow:
    scenario_id: int
    parameter_name: str
    classification: Literal["runtime-allowed", "active-but-blocked"]
    raw: int
    runtime: int | None
    selected: int | None
    proposed: int | None
    confirmed: int | None
    exclusion_reason: str
    verdict: Verdict
    evidence: str


@dataclass(frozen=True)
class CampaignResult:
    verdict: Verdict
    report_path: Path
    preflight: SchemaPreflight
    core_smoke: CoreSmokeEvidence
    evidences: tuple[ScenarioEvidence, ...]
    executions: Mapping[int, dict[str, Any]]
    assessments: tuple[ExecutionAssessment, ...]
    scope_errors: tuple[str, ...] = ()

    @property
    def exit_code(self) -> int:
        return 1 if self.verdict == "FAIL" else 0


def _text(value: Any) -> str:
    return str(value or "").strip()


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _mapping_items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _candidate_key(item: Mapping[str, Any]) -> str:
    return _text(item.get("candidate_key") or item.get("candidateKey"))


def _parameter_name(item: Mapping[str, Any]) -> str:
    return _text(
        item.get("canonical_parameter_name")
        or item.get("canonicalParameterName")
        or item.get("parameter_name")
        or item.get("parameterName"),
    )


def _parameter_names(value: Any) -> set[str]:
    return {
        name
        for item in _mapping_items(value)
        if (name := _parameter_name(item))
    }


def _proposal_value_count(value: Any) -> int:
    return sum(
        len(item.get("values") or [])
        for item in _mapping_items(value)
        if isinstance(item.get("values") or [], list)
    )


_PROPOSAL_KEY_ALIASES = {
    "parameterName": "parameter_name",
    "modelTarget": "model_target",
    "modelFile": "model_file",
    "modelSheet": "model_sheet",
    "tableName": "table_name",
    "valueFieldNames": "value_field_names",
    "slotAxesFieldNames": "slot_axes_field_names",
    "basecaseValue": "basecase_value",
    "proposedValue": "proposed_value",
    "rationaleKo": "rationale_ko",
}
_REDACTION_PATTERNS = (
    re.compile(
        r"(?i)(password|passwd|pwd|token|api[_-]?key|authorization|secret)"
        r"(\s*[=:]\s*)([^\s,;]+)",
    ),
    re.compile(r"(?i)([a-z][a-z0-9+.-]*://[^:/@\s]+):([^@\s]+)@"),
    re.compile(r"(?i)(bearer\s+)([a-z0-9._~+/-]+=*)"),
)


def _normalize_proposal_payload(
    value: Any,
    *,
    drop_lut_value: bool,
) -> Any:
    safe_value = json_safe(value)
    if isinstance(safe_value, Mapping):
        normalized: dict[str, Any] = {}
        for raw_key, raw_item in safe_value.items():
            key = _PROPOSAL_KEY_ALIASES.get(str(raw_key), str(raw_key))
            if drop_lut_value and key in {"lutValue", "lut_value"}:
                continue
            normalized[key] = _normalize_proposal_payload(
                raw_item,
                drop_lut_value=drop_lut_value,
            )
        return normalized
    if isinstance(safe_value, list):
        return [
            _normalize_proposal_payload(
                item,
                drop_lut_value=drop_lut_value,
            )
            for item in safe_value
        ]
    return safe_value


def _proposal_payload_multiset(
    value: Any,
    *,
    drop_lut_value: bool = False,
) -> tuple[str, ...]:
    normalized_items: list[str] = []
    for raw_item in _mapping_items(value):
        item = _normalize_proposal_payload(
            raw_item,
            drop_lut_value=drop_lut_value,
        )
        values = item.get("values") if isinstance(item, dict) else None
        if isinstance(values, list):
            item["values"] = sorted(
                values,
                key=lambda entry: json.dumps(
                    entry,
                    ensure_ascii=False,
                    sort_keys=True,
                    default=str,
                ),
            )
        normalized_items.append(
            json.dumps(
                item,
                ensure_ascii=False,
                sort_keys=True,
                default=str,
            ),
        )
    return tuple(sorted(normalized_items))


def _contains_lut_value(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            str(key) in {"lutValue", "lut_value"}
            or _contains_lut_value(item)
            for key, item in value.items()
        )
    if isinstance(value, list | tuple):
        return any(_contains_lut_value(item) for item in value)
    return False


def _redact(value: Any) -> str:
    text = str(value)
    for pattern in _REDACTION_PATTERNS:
        text = (
            pattern.sub(r"\1\2<redacted>", text)
            if pattern.groups == 3
            else pattern.sub(r"\1<redacted>", text)
        )
    return text


def _candidate_keys(value: Any) -> set[str]:
    return {
        key
        for item in _mapping_items(value)
        if (key := _candidate_key(item))
    }


def _basic_target_signature(item: Mapping[str, Any]) -> tuple[str, str, str]:
    return (
        _parameter_name(item).casefold(),
        _text(item.get("model_file") or item.get("modelFile")).casefold(),
        _text(item.get("model_sheet") or item.get("modelSheet")).casefold(),
    )


def _target_signature(item: Mapping[str, Any]) -> tuple[str, str, str, str]:
    return (
        *_basic_target_signature(item),
        _text(
            item.get("model_table")
            or item.get("modelTable")
            or item.get("table_name")
            or item.get("tableName"),
        ).casefold(),
    )


def _merged_raw_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    for item in _mapping_items(value):
        merged_keys = item.get("merged_candidate_keys") or item.get(
            "mergedCandidateKeys",
        )
        if isinstance(merged_keys, Sequence) and not isinstance(
            merged_keys,
            str | bytes,
        ):
            keys.update(_text(key) for key in merged_keys if _text(key))
            continue
        candidate_key = _candidate_key(item)
        if candidate_key.startswith("v4-lever|"):
            keys.add(candidate_key)
    return keys


def _field_key(value: Any) -> str:
    return re.sub(r"[^0-9a-zA-Z가-힣]+", "", _text(value)).lower()


def _parameter_candidate_key(item: Mapping[str, Any]) -> str:
    return "|".join(
        (
            "parameter",
            "v4",
            _field_key(item.get("model_file") or item.get("modelFile")),
            _field_key(item.get("model_sheet") or item.get("modelSheet")),
            _field_key(_parameter_name(item)),
        ),
    )


def _coordinate_signature(value: Any) -> str:
    coordinates = _mapping(value)
    return json.dumps(
        json_safe(coordinates),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def _slot_coordinates(slot: Mapping[str, Any]) -> dict[str, Any]:
    direct = slot.get("coordinates")
    if isinstance(direct, Mapping):
        return dict(direct)
    coordinates: dict[str, Any] = {}
    for axis in _mapping_items(slot.get("slot_axes") or slot.get("slotAxes")):
        axis_name = _text(axis.get("axis_name") or axis.get("axisName"))
        if axis_name:
            coordinates[axis_name] = axis.get("axis_value", axis.get("axisValue"))
    return coordinates


def _period_coordinates(value: Any) -> list[dict[str, Any]]:
    periods: list[dict[str, Any]] = []
    for raw_period in _mapping_items(value):
        months = raw_period.get("Months")
        if "Year" in raw_period and isinstance(months, list):
            periods.extend(
                {"Year": raw_period["Year"], "Month": month}
                for month in months
            )
        else:
            periods.append(dict(raw_period))
    return periods


def _catalog_coordinate_signatures(catalog: Mapping[str, Any]) -> set[str]:
    coordinates: list[dict[str, Any]] = []
    for leaf in _mapping_items(catalog.get("leaves")):
        fixed_axes = _mapping(leaf.get("fixed_axes") or leaf.get("fixedAxes"))
        periods = _period_coordinates(
            leaf.get("available_periods") or leaf.get("availablePeriods"),
        )
        coordinates.extend(
            {**fixed_axes, **period} for period in periods or [{}]
        )
    if coordinates:
        return {_coordinate_signature(item) for item in coordinates}

    period_groups = {
        _text(group.get("period_group_id") or group.get("periodGroupId")): (
            _period_coordinates(
                group.get("available_periods")
                or group.get("availablePeriods"),
            )
        )
        for group in _mapping_items(
            catalog.get("period_groups") or catalog.get("periodGroups"),
        )
    }
    fixed_axis_names = [
        _text(axis_name)
        for axis_name in catalog.get("fixed_axis_names")
        or catalog.get("fixedAxisNames")
        or []
        if _text(axis_name)
    ]

    def walk(
        nodes: Any,
        depth: int,
        fixed_axes: Mapping[str, Any],
    ) -> None:
        for node in _mapping_items(nodes):
            next_axes = dict(fixed_axes)
            if depth < len(fixed_axis_names) and "axis_value" in node:
                next_axes[fixed_axis_names[depth]] = node.get("axis_value")
            elif depth < len(fixed_axis_names) and "axisValue" in node:
                next_axes[fixed_axis_names[depth]] = node.get("axisValue")
            children = node.get("children")
            if children:
                walk(children, depth + 1, next_axes)
            period_group_id = _text(
                node.get("period_group_id") or node.get("periodGroupId"),
            )
            if period_group_id:
                coordinates.extend(
                    {**next_axes, **period}
                    for period in period_groups.get(period_group_id, [])
                )

    walk(
        catalog.get("fixed_axis_hierarchy")
        or catalog.get("fixedAxisHierarchy"),
        0,
        {},
    )
    return {_coordinate_signature(item) for item in coordinates}


def _reference_coordinates(reference: Mapping[str, Any]) -> dict[str, Any]:
    return {
        **_mapping(reference.get("axes")),
        **_mapping(reference.get("metadata")),
    }


def _same_scalar(left: Any, right: Any) -> bool:
    return json_safe(left) == json_safe(right)


def _blocked_layer_hits(
    value: Any,
    blocked_candidates: Sequence[Mapping[str, Any]],
) -> set[str]:
    blocked_names = {
        _parameter_name(item) for item in blocked_candidates if _parameter_name(item)
    }
    blocked_targets = {_basic_target_signature(item) for item in blocked_candidates}
    blocked_keys = {
        key
        for item in blocked_candidates
        for key in (_candidate_key(item), _parameter_candidate_key(item))
        if key
    }
    hits: set[str] = set()
    for item in _mapping_items(value):
        name = _parameter_name(item)
        candidate_key = _candidate_key(item)
        target = _basic_target_signature(item)
        if (
            name in blocked_names
            or candidate_key in blocked_keys
            or (name and target in blocked_targets)
        ):
            hits.add(name or candidate_key or str(target))
    return hits


def _non_input_signature(item: Mapping[str, Any]) -> tuple[str, ...]:
    """Identify an excluded v4 occurrence together with its exact reason code."""
    return (
        _candidate_key(item),
        _text(
            item.get("scenario_dimension_key")
            or item.get("dimension_key")
            or item.get("source_dimension_id"),
        ),
        _text(
            item.get("source_dimension_value_id")
            or item.get("source_dimension_value"),
        ),
        _text(item.get("lever_code")),
        _text(item.get("impact_lever_id")),
        _parameter_name(item),
        _text(item.get("binding_role")),
        json.dumps(
            json_safe(item.get("source_event_ids") or []),
            ensure_ascii=False,
            sort_keys=True,
        ),
        _text(item.get("reason_code") or item.get("reasonCode")),
    )


def _canonical_mapping_multiset(value: Any) -> tuple[str, ...]:
    return tuple(
        sorted(
            json.dumps(
                json_safe(item),
                ensure_ascii=False,
                sort_keys=True,
                default=str,
            )
            for item in _mapping_items(value)
        ),
    )


def _lineage_signature(item: Mapping[str, Any]) -> str:
    states = [
        {
                "lever_code": state.get("lever_code") or state.get("leverCode"),
                "impact_lever_id": state.get("impact_lever_id")
                or state.get("impactLeverId"),
                "direction": state.get("direction"),
                "level": state.get("level"),
                "scope": state.get("scope"),
                "time_window": state.get("time_window") or state.get("timeWindow"),
                "lever_domain": state.get("lever_domain") or state.get("leverDomain"),
                "is_primary_lever": state.get("is_primary_lever")
                if "is_primary_lever" in state
                else state.get("isPrimaryLever"),
                "parameter_bindings": _canonical_mapping_multiset(
                    state.get("parameter_bindings") or state.get("parameterBindings"),
                ),
        }
        for state in _mapping_items(item.get("lever_states"))
    ]
    payload = {
        "dimension_key": item.get("scenario_dimension_key")
        or item.get("dimension_key"),
        "dimension_value": item.get("scenario_dimension_value"),
        "dimension_value_id": item.get("scenario_dimension_value_id"),
        "source_event_ids": json_safe(item.get("source_event_ids") or []),
        "primary_lever_code": item.get("primary_lever_code"),
        "primary_impact_lever_id": item.get("primary_impact_lever_id"),
        "lever_states": states,
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)


def _combine_verdicts(verdicts: Sequence[Verdict]) -> Verdict:
    if not verdicts:
        return "COVERAGE LIMIT"
    return max(verdicts, key=_VERDICT_PRIORITY.__getitem__)


def _dedupe(messages: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(message for message in messages if message))


def _binding_signature(value: Any) -> tuple[tuple[str, str, str, str, str], ...]:
    return tuple(
        (
            _text(binding.get("parameter_name") or binding.get("parameterName")),
            _text(binding.get("role") or "primary"),
            _text(binding.get("applicability")),
            _text(binding.get("support_status") or binding.get("supportStatus")),
            _text(
                binding.get("unsupported_reason_code")
                or binding.get("unsupportedReasonCode"),
            ),
        )
        for binding in _mapping_items(value)
    )


def _schema_preflight() -> SchemaPreflight:
    contracts: dict[str, set[str]] = {
        MiScenarioGroupModel.__tablename__: {
            "scenario_group_id",
            "api_version",
            "generation_strategy",
            "dimension_definitions",
            "impact_catalog_version",
            "impact_catalog_checksum",
        },
        MiScenarioGroupEventModel.__tablename__: {
            "scenario_group_id",
            "mi_event_id",
            "display_order",
        },
        MiScenarioModel.__tablename__: {
            "scenario_id",
            "scenario_group_id",
            "dimension_values",
        },
        # The execute path inserts and then ORM-loads this row.  Validate the
        # complete mapped shape before any LLM or write instead of discovering
        # an old schema after a proposal has already been attempted.
        MiModelParamProposalModel.__tablename__: set(
            MiModelParamProposalModel.__table__.columns.keys(),
        ),
        MiModelParamModel.__tablename__: {
            "parameter_name",
            "model_file",
            "model_sheet",
            "use_yn",
            "del_yn",
        },
        MiModelImpactLeverModel.__tablename__: {
            "impact_lever_id",
            "lever_code",
            "parameter_bindings",
            "catalog_version",
            "use_yn",
            "del_yn",
        },
    }
    checks: list[str] = []
    errors: list[str] = []
    session = None
    try:
        session = get_sync_session()
        inspector = inspect(session.get_bind())
        existing_tables = set(inspector.get_table_names())
        for table_name, required_columns in contracts.items():
            if table_name not in existing_tables:
                errors.append(f"필수 테이블 누락: {table_name}")
                continue
            columns = {
                str(column.get("name")): column
                for column in inspector.get_columns(table_name)
            }
            missing = sorted(required_columns - set(columns))
            if missing:
                errors.append(f"필수 컬럼 누락: {table_name}.{','.join(missing)}")
            else:
                checks.append(f"{table_name}: required columns present")
            if table_name == MiModelParamProposalModel.__tablename__:
                event_column = columns.get("mi_event_id") or {}
                if event_column.get("nullable") is not True:
                    errors.append(
                        "proposal.mi_event_id가 nullable이 아님: v4 persistence 불가",
                    )
                else:
                    checks.append("proposal.mi_event_id: nullable")
    except Exception as exc:
        errors.append(f"schema preflight 실행 실패: {_redact(repr(exc))}")
    finally:
        if session is not None:
            session.close()
    return SchemaPreflight(
        verdict="FAIL" if errors else "PASS",
        checks=tuple(checks),
        errors=_dedupe(errors),
    )


def _discover_scenario_ids(args: argparse.Namespace) -> tuple[list[int], list[str]]:
    session = None
    errors: list[str] = []
    try:
        session = get_sync_session()
        statement = (
            select(MiScenarioModel.scenario_id)
            .join(
                MiScenarioGroupModel,
                MiScenarioGroupModel.scenario_group_id
                == MiScenarioModel.scenario_group_id,
            )
            .where(
                MiScenarioModel.del_yn == "N",
                MiScenarioGroupModel.del_yn == "N",
                MiScenarioGroupModel.api_version == V4_API_VERSION,
                MiScenarioGroupModel.generation_strategy == V4_STRATEGY,
            )
            .order_by(
                MiScenarioGroupModel.scenario_group_id.desc(),
                MiScenarioModel.display_order,
                MiScenarioModel.scenario_id,
            )
        )
        if args.scenario_id is not None:
            statement = statement.where(
                MiScenarioModel.scenario_id == args.scenario_id,
            )
        elif args.scenario_group_id is not None:
            statement = statement.where(
                MiScenarioGroupModel.scenario_group_id
                == args.scenario_group_id,
            )
        else:
            scan_limit = min(
                max(args.limit * DISCOVERY_SCAN_MULTIPLIER, args.limit),
                MAX_DISCOVERY_SCAN,
            )
            statement = statement.limit(scan_limit)
        scenario_ids = [int(value) for value in session.scalars(statement).all()]
    except Exception as exc:
        scenario_ids = []
        errors.append(f"v4 scenario discovery 실패: {_redact(repr(exc))}")
    finally:
        if session is not None:
            session.close()

    if not scenario_ids and not errors:
        if args.scenario_id is not None:
            errors.append(
                f"요청 scenario_id={args.scenario_id}가 v4 {V4_STRATEGY} 범위에 없음",
            )
        elif args.scenario_group_id is not None:
            errors.append(
                "요청 scenario_group_id="
                f"{args.scenario_group_id}에 v4 실행 대상 scenario가 없음",
            )
    return scenario_ids, errors


def build_v4_scenario_evidence(
    scenario_id: int,
    context: Mapping[str, Any],
) -> ScenarioEvidence:
    """Validate a loaded v4 context and independently derive proposal boundaries."""
    scenario = _mapping(context.get("scenario"))
    group = _mapping(context.get("scenario_group"))
    context_scenario_id = _int_or_none(scenario.get("scenario_id"))
    resolved_scenario_id = scenario_id
    group_id = _int_or_none(group.get("scenario_group_id")) or 0
    api_version = _text(group.get("api_version"))
    strategy = _text(group.get("generation_strategy"))
    events = _mapping_items(context.get("events"))
    lineage = _mapping_items(context.get("dimension_lineage"))
    impact_levers = _mapping_items(context.get("impact_levers"))
    resources = _mapping(context.get("parameter_mapping_resources"))
    definitions = _mapping_items(resources.get("parameter_definitions"))
    errors: list[str] = []
    warnings = [
        _text(item)
        for item in context.get("validation_warnings") or []
        if _text(item)
    ]

    if scenario_id <= 0:
        errors.append(f"requested scenario_id가 positive integer가 아님: {scenario_id}")
    if context_scenario_id is None or context_scenario_id <= 0:
        errors.append("loaded context scenario_id가 누락되거나 유효하지 않음")
    elif context_scenario_id != scenario_id:
        errors.append(
            "loaded context scenario_id mismatch: "
            f"requested={scenario_id}, actual={context_scenario_id}",
        )
    if group_id <= 0:
        errors.append("loaded context scenario_group_id가 누락되거나 유효하지 않음")
    if api_version != V4_API_VERSION:
        errors.append(
            f"api_version mismatch: expected={V4_API_VERSION}, actual={api_version or '-'}",
        )
    if strategy != V4_STRATEGY:
        errors.append(
            f"generation_strategy mismatch: expected={V4_STRATEGY}, actual={strategy or '-'}",
        )
    if not MIN_EVENT_COUNT <= len(events) <= MAX_EVENT_COUNT:
        errors.append(
            f"ordered event count must be {MIN_EVENT_COUNT}..{MAX_EVENT_COUNT}: {len(events)}",
        )
    event_ids = [_int_or_none(event.get("mi_event_id")) for event in events]
    if any(event_id is None for event_id in event_ids):
        errors.append("ordered event에 mi_event_id가 누락됨")
    clean_event_ids = [event_id for event_id in event_ids if event_id is not None]
    if len(clean_event_ids) != len(set(clean_event_ids)):
        errors.append("ordered event에 중복 mi_event_id가 있음")
    display_orders = [_int_or_none(event.get("display_order")) for event in events]
    if any(order is None for order in display_orders):
        errors.append("ordered event에 display_order가 누락됨")
    elif display_orders != list(range(1, len(events) + 1)):
        errors.append("ordered event display_order가 exact 1..N 순서가 아님")

    stored_version = _text(group.get("impact_catalog_version"))
    stored_checksum = _text(group.get("impact_catalog_checksum"))
    active_version = _text(context.get("impact_catalog_version"))
    active_checksum = _text(context.get("impact_catalog_checksum"))
    if not stored_version or not stored_checksum:
        errors.append("scenario group의 impact catalog pin(version/checksum)이 누락됨")
    if not active_version or not active_checksum:
        errors.append("active impact catalog version/checksum 증적이 누락됨")
    if stored_version != active_version:
        errors.append(
            f"impact catalog version mismatch: stored={stored_version or '-'}, active={active_version or '-'}",
        )
    if stored_checksum != active_checksum:
        errors.append(
            f"impact catalog checksum mismatch: stored={stored_checksum or '-'}, active={active_checksum or '-'}",
        )

    catalog_by_code: dict[str, dict[str, Any]] = {}
    for lever in impact_levers:
        lever_code = _text(lever.get("lever_code") or lever.get("leverCode"))
        if not lever_code:
            errors.append("active catalog Lever에 lever_code가 누락됨")
            continue
        if lever_code in catalog_by_code:
            errors.append(f"active catalog Lever code 중복: {lever_code}")
            continue
        catalog_by_code[lever_code] = lever
        lever_version = _text(
            lever.get("catalog_version") or lever.get("catalogVersion"),
        )
        if lever_version != active_version:
            errors.append(
                f"Lever catalog version mismatch: {lever_code}={lever_version or '-'}",
            )

    seen_dimensions: set[str] = set()
    group_event_id_set = set(clean_event_ids)
    for item in lineage:
        dimension_key = _text(
            item.get("scenario_dimension_key")
            or item.get("scenarioDimensionKey"),
        )
        if not dimension_key:
            errors.append("dimension lineage key가 누락됨")
        elif dimension_key in seen_dimensions:
            errors.append(f"dimension lineage key 중복: {dimension_key}")
        seen_dimensions.add(dimension_key)

        source_ids = [
            _int_or_none(value)
            for value in item.get("source_event_ids")
            or item.get("sourceEventIds")
            or []
        ]
        if not source_ids or any(value is None for value in source_ids):
            errors.append(f"dimension={dimension_key or '-'} source_event_ids가 유효하지 않음")
        else:
            integer_source_ids = [value for value in source_ids if value is not None]
            if len(integer_source_ids) != len(set(integer_source_ids)):
                errors.append(f"dimension={dimension_key} source_event_ids 중복")
            outside = sorted(set(integer_source_ids) - group_event_id_set)
            if outside:
                errors.append(
                    f"dimension={dimension_key} source_event_ids가 group 밖을 참조: {outside}",
                )

        states = _mapping_items(item.get("lever_states") or item.get("leverStates"))
        if not states:
            errors.append(f"dimension={dimension_key or '-'} selected lever_states가 없음")
        seen_lever_codes: set[str] = set()
        for state in states:
            lever_code = _text(state.get("lever_code") or state.get("leverCode"))
            if not lever_code:
                errors.append(f"dimension={dimension_key or '-'} Lever code 누락")
                continue
            if lever_code in seen_lever_codes:
                errors.append(f"dimension={dimension_key} Lever state 중복: {lever_code}")
            seen_lever_codes.add(lever_code)
            catalog_lever = catalog_by_code.get(lever_code)
            if catalog_lever is None:
                errors.append(
                    f"dimension={dimension_key} Lever가 active catalog에 없음: {lever_code}",
                )
                continue
            state_id = _int_or_none(
                state.get("impact_lever_id") or state.get("impactLeverId"),
            )
            catalog_id = _int_or_none(
                catalog_lever.get("impact_lever_id")
                or catalog_lever.get("impactLeverId"),
            )
            if state_id != catalog_id:
                errors.append(
                    f"dimension={dimension_key} Lever ID mismatch: {lever_code} stored={state_id}, active={catalog_id}",
                )
            state_domain = _text(
                state.get("lever_domain") or state.get("leverDomain"),
            )
            catalog_domain = _text(catalog_lever.get("domain"))
            if state_domain != catalog_domain:
                errors.append(
                    f"dimension={dimension_key} Lever domain mismatch: {lever_code}",
                )
            state_bindings = _binding_signature(
                state.get("parameter_bindings") or state.get("parameterBindings"),
            )
            catalog_bindings = _binding_signature(
                catalog_lever.get("parameter_bindings")
                or catalog_lever.get("parameterBindings"),
            )
            if state_bindings != catalog_bindings:
                errors.append(
                    f"dimension={dimension_key} catalog-pinned binding mismatch: {lever_code}",
                )

        primary_lever_code = _text(
            item.get("primary_lever_code") or item.get("primaryLeverCode"),
        )
        primary_lever_id = _int_or_none(
            item.get("primary_impact_lever_id")
            or item.get("primaryImpactLeverId"),
        )
        primary_catalog = catalog_by_code.get(primary_lever_code)
        primary_states = [
            state
            for state in states
            if _text(state.get("lever_code") or state.get("leverCode"))
            == primary_lever_code
        ]
        if not primary_lever_code or primary_catalog is None:
            errors.append(
                f"dimension={dimension_key or '-'} primary Lever가 active catalog에 없음",
            )
        elif primary_lever_id != _int_or_none(
            primary_catalog.get("impact_lever_id")
            or primary_catalog.get("impactLeverId"),
        ):
            errors.append(f"dimension={dimension_key} primary Lever ID mismatch")
        if len(primary_states) != 1:
            errors.append(
                f"dimension={dimension_key} primary Lever state가 정확히 1개가 아님",
            )
        elif (
            _int_or_none(
                primary_states[0].get("impact_lever_id")
                or primary_states[0].get("impactLeverId"),
            )
            != primary_lever_id
            or primary_states[0].get("is_primary_lever") is not True
        ):
            errors.append(
                f"dimension={dimension_key} primary Lever state code/ID/flag mismatch",
            )
        flagged_primary_codes = {
            _text(state.get("lever_code") or state.get("leverCode"))
            for state in states
            if state.get("is_primary_lever") is True
        }
        if flagged_primary_codes != {primary_lever_code}:
            errors.append(
                f"dimension={dimension_key} primary Lever flag set mismatch: {sorted(flagged_primary_codes)}",
            )

    if not lineage:
        errors.append("selected dimension_lineage가 없음")
    if not definitions:
        errors.append("active model parameter definition이 없음")

    raw_candidates: list[dict[str, Any]] = []
    runtime_candidates: list[dict[str, Any]] = []
    blocked_candidates: list[dict[str, Any]] = []
    matcher_non_inputs: list[dict[str, Any]] = []
    if definitions and lineage:
        try:
            raw_candidates, matcher_non_inputs, matcher_warnings = (
                match_v4_parameter_candidates_from_rows(
                    parameter_rows=definitions,
                    scenario_context=dict(context),
                )
            )
            runtime_candidates, blocked_candidates = (
                partition_proposal_parameter_candidates(raw_candidates)
            )
            warnings.extend(_text(item) for item in matcher_warnings if _text(item))
        except Exception as exc:
            errors.append(f"v4 candidate derivation 실패: {_redact(repr(exc))}")

    raw_keys = [_candidate_key(candidate) for candidate in raw_candidates]
    runtime_keys = [_candidate_key(candidate) for candidate in runtime_candidates]
    blocked_keys = [_candidate_key(candidate) for candidate in blocked_candidates]
    if any(not key for key in raw_keys):
        errors.append("raw candidate key가 누락됨")
    if len(raw_keys) != len(set(raw_keys)):
        errors.append("raw candidate key가 중복됨")
    if len(runtime_keys) != len(set(runtime_keys)):
        errors.append("runtime candidate key가 중복됨")
    if len(blocked_keys) != len(set(blocked_keys)):
        errors.append("blocked candidate key가 중복됨")
    if set(runtime_keys) & set(blocked_keys):
        errors.append("runtime/blocked candidate partition이 disjoint가 아님")
    if set(runtime_keys) | set(blocked_keys) != set(raw_keys):
        errors.append("runtime/blocked candidate partition union이 raw와 불일치")

    for candidate in runtime_candidates:
        name = _parameter_name(candidate)
        if name not in MODEL_PARAMETER_PROPOSAL_ALLOWLIST:
            errors.append(f"runtime allowlist 밖 후보가 허용됨: {name or '-'}")
    for candidate in blocked_candidates:
        name = _parameter_name(candidate)
        if name in MODEL_PARAMETER_PROPOSAL_ALLOWLIST:
            errors.append(f"runtime allowlist 후보가 차단됨: {name}")
        if candidate.get("reason_code") != PROPOSAL_SCOPE_EXCLUDED_REASON_CODE:
            errors.append(
                f"blocked candidate reason code 누락/불일치: {name or '-'}",
            )

    return ScenarioEvidence(
        scenario_group_id=group_id,
        scenario_id=resolved_scenario_id,
        group_title=_text(group.get("title")),
        scenario_title=_text(scenario.get("title")),
        api_version=api_version,
        generation_strategy=strategy,
        ordered_events=tuple(events),
        stored_catalog_version=stored_version,
        stored_catalog_checksum=stored_checksum,
        active_catalog_version=active_version,
        active_catalog_checksum=active_checksum,
        dimension_lineage=tuple(lineage),
        impact_levers=tuple(impact_levers),
        parameter_definitions=tuple(definitions),
        raw_candidates=tuple(raw_candidates),
        runtime_candidates=tuple(runtime_candidates),
        blocked_candidates=tuple(blocked_candidates),
        matcher_non_inputs=tuple(matcher_non_inputs),
        warnings=_dedupe(warnings),
        errors=_dedupe(errors),
    )


def _load_scenario_evidences(
    scenario_ids: Sequence[int],
) -> tuple[list[ScenarioEvidence], list[str]]:
    evidences: list[ScenarioEvidence] = []
    errors: list[str] = []
    service = ModelParameterService()
    for scenario_id in scenario_ids:
        try:
            context = service.load_context(scenario_id)
            evidences.append(build_v4_scenario_evidence(scenario_id, context))
        except Exception as exc:
            errors.append(
                f"scenario_id={scenario_id} context load 실패: {_redact(repr(exc))}",
            )
    return evidences, errors


def select_discovery_evidences(
    evidences: Sequence[ScenarioEvidence],
    limit: int,
) -> list[ScenarioEvidence]:
    """Greedily retain usable and diverse coverage from the bounded scan set."""
    valid = [evidence for evidence in evidences if not evidence.errors]
    if not valid:
        return list(evidences[:limit])
    remaining = list(valid)
    selected: list[ScenarioEvidence] = []
    covered_targets: set[tuple[str, str, str, str]] = set()
    while remaining and len(selected) < limit:
        best = max(
            remaining,
            key=lambda evidence: (
                len(
                    {
                        _target_signature(candidate)
                        for candidate in evidence.runtime_candidates
                    }
                    - covered_targets,
                ),
                len(evidence.runtime_candidates),
                len(evidence.raw_candidates),
                -evidences.index(evidence),
            ),
        )
        selected.append(best)
        covered_targets.update(
            _target_signature(candidate) for candidate in best.runtime_candidates
        )
        remaining.remove(best)
    return selected


def run_core_smoke(
    timeout_seconds: int = DEFAULT_CORE_SMOKE_TIMEOUT_SECONDS,
    *,
    run_command: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> CoreSmokeEvidence:
    """Run the DB/LLM-independent production contract gate in an isolated env."""
    from dotenv import dotenv_values

    environment = os.environ.copy()
    environment.update(
        {
            str(key): str(value)
            for key, value in dotenv_values(
                ROOT_DIR / "tests" / "automated" / ".env.example",
            ).items()
            if key and value is not None
        },
    )
    started = time.perf_counter()
    try:
        completed = run_command(
            CORE_SMOKE_COMMAND,
            cwd=ROOT_DIR,
            env=environment,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except Exception as exc:
        return CoreSmokeEvidence(
            status="FAIL",
            elapsed_seconds=time.perf_counter() - started,
            message=f"core smoke 실행 실패: {_redact(repr(exc))}",
        )
    output = "\n".join(
        part.strip()
        for part in (completed.stdout, completed.stderr)
        if part and part.strip()
    )
    return CoreSmokeEvidence(
        status="PASS" if completed.returncode == 0 else "FAIL",
        return_code=completed.returncode,
        elapsed_seconds=time.perf_counter() - started,
        output_tail=_redact("\n".join(output.splitlines()[-20:])),
        message=(
            "model_parameter_core passed"
            if completed.returncode == 0
            else "model_parameter_core failed; live writes blocked"
        ),
    )


async def execute_targets(
    evidences: Sequence[ScenarioEvidence],
) -> dict[int, dict[str, Any]]:
    """Execute each eligible scenario once; never retry a write-producing flow."""
    records: dict[int, dict[str, Any]] = {}
    for evidence in evidences:
        if evidence.errors or not evidence.runtime_candidates:
            continue
        started = time.perf_counter()
        try:
            record = await execute_proposal_and_confirmation(evidence.scenario_id)
            record["execution_attempt_count"] = 1
            record["elapsed_seconds"] = time.perf_counter() - started
            records[evidence.scenario_id] = record
        except Exception as exc:
            partial_record = runner_record_from_exception(exc)
            failure_trace = getattr(exc, "_model_parameter_failure_trace", None)
            if isinstance(failure_trace, Mapping):
                partial_record = {**dict(failure_trace), **partial_record}
            records[evidence.scenario_id] = {
                **partial_record,
                "scenario_id": evidence.scenario_id,
                "execution_attempt_count": 1,
                "elapsed_seconds": time.perf_counter() - started,
                "error": _redact(repr(exc)),
                "failed_stage": _redact(
                    partial_record.get("failed_stage")
                    or getattr(exc, "failed_stage", "")
                    or "proposal/confirmation workflow",
                ),
            }
    return records


def assess_execution(
    evidence: ScenarioEvidence,
    record: Mapping[str, Any],
) -> ExecutionAssessment:
    failures: list[str] = []
    reviews: list[str] = []
    if record.get("error"):
        failed_stage = _text(record.get("failed_stage")) or "unknown"
        failures.append(
            "proposal/confirmation execution error"
            f" (failed_stage={failed_stage}): {record['error']}",
        )

    execution_context = _mapping(record.get("context"))
    if not execution_context:
        reviews.append("execution context grounding trace 미수집")
    else:
        context_scenario = _mapping(execution_context.get("scenario"))
        context_group = _mapping(execution_context.get("scenario_group"))
        if _int_or_none(context_scenario.get("scenario_id")) != evidence.scenario_id:
            failures.append("execution context scenario_id가 discovery evidence와 불일치")
        if (
            _int_or_none(context_group.get("scenario_group_id"))
            != evidence.scenario_group_id
        ):
            failures.append("execution context scenario_group_id가 discovery evidence와 불일치")
        context_events = _mapping_items(execution_context.get("events"))
        expected_event_order = tuple(
            (
                _int_or_none(item.get("mi_event_id")),
                _int_or_none(item.get("display_order")),
            )
            for item in evidence.ordered_events
        )
        actual_event_order = tuple(
            (
                _int_or_none(item.get("mi_event_id")),
                _int_or_none(item.get("display_order")),
            )
            for item in context_events
        )
        if actual_event_order != expected_event_order:
            failures.append("execution context ordered Event가 discovery evidence와 불일치")
        context_catalog = (
            _text(context_group.get("impact_catalog_version")),
            _text(context_group.get("impact_catalog_checksum")),
            _text(execution_context.get("impact_catalog_version")),
            _text(execution_context.get("impact_catalog_checksum")),
        )
        evidence_catalog = (
            evidence.stored_catalog_version,
            evidence.stored_catalog_checksum,
            evidence.active_catalog_version,
            evidence.active_catalog_checksum,
        )
        if context_catalog != evidence_catalog:
            failures.append("execution context catalog version/checksum pin 불일치")
        actual_lineage = tuple(
            sorted(
                _lineage_signature(item)
                for item in _mapping_items(execution_context.get("dimension_lineage"))
            ),
        )
        expected_lineage = tuple(
            sorted(_lineage_signature(item) for item in evidence.dimension_lineage),
        )
        if actual_lineage != expected_lineage:
            failures.append("execution context selected Dimension/Lever lineage 불일치")

    expected_runtime_keys = _candidate_keys(evidence.runtime_candidates)
    expected_blocked_keys = _candidate_keys(evidence.blocked_candidates)
    actual_raw_items = _mapping_items(record.get("rule_candidates"))
    actual_raw_keys = _candidate_keys(actual_raw_items)
    actual_runtime_source = (
        record.get("runtime_candidates")
        if "runtime_candidates" in record
        else record.get("expected_candidates")
    )
    actual_runtime_items = _mapping_items(actual_runtime_source)
    actual_runtime_keys = _candidate_keys(actual_runtime_items)
    actual_raw_key_list = [_candidate_key(candidate) for candidate in actual_raw_items]
    actual_runtime_key_list = [
        _candidate_key(candidate) for candidate in actual_runtime_items
    ]
    if any(not key for key in actual_raw_key_list):
        failures.append("graph rule_candidates candidate_key가 누락됨")
    if len(actual_raw_key_list) != len(set(actual_raw_key_list)):
        failures.append("graph rule_candidates candidate_key가 중복됨")
    if any(not key for key in actual_runtime_key_list):
        failures.append("post-Step1.5 candidate_key가 누락됨")
    if len(actual_runtime_key_list) != len(set(actual_runtime_key_list)):
        failures.append("post-Step1.5 candidate_key가 중복됨")
    expected_raw_by_key = {
        _candidate_key(candidate): _target_signature(candidate)
        for candidate in evidence.raw_candidates
    }
    actual_raw_by_key = {
        _candidate_key(candidate): _target_signature(candidate)
        for candidate in actual_raw_items
    }
    if set(actual_raw_by_key) != set(expected_raw_by_key):
        failures.append(
            "graph v4 raw trace과 independent raw oracle key 불일치: "
            f"missing={sorted(set(expected_raw_by_key) - set(actual_raw_by_key))}, "
            f"unexpected={sorted(set(actual_raw_by_key) - set(expected_raw_by_key))}",
        )
    mismatched_raw_targets = sorted(
        key
        for key in set(expected_raw_by_key) & set(actual_raw_by_key)
        if expected_raw_by_key[key] != actual_raw_by_key[key]
    )
    if mismatched_raw_targets:
        failures.append(
            "graph v4 raw trace의 canonical parameter/model target 불일치: "
            f"{mismatched_raw_targets}",
        )
    expected_runtime_targets = {
        _target_signature(candidate) for candidate in evidence.runtime_candidates
    }
    actual_runtime_target_list = [
        _target_signature(candidate) for candidate in actual_runtime_items
    ]
    actual_runtime_targets = set(actual_runtime_target_list)
    if len(actual_runtime_target_list) != len(actual_runtime_targets):
        failures.append("post-Step1.5 runtime target가 여러 task로 분할됨")
    unexpected_runtime_targets = actual_runtime_targets - expected_runtime_targets
    if unexpected_runtime_targets:
        failures.append(
            "runtime candidate target가 allowlist/independent 경계 밖임: "
            f"{sorted(unexpected_runtime_targets)}",
        )
    represented_raw_keys = _merged_raw_keys(actual_runtime_items)
    unexpected_merged_lineage = represented_raw_keys - expected_runtime_keys
    if unexpected_merged_lineage:
        failures.append(
            "merged_candidate_keys가 independent runtime raw 경계 밖임: "
            f"{sorted(unexpected_merged_lineage)}",
        )
    expected_runtime_by_key = {
        _candidate_key(candidate): candidate
        for candidate in evidence.runtime_candidates
    }
    merged_key_counts: Counter[str] = Counter()
    for candidate in actual_runtime_items:
        candidate_target = _target_signature(candidate)
        if _candidate_key(candidate) != _parameter_candidate_key(candidate):
            failures.append(
                "post-Step1.5 candidate_key가 canonical parameter key와 불일치: "
                f"{_candidate_key(candidate)}",
            )
        merged_keys = [
            _text(key)
            for key in candidate.get("merged_candidate_keys") or []
            if _text(key)
        ]
        if not merged_keys:
            failures.append(
                "post-Step1.5 candidate의 merged_candidate_keys가 비어 있음: "
                f"{_candidate_key(candidate)}",
            )
        merged_key_counts.update(merged_keys)
        source_candidates = [
            expected_runtime_by_key[key]
            for key in merged_keys
            if key in expected_runtime_by_key
        ]
        mismatched_keys = [
            key
            for key in merged_keys
            if key in expected_runtime_by_key
            and _target_signature(expected_runtime_by_key[key]) != candidate_target
        ]
        if mismatched_keys:
            failures.append(
                "merged raw key→parameter/model target 결합 불일치: "
                f"{sorted(mismatched_keys)}",
            )
        expected_source_events: list[Any] = []
        for source_candidate in source_candidates:
            for event_id in source_candidate.get("source_event_ids") or []:
                if event_id not in expected_source_events:
                    expected_source_events.append(event_id)
        if json_safe(candidate.get("source_event_ids") or []) != json_safe(
            expected_source_events,
        ):
            failures.append(
                f"post-Step1.5 source_event_ids lineage 불일치: {_candidate_key(candidate)}",
            )
        for field_name in ("lever_provenance", "binding_provenance"):
            expected_provenance = [
                item
                for source_candidate in source_candidates
                for item in _mapping_items(source_candidate.get(field_name))
            ]
            actual_provenance = tuple(
                sorted(set(_canonical_mapping_multiset(candidate.get(field_name)))),
            )
            expected_provenance_signatures = tuple(
                sorted(set(_canonical_mapping_multiset(expected_provenance))),
            )
            if actual_provenance != expected_provenance_signatures:
                failures.append(
                    f"post-Step1.5 {field_name} lineage 불일치: "
                    f"{_candidate_key(candidate)}",
                )
    duplicated_merged_keys = sorted(
        key for key, count in merged_key_counts.items() if count > 1
    )
    if duplicated_merged_keys:
        failures.append(
            f"merged raw lineage key가 여러 runtime target에 중복 연결됨: {duplicated_merged_keys}",
        )
    direct_raw_keys = {
        _candidate_key(candidate)
        for candidate in evidence.runtime_candidates
        if _text(candidate.get("mapping_method")) == "direct"
    }
    missing_direct = direct_raw_keys - represented_raw_keys
    if missing_direct:
        failures.append(
            "runtime-allowed direct raw lineage가 selection에서 누락: "
            f"{sorted(missing_direct)}",
        )
    routing_raw_keys = expected_runtime_keys - direct_raw_keys
    missing_routing_raw_keys = routing_raw_keys - represented_raw_keys
    if missing_routing_raw_keys:
        reviews.append(
            "routing raw lineage 일부/전체가 선택되지 않아 의미 검토 필요: "
            f"{sorted(missing_routing_raw_keys)}",
        )

    prompt_grounding = _mapping(record.get("prompt_grounding_evidence"))
    if not prompt_grounding:
        reviews.append("Step1.5/2/3 prompt grounding packet 증적 미수집")
    else:
        if tuple(prompt_grounding.get("ordered_event_ids") or []) != (
            evidence.ordered_event_ids
        ):
            failures.append("prompt grounding ordered Event 불일치")
        if set(prompt_grounding.get("runtime_raw_candidate_keys") or []) != (
            expected_runtime_keys
        ):
            failures.append("prompt grounding runtime raw candidate lineage 불일치")
        if set(prompt_grounding.get("selected_candidate_keys") or []) != (
            actual_runtime_keys
        ):
            failures.append("prompt grounding selected candidate lineage 불일치")

    result = _mapping(record.get("result"))
    adjustments = _mapping_items(result.get("parameter_adjustments"))
    selected_items = [item for item in adjustments if item.get("selected", True)]
    parameter_slots = _mapping_items(record.get("parameter_slots"))
    slot_candidate_mappings = _mapping_items(record.get("slot_candidate_mappings"))
    effective_references = _mapping_items(record.get("effective_references"))
    selected_names = _parameter_names(selected_items)
    runtime_by_candidate_key = {
        _candidate_key(candidate): candidate for candidate in actual_runtime_items
    }
    for layer, items in (
        ("selected adjustment", selected_items),
        ("slot candidate mapping", slot_candidate_mappings),
    ):
        for item in items:
            candidate_key = _candidate_key(item)
            runtime_candidate = runtime_by_candidate_key.get(candidate_key)
            if runtime_candidate is None:
                failures.append(f"{layer} candidate_key가 runtime 후보에 없음: {candidate_key}")
            elif _basic_target_signature(item) != _basic_target_signature(
                runtime_candidate,
            ):
                failures.append(
                    f"{layer} key→parameter/model target 결합 불일치: {candidate_key}",
                )
    for layer, items in (
        ("parameter slot", parameter_slots),
        ("effective reference", effective_references),
    ):
        unknown_keys = sorted(
            {
                _candidate_key(item)
                for item in items
                if _candidate_key(item) not in runtime_by_candidate_key
            },
        )
        if unknown_keys:
            failures.append(f"{layer} candidate_key가 runtime 후보에 없음: {unknown_keys}")
    expected_selected_targets = {
        _basic_target_signature(candidate)
        for candidate in evidence.runtime_candidates
    }
    unexpected_selected_targets = {
        _basic_target_signature(item) for item in selected_items
    } - expected_selected_targets
    if unexpected_selected_targets:
        failures.append(
            "selected candidate target가 runtime 경계 밖임: "
            f"{sorted(unexpected_selected_targets)}",
        )

    response_data = _mapping(_mapping(record.get("final_response")).get("data"))
    proposed_items = _mapping_items(
        response_data.get("proposalParameters")
        or response_data.get("proposal_parameters"),
    )
    proposed_names = _parameter_names(proposed_items)
    try:
        presentation_items = [
            item.model_dump(mode="json", by_alias=True)
            for item in _proposal_parameters_from_state(
                {
                    "parameter_adjustments": adjustments,
                    "candidate_mappings": actual_runtime_items,
                },
                include_lut_value=False,
            )
        ]
    except Exception as exc:
        presentation_items = []
        failures.append(
            "production presentation projection 실패: "
            f"{_redact(repr(exc))}",
        )
    if _proposal_payload_multiset(
        presentation_items,
        drop_lut_value=True,
    ) != _proposal_payload_multiset(
        proposed_items,
        drop_lut_value=True,
    ):
        failures.append(
            "selected adjustment→production presentation→API target/value payload 불일치",
        )
    proposal_row = _mapping(record.get("proposal_db_row"))
    db_proposal_names = _parameter_names(proposal_row.get("proposal_parameters"))
    confirmed_names = _parameter_names(proposal_row.get("confirmation_parameters"))

    allowed_names = {
        _parameter_name(candidate)
        for candidate in evidence.runtime_candidates
        if _parameter_name(candidate)
    }
    blocked_names = {
        _parameter_name(candidate)
        for candidate in evidence.blocked_candidates
        if _parameter_name(candidate)
    }
    for layer, names in (
        ("runtime", _parameter_names(actual_runtime_items)),
        ("adjustment", _parameter_names(adjustments)),
        ("proposed", proposed_names),
        ("DB proposal", db_proposal_names),
        ("confirmed", confirmed_names),
    ):
        leaked = names & blocked_names
        if leaked:
            failures.append(f"active-but-blocked parameter가 {layer}에 누출: {sorted(leaked)}")
        unknown = names - allowed_names
        if unknown:
            failures.append(f"{layer} parameter가 runtime allowlist 후보 밖임: {sorted(unknown)}")
    for layer, items in (
        ("parameter_slots", parameter_slots),
        ("slot_candidate_mappings", slot_candidate_mappings),
        ("effective_references", effective_references),
    ):
        hits = _blocked_layer_hits(items, evidence.blocked_candidates)
        if hits:
            failures.append(
                f"active-but-blocked parameter가 {layer}에 누출: {sorted(hits)}",
            )

    actual_non_inputs = _mapping_items(result.get("non_input_items"))
    expected_non_input_counts = Counter(
        _non_input_signature(item)
        for item in (*evidence.matcher_non_inputs, *evidence.blocked_candidates)
    )
    actual_non_input_counts = Counter(
        _non_input_signature(item) for item in actual_non_inputs
    )
    if actual_non_input_counts != expected_non_input_counts:
        missing_non_inputs = sorted(
            (expected_non_input_counts - actual_non_input_counts).elements(),
        )
        unexpected_non_inputs = sorted(
            (actual_non_input_counts - expected_non_input_counts).elements(),
        )
        failures.append(
            "graph non_input_items identity/reason multiset 불일치: "
            f"missing={missing_non_inputs}, unexpected={unexpected_non_inputs}",
        )
    actual_reason_by_key = {
        _candidate_key(item): _text(item.get("reason_code") or item.get("reasonCode"))
        for item in actual_non_inputs
        if _candidate_key(item)
    }
    for blocked_key in expected_blocked_keys:
        reason = actual_reason_by_key.get(blocked_key)
        if reason != PROPOSAL_SCOPE_EXCLUDED_REASON_CODE:
            failures.append(
                "blocked candidate exclusion reason 누락/불일치: "
                f"candidate_key={blocked_key}, reason={reason or '-'}",
            )

    if selected_names != proposed_names:
        failures.append(
            f"selected→proposed parameter 불일치: selected={sorted(selected_names)}, proposed={sorted(proposed_names)}",
        )
    if proposed_names != db_proposal_names:
        failures.append(
            f"API→DB proposal parameter 불일치: api={sorted(proposed_names)}, db={sorted(db_proposal_names)}",
        )
    if _contains_lut_value(proposal_row.get("proposal_parameters")):
        failures.append("DB proposal payload에 response-only lutValue가 누출됨")
    if _contains_lut_value(proposal_row.get("confirmation_parameters")):
        failures.append("DB confirmation payload에 response-only lutValue가 누출됨")
    if _proposal_payload_multiset(
        proposed_items,
        drop_lut_value=True,
    ) != _proposal_payload_multiset(
        proposal_row.get("proposal_parameters"),
    ):
        failures.append(
            "API→DB proposal target/value payload 불일치(lutValue는 비교 제외)",
        )
    if db_proposal_names != confirmed_names:
        failures.append(
            "proposal→confirmation parameter 불일치: "
            f"proposal={sorted(db_proposal_names)}, confirmed={sorted(confirmed_names)}",
        )

    selected_slots = [item for item in parameter_slots if item.get("selected", True)]
    slot_catalog = _mapping_items(record.get("slot_catalog"))
    step_summary = _mapping(record.get("step_summary"))
    status_contracts = {
        "parameter_status": _text(step_summary.get("parameter_status")),
        "slot_status": _text(step_summary.get("slot_status")),
        "basecase_status": _text(step_summary.get("basecase_status")),
        "value_status": _text(step_summary.get("value_status")),
    }
    for status_name, status in status_contracts.items():
        if status == "REVIEW":
            reviews.append(f"step_summary {status_name}=REVIEW")
        elif status != "PASS":
            failures.append(
                f"step_summary {status_name}가 PASS가 아님: {status or 'missing'}",
            )

    selected_value_cells = [
        cell
        for adjustment in selected_items
        for cell in _mapping_items(adjustment.get("value_grid"))
    ]
    actual_counts = {
        "validated_candidate_count": len(actual_runtime_items),
        "selected_parameter_count": len(selected_items),
        "proposal_parameter_count": len(proposed_items),
        "selected_slot_count": len(selected_slots),
        "value_reference_record_count": len(effective_references),
        "value_cell_count": len(selected_value_cells),
        "value_cell_with_basecase_count": sum(
            cell.get("basecase_value") is not None
            for cell in selected_value_cells
        ),
    }
    for count_name, actual_count in actual_counts.items():
        summary_count = _int_or_none(step_summary.get(count_name))
        if summary_count != actual_count:
            failures.append(
                f"step_summary {count_name} 불일치: summary={summary_count}, actual={actual_count}",
            )

    if not slot_catalog:
        failures.append("Step2 slot_catalog이 비어 있음")
    if not selected_slots:
        failures.append("Step2 selected slot이 비어 있음")
    selected_slot_keys = {
        (
            _candidate_key(slot),
            _text(slot.get("slot_key") or slot.get("slotKey")),
        )
        for slot in selected_slots
    }
    reference_slot_keys = {
        (
            _candidate_key(reference),
            _text(reference.get("slot_key") or reference.get("slotKey")),
        )
        for reference in effective_references
    }
    if any(not candidate_key or not slot_key for candidate_key, slot_key in selected_slot_keys):
        failures.append("Step2 selected slot candidate_key/slot_key가 누락됨")
    if len(reference_slot_keys) != len(effective_references):
        failures.append("Step3 effective reference candidate/slot key가 누락 또는 중복")
    if selected_slot_keys != reference_slot_keys:
        failures.append(
            "Step2 selected slot과 Step3 effective reference key 집합이 불일치",
        )
    slot_links = [
        (
            _candidate_key(slot),
            _text(slot.get("slot_key") or slot.get("slotKey")),
        )
        for slot in selected_slots
    ]
    reference_links = [
        (
            _candidate_key(reference),
            _text(reference.get("slot_key") or reference.get("slotKey")),
        )
        for reference in effective_references
    ]
    if len(slot_links) != len(set(slot_links)):
        failures.append("Step2 selected slot candidate/slot key가 중복됨")
    slot_by_link = dict(zip(slot_links, selected_slots, strict=True))
    reference_by_link = dict(zip(reference_links, effective_references, strict=True))
    coordinate_mismatch_links = [
        link
        for link in set(slot_by_link) & set(reference_by_link)
        if _coordinate_signature(_slot_coordinates(slot_by_link[link]))
        != _coordinate_signature(reference_by_link[link].get("axes"))
    ]
    failures.extend(
        f"Step2 slot→effective reference axes 불일치: {link}"
        for link in coordinate_mismatch_links
    )

    catalog_by_key = {
        _candidate_key(catalog): catalog for catalog in slot_catalog
    }
    if len(catalog_by_key) != len(slot_catalog):
        failures.append("Step2 slot_catalog candidate_key가 누락 또는 중복됨")
    for slot in selected_slots:
        candidate_key = _candidate_key(slot)
        catalog = catalog_by_key.get(candidate_key)
        if catalog is None:
            failures.append(
                f"Step2 selected slot candidate가 slot_catalog에 없음: {candidate_key}",
            )
            continue
        allowed_coordinates = _catalog_coordinate_signatures(catalog)
        slot_signature = _coordinate_signature(_slot_coordinates(slot))
        if not allowed_coordinates:
            failures.append(
                f"slot_catalog exact coordinate 증적이 비어 있음: {candidate_key}",
            )
        elif slot_signature not in allowed_coordinates:
            failures.append(
                f"Step2 selected slot이 slot_catalog exact union 밖임: {candidate_key}",
            )

    reference_coordinate_counts = Counter(
        (
            _candidate_key(reference),
            _coordinate_signature(_reference_coordinates(reference)),
        )
        for reference in effective_references
    )
    adjustment_coordinate_counts = Counter(
        (
            _candidate_key(adjustment),
            _coordinate_signature(cell.get("coordinates")),
        )
        for adjustment in selected_items
        for cell in _mapping_items(adjustment.get("value_grid"))
    )
    if reference_coordinate_counts != adjustment_coordinate_counts:
        failures.append(
            "effective reference→Step3 adjustment candidate/coordinate multiset 불일치",
        )
    reference_by_coordinate: dict[tuple[str, str], dict[str, Any]] = {}
    for reference in effective_references:
        coordinate_key = (
            _candidate_key(reference),
            _coordinate_signature(_reference_coordinates(reference)),
        )
        if coordinate_key in reference_by_coordinate:
            failures.append(
                "effective reference candidate/coordinate가 중복됨: "
                f"{coordinate_key[0]}",
            )
        reference_by_coordinate[coordinate_key] = reference
    for adjustment in selected_items:
        candidate_key = _candidate_key(adjustment)
        for cell in _mapping_items(adjustment.get("value_grid")):
            coordinate_key = (
                candidate_key,
                _coordinate_signature(cell.get("coordinates")),
            )
            reference = reference_by_coordinate.get(coordinate_key)
            if reference is None:
                continue
            if not _same_scalar(
                cell.get("basecase_value"),
                reference.get("actual_basecase_value"),
            ):
                failures.append(
                    "effective reference→value cell basecase_value 불일치: "
                    f"{candidate_key}",
                )
            if not _same_scalar(
                cell.get("lut_value"),
                reference.get("lut_default_value"),
            ):
                failures.append(
                    "effective reference→value cell lut_value 불일치: "
                    f"{candidate_key}",
                )
            proposed_value = cell.get("proposed_value")
            try:
                proposed_number = float(proposed_value)
            except (TypeError, ValueError):
                proposed_number = math.nan
            if (
                isinstance(proposed_value, bool)
                or not isinstance(proposed_value, int | float)
                or not math.isfinite(proposed_number)
            ):
                failures.append(
                    f"Step3 proposed_value가 finite numeric이 아님: {candidate_key}",
                )
    for reference in effective_references:
        effective_source = _text(reference.get("effective_source"))
        llm_reference_value = reference.get("llm_reference_value")
        actual_basecase_value = reference.get("actual_basecase_value")
        lut_default_value = reference.get("lut_default_value")
        if llm_reference_value is None:
            failures.append("Step3 effective reference에 llm_reference_value가 누락됨")
        if actual_basecase_value is not None:
            if effective_source != "basecase" or not _same_scalar(
                llm_reference_value,
                actual_basecase_value,
            ):
                failures.append(
                    "Basecase-over-LUT precedence/llm_reference_value 계약 불일치",
                )
        elif lut_default_value is not None:
            if effective_source != "lut" or not _same_scalar(
                llm_reference_value,
                lut_default_value,
            ):
                failures.append(
                    "LUT fallback source/llm_reference_value 계약 불일치",
                )
        else:
            failures.append("effective reference에 Basecase/LUT value가 모두 없음")

    adjustment_value_count = len(selected_value_cells)
    api_value_count = _proposal_value_count(proposed_items)
    db_value_count = _proposal_value_count(proposal_row.get("proposal_parameters"))
    confirmed_value_count = _proposal_value_count(
        proposal_row.get("confirmation_parameters"),
    )
    value_counts = {
        adjustment_value_count,
        api_value_count,
        db_value_count,
        confirmed_value_count,
    }
    if len(value_counts) != 1 or adjustment_value_count != len(selected_slots):
        failures.append(
            "Step2 slot→Step3 adjustment→API/DB/confirmation value count 불일치: "
            f"slots={len(selected_slots)}, adjustment={adjustment_value_count}, "
            f"api={api_value_count}, db={db_value_count}, confirmed={confirmed_value_count}",
        )
    if any(
        cell.get("basecase_value") is None and cell.get("lut_value") is None
        for cell in selected_value_cells
    ):
        failures.append("Step3 value cell에 basecase/LUT reference value가 모두 누락됨")

    response_group_id = _int_or_none(
        response_data.get("scenarioGroupId")
        or response_data.get("scenario_group_id"),
    )
    if response_group_id != evidence.scenario_group_id:
        failures.append(
            f"API scenarioGroupId mismatch: {response_group_id} != {evidence.scenario_group_id}",
        )
    if _text(_mapping(record.get("final_response")).get("status")) != "success":
        failures.append("proposal API response status가 success가 아님")
    response_scenario_id = _int_or_none(
        response_data.get("scenarioId") or response_data.get("scenario_id"),
    )
    if response_scenario_id != evidence.scenario_id:
        failures.append(
            f"API scenarioId mismatch: {response_scenario_id} != {evidence.scenario_id}",
        )
    response_proposal_id = _int_or_none(
        response_data.get("modelParamProposalId")
        or response_data.get("model_param_proposal_id"),
    )
    db_proposal_id = _int_or_none(proposal_row.get("model_param_proposal_id"))
    if response_proposal_id is None or response_proposal_id != db_proposal_id:
        failures.append(
            "API→DB modelParamProposalId 불일치: "
            f"api={response_proposal_id}, db={db_proposal_id}",
        )
    if (
        "eventId" not in response_data
        and "event_id" not in response_data
    ) or (response_data.get("eventId") or response_data.get("event_id")) is not None:
        failures.append("v4 API eventId가 명시적 null이 아님")
    if _int_or_none(proposal_row.get("scenario_group_id")) != evidence.scenario_group_id:
        failures.append("proposal DB scenario_group_id가 실행 group과 불일치")
    if _int_or_none(proposal_row.get("scenario_id")) != evidence.scenario_id:
        failures.append("proposal DB scenario_id가 실행 scenario와 불일치")
    if proposal_row.get("mi_event_id") is not None:
        failures.append("v4 proposal DB mi_event_id가 NULL이 아님")
    if _text(proposal_row.get("status")) != "CONFIRMED":
        failures.append("proposal DB status가 CONFIRMED가 아님")
    if _mapping(record.get("confirmation")).get("status") != "PASS":
        failures.append("shared confirmation workflow가 PASS가 아님")
    if proposal_row.get("proposal_parameters") != proposal_row.get(
        "confirmation_parameters",
    ):
        failures.append("confirmation이 proposal payload를 그대로 보존하지 않음")

    attempts = _int_or_none(record.get("execution_attempt_count"))
    if attempts != 1:
        failures.append(f"write-producing workflow attempt는 1이어야 함: {attempts}")
    elapsed = record.get("elapsed_seconds")
    if isinstance(elapsed, int | float):
        if float(elapsed) > MAX_EXECUTION_SECONDS:
            failures.append(f"scenario execution이 {MAX_EXECUTION_SECONDS:.0f}초 초과: {elapsed}")
    else:
        reviews.append("scenario elapsed_seconds 미수집")
    llm_calls = _mapping_items(record.get("llm_calls"))
    if not llm_calls:
        reviews.append("LLM token/step 관측성 미수집")
    else:
        retry_values: list[int] = []
        retry_evidence_missing = False
        token_evidence_missing = False
        for call in llm_calls:
            raw_retry = (
                call.get("retry_count")
                if "retry_count" in call
                else call.get("internal_retry_count")
            )
            retry_count = _int_or_none(raw_retry)
            if retry_count is None:
                retry_evidence_missing = True
            else:
                retry_values.append(retry_count)
            usage = _mapping(call.get("usage"))
            if any(
                _int_or_none(usage.get(field_name)) is None
                for field_name in (
                    "prompt_tokens",
                    "completion_tokens",
                    "total_tokens",
                )
            ):
                token_evidence_missing = True
        if retry_evidence_missing:
            reviews.append("LLM retry count 관측성 미수집")
        if any(value > 0 for value in retry_values):
            reviews.append("내부 LLM retry 발생")
        if token_evidence_missing:
            reviews.append("LLM token usage 관측성 미수집")

    verdict: Verdict = "FAIL" if failures else "REVIEW" if reviews else "PASS"
    return ExecutionAssessment(
        scenario_id=evidence.scenario_id,
        verdict=verdict,
        failures=_dedupe(failures),
        reviews=_dedupe(reviews),
        raw_candidate_keys=tuple(sorted(actual_raw_keys)),
        runtime_candidate_keys=tuple(sorted(actual_runtime_keys)),
        selected_parameter_names=tuple(sorted(selected_names)),
        proposed_parameter_names=tuple(sorted(proposed_names)),
        confirmed_parameter_names=tuple(sorted(confirmed_names)),
    )


def build_coverage_rows(
    evidence: ScenarioEvidence,
    record: Mapping[str, Any] | None,
    assessment: ExecutionAssessment | None,
) -> list[CoverageRow]:
    active_names = sorted(
        {
            _parameter_name(definition)
            for definition in evidence.parameter_definitions
            if _parameter_name(definition)
        },
    )
    selected_candidate_items = (
        _mapping_items(
            record.get("runtime_candidates")
            if "runtime_candidates" in record
            else record.get("expected_candidates"),
        )
        if record is not None
        else []
    )
    response_data = _mapping(_mapping((record or {}).get("final_response")).get("data"))
    proposed_items = _mapping_items(
        response_data.get("proposalParameters")
        or response_data.get("proposal_parameters"),
    )
    confirmed_items = _mapping_items(
        _mapping((record or {}).get("proposal_db_row")).get(
            "confirmation_parameters",
        ),
    )
    actual_non_inputs = _mapping_items(
        _mapping((record or {}).get("result")).get("non_input_items"),
    )
    rows: list[CoverageRow] = []
    for name in active_names:
        classification: Literal["runtime-allowed", "active-but-blocked"] = (
            "runtime-allowed"
            if name in MODEL_PARAMETER_PROPOSAL_ALLOWLIST
            else "active-but-blocked"
        )
        raw = sum(_parameter_name(item) == name for item in evidence.raw_candidates)
        runtime = sum(
            _parameter_name(item) == name
            for item in evidence.runtime_candidates
        )
        selected = (
            sum(
                _parameter_name(item) == name
                for item in selected_candidate_items
            )
            if record is not None
            else None
        )
        proposed = (
            sum(_parameter_name(item) == name for item in proposed_items)
            if record is not None
            else None
        )
        confirmed = (
            sum(_parameter_name(item) == name for item in confirmed_items)
            if record is not None
            else None
        )
        if raw == 0:
            verdict: Verdict = "COVERAGE LIMIT"
            message = "selected Lever binding occurrence 없음"
        elif classification == "active-but-blocked":
            expected_keys = {
                _candidate_key(item)
                for item in evidence.blocked_candidates
                if _parameter_name(item) == name
            }
            actual_reasons = {
                _candidate_key(item): _text(item.get("reason_code"))
                for item in actual_non_inputs
                if _parameter_name(item) == name
            }
            if record is None:
                verdict = "PASS"
                message = "production partition에서 active-but-blocked + reason code 확인"
            elif (
                runtime == 0
                and selected == 0
                and proposed == 0
                and confirmed == 0
                and all(
                    actual_reasons.get(key) == PROPOSAL_SCOPE_EXCLUDED_REASON_CODE
                    for key in expected_keys
                )
            ):
                verdict = "PASS"
                message = "pre-LLM 차단 및 exact reason code 확인"
            else:
                verdict = "FAIL"
                message = "blocked leakage 또는 exclusion reason 누락"
        elif record is None:
            verdict = "COVERAGE LIMIT"
            message = "read-only: execution chain 미실행"
        elif assessment is not None and assessment.verdict == "FAIL":
            verdict = "FAIL"
            message = "scenario mandatory execution contract 실패"
        elif runtime and selected and proposed and confirmed:
            verdict = assessment.verdict if assessment is not None else "PASS"
            message = "eligible→runtime→selected→proposed→confirmed 연결"
        else:
            verdict = "REVIEW"
            message = "routing 미선택 또는 실행 chain 일부 미관측"
        rows.append(
            CoverageRow(
                scenario_id=evidence.scenario_id,
                parameter_name=name,
                classification=classification,
                raw=raw,
                runtime=runtime,
                selected=selected,
                proposed=proposed,
                confirmed=confirmed,
                exclusion_reason=(
                    PROPOSAL_SCOPE_EXCLUDED_REASON_CODE
                    if classification == "active-but-blocked" and raw
                    else ""
                ),
                verdict=verdict,
                evidence=message,
            ),
        )
    return rows


def _md(value: Any) -> str:
    if value is None:
        return "N/A"
    return str(value).replace("|", "\\|").replace("\n", " ")


def _count(value: int | None) -> str:
    return "N/A" if value is None else str(value)


def render_report(
    *,
    started_at: datetime,
    finished_at: datetime,
    execute: bool,
    verdict: Verdict,
    preflight: SchemaPreflight,
    core_smoke: CoreSmokeEvidence,
    evidences: Sequence[ScenarioEvidence],
    executions: Mapping[int, dict[str, Any]],
    assessments: Sequence[ExecutionAssessment],
    scope_errors: Sequence[str],
) -> str:
    assessment_by_id = {item.scenario_id: item for item in assessments}
    lines = [
        "# v4 Multi-Event Model Parameter Quality Report",
        "",
        f"- 시작: {started_at.isoformat(timespec='seconds')}",
        f"- 종료: {finished_at.isoformat(timespec='seconds')}",
        f"- 모드: {'EXECUTE (write)' if execute else 'READ-ONLY'}",
        f"- 종합 판정: **{verdict}**",
        f"- 대상 계약: `api_version={V4_API_VERSION}`, `generation_strategy={V4_STRATEGY}`",
        "- ordered event 경계: 1~5개",
        "- runtime allowlist: " + ", ".join(sorted(MODEL_PARAMETER_PROPOSAL_ALLOWLIST)),
        f"- blocked reason code: `{PROPOSAL_SCOPE_EXCLUDED_REASON_CODE}`",
        "",
        "## Preflight / automated gate",
        "",
        "| Gate | Verdict | Evidence |",
        "|---|---|---|",
        f"| DB schema | {preflight.verdict} | {_md('; '.join(preflight.errors or preflight.checks))} |",
        (
            f"| model_parameter_core | {core_smoke.status} | "
            f"rc={_md(core_smoke.return_code)}, elapsed={_md(core_smoke.elapsed_seconds)}, "
            f"{_md(core_smoke.message)} |"
        ),
        "",
        "## Target / catalog pin",
        "",
        "| Scenario | Group | API/strategy | Ordered events | Catalog stored → active | Verdict |",
        "|---:|---:|---|---|---|---|",
    ]
    for evidence in evidences:
        assessment = assessment_by_id.get(evidence.scenario_id)
        row_verdict: Verdict = (
            "FAIL"
            if evidence.errors
            else assessment.verdict
            if assessment is not None
            else "COVERAGE LIMIT"
        )
        lines.append(
            "| "
            f"{evidence.scenario_id} | {evidence.scenario_group_id} | "
            f"{_md(evidence.api_version)}/{_md(evidence.generation_strategy)} | "
            f"{_md(evidence.ordered_event_ids)} | "
            f"{_md(evidence.stored_catalog_version)}:{_md(evidence.stored_catalog_checksum[:12])} → "
            f"{_md(evidence.active_catalog_version)}:{_md(evidence.active_catalog_checksum[:12])} | "
            f"{row_verdict} |",
        )
    if not evidences:
        lines.append("| - | - | - | - | - | COVERAGE LIMIT |")

    lines.extend(
        [
            "",
            "## Catalog-pinned selected Lever evidence",
            "",
            "| Scenario | Dimension | Source events | Lever | Direction/domain | Bindings |",
            "|---:|---|---|---|---|---|",
        ],
    )
    for evidence in evidences:
        for lineage in evidence.dimension_lineage:
            for state in _mapping_items(lineage.get("lever_states")):
                bindings = [
                    f"{signature[0]}:{signature[3] or '-'}"
                    for signature in _binding_signature(state.get("parameter_bindings"))
                ]
                lines.append(
                    "| "
                    f"{evidence.scenario_id} | {_md(lineage.get('scenario_dimension_key'))} | "
                    f"{_md(lineage.get('source_event_ids'))} | {_md(state.get('lever_code'))} "
                    f"(id={_md(state.get('impact_lever_id'))}) | "
                    f"{_md(state.get('direction'))}/{_md(state.get('lever_domain'))} | "
                    f"{_md(', '.join(bindings) or '-')} |",
                )
    if not any(evidence.dimension_lineage for evidence in evidences):
        lines.append("| - | - | - | - | - | - |")

    coverage_rows = [
        row
        for evidence in evidences
        for row in build_coverage_rows(
            evidence,
            executions.get(evidence.scenario_id),
            assessment_by_id.get(evidence.scenario_id),
        )
    ]
    lines.extend(
        [
            "",
            "## Active parameter boundary matrix",
            "",
            (
                "| Scenario | Parameter | Classification | Raw | Runtime | Selected | "
                "Proposed | Confirmed | Reason | Verdict | Evidence |"
            ),
            "|---:|---|---|---:|---:|---:|---:|---:|---|---|---|",
        ],
    )
    lines.extend(
        [
            "| "
            f"{row.scenario_id} | {_md(row.parameter_name)} | {row.classification} | "
            f"{row.raw} | {_count(row.runtime)} | {_count(row.selected)} | "
            f"{_count(row.proposed)} | {_count(row.confirmed)} | "
            f"{_md(row.exclusion_reason or '-')} | {row.verdict} | {_md(row.evidence)} |"
            for row in coverage_rows
        ],
    )
    if not coverage_rows:
        lines.append("| - | - | - | - | - | - | - | - | - | COVERAGE LIMIT | 대상 없음 |")

    lines.extend(
        [
            "",
            "## Persistence / confirmation / observability",
            "",
            (
                "| Scenario | Proposal ID | Failed stage | Attempt | API eventId | DB event ID | DB group | "
                "Confirmation | Elapsed(s) | LLM calls | Verdict |"
            ),
            "|---:|---:|---|---:|---|---|---:|---|---:|---:|---|",
        ],
    )
    for evidence in evidences:
        record = executions.get(evidence.scenario_id)
        if record is None:
            lines.append(
                f"| {evidence.scenario_id} | N/A | N/A | N/A | N/A | N/A | "
                "N/A | NOT RUN | N/A | N/A | COVERAGE LIMIT |",
            )
            continue
        response_data = _mapping(_mapping(record.get("final_response")).get("data"))
        proposal_row = _mapping(record.get("proposal_db_row"))
        proposal_identifier = proposal_row.get("model_param_proposal_id")
        if proposal_identifier is None:
            proposal_identifier = record.get("model_param_proposal_id")
        if proposal_identifier is None:
            proposal_identifier = response_data.get(
                "modelParamProposalId",
                response_data.get("model_param_proposal_id"),
            )
        assessment = assessment_by_id.get(evidence.scenario_id)
        lines.append(
            "| "
            f"{evidence.scenario_id} | {_md(proposal_identifier)} | "
            f"{_md(record.get('failed_stage'))} | "
            f"{_md(record.get('execution_attempt_count'))} | "
            f"{_md(response_data.get('eventId', response_data.get('event_id')))} | "
            f"{_md(proposal_row.get('mi_event_id'))} | {_md(proposal_row.get('scenario_group_id'))} | "
            f"{_md(_mapping(record.get('confirmation')).get('status'))} | "
            f"{_md(record.get('elapsed_seconds'))} | {len(_mapping_items(record.get('llm_calls')))} | "
            f"{assessment.verdict if assessment else 'FAIL'} |",
        )

    lines.extend(
        [
            "",
            "## LLM token / retry evidence",
            "",
            "| Scenario | Step | Prompt tokens | Completion tokens | Total tokens | Internal retry |",
            "|---:|---|---:|---:|---:|---:|",
        ],
    )
    llm_row_count = 0
    for scenario_id, record in executions.items():
        for call in _mapping_items(record.get("llm_calls")):
            usage = _mapping(call.get("usage"))
            retry_count = (
                call.get("retry_count")
                if "retry_count" in call
                else call.get("internal_retry_count")
            )
            lines.append(
                "| "
                f"{scenario_id} | {_md(call.get('step'))} | "
                f"{_md(usage.get('prompt_tokens'))} | "
                f"{_md(usage.get('completion_tokens'))} | "
                f"{_md(usage.get('total_tokens'))} | {_md(retry_count)} |",
            )
            llm_row_count += 1
    if not llm_row_count:
        lines.append("| - | - | N/A | N/A | N/A | N/A |")

    all_errors = [*scope_errors, *preflight.errors]
    all_warnings: list[str] = []
    for evidence in evidences:
        all_errors.extend(
            f"scenario_id={evidence.scenario_id}: {message}"
            for message in evidence.errors
        )
        all_warnings.extend(
            f"scenario_id={evidence.scenario_id}: {message}"
            for message in evidence.warnings
        )
    for assessment in assessments:
        all_errors.extend(
            f"scenario_id={assessment.scenario_id}: {message}"
            for message in assessment.failures
        )
        all_warnings.extend(
            f"scenario_id={assessment.scenario_id}: {message}"
            for message in assessment.reviews
        )
    if core_smoke.status == "FAIL":
        all_errors.append(core_smoke.message)
    lines.extend(["", "## Errors / review items", ""])
    if all_errors:
        lines.extend(f"- FAIL: {_md(message)}" for message in _dedupe(all_errors))
    if all_warnings:
        lines.extend(f"- REVIEW: {_md(message)}" for message in _dedupe(all_warnings))
    if not all_errors and not all_warnings:
        lines.append("- 없음")
    if core_smoke.output_tail:
        lines.extend(
            [
                "",
                "### Automated gate output tail",
                "",
                "```text",
                core_smoke.output_tail,
                "```",
            ],
        )
    lines.extend(
        [
            "",
            "## Safety notes",
            "",
            "- 기본 모드는 DB read-only이며 graph/callback/confirmation을 호출하지 않는다.",
            "- `--execute`도 scenario별 write-producing workflow를 한 번만 호출하며 자동 retry하지 않는다.",
            "- `COVERAGE LIMIT`와 `REVIEW`는 CLI 성공(0), mandatory `FAIL`은 CLI 실패(1)다.",
            "",
        ],
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate v4 multi-event Model Parameter quality evidence.",
    )
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("--scenario-group-id", type=int)
    scope.add_argument("--scenario-id", type=int)
    parser.add_argument("--limit", type=int, default=DEFAULT_DISCOVERY_LIMIT)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Run one proposal+confirmation write workflow per eligible scenario.",
    )
    parser.add_argument("--report-path", type=Path)
    parser.add_argument(
        "--core-smoke-timeout",
        type=int,
        default=DEFAULT_CORE_SMOKE_TIMEOUT_SECONDS,
    )
    return parser


def _report_path(value: Path | None, started_at: datetime) -> Path:
    if value is not None:
        return value.expanduser().resolve()
    timestamp = started_at.strftime("%Y%m%d_%H%M%S_%f")
    return REPORT_DIR / f"model_parameter_v4_multi_event_quality_{timestamp}.md"


def _reserve_report_path(report_path: Path, started_at: datetime) -> None:
    """Fail before DB work if the required report cannot be created."""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("x", encoding="utf-8") as report_file:
        report_file.write(
            "# v4 Multi-Event Model Parameter Quality Report\n\n"
            f"- 상태: RUNNING\n- 시작: {started_at.isoformat(timespec='seconds')}\n",
        )


async def run_campaign(args: argparse.Namespace) -> CampaignResult:
    started_at = datetime.now(UTC)
    report_path = _report_path(args.report_path, started_at)
    _reserve_report_path(report_path, started_at)
    scope_errors: list[str] = []
    evidences: list[ScenarioEvidence] = []
    executions: dict[int, dict[str, Any]] = {}
    assessments: list[ExecutionAssessment] = []

    if args.limit < 1:
        scope_errors.append("--limit은 1 이상이어야 함")
    if args.core_smoke_timeout < 1:
        scope_errors.append("--core-smoke-timeout은 1 이상이어야 함")
    if (
        args.execute
        and args.scenario_id is None
        and args.scenario_group_id is None
    ):
        scope_errors.append(
            "--execute는 --scenario-id 또는 --scenario-group-id 명시 범위가 필수임",
        )
    preflight = (
        SchemaPreflight(
            verdict="COVERAGE LIMIT",
            checks=("argument safety gate에서 DB preflight 미실행",),
        )
        if scope_errors
        else _schema_preflight()
    )
    core_smoke = CoreSmokeEvidence(
        status="NOT RUN",
        message="argument/preflight gate or read-only mode",
    )
    if preflight.verdict != "FAIL" and not scope_errors:
        scenario_ids, discovery_errors = _discover_scenario_ids(args)
        scope_errors.extend(discovery_errors)
        loaded_evidences, context_errors = _load_scenario_evidences(scenario_ids)
        scope_errors.extend(context_errors)
        if args.scenario_group_id is not None:
            mismatched_group_ids = sorted(
                {
                    evidence.scenario_group_id
                    for evidence in loaded_evidences
                    if evidence.scenario_group_id != args.scenario_group_id
                },
            )
            if mismatched_group_ids:
                scope_errors.append(
                    "loaded evidence scenario_group_id가 명시 범위와 불일치: "
                    f"requested={args.scenario_group_id}, actual={mismatched_group_ids}",
                )
        scope_errors.extend(
            f"scanned scenario_id={evidence.scenario_id}: {message}"
            for evidence in loaded_evidences
            for message in evidence.errors
        )
        if args.scenario_id is not None or args.scenario_group_id is not None:
            evidences = loaded_evidences
        else:
            evidences = select_discovery_evidences(loaded_evidences, args.limit)
            if scenario_ids and not evidences:
                scope_errors.extend(context_errors or ["v4 discovery target context를 load하지 못함"])

    evidence_failures = any(evidence.errors for evidence in evidences)
    if args.execute and preflight.verdict != "FAIL" and not scope_errors and not evidence_failures:
        core_smoke = run_core_smoke(args.core_smoke_timeout)
        if core_smoke.status == "PASS":
            executions = await execute_targets(evidences)
            eligible_ids = {
                evidence.scenario_id
                for evidence in evidences
                if evidence.runtime_candidates and not evidence.errors
            }
            missing_execution_ids = sorted(eligible_ids - set(executions))
            unexpected_execution_ids = sorted(set(executions) - eligible_ids)
            if missing_execution_ids:
                scope_errors.append(
                    "eligible execute target의 execution record 누락: "
                    f"{missing_execution_ids}",
                )
            if unexpected_execution_ids:
                scope_errors.append(
                    "eligible 범위 밖 execution record 발생: "
                    f"{unexpected_execution_ids}",
                )
            assessments = [
                assess_execution(evidence, executions[evidence.scenario_id])
                for evidence in evidences
                if evidence.scenario_id in executions
            ]

    verdicts: list[Verdict] = []
    if (
        preflight.verdict == "FAIL"
        or scope_errors
        or evidence_failures
        or core_smoke.status == "FAIL"
    ):
        verdicts.append("FAIL")
    if not evidences:
        verdicts.append("FAIL" if scope_errors else "COVERAGE LIMIT")
    elif not args.execute or (
        not executions
        and not (scope_errors or evidence_failures or core_smoke.status == "FAIL")
    ):
        verdicts.append("COVERAGE LIMIT")
    verdicts.extend(assessment.verdict for assessment in assessments)
    assessment_by_id = {item.scenario_id: item for item in assessments}
    verdicts.extend(
        row.verdict
        for evidence in evidences
        for row in build_coverage_rows(
            evidence,
            executions.get(evidence.scenario_id),
            assessment_by_id.get(evidence.scenario_id),
        )
        if row.verdict in {"FAIL", "REVIEW"}
    )
    verdict = _combine_verdicts(verdicts)

    finished_at = datetime.now(UTC)
    report_path.write_text(
        render_report(
            started_at=started_at,
            finished_at=finished_at,
            execute=args.execute,
            verdict=verdict,
            preflight=preflight,
            core_smoke=core_smoke,
            evidences=evidences,
            executions=executions,
            assessments=assessments,
            scope_errors=scope_errors,
        ),
        encoding="utf-8",
    )
    return CampaignResult(
        verdict=verdict,
        report_path=report_path,
        preflight=preflight,
        core_smoke=core_smoke,
        evidences=tuple(evidences),
        executions=executions,
        assessments=tuple(assessments),
        scope_errors=_dedupe(scope_errors),
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = asyncio.run(run_campaign(args))
    except Exception as exc:
        print(
            f"FAIL: v4 multi-event quality runner crashed: {_redact(repr(exc))}",
            file=sys.stderr,
        )
        return 1
    print(
        json.dumps(
            {
                "verdict": result.verdict,
                "report_path": str(result.report_path),
                "scenario_count": len(result.evidences),
                "execution_count": len(result.executions),
            },
            ensure_ascii=False,
        ),
    )
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
