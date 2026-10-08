# Copyright (c) 2026 SK Innovation E&S.
# ruff: noqa: S101

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from tests.manual.model_parameter_agent.backfill_mi_base_trace_evidence import (
    BACKFILL_KIND,
    build_backfilled_evidence,
)
from tests.manual.model_parameter_agent.collect_existing_representative_trios import (
    RECENCY_POLICY,
    SELECTION_POLICY,
    build_plan as build_existing_plan,
    build_report as build_existing_report,
    render_markdown as render_existing_markdown,
    validate_testset as validate_existing_testset,
)
from tests.manual.model_parameter_agent.evaluate_representative_trios import (
    EXPECTED_CATALOG_CHECKSUM,
    attach_diagnostic_executions,
    attach_final_cohort_trio_analysis,
    build_final_cohort_trio_analysis,
    build_reusable_testset,
    build_selection_plan,
    evaluate_execution,
    expanded_event_cohort_checks,
    merge_execution_evidence,
    reconcile_final_history,
    regenerated_event_pool_checks,
    render_final_cohort_trio_report,
    render_markdown,
    require_mi_base_fallback_mode,
    select_representative_trio,
    validate_immutable_testset,
)


REUSABLE_TESTSET = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "model_parameter_agent"
    / "v4_1_2_expanded_event_cohort_representative_trio_20_groups_20261007.json"
)
REPRESENTATIVE_PLAN = (
    Path(__file__).resolve().parents[1]
    / "reports"
    / "model_parameter_agent"
    / "v4.1.2-expanded-event-cohort-trio-20261007"
    / "representative-trio-plan.json"
)
EXISTING_LATEST_TESTSET = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "model_parameter_agent"
    / "v4_1_2_existing_latest_distinct_representative_trio_40_groups_20261007.json"
)


def test_existing_read_only_report_exposes_proposed_value_kpi_without_fabricating_result() -> None:
    report = build_existing_report(
        {"counts": {}, "release_contract": {}},
        {"manifest": {"runtime_allowlist": []}, "preflight": []},
        {"groups": [], "pass": True, "checks": {}},
        testset_path=Path("frozen-testset.json"),
        testset_sha256="fixture-sha",
    )

    kpis = report["kpis"]
    assert report["read_only_scope"] == {
        "definition": (
            "기존 Group/Scenario와 Proposal history를 조회하고 release/구조 gate, runtime candidate, "
            "write guard 상태만 계산한 수집·preflight 보고서"
        ),
        "database_reads": True,
        "proposal_logic_executed": False,
        "llm_invoked": False,
        "object_storage_or_mi_base_bootstrapped": False,
        "application_data_mutated": False,
    }
    assert "실제 Proposal 품질이나 성공을 뜻하지 않음" in report["read_only_kpi_interpretation"][
        "pass_meaning"
    ]
    assert "실제 제안 Parameter 종류와 Scenario별 제안값 차이" in report[
        "read_only_kpi_interpretation"
    ]["not_evaluated"]
    assert kpis["same_types_with_any_different_values_status"] == "NOT_MEASURED_READ_ONLY"
    assert kpis["same_types_with_any_different_values_group_count"] is None
    assert kpis["same_types_with_any_different_values_applicable_group_count"] is None
    assert kpis["same_types_with_any_different_values_rate_percent"] is None

    markdown = render_existing_markdown(report)
    assert "같은 종류 + Scenario별 다른 제안값" in markdown
    assert "N/A (`NOT_MEASURED_READ_ONLY`)" in markdown
    assert "Proposal 로직을 실행하지 않았으므로" in markdown
    assert "Read-only 수집 리포트" in markdown
    assert "Proposal/LLM 실행" in markdown
    assert "Read-only KPI 의미 및 해석 방법" in markdown
    assert "실제 Proposal 성공이나 제안값 품질 통과를 의미하지 않습니다" in markdown



def _row(
    scenario_id: int,
    *,
    role: str | None,
    baseline: bool,
    pressure_band: str,
) -> dict[str, Any]:
    return {
        "scenarioId": scenario_id,
        "displayOrder": scenario_id,
        "title": f"Scenario {scenario_id}",
        "scenarioRole": role,
        "baselineYn": "Y" if baseline else "N",
        "pressureBand": pressure_band,
        "cells": {"d1": f"d1_v{scenario_id}"},
    }


def _preflight(scenario_id: int, parameters: list[str]) -> dict[str, Any]:
    return {
        "scenario_id": scenario_id,
        "status": "PASS",
        "runtime_parameter_names": parameters,
        "uncovered_guard": {"eligible": True},
    }


def test_select_representative_trio_preserves_roles_then_parameter_consistency() -> None:
    rows = [
        _row(1, role="floor", baseline=True, pressure_band="strong_bearish"),
        _row(2, role="mixed", baseline=False, pressure_band="balanced"),
        _row(3, role="ceiling", baseline=False, pressure_band="strong_bullish"),
        _row(4, role=None, baseline=False, pressure_band="bearish"),
    ]
    preflight = {
        1: _preflight(1, ["Temperature"]),
        2: _preflight(2, ["Temperature"]),
        3: _preflight(3, ["Temperature"]),
        4: _preflight(4, ["GDP"]),
    }

    selected, diagnostics = select_representative_trio(rows, preflight)

    assert [_row["scenarioId"] for _row in selected] == [1, 2, 3]
    assert diagnostics["required_role_filter_applied"] is True
    assert diagnostics["parameter_sets_identical_in_preflight"] is True
    assert diagnostics["common_runtime_parameter_names"] == ["Temperature"]


def test_select_representative_trio_keeps_three_representatives_for_coverage_limit() -> None:
    rows = [
        _row(1, role="floor", baseline=True, pressure_band="strong_bearish"),
        _row(2, role="mixed", baseline=False, pressure_band="balanced"),
        _row(3, role="ceiling", baseline=False, pressure_band="strong_bullish"),
        _row(4, role=None, baseline=False, pressure_band="bearish"),
    ]
    preflight = {
        scenario_id: {
            "scenario_id": scenario_id,
            "status": "SKIP",
            "runtime_parameter_names": [],
            "skip_reasons": ["no runtime-allowed parameter candidate"],
            "uncovered_guard": {"eligible": False},
        }
        for scenario_id in range(1, 5)
    }

    selected, diagnostics = select_representative_trio(rows, preflight)

    assert [_row["scenarioId"] for _row in selected] == [1, 2, 3]
    assert diagnostics["selection_mode"] == "representative-coverage-limit"
    assert diagnostics["coverage_limit"] is True
    assert diagnostics["parameter_sets_identical_in_preflight"] is False


def test_select_representative_trio_can_ignore_existing_proposal_history() -> None:
    rows = [
        _row(1, role="floor", baseline=True, pressure_band="strong_bearish"),
        _row(2, role="mixed", baseline=False, pressure_band="balanced"),
        _row(3, role="ceiling", baseline=False, pressure_band="strong_bullish"),
    ]
    preflight = {
        scenario_id: {
            **_preflight(scenario_id, ["Temperature"]),
            "uncovered_guard": {"eligible": False, "decision": "SKIP"},
        }
        for scenario_id in range(1, 4)
    }

    selected, diagnostics = select_representative_trio(
        rows,
        preflight,
        require_uncovered=False,
    )

    assert [row["scenarioId"] for row in selected] == [1, 2, 3]
    assert diagnostics["runtime_capable_scenario_count"] == 3
    assert diagnostics["current_write_eligible_scenario_count"] == 0
    assert diagnostics["selection_eligibility_policy"] == "runtime-capable-independent-of-history"


def test_existing_pool_plan_gates_actual_preflight_release_identity() -> None:
    rows = [
        _row(1, role="floor", baseline=True, pressure_band="strong_bearish"),
        _row(2, role="mixed", baseline=False, pressure_band="balanced"),
        _row(3, role="ceiling", baseline=False, pressure_band="strong_bullish"),
    ]
    inventory = {
        "pass": True,
        "generated_at": "2026-10-07T00:00:00+00:00",
        "max_group_count": 50,
        "selected_scenario_ids": [1, 2, 3],
        "groups": [
            {
                "scenario_group_id": 500,
                "title": "Existing Group",
                "modified_at": "2026-10-07T00:00:00",
                "created_at": "2026-10-07T00:00:00",
                "event_signature": [100],
                "events": [
                    {
                        "mi_event_id": 100,
                        "event_type_l2_id": 1,
                        "event_type_l2_code": "type_1",
                    },
                ],
                "scenario_count": 3,
                "scenarios": rows,
                "group_contract": {
                    "api_version": "v4",
                    "generation_strategy": "multi_event_model_lever_dimensions",
                    "impact_catalog_version": "v4.1",
                    "impact_catalog_checksum": EXPECTED_CATALOG_CHECKSUM,
                },
                "structural_checks": {"valid": True},
            },
        ],
    }
    preflight = {
        "mode": "read-only",
        "status": "PASS",
        "attempts": [],
        "finished_at": "2026-10-07T00:01:00+00:00",
        "manifest": {
            "capability_contract": {
                "catalog_version": "v4.1",
                "catalog_checksum": EXPECTED_CATALOG_CHECKSUM,
            },
            "resource": {"proposal_flow_release": "v4.1.3"},
        },
        "safety": {"confirmation_invoked": False, "callback_invoked": False},
        "selection": {"counts": {"discovered": 3, "preflight_fail": 0, "hard_stop": 0}},
        "preflight": [_preflight(scenario_id, ["Temperature"]) for scenario_id in (1, 2, 3)],
    }

    plan = build_existing_plan(inventory, preflight)

    assert plan["pass"] is True
    assert plan["checks"]["runner_mode_read_only"] is True
    assert plan["checks"]["preflight_catalog_release_matches"] is True
    assert plan["checks"]["preflight_proposal_flow_release_matches"] is True
    mismatched = json.loads(json.dumps(preflight))
    mismatched["manifest"]["resource"]["proposal_flow_release"] = "v4.1.1"
    mismatch_plan = build_existing_plan(inventory, mismatched)
    assert mismatch_plan["checks"]["preflight_proposal_flow_release_matches"] is False
    assert mismatch_plan["pass"] is False


def test_expanded_event_cohort_checks_require_20_disjoint_events_and_add_only_policy() -> None:
    baseline = list(range(1, 21))
    expanded = list(range(101, 121))

    checks = expanded_event_cohort_checks(
        current_event_ids=expanded,
        baseline_event_ids=baseline,
        summary_event_ids=expanded,
        selection_policy="expanded_event_cohort/add-only",
        creation_policy="add-only-preserve-existing",
    )

    assert all(checks.values())


def test_expanded_event_cohort_checks_reject_overlap() -> None:
    baseline = list(range(1, 21))
    expanded = [1, *range(102, 121)]

    checks = expanded_event_cohort_checks(
        current_event_ids=expanded,
        baseline_event_ids=baseline,
        summary_event_ids=expanded,
        selection_policy="expanded_event_cohort/add-only",
        creation_policy="add-only-preserve-existing",
    )

    assert checks["expanded_event_ids_disjoint_from_baseline"] is False


def test_selection_plan_gates_actual_read_only_release_and_scope(tmp_path: Path) -> None:
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    rows = [
        _row(1, role="floor", baseline=False, pressure_band="strong_bearish"),
        _row(2, role="mixed", baseline=True, pressure_band="balanced"),
        _row(3, role="ceiling", baseline=False, pressure_band="strong_bullish"),
    ]
    (case_dir / "final_group.json").write_text(
        json.dumps(
            {
                "scenarioGroup": {
                    "scenarioGroupId": 500,
                    "apiVersion": "v4",
                    "generationStrategy": "multi_event_model_lever_dimensions",
                    "impactCatalogVersion": "v4.1",
                    "impactCatalogChecksum": EXPECTED_CATALOG_CHECKSUM,
                    "status": "created",
                    "stage": "completed",
                    "delYn": "N",
                    "miEventId": 100,
                    "eventTypeL2Id": 1,
                    "scenarioCount": 3,
                    "parameterMappingReady": True,
                    "dimensionDefinitions": [{}, {}, {}],
                },
                "table": {"rows": rows},
            },
        ),
        encoding="utf-8",
    )
    summary_path = tmp_path / "campaign_summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "selection_policy": "expanded_event_cohort/add-only",
                "creation_policy": "add-only-preserve-existing",
                "expanded_event_ids": [100],
                "counts": {"requested_group_count": 1},
                "cases": [
                    {
                        "result": "completed",
                        "cohort_order": 1,
                        "event_type_id": 1,
                        "event_type_code": "type_1",
                        "event_id": 100,
                        "artifact_dir": str(case_dir),
                    },
                ],
            },
        ),
        encoding="utf-8",
    )
    preflight = {
        "mode": "read-only",
        "status": "PASS",
        "attempts": [],
        "manifest": {
            "capability_contract": {
                "catalog_version": "v4.1",
                "catalog_checksum": EXPECTED_CATALOG_CHECKSUM,
            },
            "resource": {
                "proposal_flow_release": "v4.1.3",
                "proposal_capability_release_id": "extend16-v8",
            },
        },
        "safety": {"confirmation_invoked": False, "callback_invoked": False},
        "preflight": [_preflight(scenario_id, ["Temperature"]) for scenario_id in (1, 2, 3)],
    }
    preflight_path = tmp_path / "preflight.json"
    preflight_path.write_text(json.dumps(preflight), encoding="utf-8")

    plan = build_selection_plan(
        scenario_summary_path=summary_path,
        preflight_path=preflight_path,
    )

    assert plan["structural_checks"]["preflight_scope_matches_all_generated_scenarios"] is True
    assert plan["structural_checks"]["preflight_proposal_flow_release_exact"] is True
    preflight["manifest"]["resource"]["proposal_flow_release"] = "v4.1.1"
    preflight_path.write_text(json.dumps(preflight), encoding="utf-8")
    mismatched = build_selection_plan(
        scenario_summary_path=summary_path,
        preflight_path=preflight_path,
    )
    assert mismatched["structural_checks"]["preflight_proposal_flow_release_exact"] is False


def test_regenerated_event_pool_checks_require_same_40_events_and_preserved_groups() -> None:
    event_ids = list(range(100, 140))
    original_group_ids = list(range(1, 41))
    new_group_ids = list(range(501, 541))

    checks = regenerated_event_pool_checks(
        current_event_ids=event_ids,
        source_event_ids=event_ids,
        original_group_ids=original_group_ids,
        current_group_ids=new_group_ids,
        selection_policy="existing_event_pool/add-only-regenerated-scenarios",
        creation_policy="add-only-preserve-existing",
        scenario_summary={
            "pass": True,
            "hard_gates": {"original_groups_preserved": True, "release_contract_exact": True},
        },
    )

    assert all(checks.values())


def test_regenerated_event_pool_checks_reject_changed_event_identity() -> None:
    event_ids = list(range(100, 140))
    changed_event_ids = [*event_ids[:-1], 999]

    checks = regenerated_event_pool_checks(
        current_event_ids=changed_event_ids,
        source_event_ids=event_ids,
        original_group_ids=list(range(1, 41)),
        current_group_ids=list(range(501, 541)),
        selection_policy="existing_event_pool/add-only-regenerated-scenarios",
        creation_policy="add-only-preserve-existing",
        scenario_summary={
            "pass": True,
            "hard_gates": {"original_groups_preserved": True},
        },
    )

    assert checks["source_event_pool_reused_exactly"] is False


def _attempt(
    scenario_id: int,
    group_id: int,
    proposed_value: float,
) -> dict[str, Any]:
    return {
        "scenario_id": scenario_id,
        "scenario_group_id": group_id,
        "status": "PASS",
        "elapsed_seconds": float(scenario_id),
        "model_param_proposal_id": 1000 + scenario_id,
        "proposal_db_row": {
            "scenario_id": scenario_id,
            "scenario_group_id": group_id,
            "mi_event_id": None,
            "status": "PROPOSED",
            "callback_status": "SKIPPED",
            "proposal_parameters": [
                {
                    "parameterName": "Temperature",
                    "values": [
                        {
                            "Country": "Korea",
                            "Year": 2027,
                            "Month": 1,
                            "basecaseValue": 1.0,
                            "proposedValue": proposed_value,
                            "rationale": "test",
                        },
                    ],
                },
            ],
        },
        "evaluation": {
            "trace_mi_base_resource": {
                "source": "configured_fallback",
                "case_id": 15,
                "run_seq": 71,
                "workbook_sha256": {
                    "demand": "demand-sha",
                    "supply": "supply-sha",
                    "trade": "trade-sha",
                },
            },
            "llm_calls": [
                {
                    "retry_count": 0,
                    "usage": {"total_tokens": 100},
                },
            ],
        },
    }


def _full_plan_and_execution() -> tuple[dict[str, Any], dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    attempts: list[dict[str, Any]] = []
    selected_ids: list[int] = []
    for group_offset in range(20):
        group_id = 500 + group_offset
        scenario_ids = [2000 + group_offset * 3 + index for index in range(3)]
        selected_ids.extend(scenario_ids)
        groups.append(
            {
                "scenario_group_id": group_id,
                "event_type_id": group_offset + 1,
                "event_type_code": f"type_{group_offset + 1}",
                "selected_scenarios": [
                    {
                        "scenario_id": scenario_id,
                        "title": f"Scenario {scenario_id}",
                        "proposal_eligible": True,
                        "runtime_parameter_names": ["Temperature"],
                    }
                    for scenario_id in scenario_ids
                ],
            },
        )
        attempts.extend(
            _attempt(scenario_id, group_id, proposed_value=0.8 + index * 0.1)
            for index, scenario_id in enumerate(scenario_ids)
        )
    plan = {
        "pass": True,
        "selected_scenario_ids": selected_ids,
        "counts": {"groups_with_preflight_identical_parameter_sets": 20},
        "groups": groups,
    }
    execution = {
        "status": "PASS",
        "manifest": {
            "capability_contract": {
                "catalog_version": "v4.1",
                "catalog_checksum": EXPECTED_CATALOG_CHECKSUM,
            },
            "resource": {"proposal_flow_release": "v4.1.3"},
        },
        "safety": {
            "confirmation_invoked": False,
            "callback_invoked": False,
            "automatic_retry": False,
        },
        "attempts": attempts,
    }
    return plan, execution


def test_evaluate_execution_distinguishes_type_and_exact_slot_value_variation() -> None:
    groups = []
    attempts = []
    selected_ids: list[int] = []
    for group_offset in range(20):
        group_id = 500 + group_offset
        scenario_ids = [2000 + group_offset * 3 + index for index in range(3)]
        selected_ids.extend(scenario_ids)
        groups.append(
            {
                "scenario_group_id": group_id,
                "event_type_id": group_offset + 1,
                "event_type_code": f"type_{group_offset + 1}",
                "selected_scenarios": [
                    {
                        "scenario_id": scenario_id,
                        "title": f"Scenario {scenario_id}",
                        "runtime_parameter_names": ["Temperature"],
                    }
                    for scenario_id in scenario_ids
                ],
            },
        )
        attempts.extend(
            _attempt(scenario_id, group_id, proposed_value=0.8 + index * 0.1)
            for index, scenario_id in enumerate(scenario_ids)
        )

    plan = {
        "pass": True,
        "selected_scenario_ids": selected_ids,
        "counts": {"groups_with_preflight_identical_parameter_sets": 20},
        "groups": groups,
    }
    execution = {
        "status": "PASS",
        "manifest": {
            "capability_contract": {
                "catalog_version": "v4.1",
                "catalog_checksum": EXPECTED_CATALOG_CHECKSUM,
            },
            "resource": {"proposal_flow_release": "v4.1.3"},
        },
        "safety": {
            "confirmation_invoked": False,
            "callback_invoked": False,
            "automatic_retry": False,
        },
        "attempts": attempts,
    }

    report = evaluate_execution(plan, execution)

    assert report["operational_pass"] is True
    assert report["kpis"]["successful_proposal_count"] == 60
    assert report["kpis"]["preflight_identical_parameter_type_group_count"] == 20
    assert report["kpis"]["preflight_parameter_type_consistency_rate_percent"] == 100.0
    assert report["kpis"]["identical_parameter_type_group_count"] == 20
    assert report["kpis"]["same_types_with_any_different_values_group_count"] == 20
    assert report["kpis"]["same_types_with_all_three_scenario_values_distinct_group_count"] == 20
    assert report["kpis"]["groups_with_different_values_on_exact_common_slots"] == 20
    assert report["kpis"]["identity_error_count"] == 0
    assert report["kpis"]["total_tokens"] == 6000


def test_value_differentiation_ignores_value_cell_order_only_changes() -> None:
    plan = {
        "pass": True,
        "counts": {"groups_with_preflight_identical_parameter_sets": 1},
        "groups": [
            {
                "scenario_group_id": 500,
                "event_type_id": 1,
                "event_type_code": "type_1",
                "selected_scenarios": [
                    {
                        "scenario_id": scenario_id,
                        "title": f"Scenario {scenario_id}",
                        "proposal_eligible": True,
                        "runtime_parameter_names": ["Temperature"],
                    }
                    for scenario_id in (1, 2, 3)
                ],
            },
        ],
    }
    attempts = [_attempt(scenario_id, 500, 1.0) for scenario_id in (1, 2, 3)]
    forward = [
        {"Country": "Korea", "Year": 2027, "proposedValue": 1.0},
        {"Country": "Japan", "Year": 2027, "proposedValue": 2.0},
    ]
    reverse = list(reversed(forward))
    for attempt, values in zip(attempts, (forward, reverse, forward), strict=True):
        attempt["proposal_db_row"]["proposal_parameters"][0]["values"] = values
    execution = {
        "status": "PASS",
        "manifest": {
            "capability_contract": {
                "catalog_version": "v4.1",
                "catalog_checksum": EXPECTED_CATALOG_CHECKSUM,
            },
            "resource": {"proposal_flow_release": "v4.1.3"},
        },
        "safety": {
            "confirmation_invoked": False,
            "callback_invoked": False,
            "automatic_retry": False,
        },
        "attempts": attempts,
    }

    report = evaluate_execution(plan, execution)

    assert report["groups"][0]["actual_parameter_sets_identical"] is True
    assert report["groups"][0]["any_parameter_value_variation"] is False
    assert report["groups"][0]["all_three_scenario_value_signatures_distinct"] is False
    assert report["groups"][0]["exact_common_slots_with_different_values"] == 0


def test_main_scenario_value_kpi_requires_all_three_signatures_to_differ() -> None:
    plan = {
        "pass": True,
        "counts": {"groups_with_preflight_identical_parameter_sets": 1},
        "groups": [
            {
                "scenario_group_id": 500,
                "event_type_id": 1,
                "event_type_code": "type_1",
                "selected_scenarios": [
                    {
                        "scenario_id": scenario_id,
                        "proposal_eligible": True,
                        "runtime_parameter_names": ["Temperature"],
                    }
                    for scenario_id in (1, 2, 3)
                ],
            },
        ],
    }
    attempts = [
        _attempt(1, 500, 1.0),
        _attempt(2, 500, 1.0),
        _attempt(3, 500, 2.0),
    ]
    execution = {
        "status": "PASS",
        "manifest": {
            "capability_contract": {
                "catalog_version": "v4.1",
                "catalog_checksum": EXPECTED_CATALOG_CHECKSUM,
            },
            "resource": {"proposal_flow_release": "v4.1.3"},
        },
        "safety": {
            "confirmation_invoked": False,
            "callback_invoked": False,
            "automatic_retry": False,
        },
        "attempts": attempts,
    }

    report = evaluate_execution(plan, execution)

    assert report["kpis"]["same_types_with_any_different_values_group_count"] == 1
    assert report["kpis"]["same_types_with_all_three_scenario_values_distinct_group_count"] == 0
    assert report["groups"][0]["ideal_same_types_different_values"] is False


def test_merge_execution_evidence_combines_non_overlapping_release_matched_attempts() -> None:
    manifest = {
        "capability_release": "extend16-v8",
        "capability_contract": {
            "catalog_version": "v4.1",
            "catalog_checksum": EXPECTED_CATALOG_CHECKSUM,
        },
        "resource": {
            "release_id": "new-bc-v7",
            "contract_sha256": "contract",
            "proposal_capability_sha256": "capability",
            "proposal_flow_release": "v4.1.3",
        },
    }
    left = {
        "status": "PASS",
        "manifest": manifest,
        "safety": {},
        "attempts": [{"scenario_id": 1, "status": "PASS"}],
    }
    right = {
        "status": "FAIL",
        "manifest": {
            **manifest,
            "mi_base_fallback_policy": {"active_case_unavailable_mode": "configured_fallback"},
        },
        "safety": {},
        "attempts": [{"scenario_id": 2, "status": "FAIL"}],
    }

    merged = merge_execution_evidence((("left.json", left), ("right.json", right)))

    assert merged["status"] == "FAIL"
    assert [attempt["scenario_id"] for attempt in merged["attempts"]] == [1, 2]
    assert merged["merge_checks"]["release_identity_consistent"] is True
    assert merged["manifest"]["mi_base_fallback_policy"] == {
        "active_case_unavailable_mode": "configured_fallback",
    }


def test_merge_execution_evidence_rejects_duplicate_scenario_attempt() -> None:
    execution = {
        "status": "PASS",
        "manifest": {
            "capability_release": "extend16-v8",
            "capability_contract": {
                "catalog_version": "v4.1",
                "catalog_checksum": EXPECTED_CATALOG_CHECKSUM,
            },
            "resource": {"proposal_flow_release": "v4.1.3"},
        },
        "attempts": [{"scenario_id": 1, "status": "PASS"}],
    }

    with pytest.raises(ValueError, match="duplicate Scenario attempt"):
        merge_execution_evidence((("first.json", execution), ("second.json", execution)))


def test_post_fix_evidence_explicitly_replaces_attempt_and_keeps_audit() -> None:
    manifest = {
        "capability_release": "extend16-v8",
        "capability_contract": {
            "catalog_version": "v4.1",
            "catalog_checksum": EXPECTED_CATALOG_CHECKSUM,
        },
        "resource": {
            "release_id": "new-bc-v7",
            "contract_sha256": "contract",
            "proposal_capability_sha256": "capability",
            "proposal_flow_release": "v4.1.3",
        },
    }
    baseline = {
        "status": "REVIEW",
        "manifest": manifest,
        "attempts": [
            {
                "scenario_id": 1,
                "status": "ABSTAINED",
                "failed_stage": "semantic abstention: step1_5",
                "semantic_empty": {"stage": "step1_5"},
            },
        ],
    }
    post_fix = {
        "status": "PASS",
        "manifest": manifest,
        "attempts": [{"scenario_id": 1, "status": "PASS"}],
    }

    merged = merge_execution_evidence(
        (("baseline.json", baseline),),
        post_fix_sources=(("post-fix.json", post_fix),),
        post_fix_reason="trace 보강 후 동일 테스트셋 재검증",
    )

    assert merged["status"] == "PASS"
    assert merged["attempts"] == [{"scenario_id": 1, "status": "PASS"}]
    assert merged["post_fix_replacements"] == [
        {
            "scenario_id": 1,
            "reason": "trace 보강 후 동일 테스트셋 재검증",
            "superseded_source": "baseline.json",
            "superseded_status": "ABSTAINED",
            "superseded_failed_stage": "semantic abstention: step1_5",
            "superseded_semantic_empty": {"stage": "step1_5"},
            "replacement_source": "post-fix.json",
            "replacement_status": "PASS",
        },
    ]
    assert merged["post_fix_comparison"] == {
        "same_attempt_scope": True,
        "baseline_scenario_ids": [1],
        "final_scenario_ids": [1],
        "baseline": {
            "attempt_count": 1,
            "successful_proposal_count": 0,
            "success_rate_percent": 0.0,
            "semantic_abstention_count": 1,
            "other_failure_count": 0,
            "structured_semantic_abstention_count": 0,
            "semantic_trace_complete_count": 0,
            "semantic_trace_missing_count": 1,
        },
        "final": {
            "attempt_count": 1,
            "successful_proposal_count": 1,
            "success_rate_percent": 100.0,
            "semantic_abstention_count": 0,
            "other_failure_count": 0,
            "structured_semantic_abstention_count": 0,
            "semantic_trace_complete_count": 0,
            "semantic_trace_missing_count": 0,
        },
        "delta": {
            "successful_proposal_count": 1.0,
            "success_rate_percent": 100.0,
            "semantic_abstention_count": -1.0,
            "other_failure_count": 0.0,
            "structured_semantic_abstention_count": 0.0,
            "semantic_trace_complete_count": 0.0,
            "semantic_trace_missing_count": -1.0,
        },
    }


def test_post_fix_evidence_requires_reason() -> None:
    execution = {
        "status": "REVIEW",
        "manifest": {
            "capability_release": "extend16-v8",
            "capability_contract": {
                "catalog_version": "v4.1",
                "catalog_checksum": EXPECTED_CATALOG_CHECKSUM,
            },
            "resource": {"proposal_flow_release": "v4.1.3"},
        },
        "attempts": [{"scenario_id": 1, "status": "ABSTAINED"}],
    }

    with pytest.raises(ValueError, match="post-fix-reason"):
        merge_execution_evidence(
            (("baseline.json", execution),),
            post_fix_sources=(("post-fix.json", execution),),
        )


def test_expected_mi_base_fallback_mode_is_a_hard_report_gate() -> None:
    plan, execution = _full_plan_and_execution()
    execution["execution_sources"] = [
        {
            "source": "baseline.json",
            "phase": "baseline",
            "mi_base_fallback_policy": {
                "active_case_unavailable_mode": "verified_cache",
            },
        },
    ]
    report = require_mi_base_fallback_mode(
        evaluate_execution(plan, execution),
        execution,
        expected_mode="configured_fallback",
    )

    assert report["mi_base_fallback_expectation"]["pass"] is False
    assert report["operational_checks"]["mi_base_fallback_mode_matches_requested"] is False
    assert report["operational_pass"] is False
    assert report["verdict"] == "FAIL"


def test_expected_mi_base_fallback_mode_requires_complete_matching_runtime_trace() -> None:
    plan, execution = _full_plan_and_execution()
    execution["manifest"]["mi_base_fallback_policy"] = {
        "active_case_unavailable_mode": "configured_fallback",
    }
    execution["execution_sources"] = [
        {
            "source": "execution.json",
            "phase": "final",
            "mi_base_fallback_policy": {
                "active_case_unavailable_mode": "configured_fallback",
            },
        },
    ]

    report = require_mi_base_fallback_mode(
        evaluate_execution(plan, execution),
        execution,
        expected_mode="configured_fallback",
    )

    assert report["mi_base_fallback_expectation"]["trace_complete"] is True
    assert report["mi_base_fallback_expectation"]["trace_source_matches"] is True
    assert report["mi_base_fallback_expectation"]["trace_identity_consistent"] is True
    assert report["mi_base_fallback_expectation"]["pass"] is True
    assert report["operational_pass"] is True


def test_authorized_mi_base_trace_backfill_is_audited_and_not_reported_as_direct() -> None:
    plan = {
        "pass": True,
        "counts": {"groups_with_preflight_identical_parameter_sets": 1},
        "groups": [
            {
                "scenario_group_id": 500,
                "event_type_id": 1,
                "event_type_code": "type_1",
                "selected_scenarios": [
                    {
                        "scenario_id": scenario_id,
                        "proposal_eligible": True,
                        "runtime_parameter_names": ["Temperature"],
                    }
                    for scenario_id in (1, 2, 3)
                ],
            },
        ],
    }
    abstained = {
        "scenario_id": 2,
        "scenario_group_id": 500,
        "status": "ABSTAINED",
        "execution_attempt_count": 1,
        "elapsed_seconds": 1.0,
        "failed_stage": "semantic abstention: step2",
        "semantic_empty": {
            "reason_code": "ABSTAINED_INSUFFICIENT_EVIDENCE",
            "stage": "step2",
            "structured": True,
            "observability_complete": True,
        },
        "failure_trace": {
            "partial_state_captured": True,
            "mapping_trace_captured": True,
            "observability_complete": True,
            "semantic_stage_evidence": {},
            "step_summary": {},
            "llm_calls": [],
        },
        "proposal_persisted": False,
        "new_proposal_ids": [],
    }
    execution = {
        "runner": "model_parameter_proposal_only",
        "mode": "execute",
        "status": "REVIEW",
        "manifest": {
            "capability_contract": {
                "catalog_version": "v4.1",
                "catalog_checksum": EXPECTED_CATALOG_CHECKSUM,
            },
            "resource": {"proposal_flow_release": "v4.1.3"},
            "required_mi_base_fallback_mode": "configured_fallback",
            "mi_base_fallback_policy": {
                "active_case_unavailable_mode": "configured_fallback",
            },
        },
        "safety": {
            "sequential": True,
            "max_attempts_per_scenario": 1,
            "automatic_retry": False,
            "confirmation_invoked": False,
            "callback_invoked": False,
        },
        "attempts": [
            _attempt(1, 500, 1.0),
            abstained,
            _attempt(3, 500, 2.0),
        ],
    }
    for direct_attempt in (execution["attempts"][0], execution["attempts"][2]):
        direct_attempt["evaluation"]["trace_mi_base_resource"]["workbook_sha256"] = {
            "demand": "d" * 64,
            "supply": "s" * 64,
            "trade": "t" * 64,
        }
    derived = build_backfilled_evidence(
        execution,
        source_path="original.json",
        source_sha256="a" * 64,
        authorization_note="사용자 요청에 따른 실행 증적 소급 보정",
        expected_attempt_count=3,
        expected_direct_count=2,
        expected_backfill_count=1,
        performed_at="2026-10-07T00:00:00+00:00",
    )

    assert "trace_mi_base_resource" not in execution["attempts"][1]["failure_trace"]
    inferred = derived["attempts"][1]["failure_trace"]["trace_mi_base_resource"]
    assert inferred["evidence_provenance"]["kind"] == BACKFILL_KIND
    assert inferred["evidence_provenance"]["directly_observed"] is False
    merged = merge_execution_evidence((("derived.json", derived),))
    report = require_mi_base_fallback_mode(
        evaluate_execution(plan, merged),
        merged,
        expected_mode="configured_fallback",
    )

    trace_summary = report["mi_base_trace_summary"]
    assert trace_summary["directly_observed_trace_count"] == 2
    assert trace_summary["authorized_backfilled_trace_count"] == 1
    assert trace_summary["effective_trace_count"] == 3
    assert trace_summary["missing_trace_scenario_ids"] == []
    assert trace_summary["backfill_audit"]["pass"] is True
    assert report["mi_base_fallback_expectation"]["direct_trace_complete"] is False
    assert report["mi_base_fallback_expectation"]["effective_trace_complete"] is True
    assert report["mi_base_fallback_expectation"]["pass"] is True
    assert report["operational_pass"] is True
    assert report["verdict"] == "REVIEW"
    markdown = render_markdown(report)
    assert "MI Base trace 직접 관측 / 소급 보정 / 전체 attempt" in markdown
    assert "승인된 소급 backfill 있음 / Proposal 재실행 없음 / 원본 증적 보존" in markdown


def test_excluded_diagnostic_execution_is_audited_and_must_not_persist() -> None:
    plan, execution = _full_plan_and_execution()
    report = attach_diagnostic_executions(
        evaluate_execution(plan, execution),
        (
            (
                "mismatch.json",
                {
                    "status": "FAIL",
                    "manifest": {
                        "mi_base_fallback_policy": {
                            "active_case_unavailable_mode": "verified_cache",
                        },
                    },
                    "attempts": [
                        {
                            "scenario_id": 1,
                            "status": "FAIL",
                            "proposal_persisted": False,
                            "error": "MI Base unavailable",
                        },
                    ],
                },
            ),
        ),
    )

    assert report["diagnostic_executions"][0]["status_counts"] == {"FAIL": 1}
    assert report["diagnostic_executions"][0]["persisted_attempt_count"] == 0
    assert report["operational_checks"]["excluded_diagnostic_runs_did_not_persist"] is True
    assert report["operational_pass"] is True


def test_build_reusable_testset_keeps_static_cohort_separate_from_observed_baseline() -> None:
    plan = {
        "generated_at": "2026-10-07T00:00:00+00:00",
        "selection_policy": "expanded_event_cohort/add-only",
        "baseline_event_ids": [1],
        "expanded_event_ids": [100],
        "method": {"representative_count_per_group": 3},
        "counts": {"new_groups": 1, "selected_scenarios": 3},
        "groups": [
            {
                "scenario_group_id": 500,
                "event_type_id": 1,
                "event_type_code": "type_1",
                "event_id": 100,
                "event_title": "Event",
                "selection_diagnostics": {"selection_mode": "proposal-eligible"},
                "selected_scenarios": [
                    {
                        "scenario_id": scenario_id,
                        "title": f"Scenario {scenario_id}",
                        "runtime_parameter_names": ["Temperature"],
                    }
                    for scenario_id in (1, 2, 3)
                ],
            },
        ],
    }
    report = {
        "generated_at": "2026-10-07T01:00:00+00:00",
        "kpis": {"successful_proposal_count": 2},
        "groups": [
            {
                "scenario_group_id": 500,
                "successful_count": 2,
                "actual_parameter_sets_identical": False,
                "any_parameter_value_variation": False,
                "exact_common_slot_count": 0,
                "exact_common_slots_with_different_values": 0,
                "scenarios": [
                    {"scenario_id": 1, "status": "PASS", "actual_parameter_names": ["Temperature"]},
                    {"scenario_id": 2, "status": "PASS", "actual_parameter_names": ["Temperature"]},
                    {"scenario_id": 3, "status": "FAIL", "actual_parameter_names": []},
                ],
            },
        ],
    }

    dataset = build_reusable_testset(plan, report)

    assert dataset["contract"]["scenario_count"] == 3
    assert dataset["contract"]["selection_policy"] == "expanded_event_cohort/add-only"
    assert dataset["cohort_identity"] == {
        "selection_policy": "expanded_event_cohort/add-only",
        "baseline_event_ids": [1],
        "expanded_event_ids": [100],
        "event_sets_disjoint": True,
    }
    assert dataset["groups"][0]["scenarios"][0]["scenario_id"] == 1
    assert dataset["observed_baseline"]["baseline_is_observational"] is True
    assert dataset["observed_baseline"]["groups"][0]["successful_count"] == 2


def test_regenerated_event_pool_testset_freezes_dynamic_40_group_identity() -> None:
    groups = []
    source_event_ids = list(range(100, 140))
    for index, event_id in enumerate(source_event_ids, start=1):
        groups.append(
            {
                "cohort_order": index,
                "scenario_group_id": 500 + index,
                "event_type_id": index,
                "event_type_code": f"type_{index}",
                "event_id": event_id,
                "event_title": f"Event {event_id}",
                "selected_scenarios": [
                    {"scenario_id": 10_000 + index * 10 + offset, "title": f"Scenario {offset}"}
                    for offset in range(3)
                ],
            },
        )
    plan = {
        "pass": True,
        "generated_at": "2026-10-07T00:00:00+00:00",
        "selection_policy": "existing_event_pool/add-only-regenerated-scenarios",
        "source_event_ids": source_event_ids,
        "cohort_event_ids": source_event_ids,
        "baseline_group_ids": list(range(1, 41)),
        "new_group_ids": [group["scenario_group_id"] for group in groups],
        "groups": groups,
    }

    dataset = build_reusable_testset(
        plan,
        {"generated_at": "2026-10-07T01:00:00+00:00", "kpis": {}, "groups": []},
    )
    result = validate_immutable_testset(
        plan,
        dataset,
        source="regenerated.json",
        sha256="sha",
    )

    assert dataset["dataset_id"] == (
        "model-parameter-v4.1.2-existing-event-pool-regenerated-40-groups-20261007"
    )
    assert dataset["cohort_identity"]["event_pool_reused_exactly"] is True
    assert result["pass"] is True


def test_semantic_empty_retry_prohibition_is_not_counted_as_integrity_error() -> None:
    scenario = {
        "scenario_id": 1,
        "title": "Semantic empty",
        "proposal_eligible": True,
        "runtime_parameter_names": ["Temperature"],
    }
    plan = {
        "pass": True,
        "groups": [
            {
                "scenario_group_id": 500,
                "event_type_id": 1,
                "event_type_code": "type_1",
                "selected_scenarios": [
                    scenario,
                    {**scenario, "scenario_id": 2},
                    {**scenario, "scenario_id": 3},
                ],
            },
        ],
    }
    execution = {
        "status": "FAIL",
        "manifest": {
            "capability_contract": {
                "catalog_version": "v4.1",
                "catalog_checksum": EXPECTED_CATALOG_CHECKSUM,
            },
            "resource": {"proposal_flow_release": "v4.1.3"},
        },
        "safety": {
            "confirmation_invoked": False,
            "callback_invoked": False,
            "automatic_retry": False,
        },
        "attempts": [
            {
                "scenario_id": scenario_id,
                "scenario_group_id": 500,
                "status": "FAIL",
                "error": "ModelParameterSemanticEmptyError('empty')",
                "integrity_errors": ["proposal evaluation raised; automatic retry is forbidden"],
                "proposal_persisted": False,
            }
            for scenario_id in (1, 2, 3)
        ],
    }

    report = evaluate_execution(plan, execution)

    assert report["kpis"]["semantic_empty_failure_count"] == 3
    assert report["kpis"]["integrity_error_count"] == 0
    assert report["operational_checks"]["identity_integrity"] is True


def test_structured_semantic_abstention_is_review_with_stage_and_trace_funnel() -> None:
    plan, execution = _full_plan_and_execution()
    original = execution["attempts"][0]
    execution["attempts"][0] = {
        "scenario_id": original["scenario_id"],
        "scenario_group_id": original["scenario_group_id"],
        "status": "ABSTAINED",
        "elapsed_seconds": 1.5,
        "semantic_empty": {
            "reason_code": "ABSTAINED_INSUFFICIENT_EVIDENCE",
            "stage": "step1_5",
            "structured": True,
            "observability_complete": True,
        },
        "failure_trace": {
            "observability_complete": True,
            "partial_state_captured": True,
            "semantic_stage_evidence": {"stage": "step1_5", "routing_tasks": []},
            "step_summary": {"termination_stage": "Step1.5 종료"},
            "llm_calls": [
                {
                    "step": "Step1.5 routing selection",
                    "retry_count": 1,
                    "usage": {"total_tokens": 77},
                },
            ],
        },
        "proposal_persisted": False,
    }
    execution["status"] = "REVIEW"

    report = evaluate_execution(plan, execution)

    assert report["operational_pass"] is True
    assert report["verdict"] == "REVIEW"
    assert report["kpis"]["semantic_abstention_count"] == 1
    assert report["kpis"]["semantic_trace_complete_count"] == 1
    assert report["kpis"]["semantic_trace_missing_count"] == 0
    assert report["semantic_abstention_by_stage"] == [{"stage": "step1_5", "count": 1}]
    assert report["semantic_abstention_by_reason_code"] == [
        {"reason_code": "ABSTAINED_INSUFFICIENT_EVIDENCE", "count": 1},
    ]
    assert report["kpis"]["total_tokens"] == 5977
    assert report["kpis"]["llm_retry_count"] == 1


def test_missing_semantic_trace_is_review_not_hard_fail() -> None:
    plan, execution = _full_plan_and_execution()
    original = execution["attempts"][0]
    execution["attempts"][0] = {
        "scenario_id": original["scenario_id"],
        "scenario_group_id": original["scenario_group_id"],
        "status": "ABSTAINED",
        "semantic_empty": {
            "reason_code": "ABSTAINED_MODEL_INPUT_NOT_FOUND",
            "stage": "step2",
            "structured": True,
            "observability_complete": False,
        },
        "failure_trace": {"llm_calls": []},
        "proposal_persisted": False,
    }

    report = evaluate_execution(plan, execution)

    assert report["operational_pass"] is True
    assert report["verdict"] == "REVIEW"
    assert report["kpis"]["semantic_trace_missing_count"] == 1
    assert any("trace가 불완전" in reason for reason in report["review_reasons"])


def test_exact_attempt_scope_mismatch_is_hard_fail() -> None:
    plan, execution = _full_plan_and_execution()
    missing_scenario_id = execution["attempts"].pop()["scenario_id"]

    report = evaluate_execution(plan, execution)

    assert report["operational_checks"]["attempt_scope_matches_eligible_scenarios"] is False
    assert report["operational_pass"] is False
    assert report["verdict"] == "FAIL"
    assert report["attempt_scope"]["missing_attempt_scenario_ids"] == [missing_scenario_id]


def test_markdown_keeps_fixed_column_dictionary_and_na_for_incomparable_group() -> None:
    plan, execution = _full_plan_and_execution()
    original = execution["attempts"][0]
    execution["attempts"][0] = {
        "scenario_id": original["scenario_id"],
        "scenario_group_id": original["scenario_group_id"],
        "status": "ABSTAINED",
        "semantic_empty": {
            "reason_code": "ABSTAINED_NO_CHANGE",
            "stage": "step3",
            "structured": True,
            "observability_complete": True,
        },
        "failure_trace": {
            "observability_complete": True,
            "semantic_stage_evidence": {"stage": "step3"},
            "step_summary": {},
            "llm_calls": [],
        },
    }
    report = evaluate_execution(plan, execution)
    report["post_fix_comparison"] = {
        "same_attempt_scope": True,
        "baseline": {
            "successful_proposal_count": 0,
            "success_rate_percent": 0.0,
            "semantic_abstention_count": 3,
            "other_failure_count": 0,
            "structured_semantic_abstention_count": 0,
            "semantic_trace_complete_count": 0,
            "semantic_trace_missing_count": 3,
        },
        "final": {
            "successful_proposal_count": 2,
            "success_rate_percent": 66.7,
            "semantic_abstention_count": 1,
            "other_failure_count": 0,
            "structured_semantic_abstention_count": 1,
            "semantic_trace_complete_count": 1,
            "semantic_trace_missing_count": 0,
        },
        "delta": {
            "successful_proposal_count": 2.0,
            "success_rate_percent": 66.7,
            "semantic_abstention_count": -2.0,
            "other_failure_count": 0.0,
            "structured_semantic_abstention_count": 1.0,
            "semantic_trace_complete_count": 1.0,
            "semantic_trace_missing_count": -3.0,
        },
    }
    markdown = render_markdown(report)

    assert "## 표 컬럼 설명 (고정)" in markdown
    assert "## Read-only KPI (핵심 7개)" in markdown
    assert "## Proposal 결과 KPI" in markdown
    assert "## KPI 정성 평가" in markdown
    assert "## 기존 KPI 개선 방안 (추가 KPI 아님)" in markdown
    assert "## MI Base trace 증적 구분" in markdown
    assert "소급 backfill 없음 / Proposal 재실행 없음" in markdown
    assert "Runtime-capable" in markdown
    assert "현재 write eligible" in markdown
    assert "메인 KPI를 대체하지 않습니다" in markdown
    assert "성공 Proposal 사이의 공통 canonical Parameter 이름" in markdown
    assert "| 2/3 | N/A | N/A | N/A | N/A |" in markdown
    assert "## 개선 전후 비교 (동일 테스트셋)" in markdown
    assert "| 성공률 | 0.0 | 66.7 | +66.7%p |" in markdown
    assert "### 개선 전후 비교" in markdown
    assert "개선 후 값에서 기존 값을 뺀 차이" in markdown


def test_reusable_representative_trio_fixture_has_exact_frozen_cohort() -> None:
    payload = json.loads(REUSABLE_TESTSET.read_text(encoding="utf-8"))
    contract = payload["contract"]
    groups = payload["groups"]
    scenario_ids = [scenario["scenario_id"] for group in groups for scenario in group["scenarios"]]

    assert payload["dataset_id"] == (
        "model-parameter-v4.1.2-expanded-event-cohort-20-groups-20261007"
    )
    assert contract == {
        "api_version": "v4",
        "generation_strategy": "multi_event_model_lever_dimensions",
        "scenario_lever_release": "v4.1",
        "scenario_lever_catalog_checksum": EXPECTED_CATALOG_CHECKSUM,
        "proposal_flow_release": "v4.1.2",
        "selection_policy": "expanded_event_cohort/add-only",
        "group_count": 20,
        "representative_scenarios_per_group": 3,
        "scenario_count": 60,
    }
    assert len(payload["cohort_identity"]["baseline_event_ids"]) == 20
    assert len(payload["cohort_identity"]["expanded_event_ids"]) == 20
    assert payload["cohort_identity"]["event_sets_disjoint"] is True
    assert len(groups) == 20
    assert all(len(group["scenarios"]) == 3 for group in groups)
    assert len(scenario_ids) == len(set(scenario_ids)) == 60
    assert len(payload["observed_baseline"]["groups"]) == 20
    assert payload["observed_baseline"]["baseline_is_observational"] is True


def test_existing_latest_representative_trio_fixture_has_frozen_40_group_cohort() -> None:
    fixture_bytes = EXISTING_LATEST_TESTSET.read_bytes()
    payload = json.loads(fixture_bytes)
    contract = payload["contract"]
    groups = payload["groups"]
    scenario_ids = [scenario["scenario_id"] for group in groups for scenario in group["scenarios"]]
    event_signatures = [tuple(group["event_signature"]) for group in groups]

    assert payload["dataset_id"] == (
        "model-parameter-v4.1.2-existing-latest-distinct-40-groups-20261007"
    )
    assert contract["selection_policy"] == SELECTION_POLICY
    assert contract["recency_policy"] == RECENCY_POLICY
    assert contract["source_mutation_policy"] == "read-only-existing-scenarios"
    assert contract["max_group_count"] == 50
    assert contract["group_count"] == len(groups) == 40
    assert contract["representative_scenarios_per_group"] == 3
    assert contract["scenario_count"] == len(scenario_ids) == 120
    assert len(scenario_ids) == len(set(scenario_ids))
    assert len(event_signatures) == len(set(event_signatures)) == 40
    assert [group["scenario_group_id"] for group in groups] == sorted(
        (group["scenario_group_id"] for group in groups),
        reverse=True,
    )
    assert payload["collection_baseline"]["observational"] is True
    assert hashlib.sha256(fixture_bytes).hexdigest() == (
        "bea75d598834b0a932dc2efa219ded6c771f1aad1861a85a24266c2eeedf7b7a"
    )


def test_existing_latest_fixture_validator_matches_dynamic_plan_identity() -> None:
    testset = json.loads(EXISTING_LATEST_TESTSET.read_text(encoding="utf-8"))
    plan = {
        "groups": [
            {
                "scenario_group_id": group["scenario_group_id"],
                "event_signature": group["event_signature"],
                "selected_scenarios": group["scenarios"],
            }
            for group in testset["groups"]
        ],
    }

    result = validate_existing_testset(plan, testset)

    assert result["pass"] is True
    mutated = json.loads(json.dumps(testset))
    mutated["groups"][0]["event_signature"][0] += 1
    mismatch = validate_existing_testset(plan, mutated)
    assert mismatch["checks"]["plan_identity_matches_testset"] is False
    assert mismatch["pass"] is False


def test_immutable_testset_matches_plan_by_ordered_group_event_and_scenario_ids() -> None:
    testset_bytes = REUSABLE_TESTSET.read_bytes()
    testset = json.loads(testset_bytes)
    plan = json.loads(REPRESENTATIVE_PLAN.read_text(encoding="utf-8"))

    result = validate_immutable_testset(
        plan,
        testset,
        source=str(REUSABLE_TESTSET),
        sha256="test-sha",
    )

    assert result["pass"] is True
    mutated = json.loads(json.dumps(plan))
    mutated["groups"][0]["selected_scenarios"][0]["scenario_id"] += 1
    mismatch = validate_immutable_testset(
        mutated,
        testset,
        source=str(REUSABLE_TESTSET),
        sha256="test-sha",
    )
    assert mismatch["checks"]["plan_identity_matches_testset"] is False
    assert mismatch["pass"] is False


def _explicit_slot_rationale() -> str:
    return (
        "대상·기간: Korea 2027; 근거 유형: BOUNDED_ASSUMPTION; 인과 경로: event→demand; "
        "기준값: 1; 적용 정책: bounded; 계산: base x factor; 제안값: 2; 근거: test; "
        "주요 가정: test assumption; 판단 설명: test judgment; 불확실성: review required"
    )


def _final_cohort_fixture_and_history() -> tuple[dict[str, Any], dict[str, Any]]:
    testset = {
        "dataset_id": "fixed-two-group-testset",
        "groups": [
            {
                "recency_rank": group_index,
                "scenario_group_id": group_id,
                "event_signature": [100 + group_index],
                "event_type_codes": [f"type_{group_index}"],
                "scenarios": [
                    {"scenario_id": scenario_id, "title": f"Scenario {scenario_id}"}
                    for scenario_id in scenario_ids
                ],
            }
            for group_index, (group_id, scenario_ids) in enumerate(
                ((10, (1, 2, 3)), (20, (4, 5, 6))),
                start=1,
            )
        ],
    }

    def proposal_row(scenario_id: int, group_id: int) -> dict[str, Any]:
        return {
            "model_param_proposal_id": 1000 + scenario_id,
            "scenario_id": scenario_id,
            "scenario_group_id": group_id,
            "status": "PROPOSED",
            "callback_status": "SKIPPED",
            "proposal_parameters": [
                {
                    "parameterName": "Temperature",
                    "values": [
                        {
                            "Country": "Korea",
                            "Year": 2027,
                            "Month": 1,
                            "basecaseValue": 1.0,
                            "proposedValue": float(scenario_id),
                            "rationale": _explicit_slot_rationale(),
                        },
                    ],
                },
            ],
            "confirmation_parameters": None,
        }

    scenario_to_group = {1: 10, 2: 10, 3: 10, 4: 20, 5: 20, 6: 20}
    covered_ids = [1, 2, 3, 4, 5]
    history = {
        "status": "PASS",
        "manifest": {
            "capability_contract": {
                "catalog_version": "v4.1",
                "catalog_checksum": EXPECTED_CATALOG_CHECKSUM,
            },
            "resource": {"proposal_flow_release": "v4.1.3"},
        },
        "selection": {
            "counts": {
                "covered_skip": 5,
                "eligible_uncovered": 1,
                "lifecycle_or_capability_skip": 0,
                "hard_stop": 0,
            },
            "discovered_scenario_ids": [1, 2, 3, 4, 5, 6],
            "covered_scenario_ids": covered_ids,
            "lifecycle_or_capability_skipped_scenario_ids": [],
        },
        "preflight": [
            {
                "scenario_id": scenario_id,
                "scenario_group_id": group_id,
                "status": "PASS",
                "uncovered_guard": {
                    "decision": "SKIP" if scenario_id in covered_ids else "ELIGIBLE",
                    "eligible": scenario_id not in covered_ids,
                    "history": (
                        [proposal_row(scenario_id, group_id)]
                        if scenario_id in covered_ids
                        else []
                    ),
                },
            }
            for scenario_id, group_id in scenario_to_group.items()
        ],
    }
    return testset, history


def test_final_cohort_analysis_uses_all_scenarios_and_compares_only_full_trios() -> None:
    testset, history = _final_cohort_fixture_and_history()

    analysis = build_final_cohort_trio_analysis(testset, history)

    assert analysis["pass"] is True
    assert analysis["verdict"] == "PASS"
    assert analysis["kpis"]["proposal_success_count"] == 5
    assert analysis["kpis"]["scenario_count"] == 6
    assert analysis["kpis"]["triple_success_group_count"] == 1
    assert analysis["kpis"]["identical_parameter_type_group_count"] == 1
    assert analysis["kpis"][
        "same_types_with_all_three_scenario_values_distinct_group_count"
    ] == 1
    assert analysis["kpis"]["exact_common_slot_count"] == 1
    assert analysis["kpis"]["exact_common_slots_with_different_values"] == 1
    assert analysis["kpis"]["exact_common_slots_with_all_three_values_distinct_rate_percent"] == 100.0
    assert analysis["kpis"]["slot_rationale_explicit_count"] == 5
    assert analysis["groups"][1]["actual_parameter_sets_identical"] is False

    markdown = render_final_cohort_trio_report(analysis)
    assert "최종 DB 기준 Trio Parameter·값 변별" in markdown
    assert "5 / 6 (83.3%)" in markdown
    assert "1 / 1 (100.0%)" in markdown
    assert "| 2 | 20 | 4, 5, 6 | 2/3 | N/A | N/A | N/A | N/A |" in markdown


def test_final_cohort_analysis_fails_closed_when_proposal_payload_is_missing() -> None:
    testset, history = _final_cohort_fixture_and_history()
    history["preflight"][0]["uncovered_guard"]["history"][0]["proposal_parameters"] = []

    analysis = build_final_cohort_trio_analysis(testset, history)

    assert analysis["pass"] is False
    assert analysis["verdict"] == "FAIL"
    assert analysis["checks"]["blocking_proposal_payload_complete"] is False
    assert analysis["payload_missing_scenario_ids"] == [1]


def test_attached_final_cohort_analysis_becomes_mandatory_report_section() -> None:
    testset, history = _final_cohort_fixture_and_history()
    report = {
        "operational_checks": {"base": True},
        "operational_pass": True,
        "verdict": "PASS",
    }

    updated = attach_final_cohort_trio_analysis(report, testset, history)

    assert updated["operational_checks"]["final_cohort_trio_analysis_complete"] is True
    assert updated["final_cohort_trio_analysis"]["kpis"]["proposal_success_count"] == 5
    assert updated["verdict"] == "PASS"


def test_main_markdown_automatically_renders_attached_final_cohort_section() -> None:
    plan, execution = _full_plan_and_execution()
    testset = {
        "dataset_id": "render-integration-testset",
        "groups": [
            {
                **group,
                "scenarios": group["selected_scenarios"],
            }
            for group in plan["groups"]
        ],
    }
    attempts_by_scenario = {
        int(attempt["scenario_id"]): attempt for attempt in execution["attempts"]
    }
    history = {
        "status": "PASS",
        "manifest": execution["manifest"],
        "selection": {
            "counts": {"covered_skip": 60},
            "discovered_scenario_ids": plan["selected_scenario_ids"],
            "covered_scenario_ids": plan["selected_scenario_ids"],
            "lifecycle_or_capability_skipped_scenario_ids": [],
        },
        "preflight": [
            {
                "scenario_id": scenario_id,
                "scenario_group_id": attempt["scenario_group_id"],
                "status": "PASS",
                "uncovered_guard": {
                    "decision": "SKIP",
                    "eligible": False,
                    "history": [
                        {
                            **attempt["proposal_db_row"],
                            "model_param_proposal_id": attempt["model_param_proposal_id"],
                        },
                    ],
                },
            }
            for scenario_id in plan["selected_scenario_ids"]
            for attempt in [attempts_by_scenario[scenario_id]]
        ],
    }

    report = attach_final_cohort_trio_analysis(
        evaluate_execution(plan, execution),
        testset,
        history,
    )
    markdown = render_markdown(report)

    assert markdown.count("## 최종 DB 기준 Trio Parameter·값 변별") == 1
    assert "| Proposal 있음 | 60 / 60 (100.0%) |" in markdown


def test_reconcile_final_history_matches_quality_outcomes() -> None:
    report = {
        "kpis": {
            "successful_proposal_count": 2,
            "semantic_empty_failure_count": 1,
            "other_failure_count": 0,
            "preflight_coverage_limit_scenario_count": 3,
        },
        "operational_checks": {"release": True},
        "operational_pass": True,
    }
    history = {
        "status": "PASS",
        "selection": {
            "counts": {
                "covered_skip": 2,
                "eligible_uncovered": 1,
                "lifecycle_or_capability_skip": 3,
                "hard_stop": 0,
            },
        },
        "preflight": [
            {
                "uncovered_guard": {
                    "history": [
                        {"status": "PROPOSED", "callback_status": "SKIPPED"},
                        {"status": "PROPOSED", "callback_status": "SKIPPED"},
                    ],
                },
            },
        ],
    }

    reconciled = reconcile_final_history(report, history, source="history.json")

    assert reconciled["db_reconciliation"]["pass"] is True
    assert reconciled["operational_checks"]["final_db_history_reconciled"] is True
    assert reconciled["operational_pass"] is True


def test_reconcile_final_history_rejects_equal_counts_with_wrong_scenario_ids() -> None:
    plan, execution = _full_plan_and_execution()
    report = evaluate_execution(plan, execution)
    scenario_to_group = {
        scenario["scenario_id"]: group["scenario_group_id"]
        for group in plan["groups"]
        for scenario in group["selected_scenarios"]
    }
    expected_ids = sorted(scenario_to_group)
    wrong_id = 999_999
    actual_ids = [*expected_ids[1:], wrong_id]
    preflight = []
    for scenario_id in actual_ids:
        group_id = scenario_to_group.get(scenario_id, 999_999)
        preflight.append(
            {
                "scenario_id": scenario_id,
                "scenario_group_id": group_id,
                "status": "PASS",
                "uncovered_guard": {
                    "decision": "SKIP",
                    "eligible": False,
                    "history": [
                        {
                            "model_param_proposal_id": 10_000 + scenario_id,
                            "scenario_id": scenario_id,
                            "scenario_group_id": group_id,
                            "status": "PROPOSED",
                            "callback_status": "SKIPPED",
                        },
                    ],
                },
            },
        )
    history = {
        "status": "PASS",
        "selection": {
            "counts": {
                "covered_skip": 60,
                "eligible_uncovered": 0,
                "lifecycle_or_capability_skip": 0,
                "hard_stop": 0,
            },
        },
        "preflight": preflight,
    }

    reconciled = reconcile_final_history(report, history)

    assert reconciled["db_reconciliation"]["checks"]["covered_scenario_ids_match_successes"] is False
    assert reconciled["db_reconciliation"]["pass"] is False
    assert reconciled["verdict"] == "FAIL"
