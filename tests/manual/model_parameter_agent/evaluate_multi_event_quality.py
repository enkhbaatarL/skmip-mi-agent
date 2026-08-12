# Copyright (c) 2026 SK Innovation E&S.
# ruff: noqa: ANN401, C901, E402, PERF401, S603, T201

from __future__ import annotations

import argparse
import asyncio
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
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

from sqlalchemy import inspect

from apps.common.configs.config import get_settings
from apps.common.configs.database.sync_database.connection import get_sync_session
from apps.persistence.event.repository import EventRepository
from apps.persistence.model_parameter.models import (
    MiModelParamDimensionMapModel,
    MiModelParamModel,
    MiModelParamProposalModel,
)
from apps.persistence.model_parameter.repository import ModelParameterRepository
from apps.persistence.scenario.models import (
    MiDimensionValueMappingModel,
    MiScenarioModel,
)
from apps.persistence.scenario.repository import ScenarioRepository
from apps.persistence.scenario_group.models import (
    MiScenarioGroupEventModel,
    MiScenarioGroupModel,
)
from apps.persistence.scenario_group.repository import ScenarioGroupRepository
from tests.manual.model_parameter_agent.runner_common import (
    execute_proposal_and_confirmation,
    json_safe,
)


V3_API_VERSION = "v3"
V3_STRATEGY = "multi_event_composite_dimensions"
REPORT_DIR = ROOT_DIR / "tests" / "reports" / "model_parameter_agent"
DEFAULT_ROUTING_LIMIT = 2
CONTRACT_TEST_CASES = (
    (
        "invalid-status service rollback",
        (
            "tests/automated/test_model_parameter_agent_contract.py::"
            "ModelParameterAgentContractTest::"
            "test_model_parameter_service_rejects_processing_confirmation_without_status_change"
        ),
    ),
    (
        "invalid-status workflow no-mutation",
        (
            "tests/automated/test_model_parameter_report_scope.py::"
            "test_invalid_status_confirmation_uses_existing_failed_row_without_mutation"
        ),
    ),
    (
        "custom parameter service persistence",
        (
            "tests/automated/test_model_parameter_agent_contract.py::"
            "ModelParameterAgentLLMTest::"
            "test_model_parameter_service_persists_unknown_parameter_metadata"
        ),
    ),
    (
        "persistence numeric precision",
        (
            "tests/automated/test_model_parameter_agent_contract.py::"
            "ModelParameterAgentContractTest::"
            "test_db_payload_uses_independent_basecase_and_proposed_precision"
        ),
    ),
    (
        "reconfirmation numeric precision",
        (
            "tests/automated/test_model_parameter_agent_contract.py::"
            "ModelParameterAgentContractTest::"
            "test_model_parameter_service_allows_reconfirming_confirmed_proposal"
        ),
    ),
    (
        "persistence finite numeric",
        (
            "tests/automated/test_model_parameter_multi_event_quality.py::"
            "test_persistence_contract_rejects_non_finite_numeric_values"
        ),
    ),
)
Verdict = Literal["PASS", "REVIEW", "FAIL", "COVERAGE LIMIT"]
_VERDICT_PRIORITY: dict[Verdict, int] = {
    "COVERAGE LIMIT": 0,
    "PASS": 1,
    "REVIEW": 2,
    "FAIL": 3,
}


@dataclass(frozen=True)
class ProjectionResult:
    occurrences: tuple[dict[str, Any], ...] = ()
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


@dataclass
class ScenarioEvidence:
    scenario_group_id: int
    scenario_id: int
    group_title: str
    scenario_title: str
    parameter_mapping_ready: bool
    relation_count: int
    group_event_ids: tuple[int, ...]
    ordered_events: tuple[dict[str, Any], ...] = ()
    occurrences: tuple[dict[str, Any], ...] = ()
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    dimension_values: dict[str, Any] = field(default_factory=dict)
    projection_statuses: tuple[str, ...] = ()
    dimension_source_event_ids: dict[str, tuple[int, ...]] = field(
        default_factory=dict,
    )
    dimension_source_refs: dict[str, tuple[dict[str, Any], ...]] = field(
        default_factory=dict,
    )
    approved_source_projections: dict[
        str,
        tuple[dict[str, Any], ...],
    ] = field(default_factory=dict)
    selection_skip_reason: str | None = None

    @property
    def eligible_parameters(self) -> set[str]:
        return {str(item.get("parameter_name") or "") for item in self.occurrences if item.get("parameter_name")}


@dataclass(frozen=True)
class CoverageRow:
    parameter_name: str
    eligible: int
    candidate: int | None
    selected: int | None
    proposed: int | None
    confirmed: int | None
    verdict: Verdict
    evidence: str


@dataclass(frozen=True)
class ParameterQualityRow:
    scenario_id: int
    parameter_name: str
    candidate_keys: tuple[str, ...]
    selected_slot_count: int
    exact_slot_count: int
    reference_count: int
    step3_value_count: int
    api_value_count: int
    db_value_count: int
    confirmed_value_count: int
    reference_sources: tuple[str, ...]
    source_count: int
    verdict: Verdict
    evidence: str
    manual_review: str


@dataclass(frozen=True)
class PerformanceRow:
    scenario_id: int
    step: str
    call_count: int
    prompt_bytes: int | None
    prompt_limit_bytes: tuple[int, ...]
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    elapsed_seconds: float | None
    outer_retry_count: int
    internal_retry_count: int | None
    verdict: Verdict
    evidence: str


@dataclass(frozen=True)
class PromptGroundingRow:
    scenario_id: int
    step: str
    event_ids: tuple[int, ...]
    dimension_keys: tuple[str, ...]
    verdict: Verdict
    evidence: str


@dataclass(frozen=True)
class SchemaPreflight:
    verdict: Verdict
    messages: tuple[str, ...]


@dataclass(frozen=True)
class ContractCaseEvidence:
    name: str
    node_id: str
    verdict: Verdict
    evidence: str


@dataclass(frozen=True)
class ContractEvidence:
    verdict: Verdict
    cases: tuple[ContractCaseEvidence, ...]
    elapsed_seconds: float | None
    evidence: str


def _value(value: Any, *names: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        for name in names:
            if name in value:
                return value[name]
        return default
    for name in names:
        if hasattr(value, name):
            return getattr(value, name)
    return default


def _int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _bounded_text(value: Any, *, limit: int) -> str:
    text = _clean(value).replace("\x00", "")
    return text if len(text) <= limit else text[: max(0, limit - 1)] + "…"


def _safe_exception_text(exc: BaseException) -> str:
    """Return stable error evidence without exception details or credentials."""
    return f"{type(exc).__name__}: details redacted"


def _redact_report_text(value: Any, *, limit: int | None = None) -> str:
    text = _clean(value).replace("\x00", "")
    if limit is not None and len(text) > limit:
        text = text[: max(0, limit - 1)] + "…"
    text = re.sub(
        r"(?i)\b(bearer)\s+[A-Za-z0-9._~+/=-]+",
        r"\1 [REDACTED]",
        text,
    )
    text = re.sub(
        r"(?i)([\"']?\b(?:password|passwd|pwd|token|secret|api[_-]?key|authorization)"
        r"\b[\"']?\s*[:=]\s*)(?:[\"'][^\"']*[\"']|[^\s,;|}]+)",
        r"\1[REDACTED]",
        text,
    )
    return re.sub(
        r"(?i)\b[a-z][a-z0-9+.-]*://[^\s]+",
        "[URL REDACTED]",
        text,
    )


def _redact_error_text(value: Any) -> str:
    text = _redact_report_text(value, limit=500)
    return text or "unknown error"


def _dimension_values(raw: Any) -> dict[str, Any]:
    if isinstance(raw, Mapping):
        return {str(key): value for key, value in raw.items() if str(key).strip()}
    if isinstance(raw, list):
        return {
            str(item.get("dim_key") or item.get("dimensionId")): item.get("value")
            for item in raw
            if isinstance(item, Mapping) and (item.get("dim_key") or item.get("dimensionId"))
        }
    return {}


def _target_signature(
    *,
    parameter_name: Any,
    model_file: Any,
    model_sheet: Any,
) -> tuple[str, str, str]:
    return (_clean(parameter_name), _clean(model_file), _clean(model_sheet))


def _stable_task_key(parameter_name: str, model_file: str, model_sheet: str) -> str:
    def normalize(value: Any) -> str:
        return re.sub(
            r"[^0-9a-zA-Z가-힣]+",
            "",
            str(value or ""),
        ).lower()

    return "|".join(
        (
            "parameter",
            "v3",
            normalize(model_file),
            normalize(model_sheet),
            normalize(parameter_name),
        ),
    )


def _normalized_relations(
    relations: Sequence[Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    normalized: list[dict[str, Any]] = []
    errors: list[str] = []
    seen_event_ids: set[int] = set()
    seen_display_orders: set[int] = set()
    for relation in relations:
        event_id = _int_or_none(_value(relation, "mi_event_id", "miEventId"))
        event_type_l2_id = _int_or_none(
            _value(relation, "event_type_l2_id", "eventTypeL2Id"),
        )
        template_id = _int_or_none(
            _value(
                relation,
                "scenario_dimension_template_id",
                "scenarioDimensionTemplateId",
            ),
        )
        if event_id is None or event_type_l2_id is None:
            errors.append("group-event relation의 event ID 또는 event type이 비어 있습니다.")
            continue
        if event_id in seen_event_ids:
            errors.append(f"group-event relation에 중복 event ID가 있습니다: {event_id}")
            continue
        seen_event_ids.add(event_id)
        display_order = _int_or_none(
            _value(relation, "display_order", "displayOrder"),
        )
        if display_order is None or display_order <= 0:
            errors.append(
                f"group-event relation의 display_order가 비어 있거나 유효하지 않습니다: event_id={event_id}",
            )
            display_order = 0
        elif display_order in seen_display_orders:
            errors.append(
                f"group-event relation에 중복 display_order가 있습니다: display_order={display_order}",
            )
        seen_display_orders.add(display_order)
        normalized.append(
            {
                "mi_event_id": event_id,
                "event_type_l2_id": event_type_l2_id,
                "scenario_dimension_template_id": template_id,
                "display_order": display_order,
            },
        )
    normalized.sort(key=lambda item: (item["display_order"], item["mi_event_id"]))
    return normalized, errors


def project_expected_mappings(
    *,
    dimension_definitions: Sequence[Any],
    scenario_dimension_values: Any,
    relations: Sequence[Any],
    mapping_rules: Sequence[Mapping[str, Any]],
    parameter_definitions: Sequence[Mapping[str, Any]],
) -> ProjectionResult:
    """Independently project v3 sourceRefs into canonical DB mappings.

    This deliberately does not call the production context adapter or matcher. It
    is the quality runner's independent oracle for lineage and mapping coverage.
    A source with no active mapping is a warning; malformed or orphan lineage is
    an error and must prevent execute mode for that scenario.
    """
    relation_rows, relation_errors = _normalized_relations(relations)
    errors = list(relation_errors)
    warnings: list[str] = []
    group_event_ids = {item["mi_event_id"] for item in relation_rows}
    relations_by_template: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for relation in relation_rows:
        template_id = relation["scenario_dimension_template_id"]
        if template_id is not None:
            relations_by_template[template_id].append(relation)

    definitions: dict[str, Any] = {}
    for raw_definition in dimension_definitions:
        dimension_id = _clean(
            _value(raw_definition, "dimension_id", "dimensionId"),
        )
        if not dimension_id:
            errors.append("dimensionDefinitions 항목에 dimensionId가 없습니다.")
            continue
        if dimension_id in definitions:
            errors.append(f"dimensionDefinitions에 중복 dimensionId가 있습니다: {dimension_id}")
            continue
        definitions[dimension_id] = raw_definition

    relation_event_ids_covered_by_definitions: set[int] = set()
    for dimension_id, definition in definitions.items():
        raw_event_ids = _value(
            definition,
            "source_event_ids",
            "sourceEventIds",
        )
        definition_event_ids = {
            event_id for raw_event_id in raw_event_ids or [] if (event_id := _int_or_none(raw_event_id)) is not None
        }
        raw_refs = _value(definition, "source_refs", "sourceRefs")
        definition_template_ids = {
            template_id
            for raw_ref in raw_refs or []
            if isinstance(raw_ref, Mapping)
            and (
                template_id := _int_or_none(
                    _value(
                        raw_ref,
                        "scenario_dimension_template_id",
                        "scenarioDimensionTemplateId",
                    ),
                )
            )
            is not None
        }
        for relation in relation_rows:
            if (
                relation["mi_event_id"] in definition_event_ids
                and relation["scenario_dimension_template_id"] in definition_template_ids
            ):
                relation_event_ids_covered_by_definitions.add(
                    relation["mi_event_id"],
                )
        if definition_event_ids and not definition_template_ids:
            errors.append(
                f"dimensionDefinition source event에 sourceRef가 없습니다: dimension={dimension_id}",
            )
    orphan_relation_event_ids = sorted(
        group_event_ids - relation_event_ids_covered_by_definitions,
    )
    if orphan_relation_event_ids:
        errors.append(
            "group relation event가 어떤 dimensionDefinition/sourceRef에도 연결되지 않습니다: "
            f"event_ids={orphan_relation_event_ids}",
        )

    dimension_values = _dimension_values(scenario_dimension_values)
    if not dimension_values:
        errors.append("scenario.dimension_values가 비어 있거나 JSON object가 아닙니다.")

    definition_by_parameter = {
        _clean(
            definition.get("canonical_parameter_name") or definition.get("parameter_name"),
        ): definition
        for definition in parameter_definitions
        if _clean(
            definition.get("canonical_parameter_name") or definition.get("parameter_name"),
        )
    }
    rules_by_source: dict[tuple[int, str], list[Mapping[str, Any]]] = defaultdict(list)
    for rule in mapping_rules:
        event_type_l2_id = _int_or_none(rule.get("event_type_l2_id"))
        dimension_key = _clean(rule.get("dimension_key"))
        if event_type_l2_id is not None and dimension_key:
            rules_by_source[(event_type_l2_id, dimension_key)].append(rule)

    occurrences_by_key: dict[tuple[Any, ...], dict[str, Any]] = {}
    for composite_key in dimension_values:
        definition = definitions.get(composite_key)
        if definition is None:
            warnings.append(
                f"dimensionDefinitions에 없는 자유 dimension value를 mapping에서 제외했습니다: {composite_key}",
            )
            continue

        raw_source_event_ids = _value(
            definition,
            "source_event_ids",
            "sourceEventIds",
        )
        if not isinstance(raw_source_event_ids, list) or not raw_source_event_ids:
            errors.append(f"sourceEventIds가 비어 있습니다: dimension={composite_key}")
            continue
        source_event_ids: list[int] = []
        malformed_event_id = False
        for raw_event_id in raw_source_event_ids:
            event_id = _int_or_none(raw_event_id)
            if event_id is None:
                malformed_event_id = True
                break
            source_event_ids.append(event_id)
        if malformed_event_id:
            errors.append(f"sourceEventIds에 정수가 아닌 값이 있습니다: dimension={composite_key}")
            continue
        if len(set(source_event_ids)) != len(source_event_ids):
            errors.append(f"sourceEventIds가 중복되었습니다: dimension={composite_key}")
            continue
        orphan_ids = sorted(set(source_event_ids) - group_event_ids)
        if orphan_ids:
            errors.append(
                f"sourceEventIds가 group relation에 없습니다: dimension={composite_key}, event_ids={orphan_ids}",
            )
            continue

        raw_refs = _value(definition, "source_refs", "sourceRefs")
        if not isinstance(raw_refs, list) or not raw_refs:
            errors.append(f"sourceRefs가 비어 있습니다: dimension={composite_key}")
            continue
        seen_refs: set[tuple[int, str]] = set()
        covered_event_ids: set[int] = set()
        for raw_ref in raw_refs:
            if not isinstance(raw_ref, Mapping):
                errors.append(f"sourceRef가 object가 아닙니다: dimension={composite_key}")
                continue
            template_id = _int_or_none(
                _value(
                    raw_ref,
                    "scenario_dimension_template_id",
                    "scenarioDimensionTemplateId",
                ),
            )
            mapping_dimension_key = _clean(
                _value(raw_ref, "dim_key", "dimKey"),
            )
            if template_id is None or not mapping_dimension_key:
                errors.append(
                    f"sourceRef의 template ID 또는 dimKey가 비어 있습니다: dimension={composite_key}",
                )
                continue
            ref_key = (template_id, mapping_dimension_key)
            if ref_key in seen_refs:
                errors.append(
                    "sourceRef가 중복되었습니다: "
                    f"dimension={composite_key}, template={template_id}, "
                    f"dimKey={mapping_dimension_key}",
                )
                continue
            seen_refs.add(ref_key)
            matching_relations = [
                relation
                for relation in relations_by_template.get(template_id, [])
                if relation["mi_event_id"] in source_event_ids
            ]
            if not matching_relations:
                errors.append(
                    "sourceRef가 group relation template과 연결되지 않습니다: "
                    f"dimension={composite_key}, template={template_id}, "
                    f"dimKey={mapping_dimension_key}",
                )
                continue
            covered_event_ids.update(relation["mi_event_id"] for relation in matching_relations)

            relations_by_event_type: dict[int, list[int]] = defaultdict(list)
            for relation in matching_relations:
                relations_by_event_type[relation["event_type_l2_id"]].append(
                    relation["mi_event_id"],
                )
            for event_type_l2_id, matched_event_ids in relations_by_event_type.items():
                source_rules = rules_by_source.get(
                    (event_type_l2_id, mapping_dimension_key),
                    [],
                )
                if not source_rules:
                    warnings.append(
                        "sourceRef에 활성 DB mapping이 없어 제외했습니다: "
                        f"event_type_l2_id={event_type_l2_id}, "
                        f"dimKey={mapping_dimension_key}, composite={composite_key}",
                    )
                    continue
                for rule in source_rules:
                    mapping_method = _clean(rule.get("mapping_method"))
                    if mapping_method not in {"direct", "routing"}:
                        continue
                    parameter_name = _clean(
                        rule.get("canonical_parameter_name"),
                    )
                    parameter_definition = definition_by_parameter.get(parameter_name)
                    if parameter_definition is None:
                        warnings.append(
                            "mapping의 parameter가 active master에 없어 제외했습니다: "
                            f"parameter={parameter_name or '<empty>'}",
                        )
                        continue
                    model_file = _clean(parameter_definition.get("model_file"))
                    model_sheet = _clean(parameter_definition.get("model_sheet"))
                    occurrence_key = (
                        composite_key,
                        template_id,
                        mapping_dimension_key,
                        event_type_l2_id,
                        parameter_name,
                        model_file,
                        model_sheet,
                        mapping_method,
                    )
                    occurrence = occurrences_by_key.setdefault(
                        occurrence_key,
                        {
                            "scenario_dimension_key": composite_key,
                            "scenario_dimension_value": dimension_values[composite_key],
                            "scenario_dimension_template_id": template_id,
                            "mapping_dimension_key": mapping_dimension_key,
                            "event_type_l2_id": event_type_l2_id,
                            "source_event_ids": [],
                            "mapping_method": mapping_method,
                            "parameter_name": parameter_name,
                            "model_file": model_file,
                            "model_sheet": model_sheet,
                            "candidate_key": _stable_task_key(
                                parameter_name,
                                model_file,
                                model_sheet,
                            ),
                        },
                    )
                    occurrence["source_event_ids"] = sorted(
                        set(occurrence["source_event_ids"]) | set(matched_event_ids),
                    )

        uncovered_ids = sorted(set(source_event_ids) - covered_event_ids)
        if uncovered_ids:
            errors.append(
                "sourceEventIds가 sourceRefs로 완전히 연결되지 않았습니다: "
                f"dimension={composite_key}, event_ids={uncovered_ids}",
            )

    occurrences = sorted(
        occurrences_by_key.values(),
        key=lambda item: (
            item["parameter_name"],
            item["scenario_dimension_key"],
            item["event_type_l2_id"],
            item["mapping_dimension_key"],
        ),
    )
    return ProjectionResult(
        occurrences=tuple(occurrences),
        warnings=tuple(dict.fromkeys(warnings)),
        errors=tuple(dict.fromkeys(errors)),
    )


def schema_preflight(session: Any) -> SchemaPreflight:
    required_columns = {
        MiScenarioGroupModel.__tablename__: {
            "scenario_group_id",
            "mi_event_id",
            "event_type_l2_id",
            "api_version",
            "generation_strategy",
            "parameter_mapping_ready",
            "dimension_definitions",
        },
        MiScenarioGroupEventModel.__tablename__: {
            "scenario_group_id",
            "mi_event_id",
            "event_type_l2_id",
            "scenario_dimension_template_id",
            "display_order",
        },
        MiDimensionValueMappingModel.__tablename__: {
            "scenario_group_id",
            "dimension_value_id",
            "dimension_id",
            "display_value",
            "source_projections",
            "status",
        },
        MiScenarioModel.__tablename__: {
            "scenario_id",
            "scenario_group_id",
            "dimension_values",
        },
        MiModelParamProposalModel.__tablename__: {
            "scenario_id",
            "scenario_group_id",
            "mi_event_id",
            "proposal_parameters",
            "confirmation_parameters",
        },
        MiModelParamModel.__tablename__: {
            "parameter_name",
            "model_file",
            "model_sheet",
            "use_yn",
            "del_yn",
        },
        MiModelParamDimensionMapModel.__tablename__: {
            "event_type_l2_id",
            "dimension_key",
            "mapping_method",
            "model_param_id",
            "use_yn",
            "del_yn",
        },
    }
    messages: list[str] = []
    try:
        db_inspector = inspect(session.get_bind())
        table_names = set(db_inspector.get_table_names())
        for table_name, expected_columns in required_columns.items():
            if table_name not in table_names:
                messages.append(f"필수 테이블이 없습니다: {table_name}")
                continue
            columns = {str(column["name"]): column for column in db_inspector.get_columns(table_name)}
            missing_columns = sorted(expected_columns - set(columns))
            if missing_columns:
                messages.append(
                    f"필수 컬럼이 없습니다: {table_name}.{missing_columns}",
                )
        proposal_columns = {
            str(column["name"]): column
            for column in db_inspector.get_columns(
                MiModelParamProposalModel.__tablename__,
            )
        }
        event_column = proposal_columns.get("mi_event_id")
        if event_column is not None and not bool(event_column.get("nullable")):
            messages.append(
                "proposal mi_event_id가 nullable이 아닙니다: nullable migration 필요",
            )
    except Exception as exc:
        messages.append(
            f"DB schema preflight 실행 실패: {_safe_exception_text(exc)}",
        )
    return SchemaPreflight(
        verdict="FAIL" if messages else "PASS",
        messages=tuple(messages or ["필수 v3/proposal schema와 nullable 계약을 확인했습니다."]),
    )


def run_automated_contract_preflight(
    *,
    timeout_seconds: float = 90.0,
) -> ContractEvidence:
    """Run isolated, non-mutating regression cases and retain actual outcomes."""
    started = time.perf_counter()
    cases: list[ContractCaseEvidence] = []
    contract_env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    for name, node_id in CONTRACT_TEST_CASES:
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "-q",
                    "-p",
                    "no:cacheprovider",
                    node_id,
                ],
                cwd=str(ROOT_DIR),
                env=contract_env,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired:
            cases.append(
                ContractCaseEvidence(
                    name=name,
                    node_id=node_id,
                    verdict="FAIL",
                    evidence=f"pytest timeout ({timeout_seconds:.0f}s); output redacted",
                ),
            )
            continue
        except OSError as exc:
            cases.append(
                ContractCaseEvidence(
                    name=name,
                    node_id=node_id,
                    verdict="FAIL",
                    evidence=_safe_exception_text(exc),
                ),
            )
            continue
        cases.append(
            ContractCaseEvidence(
                name=name,
                node_id=node_id,
                verdict="PASS" if result.returncode == 0 else "FAIL",
                evidence=(
                    "isolated mock/unit contract passed (not live DB evidence)"
                    if result.returncode == 0
                    else f"pytest exit_code={result.returncode}; output redacted"
                ),
            ),
        )
    verdict: Verdict = "FAIL" if any(case.verdict == "FAIL" for case in cases) else "PASS"
    return ContractEvidence(
        verdict=verdict,
        cases=tuple(cases),
        elapsed_seconds=time.perf_counter() - started,
        evidence=(
            "all isolated mock/unit contracts passed"
            if verdict == "PASS"
            else "one or more isolated automated contracts failed"
        ),
    )


def _group_is_v3(group: Any) -> bool:
    return (
        _clean(_value(group, "api_version")) == V3_API_VERSION
        and _clean(_value(group, "generation_strategy")) == V3_STRATEGY
    )


def _bounded_event_evidence(
    *,
    relation_rows: Sequence[Mapping[str, Any]],
    event_records: Mapping[int, Mapping[str, Any]] | None,
) -> tuple[tuple[dict[str, Any], ...], list[str]]:
    if event_records is None:
        return (), []
    events: list[dict[str, Any]] = []
    errors: list[str] = []
    for relation in relation_rows:
        event_id = int(relation["mi_event_id"])
        event = event_records.get(event_id)
        if event is None:
            errors.append(
                f"group-event relation이 존재하지 않는 event를 참조합니다: event_id={event_id}",
            )
            continue
        actual_event_type = _int_or_none(
            _value(event, "event_type_l2_id", "eventTypeL2Id"),
        )
        relation_event_type = int(relation["event_type_l2_id"])
        if actual_event_type != relation_event_type:
            errors.append(
                "group-event relation과 event의 event type이 다릅니다: "
                f"event_id={event_id}, relation={relation_event_type}, actual={actual_event_type}",
            )
        raw_bullets = _value(event, "key_bullets", "keyBullets", default=[])
        raw_tags = _value(event, "tags", default=[])
        events.append(
            {
                "display_order": int(relation["display_order"]),
                "mi_event_id": event_id,
                "event_type_l2_id": relation_event_type,
                "scenario_dimension_template_id": relation.get(
                    "scenario_dimension_template_id",
                ),
                "title": _bounded_text(
                    _value(
                        event,
                        "event_title_ko",
                        "event_title",
                        "title",
                    ),
                    limit=500,
                ),
                "one_line_summary": _bounded_text(
                    _value(event, "one_line_summary", "oneLineSummary"),
                    limit=300,
                ),
                "key_bullets": [
                    _bounded_text(item, limit=300)
                    for item in (raw_bullets if isinstance(raw_bullets, list) else [])[:5]
                ],
                "tags": [
                    _bounded_text(item, limit=100) for item in (raw_tags if isinstance(raw_tags, list) else [])[:8]
                ],
                "detail_excerpt": str(
                    _value(
                        event,
                        "detail_analysis",
                        "detailAnalysis",
                        default="",
                    )
                    or "",
                )[:1200],
            },
        )
    return tuple(events), errors


def _build_scenario_evidence(
    *,
    group: Any,
    scenario: Any,
    relations: Sequence[Any],
    dimension_mappings: Sequence[Any],
    mapping_rules: Sequence[Mapping[str, Any]],
    parameter_definitions: Sequence[Mapping[str, Any]],
    event_records: Mapping[int, Mapping[str, Any]] | None = None,
) -> ScenarioEvidence:
    relation_rows, relation_errors = _normalized_relations(relations)
    projection = project_expected_mappings(
        dimension_definitions=_value(group, "dimension_definitions", default=[]) or [],
        scenario_dimension_values=_value(scenario, "dimension_values", default={}),
        relations=relations,
        mapping_rules=mapping_rules,
        parameter_definitions=parameter_definitions,
    )
    relation_count = len(relation_rows)
    errors = [*projection.errors]
    if relation_count < 2 or relation_count > 5:
        errors.append(
            f"v3 group-event relation 수가 2~5 경계를 벗어났습니다: {relation_count}",
        )
    errors.extend(relation_errors)
    ordered_events, event_errors = _bounded_event_evidence(
        relation_rows=relation_rows,
        event_records=event_records,
    )
    errors.extend(event_errors)
    dimension_values = _dimension_values(
        _value(scenario, "dimension_values", default={}),
    )
    dimension_source_event_ids: dict[str, tuple[int, ...]] = {}
    dimension_source_refs: dict[str, tuple[dict[str, Any], ...]] = {}
    for raw_definition in (
        _value(
            group,
            "dimension_definitions",
            default=[],
        )
        or []
    ):
        if not isinstance(raw_definition, Mapping):
            continue
        dimension_key = _clean(
            _value(raw_definition, "dimension_id", "dimensionId"),
        )
        if dimension_key not in dimension_values:
            continue
        source_event_ids = tuple(
            event_id
            for raw_event_id in (
                _value(
                    raw_definition,
                    "source_event_ids",
                    "sourceEventIds",
                    default=[],
                )
                or []
            )
            if (event_id := _int_or_none(raw_event_id)) is not None
        )
        source_refs: list[dict[str, Any]] = []
        for raw_ref in (
            _value(
                raw_definition,
                "source_refs",
                "sourceRefs",
                default=[],
            )
            or []
        ):
            if not isinstance(raw_ref, Mapping):
                continue
            template_id = _int_or_none(
                _value(
                    raw_ref,
                    "scenario_dimension_template_id",
                    "scenarioDimensionTemplateId",
                ),
            )
            dim_key = _clean(_value(raw_ref, "dim_key", "dimKey"))
            if template_id is None or not dim_key:
                continue
            source_refs.append(
                {
                    "scenario_dimension_template_id": template_id,
                    "dim_key": dim_key,
                },
            )
        dimension_source_event_ids[dimension_key] = source_event_ids
        dimension_source_refs[dimension_key] = tuple(source_refs)

    projection_statuses: list[str] = []
    projection_warnings: list[str] = []
    approved_source_projections: dict[
        str,
        tuple[dict[str, Any], ...],
    ] = {}
    for dimension_key, selected_value in dimension_values.items():
        matching = [
            mapping
            for mapping in dimension_mappings
            if _clean(_value(mapping, "dimension_id", "dimensionId")) == dimension_key
            and _clean(
                _value(
                    mapping,
                    "display_value",
                    "displayValue",
                    "dimension_value_id",
                    "dimensionValueId",
                ),
            )
            == _clean(selected_value)
        ]
        if not matching:
            projection_statuses.append(f"{dimension_key}=missing")
            projection_warnings.append(
                "선택 dimension value에 승인 projection이 없어 raw composite value를 사용합니다: "
                f"dimension={dimension_key}",
            )
            continue
        statuses = sorted(
            {_clean(_value(mapping, "status")) or "unknown" for mapping in matching},
        )
        projection_statuses.extend(f"{dimension_key}={status}" for status in statuses)
        approved_source_projections[dimension_key] = tuple(
            json_safe(dict(projection))
            for mapping in matching
            if _clean(_value(mapping, "status")) == "approved"
            for projection in (
                _value(
                    mapping,
                    "source_projections",
                    "sourceProjections",
                    default=[],
                )
                or []
            )
            if isinstance(projection, Mapping)
        )
        if "approved" not in statuses:
            projection_warnings.append(
                "선택 dimension value projection이 승인 상태가 아니어서 보조 근거에서 제외됩니다: "
                f"dimension={dimension_key}, statuses={statuses}",
            )
    if not bool(_value(group, "parameter_mapping_ready", default=False)):
        projection_warnings.append(
            "parameter_mapping_ready=false이지만 proposal eligibility gate로 사용하지 않습니다.",
        )

    return ScenarioEvidence(
        scenario_group_id=int(_value(group, "scenario_group_id")),
        scenario_id=int(_value(scenario, "scenario_id")),
        group_title=_clean(_value(group, "title")),
        scenario_title=_clean(_value(scenario, "title")),
        parameter_mapping_ready=bool(
            _value(group, "parameter_mapping_ready", default=False),
        ),
        relation_count=relation_count,
        group_event_ids=tuple(item["mi_event_id"] for item in relation_rows),
        ordered_events=ordered_events,
        occurrences=projection.occurrences,
        warnings=tuple(
            dict.fromkeys([*projection.warnings, *projection_warnings]),
        ),
        errors=tuple(dict.fromkeys(errors)),
        dimension_values=dimension_values,
        projection_statuses=tuple(projection_statuses),
        dimension_source_event_ids=dimension_source_event_ids,
        dimension_source_refs=dimension_source_refs,
        approved_source_projections=approved_source_projections,
    )


def discover_v3_scenarios(
    session: Any,
    *,
    scenario_group_id: int | None = None,
    scenario_id: int | None = None,
) -> tuple[list[ScenarioEvidence], list[dict[str, Any]], list[str]]:
    group_repository = ScenarioGroupRepository(session=session)
    scenario_repository = ScenarioRepository(session=session)
    event_repository = EventRepository(session=session)
    parameter_repository = ModelParameterRepository(session=session)
    mapping_rules, parameter_definitions = parameter_repository.fetch_parameter_mapping_resources()

    discovery_messages: list[str] = []
    if scenario_id is not None:
        scenario = scenario_repository.fetch_model_by_id(scenario_id)
        if scenario is None:
            return [], parameter_definitions, [f"scenario를 찾을 수 없습니다: {scenario_id}"]
        group = group_repository.fetch_by_id(int(scenario.scenario_group_id))
        groups = [group] if group is not None else []
        scenarios_by_group = {int(scenario.scenario_group_id): [scenario]}
    elif scenario_group_id is not None:
        group = group_repository.fetch_by_id(scenario_group_id)
        groups = [group] if group is not None else []
        scenarios_by_group = {
            scenario_group_id: scenario_repository.fetch_models_by_group_id(
                scenario_group_id,
            ),
        }
    else:
        groups = [group for group in group_repository.list_for_backoffice(sort="latest") if _group_is_v3(group)]
        scenarios_by_group = {
            int(group.scenario_group_id): scenario_repository.fetch_models_by_group_id(
                int(group.scenario_group_id),
            )
            for group in groups
        }

    if not groups:
        if scenario_id is not None or scenario_group_id is not None:
            discovery_messages.append("지정한 scenario/group을 찾지 못했습니다.")
        else:
            discovery_messages.append("실제 v3 multi-event scenario group이 없습니다.")
        return [], parameter_definitions, discovery_messages

    evidences: list[ScenarioEvidence] = []
    for group in groups:
        if not _group_is_v3(group):
            discovery_messages.append(
                "지정 대상이 v3 multi_event_composite_dimensions가 아닙니다: "
                f"scenario_group_id={group.scenario_group_id}",
            )
            continue
        group_id = int(group.scenario_group_id)
        relations = group_repository.fetch_group_events(group_id)
        event_records: dict[int, Mapping[str, Any]] = {}
        for relation in relations:
            event_id = _int_or_none(_value(relation, "mi_event_id", "miEventId"))
            if event_id is None:
                continue
            event = event_repository.fetch_event_by_id(event_id)
            if isinstance(event, Mapping):
                event_records[event_id] = event
        dimension_mappings = scenario_repository.fetch_mappings_by_group_id(
            group_id,
        )
        scenarios = scenarios_by_group.get(group_id) or []
        if not scenarios:
            discovery_messages.append(
                f"group에 활성 scenario가 없습니다: scenario_group_id={group_id}",
            )
            continue
        for scenario in scenarios:
            evidences.append(
                _build_scenario_evidence(
                    group=group,
                    scenario=scenario,
                    relations=relations,
                    dimension_mappings=dimension_mappings,
                    mapping_rules=mapping_rules,
                    parameter_definitions=parameter_definitions,
                    event_records=event_records,
                ),
            )
    return evidences, parameter_definitions, discovery_messages


def _coverage_features(target: ScenarioEvidence) -> set[str]:
    features = {f"parameter:{name}" for name in target.eligible_parameters}
    dimensions_by_parameter: dict[str, set[str]] = defaultdict(set)
    event_types_by_parameter: dict[str, set[int]] = defaultdict(set)
    parameters_by_dimension: dict[str, set[str]] = defaultdict(set)
    for occurrence in target.occurrences:
        parameter_name = str(occurrence["parameter_name"])
        dimension_key = str(occurrence["scenario_dimension_key"])
        dimensions_by_parameter[parameter_name].add(dimension_key)
        event_types_by_parameter[parameter_name].add(
            int(occurrence["event_type_l2_id"]),
        )
        parameters_by_dimension[dimension_key].add(parameter_name)
    features.update(
        f"convergence:{parameter_name}"
        for parameter_name, dimensions in dimensions_by_parameter.items()
        if len(dimensions) > 1 or len(event_types_by_parameter[parameter_name]) > 1
    )
    features.update(
        f"expansion:{dimension_key}"
        for dimension_key, parameters in parameters_by_dimension.items()
        if len(parameters) > 1
    )
    return features


def select_quality_targets(
    candidates: Sequence[ScenarioEvidence],
    *,
    max_scenarios: int,
    explicit_scope: bool,
) -> tuple[list[ScenarioEvidence], list[ScenarioEvidence]]:
    ordered = sorted(
        candidates,
        key=lambda item: (item.scenario_group_id, item.scenario_id),
    )
    for item in ordered:
        item.selection_skip_reason = None
    if explicit_scope:
        return ordered, []

    valid = [item for item in ordered if not item.errors]
    invalid = [item for item in ordered if item.errors]
    selected: list[ScenarioEvidence] = []
    remaining = list(valid)
    covered_features: set[str] = set()
    while remaining and len(selected) < max_scenarios:
        ranked = sorted(
            remaining,
            key=lambda item: (
                len(_coverage_features(item) - covered_features),
                len(item.occurrences),
                item.scenario_group_id,
                item.scenario_id,
            ),
            reverse=True,
        )
        best = ranked[0]
        new_features = _coverage_features(best) - covered_features
        if selected and not new_features:
            break
        selected.append(best)
        covered_features.update(_coverage_features(best))
        remaining.remove(best)
    selected_occurrence_keys = {key for target in selected for key in _expected_occurrence_keys(target.occurrences)}
    cap_reached = bool(remaining) and len(selected) >= max_scenarios
    for item in remaining:
        unique_eligible_count = len(
            _expected_occurrence_keys(item.occurrences) - selected_occurrence_keys,
        )
        if cap_reached:
            reason = f"max_scenarios={max_scenarios} cap으로 미선택"
        else:
            reason = "coverage feature가 기선택 대상과 중복되어 미선택"
        item.selection_skip_reason = f"{reason}; unique eligible occurrence={unique_eligible_count}"
    # Invalid discovered lineage must remain selected FAIL evidence instead of
    # disappearing behind automatic coverage selection.
    return [*selected, *invalid], remaining


def _parameter_name(item: Mapping[str, Any]) -> str:
    return _clean(
        item.get("canonical_parameter_name") or item.get("parameter_name") or item.get("parameterName"),
    )


def _model_target(item: Mapping[str, Any]) -> tuple[str, str]:
    target = item.get("modelTarget") or item.get("model_target") or {}
    if not isinstance(target, Mapping):
        target = {}
    return (
        _clean(item.get("model_file") or target.get("modelFile") or target.get("model_file")),
        _clean(item.get("model_sheet") or target.get("modelSheet") or target.get("model_sheet")),
    )


def _actual_occurrence_keys(items: Iterable[Any]) -> set[tuple[Any, ...]]:
    keys: set[tuple[Any, ...]] = set()
    for raw_item in items:
        if not isinstance(raw_item, Mapping):
            continue
        parameter_name = _parameter_name(raw_item)
        model_file, model_sheet = _model_target(raw_item)
        raw_sources = raw_item.get("sources") or raw_item.get("source_dimensions") or raw_item.get("sourceDimensions")
        sources = (
            [item for item in raw_sources if isinstance(item, Mapping)] if isinstance(raw_sources, list) else [raw_item]
        )
        for source in sources:
            composite_key = _clean(
                source.get("scenario_dimension_key")
                or source.get("source_dimension_id")
                or source.get("dimension_key"),
            )
            template_id = _int_or_none(
                source.get("scenario_dimension_template_id") or source.get("scenarioDimensionTemplateId"),
            )
            mapping_dimension_key = _clean(
                source.get("mapping_dimension_key") or source.get("mappingDimensionKey"),
            )
            event_type_l2_id = _int_or_none(
                source.get("event_type_l2_id") or source.get("eventTypeL2Id"),
            )
            mapping_method = _clean(
                source.get("mapping_method") or raw_item.get("mapping_method"),
            )
            source_event_ids = source.get("source_event_ids") or source.get("sourceEventIds") or [None]
            if not isinstance(source_event_ids, list):
                source_event_ids = [source_event_ids]
            for source_event_id in source_event_ids or [None]:
                keys.add(
                    (
                        composite_key,
                        template_id,
                        mapping_dimension_key,
                        event_type_l2_id,
                        _int_or_none(source_event_id),
                        parameter_name,
                        model_file,
                        model_sheet,
                        mapping_method,
                    ),
                )
    return keys


def _expected_occurrence_keys(
    occurrences: Iterable[Mapping[str, Any]],
) -> set[tuple[Any, ...]]:
    keys: set[tuple[Any, ...]] = set()
    for occurrence in occurrences:
        for source_event_id in occurrence.get("source_event_ids") or [None]:
            keys.add(
                (
                    _clean(occurrence.get("scenario_dimension_key")),
                    _int_or_none(occurrence.get("scenario_dimension_template_id")),
                    _clean(occurrence.get("mapping_dimension_key")),
                    _int_or_none(occurrence.get("event_type_l2_id")),
                    _int_or_none(source_event_id),
                    _clean(occurrence.get("parameter_name")),
                    _clean(occurrence.get("model_file")),
                    _clean(occurrence.get("model_sheet")),
                    _clean(occurrence.get("mapping_method")),
                ),
            )
    return keys


def _selected_routing_targets_by_dimension(
    items: Iterable[Any],
) -> dict[str, set[tuple[str, str, str]]]:
    targets_by_dimension: dict[str, set[tuple[str, str, str]]] = defaultdict(set)
    for key in _actual_occurrence_keys(items):
        if key[-1] != "routing" or not _clean(key[0]):
            continue
        targets_by_dimension[_clean(key[0])].add(
            (_clean(key[5]), _clean(key[6]), _clean(key[7])),
        )
    return targets_by_dimension


def _routing_limit_from_settings() -> int:
    try:
        value = int(
            get_settings().model_parameter_max_routing_candidates_per_dimension,
        )
    except (AttributeError, TypeError, ValueError):
        return DEFAULT_ROUTING_LIMIT
    return max(1, value)


def _parameter_targets(items: Iterable[Any]) -> set[tuple[str, str, str]]:
    targets: set[tuple[str, str, str]] = set()
    for item in items:
        if not isinstance(item, Mapping):
            continue
        parameter_name = _parameter_name(item)
        model_file, model_sheet = _model_target(item)
        if parameter_name:
            targets.add(
                _target_signature(
                    parameter_name=parameter_name,
                    model_file=model_file,
                    model_sheet=model_sheet,
                ),
            )
    return targets


def _final_proposal_parameters(record: Mapping[str, Any]) -> list[dict[str, Any]]:
    data = (record.get("final_response") or {}).get("data") or {}
    parameters = data.get("proposalParameters") or data.get("proposal_parameters") or []
    return [item for item in parameters if isinstance(item, dict)]


def _confirmed_parameters(record: Mapping[str, Any]) -> list[dict[str, Any]]:
    row = record.get("proposal_db_row") or {}
    parameters = row.get("confirmation_parameters") or []
    return [item for item in parameters if isinstance(item, dict)]


def _definition_target(definition: Mapping[str, Any]) -> tuple[str, str, str]:
    return _target_signature(
        parameter_name=(definition.get("canonical_parameter_name") or definition.get("parameter_name")),
        model_file=definition.get("model_file"),
        model_sheet=definition.get("model_sheet"),
    )


def _quality_axis_value(axis_name: str, value: Any) -> Any:
    if value is None or isinstance(value, bool):
        return value
    if axis_name.lower() in {"year", "month", "period"}:
        parsed = _int_or_none(value)
        if parsed is not None:
            return parsed
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def _quality_coordinates(raw: Mapping[str, Any]) -> dict[str, Any]:
    coordinates: dict[str, Any] = {}
    raw_axes = raw.get("slot_axes") or raw.get("slotAxes")
    if isinstance(raw_axes, list):
        for axis in raw_axes:
            if not isinstance(axis, Mapping):
                continue
            axis_name = _clean(axis.get("axis_name") or axis.get("axisName"))
            if axis_name:
                coordinates[axis_name] = _quality_axis_value(
                    axis_name,
                    axis.get("axis_value") if "axis_value" in axis else axis.get("axisValue"),
                )
        return coordinates
    raw_coordinates = raw.get("coordinates") or raw.get("axes") or {}
    if not isinstance(raw_coordinates, Mapping):
        return {}
    return {
        str(axis_name): _quality_axis_value(str(axis_name), axis_value)
        for axis_name, axis_value in raw_coordinates.items()
    }


def _quality_reference_coordinates(
    reference: Mapping[str, Any],
) -> dict[str, Any]:
    coordinates = _quality_coordinates(reference)
    metadata = reference.get("metadata") or {}
    if isinstance(metadata, Mapping):
        coordinates.update(
            {
                str(axis_name): _quality_axis_value(
                    str(axis_name),
                    axis_value,
                )
                for axis_name, axis_value in metadata.items()
            },
        )
    return coordinates


def _coordinates_contain(
    coordinates: Mapping[str, Any],
    expected: Mapping[str, Any],
) -> bool:
    return all(
        axis_name in coordinates and _quality_values_equal(coordinates[axis_name], axis_value)
        for axis_name, axis_value in expected.items()
    )


def _quality_coordinate_key(coordinates: Mapping[str, Any]) -> str:
    normalized = {
        str(axis_name): _quality_axis_value(str(axis_name), axis_value)
        for axis_name, axis_value in sorted(coordinates.items())
    }
    return json.dumps(normalized, ensure_ascii=False, sort_keys=True, default=str)


def _quality_values_equal(left: Any, right: Any) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return left is right
    try:
        return float(left) == float(right)
    except (TypeError, ValueError):
        return left == right


def _period_group_matches(
    period_group: Mapping[str, Any],
    *,
    time_axes: Sequence[str],
    coordinates: Mapping[str, Any],
) -> bool:
    expected = {axis_name: coordinates.get(axis_name) for axis_name in time_axes}
    periods = period_group.get("available_periods") or []
    for period in periods:
        if not isinstance(period, Mapping):
            continue
        if tuple(time_axes) == ("Year", "Month") and "Months" in period:
            if not _quality_values_equal(period.get("Year"), expected.get("Year")):
                continue
            return any(_quality_values_equal(month, expected.get("Month")) for month in period.get("Months") or [])
        if all(_quality_values_equal(period.get(axis_name), expected.get(axis_name)) for axis_name in time_axes):
            return True
    return not time_axes and any(not period for period in periods)


def _slot_is_in_exact_catalog(
    slot: Mapping[str, Any],
    slot_catalog: Sequence[Any],
) -> bool:
    candidate_key = _clean(slot.get("candidate_key") or slot.get("candidateKey"))
    raw_axes = slot.get("slot_axes") or slot.get("slotAxes")
    if isinstance(raw_axes, list):
        axis_names = [
            _clean(axis.get("axis_name") or axis.get("axisName")) for axis in raw_axes if isinstance(axis, Mapping)
        ]
        if not axis_names or len(axis_names) != len(set(axis_names)):
            return False
    coordinates = _quality_coordinates(slot)
    catalog = next(
        (
            item
            for item in slot_catalog
            if isinstance(item, Mapping)
            and _clean(item.get("candidate_key") or item.get("candidateKey")) == candidate_key
        ),
        None,
    )
    if catalog is None:
        return False
    key_axes = [str(item) for item in catalog.get("key_axes") or catalog.get("keyAxes") or []]
    if set(coordinates) != set(key_axes):
        return False
    fixed_axes = [str(item) for item in catalog.get("fixed_axis_names") or catalog.get("fixedAxisNames") or []]
    time_axes = [str(item) for item in catalog.get("time_axis_names") or catalog.get("timeAxisNames") or []]
    nodes = catalog.get("fixed_axis_hierarchy") or catalog.get("fixedAxisHierarchy") or []
    terminal: Mapping[str, Any] | None = None
    for axis_name in fixed_axes:
        terminal = next(
            (
                node
                for node in nodes
                if isinstance(node, Mapping)
                and _quality_values_equal(node.get("axis_value"), coordinates.get(axis_name))
            ),
            None,
        )
        if terminal is None:
            return False
        nodes = terminal.get("children") or []
    if not fixed_axes:
        terminal = next(
            (node for node in nodes if isinstance(node, Mapping)),
            None,
        )
    period_group_id = _clean((terminal or {}).get("period_group_id"))
    period_group = next(
        (
            group
            for group in catalog.get("period_groups") or catalog.get("periodGroups") or []
            if isinstance(group, Mapping)
            and _clean(group.get("period_group_id") or group.get("periodGroupId")) == period_group_id
        ),
        None,
    )
    return period_group is not None and _period_group_matches(
        period_group,
        time_axes=time_axes,
        coordinates=coordinates,
    )


def _matching_parameter_items(
    items: Iterable[Any],
    parameter_target: tuple[str, str, str],
) -> list[dict[str, Any]]:
    return [
        dict(item)
        for item in items
        if isinstance(item, Mapping)
        and _target_signature(
            parameter_name=_parameter_name(item),
            model_file=_model_target(item)[0],
            model_sheet=_model_target(item)[1],
        )
        == parameter_target
    ]


def _parameter_values(items: Iterable[Any]) -> list[dict[str, Any]]:
    return [
        dict(value)
        for item in items
        if isinstance(item, Mapping)
        for value in item.get("values") or []
        if isinstance(value, Mapping)
    ]


def _quality_scalar(value: Any) -> Any:
    if value is None or isinstance(value, bool):
        return value
    try:
        number = float(value)
    except (TypeError, ValueError):
        return json_safe(value)
    if not math.isfinite(number):
        return f"NON_FINITE:{value!s}"
    return int(number) if number.is_integer() else number


def _quality_signature(items: Sequence[Mapping[str, Any]]) -> str:
    normalized = [json_safe(dict(item)) for item in items]
    return json.dumps(
        sorted(
            normalized,
            key=lambda item: json.dumps(
                item,
                ensure_ascii=False,
                sort_keys=True,
                default=str,
            ),
        ),
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )


def _parameter_envelope_signature(items: Sequence[Mapping[str, Any]]) -> str:
    return _quality_signature(
        [{key: value for key, value in item.items() if key != "values"} for item in items],
    )


def _final_value_signatures(
    items: Sequence[Mapping[str, Any]],
    *,
    include_lut_reference: bool,
) -> str:
    signatures: list[dict[str, Any]] = []
    value_fields = {
        "basecaseValue",
        "basecase_value",
        "lutValue",
        "lut_value",
        "proposedValue",
        "proposed_value",
        "rationale",
    }
    for parameter in items:
        target = parameter.get("modelTarget") or parameter.get("model_target") or {}
        raw_axes = (
            target.get("slotAxesFieldNames") or target.get("slot_axes_field_names") or []
            if isinstance(target, Mapping)
            else []
        )
        for value in parameter.get("values") or []:
            if not isinstance(value, Mapping):
                continue
            axis_names = [str(axis) for axis in raw_axes] or sorted(
                str(key) for key in value if str(key) not in value_fields
            )
            basecase = value.get("basecaseValue", value.get("basecase_value"))
            lut = value.get("lutValue", value.get("lut_value"))
            signature = {
                "coordinates": _quality_coordinate_key(
                    {
                        axis_name: _quality_axis_value(
                            axis_name,
                            value.get(axis_name),
                        )
                        for axis_name in axis_names
                    },
                ),
                "basecase": _quality_scalar(basecase),
                "proposed": _quality_scalar(
                    value.get("proposedValue", value.get("proposed_value")),
                ),
            }
            if include_lut_reference:
                signature["lut"] = _quality_scalar(lut)
                signature["reference"] = _quality_scalar(
                    basecase if basecase is not None else lut,
                )
            signatures.append(signature)
    return _quality_signature(signatures)


def _step3_value_signatures(
    *,
    adjustments: Sequence[Mapping[str, Any]],
    references: Sequence[Mapping[str, Any]],
    include_lut_reference: bool,
) -> str:
    references_by_candidate: dict[str, list[Mapping[str, Any]]] = {}
    for reference in references:
        references_by_candidate.setdefault(
            _clean(reference.get("candidate_key") or reference.get("candidateKey")),
            [],
        ).append(reference)
    signatures: list[dict[str, Any]] = []
    for adjustment in adjustments:
        candidate_key = _clean(
            adjustment.get("candidate_key") or adjustment.get("candidateKey"),
        )
        for cell in adjustment.get("value_grid") or adjustment.get("valueGrid") or []:
            if not isinstance(cell, Mapping):
                continue
            proposed = cell.get("proposed_value", cell.get("proposedValue"))
            if proposed is None:
                continue
            coordinates = _quality_coordinates(cell)
            coordinate_key = _quality_coordinate_key(coordinates)
            reference = next(
                (
                    item
                    for item in references_by_candidate.get(candidate_key, [])
                    if _coordinates_contain(
                        coordinates,
                        _quality_coordinates(item),
                    )
                ),
                {},
            )
            basecase = cell.get("basecase_value", cell.get("basecaseValue"))
            lut = cell.get("lut_value", cell.get("lutValue"))
            signature = {
                "coordinates": coordinate_key,
                "basecase": _quality_scalar(basecase),
                "proposed": _quality_scalar(proposed),
            }
            if include_lut_reference:
                signature["lut"] = _quality_scalar(lut)
                signature["reference"] = _quality_scalar(
                    reference.get(
                        "llm_reference_value",
                        reference.get("llmReferenceValue"),
                    ),
                )
            signatures.append(signature)
    return _quality_signature(signatures)


def _reference_contract_issues(reference: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    source = _clean(reference.get("effective_source") or reference.get("effectiveSource"))
    llm_value = (
        reference.get("llm_reference_value")
        if "llm_reference_value" in reference
        else reference.get("llmReferenceValue")
    )
    basecase_value = (
        reference.get("actual_basecase_value")
        if "actual_basecase_value" in reference
        else reference.get("actualBasecaseValue")
    )
    lut_value = (
        reference.get("lut_default_value") if "lut_default_value" in reference else reference.get("lutDefaultValue")
    )
    if source == "basecase":
        if basecase_value is None or not _quality_values_equal(llm_value, basecase_value):
            issues.append("Basecase 우선 reference 값 불일치")
        if not _clean(
            reference.get("basecase_reference_id") or reference.get("basecaseReferenceId"),
        ):
            issues.append("Basecase reference ID 누락")
    elif source == "lut":
        if basecase_value is not None:
            issues.append("Basecase 값이 있는데 LUT fallback을 선택함")
        if lut_value is None or not _quality_values_equal(llm_value, lut_value):
            issues.append("LUT fallback reference 값 불일치")
        if not _clean(
            reference.get("lut_reference_id") or reference.get("lutReferenceId"),
        ):
            issues.append("LUT reference ID 누락")
    else:
        issues.append(f"effective reference source가 단일 basecase/lut가 아님: {source or '<empty>'}")
    return issues


def _candidate_quality_row(
    *,
    target: ScenarioEvidence,
    parameter_target: tuple[str, str, str],
    candidates: Sequence[Mapping[str, Any]],
    execution: Mapping[str, Any],
) -> ParameterQualityRow:
    candidate_keys = tuple(
        sorted(
            {
                _clean(candidate.get("candidate_key") or candidate.get("candidateKey"))
                for candidate in candidates
                if _clean(candidate.get("candidate_key") or candidate.get("candidateKey"))
            },
        ),
    )
    slots = [
        dict(slot)
        for slot in execution.get("parameter_slots") or []
        if isinstance(slot, Mapping)
        and _clean(slot.get("candidate_key") or slot.get("candidateKey")) in candidate_keys
        and slot.get("selected", True) is not False
    ]
    catalog = execution.get("slot_catalog") or []
    exact_slots = [slot for slot in slots if _slot_is_in_exact_catalog(slot, catalog)]
    references = [
        dict(reference)
        for reference in execution.get("effective_references") or []
        if isinstance(reference, Mapping)
        and _clean(reference.get("candidate_key") or reference.get("candidateKey")) in candidate_keys
    ]
    adjustments = [
        dict(adjustment)
        for adjustment in (execution.get("result") or {}).get("parameter_adjustments") or []
        if isinstance(adjustment, Mapping)
        and _clean(adjustment.get("candidate_key") or adjustment.get("candidateKey")) in candidate_keys
        and adjustment.get("selected", True) is not False
    ]
    result_cells = [
        dict(cell)
        for adjustment in adjustments
        for cell in adjustment.get("value_grid") or adjustment.get("valueGrid") or []
        if isinstance(cell, Mapping) and cell.get("proposed_value", cell.get("proposedValue")) is not None
    ]
    api_parameters = _matching_parameter_items(
        _final_proposal_parameters(execution),
        parameter_target,
    )
    db_parameters = _matching_parameter_items(
        (execution.get("proposal_db_row") or {}).get("proposal_parameters") or [],
        parameter_target,
    )
    confirmed_parameters = _matching_parameter_items(
        (execution.get("proposal_db_row") or {}).get("confirmation_parameters") or [],
        parameter_target,
    )
    api_values = _parameter_values(api_parameters)
    db_values = _parameter_values(db_parameters)
    confirmed_values = _parameter_values(confirmed_parameters)
    failures: list[str] = []
    reviews: list[str] = []

    if not slots:
        failures.append("Step2 selected slot 없음")
    if len(exact_slots) != len(slots):
        failures.append(
            f"Step2 exact slot 불일치={len(slots) - len(exact_slots)}",
        )
    slot_keys = {
        (
            _clean(slot.get("candidate_key") or slot.get("candidateKey")),
            _clean(slot.get("slot_key") or slot.get("slotKey")),
            _quality_coordinate_key(_quality_coordinates(slot)),
        )
        for slot in slots
    }
    reference_keys = {
        (
            _clean(reference.get("candidate_key") or reference.get("candidateKey")),
            _clean(reference.get("slot_key") or reference.get("slotKey")),
            _quality_coordinate_key(_quality_coordinates(reference)),
        )
        for reference in references
    }
    if reference_keys != slot_keys:
        failures.append(
            "Step2 slot과 effective reference의 candidate/slot/coordinates가 일치하지 않음",
        )
    if len(slot_keys) != len(slots):
        failures.append("Step2 selected slot candidate/slot/coordinates 중복")
    if len(reference_keys) != len(references):
        failures.append("effective reference candidate/slot/coordinates 중복")
    for reference in references:
        failures.extend(_reference_contract_issues(reference))

    unmatched_result_coordinates = [
        _quality_coordinates(cell)
        for cell in result_cells
        if not any(
            _coordinates_contain(
                _quality_coordinates(cell),
                _quality_coordinates(slot),
            )
            for slot in slots
        )
    ]
    unmatched_slot_coordinates = [
        _quality_coordinates(slot)
        for slot in slots
        if not any(
            _coordinates_contain(
                _quality_coordinates(cell),
                _quality_coordinates(slot),
            )
            for cell in result_cells
        )
    ]
    if unmatched_result_coordinates or unmatched_slot_coordinates:
        failures.append("Step3 result coordinates가 input slot과 일치하지 않음")
    for cell in result_cells:
        cell_coordinates = _quality_coordinates(cell)
        matching_references = [
            reference
            for reference in references
            if _coordinates_contain(
                cell_coordinates,
                _quality_coordinates(reference),
            )
        ]
        if len(matching_references) != 1:
            failures.append(
                "Step3 result cell과 effective reference를 단일 매칭하지 못함",
            )
            continue
        if cell_coordinates != _quality_reference_coordinates(
            matching_references[0],
        ):
            failures.append(
                "Step3 coordinates가 reference axes+metadata와 일치하지 않음",
            )
    counts = (
        len(slots),
        len(references),
        len(result_cells),
        len(api_values),
        len(db_values),
        len(confirmed_values),
    )
    if not counts[0] or len(set(counts)) != 1:
        failures.append(
            "Step3 input/reference/result/final DB value 수 불일치: "
            f"slot={counts[0]}, reference={counts[1]}, result={counts[2]}, "
            f"api={counts[3]}, db={counts[4]}, confirmed={counts[5]}",
        )
    result_axis_sets = {frozenset(_quality_coordinates(cell)) for cell in result_cells}
    for parameter in api_parameters:
        model_target = parameter.get("modelTarget") or parameter.get(
            "model_target",
        )
        api_axis_names = (
            model_target.get("slotAxesFieldNames") or model_target.get("slot_axes_field_names") or []
            if isinstance(model_target, Mapping)
            else []
        )
        if result_axis_sets and (
            len(result_axis_sets) != 1
            or frozenset(str(item) for item in api_axis_names) != next(iter(result_axis_sets))
        ):
            failures.append(
                "API slotAxesFieldNames가 Step3 axes+metadata와 일치하지 않음",
            )
    step3_api_signature = _step3_value_signatures(
        adjustments=adjustments,
        references=references,
        include_lut_reference=True,
    )
    step3_persistent_signature = _step3_value_signatures(
        adjustments=adjustments,
        references=references,
        include_lut_reference=False,
    )
    api_signature = _final_value_signatures(
        api_parameters,
        include_lut_reference=True,
    )
    api_persistent_signature = _final_value_signatures(
        api_parameters,
        include_lut_reference=False,
    )
    db_signature = _final_value_signatures(
        db_parameters,
        include_lut_reference=False,
    )
    confirmation_signature = _final_value_signatures(
        confirmed_parameters,
        include_lut_reference=False,
    )
    if step3_api_signature != api_signature:
        failures.append(
            "Step3 coordinates/proposed/basecase/reference signature와 API 값이 다름",
        )
    if step3_persistent_signature != api_persistent_signature:
        failures.append(
            "Step3 persistent value signature와 API 값이 다름",
        )
    if step3_persistent_signature != db_signature:
        failures.append(
            "Step3 persistent value signature와 DB proposal read-back이 다름",
        )
    if step3_persistent_signature != confirmation_signature:
        failures.append(
            "Step3 persistent value signature와 confirmation read-back이 다름",
        )
    if api_parameters and db_parameters and api_persistent_signature != db_signature:
        failures.append("API proposal values와 DB proposal read-back이 다름")
    if db_parameters and confirmed_parameters and db_signature != confirmation_signature:
        failures.append("DB proposal values와 confirmation read-back이 다름")
    if (
        api_parameters
        and db_parameters
        and _parameter_envelope_signature(api_parameters) != _parameter_envelope_signature(db_parameters)
    ):
        failures.append("API와 DB proposal parameter envelope가 다름")
    if (
        db_parameters
        and confirmed_parameters
        and _parameter_envelope_signature(db_parameters) != _parameter_envelope_signature(confirmed_parameters)
    ):
        failures.append("DB proposal과 confirmation parameter envelope가 다름")

    summary = execution.get("step_summary") or {}
    all_slots = [
        slot
        for slot in execution.get("parameter_slots") or []
        if isinstance(slot, Mapping) and slot.get("selected", True) is not False
    ]
    all_cells = [
        cell
        for adjustment in (execution.get("result") or {}).get("parameter_adjustments") or []
        if isinstance(adjustment, Mapping) and adjustment.get("selected", True) is not False
        for cell in adjustment.get("value_grid") or adjustment.get("valueGrid") or []
        if isinstance(cell, Mapping)
    ]
    summary_contract = {
        "selected_slot_count": len(all_slots),
        "value_reference_record_count": len(execution.get("effective_references") or []),
        "value_cell_count": len(all_cells),
        "proposal_parameter_count": len(_final_proposal_parameters(execution)),
    }
    for field_name, actual_count in summary_contract.items():
        if _int_or_none(summary.get(field_name)) != actual_count:
            failures.append(
                f"step_summary.{field_name}={summary.get(field_name)!r}, actual={actual_count}",
            )

    if any(
        not _clean(
            adjustment.get("parameter_selection_rationale_ko") or adjustment.get("parameterSelectionRationaleKo"),
        )
        for adjustment in adjustments
    ):
        failures.append("merged parameter selection rationale 비어 있음")
    if any(not _clean(cell.get("rationale_ko") or cell.get("rationale")) for cell in result_cells):
        failures.append("Step3 value rationale 비어 있음")
    if len(api_parameters) != 1 or any(not _clean(parameter.get("rationale")) for parameter in api_parameters):
        failures.append("final merged parameter rationale 비어 있거나 parameter가 중복됨")
    if any(not _clean(value.get("rationale")) for value in api_values):
        failures.append("final proposal value rationale 비어 있음")

    source_keys = (
        set().union(
            *(_actual_occurrence_keys([candidate]) for candidate in candidates),
        )
        if candidates
        else set()
    )
    source_count = len(source_keys)
    rationale_texts = [
        *(
            _clean(
                adjustment.get("parameter_selection_rationale_ko") or adjustment.get("parameterSelectionRationaleKo"),
            )
            for adjustment in adjustments
        ),
        *(_clean(cell.get("rationale_ko") or cell.get("rationale")) for cell in result_cells),
        *(_clean(parameter.get("rationale")) for parameter in api_parameters),
        *(_clean(value.get("rationale")) for value in api_values),
    ]
    explicit_conflict_markers = (
        "방향 역전",
        "근거 불일치",
        "source event와 모순",
        "이벤트와 모순",
        "dimension과 모순",
        "contradict",
        "opposite direction",
    )
    if any(marker in rationale.lower() for rationale in rationale_texts for marker in explicit_conflict_markers):
        failures.append("rationale에 명시적인 방향 역전 또는 source 근거 모순이 있음")

    manual_review = "rationale의 event/dimension 방향·강도·기간·대상 정합성 수동 검토 필요"
    reviews.append("rationale 의미 품질을 기계적으로 확정할 수 없음")
    if source_count > 1:
        manual_review = "다중 source의 방향·강도·기간·대상 충돌을 하나의 최종값으로 종합했는지 rationale 수동 검토 필요"
        reviews.append("다중 source 충돌 종합 근거를 기계적으로 확정할 수 없음")

    if failures:
        verdict: Verdict = "FAIL"
        evidence = "; ".join(dict.fromkeys(failures))
    elif reviews:
        verdict = "REVIEW"
        evidence = "; ".join(dict.fromkeys(reviews))
    else:
        verdict = "PASS"
        evidence = "exact slot/reference/value/rationale 구조 계약 일치"
    return ParameterQualityRow(
        scenario_id=target.scenario_id,
        parameter_name=parameter_target[0],
        candidate_keys=candidate_keys,
        selected_slot_count=len(slots),
        exact_slot_count=len(exact_slots),
        reference_count=len(references),
        step3_value_count=len(result_cells),
        api_value_count=len(api_values),
        db_value_count=len(db_values),
        confirmed_value_count=len(confirmed_values),
        reference_sources=tuple(
            sorted(
                {
                    _clean(reference.get("effective_source") or reference.get("effectiveSource"))
                    for reference in references
                },
            ),
        ),
        source_count=source_count,
        verdict=verdict,
        evidence=evidence,
        manual_review=manual_review,
    )


def build_parameter_quality_rows(
    *,
    targets: Sequence[ScenarioEvidence],
    executions: Mapping[int, Mapping[str, Any]],
    execute: bool,
) -> list[ParameterQualityRow]:
    if not execute:
        return []
    rows: list[ParameterQualityRow] = []
    for target in targets:
        execution = executions.get(target.scenario_id) or {}
        if execution.get("error"):
            continue
        candidates = [item for item in execution.get("expected_candidates") or [] if isinstance(item, Mapping)]
        candidates_by_target: dict[tuple[str, str, str], list[Mapping[str, Any]]] = defaultdict(list)
        for candidate in candidates:
            parameter_target = _target_signature(
                parameter_name=_parameter_name(candidate),
                model_file=_model_target(candidate)[0],
                model_sheet=_model_target(candidate)[1],
            )
            candidates_by_target[parameter_target].append(candidate)
        rows.extend(
            _candidate_quality_row(
                target=target,
                parameter_target=parameter_target,
                candidates=parameter_candidates,
                execution=execution,
            )
            for parameter_target, parameter_candidates in sorted(
                candidates_by_target.items(),
            )
        )
    return rows


def build_coverage_matrix(
    *,
    active_parameter_definitions: Sequence[Mapping[str, Any]],
    targets: Sequence[ScenarioEvidence],
    executions: Mapping[int, Mapping[str, Any]],
    execute: bool,
    routing_limit: int | None = None,
    discovered_targets: Sequence[ScenarioEvidence] | None = None,
) -> tuple[list[CoverageRow], list[str]]:
    rows: list[CoverageRow] = []
    integrity_issues: list[str] = []
    quality_rows = build_parameter_quality_rows(
        targets=targets,
        executions=executions,
        execute=execute,
    )
    quality_by_scenario_parameter = {(row.scenario_id, row.parameter_name): row for row in quality_rows}
    discovery_scope = targets if discovered_targets is None else discovered_targets
    valid_discovered_targets = [target for target in discovery_scope if not target.errors]
    selected_scenario_ids = {target.scenario_id for target in targets}
    effective_routing_limit = routing_limit or _routing_limit_from_settings()
    routing_limit_failures: dict[tuple[int, tuple[str, str, str]], str] = {}
    for target in targets:
        execution = executions.get(target.scenario_id) or {}
        if not execute or execution.get("error"):
            continue
        expected_all = _expected_occurrence_keys(target.occurrences)
        actual_all = _actual_occurrence_keys(
            execution.get("rule_candidates") or [],
        )
        extra_occurrences = actual_all - expected_all
        if extra_occurrences:
            integrity_issues.append(
                f"scenario {target.scenario_id}: mapping 밖 candidate occurrence={len(extra_occurrences)}",
            )
        selected_all = _actual_occurrence_keys(
            execution.get("expected_candidates") or [],
        )
        selected_extra_occurrences = selected_all - expected_all
        if selected_extra_occurrences:
            integrity_issues.append(
                f"scenario {target.scenario_id}: mapping 밖 selected occurrence={len(selected_extra_occurrences)}",
            )
        expected_parameter_targets = _parameter_targets(target.occurrences)
        proposal_extra_targets = _parameter_targets(_final_proposal_parameters(execution)) - expected_parameter_targets
        if proposal_extra_targets:
            integrity_issues.append(
                f"scenario {target.scenario_id}: mapping 밖 proposal target={sorted(proposal_extra_targets)}",
            )
        confirmation_extra_targets = _parameter_targets(_confirmed_parameters(execution)) - expected_parameter_targets
        if confirmation_extra_targets:
            integrity_issues.append(
                f"scenario {target.scenario_id}: mapping 밖 confirmation target={sorted(confirmation_extra_targets)}",
            )
        for dimension_key, selected_targets in _selected_routing_targets_by_dimension(
            execution.get("expected_candidates") or [],
        ).items():
            if len(selected_targets) <= effective_routing_limit:
                continue
            message = (
                f"scenario {target.scenario_id} composite dimension={dimension_key} "
                f"routing selected target={len(selected_targets)}가 configured max="
                f"{effective_routing_limit}를 초과함"
            )
            integrity_issues.append(message)
            for selected_target in selected_targets:
                routing_limit_failures[(target.scenario_id, selected_target)] = message
    definitions = sorted(
        active_parameter_definitions,
        key=lambda item: _definition_target(item),
    )
    for definition in definitions:
        parameter_target = _definition_target(definition)
        parameter_name = parameter_target[0]
        discovered_eligible_targets = [
            target
            for target in valid_discovered_targets
            if any(
                _target_signature(
                    parameter_name=occurrence.get("parameter_name"),
                    model_file=occurrence.get("model_file"),
                    model_sheet=occurrence.get("model_sheet"),
                )
                == parameter_target
                for occurrence in target.occurrences
            )
        ]
        eligible_targets = [
            target
            for target in targets
            if not target.errors
            if any(
                _target_signature(
                    parameter_name=occurrence.get("parameter_name"),
                    model_file=occurrence.get("model_file"),
                    model_sheet=occurrence.get("model_sheet"),
                )
                == parameter_target
                for occurrence in target.occurrences
            )
        ]
        discovered_expected_occurrences = [
            occurrence
            for target in discovered_eligible_targets
            for occurrence in target.occurrences
            if _target_signature(
                parameter_name=occurrence.get("parameter_name"),
                model_file=occurrence.get("model_file"),
                model_sheet=occurrence.get("model_sheet"),
            )
            == parameter_target
        ]
        selected_expected_occurrences = [
            occurrence
            for target in eligible_targets
            for occurrence in target.occurrences
            if _target_signature(
                parameter_name=occurrence.get("parameter_name"),
                model_file=occurrence.get("model_file"),
                model_sheet=occurrence.get("model_sheet"),
            )
            == parameter_target
        ]
        discovered_expected_keys = _expected_occurrence_keys(
            discovered_expected_occurrences,
        )
        selected_expected_keys = _expected_occurrence_keys(
            selected_expected_occurrences,
        )
        eligible_count = len(discovered_expected_keys)
        skipped_unique_count = len(
            discovered_expected_keys - selected_expected_keys,
        )
        skipped_coverage_notes: list[str] = []
        for target in discovered_eligible_targets:
            if target.scenario_id in selected_scenario_ids:
                continue
            target_keys = _expected_occurrence_keys(
                occurrence
                for occurrence in target.occurrences
                if _target_signature(
                    parameter_name=occurrence.get("parameter_name"),
                    model_file=occurrence.get("model_file"),
                    model_sheet=occurrence.get("model_sheet"),
                )
                == parameter_target
            )
            target_unique_count = len(target_keys - selected_expected_keys)
            if not target_unique_count:
                continue
            skipped_coverage_notes.append(
                f"scenario {target.scenario_id}: "
                f"{target.selection_skip_reason or 'selection scope에서 미선택'}; "
                f"parameter unique eligible occurrence={target_unique_count}",
            )
        skipped_coverage_evidence = (
            f"discovered eligible={eligible_count}, "
            f"selected eligible={len(selected_expected_keys)}, "
            f"skipped unique={skipped_unique_count}; " + "; ".join(skipped_coverage_notes)
        )
        if eligible_count == 0:
            unexpected_candidate_count = sum(
                len(
                    _actual_occurrence_keys(
                        _matching_parameter_items(
                            (executions.get(target.scenario_id) or {}).get(
                                "rule_candidates",
                            )
                            or [],
                            parameter_target,
                        ),
                    ),
                )
                for target in targets
            )
            unexpected_selected_count = sum(
                len(
                    _actual_occurrence_keys(
                        _matching_parameter_items(
                            (executions.get(target.scenario_id) or {}).get(
                                "expected_candidates",
                            )
                            or [],
                            parameter_target,
                        ),
                    ),
                )
                for target in targets
            )
            unexpected_proposed_count = sum(
                len(
                    _matching_parameter_items(
                        _final_proposal_parameters(
                            executions.get(target.scenario_id) or {},
                        ),
                        parameter_target,
                    ),
                )
                for target in targets
            )
            unexpected_confirmed_count = sum(
                len(
                    _matching_parameter_items(
                        _confirmed_parameters(
                            executions.get(target.scenario_id) or {},
                        ),
                        parameter_target,
                    ),
                )
                for target in targets
            )
            if execute and any(
                (
                    unexpected_candidate_count,
                    unexpected_selected_count,
                    unexpected_proposed_count,
                    unexpected_confirmed_count,
                ),
            ):
                message = (
                    "eligible sourceRef 없이 mapping 밖 chain이 생성됨: "
                    f"candidate={unexpected_candidate_count}, "
                    f"selected={unexpected_selected_count}, "
                    f"proposed={unexpected_proposed_count}, "
                    f"confirmed={unexpected_confirmed_count}"
                )
                rows.append(
                    CoverageRow(
                        parameter_name=parameter_name,
                        eligible=0,
                        candidate=unexpected_candidate_count,
                        selected=unexpected_selected_count,
                        proposed=unexpected_proposed_count,
                        confirmed=unexpected_confirmed_count,
                        verdict="FAIL",
                        evidence=message,
                    ),
                )
                integrity_issues.append(f"{parameter_name}: {message}")
                continue
            rows.append(
                CoverageRow(
                    parameter_name=parameter_name,
                    eligible=0,
                    candidate=None,
                    selected=None,
                    proposed=None,
                    confirmed=None,
                    verdict="COVERAGE LIMIT",
                    evidence="실행 범위에 적합한 sourceRef가 없음",
                ),
            )
            continue
        if not execute:
            evidence = "read-only discovery; --execute 미지정"
            if skipped_unique_count:
                evidence = f"{evidence}; {skipped_coverage_evidence}"
            rows.append(
                CoverageRow(
                    parameter_name=parameter_name,
                    eligible=eligible_count,
                    candidate=None,
                    selected=None,
                    proposed=None,
                    confirmed=None,
                    verdict="COVERAGE LIMIT",
                    evidence=evidence,
                ),
            )
            continue
        if not eligible_targets:
            rows.append(
                CoverageRow(
                    parameter_name=parameter_name,
                    eligible=eligible_count,
                    candidate=None,
                    selected=None,
                    proposed=None,
                    confirmed=None,
                    verdict="COVERAGE LIMIT",
                    evidence=(
                        f"discovery selection limit으로 eligible scenario를 실행하지 못함; {skipped_coverage_evidence}"
                    ),
                ),
            )
            continue

        candidate_count = 0
        selected_count = 0
        proposed_count = 0
        confirmed_count = 0
        row_failures: list[str] = []
        row_reviews: list[str] = []
        for target in eligible_targets:
            execution = executions.get(target.scenario_id) or {}
            if execution.get("error"):
                row_failures.append(
                    f"scenario {target.scenario_id} execution error",
                )
                continue
            routing_limit_failure = routing_limit_failures.get(
                (target.scenario_id, parameter_target),
            )
            if routing_limit_failure:
                row_failures.append(routing_limit_failure)
            expected_for_scenario = [
                item
                for item in target.occurrences
                if _target_signature(
                    parameter_name=item.get("parameter_name"),
                    model_file=item.get("model_file"),
                    model_sheet=item.get("model_sheet"),
                )
                == parameter_target
            ]
            expected_keys = _expected_occurrence_keys(expected_for_scenario)
            expected_direct = {key for key in expected_keys if key[-1] == "direct"}
            expected_routing = {key for key in expected_keys if key[-1] == "routing"}
            candidate_items = _matching_parameter_items(
                execution.get("rule_candidates") or [],
                parameter_target,
            )
            selected_items = _matching_parameter_items(
                execution.get("expected_candidates") or [],
                parameter_target,
            )
            candidate_keys = {key for key in _actual_occurrence_keys(candidate_items) if key[5:8] == parameter_target}
            selected_keys = {
                key
                for key in _actual_occurrence_keys(
                    execution.get("expected_candidates") or [],
                )
                if key[5:8] == parameter_target
            }
            candidate_count += len(candidate_keys)
            selected_count += len(selected_keys)
            if candidate_keys != expected_keys:
                row_failures.append(
                    f"scenario {target.scenario_id} candidate mismatch "
                    f"(missing={len(expected_keys - candidate_keys)}, "
                    f"extra={len(candidate_keys - expected_keys)})",
                )
            expected_task_key = _stable_task_key(
                parameter_target[0],
                parameter_target[1],
                parameter_target[2],
            )
            selected_task_keys = {
                _clean(item.get("candidate_key") or item.get("candidateKey"))
                for item in selected_items
                if _clean(item.get("candidate_key") or item.get("candidateKey"))
            }
            if selected_keys and selected_task_keys != {expected_task_key}:
                row_failures.append(
                    f"scenario {target.scenario_id} selected v3 parameter task identity 불일치: "
                    f"expected={expected_task_key}, actual={sorted(selected_task_keys)}",
                )
            if selected_keys and len(selected_items) != 1:
                row_failures.append(
                    f"scenario {target.scenario_id} selected parameter task가 1개로 병합되지 않음: "
                    f"actual={len(selected_items)}",
                )
            if not expected_direct.issubset(selected_keys):
                row_failures.append(
                    f"scenario {target.scenario_id} direct selected 누락",
                )
            selected_extra = selected_keys - expected_keys
            if selected_extra:
                row_failures.append(
                    f"scenario {target.scenario_id} mapping 밖 selected={len(selected_extra)}",
                )
            selected_routing = selected_keys & expected_routing
            if expected_routing and not selected_routing:
                row_reviews.append(
                    f"scenario {target.scenario_id} routing 후보 미선택",
                )
            elif selected_routing and selected_routing != expected_routing:
                row_failures.append(
                    f"scenario {target.scenario_id} routing selected source union 누락 "
                    f"(missing={len(expected_routing - selected_routing)})",
                )

            proposed_targets = _parameter_targets(_final_proposal_parameters(execution))
            confirmed_targets = _parameter_targets(_confirmed_parameters(execution))
            if parameter_target in proposed_targets:
                proposed_count += 1
            if parameter_target in confirmed_targets:
                confirmed_count += 1
            selected_for_parameter = bool(selected_keys)
            if selected_for_parameter and parameter_target not in proposed_targets:
                row_failures.append(
                    f"scenario {target.scenario_id} selected→proposed 누락",
                )
            if parameter_target in proposed_targets and parameter_target not in confirmed_targets:
                row_failures.append(
                    f"scenario {target.scenario_id} proposed→confirmed 누락",
                )

            proposal_row = execution.get("proposal_db_row") or {}
            response_data = (execution.get("final_response") or {}).get("data") or {}
            if "eventId" not in response_data or response_data.get("eventId") is not None:
                row_failures.append(
                    f"scenario {target.scenario_id} API eventId가 명시적 null이 아님",
                )
            if _int_or_none(response_data.get("scenarioGroupId")) != target.scenario_group_id:
                row_failures.append(
                    f"scenario {target.scenario_id} API scenarioGroupId 불일치",
                )
            if proposal_row.get("mi_event_id", object()) is not None:
                row_failures.append(
                    f"scenario {target.scenario_id} proposal.mi_event_id가 NULL이 아님",
                )
            if _int_or_none(proposal_row.get("scenario_group_id")) != target.scenario_group_id:
                row_failures.append(
                    f"scenario {target.scenario_id} proposal group link 불일치",
                )
            if (execution.get("confirmation") or {}).get("status") != "PASS":
                row_failures.append(
                    f"scenario {target.scenario_id} confirmation contract 실패",
                )
            if selected_for_parameter:
                quality = quality_by_scenario_parameter.get(
                    (target.scenario_id, parameter_name),
                )
                if quality is None:
                    row_failures.append(
                        f"scenario {target.scenario_id} slot/reference/value 증적 누락",
                    )
                elif quality.verdict == "FAIL":
                    row_failures.append(
                        f"scenario {target.scenario_id} value contract FAIL: {quality.evidence}",
                    )
                elif quality.verdict == "REVIEW":
                    row_reviews.append(
                        f"scenario {target.scenario_id} value contract REVIEW: {quality.evidence}",
                    )

        if row_failures:
            verdict: Verdict = "FAIL"
            evidence = "; ".join(dict.fromkeys(row_failures))
            integrity_issues.extend(f"{parameter_name}: {item}" for item in row_failures)
        elif row_reviews:
            verdict = "REVIEW"
            evidence = "; ".join(dict.fromkeys(row_reviews))
        else:
            verdict = "PASS"
            evidence = "eligible chain과 nullable persistence가 일치함"
        if skipped_unique_count:
            evidence = f"{evidence}; {skipped_coverage_evidence}"
            if verdict == "PASS":
                verdict = "COVERAGE LIMIT"
        rows.append(
            CoverageRow(
                parameter_name=parameter_name,
                eligible=eligible_count,
                candidate=candidate_count,
                selected=selected_count,
                proposed=proposed_count,
                confirmed=confirmed_count,
                verdict=verdict,
                evidence=evidence,
            ),
        )
    return rows, integrity_issues


def _overall_verdict(
    *,
    preflight: SchemaPreflight,
    targets: Sequence[ScenarioEvidence],
    coverage_rows: Sequence[CoverageRow],
    execution_errors: Sequence[str],
    additional_verdicts: Sequence[Verdict] = (),
) -> Verdict:
    if preflight.verdict == "FAIL" or execution_errors or any(target.errors for target in targets):
        return "FAIL"
    verdicts = [row.verdict for row in coverage_rows] + list(additional_verdicts)
    if not verdicts:
        return "COVERAGE LIMIT"
    return max(verdicts, key=lambda item: _VERDICT_PRIORITY[item])


def _md(value: Any) -> str:
    text = _redact_report_text(value if value is not None else "-")
    return text.replace("|", "\\|").replace("\n", " ")


def _count_text(value: int | None) -> str:
    return "NOT RUN" if value is None else str(value)


def _unit_contract_status(verdict: Verdict) -> str:
    return f"UNIT {verdict}"


def _llm_metrics(execution: Mapping[str, Any]) -> dict[str, Any]:
    calls = [item for item in execution.get("llm_calls") or [] if isinstance(item, Mapping)]
    total_tokens = 0
    usage_complete = bool(calls)
    prompt_bytes = 0
    prompt_bytes_captured = False
    prompt_guard_exceeded = False
    internal_retry_captured = bool(calls)
    call_elapsed_captured = bool(calls)
    for call in calls:
        usage = call.get("usage") or {}
        raw_total = usage.get("total_tokens") if isinstance(usage, Mapping) else None
        if raw_total is None:
            usage_complete = False
        else:
            total_tokens += int(raw_total)
        raw_prompt_bytes = call.get("prompt_bytes")
        if raw_prompt_bytes is not None:
            prompt_bytes += int(raw_prompt_bytes)
            prompt_bytes_captured = True
            raw_limit = call.get("prompt_limit_bytes")
            if raw_limit is not None and int(raw_prompt_bytes) > int(raw_limit):
                prompt_guard_exceeded = True
        if not any(
            field_name in call
            for field_name in (
                "internal_retry_count",
                "retry_count",
                "retries",
            )
        ):
            internal_retry_captured = False
        if call.get("elapsed_seconds") is None:
            call_elapsed_captured = False
    return {
        "call_count": len(calls),
        "total_tokens": total_tokens if usage_complete else None,
        "prompt_bytes": prompt_bytes if prompt_bytes_captured else None,
        "prompt_guard_exceeded": prompt_guard_exceeded,
        "internal_retry_captured": internal_retry_captured,
        "call_elapsed_captured": call_elapsed_captured,
    }


def _quality_step_name(call: Mapping[str, Any]) -> str | None:
    step = _clean(call.get("step")).lower()
    if "step1.5" in step:
        return "Step1.5"
    if "step2" in step:
        return "Step2"
    if "step3" in step:
        return "Step3"
    return None


def capture_execute_prompt_packets(
    execution: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    """Rebuild the exact prompt packets from the completed graph state.

    The capture runs only after a real graph execution and calls the same packet
    builders used immediately before each connector invocation. Keeping the
    packets in the manual execution record lets the quality evaluator compare
    actual stage input with its independently discovered DB lineage.
    """
    from apps.agents.model_parameter_agent.flows.propose_parameters.nodes import (
        _build_candidate_validation_prompt_packet,
        _build_slot_proposal_prompt_packet,
        _build_value_proposal_prompt_packet,
        _merge_v3_routing_candidates_for_validation,
        _partition_candidate_validation_work,
    )

    context = execution.get("context")
    if not isinstance(context, Mapping):
        msg = "completed execution has no scenario context for prompt capture"
        raise TypeError(msg)
    scenario_context = dict(context)
    rule_candidates = [dict(item) for item in execution.get("rule_candidates") or [] if isinstance(item, Mapping)]
    selected_candidates = [
        dict(item) for item in execution.get("expected_candidates") or [] if isinstance(item, Mapping)
    ]
    result = execution.get("result") or {}
    raw_non_inputs = (
        result.get("non_input_items")
        if isinstance(result, Mapping) and result.get("non_input_items") is not None
        else execution.get("non_input_items")
    )
    non_input_items = [dict(item) for item in raw_non_inputs or [] if isinstance(item, Mapping)]
    packets: dict[str, dict[str, Any]] = {}

    validation_candidates = _merge_v3_routing_candidates_for_validation(
        rule_candidates,
    )
    _, routing_tasks = _partition_candidate_validation_work(
        validation_candidates,
    )
    if routing_tasks:
        packets["Step1.5"] = json_safe(
            _build_candidate_validation_prompt_packet(
                scenario_context,
                routing_tasks,
                non_input_items,
            ),
        )

    if selected_candidates:
        packets["Step2"] = json_safe(
            _build_slot_proposal_prompt_packet(
                scenario_context,
                selected_candidates,
                [dict(item) for item in execution.get("slot_catalog") or [] if isinstance(item, Mapping)],
                non_input_items,
            ),
        )

    selected_candidate_keys = {
        _clean(slot.get("candidate_key") or slot.get("candidateKey"))
        for slot in execution.get("parameter_slots") or []
        if isinstance(slot, Mapping) and slot.get("selected", True) is not False
    }
    value_candidates = [
        dict(item) for item in execution.get("slot_candidate_mappings") or [] if isinstance(item, Mapping)
    ] or [
        candidate
        for candidate in selected_candidates
        if _clean(candidate.get("candidate_key") or candidate.get("candidateKey")) in selected_candidate_keys
    ]
    if value_candidates and selected_candidate_keys:
        packets["Step3"] = json_safe(
            _build_value_proposal_prompt_packet(
                scenario_context,
                value_candidates,
                [dict(item) for item in execution.get("parameter_slots") or [] if isinstance(item, Mapping)],
                [dict(item) for item in execution.get("effective_references") or [] if isinstance(item, Mapping)],
                non_input_items,
            ),
        )
    return packets


def _prompt_dimension_key(item: Mapping[str, Any]) -> str:
    return _clean(
        item.get("scenario_dimension_key") or item.get("dimension_key") or item.get("source_dimension_id"),
    )


def _prompt_source_dimensions(item: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    raw = item.get("source_dimensions")
    if isinstance(raw, list) and raw:
        return [value for value in raw if isinstance(value, Mapping)]
    return [item]


def _prompt_lineage_expectations(
    items: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, set[Any]]]:
    expected: dict[str, dict[str, set[Any]]] = {}
    for item in items:
        for source in _prompt_source_dimensions(item):
            dimension_key = _prompt_dimension_key(source)
            if not dimension_key:
                continue
            lineage = expected.setdefault(
                dimension_key,
                {"events": set(), "refs": set(), "projections": set()},
            )
            lineage["events"].update(
                event_id
                for raw_event_id in source.get("source_event_ids") or []
                if (event_id := _int_or_none(raw_event_id)) is not None
            )
            lineage["refs"].update(
                (
                    template_id,
                    dim_key,
                )
                for raw_ref in source.get("source_refs") or []
                if isinstance(raw_ref, Mapping)
                and (
                    template_id := _int_or_none(
                        raw_ref.get("scenario_dimension_template_id") or raw_ref.get("scenarioDimensionTemplateId"),
                    )
                )
                is not None
                and (
                    dim_key := _clean(
                        raw_ref.get("dim_key") or raw_ref.get("dimKey"),
                    )
                )
            )
            lineage["projections"].update(
                json.dumps(
                    json_safe(dict(projection)),
                    ensure_ascii=False,
                    sort_keys=True,
                    default=str,
                )
                for projection in source.get("approved_source_projections") or []
                if isinstance(projection, Mapping)
            )
    return expected


def _merge_prompt_expectations(
    *expectations: Mapping[str, Mapping[str, set[Any]]],
) -> dict[str, dict[str, set[Any]]]:
    merged: dict[str, dict[str, set[Any]]] = {}
    for expectation in expectations:
        for dimension_key, lineage in expectation.items():
            target = merged.setdefault(
                dimension_key,
                {"events": set(), "refs": set(), "projections": set()},
            )
            for field_name in ("events", "refs", "projections"):
                target[field_name].update(lineage.get(field_name) or set())
    return merged


def _discovered_prompt_expectations(
    target: ScenarioEvidence,
    *,
    dimension_keys: set[str],
    fallback: Mapping[str, Mapping[str, set[Any]]],
) -> dict[str, dict[str, set[Any]]]:
    expected: dict[str, dict[str, set[Any]]] = {}
    for dimension_key in dimension_keys:
        fallback_lineage = fallback.get(dimension_key) or {}
        discovered_events = target.dimension_source_event_ids.get(
            dimension_key,
        )
        discovered_refs = target.dimension_source_refs.get(dimension_key)
        discovered_projections = target.approved_source_projections.get(
            dimension_key,
        )
        expected[dimension_key] = {
            "events": set(
                discovered_events if discovered_events is not None else fallback_lineage.get("events") or set(),
            ),
            "refs": {
                (
                    _int_or_none(
                        raw_ref.get("scenario_dimension_template_id") or raw_ref.get("scenarioDimensionTemplateId"),
                    ),
                    _clean(raw_ref.get("dim_key") or raw_ref.get("dimKey")),
                )
                for raw_ref in (discovered_refs if discovered_refs is not None else ())
                if isinstance(raw_ref, Mapping)
            }
            if discovered_refs is not None
            else set(fallback_lineage.get("refs") or set()),
            "projections": {
                json.dumps(
                    json_safe(dict(projection)),
                    ensure_ascii=False,
                    sort_keys=True,
                    default=str,
                )
                for projection in (discovered_projections if discovered_projections is not None else ())
                if isinstance(projection, Mapping)
            }
            if discovered_projections is not None
            else set(fallback_lineage.get("projections") or set()),
        }
    return expected


def _validate_prompt_events(
    target: ScenarioEvidence,
    scenario_brief: Mapping[str, Any],
) -> tuple[list[str], list[str], tuple[int, ...]]:
    failures: list[str] = []
    reviews: list[str] = []
    raw_events = scenario_brief.get("events")
    if not isinstance(raw_events, list):
        return ["scenario_brief.events 배열 누락"], reviews, ()
    events = [event for event in raw_events if isinstance(event, Mapping)]
    actual_event_ids = tuple(
        event_id
        for event in events
        if (event_id := _int_or_none(event.get("event_id") or event.get("mi_event_id"))) is not None
    )
    if actual_event_ids != target.group_event_ids:
        failures.append(
            f"group display order event ID 불일치: expected={target.group_event_ids}, actual={actual_event_ids}",
        )
    if len(events) != len(target.group_event_ids):
        failures.append(
            f"connected event 수 불일치: expected={len(target.group_event_ids)}, actual={len(events)}",
        )
    expected_by_id = {
        int(event["mi_event_id"]): event
        for event in target.ordered_events
        if _int_or_none(event.get("mi_event_id")) is not None
    }
    if not expected_by_id:
        reviews.append("DB event 본문 discovery 증적이 없어 packet 내용 exact 비교 불가")
    for event in events:
        event_id = _int_or_none(event.get("event_id") or event.get("mi_event_id"))
        if event_id is None:
            failures.append("prompt event ID 누락")
            continue
        if event_id not in target.group_event_ids:
            failures.append(f"group 밖 prompt event ID={event_id}")
        expected = expected_by_id.get(event_id)
        actual_event_type = _int_or_none(
            event.get("event_type_l2_id") or event.get("eventTypeL2Id"),
        )
        if expected is not None and actual_event_type != int(expected["event_type_l2_id"]):
            failures.append(f"event {event_id} event type 불일치")
        title = _clean(event.get("title"))
        if not title:
            failures.append(f"event {event_id} title 누락")
        elif expected is not None and title != _clean(expected.get("title")):
            failures.append(f"event {event_id} title 불일치")
        summary = _clean(event.get("one_line_summary") or event.get("oneLineSummary"))
        if expected is not None and summary != _clean(expected.get("one_line_summary")):
            failures.append(f"event {event_id} one-line summary 불일치")
        bullets = event.get("key_bullets") or event.get("keyBullets") or []
        tags = event.get("tags") or []
        detail = _clean(event.get("detail_excerpt") or event.get("detailExcerpt"))
        if not isinstance(bullets, list) or len(bullets) > 5:
            failures.append(f"event {event_id} key bullet 5개 제한 위반")
        if not isinstance(tags, list) or len(tags) > 8:
            failures.append(f"event {event_id} tag 8개 제한 위반")
        if len(detail) > 1200:
            failures.append(f"event {event_id} detail excerpt 1,200자 제한 위반")
        if expected is not None:
            if list(bullets) != list(expected.get("key_bullets") or []):
                failures.append(f"event {event_id} key bullet 불일치")
            if list(tags) != list(expected.get("tags") or []):
                failures.append(f"event {event_id} tag 불일치")
            if detail != _clean(expected.get("detail_excerpt")):
                failures.append(f"event {event_id} detail excerpt 불일치")
    return failures, reviews, actual_event_ids


def _validate_prompt_dimension_items(
    *,
    label: str,
    items: Sequence[Mapping[str, Any]],
    expected: Mapping[str, Mapping[str, set[Any]]],
    exact_keys: bool,
) -> list[str]:
    failures: list[str] = []
    actual = _prompt_lineage_expectations(items)
    actual_keys = set(actual)
    expected_keys = set(expected)
    missing_keys = sorted(expected_keys - actual_keys)
    extra_keys = sorted(actual_keys - expected_keys)
    if missing_keys:
        failures.append(f"{label} dimension 누락={missing_keys}")
    if exact_keys and extra_keys:
        failures.append(f"{label} 무관 dimension 포함={extra_keys}")
    for dimension_key in sorted(expected_keys & actual_keys):
        actual_lineage = actual[dimension_key]
        expected_lineage = expected[dimension_key]
        expected_events = expected_lineage.get("events") or set()
        if not actual_lineage["events"]:
            failures.append(f"{label} {dimension_key} source event lineage 누락")
        elif expected_events and actual_lineage["events"] != expected_events:
            failures.append(
                f"{label} {dimension_key} source event lineage 불일치: "
                f"expected={sorted(expected_events)}, actual={sorted(actual_lineage['events'])}",
            )
        expected_refs = expected_lineage.get("refs") or set()
        if expected_refs and actual_lineage["refs"] != expected_refs:
            failures.append(f"{label} {dimension_key} sourceRef lineage 불일치")
        expected_projections = expected_lineage.get("projections") or set()
        if expected_projections and actual_lineage["projections"] != expected_projections:
            failures.append(f"{label} {dimension_key} 승인 projection 불일치/누락")
    return failures


def _stage_prompt_candidates(
    step_name: str,
    execution: Mapping[str, Any],
) -> list[Mapping[str, Any]]:
    if step_name == "Step1.5":
        return [
            item
            for item in execution.get("rule_candidates") or []
            if isinstance(item, Mapping) and _clean(item.get("mapping_method")) == "routing"
        ]
    if step_name == "Step2":
        return [item for item in execution.get("expected_candidates") or [] if isinstance(item, Mapping)]
    selected_candidate_keys = {
        _clean(slot.get("candidate_key") or slot.get("candidateKey"))
        for slot in execution.get("parameter_slots") or []
        if isinstance(slot, Mapping) and slot.get("selected", True) is not False
    }
    return [
        item
        for item in execution.get("slot_candidate_mappings") or execution.get("expected_candidates") or []
        if isinstance(item, Mapping)
        and _clean(item.get("candidate_key") or item.get("candidateKey")) in selected_candidate_keys
    ]


def _stage_prompt_task_dimensions(
    step_name: str,
    packet: Mapping[str, Any],
) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    selection: list[Mapping[str, Any]] = []
    supporting: list[Mapping[str, Any]] = []
    if step_name == "Step1.5":
        for task in packet.get("routing_tasks") or []:
            if not isinstance(task, Mapping):
                continue
            for candidate in task.get("candidates") or []:
                if not isinstance(candidate, Mapping):
                    continue
                selection.extend(_prompt_source_dimensions(candidate))
        return selection, supporting
    task_field = "parameter_slot_tasks" if step_name == "Step2" else "parameter_value_tasks"
    for task in packet.get(task_field) or []:
        if not isinstance(task, Mapping):
            continue
        selection.extend(item for item in task.get("selection_dimensions") or [] if isinstance(item, Mapping))
        supporting.extend(item for item in task.get("supporting_dimensions") or [] if isinstance(item, Mapping))
    return selection, supporting


def build_prompt_grounding_rows(
    *,
    targets: Sequence[ScenarioEvidence],
    executions: Mapping[int, Mapping[str, Any]],
    execute: bool,
) -> list[PromptGroundingRow]:
    if not execute:
        return []
    rows: list[PromptGroundingRow] = []
    for target in targets:
        execution = executions.get(target.scenario_id) or {}
        raw_packets = execution.get("prompt_packets")
        packets = raw_packets if isinstance(raw_packets, Mapping) else {}
        raw_result = execution.get("result") or {}
        raw_non_inputs = (
            raw_result.get("non_input_items")
            if isinstance(raw_result, Mapping) and raw_result.get("non_input_items") is not None
            else execution.get("non_input_items")
        )
        indirect_items = [
            item
            for item in raw_non_inputs or []
            if isinstance(item, Mapping) and _clean(item.get("mapping_method")) == "indirect"
        ]
        indirect_expectations = _prompt_lineage_expectations(indirect_items)
        for step_name in ("Step1.5", "Step2", "Step3"):
            stage_candidates = _stage_prompt_candidates(
                step_name,
                execution,
            )
            expected_stage = bool(stage_candidates)
            packet = packets.get(step_name)
            if not expected_stage and packet is None:
                rows.append(
                    PromptGroundingRow(
                        scenario_id=target.scenario_id,
                        step=step_name,
                        event_ids=(),
                        dimension_keys=(),
                        verdict="PASS",
                        evidence="해당 단계 prompt packet 불필요로 skip",
                    ),
                )
                continue
            failures: list[str] = []
            reviews: list[str] = []
            if execution.get("prompt_packet_capture_error"):
                failures.append(
                    "actual prompt packet capture 실패: "
                    f"{_redact_error_text(execution['prompt_packet_capture_error'])}",
                )
            if not isinstance(packet, Mapping):
                failures.append("실행된 단계의 actual prompt packet 증적 누락")
                rows.append(
                    PromptGroundingRow(
                        scenario_id=target.scenario_id,
                        step=step_name,
                        event_ids=(),
                        dimension_keys=(),
                        verdict="FAIL",
                        evidence="; ".join(dict.fromkeys(failures)),
                    ),
                )
                continue
            if not expected_stage:
                reviews.append("실행 대상이 아닌 단계에 prompt packet 증적이 존재함")
            scenario_brief = packet.get("scenario_brief")
            if not isinstance(scenario_brief, Mapping):
                failures.append("actual prompt packet scenario_brief 누락")
                event_ids: tuple[int, ...] = ()
                actual_dimension_keys: tuple[str, ...] = ()
            else:
                event_failures, event_reviews, event_ids = _validate_prompt_events(
                    target,
                    scenario_brief,
                )
                failures.extend(event_failures)
                reviews.extend(event_reviews)
                candidate_expectations = _prompt_lineage_expectations(
                    stage_candidates,
                )
                relevant_keys = set(candidate_expectations) | set(
                    indirect_expectations,
                )
                combined_expectations = _merge_prompt_expectations(
                    candidate_expectations,
                    indirect_expectations,
                )
                scenario_expectations = _discovered_prompt_expectations(
                    target,
                    dimension_keys=relevant_keys,
                    fallback=combined_expectations,
                )
                selected_dimensions = [
                    item for item in scenario_brief.get("selected_dimensions") or [] if isinstance(item, Mapping)
                ]
                failures.extend(
                    _validate_prompt_dimension_items(
                        label="scenario_brief.selected_dimensions",
                        items=selected_dimensions,
                        expected=scenario_expectations,
                        exact_keys=True,
                    ),
                )
                actual_dimension_keys = tuple(
                    sorted(
                        {_prompt_dimension_key(item) for item in selected_dimensions if _prompt_dimension_key(item)},
                    ),
                )
                brief_scenario = scenario_brief.get("scenario") or {}
                dimension_values = (
                    brief_scenario.get("dimension_values") if isinstance(brief_scenario, Mapping) else None
                )
                actual_value_keys = (
                    {_clean(key) for key in dimension_values} if isinstance(dimension_values, Mapping) else set()
                )
                if actual_value_keys != relevant_keys:
                    failures.append(
                        "scenario_brief scenario dimension filter 불일치: "
                        f"expected={sorted(relevant_keys)}, actual={sorted(actual_value_keys)}",
                    )

                selection_dimensions, supporting_dimensions = _stage_prompt_task_dimensions(
                    step_name,
                    packet,
                )
                failures.extend(
                    _validate_prompt_dimension_items(
                        label=f"{step_name} task selection",
                        items=selection_dimensions,
                        expected=candidate_expectations,
                        exact_keys=True,
                    ),
                )
                if step_name != "Step1.5":
                    failures.extend(
                        _validate_prompt_dimension_items(
                            label=f"{step_name} task supporting",
                            items=supporting_dimensions,
                            expected=indirect_expectations,
                            exact_keys=True,
                        ),
                    )
            if failures:
                verdict: Verdict = "FAIL"
                evidence = "; ".join(dict.fromkeys(failures))
            elif reviews:
                verdict = "REVIEW"
                evidence = "; ".join(dict.fromkeys(reviews))
            else:
                verdict = "PASS"
                evidence = (
                    "actual prompt packet의 ordered event, 관련 composite/indirect dimension, "
                    "source lineage, 승인 projection이 discovery와 일치함"
                )
            rows.append(
                PromptGroundingRow(
                    scenario_id=target.scenario_id,
                    step=step_name,
                    event_ids=event_ids,
                    dimension_keys=actual_dimension_keys,
                    verdict=verdict,
                    evidence=evidence,
                ),
            )
    return rows


def _sum_call_field(
    calls: Sequence[Mapping[str, Any]],
    *,
    field_name: str,
    usage: bool = False,
) -> int | None:
    values: list[int] = []
    for call in calls:
        source = (call.get("usage") or {}) if usage else call
        if not isinstance(source, Mapping) or source.get(field_name) is None:
            return None
        values.append(int(source[field_name]))
    return sum(values) if values else None


def _internal_retry_count(calls: Sequence[Mapping[str, Any]]) -> int | None:
    counts: list[int] = []
    for call in calls:
        raw = next(
            (
                call[field_name]
                for field_name in (
                    "internal_retry_count",
                    "retry_count",
                    "retries",
                )
                if field_name in call
            ),
            None,
        )
        if raw is None:
            return None
        counts.append(int(raw))
    return sum(counts) if counts else None


def build_performance_rows(
    *,
    targets: Sequence[ScenarioEvidence],
    executions: Mapping[int, Mapping[str, Any]],
    execute: bool,
) -> list[PerformanceRow]:
    if not execute:
        return []
    rows: list[PerformanceRow] = []
    for target in targets:
        execution = executions.get(target.scenario_id) or {}
        all_calls = [call for call in execution.get("llm_calls") or [] if isinstance(call, Mapping)]
        calls_by_step: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
        for call in all_calls:
            step_name = _quality_step_name(call)
            if step_name is not None:
                calls_by_step[step_name].append(call)
        expected = {
            "Step1.5": any(
                _clean(candidate.get("mapping_method")) == "routing"
                for candidate in execution.get("rule_candidates") or []
                if isinstance(candidate, Mapping)
            ),
            "Step2": bool(execution.get("expected_candidates")),
            "Step3": bool(execution.get("parameter_slots")),
        }
        raw_attempts = execution.get("attempts")
        outer_retry_count = max(0, int(raw_attempts or 0) - 1)
        total_elapsed = execution.get("elapsed_seconds")
        for step_name in ("Step1.5", "Step2", "Step3"):
            calls = calls_by_step.get(step_name) or []
            prompt_bytes = _sum_call_field(calls, field_name="prompt_bytes")
            limits = tuple(
                sorted(
                    {int(call["prompt_limit_bytes"]) for call in calls if call.get("prompt_limit_bytes") is not None},
                ),
            )
            prompt_tokens = _sum_call_field(
                calls,
                field_name="prompt_tokens",
                usage=True,
            )
            completion_tokens = _sum_call_field(
                calls,
                field_name="completion_tokens",
                usage=True,
            )
            total_tokens = _sum_call_field(
                calls,
                field_name="total_tokens",
                usage=True,
            )
            elapsed_values = [
                float(call["elapsed_seconds"]) for call in calls if call.get("elapsed_seconds") is not None
            ]
            elapsed_seconds = sum(elapsed_values) if len(elapsed_values) == len(calls) and calls else None
            internal_retry_count = _internal_retry_count(calls)
            failures: list[str] = []
            reviews: list[str] = []
            if execution.get("error"):
                failures.append("scenario execution error")
            if not calls and expected[step_name]:
                failures.append("필수 LLM call 증적 없음")
            if calls and any(call.get("success") is False for call in calls):
                failures.append("실패 LLM call 포함")
            if calls and (
                prompt_bytes is None
                or len(limits) != 1
                or prompt_tokens is None
                or completion_tokens is None
                or total_tokens is None
                or elapsed_seconds is None
            ):
                reviews.append("prompt/token/time/guard 증적 일부 미수집")
            if (
                calls
                and prompt_bytes is not None
                and limits
                and any(
                    int(call.get("prompt_bytes") or 0) > int(call.get("prompt_limit_bytes") or limits[0])
                    for call in calls
                )
            ):
                failures.append("configured prompt byte guard 초과")
            if calls and internal_retry_count is None:
                reviews.append("internal retry 미수집")
            elif internal_retry_count:
                reviews.append(f"internal retry {internal_retry_count}회")
            if calls and raw_attempts is None:
                reviews.append("outer retry 미수집")
            if outer_retry_count:
                reviews.append(f"outer retry {outer_retry_count}회")
            if isinstance(total_elapsed, int | float) and total_elapsed > 180:
                failures.append(f"scenario 전체 180초 초과 ({total_elapsed:.3f}s)")
            elif not isinstance(total_elapsed, int | float):
                reviews.append("scenario 전체 elapsed 미수집")
            if not calls and not expected[step_name] and not failures and not reviews:
                verdict: Verdict = "PASS"
                evidence = "해당 단계 LLM call 불필요로 skip"
            elif failures:
                verdict = "FAIL"
                evidence = "; ".join(dict.fromkeys(failures))
            elif reviews:
                verdict = "REVIEW"
                evidence = "; ".join(dict.fromkeys(reviews))
            else:
                verdict = "PASS"
                evidence = "prompt bytes/token/time/retry 증적 일치"
            rows.append(
                PerformanceRow(
                    scenario_id=target.scenario_id,
                    step=step_name,
                    call_count=len(calls),
                    prompt_bytes=prompt_bytes,
                    prompt_limit_bytes=limits,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    elapsed_seconds=elapsed_seconds,
                    outer_retry_count=outer_retry_count,
                    internal_retry_count=internal_retry_count,
                    verdict=verdict,
                    evidence=evidence,
                ),
            )
    return rows


def _performance_verdict(execution: Mapping[str, Any]) -> Verdict:
    metrics = _llm_metrics(execution)
    elapsed = execution.get("elapsed_seconds")
    attempts = int(execution.get("attempts") or 0)
    if (
        execution.get("error")
        or (isinstance(elapsed, int | float) and elapsed > 180)
        or metrics["prompt_guard_exceeded"]
    ):
        return "FAIL"
    if (
        attempts > 1
        or metrics["prompt_bytes"] is None
        or metrics["total_tokens"] is None
        or not metrics["internal_retry_captured"]
        or not metrics["call_elapsed_captured"]
        or not isinstance(elapsed, int | float)
    ):
        return "REVIEW"
    return "PASS"


def _bounded_stage_evidence(
    value: Any,
    *,
    depth: int = 0,
    max_depth: int = 6,
    list_limit: int = 8,
    mapping_limit: int = 30,
    text_limit: int = 500,
) -> Any:
    """Bound stage evidence without storing complete prompts or large catalogs."""
    if depth >= max_depth:
        if isinstance(value, Mapping):
            return {"summary": f"mapping({len(value)}) omitted at depth {depth}"}
        if isinstance(value, list | tuple):
            return [f"{len(value)} items omitted at depth {depth}"]
    if isinstance(value, Mapping):
        items = list(value.items())
        bounded = {
            str(key): _bounded_stage_evidence(
                item,
                depth=depth + 1,
                max_depth=max_depth,
                list_limit=list_limit,
                mapping_limit=mapping_limit,
                text_limit=text_limit,
            )
            for key, item in items[:mapping_limit]
        }
        if len(items) > mapping_limit:
            bounded["_omitted_fields"] = len(items) - mapping_limit
        return bounded
    if isinstance(value, list | tuple):
        bounded_items = [
            _bounded_stage_evidence(
                item,
                depth=depth + 1,
                max_depth=max_depth,
                list_limit=list_limit,
                mapping_limit=mapping_limit,
                text_limit=text_limit,
            )
            for item in value[:list_limit]
        ]
        if len(value) > list_limit:
            bounded_items.append({"_omitted_items": len(value) - list_limit})
        return bounded_items
    if isinstance(value, str) and len(value) > text_limit:
        return {
            "text_chars": len(value),
            "excerpt": value[:text_limit],
        }
    return json_safe(value)


def _stage_output_evidence(
    step_name: str,
    execution: Mapping[str, Any],
) -> dict[str, Any]:
    result = execution.get("result") or {}
    warnings = (result.get("validation_warnings") if isinstance(result, Mapping) else []) or []
    if step_name == "Step1.5":
        return {
            "selected_candidates": execution.get("expected_candidates") or [],
            "routing_status": execution.get("routing_status"),
            "routing_messages": execution.get("routing_messages") or [],
            "validation_warnings": warnings,
        }
    if step_name == "Step2":
        return {
            "selected_slots": [
                slot
                for slot in execution.get("parameter_slots") or []
                if isinstance(slot, Mapping) and slot.get("selected", True) is not False
            ],
            "validation_warnings": warnings,
        }
    proposal_row = execution.get("proposal_db_row") or {}
    final_response = execution.get("final_response") or {}
    response_data = (final_response.get("data") if isinstance(final_response, Mapping) else {}) or {}
    return {
        "parameter_adjustments": (result.get("parameter_adjustments") if isinstance(result, Mapping) else []) or [],
        "validation_warnings": warnings,
        "persistence_read_back": {
            "model_param_proposal_id": proposal_row.get(
                "model_param_proposal_id",
            ),
            "scenario_id": proposal_row.get("scenario_id"),
            "scenario_group_id": proposal_row.get("scenario_group_id"),
            "mi_event_id": proposal_row.get("mi_event_id"),
            "status": proposal_row.get("status"),
            "proposal_parameter_count": len(
                proposal_row.get("proposal_parameters") or [],
            ),
            "confirmation_parameter_count": len(
                proposal_row.get("confirmation_parameters") or [],
            ),
            "api_event_id": response_data.get("eventId"),
            "api_scenario_group_id": response_data.get("scenarioGroupId"),
        },
    }


def _render_stage_io_appendix(
    *,
    selected_targets: Sequence[ScenarioEvidence],
    executions: Mapping[int, Mapping[str, Any]],
    execute: bool,
) -> list[str]:
    lines = [
        "",
        "## 단계별 LLM 입출력 증적",
        "",
        (
            "입력은 완료된 graph state에서 production과 동일한 packet builder로 사후 재구성한 "
            "sanitized 요약이며 provider wire payload 원문이 아닙니다. 출력은 graph의 정규화 결과와 "
            "DB read-back 요약입니다. 비밀값과 전체 prompt 원문은 기록하지 않습니다."
        ),
    ]
    if not execute:
        lines.extend(["", "- `--execute` 미지정으로 단계별 입출력 증적 없음"])
        return lines
    for target in selected_targets:
        execution = executions.get(target.scenario_id) or {}
        packets = execution.get("prompt_packets") or {}
        lines.extend(["", f"### Scenario {target.scenario_id}", ""])
        for step_name in ("Step1.5", "Step2", "Step3"):
            packet = packets.get(step_name) if isinstance(packets, Mapping) else None
            if not isinstance(packet, Mapping):
                lines.append(
                    f"- `{step_name}`: LLM 호출 불필요로 skip되었거나 packet 증적이 없습니다.",
                )
                continue
            input_json = json.dumps(
                _bounded_stage_evidence(packet),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
                default=str,
            )
            output_json = json.dumps(
                _bounded_stage_evidence(
                    _stage_output_evidence(step_name, execution),
                ),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
                default=str,
            )
            lines.extend(
                [
                    f"<details><summary>{step_name} 입력/출력</summary>",
                    "",
                    "입력 packet 요약:",
                    "",
                    "```json",
                    _redact_report_text(input_json),
                    "```",
                    "",
                    "출력 요약:",
                    "",
                    "```json",
                    _redact_report_text(output_json),
                    "```",
                    "",
                    "</details>",
                    "",
                ],
            )
    return lines


def render_report(
    *,
    started_at: datetime,
    finished_at: datetime,
    execute: bool,
    preflight: SchemaPreflight,
    selected_targets: Sequence[ScenarioEvidence],
    skipped_targets: Sequence[ScenarioEvidence],
    discovery_messages: Sequence[str],
    active_parameter_definitions: Sequence[Mapping[str, Any]],
    coverage_rows: Sequence[CoverageRow],
    executions: Mapping[int, Mapping[str, Any]],
    integrity_issues: Sequence[str],
    contract_evidence: ContractEvidence | None = None,
) -> str:
    execution_errors = [
        f"scenario {scenario_id}: {_redact_error_text(record.get('error'))}"
        for scenario_id, record in executions.items()
        if record.get("error")
    ]
    parameter_quality_rows = build_parameter_quality_rows(
        targets=selected_targets,
        executions=executions,
        execute=execute,
    )
    performance_rows = build_performance_rows(
        targets=selected_targets,
        executions=executions,
        execute=execute,
    )
    performance_verdicts = [row.verdict for row in performance_rows]
    prompt_grounding_rows = build_prompt_grounding_rows(
        targets=selected_targets,
        executions=executions,
        execute=execute,
    )
    prompt_grounding_verdicts = [row.verdict for row in prompt_grounding_rows]
    contract_failure_verdicts: list[Verdict] = (
        [contract_evidence.verdict] if contract_evidence is not None and contract_evidence.verdict != "PASS" else []
    )
    contract_status_by_name = {
        case.name: case.verdict for case in (contract_evidence.cases if contract_evidence is not None else ())
    }
    invalid_status_contract: Verdict = max(
        (
            contract_status_by_name.get(
                "invalid-status service rollback",
                "COVERAGE LIMIT",
            ),
            contract_status_by_name.get(
                "invalid-status workflow no-mutation",
                "COVERAGE LIMIT",
            ),
        ),
        key=lambda item: _VERDICT_PRIORITY[item],
    )
    numeric_contract_status: Verdict = max(
        (
            contract_status_by_name.get(
                "persistence numeric precision",
                "COVERAGE LIMIT",
            ),
            contract_status_by_name.get(
                "persistence finite numeric",
                "COVERAGE LIMIT",
            ),
            contract_status_by_name.get(
                "reconfirmation numeric precision",
                "COVERAGE LIMIT",
            ),
        ),
        key=lambda item: _VERDICT_PRIORITY[item],
    )
    custom_parameter_contract = _unit_contract_status(
        contract_status_by_name.get(
            "custom parameter service persistence",
            "COVERAGE LIMIT",
        ),
    )
    overall = _overall_verdict(
        preflight=preflight,
        targets=selected_targets,
        coverage_rows=coverage_rows,
        execution_errors=[
            *execution_errors,
            *integrity_issues,
            *("performance contract FAIL" for verdict in performance_verdicts if verdict == "FAIL"),
            *("actual prompt grounding contract FAIL" for verdict in prompt_grounding_verdicts if verdict == "FAIL"),
        ],
        additional_verdicts=[
            *performance_verdicts,
            *prompt_grounding_verdicts,
            *contract_failure_verdicts,
        ],
    )
    lines = [
        "# Model Parameter v3 Multi-Event Quality Report",
        "",
        f"- 판정: **{overall}**",
        f"- 모드: {'EXECUTE (proposal/confirmation write)' if execute else 'READ-ONLY DISCOVERY'}",
        f"- 시작: {started_at.isoformat(timespec='seconds')}",
        f"- 종료: {finished_at.isoformat(timespec='seconds')}",
        f"- active parameter: {len(active_parameter_definitions)}개 (DB runtime 조회)",
        "- `parameter_mapping_ready=false`는 실행 gate로 사용하지 않음",
        "",
        "## Schema preflight",
        "",
        f"- 판정: {preflight.verdict}",
        *[f"- {_md(message)}" for message in preflight.messages],
        "",
        "## Automated mock/unit contract preflight",
        "",
        "- 아래 결과는 외부 DB·LLM을 사용하지 않은 격리 회귀이며 live 실행 증적을 대체하지 않습니다.",
        (
            f"- 판정: {contract_evidence.verdict}"
            if contract_evidence is not None
            else "- 판정: COVERAGE LIMIT (hook 증적 미제공)"
        ),
        (
            f"- 소요시간: {contract_evidence.elapsed_seconds:.3f}s"
            if contract_evidence is not None and contract_evidence.elapsed_seconds is not None
            else "- 소요시간: N/A"
        ),
        "",
        "| contract | node | 판정 | 증적 |",
        "|---|---|---|---|",
    ]
    if contract_evidence is not None:
        for case in contract_evidence.cases:
            lines.append(
                f"| {_md(case.name)} | `{_md(case.node_id)}` | {case.verdict} | {_md(case.evidence)} |",
            )
    else:
        lines.append("| - | - | COVERAGE LIMIT | automated hook 미실행 |")
    lines.extend(
        [
            "",
            "## 선택 대상",
            "",
            "| group | scenario | events | mapping ready | eligible parameters | lineage |",
            "|---:|---:|---:|---|---|---|",
        ],
    )
    if selected_targets:
        for target in selected_targets:
            lineage = "FAIL: " + "; ".join(target.errors) if target.errors else "PASS"
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(target.scenario_group_id),
                        str(target.scenario_id),
                        str(target.relation_count),
                        str(target.parameter_mapping_ready).lower(),
                        _md(", ".join(sorted(target.eligible_parameters)) or "없음"),
                        _md(lineage),
                    ],
                )
                + " |",
            )
    else:
        lines.append("| - | - | - | - | 없음 | COVERAGE LIMIT |")

    lines.extend(
        [
            "",
            "## Ordered event grounding evidence",
            "",
            ("이벤트 핵심 정보는 title 500자, summary 300자, bullet 5개, tag 8개, detail 1,200자로 제한해 표시합니다."),
            "",
            ("| scenario | order | event/type/template | title | summary | key bullets | tags | detail excerpt |"),
            "|---:|---:|---|---|---|---|---|---|",
        ],
    )
    event_count = 0
    for target in selected_targets:
        for event in target.ordered_events:
            event_count += 1
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(target.scenario_id),
                        str(event.get("display_order") or "-"),
                        _md(
                            f"{event.get('mi_event_id')}/"
                            f"{event.get('event_type_l2_id')}/"
                            f"{event.get('scenario_dimension_template_id')}",
                        ),
                        _md(event.get("title")),
                        _md(event.get("one_line_summary")),
                        _md(" / ".join(event.get("key_bullets") or [])),
                        _md(", ".join(event.get("tags") or [])),
                        _md(event.get("detail_excerpt")),
                    ],
                )
                + " |",
            )
    if event_count == 0:
        lines.append("| - | - | - | - | - | - | - | COVERAGE LIMIT |")

    lines.extend(
        [
            "",
            "## Actual Step1.5/2/3 prompt grounding contract",
            "",
            (
                "Discovery 표가 아니라 완료된 graph state에서 production과 동일한 packet builder로 "
                "재구성한 실제 단계 입력을 판정합니다. 필수 packet 또는 scenario_brief가 없으면 FAIL입니다."
            ),
            "",
            "| scenario | step | ordered event IDs | relevant dimensions | 판정 | 증적 |",
            "|---:|---|---|---|---|---|",
        ],
    )
    if prompt_grounding_rows:
        for row in prompt_grounding_rows:
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(row.scenario_id),
                        row.step,
                        _md(",".join(map(str, row.event_ids)) or "-"),
                        _md(",".join(row.dimension_keys) or "-"),
                        row.verdict,
                        _md(row.evidence),
                    ],
                )
                + " |",
            )
    else:
        lines.append(
            "| - | Step1.5/2/3 | - | - | COVERAGE LIMIT | --execute 미지정 |",
        )

    lines.extend(
        _render_stage_io_appendix(
            selected_targets=selected_targets,
            executions=executions,
            execute=execute,
        ),
    )

    lines.extend(
        [
            "",
            "## Scenario dimension grounding",
            "",
            "| scenario | dimension | selected value | projection status |",
            "|---:|---|---|---|",
        ],
    )
    dimension_count = 0
    for target in selected_targets:
        for dimension_key, selected_value in target.dimension_values.items():
            dimension_count += 1
            statuses = [status for status in target.projection_statuses if status.startswith(f"{dimension_key}=")]
            lines.append(
                f"| {target.scenario_id} | {_md(dimension_key)} | "
                f"{_md(selected_value)} | {_md(', '.join(statuses) or 'raw')} |",
            )
    if dimension_count == 0:
        lines.append("| - | - | - | COVERAGE LIMIT |")

    lines.extend(
        [
            "",
            "## Active parameter coverage",
            "",
            (
                "`eligible`은 sourceRef와 DB mapping을 독립 역투영한 occurrence 수입니다. "
                "`candidate`는 Step1, `selected`는 Step1.5 결과입니다."
            ),
            "",
            "| parameter | eligible | candidate | selected | proposed | confirmed | 판정 | 증적 |",
            "|---|---:|---:|---:|---:|---:|---|---|",
        ],
    )
    for row in coverage_rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    _md(row.parameter_name),
                    str(row.eligible),
                    _count_text(row.candidate),
                    _count_text(row.selected),
                    _count_text(row.proposed),
                    _count_text(row.confirmed),
                    row.verdict,
                    _md(row.evidence),
                ],
            )
            + " |",
        )

    lines.extend(
        [
            "",
            "## Lineage 및 expected mapping",
            "",
            (
                "| scenario | composite dimension | source template/dim | event type | "
                "source events | method | parameter task |"
            ),
            "|---:|---|---|---:|---|---|---|",
        ],
    )
    occurrence_count = 0
    for target in selected_targets:
        for occurrence in target.occurrences:
            occurrence_count += 1
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(target.scenario_id),
                        _md(occurrence["scenario_dimension_key"]),
                        _md(
                            f"{occurrence['scenario_dimension_template_id']}/{occurrence['mapping_dimension_key']}",
                        ),
                        str(occurrence["event_type_l2_id"]),
                        _md(",".join(map(str, occurrence["source_event_ids"]))),
                        _md(occurrence["mapping_method"]),
                        _md(occurrence["candidate_key"]),
                    ],
                )
                + " |",
            )
    if occurrence_count == 0:
        lines.append("| - | - | - | - | - | - | 없음 |")

    lines.extend(
        [
            "",
            "## Slot/reference/value/rationale 계약",
            "",
            (
                "| scenario | parameter | selected/exact slots | references | "
                "Step3/API/DB/confirmed values | source | source count | 판정 | 증적 |"
            ),
            "|---:|---|---:|---:|---|---|---:|---|---|",
        ],
    )
    if parameter_quality_rows:
        for row in parameter_quality_rows:
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(row.scenario_id),
                        _md(row.parameter_name),
                        f"{row.selected_slot_count}/{row.exact_slot_count}",
                        str(row.reference_count),
                        (
                            f"{row.step3_value_count}/{row.api_value_count}/"
                            f"{row.db_value_count}/{row.confirmed_value_count}"
                        ),
                        _md(",".join(row.reference_sources) or "-"),
                        str(row.source_count),
                        row.verdict,
                        _md(row.evidence),
                    ],
                )
                + " |",
            )
    else:
        lines.append("| - | - | NOT RUN | NOT RUN | NOT RUN | - | - | COVERAGE LIMIT | --execute 미지정 |")

    lines.extend(
        [
            "",
            "### Rationale 의미 품질 수동 검토",
            "",
            "| scenario | parameter | source count | 판정 | 수동 검토 항목 |",
            "|---:|---|---:|---|---|",
        ],
    )
    manual_rows = list(parameter_quality_rows)
    if manual_rows:
        for row in manual_rows:
            lines.append(
                f"| {row.scenario_id} | {_md(row.parameter_name)} | {row.source_count} | "
                f"{row.verdict} | {_md(row.manual_review)} |",
            )
    else:
        lines.append("| - | - | - | COVERAGE LIMIT | 검토 대상 실행 증적 없음 |")

    lines.extend(
        [
            "",
            "### Proposed value grounding 수동 검토",
            "",
            (
                "| scenario | parameter | coordinates | basecase | LUT | proposed | "
                "parameter rationale | value rationale |"
            ),
            "|---:|---|---|---:|---:|---:|---|---|",
        ],
    )
    proposed_value_count = 0
    for target in selected_targets:
        execution = executions.get(target.scenario_id) or {}
        for parameter in _final_proposal_parameters(execution):
            parameter_name = _parameter_name(parameter)
            parameter_rationale = _bounded_text(
                parameter.get("rationale"),
                limit=600,
            )
            for value in parameter.get("values") or []:
                if not isinstance(value, Mapping):
                    continue
                proposed_value_count += 1
                coordinates = {
                    str(key): item
                    for key, item in value.items()
                    if str(key)
                    not in {
                        "basecaseValue",
                        "basecase_value",
                        "lutValue",
                        "lut_value",
                        "proposedValue",
                        "proposed_value",
                        "rationale",
                    }
                }
                lines.append(
                    "| "
                    + " | ".join(
                        [
                            str(target.scenario_id),
                            _md(parameter_name),
                            _md(
                                json.dumps(
                                    coordinates,
                                    ensure_ascii=False,
                                    sort_keys=True,
                                    default=str,
                                ),
                            ),
                            _md(value.get("basecaseValue", value.get("basecase_value"))),
                            _md(value.get("lutValue", value.get("lut_value"))),
                            _md(value.get("proposedValue", value.get("proposed_value"))),
                            _md(parameter_rationale),
                            _md(_bounded_text(value.get("rationale"), limit=600)),
                        ],
                    )
                    + " |",
                )
    if proposed_value_count == 0:
        lines.append("| - | - | - | - | - | - | - | COVERAGE LIMIT |")

    lines.extend(
        [
            "",
            "## 성능 및 관측성",
            "",
            (
                "| scenario | step | calls | prompt bytes / configured guard | "
                "prompt/completion/total tokens | elapsed | outer retry | internal retry | 판정 | 증적 |"
            ),
            "|---:|---|---:|---|---|---:|---:|---:|---|---|",
        ],
    )
    if performance_rows:
        for row in performance_rows:
            limits = ",".join(map(str, row.prompt_limit_bytes)) or "N/A"
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(row.scenario_id),
                        row.step,
                        str(row.call_count),
                        f"{row.prompt_bytes if row.prompt_bytes is not None else 'N/A'} / {limits}",
                        (
                            f"{row.prompt_tokens if row.prompt_tokens is not None else 'N/A'}/"
                            f"{row.completion_tokens if row.completion_tokens is not None else 'N/A'}/"
                            f"{row.total_tokens if row.total_tokens is not None else 'N/A'}"
                        ),
                        (f"{row.elapsed_seconds:.3f}s" if row.elapsed_seconds is not None else "N/A"),
                        str(row.outer_retry_count),
                        (str(row.internal_retry_count) if row.internal_retry_count is not None else "N/A"),
                        row.verdict,
                        _md(row.evidence),
                    ],
                )
                + " |",
            )
    else:
        lines.append(
            "| - | Step1.5/2/3 | NOT RUN | N/A | N/A | N/A | N/A | N/A | COVERAGE LIMIT | --execute 미지정 |",
        )

    lines.extend(
        [
            "",
            "### Scenario overall 및 attempt trace",
            "",
            (
                "| scenario | overall elapsed | attempt | status | attempt elapsed | "
                "LLM calls | total tokens | prompt bytes | error |"
            ),
            "|---:|---:|---:|---|---:|---:|---:|---:|---|",
        ],
    )
    attempt_row_count = 0
    for target in selected_targets:
        execution = executions.get(target.scenario_id) or {}
        overall_elapsed = execution.get("elapsed_seconds")
        attempt_traces = [trace for trace in execution.get("attempt_traces") or [] if isinstance(trace, Mapping)]
        if not attempt_traces:
            attempt_row_count += 1
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(target.scenario_id),
                        (f"{float(overall_elapsed):.3f}s" if isinstance(overall_elapsed, int | float) else "N/A"),
                        "-",
                        "NOT RUN",
                        "N/A",
                        "0",
                        "N/A",
                        "N/A",
                        _md(_redact_error_text(execution.get("error"))) if execution.get("error") else "-",
                    ],
                )
                + " |",
            )
            continue
        for trace in attempt_traces:
            attempt_row_count += 1
            calls = [call for call in trace.get("llm_calls") or [] if isinstance(call, Mapping)]
            total_tokens = _sum_call_field(
                calls,
                field_name="total_tokens",
                usage=True,
            )
            prompt_bytes = _sum_call_field(
                calls,
                field_name="prompt_bytes",
            )
            attempt_elapsed = trace.get("elapsed_seconds")
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(target.scenario_id),
                        (f"{float(overall_elapsed):.3f}s" if isinstance(overall_elapsed, int | float) else "N/A"),
                        str(trace.get("attempt") or "-"),
                        _md(trace.get("status") or "UNKNOWN"),
                        (f"{float(attempt_elapsed):.3f}s" if isinstance(attempt_elapsed, int | float) else "N/A"),
                        str(len(calls)),
                        str(total_tokens) if total_tokens is not None else "N/A",
                        str(prompt_bytes) if prompt_bytes is not None else "N/A",
                        (_md(_redact_error_text(trace.get("error"))) if trace.get("error") else "-"),
                    ],
                )
                + " |",
            )
    if attempt_row_count == 0:
        lines.append("| - | N/A | - | NOT RUN | N/A | 0 | N/A | N/A | - |")

    lines.extend(
        [
            "",
            "## Confirmation regression evidence",
            "",
            (
                "| scenario | empty rollback (live execute) | valid (live execute) | "
                "reconfirm (live execute) | invalid-status (mock/unit) | "
                "custom persistence (mock/unit) | finite/precision (mock/unit) |"
            ),
            "|---:|---|---|---|---|---|---|",
        ],
    )
    if selected_targets:
        for target in selected_targets:
            confirmation = (executions.get(target.scenario_id) or {}).get("confirmation") or {}
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(target.scenario_id),
                        _md(
                            (confirmation.get("invalid_payload") or {}).get("status") or "NOT RUN",
                        ),
                        _md(
                            (confirmation.get("valid_confirmation") or {}).get("status") or "NOT RUN",
                        ),
                        _md(
                            (confirmation.get("reconfirmation") or {}).get("status") or "NOT RUN",
                        ),
                        _unit_contract_status(invalid_status_contract),
                        custom_parameter_contract,
                        _unit_contract_status(numeric_contract_status),
                    ],
                )
                + " |",
            )
    else:
        lines.append(
            "| - | NOT RUN | NOT RUN | NOT RUN | "
            f"{_unit_contract_status(invalid_status_contract)} | "
            f"{custom_parameter_contract} | "
            f"{_unit_contract_status(numeric_contract_status)} |",
        )

    notes = [
        *discovery_messages,
        *(
            f"skipped scenario {target.scenario_id}: "
            + (
                "; ".join(target.errors)
                if target.errors
                else target.selection_skip_reason or "selection scope에서 미선택"
            )
            for target in skipped_targets
        ),
        *(f"scenario {target.scenario_id}: {warning}" for target in selected_targets for warning in target.warnings),
        *integrity_issues,
        *execution_errors,
    ]
    lines.extend(["", "## 경고 및 제한", ""])
    if notes:
        lines.extend(f"- {_md(note)}" for note in dict.fromkeys(notes))
    else:
        lines.append("- 없음")
    lines.extend(
        [
            "",
            "## 판정 해석",
            "",
            "- `PASS`: 실행된 eligible chain과 lineage/persistence 계약이 일치함.",
            "- `REVIEW`: 형식은 유효하나 routing 선택, 재시도, prompt 관측성 또는 값 근거의 수동 검토가 필요함.",
            "- `FAIL`: lineage, mapping, slot/persistence/confirmation 또는 실행 계약 위반.",
            "- `COVERAGE LIMIT`: 실제 적합 scenario가 없거나 read-only 모드라 후속 단계를 실행하지 않음.",
        ],
    )
    return "\n".join(lines) + "\n"


async def execute_targets(
    targets: Sequence[ScenarioEvidence],
    *,
    retries: int,
) -> dict[int, dict[str, Any]]:
    executions: dict[int, dict[str, Any]] = {}
    if any(target.errors for target in targets):
        blocked_ids = [target.scenario_id for target in targets if target.errors]
        message = f"global lineage preflight failed; all graph/write calls blocked: invalid_scenario_ids={blocked_ids}"
        return {
            target.scenario_id: {
                "error": message,
                "attempts": 0,
                "attempt_traces": [],
                "elapsed_seconds": 0.0,
                "llm_calls": [],
            }
            for target in targets
        }
    for target in targets:
        started = time.perf_counter()
        attempt_traces: list[dict[str, Any]] = []
        for attempt_index in range(retries + 1):
            attempt_started = time.perf_counter()
            try:
                record = await execute_proposal_and_confirmation(target.scenario_id)
                try:
                    record["prompt_packets"] = capture_execute_prompt_packets(
                        record,
                    )
                except Exception as prompt_capture_exc:
                    record["prompt_packets"] = {}
                    record["prompt_packet_capture_error"] = _safe_exception_text(
                        prompt_capture_exc,
                    )
                attempt_llm_calls = [
                    {
                        **dict(call),
                        "outer_attempt": attempt_index + 1,
                    }
                    for call in record.get("llm_calls") or []
                    if isinstance(call, Mapping)
                ]
                attempt_traces.append(
                    {
                        "attempt": attempt_index + 1,
                        "elapsed_seconds": time.perf_counter() - attempt_started,
                        "status": "PASS",
                        "llm_calls": json_safe(attempt_llm_calls),
                    },
                )
                record["attempts"] = attempt_index + 1
                record["attempt_traces"] = attempt_traces
                record["elapsed_seconds"] = time.perf_counter() - started
                record["llm_calls"] = [
                    call for attempt_trace in attempt_traces for call in attempt_trace.get("llm_calls") or []
                ]
                executions[target.scenario_id] = record
                break
            except Exception as exc:
                trace: dict[str, Any] = {
                    "attempt": attempt_index + 1,
                    "elapsed_seconds": time.perf_counter() - attempt_started,
                    "status": "FAIL",
                    "error": _safe_exception_text(exc),
                }
                failure_trace = getattr(exc, "_model_parameter_failure_trace", None)
                if isinstance(failure_trace, dict):
                    trace.update(json_safe(failure_trace))
                    trace["error"] = _safe_exception_text(exc)
                    trace["llm_calls"] = [
                        {
                            **dict(call),
                            "outer_attempt": attempt_index + 1,
                        }
                        for call in trace.get("llm_calls") or []
                        if isinstance(call, Mapping)
                    ]
                attempt_traces.append(trace)
                if attempt_index < retries:
                    await asyncio.sleep(2.0 * (attempt_index + 1))
                    continue
                executions[target.scenario_id] = {
                    "error": _safe_exception_text(exc),
                    "attempts": attempt_index + 1,
                    "attempt_traces": attempt_traces,
                    "elapsed_seconds": time.perf_counter() - started,
                    "llm_calls": [
                        call for attempt_trace in attempt_traces for call in attempt_trace.get("llm_calls") or []
                    ],
                }
    return executions


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Discover and optionally execute v3 multi-event Model Parameter "
            "quality evaluation. The default mode is read-only."
        ),
    )
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("--scenario-group-id", type=int)
    scope.add_argument("--scenario-id", type=int)
    parser.add_argument(
        "--max-scenarios",
        type=int,
        default=5,
        help="Maximum scenarios selected by dynamic coverage discovery (default: 5).",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Opt in to real graph execution, proposal persistence, and confirmation writes.",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=0,
        help="Outer retries per scenario in execute mode (default: 0).",
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        help="Integrated Markdown output path.",
    )
    return parser


async def run(args: argparse.Namespace) -> tuple[Path, Verdict]:
    started_at = datetime.now(UTC)
    contract_evidence = await asyncio.to_thread(
        run_automated_contract_preflight,
    )
    session = get_sync_session()
    try:
        preflight = schema_preflight(session)
        if preflight.verdict == "PASS":
            discovered, parameter_definitions, discovery_messages = discover_v3_scenarios(
                session,
                scenario_group_id=args.scenario_group_id,
                scenario_id=args.scenario_id,
            )
        else:
            discovered = []
            parameter_definitions = []
            discovery_messages = ["schema preflight 실패로 discovery를 중단했습니다."]
    finally:
        session.close()

    explicit_scope = args.scenario_group_id is not None or args.scenario_id is not None
    selected_targets, skipped_targets = select_quality_targets(
        discovered,
        max_scenarios=max(1, args.max_scenarios),
        explicit_scope=explicit_scope,
    )
    if args.execute and contract_evidence.verdict != "PASS":
        executions = {
            target.scenario_id: {
                "error": "automated contract preflight failed; all graph/write calls blocked",
                "attempts": 0,
                "attempt_traces": [],
                "elapsed_seconds": 0.0,
                "llm_calls": [],
            }
            for target in selected_targets
        }
    elif args.execute:
        executions = await execute_targets(
            selected_targets,
            retries=max(0, args.retries),
        )
    else:
        executions = {}
    coverage_rows, integrity_issues = build_coverage_matrix(
        active_parameter_definitions=parameter_definitions,
        targets=selected_targets,
        executions=executions,
        execute=args.execute,
        discovered_targets=discovered,
    )
    finished_at = datetime.now(UTC)
    report = render_report(
        started_at=started_at,
        finished_at=finished_at,
        execute=args.execute,
        preflight=preflight,
        selected_targets=selected_targets,
        skipped_targets=skipped_targets,
        discovery_messages=discovery_messages,
        active_parameter_definitions=parameter_definitions,
        coverage_rows=coverage_rows,
        executions=executions,
        integrity_issues=integrity_issues,
        contract_evidence=contract_evidence,
    )
    report_path = args.report_path
    if report_path is None:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        report_path = REPORT_DIR / (f"model_parameter_multi_event_quality_{started_at.strftime('%Y%m%d_%H%M%S')}.md")
    else:
        report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    execution_errors = [
        *(_redact_error_text(record.get("error")) for record in executions.values() if record.get("error")),
        *integrity_issues,
    ]
    performance_rows = build_performance_rows(
        targets=selected_targets,
        executions=executions,
        execute=args.execute,
    )
    execution_errors.extend(
        f"scenario {row.scenario_id} {row.step} performance contract FAIL"
        for row in performance_rows
        if row.verdict == "FAIL"
    )
    prompt_grounding_rows = build_prompt_grounding_rows(
        targets=selected_targets,
        executions=executions,
        execute=args.execute,
    )
    execution_errors.extend(
        f"scenario {row.scenario_id} {row.step} actual prompt grounding contract FAIL"
        for row in prompt_grounding_rows
        if row.verdict == "FAIL"
    )
    overall = _overall_verdict(
        preflight=preflight,
        targets=selected_targets,
        coverage_rows=coverage_rows,
        execution_errors=execution_errors,
        additional_verdicts=[
            *[row.verdict for row in performance_rows],
            *[row.verdict for row in prompt_grounding_rows],
            *([contract_evidence.verdict] if contract_evidence.verdict != "PASS" else []),
        ],
    )
    return report_path, overall


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report_path, verdict = asyncio.run(run(args))
    print(json.dumps({"report": str(report_path), "verdict": verdict}, ensure_ascii=False))
    return 1 if verdict == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
