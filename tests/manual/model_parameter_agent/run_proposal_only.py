# Copyright (c) 2026 SK Innovation E&S.
# ruff: noqa: ANN401, C901, E402

"""Run proposal-only Model Parameter evaluations once with durable evidence.

This runner is intentionally narrower than the API/background workflows: it calls
``_evaluate_scenario`` directly, never calls confirmation or callback code, and
never retries a write-producing attempt.
"""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import re
import sys
import time
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

from sqlalchemy import select

from apps.agents.model_parameter_agent.persistence.model_parameter_service import (
    ModelParameterService,
)
from apps.common.configs.database.sync_database.connection import get_sync_session
from apps.common.logging.logger_config import logger
from apps.persistence.model_parameter.models import MiModelParamProposalModel
from tests.manual.model_parameter_agent.evaluate_proposals import (
    _evaluate_scenario,
    _failure_trace_from_exception,
)
from tests.manual.model_parameter_agent.runner_common import (
    fetch_proposal_db_row,
    json_safe,
    proposal_id,
)


V4_API_VERSION = "v4"
V4_STRATEGY = "multi_event_model_lever_dimensions"
EVIDENCE_SCHEMA_VERSION = 1
DEFAULT_EVIDENCE_DIR = ROOT_DIR / "tests" / "reports" / "model_parameter_agent"

_SECRET_PATTERNS = (
    re.compile(
        r"(?i)(password|passwd|pwd|token|api[_-]?key|authorization|secret)"
        r"(\s*[=:]\s*)([^\s,;]+)",
    ),
    re.compile(r"(?i)([a-z][a-z0-9+.-]*://[^:/@\s]+):([^@\s]+)@"),
    re.compile(r"(?i)(bearer\s+)([a-z0-9._~+/-]+=*)"),
)
_OMITTED_KEYS = {
    "access_key",
    "access_key_id",
    "access_token",
    "api_key",
    "authorization",
    "client_secret",
    "context",
    "cookie",
    "messages",
    "password",
    "prompt",
    "refresh_token",
    "scenario_context",
    "secret",
    "secret_access_key",
    "token",
}
_PROPOSAL_ROW_FIELDS = (
    "model_param_proposal_id",
    "scenario_id",
    "scenario_group_id",
    "mi_event_id",
    "request_usr_id",
    "status",
    "callback_status",
    "proposal_completed_dtm",
    "callback_sent_dtm",
    "confirmed_dtm",
    "error_code",
    "error_message",
    "proposal_parameters",
    "confirmation_parameters",
    "mod_usr_logn_id",
    "mod_dtm",
    "fetch_status",
)


@dataclass(frozen=True)
class ProposalOnlyOptions:
    execute: bool
    scenario_ids: tuple[int, ...]
    evidence_path: Path


@dataclass(frozen=True)
class RunnerDependencies:
    load_context: Callable[[int], Mapping[str, Any]]
    snapshot_proposal_ids: Callable[[int], tuple[int, ...]]
    evaluate_scenario: Callable[[int], Awaitable[dict[str, Any]]]
    fetch_proposal: Callable[[int | None], dict[str, Any]]
    failure_trace: Callable[[BaseException], Mapping[str, Any]]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run each explicitly selected v4 scenario proposal exactly once without confirmation/callback.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Required acknowledgement that proposal rows will be written.",
    )
    parser.add_argument(
        "--scenario-id",
        action="append",
        dest="scenario_ids",
        type=int,
        default=[],
        help="Scenario ID to execute; repeat for additional scenarios.",
    )
    parser.add_argument("--evidence-path", type=Path)
    return parser


def _default_evidence_path(started_at: datetime) -> Path:
    timestamp = started_at.strftime("%Y%m%d_%H%M%S_%f")
    return DEFAULT_EVIDENCE_DIR / f"model_parameter_proposal_only_{timestamp}.json"


def _options_from_args(args: argparse.Namespace, started_at: datetime) -> ProposalOnlyOptions:
    raw_path = args.evidence_path or _default_evidence_path(started_at)
    return ProposalOnlyOptions(
        execute=bool(args.execute),
        scenario_ids=tuple(args.scenario_ids),
        evidence_path=raw_path.expanduser().resolve(),
    )


def _validate_options(options: ProposalOnlyOptions) -> None:
    if not options.execute:
        message = "--execute is required; this runner has no implicit write mode"
        raise ValueError(message)
    if not options.scenario_ids:
        message = "at least one --scenario-id is required"
        raise ValueError(message)
    invalid_ids = [scenario_id for scenario_id in options.scenario_ids if scenario_id <= 0]
    if invalid_ids:
        message = f"--scenario-id must be positive: {invalid_ids}"
        raise ValueError(message)
    duplicate_ids = sorted(
        {scenario_id for scenario_id in options.scenario_ids if options.scenario_ids.count(scenario_id) > 1},
    )
    if duplicate_ids:
        message = f"duplicate --scenario-id values are not allowed: {duplicate_ids}"
        raise ValueError(message)


def _redact_text(value: object) -> str:
    text = str(value)
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub(r"\1\2<redacted>", text) if pattern.groups == 3 else pattern.sub(r"\1<redacted>", text)
    return text


def _sanitize_json(value: Any) -> Any:
    safe = json_safe(value)
    if isinstance(safe, Mapping):
        sanitized: dict[str, Any] = {}
        for raw_key, item in safe.items():
            key = str(raw_key)
            normalized_key = key.casefold().replace("-", "_")
            if (
                normalized_key in _OMITTED_KEYS
                or normalized_key.endswith(("_context", "_messages", "_secret"))
                or "prompt" in normalized_key
            ):
                continue
            sanitized[key] = _sanitize_json(item)
        return sanitized
    if isinstance(safe, list | tuple):
        return [_sanitize_json(item) for item in safe]
    if isinstance(safe, str):
        return _redact_text(safe)
    return safe


def _reserve_evidence_path(path: Path, initial_evidence: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as evidence_file:
        json.dump(
            _sanitize_json(initial_evidence),
            evidence_file,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        evidence_file.write("\n")


def _write_evidence(path: Path, evidence: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(
            _sanitize_json(evidence),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _snapshot_proposal_ids(scenario_id: int) -> tuple[int, ...]:
    session = get_sync_session()
    try:
        proposal_ids = session.execute(
            select(MiModelParamProposalModel.model_param_proposal_id)
            .where(
                MiModelParamProposalModel.scenario_id == scenario_id,
                MiModelParamProposalModel.del_yn == "N",
            )
            .order_by(MiModelParamProposalModel.model_param_proposal_id),
        ).scalars()
        return tuple(int(value) for value in proposal_ids.all())
    finally:
        session.close()


def _runtime_dependencies() -> RunnerDependencies:
    service = ModelParameterService()
    return RunnerDependencies(
        load_context=service.load_context,
        snapshot_proposal_ids=_snapshot_proposal_ids,
        evaluate_scenario=_evaluate_scenario,
        fetch_proposal=fetch_proposal_db_row,
        failure_trace=_failure_trace_from_exception,
    )


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _preflight_scenario(
    scenario_id: int,
    load_context: Callable[[int], Mapping[str, Any]],
) -> dict[str, Any]:
    try:
        context = load_context(scenario_id)
        group = context.get("scenario_group") or {}
        scenario = context.get("scenario") or {}
        api_version = str(group.get("api_version") or "")
        strategy = str(group.get("generation_strategy") or "")
        loaded_scenario_id = _int_or_none(scenario.get("scenario_id"))
        errors: list[str] = []
        if loaded_scenario_id != scenario_id:
            errors.append(
                f"scenario identity mismatch: requested={scenario_id}, loaded={loaded_scenario_id}",
            )
        if api_version != V4_API_VERSION:
            errors.append(f"api_version must be exactly {V4_API_VERSION!r}: actual={api_version!r}")
        if strategy != V4_STRATEGY:
            errors.append(f"generation_strategy must be exactly {V4_STRATEGY!r}: actual={strategy!r}")
        return {
            "scenario_id": scenario_id,
            "scenario_group_id": _int_or_none(group.get("scenario_group_id")),
            "api_version": api_version,
            "generation_strategy": strategy,
            "status": "PASS" if not errors else "FAIL",
            "errors": errors,
        }
    except Exception as exc:
        return {
            "scenario_id": scenario_id,
            "status": "FAIL",
            "errors": [f"context preflight failed: {_redact_text(repr(exc))}"],
        }


def _proposal_row_evidence(row: Mapping[str, Any]) -> dict[str, Any]:
    return {field: row.get(field) for field in _PROPOSAL_ROW_FIELDS if field in row}


def _public_final_response(record: Mapping[str, Any]) -> dict[str, Any]:
    response = record.get("final_response") or {}
    if not isinstance(response, Mapping):
        return {}
    data = response.get("data") or {}
    safe_data = (
        {
            key: data.get(key)
            for key in (
                "modelParamProposalId",
                "model_param_proposal_id",
                "scenarioId",
                "scenario_id",
                "scenarioGroupId",
                "scenario_group_id",
                "eventId",
                "event_id",
                "proposalParameters",
                "proposal_parameters",
            )
            if key in data
        }
        if isinstance(data, Mapping)
        else {}
    )
    return {
        key: value
        for key, value in {
            "status": response.get("status"),
            "message": response.get("message"),
            "data": safe_data,
        }.items()
        if value is not None
    }


def _llm_call_evidence(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list | tuple):
        return []
    calls: list[dict[str, Any]] = []
    for raw_call in value:
        if not isinstance(raw_call, Mapping):
            continue
        call = {
            field: raw_call.get(field)
            for field in (
                "step",
                "success",
                "model_name",
                "elapsed_seconds",
                "prompt_bytes",
                "prompt_limit_bytes",
                "parameter_bytes",
                "retry_count",
                "internal_retry_count",
                "attempt",
                "attempt_count",
                "retries",
                "error",
            )
            if field in raw_call
        }
        usage = raw_call.get("usage")
        if isinstance(usage, Mapping):
            call["usage"] = {
                field: usage.get(field)
                for field in (
                    "prompt_tokens",
                    "completion_tokens",
                    "total_tokens",
                    "input_tokens",
                    "output_tokens",
                )
                if field in usage
            }
        calls.append(call)
    return calls


def _record_summary(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "mapping_ok": record.get("mapping_ok"),
        "mapping_messages": record.get("mapping_messages") or [],
        "selected_ok": record.get("selected_ok"),
        "selected_messages": record.get("selected_messages") or [],
        "routing_status": record.get("routing_status"),
        "routing_messages": record.get("routing_messages") or [],
        "step_summary": record.get("step_summary") or {},
        "lut_version": record.get("lut_version"),
        "value_signature": record.get("value_signature"),
        "llm_calls": _llm_call_evidence(record.get("llm_calls")),
        "final_response": _public_final_response(record),
    }


def _failure_summary(trace: Mapping[str, Any]) -> dict[str, Any]:
    summary = {
        key: trace.get(key)
        for key in (
            "failed_stage",
            "error",
            "proposal_persisted",
            "model_param_proposal_id",
            "mapping_trace_captured",
            "partial_state_captured",
            "step_summary",
        )
        if key in trace
    }
    summary["llm_calls"] = _llm_call_evidence(trace.get("llm_calls"))
    return summary


def _safe_fetch_proposal(
    proposal_id_value: int,
    fetch_proposal: Callable[[int | None], dict[str, Any]],
) -> tuple[dict[str, Any], str | None]:
    try:
        row = fetch_proposal(proposal_id_value)
        return _proposal_row_evidence(row), None
    except Exception as exc:
        return {}, _redact_text(repr(exc))


def _success_integrity_errors(
    *,
    scenario_id: int,
    scenario_group_id: int | None,
    model_param_proposal_id: int | None,
    new_proposal_ids: Sequence[int],
    proposal_row: Mapping[str, Any],
    readback_error: str | None,
) -> list[str]:
    errors: list[str] = []
    if model_param_proposal_id is None:
        errors.append("success response did not contain modelParamProposalId")
    if model_param_proposal_id is not None and tuple(new_proposal_ids) != (model_param_proposal_id,):
        errors.append(
            "proposal ID snapshot delta must contain exactly the returned ID: "
            f"returned={model_param_proposal_id}, delta={list(new_proposal_ids)}",
        )
    if readback_error:
        errors.append(f"proposal DB read-back failed: {readback_error}")
    if model_param_proposal_id is not None and not proposal_row:
        errors.append("proposal DB read-back returned no row")
    expected_fields = {
        "model_param_proposal_id": model_param_proposal_id,
        "scenario_id": scenario_id,
        "scenario_group_id": scenario_group_id,
        "mi_event_id": None,
        "status": "PROPOSED",
        "callback_status": "SKIPPED",
        "confirmation_parameters": None,
        "confirmed_dtm": None,
    }
    for field, expected in expected_fields.items():
        if proposal_row and proposal_row.get(field) != expected:
            errors.append(f"proposal DB field mismatch: {field}={proposal_row.get(field)!r}, expected={expected!r}")
    return errors


async def _execute_once(
    scenario_id: int,
    preflight: Mapping[str, Any],
    dependencies: RunnerDependencies,
) -> dict[str, Any]:
    started_at = datetime.now(UTC)
    started = time.perf_counter()
    attempt: dict[str, Any] = {
        "scenario_id": scenario_id,
        "scenario_group_id": preflight.get("scenario_group_id"),
        "execution_attempt_count": 0,
        "started_at": started_at.isoformat(),
        "status": "FAIL",
    }
    try:
        before_ids = dependencies.snapshot_proposal_ids(scenario_id)
    except Exception as exc:
        attempt.update(
            {
                "failed_stage": "proposal ID pre-snapshot",
                "error": _redact_text(repr(exc)),
                "finished_at": datetime.now(UTC).isoformat(),
                "elapsed_seconds": time.perf_counter() - started,
            },
        )
        return attempt

    attempt["proposal_ids_before"] = list(before_ids)
    attempt["execution_attempt_count"] = 1
    evaluation_record: dict[str, Any] = {}
    evaluation_error: Exception | None = None
    trace: Mapping[str, Any] = {}
    try:
        evaluation_record = await dependencies.evaluate_scenario(scenario_id)
    except Exception as exc:
        evaluation_error = exc
        trace = dependencies.failure_trace(exc)

    if evaluation_error is None:
        attempt["evaluation"] = _record_summary(evaluation_record)
        model_param_proposal_id = proposal_id(evaluation_record.get("final_response") or {})
    else:
        attempt["failed_stage"] = trace.get("failed_stage") or "proposal evaluation"
        attempt["error"] = _redact_text(repr(evaluation_error))
        attempt["failure_trace"] = _failure_summary(trace)
        model_param_proposal_id = _int_or_none(trace.get("model_param_proposal_id"))
    attempt["model_param_proposal_id"] = model_param_proposal_id

    proposal_row: dict[str, Any] = {}
    readback_error: str | None = None
    if model_param_proposal_id is not None:
        proposal_row, readback_error = _safe_fetch_proposal(
            model_param_proposal_id,
            dependencies.fetch_proposal,
        )
        attempt["proposal_db_row"] = proposal_row
        if readback_error:
            attempt["proposal_db_readback_error"] = readback_error

    after_ids: tuple[int, ...] = ()
    snapshot_after_error: str | None = None
    try:
        after_ids = dependencies.snapshot_proposal_ids(scenario_id)
        attempt["proposal_ids_after"] = list(after_ids)
    except Exception as exc:
        snapshot_after_error = _redact_text(repr(exc))
        attempt["proposal_id_post_snapshot_error"] = snapshot_after_error

    new_ids = tuple(value for value in after_ids if value not in set(before_ids))
    attempt["new_proposal_ids"] = list(new_ids)
    undiscovered_ids = [value for value in new_ids if value != model_param_proposal_id]
    if undiscovered_ids:
        snapshot_rows: dict[str, Any] = {}
        for discovered_id in undiscovered_ids:
            row, error = _safe_fetch_proposal(discovered_id, dependencies.fetch_proposal)
            snapshot_rows[str(discovered_id)] = row if error is None else {"readback_error": error}
        attempt["snapshot_discovered_rows"] = snapshot_rows
        if model_param_proposal_id is None and len(undiscovered_ids) == 1:
            reconciled_id = undiscovered_ids[0]
            attempt["reconciled_model_param_proposal_id"] = reconciled_id
            reconciled_row = snapshot_rows[str(reconciled_id)]
            if "readback_error" not in reconciled_row:
                attempt["proposal_db_row"] = reconciled_row

    integrity_errors: list[str] = []
    if evaluation_error is None:
        integrity_errors.extend(
            _success_integrity_errors(
                scenario_id=scenario_id,
                scenario_group_id=_int_or_none(preflight.get("scenario_group_id")),
                model_param_proposal_id=model_param_proposal_id,
                new_proposal_ids=new_ids,
                proposal_row=proposal_row,
                readback_error=readback_error,
            ),
        )
    else:
        integrity_errors.append("proposal evaluation raised; automatic retry is forbidden")
    if snapshot_after_error:
        integrity_errors.append(f"proposal ID post-snapshot failed: {snapshot_after_error}")
    if integrity_errors:
        attempt["integrity_errors"] = integrity_errors
    else:
        attempt["status"] = "PASS"
    attempt["proposal_persisted"] = bool(
        trace.get("proposal_persisted") or model_param_proposal_id is not None or new_ids,
    )
    attempt["finished_at"] = datetime.now(UTC).isoformat()
    attempt["elapsed_seconds"] = time.perf_counter() - started
    return attempt


async def run_campaign(
    options: ProposalOnlyOptions,
    *,
    dependencies: RunnerDependencies | None = None,
) -> dict[str, Any]:
    _validate_options(options)
    dependencies = dependencies or _runtime_dependencies()
    started_at = datetime.now(UTC)
    evidence: dict[str, Any] = {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "runner": "model_parameter_proposal_only",
        "mode": "execute",
        "status": "RESERVED",
        "started_at": started_at.isoformat(),
        "requested_scenario_ids": list(options.scenario_ids),
        "safety": {
            "sequential": True,
            "max_attempts_per_scenario": 1,
            "automatic_retry": False,
            "confirmation_invoked": False,
            "callback_invoked": False,
            "required_api_version": V4_API_VERSION,
            "required_generation_strategy": V4_STRATEGY,
        },
        "preflight": [],
        "attempts": [],
    }
    _reserve_evidence_path(options.evidence_path, evidence)

    preflight = [_preflight_scenario(scenario_id, dependencies.load_context) for scenario_id in options.scenario_ids]
    evidence["preflight"] = preflight
    if any(item.get("status") != "PASS" for item in preflight):
        evidence["status"] = "BLOCKED"
        evidence["finished_at"] = datetime.now(UTC).isoformat()
        _write_evidence(options.evidence_path, evidence)
        return evidence

    evidence["status"] = "RUNNING"
    _write_evidence(options.evidence_path, evidence)
    preflight_by_id = {int(item["scenario_id"]): item for item in preflight}
    for scenario_id in options.scenario_ids:
        attempt = await _execute_once(
            scenario_id,
            preflight_by_id[scenario_id],
            dependencies,
        )
        evidence["attempts"].append(attempt)
        _write_evidence(options.evidence_path, evidence)
        if attempt.get("execution_attempt_count") == 0:
            break

    evidence["status"] = (
        "PASS"
        if len(evidence["attempts"]) == len(options.scenario_ids)
        and all(attempt.get("status") == "PASS" for attempt in evidence["attempts"])
        else "FAIL"
    )
    evidence["finished_at"] = datetime.now(UTC).isoformat()
    _write_evidence(options.evidence_path, evidence)
    return evidence


def main(argv: Sequence[str] | None = None) -> int:
    started_at = datetime.now(UTC)
    args = build_parser().parse_args(argv)
    options = _options_from_args(args, started_at)
    try:
        evidence = asyncio.run(run_campaign(options))
    except (FileExistsError, ValueError) as exc:
        logger.error("Proposal-only runner safety gate failed | error={}", _redact_text(repr(exc)))
        return 2
    except Exception as exc:
        logger.exception("Proposal-only runner failed unexpectedly | error={}", _redact_text(repr(exc)))
        return 1
    logger.info(
        "Proposal-only runner finished | status={} evidence_path={} scenarios={} attempts={}",
        evidence["status"],
        options.evidence_path,
        len(options.scenario_ids),
        len(evidence["attempts"]),
    )
    return 0 if evidence["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
