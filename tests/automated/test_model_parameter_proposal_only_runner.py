# Copyright (c) 2026 SK Innovation E&S.
# ruff: noqa: S101

from __future__ import annotations

import asyncio
import inspect
import json
from pathlib import Path

import pytest

from tests.manual.model_parameter_agent import run_proposal_only as runner


def _context(scenario_id: int, *, api_version: str = "v4", strategy: str = runner.V4_STRATEGY) -> dict[str, object]:
    return {
        "scenario": {"scenario_id": scenario_id, "scenario_group_id": scenario_id + 1_000},
        "scenario_group": {
            "scenario_group_id": scenario_id + 1_000,
            "api_version": api_version,
            "generation_strategy": strategy,
        },
    }


def _proposal_row(scenario_id: int, proposal_id: int) -> dict[str, object]:
    return {
        "model_param_proposal_id": proposal_id,
        "scenario_id": scenario_id,
        "scenario_group_id": scenario_id + 1_000,
        "mi_event_id": None,
        "request_usr_id": None,
        "status": "PROPOSED",
        "callback_status": "SKIPPED",
        "proposal_completed_dtm": "2026-09-16T10:00:00",
        "callback_sent_dtm": None,
        "confirmed_dtm": None,
        "error_code": None,
        "error_message": None,
        "proposal_parameters": [{"parameterName": "GDP"}],
        "confirmation_parameters": None,
        "mod_usr_logn_id": "system",
        "mod_dtm": "2026-09-16T10:00:00",
    }


def _options(tmp_path: Path, *scenario_ids: int, execute: bool = True) -> runner.ProposalOnlyOptions:
    return runner.ProposalOnlyOptions(
        execute=execute,
        scenario_ids=scenario_ids,
        evidence_path=tmp_path / "proposal-only.json",
    )


def test_parser_accepts_repeatable_scenario_ids_and_execute_is_mandatory(tmp_path: Path) -> None:
    args = runner.build_parser().parse_args(
        [
            "--execute",
            "--scenario-id",
            "101",
            "--scenario-id",
            "102",
            "--evidence-path",
            str(tmp_path / "evidence.json"),
        ],
    )
    options = runner._options_from_args(args, runner.datetime.now(runner.UTC))  # noqa: SLF001

    assert options.execute is True
    assert options.scenario_ids == (101, 102)
    with pytest.raises(ValueError, match="--execute is required"):
        asyncio.run(runner.run_campaign(_options(tmp_path, 101, execute=False)))
    with pytest.raises(ValueError, match="duplicate --scenario-id"):
        asyncio.run(runner.run_campaign(_options(tmp_path, 101, 101)))


def test_evidence_path_is_reserved_exclusively(tmp_path: Path) -> None:
    path = tmp_path / "exclusive.json"

    runner._reserve_evidence_path(path, {"status": "RESERVED"})  # noqa: SLF001

    assert json.loads(path.read_text(encoding="utf-8"))["status"] == "RESERVED"
    with pytest.raises(FileExistsError):
        runner._reserve_evidence_path(path, {"status": "SHOULD_NOT_OVERWRITE"})  # noqa: SLF001
    assert json.loads(path.read_text(encoding="utf-8"))["status"] == "RESERVED"


def test_exact_v4_strategy_preflight_blocks_every_write(tmp_path: Path) -> None:
    evaluated: list[int] = []

    async def evaluate(scenario_id: int) -> dict[str, object]:
        evaluated.append(scenario_id)
        return {}

    def snapshot(_scenario_id: int) -> tuple[int, ...]:
        message = "snapshot must not run when any target fails the all-scenario preflight"
        raise AssertionError(message)

    dependencies = runner.RunnerDependencies(
        load_context=lambda scenario_id: (
            _context(scenario_id) if scenario_id == 101 else _context(scenario_id, api_version="V4")
        ),
        snapshot_proposal_ids=snapshot,
        evaluate_scenario=evaluate,
        fetch_proposal=lambda _proposal_id: {},
        failure_trace=lambda _exc: {},
    )

    evidence = asyncio.run(
        runner.run_campaign(
            _options(tmp_path, 101, 102),
            dependencies=dependencies,
        ),
    )

    assert evidence["status"] == "BLOCKED"
    assert evidence["attempts"] == []
    assert evaluated == []
    assert [item["status"] for item in evidence["preflight"]] == ["PASS", "FAIL"]


def test_successful_scenarios_execute_once_sequentially_and_update_sanitized_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposal_ids = {101: 501, 102: 502}
    snapshot_values = {
        101: iter(((400,), (400, 501))),
        102: iter(((401,), (401, 502))),
    }
    calls: list[tuple[str, int]] = []
    write_attempt_counts: list[int] = []

    def snapshot(scenario_id: int) -> tuple[int, ...]:
        calls.append(("snapshot", scenario_id))
        return next(snapshot_values[scenario_id])

    async def evaluate(scenario_id: int) -> dict[str, object]:
        calls.append(("evaluate", scenario_id))
        proposal_id = proposal_ids[scenario_id]
        return {
            "context": {"raw": "MUST_NOT_BE_WRITTEN"},
            "llm_calls": [
                {
                    "step": "Step3",
                    "success": True,
                    "model_name": "quality-model",
                    "elapsed_seconds": 1.25,
                    "usage": {
                        "prompt_tokens": 100,
                        "completion_tokens": 20,
                        "total_tokens": 120,
                        "provider_raw": "MUST_NOT_BE_WRITTEN",
                    },
                    "retry_count": 1,
                    "prompt": "FULL_SECRET_PROMPT",
                    "messages": [{"content": "FULL_SECRET_PROMPT"}],
                },
            ],
            "mapping_ok": True,
            "mapping_messages": ["password=do-not-store"],
            "selected_ok": True,
            "selected_messages": [],
            "routing_status": "PASS",
            "routing_messages": [],
            "step_summary": {"proposal_parameter_count": 1, "system_prompt": "FULL_SECRET_PROMPT"},
            "lut_version": "test-v1",
            "value_signature": "safe-signature",
            "final_response": {
                "status": "success",
                "message": "model parameter proposal completed",
                "data": {
                    "modelParamProposalId": proposal_id,
                    "scenarioId": scenario_id,
                    "scenarioGroupId": scenario_id + 1_000,
                    "eventId": None,
                    "proposalParameters": [{"parameterName": "GDP"}],
                },
            },
        }

    def fetch(proposal_id: int | None) -> dict[str, object]:
        assert proposal_id is not None
        scenario_id = next(key for key, value in proposal_ids.items() if value == proposal_id)
        calls.append(("fetch", scenario_id))
        return _proposal_row(scenario_id, proposal_id)

    original_write = runner._write_evidence  # noqa: SLF001

    def record_write(path: Path, evidence: dict[str, object]) -> None:
        write_attempt_counts.append(len(evidence["attempts"]))  # type: ignore[arg-type]
        original_write(path, evidence)

    monkeypatch.setattr(runner, "_write_evidence", record_write)
    dependencies = runner.RunnerDependencies(
        load_context=_context,
        snapshot_proposal_ids=snapshot,
        evaluate_scenario=evaluate,
        fetch_proposal=fetch,
        failure_trace=lambda _exc: {},
    )

    evidence = asyncio.run(
        runner.run_campaign(
            _options(tmp_path, 101, 102),
            dependencies=dependencies,
        ),
    )

    assert evidence["status"] == "PASS"
    assert [attempt["execution_attempt_count"] for attempt in evidence["attempts"]] == [1, 1]
    assert [attempt["model_param_proposal_id"] for attempt in evidence["attempts"]] == [501, 502]
    assert evidence["attempts"][0]["evaluation"]["llm_calls"] == [
        {
            "step": "Step3",
            "success": True,
            "model_name": "quality-model",
            "elapsed_seconds": 1.25,
            "retry_count": 1,
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 20,
                "total_tokens": 120,
            },
        },
    ]
    assert calls == [
        ("snapshot", 101),
        ("evaluate", 101),
        ("fetch", 101),
        ("snapshot", 101),
        ("snapshot", 102),
        ("evaluate", 102),
        ("fetch", 102),
        ("snapshot", 102),
    ]
    assert write_attempt_counts == [0, 1, 2, 2]
    serialized = _options(tmp_path, 101, 102).evidence_path.read_text(encoding="utf-8")
    assert "FULL_SECRET_PROMPT" not in serialized
    assert "MUST_NOT_BE_WRITTEN" not in serialized
    assert "do-not-store" not in serialized
    assert json.loads(serialized)["safety"] == {
        "automatic_retry": False,
        "callback_invoked": False,
        "confirmation_invoked": False,
        "max_attempts_per_scenario": 1,
        "required_api_version": "v4",
        "required_generation_strategy": runner.V4_STRATEGY,
        "sequential": True,
    }


def test_failure_retains_trace_persisted_id_readback_and_never_retries(tmp_path: Path) -> None:
    class ProposalFailureError(RuntimeError):
        pass

    snapshots = iter(((600,), (600, 601)))
    calls = 0

    async def evaluate(_scenario_id: int) -> dict[str, object]:
        nonlocal calls
        calls += 1
        message = "response failed password=top-secret"
        raise ProposalFailureError(message)

    def failure_trace(_exc: BaseException) -> dict[str, object]:
        return {
            "failed_stage": "output validation/persistence",
            "proposal_persisted": True,
            "model_param_proposal_id": 601,
            "mapping_trace_captured": True,
            "partial_state_captured": True,
            "context": {"secret": "RAW_CONTEXT_SECRET"},
            "prompt": "FULL_PROMPT_SECRET",
        }

    dependencies = runner.RunnerDependencies(
        load_context=_context,
        snapshot_proposal_ids=lambda _scenario_id: next(snapshots),
        evaluate_scenario=evaluate,
        fetch_proposal=lambda proposal_id: _proposal_row(101, int(proposal_id or 0)),
        failure_trace=failure_trace,
    )

    evidence = asyncio.run(
        runner.run_campaign(
            _options(tmp_path, 101),
            dependencies=dependencies,
        ),
    )

    assert evidence["status"] == "FAIL"
    assert calls == 1
    attempt = evidence["attempts"][0]
    assert attempt["execution_attempt_count"] == 1
    assert attempt["model_param_proposal_id"] == 601
    assert attempt["proposal_persisted"] is True
    assert attempt["proposal_db_row"]["model_param_proposal_id"] == 601
    assert attempt["new_proposal_ids"] == [601]
    serialized = _options(tmp_path, 101).evidence_path.read_text(encoding="utf-8")
    assert "top-secret" not in serialized
    assert "RAW_CONTEXT_SECRET" not in serialized
    assert "FULL_PROMPT_SECRET" not in serialized


def test_snapshot_delta_recovers_unknown_persisted_id_after_failure(tmp_path: Path) -> None:
    snapshots = iter(((700,), (700, 701)))
    fetched: list[int] = []

    async def evaluate(_scenario_id: int) -> dict[str, object]:
        message = "failure without attached proposal ID"
        raise RuntimeError(message)

    def fetch(proposal_id: int | None) -> dict[str, object]:
        assert proposal_id is not None
        fetched.append(proposal_id)
        return _proposal_row(101, proposal_id)

    dependencies = runner.RunnerDependencies(
        load_context=_context,
        snapshot_proposal_ids=lambda _scenario_id: next(snapshots),
        evaluate_scenario=evaluate,
        fetch_proposal=fetch,
        failure_trace=lambda _exc: {"failed_stage": "output validation/persistence"},
    )

    evidence = asyncio.run(
        runner.run_campaign(
            _options(tmp_path, 101),
            dependencies=dependencies,
        ),
    )

    attempt = evidence["attempts"][0]
    assert evidence["status"] == "FAIL"
    assert attempt["model_param_proposal_id"] is None
    assert attempt["reconciled_model_param_proposal_id"] == 701
    assert attempt["new_proposal_ids"] == [701]
    assert attempt["snapshot_discovered_rows"]["701"]["model_param_proposal_id"] == 701
    assert attempt["proposal_db_row"]["model_param_proposal_id"] == 701
    assert fetched == [701]


def test_orchestrator_has_no_confirmation_or_callback_dependency() -> None:
    source = inspect.getsource(runner._execute_once) + inspect.getsource(runner.run_campaign)  # noqa: SLF001

    assert "execute_proposal_and_confirmation" not in source
    assert "run_confirmation_workflow" not in source
    assert "callback" not in inspect.getsource(runner._execute_once)  # noqa: SLF001
