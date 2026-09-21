# Copyright (c) 2026 SK Innovation E&S.
# ruff: noqa: S101, SLF001

from __future__ import annotations

import argparse
import asyncio
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
import subprocess
from typing import Any

import pytest

from apps.agents.model_parameter_agent.constants import (
    MODEL_PARAMETER_PROPOSAL_ALLOWLIST,
    PROPOSAL_SCOPE_EXCLUDED_REASON_CODE,
)
from apps.agents.model_parameter_agent.flows.propose_parameters.nodes import (
    _merge_candidates_by_parameter,
)
from apps.agents.model_parameter_agent.flows.propose_parameters.validation import (
    ABSTAINED_INSUFFICIENT_EVIDENCE,
)
from tests.manual.model_parameter_agent import evaluate_multi_event_quality as runner


pytestmark = pytest.mark.model_parameter_core

CATALOG_VERSION = "v4-test"
CATALOG_CHECKSUM = "a" * 64


def _binding(parameter_name: str) -> dict[str, Any]:
    return {
        "parameter_name": parameter_name,
        "role": "primary",
        "applicability": f"Use {parameter_name} when the Lever is selected.",
        "support_status": "executable",
        "unsupported_reason_code": None,
    }


def _lever(
    impact_lever_id: int,
    lever_code: str,
    parameter_name: str,
    *,
    domain: str,
) -> dict[str, Any]:
    return {
        "impact_lever_id": impact_lever_id,
        "lever_code": lever_code,
        "domain": domain,
        "label": lever_code,
        "description": f"{lever_code} description",
        "applicability_hint": f"{lever_code} hint",
        "parameter_bindings": [_binding(parameter_name)],
        "catalog_version": CATALOG_VERSION,
    }


def _lever_state(
    lever: dict[str, Any],
    *,
    is_primary: bool = False,
) -> dict[str, Any]:
    return {
        "lever_code": lever["lever_code"],
        "impact_lever_id": lever["impact_lever_id"],
        "direction": "increase",
        "level": "high",
        "scope": "global",
        "time_window": "2027-2028",
        "is_primary_lever": is_primary,
        "lever_domain": lever["domain"],
        "lever_label": lever["label"],
        "lever_description": lever["description"],
        "lever_applicability_hint": lever["applicability_hint"],
        "parameter_bindings": deepcopy(lever["parameter_bindings"]),
    }


def _definition(
    parameter_name: str,
    *,
    model_file: str,
    model_sheet: str,
) -> dict[str, Any]:
    model_param_ids = {"GDP": 4, "PMI": 6, "ShippingCost": 20}
    return {
        "model_param_id": model_param_ids[parameter_name],
        "canonical_parameter_name": parameter_name,
        "parameter_name": parameter_name,
        "parameter_hint": f"{parameter_name} input",
        "model_file": model_file,
        "model_sheet": model_sheet,
        "model_table": "table1",
        "semantic_axes": "Country, Year",
    }


def _context(*, event_count: int = 2) -> dict[str, Any]:
    gdp_lever = _lever(101, "economic_activity", "GDP", domain="demand")
    shipping_lever = _lever(102, "shipping_cost", "ShippingCost", domain="trade")
    events = [
        {
            "mi_event_id": 100 + index,
            "display_order": index,
            "event_title_ko": f"event-{index}",
        }
        for index in range(1, event_count + 1)
    ]
    source_event_ids = [events[0]["mi_event_id"]] if events else []
    return {
        "scenario": {
            "scenario_id": 501,
            "scenario_group_id": 41,
            "title": "v4 scenario",
            "dimension_values": {"market_pressure": "high"},
        },
        "scenario_group": {
            "scenario_group_id": 41,
            "title": "v4 group",
            "api_version": runner.V4_API_VERSION,
            "generation_strategy": runner.V4_STRATEGY,
            "impact_catalog_version": CATALOG_VERSION,
            "impact_catalog_checksum": CATALOG_CHECKSUM,
        },
        "event": {},
        "events": events,
        "event_type": {},
        "dimension_template": [],
        "dimension_value_mappings": [],
        "dimension_lineage": [
            {
                "scenario_dimension_key": "market_pressure",
                "scenario_dimension_label": "Market pressure",
                "scenario_dimension_value": "high",
                "scenario_dimension_value_id": "high",
                "source_event_ids": source_event_ids,
                "primary_lever_code": gdp_lever["lever_code"],
                "primary_impact_lever_id": gdp_lever["impact_lever_id"],
                "lever_states": [
                    _lever_state(gdp_lever, is_primary=True),
                    _lever_state(shipping_lever),
                ],
            },
        ],
        "impact_levers": [gdp_lever, shipping_lever],
        "impact_catalog_version": CATALOG_VERSION,
        "impact_catalog_checksum": CATALOG_CHECKSUM,
        "model_support_issues": [],
        "candidate_exclusion_reason_codes": [],
        "executable_binding_occurrences": 2,
        "validation_warnings": [],
        "parameter_mapping_resources": {
            "mapping_rules": [],
            "parameter_definitions": [
                _definition("GDP", model_file="Demand", model_sheet="GDPPopulationAdjustment"),
                _definition(
                    "ShippingCost",
                    model_file="Trade",
                    model_sheet="ShippingCostInput",
                ),
            ],
        },
    }


def _evidence(*, event_count: int = 2) -> runner.ScenarioEvidence:
    evidence = runner.build_v4_scenario_evidence(501, _context(event_count=event_count))
    assert evidence.errors == ()
    return evidence


def _proposal_parameter(parameter_name: str = "GDP") -> dict[str, Any]:
    return {
        "parameterName": parameter_name,
        "modelTarget": {
            "modelFile": "Demand" if parameter_name == "GDP" else "Trade",
            "modelSheet": "GDPPopulationAdjustment" if parameter_name == "GDP" else "ShippingCostInput",
            "tableName": "table1",
            "valueFieldNames": [parameter_name],
            "slotAxesFieldNames": ["Country", "Year"],
        },
        "rationale": "test",
        "values": [
            {
                "Country": "Korea",
                "Year": 2027,
                "basecaseValue": 1.0,
                "proposedValue": 1.1,
                "rationale": "test",
            },
        ],
    }


def _execution_record(evidence: runner.ScenarioEvidence) -> dict[str, Any]:
    merged_candidates, warnings = _merge_candidates_by_parameter(
        [dict(item) for item in evidence.runtime_candidates],
    )
    assert warnings == []
    merged = merged_candidates[0]
    proposal_parameters = [_proposal_parameter()]
    return {
        "scenario_id": evidence.scenario_id,
        "context": {
            "scenario": {
                "scenario_id": evidence.scenario_id,
                "scenario_group_id": evidence.scenario_group_id,
            },
            "scenario_group": {
                "scenario_group_id": evidence.scenario_group_id,
                "api_version": evidence.api_version,
                "generation_strategy": evidence.generation_strategy,
                "impact_catalog_version": evidence.stored_catalog_version,
                "impact_catalog_checksum": evidence.stored_catalog_checksum,
            },
            "events": deepcopy(list(evidence.ordered_events)),
            "dimension_lineage": deepcopy(list(evidence.dimension_lineage)),
            "impact_catalog_version": evidence.active_catalog_version,
            "impact_catalog_checksum": evidence.active_catalog_checksum,
        },
        "rule_candidates": [dict(item) for item in evidence.raw_candidates],
        "expected_candidates": merged_candidates,
        "prompt_grounding_evidence": {
            "ordered_event_ids": list(evidence.ordered_event_ids),
            "runtime_raw_candidate_keys": sorted(
                item["candidate_key"] for item in evidence.runtime_candidates
            ),
            "selected_candidate_keys": sorted(
                item["candidate_key"] for item in merged_candidates
            ),
        },
        "result": {
            "parameter_adjustments": [
                {
                    "candidate_key": merged["candidate_key"],
                    "model_file": merged["model_file"],
                    "model_sheet": merged["model_sheet"],
                    "parameter_name": "GDP",
                    "selected": True,
                    "parameter_selection_rationale_ko": "test",
                    "value_grid": [
                        {
                            "coordinates": {"Country": "Korea", "Year": 2027},
                            "basecase_value": 1.0,
                            "proposed_value": 1.1,
                            "rationale_ko": "test",
                        },
                    ],
                },
            ],
            "non_input_items": [dict(item) for item in evidence.blocked_candidates],
            "validation_warnings": [],
        },
        "parameter_slots": [
            {
                "candidate_key": merged["candidate_key"],
                "slot_key": "slot-1",
                "selected": True,
                "slot_axes": [
                    {"axis_name": "Country", "axis_value": "Korea"},
                    {"axis_name": "Year", "axis_value": 2027},
                ],
            },
        ],
        "slot_catalog": [
            {
                "candidate_key": merged["candidate_key"],
                "parameter_name": "GDP",
                "key_axes": ["Country", "Year"],
                "fixed_axis_names": ["Country"],
                "time_axis_names": ["Year"],
                "period_groups": [
                    {
                        "period_group_id": "period-group-1",
                        "available_periods": [{"Year": 2027}],
                    },
                ],
                "fixed_axis_hierarchy": [
                    {
                        "axis_value": "Korea",
                        "period_group_id": "period-group-1",
                    },
                ],
            },
        ],
        "slot_candidate_mappings": [deepcopy(merged)],
        "effective_references": [
            {
                "candidate_key": merged["candidate_key"],
                "slot_key": "slot-1",
                "axes": {"Country": "Korea", "Year": 2027},
                "actual_basecase_value": 1.0,
                "lut_default_value": None,
                "llm_reference_value": 1.0,
                "effective_source": "basecase",
                "basecase_reference_id": "basecase:gdp:1",
            },
        ],
        "step_summary": {
            "parameter_status": "PASS",
            "slot_status": "PASS",
            "basecase_status": "PASS",
            "value_status": "PASS",
            "validated_candidate_count": 1,
            "selected_parameter_count": 1,
            "proposal_parameter_count": 1,
            "selected_slot_count": 1,
            "value_reference_record_count": 1,
            "value_cell_count": 1,
            "value_cell_with_basecase_count": 1,
        },
        "final_response": {
            "status": "success",
            "data": {
                "modelParamProposalId": 9001,
                "scenarioId": evidence.scenario_id,
                "scenarioGroupId": evidence.scenario_group_id,
                "eventId": None,
                "proposalParameters": deepcopy(proposal_parameters),
            },
        },
        "proposal_db_row": {
            "model_param_proposal_id": 9001,
            "scenario_id": evidence.scenario_id,
            "scenario_group_id": evidence.scenario_group_id,
            "mi_event_id": None,
            "status": "CONFIRMED",
            "proposal_parameters": deepcopy(proposal_parameters),
            "confirmation_parameters": deepcopy(proposal_parameters),
        },
        "confirmation": {"status": "PASS"},
        "execution_attempt_count": 1,
        "elapsed_seconds": 2.5,
        "llm_calls": [
            {
                "step": "Step1.5",
                "retry_count": 0,
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 20,
                    "total_tokens": 120,
                },
            },
        ],
    }


def _args(report_path: Path, *, execute: bool = False) -> argparse.Namespace:
    return runner.build_parser().parse_args(
        [
            *(
                ["--execute", "--scenario-id", "501"]
                if execute
                else []
            ),
            "--report-path",
            str(report_path),
        ],
    )


def test_parser_defaults_to_read_only_and_has_no_retry_option() -> None:
    args = runner.build_parser().parse_args([])

    assert args.execute is False
    assert args.limit == runner.DEFAULT_DISCOVERY_LIMIT
    with pytest.raises(SystemExit):
        runner.build_parser().parse_args(["--retries", "2"])


@pytest.mark.parametrize("event_count", [1, 5])
def test_v4_evidence_accepts_ordered_one_to_five_events(event_count: int) -> None:
    evidence = _evidence(event_count=event_count)

    assert len(evidence.ordered_event_ids) == event_count
    assert evidence.api_version == "v4"
    assert evidence.generation_strategy == runner.V4_STRATEGY


@pytest.mark.parametrize("event_count", [0, 6])
def test_v4_evidence_rejects_event_count_outside_one_to_five(
    event_count: int,
) -> None:
    evidence = runner.build_v4_scenario_evidence(
        501,
        _context(event_count=event_count),
    )

    assert any("ordered event count" in message for message in evidence.errors)


def test_v4_evidence_requires_exact_one_to_n_display_order() -> None:
    context = _context()
    context["events"][1]["display_order"] = 3

    evidence = runner.build_v4_scenario_evidence(501, context)

    assert any("exact 1..N" in message for message in evidence.errors)


def test_v4_evidence_rejects_loaded_context_for_another_scenario() -> None:
    context = _context()
    context["scenario"]["scenario_id"] = 999

    evidence = runner.build_v4_scenario_evidence(501, context)

    assert evidence.scenario_id == 501
    assert any("scenario_id mismatch" in message for message in evidence.errors)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("api_version", "v3"),
        ("generation_strategy", "multi_event_composite_dimensions"),
    ],
)
def test_v4_evidence_rejects_legacy_identity(field: str, value: str) -> None:
    context = _context()
    context["scenario_group"][field] = value

    evidence = runner.build_v4_scenario_evidence(501, context)

    assert any("mismatch" in message for message in evidence.errors)


def test_v4_evidence_rejects_catalog_checksum_drift() -> None:
    context = _context()
    context["scenario_group"]["impact_catalog_checksum"] = "b" * 64

    evidence = runner.build_v4_scenario_evidence(501, context)

    assert any("catalog checksum mismatch" in message for message in evidence.errors)


def test_v4_evidence_rejects_hydrated_binding_drift() -> None:
    context = _context()
    context["dimension_lineage"][0]["lever_states"][0]["parameter_bindings"][0][
        "applicability"
    ] = "stale binding"

    evidence = runner.build_v4_scenario_evidence(501, context)

    assert any("catalog-pinned binding mismatch" in message for message in evidence.errors)


def test_v4_evidence_rejects_primary_lever_state_drift() -> None:
    context = _context()
    context["dimension_lineage"][0]["primary_impact_lever_id"] = 999

    evidence = runner.build_v4_scenario_evidence(501, context)

    assert any("primary Lever ID mismatch" in message for message in evidence.errors)


def test_partition_requires_unique_raw_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    candidate = dict(_evidence().runtime_candidates[0])
    monkeypatch.setattr(
        runner,
        "match_v4_parameter_candidates_from_rows",
        lambda **kwargs: ([candidate, dict(candidate)], [], []),
    )

    evidence = runner.build_v4_scenario_evidence(501, _context())

    assert any("raw candidate key가 중복" in message for message in evidence.errors)


def test_production_allowlist_partitions_active_but_blocked_parameter() -> None:
    evidence = _evidence()

    assert {_parameter["parameter_name"] for _parameter in evidence.runtime_candidates} == {
        "GDP",
    }
    assert {_parameter["parameter_name"] for _parameter in evidence.blocked_candidates} == {
        "ShippingCost",
    }
    assert all(
        item["reason_code"] == PROPOSAL_SCOPE_EXCLUDED_REASON_CODE
        for item in evidence.blocked_candidates
    )
    assert "GDP" in MODEL_PARAMETER_PROPOSAL_ALLOWLIST
    assert "ShippingCost" not in MODEL_PARAMETER_PROPOSAL_ALLOWLIST


def test_read_only_coverage_exposes_runtime_partition_before_selection() -> None:
    evidence = _evidence()

    rows = {
        row.parameter_name: row
        for row in runner.build_coverage_rows(evidence, None, None)
    }

    assert rows["GDP"].raw == 1
    assert rows["GDP"].runtime == 1
    assert rows["GDP"].selected is None
    assert rows["GDP"].verdict == "COVERAGE LIMIT"
    assert rows["ShippingCost"].raw == 1
    assert rows["ShippingCost"].runtime == 0
    assert rows["ShippingCost"].verdict == "PASS"


def test_clean_execution_uses_merged_lineage_and_passes() -> None:
    evidence = _evidence()
    record = _execution_record(evidence)

    assessment = runner.assess_execution(evidence, record)

    assert assessment.verdict == "PASS"
    assert record["expected_candidates"][0]["candidate_key"].startswith("parameter|v4|")
    assert set(record["expected_candidates"][0]["merged_candidate_keys"]) == {
        evidence.runtime_candidates[0]["candidate_key"],
    }


def test_post_selection_abstention_is_valid_terminal_evidence() -> None:
    evidence = _evidence()
    gdp = dict(evidence.runtime_candidates[0])
    pmi = deepcopy(gdp)
    pmi["candidate_key"] = pmi["candidate_key"].replace("|gdp|", "|pmi|")
    pmi["canonical_parameter_name"] = "PMI"
    pmi["parameter_name"] = "PMI"
    pmi["model_sheet"] = "PMIAdjustment"
    evidence.runtime_candidates = (gdp, pmi)
    evidence.raw_candidates = (gdp, pmi, *evidence.blocked_candidates)
    evidence.parameter_definitions = (
        *evidence.parameter_definitions,
        _definition("PMI", model_file="Demand", model_sheet="PMIAdjustment"),
    )
    record = _execution_record(evidence)
    record["step_summary"]["validated_candidate_count"] = 2
    pmi_candidate = next(
        item
        for item in record["expected_candidates"]
        if item["parameter_name"] == "PMI"
    )
    record["result"]["non_input_items"].append(
        {
            "candidate_key": pmi_candidate["candidate_key"],
            "parameter_name": "PMI",
            "lever_code": "economic_activity",
            "source_event_ids": [101],
            "reason_code": ABSTAINED_INSUFFICIENT_EVIDENCE,
        },
    )

    assessment = runner.assess_execution(evidence, record)
    rows = {
        row.parameter_name: row
        for row in runner.build_coverage_rows(evidence, record, assessment)
    }

    assert assessment.verdict == "PASS"
    assert rows["GDP"].verdict == "PASS"
    assert rows["PMI"].verdict == "PASS"
    assert rows["PMI"].exclusion_reason == ABSTAINED_INSUFFICIENT_EVIDENCE


def test_post_selection_abstention_rejects_unknown_reason() -> None:
    evidence = _evidence()
    record = _execution_record(evidence)
    candidate = record["expected_candidates"][0]
    record["result"]["parameter_adjustments"] = []
    record["result"]["non_input_items"].append(
        {
            "candidate_key": candidate["candidate_key"],
            "parameter_name": "GDP",
            "reason_code": "UNKNOWN_ABSTENTION",
        },
    )

    assessment = runner.assess_execution(evidence, record)

    assert assessment.verdict == "FAIL"
    assert any("reason code" in message for message in assessment.failures)


def test_graph_v4_raw_trace_must_match_independent_raw_oracle() -> None:
    evidence = _evidence()
    record = _execution_record(evidence)
    record["rule_candidates"] = []

    assessment = runner.assess_execution(evidence, record)

    assert assessment.verdict == "FAIL"
    assert any("raw oracle key" in message for message in assessment.failures)


def test_unexpected_merged_raw_lineage_is_fail() -> None:
    evidence = _evidence()
    record = _execution_record(evidence)
    record["expected_candidates"][0]["merged_candidate_keys"].append(
        evidence.blocked_candidates[0]["candidate_key"],
    )

    assessment = runner.assess_execution(evidence, record)

    assert assessment.verdict == "FAIL"
    assert any("merged_candidate_keys" in message for message in assessment.failures)


def test_merged_raw_key_must_stay_bound_to_its_independent_target() -> None:
    evidence = _evidence()
    gdp = dict(evidence.runtime_candidates[0])
    pmi = deepcopy(gdp)
    pmi["candidate_key"] = pmi["candidate_key"].replace("|gdp|", "|pmi|")
    pmi["canonical_parameter_name"] = "PMI"
    pmi["parameter_name"] = "PMI"
    pmi["model_sheet"] = "PMIInput"
    evidence.runtime_candidates = (gdp, pmi)
    evidence.raw_candidates = (gdp, pmi, *evidence.blocked_candidates)
    record = _execution_record(evidence)
    record["expected_candidates"][0]["merged_candidate_keys"].append(
        pmi["candidate_key"],
    )
    record["expected_candidates"] = record["expected_candidates"][:1]
    record["prompt_grounding_evidence"]["selected_candidate_keys"] = [
        record["expected_candidates"][0]["candidate_key"],
    ]

    assessment = runner.assess_execution(evidence, record)

    assert assessment.verdict == "FAIL"
    assert any("key→parameter/model target" in message for message in assessment.failures)


@pytest.mark.parametrize("layer", ["raw", "runtime"])
def test_graph_trace_candidate_key_duplicate_is_fail(layer: str) -> None:
    evidence = _evidence()
    record = _execution_record(evidence)
    field_name = "rule_candidates" if layer == "raw" else "expected_candidates"
    record[field_name].append(deepcopy(record[field_name][0]))

    assessment = runner.assess_execution(evidence, record)

    assert assessment.verdict == "FAIL"
    assert any("candidate_key가 중복" in message for message in assessment.failures)


def test_partial_routing_lineage_loss_is_review() -> None:
    evidence = _evidence()
    gdp = dict(evidence.runtime_candidates[0])
    gdp["mapping_method"] = "routing"
    pmi = deepcopy(gdp)
    pmi["candidate_key"] = pmi["candidate_key"].replace("|gdp|", "|pmi|")
    pmi["canonical_parameter_name"] = "PMI"
    pmi["parameter_name"] = "PMI"
    evidence.runtime_candidates = (gdp, pmi)
    evidence.raw_candidates = (gdp, pmi, *evidence.blocked_candidates)
    record = _execution_record(evidence)
    record["rule_candidates"] = [dict(item) for item in evidence.raw_candidates]
    record["expected_candidates"] = [
        item
        for item in record["expected_candidates"]
        if item["parameter_name"] == "GDP"
    ]
    record["prompt_grounding_evidence"]["selected_candidate_keys"] = [
        record["expected_candidates"][0]["candidate_key"],
    ]

    assessment = runner.assess_execution(evidence, record)

    assert assessment.verdict == "REVIEW"
    assert any("routing raw lineage" in message for message in assessment.reviews)
    evidence.parameter_definitions = (
        *evidence.parameter_definitions,
        _definition("PMI", model_file="Demand", model_sheet="PMIAdjustment"),
    )
    rows = {
        row.parameter_name: row
        for row in runner.build_coverage_rows(evidence, record, assessment)
    }
    assert rows["PMI"].runtime == 1
    assert rows["PMI"].selected == 0
    assert rows["PMI"].verdict == "REVIEW"


def test_lut_only_reference_is_valid_and_api_lut_value_is_response_only() -> None:
    evidence = _evidence()
    record = _execution_record(evidence)
    cell = record["result"]["parameter_adjustments"][0]["value_grid"][0]
    cell["basecase_value"] = None
    cell["lut_value"] = 0.9
    reference = record["effective_references"][0]
    reference["actual_basecase_value"] = None
    reference["lut_default_value"] = 0.9
    reference["llm_reference_value"] = 0.9
    reference["effective_source"] = "lut"
    record["step_summary"]["value_cell_with_basecase_count"] = 0
    api_value = record["final_response"]["data"]["proposalParameters"][0]["values"][0]
    api_value["basecaseValue"] = None
    api_value["lutValue"] = 0.9
    for field_name in ("proposal_parameters", "confirmation_parameters"):
        record["proposal_db_row"][field_name][0]["values"][0]["basecaseValue"] = None

    assessment = runner.assess_execution(evidence, record)

    assert assessment.verdict == "PASS"


@pytest.mark.parametrize("layer", ["runtime", "selected", "proposed", "confirmed"])
def test_blocked_parameter_leakage_is_mandatory_fail(layer: str) -> None:
    evidence = _evidence()
    record = _execution_record(evidence)
    blocked = dict(evidence.blocked_candidates[0])
    if layer == "runtime":
        merged, _ = _merge_candidates_by_parameter([blocked])
        record["runtime_candidates"] = [*record["expected_candidates"], *merged]
    elif layer == "selected":
        record["result"]["parameter_adjustments"].append(
            {
                "candidate_key": "parameter|v4|trade|shippinginput|shippingcost",
                "model_file": "Trade",
                "model_sheet": "ShippingInput",
                "parameter_name": "ShippingCost",
                "selected": True,
            },
        )
    elif layer == "proposed":
        record["final_response"]["data"]["proposalParameters"].append(
            _proposal_parameter("ShippingCost"),
        )
    else:
        record["proposal_db_row"]["confirmation_parameters"].append(
            _proposal_parameter("ShippingCost"),
        )

    assessment = runner.assess_execution(evidence, record)

    assert assessment.verdict == "FAIL"
    assert any("active-but-blocked" in message for message in assessment.failures)


@pytest.mark.parametrize(
    "layer",
    ["parameter_slots", "slot_candidate_mappings", "effective_references"],
)
def test_blocked_parameter_leakage_in_step2_or_step3_is_fail(layer: str) -> None:
    evidence = _evidence()
    record = _execution_record(evidence)
    blocked_merged, _ = _merge_candidates_by_parameter(
        [dict(evidence.blocked_candidates[0])],
    )
    blocked = blocked_merged[0]
    if layer == "parameter_slots":
        record[layer].append(
            {
                "candidate_key": blocked["candidate_key"],
                "slot_key": "slot-blocked",
                "selected": True,
            },
        )
    elif layer == "slot_candidate_mappings":
        record[layer] = [blocked]
    else:
        record[layer].append(
            {
                "candidate_key": blocked["candidate_key"],
                "slot_key": "slot-blocked",
                "parameter_name": "ShippingCost",
                "llm_reference_value": 1.0,
                "effective_source": "basecase",
                "actual_basecase_value": 1.0,
            },
        )

    assessment = runner.assess_execution(evidence, record)

    assert assessment.verdict == "FAIL"
    assert any(layer in message for message in assessment.failures)


def test_missing_blocked_exclusion_reason_is_mandatory_fail() -> None:
    evidence = _evidence()
    record = _execution_record(evidence)
    record["result"]["non_input_items"] = []

    assessment = runner.assess_execution(evidence, record)

    assert assessment.verdict == "FAIL"
    assert any("exclusion reason" in message for message in assessment.failures)


@pytest.mark.parametrize("mutation", ["missing", "wrong_reason"])
def test_matcher_non_input_identity_and_reason_must_survive_graph(
    mutation: str,
) -> None:
    evidence = _evidence()
    matcher_non_input = {
        "scenario_dimension_key": "market_pressure",
        "source_dimension_value_id": "high",
        "source_event_ids": [101],
        "lever_code": "weather_risk",
        "impact_lever_id": 999,
        "direction": "unchanged",
        "reason_code": "UNCHANGED_LEVER_STATE",
    }
    evidence.matcher_non_inputs = (matcher_non_input,)
    record = _execution_record(evidence)
    graph_item = dict(matcher_non_input)
    record["result"]["non_input_items"].append(graph_item)
    if mutation == "missing":
        record["result"]["non_input_items"].remove(graph_item)
    else:
        graph_item["reason_code"] = "NO_PARAMETER_BINDING"

    assessment = runner.assess_execution(evidence, record)

    assert assessment.verdict == "FAIL"
    assert any("identity/reason multiset" in message for message in assessment.failures)


def test_step_summary_or_slot_value_count_drift_is_mandatory_fail() -> None:
    evidence = _evidence()
    record = _execution_record(evidence)
    record["step_summary"]["value_cell_count"] = 2

    assessment = runner.assess_execution(evidence, record)

    assert assessment.verdict == "FAIL"
    assert any("value_cell_count" in message for message in assessment.failures)


def test_slot_reference_adjustment_coordinate_drift_is_fail() -> None:
    evidence = _evidence()
    record = _execution_record(evidence)
    record["effective_references"][0]["axes"]["Country"] = "China"

    assessment = runner.assess_execution(evidence, record)

    assert assessment.verdict == "FAIL"
    assert any("reference axes" in message for message in assessment.failures)


def test_selected_slot_must_belong_to_exact_slot_catalog() -> None:
    evidence = _evidence()
    record = _execution_record(evidence)
    record["parameter_slots"][0]["slot_axes"][0]["axis_value"] = "Japan"
    record["effective_references"][0]["axes"]["Country"] = "Japan"
    record["result"]["parameter_adjustments"][0]["value_grid"][0]["coordinates"][
        "Country"
    ] = "Japan"

    assessment = runner.assess_execution(evidence, record)

    assert assessment.verdict == "FAIL"
    assert any("slot_catalog exact union" in message for message in assessment.failures)


def test_basecase_value_must_take_precedence_over_lut_default() -> None:
    evidence = _evidence()
    record = _execution_record(evidence)
    reference = record["effective_references"][0]
    reference["lut_default_value"] = 0.9
    reference["llm_reference_value"] = 0.9
    reference["effective_source"] = "lut"

    assessment = runner.assess_execution(evidence, record)

    assert assessment.verdict == "FAIL"
    assert any("Basecase-over-LUT" in message for message in assessment.failures)


def test_value_cell_reference_value_mismatch_is_fail_even_if_api_db_match() -> None:
    evidence = _evidence()
    record = _execution_record(evidence)
    record["result"]["parameter_adjustments"][0]["value_grid"][0][
        "basecase_value"
    ] = 999.0
    record["final_response"]["data"]["proposalParameters"][0]["values"][0][
        "basecaseValue"
    ] = 999.0
    for field_name in ("proposal_parameters", "confirmation_parameters"):
        record["proposal_db_row"][field_name][0]["values"][0][
            "basecaseValue"
        ] = 999.0

    assessment = runner.assess_execution(evidence, record)

    assert assessment.verdict == "FAIL"
    assert any("value cell basecase_value" in message for message in assessment.failures)


def test_non_finite_step3_value_is_fail() -> None:
    evidence = _evidence()
    record = _execution_record(evidence)
    record["result"]["parameter_adjustments"][0]["value_grid"][0][
        "proposed_value"
    ] = float("nan")
    record["final_response"]["data"]["proposalParameters"][0]["values"][0][
        "proposedValue"
    ] = float("nan")
    for field_name in ("proposal_parameters", "confirmation_parameters"):
        record["proposal_db_row"][field_name][0]["values"][0][
            "proposedValue"
        ] = float("nan")

    assessment = runner.assess_execution(evidence, record)

    assert assessment.verdict == "FAIL"
    assert any("finite numeric" in message for message in assessment.failures)


def test_api_db_model_target_or_value_payload_drift_is_fail() -> None:
    evidence = _evidence()
    record = _execution_record(evidence)
    record["proposal_db_row"]["proposal_parameters"][0]["modelTarget"][
        "modelFile"
    ] = "WrongModel"

    assessment = runner.assess_execution(evidence, record)

    assert assessment.verdict == "FAIL"
    assert any("target/value payload" in message for message in assessment.failures)


def test_post_merge_model_table_must_stay_inside_independent_runtime_target() -> None:
    evidence = _evidence()
    record = _execution_record(evidence)
    record["expected_candidates"][0]["model_table"] = "WrongTable"

    assessment = runner.assess_execution(evidence, record)

    assert assessment.verdict == "FAIL"
    assert any("candidate target" in message for message in assessment.failures)


def test_post_merge_candidate_requires_raw_lineage_even_for_allowed_target() -> None:
    evidence = _evidence()
    record = _execution_record(evidence)
    record["expected_candidates"][0]["merged_candidate_keys"] = []
    record["expected_candidates"][0]["source_event_ids"] = []
    record["expected_candidates"][0]["lever_provenance"] = []
    record["expected_candidates"][0]["binding_provenance"] = []

    assessment = runner.assess_execution(evidence, record)

    assert assessment.verdict == "FAIL"
    assert any("merged_candidate_keys가 비어" in message for message in assessment.failures)


def test_same_target_raw_lineage_cannot_split_into_multiple_runtime_tasks() -> None:
    context = _context()
    context["impact_levers"][1]["parameter_bindings"] = [_binding("GDP")]
    context["dimension_lineage"][0]["lever_states"][1][
        "parameter_bindings"
    ] = [_binding("GDP")]
    evidence = runner.build_v4_scenario_evidence(501, context)
    assert evidence.errors == ()
    assert len(evidence.runtime_candidates) == 2
    record = _execution_record(evidence)
    merged = record["expected_candidates"][0]
    raw_keys = [item["candidate_key"] for item in evidence.runtime_candidates]
    first = deepcopy(merged)
    first["merged_candidate_keys"] = [raw_keys[0]]
    second = deepcopy(merged)
    second["candidate_key"] = f"{merged['candidate_key']}|split"
    second["merged_candidate_keys"] = [raw_keys[1]]
    record["expected_candidates"] = [first, second]

    assessment = runner.assess_execution(evidence, record)

    assert assessment.verdict == "FAIL"
    assert any("여러 task로 분할" in message for message in assessment.failures)


def test_db_payload_must_not_persist_response_only_lut_value() -> None:
    evidence = _evidence()
    record = _execution_record(evidence)
    for field_name in ("proposal_parameters", "confirmation_parameters"):
        record["proposal_db_row"][field_name][0]["values"][0]["lutValue"] = 0.9

    assessment = runner.assess_execution(evidence, record)

    assert assessment.verdict == "FAIL"
    assert any("DB proposal payload" in message for message in assessment.failures)
    assert any("DB confirmation payload" in message for message in assessment.failures)


def test_adjustment_to_production_presentation_drift_is_fail() -> None:
    evidence = _evidence()
    record = _execution_record(evidence)
    record["result"]["parameter_adjustments"][0]["value_grid"][0][
        "proposed_value"
    ] = 9.9

    assessment = runner.assess_execution(evidence, record)

    assert assessment.verdict == "FAIL"
    assert any("production presentation" in message for message in assessment.failures)


def test_api_non_success_status_is_fail() -> None:
    evidence = _evidence()
    record = _execution_record(evidence)
    record["final_response"]["status"] = "error"

    assessment = runner.assess_execution(evidence, record)

    assert assessment.verdict == "FAIL"
    assert any("response status" in message for message in assessment.failures)


def test_missing_token_and_retry_observability_is_review() -> None:
    evidence = _evidence()
    record = _execution_record(evidence)
    record["llm_calls"] = [{"step": "Step1.5"}]

    assessment = runner.assess_execution(evidence, record)

    assert assessment.verdict == "REVIEW"
    assert any("retry count" in message for message in assessment.reviews)
    assert any("token usage" in message for message in assessment.reviews)


def test_missing_prompt_grounding_packet_is_review() -> None:
    evidence = _evidence()
    record = _execution_record(evidence)
    record.pop("prompt_grounding_evidence")

    assessment = runner.assess_execution(evidence, record)

    assert assessment.verdict == "REVIEW"
    assert any("prompt grounding packet" in message for message in assessment.reviews)


def test_numeric_string_proposed_value_is_fail() -> None:
    evidence = _evidence()
    record = _execution_record(evidence)
    record["result"]["parameter_adjustments"][0]["value_grid"][0][
        "proposed_value"
    ] = "1.1"
    record["final_response"]["data"]["proposalParameters"][0]["values"][0][
        "proposedValue"
    ] = "1.1"
    for field_name in ("proposal_parameters", "confirmation_parameters"):
        record["proposal_db_row"][field_name][0]["values"][0][
            "proposedValue"
        ] = "1.1"

    assessment = runner.assess_execution(evidence, record)

    assert assessment.verdict == "FAIL"
    assert any("finite numeric" in message for message in assessment.failures)


@pytest.mark.parametrize(
    ("mutation", "expected_message"),
    [
        ("api_event", "API eventId"),
        ("db_event", "DB mi_event_id"),
        ("db_group", "DB scenario_group_id"),
        ("confirmation", "confirmation workflow"),
    ],
)
def test_v4_persistence_contract_break_is_fail(
    mutation: str,
    expected_message: str,
) -> None:
    evidence = _evidence()
    record = _execution_record(evidence)
    if mutation == "api_event":
        record["final_response"]["data"]["eventId"] = 101
    elif mutation == "db_event":
        record["proposal_db_row"]["mi_event_id"] = 101
    elif mutation == "db_group":
        record["proposal_db_row"]["scenario_group_id"] = 999
    else:
        record["confirmation"]["status"] = "FAIL"

    assessment = runner.assess_execution(evidence, record)

    assert assessment.verdict == "FAIL"
    assert any(expected_message in message for message in assessment.failures)


def test_execute_targets_never_retries_after_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    evidence = _evidence()
    calls: list[int] = []

    async def fail_once(scenario_id: int) -> dict[str, Any]:
        calls.append(scenario_id)
        message = "write failed"
        raise RuntimeError(message)

    monkeypatch.setattr(runner, "execute_proposal_and_confirmation", fail_once)

    records = asyncio.run(runner.execute_targets([evidence]))

    assert calls == [evidence.scenario_id]
    assert records[evidence.scenario_id]["execution_attempt_count"] == 1
    assert "write failed" in records[evidence.scenario_id]["error"]


def test_execute_targets_preserves_attached_partial_write_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evidence = _evidence()

    async def fail_after_proposal(scenario_id: int) -> dict[str, Any]:
        message = "confirmation fetch failed"
        error = RuntimeError(message)
        error._model_parameter_runner_record = {  # type: ignore[attr-defined]
            "failed_stage": "confirmation DB read-back",
            "final_response": {
                "data": {"modelParamProposalId": 9001},
            },
            "proposal_db_row": {"model_param_proposal_id": 9001},
        }
        raise error

    monkeypatch.setattr(
        runner,
        "execute_proposal_and_confirmation",
        fail_after_proposal,
    )

    records = asyncio.run(runner.execute_targets([evidence]))
    record = records[evidence.scenario_id]

    assert record["final_response"]["data"]["modelParamProposalId"] == 9001
    assert record["proposal_db_row"]["model_param_proposal_id"] == 9001
    assert record["failed_stage"] == "confirmation DB read-back"


def test_core_smoke_failure_is_fail() -> None:
    def fail_command(
        *args: object,
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=args[0], returncode=2, stdout="failed", stderr="")

    result = runner.run_core_smoke(run_command=fail_command)

    assert result.status == "FAIL"
    assert result.return_code == 2


def test_schema_connection_error_is_redacted(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_connection() -> object:
        message = "password=hunter2 token=secret-token"
        raise RuntimeError(message)

    monkeypatch.setattr(runner, "get_sync_session", fail_connection)

    result = runner._schema_preflight()

    assert result.verdict == "FAIL"
    assert "hunter2" not in result.errors[0]
    assert "secret-token" not in result.errors[0]
    assert "<redacted>" in result.errors[0]


def test_discovery_selection_looks_past_first_non_usable_scenario() -> None:
    usable = _evidence()
    usable.scenario_id = 502
    no_runtime = deepcopy(usable)
    no_runtime.scenario_id = 501
    no_runtime.raw_candidates = ()
    no_runtime.runtime_candidates = ()
    no_runtime.blocked_candidates = ()

    selected = runner.select_discovery_evidences([no_runtime, usable], limit=1)

    assert [item.scenario_id for item in selected] == [502]


def test_read_only_without_suitable_v4_scenario_is_coverage_limit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        runner,
        "_schema_preflight",
        lambda: runner.SchemaPreflight(verdict="PASS"),
    )
    monkeypatch.setattr(runner, "_discover_scenario_ids", lambda args: ([], []))

    result = asyncio.run(
        runner.run_campaign(_args(tmp_path / "read-only.md")),
    )

    assert result.verdict == "COVERAGE LIMIT"
    assert result.exit_code == 0


def test_unscoped_execute_fails_before_db_or_write(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    preflight_called = False
    execution_called = False

    def forbidden_preflight() -> runner.SchemaPreflight:
        nonlocal preflight_called
        preflight_called = True
        return runner.SchemaPreflight(verdict="PASS")

    async def forbidden_execution(
        evidences: list[runner.ScenarioEvidence],
    ) -> dict[int, dict[str, Any]]:
        nonlocal execution_called
        execution_called = True
        return {}

    monkeypatch.setattr(runner, "_schema_preflight", forbidden_preflight)
    monkeypatch.setattr(runner, "execute_targets", forbidden_execution)
    args = runner.build_parser().parse_args(
        ["--execute", "--report-path", str(tmp_path / "unscoped.md")],
    )

    result = asyncio.run(runner.run_campaign(args))

    assert result.verdict == "FAIL"
    assert preflight_called is False
    assert execution_called is False
    assert any("명시 범위가 필수" in message for message in result.scope_errors)


def test_existing_report_is_not_overwritten_and_fails_before_db_preflight(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    preflight_called = False

    def forbidden_preflight() -> runner.SchemaPreflight:
        nonlocal preflight_called
        preflight_called = True
        return runner.SchemaPreflight(verdict="PASS")

    report_path = tmp_path / "existing-report.md"
    report_path.write_text("retain this report", encoding="utf-8")
    monkeypatch.setattr(runner, "_schema_preflight", forbidden_preflight)
    args = runner.build_parser().parse_args(
        ["--report-path", str(report_path)],
    )

    with pytest.raises(FileExistsError):
        asyncio.run(runner.run_campaign(args))

    assert preflight_called is False
    assert report_path.read_text(encoding="utf-8") == "retain this report"


def test_explicit_nonmatching_scenario_is_fail(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        runner,
        "_schema_preflight",
        lambda: runner.SchemaPreflight(verdict="PASS"),
    )
    monkeypatch.setattr(
        runner,
        "_discover_scenario_ids",
        lambda args: ([], ["requested scenario is not v4"]),
    )

    args = runner.build_parser().parse_args(
        [
            "--scenario-id",
            "999",
            "--report-path",
            str(tmp_path / "explicit-miss.md"),
        ],
    )
    result = asyncio.run(runner.run_campaign(args))

    assert result.verdict == "FAIL"
    assert result.exit_code == 1


def test_explicit_group_scope_rejects_redirected_loaded_evidence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    evidence = _evidence()
    monkeypatch.setattr(
        runner,
        "_schema_preflight",
        lambda: runner.SchemaPreflight(verdict="PASS"),
    )
    monkeypatch.setattr(runner, "_discover_scenario_ids", lambda args: ([501], []))
    monkeypatch.setattr(
        runner,
        "_load_scenario_evidences",
        lambda ids: ([evidence], []),
    )
    args = runner.build_parser().parse_args(
        [
            "--scenario-group-id",
            "999",
            "--execute",
            "--report-path",
            str(tmp_path / "redirected-group.md"),
        ],
    )

    result = asyncio.run(runner.run_campaign(args))

    assert result.verdict == "FAIL"
    assert result.executions == {}
    assert any("명시 범위와 불일치" in message for message in result.scope_errors)


def test_auto_discovery_preserves_context_load_errors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    evidence = _evidence()
    monkeypatch.setattr(
        runner,
        "_schema_preflight",
        lambda: runner.SchemaPreflight(verdict="PASS"),
    )
    monkeypatch.setattr(
        runner,
        "_discover_scenario_ids",
        lambda args: ([501, 502], []),
    )
    monkeypatch.setattr(
        runner,
        "_load_scenario_evidences",
        lambda ids: ([evidence], ["scenario_id=502 catalog checksum mismatch"]),
    )

    result = asyncio.run(
        runner.run_campaign(_args(tmp_path / "context-errors.md")),
    )

    assert result.verdict == "FAIL"
    assert any("scenario_id=502" in message for message in result.scope_errors)


def test_failed_core_smoke_blocks_all_execution(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    evidence = _evidence()
    execution_called = False

    async def forbidden_execution(
        evidences: list[runner.ScenarioEvidence],
    ) -> dict[int, dict[str, Any]]:
        nonlocal execution_called
        execution_called = True
        return {}

    monkeypatch.setattr(
        runner,
        "_schema_preflight",
        lambda: runner.SchemaPreflight(verdict="PASS"),
    )
    monkeypatch.setattr(runner, "_discover_scenario_ids", lambda args: ([501], []))
    monkeypatch.setattr(
        runner,
        "_load_scenario_evidences",
        lambda ids: ([evidence], []),
    )
    monkeypatch.setattr(
        runner,
        "run_core_smoke",
        lambda timeout: runner.CoreSmokeEvidence(
            status="FAIL",
            message="core failed",
        ),
    )
    monkeypatch.setattr(runner, "execute_targets", forbidden_execution)

    result = asyncio.run(
        runner.run_campaign(_args(tmp_path / "blocked.md", execute=True)),
    )

    assert result.verdict == "FAIL"
    assert execution_called is False


def test_missing_eligible_execution_record_is_fail(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    evidence = _evidence()

    async def missing_execution(
        evidences: list[runner.ScenarioEvidence],
    ) -> dict[int, dict[str, Any]]:
        return {}

    monkeypatch.setattr(
        runner,
        "_schema_preflight",
        lambda: runner.SchemaPreflight(verdict="PASS"),
    )
    monkeypatch.setattr(runner, "_discover_scenario_ids", lambda args: ([501], []))
    monkeypatch.setattr(
        runner,
        "_load_scenario_evidences",
        lambda ids: ([evidence], []),
    )
    monkeypatch.setattr(
        runner,
        "run_core_smoke",
        lambda timeout: runner.CoreSmokeEvidence(status="PASS"),
    )
    monkeypatch.setattr(runner, "execute_targets", missing_execution)

    result = asyncio.run(
        runner.run_campaign(_args(tmp_path / "missing.md", execute=True)),
    )

    assert result.verdict == "FAIL"
    assert any("execution record 누락" in message for message in result.scope_errors)


def test_coverage_row_fail_is_included_in_overall_verdict(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    evidence = _evidence()
    record = _execution_record(evidence)

    async def one_execution(
        evidences: list[runner.ScenarioEvidence],
    ) -> dict[int, dict[str, Any]]:
        return {evidence.scenario_id: record}

    coverage_failure = runner.CoverageRow(
        scenario_id=evidence.scenario_id,
        parameter_name="GDP",
        classification="runtime-allowed",
        raw=1,
        runtime=0,
        selected=0,
        proposed=0,
        confirmed=0,
        exclusion_reason="",
        verdict="FAIL",
        evidence="forced coverage failure",
    )
    monkeypatch.setattr(
        runner,
        "_schema_preflight",
        lambda: runner.SchemaPreflight(verdict="PASS"),
    )
    monkeypatch.setattr(runner, "_discover_scenario_ids", lambda args: ([501], []))
    monkeypatch.setattr(
        runner,
        "_load_scenario_evidences",
        lambda ids: ([evidence], []),
    )
    monkeypatch.setattr(
        runner,
        "run_core_smoke",
        lambda timeout: runner.CoreSmokeEvidence(status="PASS"),
    )
    monkeypatch.setattr(runner, "execute_targets", one_execution)
    monkeypatch.setattr(
        runner,
        "build_coverage_rows",
        lambda evidence, record, assessment: [coverage_failure],
    )

    result = asyncio.run(
        runner.run_campaign(_args(tmp_path / "coverage-fail.md", execute=True)),
    )

    assert result.verdict == "FAIL"


@pytest.mark.parametrize(
    ("verdict", "exit_code"),
    [
        ("PASS", 0),
        ("REVIEW", 0),
        ("COVERAGE LIMIT", 0),
        ("FAIL", 1),
    ],
)
def test_cli_exit_code_only_fails_for_mandatory_fail(
    verdict: runner.Verdict,
    exit_code: int,
    tmp_path: Path,
) -> None:
    result = runner.CampaignResult(
        verdict=verdict,
        report_path=tmp_path / "report.md",
        preflight=runner.SchemaPreflight(verdict="PASS"),
        core_smoke=runner.CoreSmokeEvidence(status="NOT RUN"),
        evidences=(),
        executions={},
        assessments=(),
    )

    assert result.exit_code == exit_code


def test_report_contains_v4_catalog_and_allowlist_boundary() -> None:
    evidence = _evidence()
    record = _execution_record(evidence)
    assessment = runner.assess_execution(evidence, record)

    report = runner.render_report(
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        execute=True,
        verdict=assessment.verdict,
        preflight=runner.SchemaPreflight(verdict="PASS"),
        core_smoke=runner.CoreSmokeEvidence(status="PASS"),
        evidences=[evidence],
        executions={evidence.scenario_id: record},
        assessments=[assessment],
        scope_errors=[],
    )

    assert "v4 Multi-Event" in report
    assert "Catalog-pinned selected Lever evidence" in report
    assert "active-but-blocked" in report
    assert PROPOSAL_SCOPE_EXCLUDED_REASON_CODE in report
    assert "9001" in report
    assert "Prompt tokens" in report
    assert "120" in report


def test_report_retains_partial_proposal_id_and_failed_stage() -> None:
    evidence = _evidence()
    record = {
        "scenario_id": evidence.scenario_id,
        "model_param_proposal_id": 9002,
        "failed_stage": "proposal DB read-back",
        "execution_attempt_count": 1,
        "error": "read-back failed",
    }
    assessment = runner.assess_execution(evidence, record)

    report = runner.render_report(
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        execute=True,
        verdict=assessment.verdict,
        preflight=runner.SchemaPreflight(verdict="PASS"),
        core_smoke=runner.CoreSmokeEvidence(status="PASS"),
        evidences=[evidence],
        executions={evidence.scenario_id: record},
        assessments=[assessment],
        scope_errors=[],
    )

    assert "9002" in report
    assert "proposal DB read-back" in report
    assert "failed_stage=proposal DB read-back" in report
