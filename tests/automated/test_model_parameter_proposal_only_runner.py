# Copyright (c) 2026 SK Innovation E&S.
# ruff: noqa: S101

from __future__ import annotations

import asyncio
import inspect
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.manual.model_parameter_agent import evaluate_proposals, run_proposal_only as runner


def _context(
    scenario_id: int,
    *,
    api_version: str = "v4",
    strategy: str = runner.V4_STRATEGY,
    scenario_group_id: int | None = None,
    catalog_version: str = "v4.1",
    catalog_checksum: str = runner.EXPECTED_V4_1_CATALOG_CHECKSUM,
) -> dict[str, object]:
    resolved_group_id = scenario_group_id or scenario_id + 1_000
    return {
        "scenario": {
            "scenario_id": scenario_id,
            "scenario_group_id": resolved_group_id,
            "status": "created",
            "dimension_values": {"d1": "base"},
            "title": f"Scenario {scenario_id}",
            "narrative": "baseline narrative",
        },
        "scenario_group": {
            "scenario_group_id": resolved_group_id,
            "api_version": api_version,
            "generation_strategy": strategy,
            "status": "created",
            "stage": "completed",
            "impact_catalog_version": catalog_version,
            "impact_catalog_checksum": catalog_checksum,
        },
        "events": [
            {
                "mi_event_id": scenario_id + 10_000,
                "display_order": 1,
                "event_title_ko": "test event",
                "detail_analysis": "baseline event detail",
            },
        ],
        "impact_catalog_version": catalog_version,
        "impact_catalog_checksum": catalog_checksum,
    }


def _proposal_row(
    scenario_id: int,
    proposal_id: int,
    *,
    status: str = "PROPOSED",
) -> dict[str, object]:
    return {
        "model_param_proposal_id": proposal_id,
        "scenario_id": scenario_id,
        "scenario_group_id": scenario_id + 1_000,
        "mi_event_id": None,
        "request_usr_id": None,
        "status": status,
        "callback_status": "SKIPPED",
        "proposal_completed_dtm": "2026-09-16T10:00:00",
        "callback_sent_dtm": None,
        "confirmed_dtm": None,
        "error_code": None,
        "error_message": None,
        "proposal_parameters": [{"parameterName": "GDP"}],
        "confirmation_parameters": None,
        "mod_usr_logn_id": "system",
        "crt_dtm": "2026-09-16T09:59:00",
        "mod_dtm": "2026-09-16T10:00:00",
    }


def _options(
    tmp_path: Path,
    *scenario_ids: int,
    execute: bool = True,
    scenario_group_id: int | None = None,
    replay_covered: bool = False,
) -> runner.ProposalOnlyOptions:
    return runner.ProposalOnlyOptions(
        execute=execute,
        scenario_ids=scenario_ids,
        scenario_group_id=scenario_group_id,
        capability_release=runner.BASELINE_CAPABILITY_RELEASE,
        evidence_path=tmp_path / "proposal-only.json",
        replay_covered=replay_covered,
    )


def _quality_evidence(
    *,
    errors: tuple[str, ...] = (),
    catalog_version: str = "v4.1",
    catalog_checksum: str = runner.EXPECTED_V4_1_CATALOG_CHECKSUM,
    runtime_candidates: tuple[dict[str, object], ...] = (
        {
            "candidate_key": "gdp-candidate",
            "canonical_parameter_name": "GDP",
        },
    ),
) -> SimpleNamespace:
    return SimpleNamespace(
        errors=errors,
        active_catalog_version=catalog_version,
        active_catalog_checksum=catalog_checksum,
        raw_candidates=runtime_candidates,
        runtime_candidates=runtime_candidates,
        blocked_candidates=(),
        dimension_lineage=(),
    )


def test_parser_accepts_repeatable_scenario_ids_and_defaults_to_read_only(tmp_path: Path) -> None:
    args = runner.build_parser().parse_args(
        [
            "--scenario-id",
            "101",
            "--scenario-id",
            "102",
            "--capability-release",
            runner.BASELINE_CAPABILITY_RELEASE,
            "--evidence-path",
            str(tmp_path / "evidence.json"),
        ],
    )
    options = runner._options_from_args(args, runner.datetime.now(runner.UTC))  # noqa: SLF001

    assert options.execute is False
    assert options.scenario_ids == (101, 102)
    assert options.required_mi_base_fallback_mode is None
    with pytest.raises(ValueError, match="duplicate --scenario-id"):
        asyncio.run(runner.run_campaign(_options(tmp_path, 101, 101)))


def test_required_mi_base_fallback_mode_blocks_before_resource_or_scenario_work(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resource_manifest = runner._resource_manifest()  # noqa: SLF001
    fallback_policy = SimpleNamespace(
        model_dump=lambda **_kwargs: {
            "no_active_case_mode": "fail",
            "active_case_unavailable_mode": "verified_cache",
        },
    )
    monkeypatch.setattr(runner, "_resource_manifest", lambda: resource_manifest)
    monkeypatch.setattr(
        runner,
        "get_settings",
        lambda: SimpleNamespace(
            model_parameter_mi_base_fallback=fallback_policy,
            model_dump=lambda **_kwargs: {},
        ),
    )
    options = runner.ProposalOnlyOptions(
        execute=True,
        scenario_ids=(101,),
        scenario_group_id=None,
        capability_release=runner.BASELINE_CAPABILITY_RELEASE,
        evidence_path=tmp_path / "fallback-mismatch.json",
        required_mi_base_fallback_mode="configured_fallback",
    )
    dependencies = runner.RunnerDependencies(
        load_context=lambda _scenario_id: (_ for _ in ()).throw(AssertionError("must not load context")),
        snapshot_proposal_rows=lambda _group_id, _scenario_ids: (),
        evaluate_scenario=lambda _scenario_id: (_ for _ in ()).throw(AssertionError("must not evaluate")),
        fetch_proposal=lambda _proposal_id: {},
        failure_trace=lambda _exc: {},
        prepare_resources=lambda: (_ for _ in ()).throw(AssertionError("must not prepare resources")),
    )

    evidence = asyncio.run(runner.run_campaign(options, dependencies=dependencies))

    assert evidence["status"] == "BLOCKED"
    assert evidence["attempts"] == []
    assert evidence["manifest"]["required_mi_base_fallback_mode"] == "configured_fallback"
    assert evidence["selection"]["errors"] == [
        "MI Base fallback mode mismatch: required='configured_fallback', actual='verified_cache'",
    ]


def test_evidence_path_is_reserved_exclusively(tmp_path: Path) -> None:
    path = tmp_path / "exclusive.json"

    runner._reserve_evidence_path(path, {"status": "RESERVED"})  # noqa: SLF001

    assert json.loads(path.read_text(encoding="utf-8"))["status"] == "RESERVED"
    with pytest.raises(FileExistsError):
        runner._reserve_evidence_path(path, {"status": "SHOULD_NOT_OVERWRITE"})  # noqa: SLF001
    assert json.loads(path.read_text(encoding="utf-8"))["status"] == "RESERVED"


def test_config_snapshot_captures_local_neuro_and_runtime_without_secrets() -> None:
    snapshot = runner._model_parameter_config_snapshot()  # noqa: SLF001

    assert snapshot["top_level_key_parity"] is True
    for section in ("local_declared", "neuro_declared", "runtime_effective"):
        values = snapshot[section]
        assert values["model_parameter_proposal_flow_release"] == "v4.1.7"
        assert values["model_parameter_variation_profile_enabled"] is True
        assert values["model_parameter_grounded_slot_recovery_enabled"] is True
        storage = values["model_parameter_resource_storage"]
        assert storage["access_key_id"] == "<redacted>"
        assert storage["secret_access_key"] == "<redacted>"


@pytest.mark.parametrize(
    ("rows", "decision", "reason_code", "hard_stop"),
    [
        ((), "ELIGIBLE", "NO_PROPOSAL_HISTORY", False),
        ((_proposal_row(101, 1, status="FAILED"),), "ELIGIBLE", "FAILED_ONLY", False),
        ((_proposal_row(101, 8, status="ABSTAINED"),), "ELIGIBLE", "ABSTAINED_ONLY", False),
        (
            (
                _proposal_row(101, 9, status="ABSTAINED"),
                _proposal_row(101, 10, status="FAILED"),
            ),
            "ELIGIBLE",
            "ABSTAINED_OR_FAILED_ONLY",
            False,
        ),
        ((_proposal_row(101, 2),), "SKIP", "PROPOSED_EXISTS", False),
        (
            (
                _proposal_row(101, 3, status="CONFIRMED"),
                _proposal_row(101, 4),
            ),
            "SKIP",
            "CONFIRMED_EXISTS",
            False,
        ),
        (
            (_proposal_row(101, 5, status="PROCESSING"),),
            "HARD_STOP",
            "PROCESSING_REQUIRES_MANUAL_REVIEW",
            True,
        ),
        ((_proposal_row(101, 6, status="UNKNOWN"),), "HARD_STOP", "UNKNOWN_PROPOSAL_STATUS", True),
    ],
)
def test_uncovered_guard_classifies_full_active_history(
    rows: tuple[dict[str, object], ...],
    decision: str,
    reason_code: str,
    hard_stop: bool,  # noqa: FBT001
) -> None:
    result = runner._classify_uncovered_guard(  # noqa: SLF001
        scenario_id=101,
        scenario_group_id=1_101,
        rows=rows,
    )

    assert result["decision"] == decision
    assert result["reason_code"] == reason_code
    assert result["hard_stop"] is hard_stop


def test_uncovered_guard_hard_stops_identity_mismatch() -> None:
    row = _proposal_row(101, 7, status="FAILED")
    row["scenario_group_id"] = 999

    result = runner._classify_uncovered_guard(  # noqa: SLF001
        scenario_id=101,
        scenario_group_id=1_101,
        rows=(row,),
    )

    assert result["decision"] == "HARD_STOP"
    assert result["reason_code"] == "PROPOSAL_GUARD_IDENTITY_MISMATCH"
    assert result["hard_stop"] is True


def test_release_replay_allows_proposed_but_not_confirmed_or_processing() -> None:
    proposed = runner._classify_uncovered_guard(  # noqa: SLF001
        scenario_id=101,
        scenario_group_id=1_101,
        rows=(_proposal_row(101, 1, status="PROPOSED"),),
        replay_covered=True,
    )
    confirmed = runner._classify_uncovered_guard(  # noqa: SLF001
        scenario_id=101,
        scenario_group_id=1_101,
        rows=(_proposal_row(101, 2, status="CONFIRMED"),),
        replay_covered=True,
    )
    processing = runner._classify_uncovered_guard(  # noqa: SLF001
        scenario_id=101,
        scenario_group_id=1_101,
        rows=(_proposal_row(101, 3, status="PROCESSING"),),
        replay_covered=True,
    )

    assert proposed["reason_code"] == "PROPOSED_RELEASE_REPLAY"
    assert proposed["eligible"] is True
    assert confirmed["eligible"] is False
    assert processing["hard_stop"] is True


def test_read_only_default_discovers_without_evaluating_or_writing(tmp_path: Path) -> None:
    evaluated: list[int] = []

    async def evaluate(scenario_id: int) -> dict[str, object]:
        evaluated.append(scenario_id)
        return {}

    dependencies = runner.RunnerDependencies(
        load_context=_context,
        snapshot_proposal_rows=lambda _group_id, _scenario_ids: (),
        evaluate_scenario=evaluate,
        fetch_proposal=lambda _proposal_id: {},
        failure_trace=lambda _exc: {},
    )

    evidence = asyncio.run(
        runner.run_campaign(
            _options(tmp_path, 101, execute=False),
            dependencies=dependencies,
        ),
    )

    assert evidence["mode"] == "read-only"
    assert evidence["status"] == "PASS"
    assert evidence["selection"]["eligible_scenario_ids"] == [101]
    assert evidence["attempts"] == []
    assert evaluated == []


def test_quality_oracle_error_blocks_before_proposal_guard(tmp_path: Path) -> None:
    dependencies = runner.RunnerDependencies(
        load_context=_context,
        snapshot_proposal_rows=lambda _group_id, _scenario_ids: (_ for _ in ()).throw(
            AssertionError("quality failure must block before proposal history discovery"),
        ),
        evaluate_scenario=lambda _scenario_id: (_ for _ in ()).throw(AssertionError("must not evaluate")),
        fetch_proposal=lambda _proposal_id: {},
        failure_trace=lambda _exc: {},
        build_quality_evidence=lambda _scenario_id, _context_value: _quality_evidence(
            errors=("catalog lineage drift",),
        ),
    )

    evidence = asyncio.run(
        runner.run_campaign(
            _options(tmp_path, 101, execute=False),
            dependencies=dependencies,
        ),
    )

    assert evidence["status"] == "BLOCKED"
    assert evidence["preflight"][0]["status"] == "FAIL"
    assert "catalog lineage drift" in evidence["preflight"][0]["errors"]


def test_zero_runtime_candidate_is_skipped_but_still_proposal_guarded(tmp_path: Path) -> None:
    snapshots: list[tuple[int, tuple[int, ...]]] = []

    def snapshot(group_id: int, scenario_ids: object) -> tuple[dict[str, object], ...]:
        snapshots.append((group_id, tuple(scenario_ids)))  # type: ignore[arg-type]
        return ()

    dependencies = runner.RunnerDependencies(
        load_context=_context,
        snapshot_proposal_rows=snapshot,
        evaluate_scenario=lambda _scenario_id: (_ for _ in ()).throw(AssertionError("must not evaluate")),
        fetch_proposal=lambda _proposal_id: {},
        failure_trace=lambda _exc: {},
        build_quality_evidence=lambda _scenario_id, _context_value: _quality_evidence(runtime_candidates=()),
    )

    evidence = asyncio.run(
        runner.run_campaign(
            _options(tmp_path, 101, execute=False),
            dependencies=dependencies,
        ),
    )

    assert evidence["status"] == "PASS"
    assert evidence["preflight"][0]["status"] == "SKIP"
    assert evidence["selection"]["eligible_scenario_ids"] == []
    assert snapshots == [(1_101, (101,))]


def test_incomplete_or_discarded_scenario_is_guarded_but_not_quality_evaluated(tmp_path: Path) -> None:
    context = _context(101)
    context["scenario"]["status"] = "discarded"  # type: ignore[index]
    snapshots: list[tuple[int, tuple[int, ...]]] = []

    def snapshot(group_id: int, scenario_ids: object) -> tuple[dict[str, object], ...]:
        snapshots.append((group_id, tuple(scenario_ids)))  # type: ignore[arg-type]
        return ()

    def quality(_scenario_id: int, _context_value: object) -> object:
        message = "lifecycle-ineligible Scenario must not run the quality oracle"
        raise AssertionError(message)

    dependencies = runner.RunnerDependencies(
        load_context=lambda _scenario_id: context,
        snapshot_proposal_rows=snapshot,
        evaluate_scenario=lambda _scenario_id: (_ for _ in ()).throw(AssertionError("must not evaluate")),
        fetch_proposal=lambda _proposal_id: {},
        failure_trace=lambda _exc: {},
        build_quality_evidence=quality,
    )

    evidence = asyncio.run(
        runner.run_campaign(
            _options(tmp_path, 101, execute=False),
            dependencies=dependencies,
        ),
    )

    assert evidence["status"] == "PASS"
    assert evidence["preflight"][0]["status"] == "SKIP"
    assert evidence["selection"]["lifecycle_or_capability_skipped_scenario_ids"] == [101]
    assert evidence["attempts"] == []
    assert snapshots == [(1_101, (101,))]


def test_processing_on_lifecycle_skipped_scenario_hard_stops_campaign(tmp_path: Path) -> None:
    evaluated: list[int] = []

    def context(scenario_id: int) -> dict[str, object]:
        value = _context(scenario_id)
        if scenario_id == 102:
            value["scenario"]["status"] = "discarded"  # type: ignore[index]
        return value

    def snapshot(group_id: int, _scenario_ids: object) -> tuple[dict[str, object], ...]:
        if group_id == 1_102:
            return (_proposal_row(102, 902, status="PROCESSING"),)
        return ()

    async def evaluate(scenario_id: int) -> dict[str, object]:
        evaluated.append(scenario_id)
        return {}

    dependencies = runner.RunnerDependencies(
        load_context=context,
        snapshot_proposal_rows=snapshot,
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
    assert evidence["selection"]["hard_stop_scenario_ids"] == [102]
    assert evidence["attempts"] == []
    assert evaluated == []


def test_processing_in_any_target_hard_stops_campaign_before_first_write(tmp_path: Path) -> None:
    evaluated: list[int] = []

    async def evaluate(scenario_id: int) -> dict[str, object]:
        evaluated.append(scenario_id)
        return {}

    def snapshot(group_id: int, _scenario_ids: object) -> tuple[dict[str, object], ...]:
        if group_id == 1_102:
            return (_proposal_row(102, 900, status="PROCESSING"),)
        return ()

    dependencies = runner.RunnerDependencies(
        load_context=_context,
        snapshot_proposal_rows=snapshot,
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
    assert evidence["selection"]["hard_stop_scenario_ids"] == [102]
    assert evidence["attempts"] == []
    assert evaluated == []


def test_new_processing_on_other_target_hard_stops_campaign_at_prewrite_recheck(tmp_path: Path) -> None:
    calls_by_group = {1_101: 0, 1_102: 0}
    evaluated: list[int] = []

    def snapshot(group_id: int, _scenario_ids: object) -> tuple[dict[str, object], ...]:
        calls_by_group[group_id] += 1
        if group_id == 1_102 and calls_by_group[group_id] >= 2:
            return (_proposal_row(102, 903, status="PROCESSING"),)
        return ()

    async def evaluate(scenario_id: int) -> dict[str, object]:
        evaluated.append(scenario_id)
        return {}

    dependencies = runner.RunnerDependencies(
        load_context=_context,
        snapshot_proposal_rows=snapshot,
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
    assert evidence["attempts"][0]["campaign_hard_stop_scenario_ids"] == [102]
    assert evidence["attempts"][0]["execution_attempt_count"] == 0
    assert evaluated == []


def test_covered_execute_scope_is_a_successful_noop(tmp_path: Path) -> None:
    evaluated: list[int] = []

    async def evaluate(scenario_id: int) -> dict[str, object]:
        evaluated.append(scenario_id)
        return {}

    dependencies = runner.RunnerDependencies(
        load_context=_context,
        snapshot_proposal_rows=lambda _group_id, _scenario_ids: (_proposal_row(101, 901, status="CONFIRMED"),),
        evaluate_scenario=evaluate,
        fetch_proposal=lambda _proposal_id: {},
        failure_trace=lambda _exc: {},
    )

    evidence = asyncio.run(
        runner.run_campaign(
            _options(tmp_path, 101),
            dependencies=dependencies,
        ),
    )

    assert evidence["status"] == "PASS"
    assert evidence["selection"]["covered_scenario_ids"] == [101]
    assert evidence["selection"]["eligible_scenario_ids"] == []
    assert evidence["attempts"] == []
    assert evaluated == []


def test_group_scope_is_expanded_before_read_only_guard(tmp_path: Path) -> None:
    discovered: list[int] = []

    def discover(group_id: int) -> tuple[int, ...]:
        discovered.append(group_id)
        return (101, 102)

    dependencies = runner.RunnerDependencies(
        load_context=lambda scenario_id: _context(scenario_id, scenario_group_id=282),
        snapshot_proposal_rows=lambda _group_id, _scenario_ids: (),
        evaluate_scenario=lambda _scenario_id: (_ for _ in ()).throw(AssertionError("must not evaluate")),
        fetch_proposal=lambda _proposal_id: {},
        failure_trace=lambda _exc: {},
        discover_scenario_ids=discover,
    )

    evidence = asyncio.run(
        runner.run_campaign(
            _options(tmp_path, execute=False, scenario_group_id=282),
            dependencies=dependencies,
        ),
    )

    assert evidence["status"] == "PASS"
    assert evidence["selection"]["discovered_scenario_ids"] == [101, 102]
    assert evidence["selection"]["eligible_scenario_ids"] == [101, 102]
    assert discovered == [282]


def test_group_scope_mismatch_blocks_before_proposal_guard(tmp_path: Path) -> None:
    dependencies = runner.RunnerDependencies(
        load_context=lambda scenario_id: _context(scenario_id, scenario_group_id=999),
        snapshot_proposal_rows=lambda _group_id, _scenario_ids: (_ for _ in ()).throw(
            AssertionError("scope mismatch must block before proposal history discovery"),
        ),
        evaluate_scenario=lambda _scenario_id: (_ for _ in ()).throw(AssertionError("must not evaluate")),
        fetch_proposal=lambda _proposal_id: {},
        failure_trace=lambda _exc: {},
        discover_scenario_ids=lambda _group_id: (101,),
    )

    evidence = asyncio.run(
        runner.run_campaign(
            _options(tmp_path, execute=False, scenario_group_id=282),
            dependencies=dependencies,
        ),
    )

    assert evidence["status"] == "BLOCKED"
    assert "does not match the explicit campaign scope" in evidence["preflight"][0]["errors"][-1]


def test_scenario_and_group_internal_identity_mismatch_fails_preflight(tmp_path: Path) -> None:
    context = _context(101)
    context["scenario"]["scenario_group_id"] = 777  # type: ignore[index]
    dependencies = runner.RunnerDependencies(
        load_context=lambda _scenario_id: context,
        snapshot_proposal_rows=lambda _group_id, _scenario_ids: (_ for _ in ()).throw(
            AssertionError("identity mismatch must block before proposal history discovery"),
        ),
        evaluate_scenario=lambda _scenario_id: (_ for _ in ()).throw(AssertionError("must not evaluate")),
        fetch_proposal=lambda _proposal_id: {},
        failure_trace=lambda _exc: {},
    )

    evidence = asyncio.run(
        runner.run_campaign(
            _options(tmp_path, 101, execute=False),
            dependencies=dependencies,
        ),
    )

    assert evidence["status"] == "BLOCKED"
    assert any("scenario/group identity mismatch" in error for error in evidence["preflight"][0]["errors"])


def test_input_fingerprint_covers_scenario_narrative_ordered_event_and_resource() -> None:
    base_context = _context(101)
    narrative_context = _context(101)
    narrative_context["scenario"]["narrative"] = "changed narrative"  # type: ignore[index]
    event_context = _context(101)
    event_context["events"][0]["detail_analysis"] = "changed event detail"  # type: ignore[index]
    resource = runner._resource_manifest()  # noqa: SLF001
    changed_resource = {**resource, "contract_sha256": "f" * 64}

    def fingerprint(context_value: dict[str, object], resource_value: dict[str, object]) -> str:
        result = runner._preflight_scenario(  # noqa: SLF001
            101,
            lambda _scenario_id: context_value,
            capability_release=runner.BASELINE_CAPABILITY_RELEASE,
            resource_manifest=resource_value,
        )
        assert result["status"] == "PASS"
        return str(result["input_fingerprint"])

    base_fingerprint = fingerprint(base_context, resource)

    assert fingerprint(narrative_context, resource) != base_fingerprint
    assert fingerprint(event_context, resource) != base_fingerprint
    assert fingerprint(base_context, changed_resource) != base_fingerprint


def test_effective_resource_fingerprint_accepts_packaged_release_symlinks(tmp_path: Path) -> None:
    package_root = tmp_path / "package"
    package_basecase = package_root / "basecase"
    package_lut = package_root / "lut"
    package_basecase.mkdir(parents=True)
    package_lut.mkdir()
    (package_basecase / "Demand.xlsm").write_bytes(b"basecase")
    (package_lut / "Demand.csv").write_bytes(b"lut")

    release_root = tmp_path / "release"
    release_root.mkdir()
    (release_root / "basecase").symlink_to(package_basecase, target_is_directory=True)
    (release_root / "lut").symlink_to(package_lut, target_is_directory=True)
    manifest = SimpleNamespace(
        selected_files=lambda *, lut_enabled: (
            SimpleNamespace(target_relative_path="basecase/Demand.xlsm"),
            SimpleNamespace(target_relative_path="lut/Demand.csv"),
        ),
    )

    fingerprint = runner._effective_resource_fingerprint(  # noqa: SLF001
        resource_root=release_root,
        basecase_dir=release_root / "basecase",
        lut_root=release_root / "lut",
        resource_manifest=manifest,
        lut_enabled=True,
    )

    assert len(fingerprint) == 64


def test_prewrite_guard_recheck_blocks_newly_covered_scenario(tmp_path: Path) -> None:
    snapshots = iter(
        (
            (),
            (_proposal_row(101, 990),),
        ),
    )
    evaluated: list[int] = []

    async def evaluate(scenario_id: int) -> dict[str, object]:
        evaluated.append(scenario_id)
        return {}

    dependencies = runner.RunnerDependencies(
        load_context=_context,
        snapshot_proposal_rows=lambda _group_id, _scenario_ids: next(snapshots),
        evaluate_scenario=evaluate,
        fetch_proposal=lambda _proposal_id: {},
        failure_trace=lambda _exc: {},
    )

    evidence = asyncio.run(
        runner.run_campaign(
            _options(tmp_path, 101),
            dependencies=dependencies,
        ),
    )

    assert evidence["status"] == "BLOCKED"
    assert evidence["attempts"][0]["execution_attempt_count"] == 0
    assert evidence["attempts"][0]["campaign_guard_before_write"]["101"]["reason_code"] == "PROPOSED_EXISTS"
    assert evaluated == []


def test_prewrite_context_recheck_blocks_input_drift_before_proposal_guard(tmp_path: Path) -> None:
    contexts = iter((_context(101), _context(101)))
    second_context = next(contexts)
    second_context["scenario"]["narrative"] = "changed after campaign preflight"  # type: ignore[index]
    contexts = iter((_context(101), second_context))
    snapshot_calls = 0
    evaluated: list[int] = []

    def snapshot(_group_id: int, _scenario_ids: object) -> tuple[dict[str, object], ...]:
        nonlocal snapshot_calls
        snapshot_calls += 1
        return ()

    async def evaluate(scenario_id: int) -> dict[str, object]:
        evaluated.append(scenario_id)
        return {}

    dependencies = runner.RunnerDependencies(
        load_context=lambda _scenario_id: next(contexts),
        snapshot_proposal_rows=snapshot,
        evaluate_scenario=evaluate,
        fetch_proposal=lambda _proposal_id: {},
        failure_trace=lambda _exc: {},
    )

    evidence = asyncio.run(
        runner.run_campaign(
            _options(tmp_path, 101),
            dependencies=dependencies,
        ),
    )

    assert evidence["status"] == "BLOCKED"
    assert evidence["attempts"][0]["failed_stage"] == "context/resource preflight recheck"
    assert evidence["attempts"][0]["execution_attempt_count"] == 0
    assert snapshot_calls == 1
    assert evaluated == []


def test_exact_v4_strategy_preflight_blocks_every_write(tmp_path: Path) -> None:
    evaluated: list[int] = []

    async def evaluate(scenario_id: int) -> dict[str, object]:
        evaluated.append(scenario_id)
        return {}

    def snapshot(_scenario_group_id: int, _scenario_ids: object) -> tuple[dict[str, object], ...]:
        message = "snapshot must not run when any target fails the all-scenario preflight"
        raise AssertionError(message)

    dependencies = runner.RunnerDependencies(
        load_context=lambda scenario_id: (
            _context(scenario_id) if scenario_id == 101 else _context(scenario_id, api_version="V4")
        ),
        snapshot_proposal_rows=snapshot,
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


def test_approved_release_requires_exact_v4_1_catalog_pin(tmp_path: Path) -> None:
    stale_context = _context(101)
    stale_context["scenario_group"]["impact_catalog_checksum"] = "a" * 64  # type: ignore[index]
    dependencies = runner.RunnerDependencies(
        load_context=lambda _scenario_id: stale_context,
        snapshot_proposal_rows=lambda _group_id, _scenario_ids: (_ for _ in ()).throw(
            AssertionError("catalog pin mismatch must block before proposal history discovery"),
        ),
        evaluate_scenario=lambda _scenario_id: (_ for _ in ()).throw(AssertionError("must not evaluate")),
        fetch_proposal=lambda _proposal_id: {},
        failure_trace=lambda _exc: {},
    )

    evidence = asyncio.run(
        runner.run_campaign(
            _options(tmp_path, 101, execute=False),
            dependencies=dependencies,
        ),
    )

    assert evidence["status"] == "BLOCKED"
    assert any("approved capability release" in error for error in evidence["preflight"][0]["errors"])


def test_v8_compat_release_accepts_existing_v4_0_catalog_pin(tmp_path: Path) -> None:
    context = _context(
        101,
        catalog_version="v4.0",
        catalog_checksum=runner.EXPECTED_V4_0_CATALOG_CHECKSUM,
    )
    options = runner.ProposalOnlyOptions(
        execute=False,
        scenario_ids=(101,),
        scenario_group_id=None,
        capability_release="extend16-v8-v4.0-compat",
        evidence_path=tmp_path / "v4-0-compat.json",
    )
    dependencies = runner.RunnerDependencies(
        load_context=lambda _scenario_id: context,
        snapshot_proposal_rows=lambda _group_id, _scenario_ids: (),
        evaluate_scenario=lambda _scenario_id: (_ for _ in ()).throw(
            AssertionError("read-only campaign must not execute"),
        ),
        fetch_proposal=lambda _proposal_id: {},
        failure_trace=lambda _exc: {},
        build_quality_evidence=lambda _scenario_id, _context_value: _quality_evidence(
            catalog_version="v4.0",
            catalog_checksum=runner.EXPECTED_V4_0_CATALOG_CHECKSUM,
        ),
    )

    evidence = asyncio.run(
        runner.run_campaign(options, dependencies=dependencies),
    )

    assert evidence["status"] == "PASS"
    assert evidence["preflight"][0]["stored_catalog_version"] == "v4.0"
    assert evidence["preflight"][0]["active_catalog_version"] == "v4.0"


def test_approved_release_blocks_runtime_allowlist_drift_before_database(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        runner,
        "RUNTIME_PROPOSAL_CAPABILITY_NAMES",
        frozenset({*runner.EXPECTED_EXTEND16_ALLOWLIST, "RemainingUnrestrictedAmount"}),
    )

    dependencies = runner.RunnerDependencies(
        load_context=lambda _scenario_id: (_ for _ in ()).throw(AssertionError("must not load context")),
        snapshot_proposal_rows=lambda _group_id, _scenario_ids: (),
        evaluate_scenario=lambda _scenario_id: (_ for _ in ()).throw(AssertionError("must not evaluate")),
        fetch_proposal=lambda _proposal_id: {},
        failure_trace=lambda _exc: {},
    )

    evidence = asyncio.run(
        runner.run_campaign(
            _options(tmp_path, 101, execute=False),
            dependencies=dependencies,
        ),
    )

    assert evidence["status"] == "BLOCKED"
    assert "runtime capability drifted" in evidence["selection"]["errors"][0]


@pytest.mark.parametrize(
    "field",
    [
        "contract_sha256",
        "declared_semantic_schema_hash",
        "effective_resource_fingerprint",
    ],
)
def test_approved_release_rejects_resource_content_identity_drift(field: str) -> None:
    manifest = runner._resource_manifest()  # noqa: SLF001
    manifest[field] = "f" * 64

    errors = runner._release_contract_errors(  # noqa: SLF001
        capability_release=runner.BASELINE_CAPABILITY_RELEASE,
        resource_manifest=manifest,
        require_registered_resources=False,
    )

    assert errors


def test_execute_resource_preparation_failure_blocks_before_database_access(tmp_path: Path) -> None:
    async def prepare() -> None:
        message = "resource bootstrap unavailable"
        raise RuntimeError(message)

    def database_access(*_args: object) -> object:
        message = "resource failure must block before Scenario DB access"
        raise AssertionError(message)

    dependencies = runner.RunnerDependencies(
        load_context=database_access,  # type: ignore[arg-type]
        snapshot_proposal_rows=database_access,  # type: ignore[arg-type]
        evaluate_scenario=lambda _scenario_id: (_ for _ in ()).throw(AssertionError("must not evaluate")),
        fetch_proposal=lambda _proposal_id: {},
        failure_trace=lambda _exc: {},
        prepare_resources=prepare,
        require_registered_resources=True,
    )

    evidence = asyncio.run(
        runner.run_campaign(
            _options(tmp_path, 101),
            dependencies=dependencies,
        ),
    )

    assert evidence["status"] == "BLOCKED"
    assert "resource runtime preparation failed" in evidence["selection"]["errors"][0]
    assert evidence["selection"]["counts"]["discovered"] == 0


def test_execute_schema_preflight_failure_blocks_before_scenario_access(tmp_path: Path) -> None:
    def scenario_access(*_args: object) -> object:
        message = "schema failure must block before Scenario access"
        raise AssertionError(message)

    dependencies = runner.RunnerDependencies(
        load_context=scenario_access,  # type: ignore[arg-type]
        snapshot_proposal_rows=scenario_access,  # type: ignore[arg-type]
        evaluate_scenario=lambda _scenario_id: (_ for _ in ()).throw(AssertionError("must not evaluate")),
        fetch_proposal=lambda _proposal_id: {},
        failure_trace=lambda _exc: {},
        schema_preflight=lambda: SimpleNamespace(
            verdict="FAIL",
            checks=(),
            errors=("proposal.mi_event_id must be nullable",),
        ),
    )

    evidence = asyncio.run(
        runner.run_campaign(
            _options(tmp_path, 101),
            dependencies=dependencies,
        ),
    )

    assert evidence["status"] == "BLOCKED"
    assert evidence["schema_preflight"]["verdict"] == "FAIL"
    assert evidence["selection"]["counts"]["discovered"] == 0


def test_unknown_capability_release_is_rejected_before_evidence_or_database(tmp_path: Path) -> None:
    options = runner.ProposalOnlyOptions(
        execute=False,
        scenario_ids=(101,),
        scenario_group_id=None,
        capability_release="unapproved-release",
        evidence_path=tmp_path / "unknown-release.json",
    )

    with pytest.raises(ValueError, match="unsupported --capability-release"):
        asyncio.run(runner.run_campaign(options))

    assert not options.evidence_path.exists()


def test_reused_evidence_path_fails_before_database_access(tmp_path: Path) -> None:
    options = _options(tmp_path, 101, execute=False)
    runner._reserve_evidence_path(options.evidence_path, {"status": "RESERVED"})  # noqa: SLF001

    def database_access(*_args: object) -> object:
        message = "exclusive evidence reservation must fail before DB access"
        raise AssertionError(message)

    dependencies = runner.RunnerDependencies(
        load_context=database_access,  # type: ignore[arg-type]
        snapshot_proposal_rows=database_access,  # type: ignore[arg-type]
        evaluate_scenario=lambda _scenario_id: (_ for _ in ()).throw(AssertionError("must not evaluate")),
        fetch_proposal=lambda _proposal_id: {},
        failure_trace=lambda _exc: {},
    )

    with pytest.raises(FileExistsError):
        asyncio.run(runner.run_campaign(options, dependencies=dependencies))


def test_successful_scenarios_execute_once_sequentially_and_update_sanitized_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposal_ids = {101: 501, 102: 502}
    history = {
        101: [_proposal_row(101, 400, status="FAILED")],
        102: [_proposal_row(102, 401, status="FAILED")],
    }
    calls: list[tuple[str, int]] = []
    write_attempt_counts: list[int] = []

    def snapshot(scenario_group_id: int, scenario_ids: object) -> tuple[dict[str, object], ...]:
        scenario_id = int(next(iter(scenario_ids)))  # type: ignore[arg-type]
        assert scenario_group_id == scenario_id + 1_000
        calls.append(("snapshot", scenario_id))
        return tuple(history[scenario_id])

    async def evaluate(scenario_id: int) -> dict[str, object]:
        calls.append(("evaluate", scenario_id))
        proposal_id = proposal_ids[scenario_id]
        history[scenario_id].append(_proposal_row(scenario_id, proposal_id))
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
        snapshot_proposal_rows=snapshot,
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
        ("snapshot", 102),
        ("snapshot", 101),
        ("snapshot", 102),
        ("snapshot", 101),
        ("evaluate", 101),
        ("fetch", 101),
        ("snapshot", 101),
        ("snapshot", 101),
        ("snapshot", 102),
        ("snapshot", 102),
        ("evaluate", 102),
        ("fetch", 102),
        ("snapshot", 102),
        ("fetch", 101),
        ("fetch", 102),
    ]
    assert write_attempt_counts[-3:] == [1, 2, 2]
    serialized = _options(tmp_path, 101, 102).evidence_path.read_text(encoding="utf-8")
    assert "FULL_SECRET_PROMPT" not in serialized
    assert "MUST_NOT_BE_WRITTEN" not in serialized
    assert "do-not-store" not in serialized
    assert json.loads(serialized)["safety"] == {
        "automatic_retry": False,
        "callback_invoked": False,
        "confirmation_invoked": False,
        "max_attempts_per_scenario": 1,
        "processing_policy": "any active PROCESSING row hard-stops the entire campaign",
        "required_api_version": "v4",
        "required_generation_strategy": runner.V4_STRATEGY,
        "scenario_failure_policy": "isolate ABSTAINED/FAIL and continue; BLOCKED hard-stops the campaign",
        "sequential": True,
        "single_worker_best_effort": True,
        "uncovered_only": True,
        "append_only_release_replay": False,
        "existing_proposal_rows_preserved": True,
    }


def test_scenario_failure_is_isolated_and_later_candidate_executes_once(tmp_path: Path) -> None:
    history = {
        101: [_proposal_row(101, 400, status="FAILED")],
        102: [_proposal_row(102, 401, status="FAILED")],
    }
    evaluated: list[int] = []

    def snapshot(_scenario_group_id: int, scenario_ids: object) -> tuple[dict[str, object], ...]:
        scenario_id = int(next(iter(scenario_ids)))  # type: ignore[arg-type]
        return tuple(history[scenario_id])

    async def evaluate(scenario_id: int) -> dict[str, object]:
        evaluated.append(scenario_id)
        if scenario_id == 101:
            message = "semantic proposal failure"
            raise RuntimeError(message)
        history[scenario_id].append(_proposal_row(scenario_id, 502))
        return {
            "final_response": {
                "status": "success",
                "message": "done",
                "data": {
                    "modelParamProposalId": 502,
                    "scenarioId": scenario_id,
                    "scenarioGroupId": scenario_id + 1_000,
                    "eventId": None,
                    "proposalParameters": [{"parameterName": "GDP"}],
                },
            },
        }

    dependencies = runner.RunnerDependencies(
        load_context=_context,
        snapshot_proposal_rows=snapshot,
        evaluate_scenario=evaluate,
        fetch_proposal=lambda proposal_id: _proposal_row(102, int(proposal_id or 0)),
        failure_trace=lambda _exc: {},
    )

    evidence = asyncio.run(
        runner.run_campaign(
            _options(tmp_path, 101, 102),
            dependencies=dependencies,
        ),
    )

    assert evidence["status"] == "FAIL"
    assert evaluated == [101, 102]
    assert [attempt["status"] for attempt in evidence["attempts"]] == ["FAIL", "PASS"]
    assert evidence["selection"]["counts"]["attempted"] == 2
    assert evidence["selection"]["counts"]["succeeded"] == 1
    assert evidence["selection"]["counts"]["failed"] == 1


def test_structured_semantic_empty_is_abstained_with_complete_trace(tmp_path: Path) -> None:
    history = {101: [_proposal_row(101, 400, status="FAILED")]}

    def snapshot(_scenario_group_id: int, scenario_ids: object) -> tuple[dict[str, object], ...]:
        scenario_id = int(next(iter(scenario_ids)))  # type: ignore[arg-type]
        return tuple(history[scenario_id])

    async def evaluate(_scenario_id: int) -> dict[str, object]:
        raise runner.ModelParameterSemanticEmptyError(
            reason_code="ABSTAINED_INSUFFICIENT_EVIDENCE",
            stage="step1_5",
            title="파라미터로 반영할 변경 항목이 없습니다.",
            detail="시나리오 근거가 부족합니다.",
        )

    def failure_trace(_exc: BaseException) -> dict[str, object]:
        return {
            "failed_stage": "semantic abstention: step1_5",
            "semantic_empty": {
                "reason_code": "ABSTAINED_INSUFFICIENT_EVIDENCE",
                "stage": "step1_5",
                "message": "safe",
            },
            "semantic_stage_evidence": {
                "stage": "step1_5",
                "routing_tasks": [],
                "prompt": "MUST_NOT_BE_WRITTEN",
            },
            "step_summary": {"termination_stage": "Step1.5 종료"},
            "trace_mi_base_resource": {
                "source": "configured_fallback",
                "case_id": 15,
                "run_seq": 71,
                "workbook_sha256": {
                    "demand": "demand-sha256",
                    "supply": "supply-sha256",
                    "trade": "trade-sha256",
                },
            },
            "llm_calls": [
                {
                    "step": "Step1.5 routing selection",
                    "success": True,
                    "usage": {"total_tokens": 42},
                },
            ],
            "observability_complete": True,
            "partial_state_captured": True,
            "proposal_persisted": False,
        }

    evidence = asyncio.run(
        runner.run_campaign(
            _options(tmp_path, 101),
            dependencies=runner.RunnerDependencies(
                load_context=_context,
                snapshot_proposal_rows=snapshot,
                evaluate_scenario=evaluate,
                fetch_proposal=lambda _proposal_id: {},
                failure_trace=failure_trace,
            ),
        ),
    )

    assert evidence["status"] == "REVIEW"
    assert evidence["selection"]["counts"]["abstained"] == 1
    assert evidence["selection"]["counts"]["failed"] == 0
    attempt = evidence["attempts"][0]
    assert attempt["status"] == "ABSTAINED"
    assert attempt["semantic_empty"] == {
        "reason_code": "ABSTAINED_INSUFFICIENT_EVIDENCE",
        "stage": "step1_5",
        "message": "파라미터로 반영할 변경 항목이 없습니다.\n시나리오 근거가 부족합니다.",
        "structured": True,
        "observability_complete": True,
    }
    assert attempt["failure_trace"]["llm_calls"][0]["usage"]["total_tokens"] == 42
    assert attempt["failure_trace"]["trace_mi_base_resource"]["source"] == "configured_fallback"
    assert "MUST_NOT_BE_WRITTEN" not in _options(tmp_path, 101).evidence_path.read_text(encoding="utf-8")


def test_second_campaign_skips_proposed_row_created_by_first_campaign(tmp_path: Path) -> None:
    history: list[dict[str, object]] = []
    evaluated: list[int] = []

    async def evaluate(scenario_id: int) -> dict[str, object]:
        evaluated.append(scenario_id)
        history.append(_proposal_row(scenario_id, 777))
        return {
            "final_response": {
                "status": "success",
                "message": "done",
                "data": {
                    "modelParamProposalId": 777,
                    "scenarioId": scenario_id,
                    "scenarioGroupId": scenario_id + 1_000,
                    "eventId": None,
                    "proposalParameters": [{"parameterName": "GDP"}],
                },
            },
        }

    dependencies = runner.RunnerDependencies(
        load_context=_context,
        snapshot_proposal_rows=lambda _group_id, _scenario_ids: tuple(history),
        evaluate_scenario=evaluate,
        fetch_proposal=lambda _proposal_id: dict(history[-1]),
        failure_trace=lambda _exc: {},
    )

    first = asyncio.run(
        runner.run_campaign(
            _options(tmp_path, 101),
            dependencies=dependencies,
        ),
    )
    second_options = runner.ProposalOnlyOptions(
        execute=True,
        scenario_ids=(101,),
        scenario_group_id=None,
        capability_release=runner.BASELINE_CAPABILITY_RELEASE,
        evidence_path=tmp_path / "proposal-only-second.json",
    )
    second = asyncio.run(
        runner.run_campaign(
            second_options,
            dependencies=dependencies,
        ),
    )

    assert first["status"] == "PASS"
    assert second["status"] == "PASS"
    assert second["selection"]["covered_scenario_ids"] == [101]
    assert second["attempts"] == []
    assert evaluated == [101]


def test_release_replay_appends_one_new_row_and_pins_final_campaign_readback(
    tmp_path: Path,
) -> None:
    history = [_proposal_row(101, 700)]

    async def evaluate(scenario_id: int) -> dict[str, object]:
        history.append(_proposal_row(scenario_id, 701))
        return {
            "final_response": {
                "status": "success",
                "message": "done",
                "data": {
                    "modelParamProposalId": 701,
                    "scenarioId": scenario_id,
                    "scenarioGroupId": scenario_id + 1_000,
                    "eventId": None,
                    "proposalParameters": [{"parameterName": "GDP"}],
                },
            },
        }

    dependencies = runner.RunnerDependencies(
        load_context=_context,
        snapshot_proposal_rows=lambda _group_id, _scenario_ids: tuple(history),
        evaluate_scenario=evaluate,
        fetch_proposal=lambda proposal_id: next(
            dict(row) for row in history if row["model_param_proposal_id"] == proposal_id
        ),
        failure_trace=lambda _exc: {},
    )

    evidence = asyncio.run(
        runner.run_campaign(
            _options(tmp_path, 101, replay_covered=True),
            dependencies=dependencies,
        ),
    )

    assert evidence["status"] == "PASS"
    assert [row["model_param_proposal_id"] for row in history] == [700, 701]
    assert evidence["manifest"]["execution_policy_version"] == "release-replay-v1"
    assert evidence["safety"]["append_only_release_replay"] is True
    assert evidence["selection"]["preexisting_proposal_scenario_ids"] == [101]
    assert evidence["selection"]["campaign_proposal_ids_by_scenario"] == {"101": 701}
    assert [row["model_param_proposal_id"] for row in evidence["final_campaign_readback"]] == [701]


def test_success_integrity_rejects_empty_or_mismatched_persisted_payload() -> None:
    row = _proposal_row(101, 777)
    row["proposal_parameters"] = []

    errors = runner._success_integrity_errors(  # noqa: SLF001
        scenario_id=101,
        scenario_group_id=1_101,
        model_param_proposal_id=777,
        new_proposal_ids=(777,),
        proposal_row=row,
        readback_error=None,
        final_response={
            "status": "success",
            "data": {
                "modelParamProposalId": 777,
                "scenarioId": 101,
                "scenarioGroupId": 1_101,
                "eventId": None,
                "proposalParameters": [{"parameterName": "GDP"}],
            },
        },
        allowed_parameter_names={"GDP"},
    )

    assert "proposal DB row contains no proposal_parameters" in errors
    assert "proposal DB payload does not match the API response after excluding lutValue" in errors


def test_success_integrity_applies_persistence_precision_to_basecase_values() -> None:
    row = _proposal_row(101, 779)
    row["proposal_parameters"] = [
        {
            "parameterName": "PowerMix",
            "values": [
                {
                    "Country": "Japan",
                    "Year": 2026,
                    "basecaseValue": 0.03562,
                    "proposedValue": 0.04062525965932699,
                },
            ],
        },
    ]

    errors = runner._success_integrity_errors(  # noqa: SLF001
        scenario_id=101,
        scenario_group_id=1_101,
        model_param_proposal_id=779,
        new_proposal_ids=(779,),
        proposal_row=row,
        readback_error=None,
        final_response={
            "status": "success",
            "data": {
                "modelParamProposalId": 779,
                "scenarioId": 101,
                "scenarioGroupId": 1_101,
                "eventId": None,
                "proposalParameters": [
                    {
                        "parameterName": "PowerMix",
                        "values": [
                            {
                                "Country": "Japan",
                                "Year": 2026,
                                "basecaseValue": 0.03562525965932699,
                                "lutValue": 0.03562525965932699,
                                "proposedValue": 0.04062525965932699,
                            },
                        ],
                    },
                ],
            },
        },
        allowed_parameter_names={"PowerMix"},
    )

    assert errors == []


def test_success_integrity_tolerates_json_float_round_trip_noise() -> None:
    row = _proposal_row(101, 780)
    row["proposal_parameters"] = [
        {
            "parameterName": "PowerMix",
            "values": [
                {
                    "Country": "Japan",
                    "Year": 2026,
                    "basecaseValue": 0.11247,
                    "proposedValue": 0.11247403406730376,
                },
            ],
        },
    ]

    errors = runner._success_integrity_errors(  # noqa: SLF001
        scenario_id=101,
        scenario_group_id=1_101,
        model_param_proposal_id=780,
        new_proposal_ids=(780,),
        proposal_row=row,
        readback_error=None,
        final_response={
            "status": "success",
            "data": {
                "modelParamProposalId": 780,
                "scenarioId": 101,
                "scenarioGroupId": 1_101,
                "eventId": None,
                "proposalParameters": [
                    {
                        "parameterName": "PowerMix",
                        "values": [
                            {
                                "Country": "Japan",
                                "Year": 2026,
                                "basecaseValue": 0.11247403406730375,
                                "lutValue": 0.11247403406730375,
                                "proposedValue": 0.11247403406730375,
                            },
                        ],
                    },
                ],
            },
        },
        allowed_parameter_names={"PowerMix"},
    )

    assert errors == []


def test_success_integrity_rejects_material_proposed_value_difference() -> None:
    row = _proposal_row(101, 781)
    row["proposal_parameters"] = [
        {
            "parameterName": "GDP",
            "values": [{"Year": 2026, "proposedValue": 4.1}],
        },
    ]

    errors = runner._success_integrity_errors(  # noqa: SLF001
        scenario_id=101,
        scenario_group_id=1_101,
        model_param_proposal_id=781,
        new_proposal_ids=(781,),
        proposal_row=row,
        readback_error=None,
        final_response={
            "status": "success",
            "data": {
                "modelParamProposalId": 781,
                "scenarioId": 101,
                "scenarioGroupId": 1_101,
                "eventId": None,
                "proposalParameters": [
                    {
                        "parameterName": "GDP",
                        "values": [{"Year": 2026, "proposedValue": 4.2}],
                    },
                ],
            },
        },
        allowed_parameter_names={"GDP"},
    )

    assert "proposal DB payload does not match the API response after excluding lutValue" in errors


def test_success_integrity_rejects_response_identity_scope_and_persisted_lut_value() -> None:
    row = _proposal_row(101, 778)
    row["proposal_parameters"] = [
        {
            "parameterName": "ShippingCost",
            "values": [{"proposedValue": 1.0, "lutValue": 0.9}],
        },
    ]

    errors = runner._success_integrity_errors(  # noqa: SLF001
        scenario_id=101,
        scenario_group_id=1_101,
        model_param_proposal_id=778,
        new_proposal_ids=(778,),
        proposal_row=row,
        readback_error=None,
        final_response={
            "status": "failed",
            "data": {
                "modelParamProposalId": 778,
                "scenarioId": 999,
                "scenarioGroupId": 888,
                "eventId": 777,
                "proposalParameters": [{"parameterName": "ShippingCost", "values": [{"proposedValue": 1.0}]}],
            },
        },
        allowed_parameter_names={"GDP"},
    )

    assert any("status is not success" in error for error in errors)
    assert any("scenario ID mismatch" in error for error in errors)
    assert any("Scenario Group ID mismatch" in error for error in errors)
    assert any("eventId must be present and null" in error for error in errors)
    assert "proposal DB payload must not persist lutValue" in errors
    assert any("escaped the preflight runtime candidates" in error for error in errors)


def test_failure_retains_trace_persisted_id_readback_and_never_retries(tmp_path: Path) -> None:
    class ProposalFailureError(RuntimeError):
        pass

    snapshots = iter(
        (
            (_proposal_row(101, 600, status="FAILED"),),
            (_proposal_row(101, 600, status="FAILED"),),
            (_proposal_row(101, 600, status="FAILED"),),
            (
                _proposal_row(101, 600, status="FAILED"),
                _proposal_row(101, 601),
            ),
        ),
    )
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
        snapshot_proposal_rows=lambda _group_id, _scenario_ids: next(snapshots),
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
    snapshots = iter(
        (
            (_proposal_row(101, 700, status="FAILED"),),
            (_proposal_row(101, 700, status="FAILED"),),
            (_proposal_row(101, 700, status="FAILED"),),
            (
                _proposal_row(101, 700, status="FAILED"),
                _proposal_row(101, 701),
            ),
        ),
    )
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
        snapshot_proposal_rows=lambda _group_id, _scenario_ids: next(snapshots),
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


def test_runtime_evaluator_checks_frozen_graph_context_before_persistence() -> None:
    dependencies = runner._runtime_dependencies()  # noqa: SLF001
    source = inspect.getsource(runner._evaluate_scenario)  # noqa: SLF001

    assert dependencies.evaluate_scenario_with_context is not None
    assert source.index('raw_state.get("scenario_context")') < source.index("_serialize_output_with_persistence_trace")
    assert source.index("proposal pre-persistence quality gate failed") < source.index(
        "_serialize_output_with_persistence_trace",
    )


def test_frozen_graph_context_ignores_only_request_local_mi_base_pin() -> None:
    expected = _context(101)
    actual = json.loads(json.dumps(expected))
    actual["mi_base_case_id"] = 15

    assert evaluate_proposals._matches_frozen_graph_context(actual, expected)  # noqa: SLF001

    actual["scenario"]["title"] = "mutated title"  # type: ignore[index]
    assert not evaluate_proposals._matches_frozen_graph_context(actual, expected)  # noqa: SLF001


def test_post_graph_trace_allows_only_mi_base_transport_source_change() -> None:
    graph_identity = {
        "source": "mi_base",
        "case_id": 15,
        "run_seq": 71,
        "workbook_sha256": {"demand": "a", "supply": "b", "trade": "c"},
    }
    cache_identity = {
        **graph_identity,
        "source": "verified_cache",
    }

    assert evaluate_proposals._same_mi_base_content_identity(  # noqa: SLF001
        graph_identity,
        cache_identity,
    )

    cache_identity["workbook_sha256"] = {"demand": "changed", "supply": "b", "trade": "c"}
    assert not evaluate_proposals._same_mi_base_content_identity(  # noqa: SLF001
        graph_identity,
        cache_identity,
    )
