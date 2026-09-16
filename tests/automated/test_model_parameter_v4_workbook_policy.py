# Copyright (c) 2026 SK Innovation E&S.

from __future__ import annotations

# ruff: noqa: ANN401, FBT001, S101, SLF001
from collections.abc import Mapping
import math
import os
from types import MappingProxyType, SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest


os.environ.setdefault("METADATA_DB_PORT", "3306")

from apps.agents.model_parameter_agent.flows.propose_parameters import nodes
from apps.agents.model_parameter_agent.flows.propose_parameters.state import (
    ModelParameterProposalState,
)
from apps.agents.model_parameter_agent.schemas.model_parameter_proposal import (
    LLMValueAdjustment,
    LLMValueCell,
)
from apps.agents.model_parameter_agent.utils.lut import build_basecase_index
from apps.agents.model_parameter_agent.utils.lut.catalog import LutCatalog
from apps.agents.model_parameter_agent.utils.lut.keys import canonical_key_from_axes
from apps.agents.model_parameter_agent.utils.lut.models import (
    LutRecord,
    ReferenceLoadPolicy,
    freeze_mapping,
)
from apps.agents.model_parameter_agent.utils.proposal_policy import (
    POWER_MIX_ENERGY_SOURCES,
    evaluate_liq_util_evidence,
    expand_power_mix_atomic_slots,
    has_specific_time_evidence,
    time_evidence_matches_slot,
)
from apps.agents.model_parameter_agent.utils.resource_runtime import (
    get_model_parameter_resource_paths,
)
from apps.common.exceptions.custom import MIBaseError


V4_CONTEXT = {
    "scenario_group": {
        "api_version": "v4",
        "generation_strategy": "multi_event_model_lever_dimensions",
    },
}


def _candidate(parameter_name: str, candidate_key: str) -> dict[str, Any]:
    return {
        "candidate_key": candidate_key,
        "mapping_strategy": "v4",
        "canonical_parameter_name": parameter_name,
        "parameter_name": parameter_name,
        "model_file": "Supply" if parameter_name == "LiqUtilAdjustment" else "Demand",
        "model_sheet": f"{parameter_name}Adjustment",
        "model_table": "table1",
        "basecase_column_roles": (
            "B:Country,C:LNG Plant,D:LNG Plant Train,E:Life Cycle Category,"
            "F:Nameplate Capacity (MTPA),G:LiqUtilAdjustment"
            if parameter_name == "LiqUtilAdjustment"
            else "A:Country,B:Year,C:Energy Source,D:PowerMix"
        ),
    }


def _slot(candidate_key: str, axes: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "candidate_key": candidate_key,
        "slot_axes": [{"axis_name": axis_name, "axis_value": axis_value} for axis_name, axis_value in axes.items()],
    }


def _reference(
    candidate_key: str,
    parameter_name: str,
    axes: Mapping[str, Any],
    value: float,
) -> dict[str, Any]:
    return {
        "candidate_key": candidate_key,
        "parameter_name": parameter_name,
        "axes": dict(axes),
        "metadata": {},
        "actual_basecase_value": value,
        "lut_default_value": None,
        "llm_reference_value": value,
        "effective_source": "basecase",
        "basecase_reference_id": f"base:{candidate_key}:{len(str(axes))}",
        "lut_reference_id": None,
        "lut_version": None,
        "slot_key": "",
    }


def _liq_candidate(*, source_event_ids: list[int] | None = None) -> dict[str, Any]:
    candidate = _candidate("LiqUtilAdjustment", "liq")
    candidate.update(
        {
            "source_event_ids": source_event_ids or [101],
            "lever_code": "liquefaction_availability",
            "lever_provenance": [
                {
                    "scenario_dimension_key": "freeport_outage",
                    "source_event_ids": source_event_ids or [101],
                    "lever_code": "liquefaction_availability",
                    "direction": "decrease",
                    "scope": "Freeport LNG / Freeport LNG T1",
                    "time_window": "2027 Q2",
                },
            ],
            "source_dimensions": [
                {
                    "scenario_dimension_key": "freeport_outage",
                    "source_dimension_description": "Freeport LNG outage severity",
                },
            ],
        },
    )
    return candidate


def _liq_slot() -> dict[str, Any]:
    return _slot(
        "liq",
        {
            "Country": "United States",
            "LNG Plant": "Freeport LNG",
            "LNG Plant Train": "Freeport LNG T1",
            "Year": 2027,
            "Month": 5,
        },
    )


def test_liq_util_evidence_requires_one_linked_facility_specific_provenance() -> None:
    context = {
        "events": [
            {
                "mi_event_id": 101,
                "event_title": "Freeport LNG outage extends through May 2027",
                "description": "Train availability remains constrained.",
            },
        ],
    }

    decision = evaluate_liq_util_evidence(_liq_candidate(), _liq_slot(), context)

    assert decision.allowed is True
    assert decision.missing_components == ()


@pytest.mark.parametrize(
    ("mutation", "missing_component"),
    [
        (lambda candidate: candidate["lever_provenance"][0].update(direction="unchanged"), "direction"),
        (lambda candidate: candidate["lever_provenance"][0].update(time_window="단기"), "specific_time_window"),
        (
            lambda candidate: (
                candidate["lever_provenance"][0].update(scope="global LNG market"),
                candidate["source_dimensions"][0].update(
                    source_dimension_description="Generic outage severity",
                ),
            ),
            "specific_facility_evidence",
        ),
    ],
)
def test_liq_util_evidence_fails_closed_when_component_is_missing(
    mutation: Any,
    missing_component: str,
) -> None:
    candidate = _liq_candidate()
    mutation(candidate)
    context = {
        "events": [
            {
                "mi_event_id": 101,
                "event_title": "Generic LNG market update",
            },
        ],
    }

    decision = evaluate_liq_util_evidence(candidate, _liq_slot(), context)

    assert decision.allowed is False
    assert missing_component in decision.missing_components


def test_liq_util_evidence_ignores_facility_text_from_unlinked_event() -> None:
    context = {
        "events": [
            {"mi_event_id": 101, "event_title": "Generic LNG market update"},
            {"mi_event_id": 202, "event_title": "Freeport LNG outage in 2027"},
        ],
    }
    candidate = _liq_candidate(source_event_ids=[101])
    candidate["lever_provenance"][0]["scope"] = "United States"
    candidate["source_dimensions"][0]["source_dimension_description"] = "Generic outage severity"

    decision = evaluate_liq_util_evidence(candidate, _liq_slot(), context)

    assert decision.allowed is False
    assert "specific_facility_evidence" in decision.missing_components


def test_liq_util_evidence_requires_explicit_lineage_and_matching_slot_period() -> None:
    context = {
        "events": [
            {
                "mi_event_id": 101,
                "event_title": "Freeport LNG T1 outage in 2027 Q2",
            },
        ],
    }
    candidate = _liq_candidate()
    candidate_without_lineage = {**candidate, "lever_provenance": []}

    absent = evaluate_liq_util_evidence(candidate_without_lineage, _liq_slot(), context)
    mismatch = evaluate_liq_util_evidence(
        candidate,
        _slot(
            "liq",
            {
                "Country": "United States",
                "LNG Plant": "Freeport LNG",
                "LNG Plant Train": "Freeport LNG T1",
                "Year": 2030,
                "Month": 12,
            },
        ),
        context,
    )

    assert absent.allowed is False
    assert "lever_provenance" in absent.missing_components
    assert mismatch.allowed is False
    assert "specific_time_window" in mismatch.missing_components


def test_liq_util_partial_abstention_keeps_internal_slot_diagnostic() -> None:
    candidate = _liq_candidate()
    may_axes = {
        "Country": "United States",
        "LNG Plant": "Freeport LNG",
        "LNG Plant Train": "Freeport LNG T1",
        "Year": 2027,
        "Month": 5,
    }
    december_axes = {**may_axes, "Month": 12}
    registry = get_model_parameter_resource_paths().lut_registry
    basecase_index = build_basecase_index(
        [
            {
                "candidate_key": "liq",
                "parameter_name": "LiqUtilAdjustment",
                "reference_id": "base:liq:may",
                "axes": {
                    **may_axes,
                    "Period": 17,
                    "Life Cycle Category": "Operational",
                    "Nameplate Capacity (MTPA)": 5.0,
                },
                "value": 0.9,
            },
            {
                "candidate_key": "liq",
                "parameter_name": "LiqUtilAdjustment",
                "reference_id": "base:liq:december",
                "axes": {
                    **december_axes,
                    "Period": 24,
                    "Life Cycle Category": "Operational",
                    "Nameplate Capacity (MTPA)": 5.0,
                },
                "value": 0.9,
            },
        ],
        [candidate],
        registry=registry,
    )
    state = ModelParameterProposalState(
        scenario_id=501,
        scenario_context={
            **V4_CONTEXT,
            "events": [
                {
                    "mi_event_id": 101,
                    "event_title": "Freeport LNG T1 outage in 2027 Q2",
                },
            ],
        },
        candidate_mappings=[candidate],
        parameter_slots=[_slot("liq", may_axes), _slot("liq", december_axes)],
        basecase_index=basecase_index,
        resolved_config={"model_parameter_lut_enabled": False},
    )

    result = nodes.filter_basecase_records_by_slots(state)

    assert len(result["parameter_slots"]) == 1
    diagnostic = result["non_input_items"][0]
    assert diagnostic["reason_code"] == "ABSTAINED_INSUFFICIENT_EVIDENCE"
    assert diagnostic["excluded_slot_count"] == 1
    assert diagnostic["partial_candidate"] is True
    assert any("ABSTAINED_INSUFFICIENT_EVIDENCE" in item for item in result["validation_warnings"])


@pytest.mark.parametrize(
    ("period", "year", "month"),
    [
        ("2027년 하반기", 2027, 8),
        ("2027 H2", 2027, 8),
        ("2027 Q2", 2027, 5),
        ("2027년 2분기", 2027, 5),
        ("May 2027", 2027, 5),
    ],
)
def test_specific_time_policy_accepts_supported_clear_periods(
    period: str,
    year: int,
    month: int,
) -> None:
    assert has_specific_time_evidence(period)
    assert time_evidence_matches_slot(period, year=year, month=month)


@pytest.mark.parametrize(
    ("period", "anchor_year", "anchor_month", "year", "month", "expected"),
    [
        ("6개월", 2026, 1, 2026, 6, True),
        ("6개월", 2026, 1, 2026, 7, False),
        ("내년", 2026, 5, 2027, 12, True),
        ("내년", 2026, 5, 2030, 12, False),
        ("다음 달", 2026, 12, 2027, 1, True),
        ("다음 달", 2026, 12, 2027, 2, False),
        ("올해 하반기", 2026, 9, 2026, 1, False),
        ("올해 하반기", 2026, 9, 2026, 8, True),
        ("내년 상반기", 2026, 9, 2027, 5, True),
        ("내년 상반기", 2026, 9, 2027, 7, False),
        ("내년 Q2", 2026, 9, 2027, 5, True),
        ("내년 Q2", 2026, 9, 2027, 10, False),
        ("올해 2분기", 2026, 9, 2026, 4, True),
        ("올해 2분기", 2026, 9, 2026, 10, False),
    ],
)
def test_relative_time_policy_is_bounded_by_calendar_anchor(
    period: str,
    anchor_year: int,
    anchor_month: int,
    year: int,
    month: int,
    expected: bool,
) -> None:
    assert (
        time_evidence_matches_slot(
            period,
            year=year,
            month=month,
            anchor_year=anchor_year,
            anchor_month=anchor_month,
        )
        is expected
    )


@pytest.mark.parametrize(
    ("period", "year", "month", "expected"),
    [
        ("2027-05", 2027, 5, True),
        ("2027/05", 2027, 12, False),
        ("2027.05", 2027, 4, False),
        ("2027 Q2", 2027, 12, False),
        ("2027 H2", 2027, 1, False),
        ("2027년 1분기", 2027, 3, True),
        ("2027년 1분기", 2027, 4, False),
        ("2027년 4분기", 2027, 10, True),
        ("2027년 4분기", 2027, 4, False),
        ("2027-2028", 2027, 1, True),
        ("2027-2028", 2027, 6, True),
        ("2027-2028", 2028, 12, True),
        ("2027-2028", 2029, 2, False),
        ("2027 - 2028", 2028, 2, True),
        ("Q4 2027 - Q1 2028", 2027, 11, True),
        ("Q4 2027 - Q1 2028", 2028, 2, True),
        ("Q4 2027 - Q1 2028", 2027, 2, False),
        ("Q4 2027 - Q1 2028", 2028, 11, False),
    ],
)
def test_specific_time_policy_requires_explicit_month_match(
    period: str,
    year: int,
    month: int,
    expected: bool,
) -> None:
    assert time_evidence_matches_slot(period, year=year, month=month) is expected


@pytest.mark.parametrize(
    "period",
    [
        "2027-00",
        "2027-13",
        "2027/13",
        "2027.00",
        "2027년 13월",
        "2027 Q5",
        "Q0 2027",
        "2027 H3",
        "2027년 5분기",
        "2028-2027",
    ],
)
def test_specific_time_policy_rejects_malformed_absolute_period(period: str) -> None:
    assert time_evidence_matches_slot(period, year=2027, month=6) is False


@pytest.mark.parametrize(
    ("period", "year", "month"),
    [
        ("올해 13월", 2026, 6),
        ("내년 0월", 2027, 6),
        ("-1개월", 2026, 9),
        ("-6 months", 2026, 9),
        ("1.5개월", 2026, 9),
        ("12.5 months", 2026, 9),
    ],
)
def test_relative_time_policy_rejects_malformed_period(
    period: str,
    year: int,
    month: int,
) -> None:
    assert (
        time_evidence_matches_slot(
            period,
            year=year,
            month=month,
            anchor_year=2026,
            anchor_month=9,
        )
        is False
    )


def _power_mix_records(
    candidate_key: str = "power",
    *,
    year: int = 2027,
) -> list[dict[str, Any]]:
    values = (0.03, 0.12, 0.08, 0.09, 0.03, 0.35, 0.16, 0.12, 0.01, 0.01)
    return [
        {
            "candidate_key": candidate_key,
            "parameter_name": "PowerMix",
            "reference_id": f"new-bc:PowerMix:Japan:{year}:{source}",
            "axes": {"Country": "Japan", "Year": year, "Energy Source": source},
            "value": value,
        }
        for source, value in zip(POWER_MIX_ENERGY_SOURCES, values, strict=True)
    ]


def test_power_mix_seed_expands_to_complete_authoritative_vector() -> None:
    candidate = _candidate("PowerMix", "power")
    registry = get_model_parameter_resource_paths().lut_registry
    basecase_index = build_basecase_index(
        _power_mix_records(),
        [candidate],
        registry=registry,
    )

    expanded, warnings = expand_power_mix_atomic_slots(
        [_slot("power", {"Country": "Japan", "Year": 2027, "Energy Source": "Gas"})],
        [candidate],
        basecase_index,
        None,
    )

    assert not warnings
    assert len(expanded) == 10
    assert [slot["slot_axes"][2]["axis_value"] for slot in expanded] == list(POWER_MIX_ENERGY_SOURCES)


@pytest.mark.parametrize(
    "slot_axes",
    [
        [
            {"axis_name": "Country", "axis_value": "Japan"},
            {"axis_name": "Year", "axis_value": 2027},
            {"axis_name": "Energy Source", "axis_value": "Gas"},
            {"axis_name": "Unexpected", "axis_value": "ignored"},
        ],
        [
            {"axis_name": "Country", "axis_value": "Wrong"},
            {"axis_name": "Country", "axis_value": "Japan"},
            {"axis_name": "Year", "axis_value": 2027},
            {"axis_name": "Energy Source", "axis_value": "Gas"},
        ],
        [
            {"axis_name": "Country", "axis_value": "Japan"},
            {"axis_name": "Year", "axis_value": 2027},
        ],
        [
            {"axis_name": "Country", "axis_value": "Japan"},
            {"axis_name": "Year", "axis_value": 2027.5},
            {"axis_name": "Energy Source", "axis_value": "Gas"},
        ],
        [
            {"axis_name": "Country", "axis_value": "Japan"},
            {"axis_name": "Year", "axis_value": 2027},
            {"axis_name": "Energy Source", "axis_value": "Hydrogen"},
        ],
    ],
)
def test_power_mix_expansion_rejects_malformed_seed_before_rewrite(
    slot_axes: list[dict[str, Any]],
) -> None:
    candidate = _candidate("PowerMix", "power")
    registry = get_model_parameter_resource_paths().lut_registry
    basecase_index = build_basecase_index(
        _power_mix_records(),
        [candidate],
        registry=registry,
    )

    expanded, warnings = expand_power_mix_atomic_slots(
        [{"candidate_key": "power", "slot_axes": slot_axes}],
        [candidate],
        basecase_index,
        None,
    )

    assert expanded == []
    assert len(warnings) == 1
    assert "canonical exact key" in warnings[0]


def test_power_mix_expansion_uses_same_exact_key_lut_fallback() -> None:
    candidate = _candidate("PowerMix", "power")
    registry = get_model_parameter_resource_paths().lut_registry
    policy = ReferenceLoadPolicy()
    basecase_records = _power_mix_records()[:-1]
    basecase_index = build_basecase_index(
        basecase_records,
        [candidate],
        registry=registry,
        policy=policy,
    )
    axes = {"Country": "Japan", "Year": 2027, "Energy Source": "Other"}
    lut_record = LutRecord(
        parameter_name="PowerMix",
        canonical_key=canonical_key_from_axes(axes, ("Country", "Year", "Energy Source")),
        axes=freeze_mapping(axes),
        value=0.01,
        metadata=freeze_mapping(),
        reference_id="lut:PowerMix:Japan:2027:Other",
    )
    lut_catalog = LutCatalog(
        version="test",
        policy=policy,
        registry=registry,
        records=(lut_record,),
        diagnostics=(),
        _by_parameter=MappingProxyType(
            {"PowerMix": MappingProxyType({lut_record.canonical_key: lut_record})},
        ),
    )

    expanded, warnings = expand_power_mix_atomic_slots(
        [_slot("power", {"Country": "Japan", "Year": 2027, "Energy Source": "Gas"})],
        [candidate],
        basecase_index,
        lut_catalog,
    )

    assert not warnings
    assert len(expanded) == 10


def test_power_mix_expansion_preserves_authoritative_source_precision() -> None:
    candidate = _candidate("PowerMix", "power")
    registry = get_model_parameter_resource_paths().lut_registry
    values = [0.100009] * 9 + [0.099919]
    records = _power_mix_records()
    for record, value in zip(records, values, strict=True):
        record["value"] = value
        record["_preserve_reference_precision"] = True
    basecase_index = build_basecase_index(records, [candidate], registry=registry)

    expanded, warnings = expand_power_mix_atomic_slots(
        [_slot("power", {"Country": "Japan", "Year": 2027, "Energy Source": "Gas"})],
        [candidate],
        basecase_index,
        None,
    )

    assert math.fsum(float(record.value) for record in basecase_index.records_for_candidate("power")) == pytest.approx(
        1.0,
    )
    assert not warnings
    assert len(expanded) == 10


def test_power_mix_expansion_rejects_non_normalized_effective_vector() -> None:
    candidate = _candidate("PowerMix", "power")
    registry = get_model_parameter_resource_paths().lut_registry
    values = [0.100009] * 9 + [0.099919]
    records = _power_mix_records()
    for record, value in zip(records, values, strict=True):
        record["value"] = value
    basecase_index = build_basecase_index(records, [candidate], registry=registry)

    expanded, warnings = expand_power_mix_atomic_slots(
        [_slot("power", {"Country": "Japan", "Year": 2027, "Energy Source": "Gas"})],
        [candidate],
        basecase_index,
        None,
    )

    assert expanded == []
    assert len(warnings) == 1
    assert "atomic group" in warnings[0]


@pytest.mark.parametrize(
    ("limit", "expected_slot_count"),
    [(9, 0), (10, 10), (15, 10), (20, 20)],
)
def test_power_mix_parameter_limit_reserves_each_atomic_group_once(
    limit: int,
    expected_slot_count: int,
) -> None:
    candidate = _candidate("PowerMix", "power")
    registry = get_model_parameter_resource_paths().lut_registry
    basecase_index = build_basecase_index(
        [
            *(_power_mix_records(year=2027)),
            *(_power_mix_records(year=2028)),
        ],
        [candidate],
        registry=registry,
    )
    state = ModelParameterProposalState(
        scenario_id=502,
        scenario_context=V4_CONTEXT,
        candidate_mappings=[candidate],
        parameter_slots=[
            _slot("power", {"Country": "Japan", "Year": 2027, "Energy Source": "Gas"}),
            _slot("power", {"Country": "Japan", "Year": 2028, "Energy Source": "Gas"}),
        ],
        basecase_index=basecase_index,
        resolved_config={"model_parameter_lut_enabled": False},
    )
    settings = SimpleNamespace(
        model_parameter_max_parameter_slots=limit,
        model_parameter_max_value_prompt_basecase_records=limit,
        model_parameter_max_total_selected_slots=300,
    )

    with patch.object(nodes, "get_settings", return_value=settings):
        result = nodes.filter_basecase_records_by_slots(state)

    assert len(result["parameter_slots"]) == expected_slot_count
    assert len(result["effective_references"]) == expected_slot_count


@pytest.mark.parametrize(
    ("scenario_context", "expected_preserved_parameters", "expected_slot_count"),
    [
        (V4_CONTEXT, frozenset({"PowerMix"}), 10),
        (
            {
                "scenario_group": {
                    "api_version": "v3",
                    "generation_strategy": "multi_event_composite_dimensions",
                },
            },
            frozenset(),
            1,
        ),
    ],
)
def test_power_mix_lut_precision_override_is_exact_v4_only(
    scenario_context: dict[str, Any],
    expected_preserved_parameters: frozenset[str],
    expected_slot_count: int,
) -> None:
    candidate = _candidate("PowerMix", "power")
    registry = get_model_parameter_resource_paths().lut_registry
    basecase_index = build_basecase_index(
        _power_mix_records(),
        [candidate],
        registry=registry,
    )
    state = ModelParameterProposalState(
        scenario_id=503,
        scenario_context=scenario_context,
        candidate_mappings=[candidate],
        parameter_slots=[
            _slot("power", {"Country": "Japan", "Year": 2027, "Energy Source": "Gas"}),
        ],
        basecase_index=basecase_index,
        resolved_config={"model_parameter_lut_enabled": True},
    )
    settings = SimpleNamespace(
        model_parameter_max_parameter_slots=100,
        model_parameter_max_value_prompt_basecase_records=100,
        model_parameter_max_total_selected_slots=300,
    )

    with (
        patch.object(nodes, "get_settings", return_value=settings),
        patch.object(nodes, "get_lut_catalog", return_value=None) as get_lut_catalog,
    ):
        result = nodes.filter_basecase_records_by_slots(state)

    assert len(result["parameter_slots"]) == expected_slot_count
    assert get_lut_catalog.call_args.kwargs["preserve_value_precision_parameters"] == (expected_preserved_parameters)


def test_missing_metadata_is_only_allowed_for_marked_v4_axis() -> None:
    candidate = _candidate("LiqUtilAdjustment", "liq")
    registry = get_model_parameter_resource_paths().lut_registry
    axes = {
        "Country": "United Kingdom",
        "LNG Plant": "Tilbury LNG",
        "LNG Plant Train": "Tilbury LNG T1",
        "Year": 2026,
        "Month": 1,
        "Period": 1,
        "Nameplate Capacity (MTPA)": 0.0,
    }
    record = {
        "candidate_key": "liq",
        "parameter_name": "LiqUtilAdjustment",
        "reference_id": "new-bc:liq:tilbury",
        "axes": axes,
        "value": 0.0,
    }

    with pytest.raises(MIBaseError, match="Life Cycle Category"):
        build_basecase_index([record], [candidate], registry=registry)

    marked_record = {
        **record,
        "_allow_missing_metadata_axes": ("Life Cycle Category",),
    }
    index = build_basecase_index([marked_record], [candidate], registry=registry)

    indexed = index.records_for_candidate("liq")[0]
    assert indexed.metadata == {"Period": 1, "Nameplate Capacity (MTPA)": 0}


def _power_mix_step3_fixture() -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    candidate = _candidate("PowerMix", "power")
    slots: list[dict[str, Any]] = []
    references: list[dict[str, Any]] = []
    for index, record in enumerate(_power_mix_records(), start=1):
        axes = record["axes"]
        slot = _slot("power", axes)
        slot["slot_key"] = f"slot-{index}"
        reference = _reference("power", "PowerMix", axes, float(record["value"]))
        reference["slot_key"] = f"slot-{index}"
        slots.append(slot)
        references.append(reference)
    return candidate, slots, references


def test_power_mix_step3_accepts_only_complete_normalized_vector() -> None:
    candidate, slots, references = _power_mix_step3_fixture()
    adjustment = LLMValueAdjustment(
        candidate_key="power",
        rationale_ko="전체 vector 유지",
        slot_values=[
            LLMValueCell(
                slot_key=f"slot-{index}",
                proposed_value=reference["llm_reference_value"],
                rationale_ko="atomic member",
            )
            for index, reference in enumerate(references, start=1)
        ],
    )

    sanitized, warnings = nodes._sanitize_llm_adjustments(
        [adjustment],
        [candidate],
        slots,
        references,
        scenario_context=V4_CONTEXT,
    )

    assert not warnings
    assert len(sanitized[0]["value_grid"]) == 10


def test_power_mix_step3_drops_partial_vector_atomically() -> None:
    candidate, slots, references = _power_mix_step3_fixture()
    adjustment = LLMValueAdjustment(
        candidate_key="power",
        rationale_ko="부분 vector",
        slot_values=[
            LLMValueCell(
                slot_key=f"slot-{index}",
                proposed_value=reference["llm_reference_value"],
                rationale_ko="partial member",
            )
            for index, reference in enumerate(references[:-1], start=1)
        ],
    )

    sanitized, warnings = nodes._sanitize_llm_adjustments(
        [adjustment],
        [candidate],
        slots,
        references,
        scenario_context=V4_CONTEXT,
    )

    assert sanitized == []
    assert any("atomic group 전체" in warning for warning in warnings)


def test_v4_liq_util_rejects_negative_but_preserves_over_utilisation() -> None:
    candidate = _liq_candidate()
    axes = {
        "Country": "United States",
        "LNG Plant": "Freeport LNG",
        "LNG Plant Train": "Freeport LNG T1",
        "Year": 2027,
        "Month": 5,
    }
    slots = [_slot("liq", axes), _slot("liq", {**axes, "Month": 6})]
    references = [
        {**_reference("liq", "LiqUtilAdjustment", slot_axes, 0.9), "slot_key": f"slot-{index}"}
        for index, slot_axes in enumerate((axes, {**axes, "Month": 6}), start=1)
    ]
    adjustment = LLMValueAdjustment(
        candidate_key="liq",
        rationale_ko="over-utilisation 보존",
        slot_values=[
            LLMValueCell(slot_key="slot-1", proposed_value=1.1, rationale_ko="정상 초과 가동"),
            LLMValueCell(slot_key="slot-2", proposed_value=-0.1, rationale_ko="음수"),
        ],
    )

    sanitized, warnings = nodes._sanitize_llm_adjustments(
        [adjustment],
        [candidate],
        slots,
        references,
        scenario_context=V4_CONTEXT,
    )

    assert [cell["proposed_value"] for cell in sanitized[0]["value_grid"]] == [1.1]
    assert any("음수" in warning for warning in warnings)


def test_new_value_constraints_do_not_apply_without_exact_v4_context() -> None:
    candidate, slots, references = _power_mix_step3_fixture()
    adjustment = LLMValueAdjustment(
        candidate_key="power",
        rationale_ko="legacy partial behavior",
        slot_values=[
            LLMValueCell(
                slot_key="slot-1",
                proposed_value=references[0]["llm_reference_value"],
                rationale_ko="legacy member",
            ),
        ],
    )

    sanitized, warnings = nodes._sanitize_llm_adjustments(
        [adjustment],
        [candidate],
        slots,
        references,
        scenario_context={
            "scenario_group": {
                "api_version": "v3",
                "generation_strategy": "multi_event_model_lever_dimensions",
            },
        },
    )

    assert len(sanitized[0]["value_grid"]) == 1
    assert not any("atomic group 전체" in warning for warning in warnings)
