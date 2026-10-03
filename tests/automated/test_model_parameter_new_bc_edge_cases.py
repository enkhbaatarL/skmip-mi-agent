# Copyright (c) 2026 SK Innovation E&S.
# ruff: noqa: S101, SLF001

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from openpyxl import Workbook
from openpyxl.utils.cell import column_index_from_string
from openpyxl.worksheet.worksheet import Worksheet
import pytest

from apps.agents.model_parameter_agent.flows.propose_parameters import nodes
from apps.agents.model_parameter_agent.flows.propose_parameters.state import (
    ModelParameterProposalState,
)
from apps.agents.model_parameter_agent.schemas.model_parameter_proposal import (
    LLMValueAdjustment,
    LLMValueCell,
)
from apps.agents.model_parameter_agent.utils.lut import build_basecase_index
from apps.agents.model_parameter_agent.utils.proposal_policy import (
    POWER_MIX_ENERGY_SOURCES,
    evaluate_liq_util_evidence,
)
from apps.agents.model_parameter_agent.utils.resource_runtime import (
    get_model_parameter_resource_paths,
)
from apps.agents.model_parameter_agent.utils.workbook_contract import (
    load_workbook_contract,
)
from apps.agents.model_parameter_agent.utils.workbook_reference import (
    _power_mix_records as parse_power_mix_records,
    _year_column_records as parse_year_column_records,
)
from apps.common.exceptions.custom import MIBaseError


V1_CONTEXT = {
    "scenario_group": {
        "api_version": "v1",
        "generation_strategy": "single_event_template_dimensions",
    },
}
V3_CONTEXT = {
    "scenario_group": {
        "api_version": "v3",
        "generation_strategy": "multi_event_composite_dimensions",
    },
}
V4_CONTEXT = {
    "scenario_group": {
        "api_version": "v4",
        "generation_strategy": "multi_event_model_lever_dimensions",
    },
}
POWER_MIX_VALUES = {
    "Liquids": 0.03,
    "Hydro": 0.12,
    "Solar": 0.08,
    "Wind": 0.09,
    "Bioenergy": 0.03,
    "Gas": 0.35,
    "Coal": 0.16,
    "Nuclear": 0.12,
    "Geothermal": 0.01,
    "Other": 0.01,
}


def _candidate(parameter_name: str, candidate_key: str) -> dict[str, Any]:
    return {
        "candidate_key": candidate_key,
        "canonical_parameter_name": parameter_name,
        "parameter_name": parameter_name,
        "model_file": "Supply" if parameter_name == "LiqUtilAdjustment" else "Demand",
        "model_sheet": ("LiqUtilAdjustment" if parameter_name == "LiqUtilAdjustment" else "PowerMixAdjustment"),
        "model_table": "table1",
    }


def _slot(candidate_key: str, axes: Mapping[str, Any], *, slot_key: str | None = None) -> dict[str, Any]:
    slot = {
        "candidate_key": candidate_key,
        "slot_axes": [{"axis_name": axis_name, "axis_value": axis_value} for axis_name, axis_value in axes.items()],
    }
    if slot_key is not None:
        slot["slot_key"] = slot_key
    return slot


def _reference(
    candidate_key: str,
    parameter_name: str,
    axes: Mapping[str, Any],
    value: float,
    *,
    slot_key: str,
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
        "basecase_reference_id": f"base:{candidate_key}:{slot_key}",
        "lut_reference_id": None,
        "lut_version": None,
        "slot_key": slot_key,
    }


@pytest.mark.parametrize(
    "failure_mode",
    ["missing", "conflicting_duplicate", "nonfinite", "sum_only", "out_of_range"],
)
def test_power_mix_raw_failure_blocks_the_complete_approved_vector(
    failure_mode: str,
) -> None:
    contract = load_workbook_contract()
    parameter = contract.parameters["PowerMix"]
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = parameter.reference_source.sheet
    values: list[tuple[str, object]] = list(POWER_MIX_VALUES.items())

    if failure_mode == "missing":
        values = [item for item in values if item[0] != "Other"]
    elif failure_mode == "conflicting_duplicate":
        values.append(("Gas", 0.34))
    elif failure_mode == "nonfinite":
        values = [(member, "#REF!" if member == "Gas" else value) for member, value in values]
    elif failure_mode == "sum_only":
        values = [(member, 0.0 if member == "Other" else value) for member, value in values]
    elif failure_mode == "out_of_range":
        values = [
            (member, -0.01 if member == "Gas" else 0.52 if member == "Coal" else value) for member, value in values
        ]

    for row, (member, value) in enumerate(
        values,
        start=parameter.reference_source.data_start_row,
    ):
        worksheet[f"Z{row}"] = "Testland"
        worksheet[f"AA{row}"] = 2027
        worksheet[f"AB{row}"] = 1
        worksheet[f"AC{row}"] = member
        worksheet[f"AE{row}"] = value

    records, warnings, blocked_keys = parse_power_mix_records(
        contract,
        "PowerMix",
        parameter,
        worksheet,
    )
    workbook.close()

    expected_keys = frozenset(("Testland", 2027, member) for member in POWER_MIX_ENERGY_SOURCES)
    assert records == ()
    assert blocked_keys == expected_keys
    assert any("invalid atomic source vector" in warning for warning in warnings)


def _power_mix_step3_inputs() -> tuple[
    dict[str, Any],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    candidate = _candidate("PowerMix", "power")
    slots: list[dict[str, Any]] = []
    references: list[dict[str, Any]] = []
    for index, member in enumerate(POWER_MIX_ENERGY_SOURCES, start=1):
        slot_key = f"slot-{index}"
        axes = {"Country": "Japan", "Year": 2027, "Energy Source": member}
        slots.append(_slot("power", axes, slot_key=slot_key))
        references.append(
            _reference(
                "power",
                "PowerMix",
                axes,
                POWER_MIX_VALUES[member],
                slot_key=slot_key,
            ),
        )
    return candidate, slots, references


@pytest.mark.parametrize(
    "failure_mode",
    ["duplicate", "nonfinite", "sum_only", "out_of_range"],
)
def test_power_mix_step3_failure_drops_the_complete_vector(
    failure_mode: str,
) -> None:
    candidate, slots, references = _power_mix_step3_inputs()
    proposed_values: list[object] = [POWER_MIX_VALUES[member] for member in POWER_MIX_ENERGY_SOURCES]
    if failure_mode == "nonfinite":
        proposed_values[0] = "nan"
    elif failure_mode == "sum_only":
        proposed_values[-1] = 0.0
    elif failure_mode == "out_of_range":
        proposed_values[5] = -0.01
        proposed_values[6] = 0.52

    slot_values = [
        LLMValueCell(
            slot_key=f"slot-{index}",
            proposed_value=value,
            rationale_ko="atomic member",
        )
        for index, value in enumerate(proposed_values, start=1)
    ]
    if failure_mode == "duplicate":
        slot_values.append(
            LLMValueCell(
                slot_key="slot-1",
                proposed_value=POWER_MIX_VALUES["Liquids"],
                rationale_ko="duplicate member",
            ),
        )
    adjustment = LLMValueAdjustment(
        candidate_key="power",
        rationale_ko="invalid atomic vector",
        slot_values=slot_values,
    )

    sanitized, warnings = nodes._sanitize_llm_adjustments(
        [adjustment],
        [candidate],
        slots,
        references,
        scenario_context=V4_CONTEXT,
    )

    assert sanitized == []
    assert any("PowerMix Step3" in warning and "atomic group" in warning for warning in warnings)


def _set_year_column_row(
    worksheet: Worksheet,
    *,
    parameter_name: str,
    row: int,
    country: str,
    values_by_year: Mapping[int, object],
) -> None:
    contract = load_workbook_contract()
    parameter = contract.parameters[parameter_name]
    source = parameter.reference_source
    worksheet.cell(row, column_index_from_string(source.columns["Continent"]), "Test Continent")
    worksheet.cell(row, column_index_from_string(source.columns["Region"]), "Test Region")
    worksheet.cell(row, column_index_from_string(source.columns["Country"]), country)
    worksheet.cell(row, column_index_from_string(source.columns["Month"]), 1)
    first_year_column = column_index_from_string(source.columns["Month"]) + 1
    for offset, year in enumerate(contract.horizon.years):
        worksheet.cell(row, first_year_column + offset, values_by_year.get(year, float(year)))


@pytest.mark.parametrize("parameter_name", ["PMI", "Temperature"])
def test_year_column_reader_preserves_zero_and_blocks_invalid_exact_values(
    parameter_name: str,
) -> None:
    contract = load_workbook_contract()
    parameter = contract.parameters[parameter_name]
    source = parameter.reference_source
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = source.sheet
    first_year_column = column_index_from_string(source.columns["Month"]) + 1
    for offset, year in enumerate(contract.horizon.years):
        worksheet.cell(source.header_row, first_year_column + offset, year)

    _set_year_column_row(
        worksheet,
        parameter_name=parameter_name,
        row=source.data_start_row,
        country="Zero",
        values_by_year={2026: 0.0},
    )
    _set_year_column_row(
        worksheet,
        parameter_name=parameter_name,
        row=source.data_start_row + 1,
        country="RefError",
        values_by_year={2026: "#REF!"},
    )
    _set_year_column_row(
        worksheet,
        parameter_name=parameter_name,
        row=source.data_start_row + 2,
        country="Nonfinite",
        values_by_year={2026: "nan"},
    )
    _set_year_column_row(
        worksheet,
        parameter_name=parameter_name,
        row=source.data_start_row + 3,
        country="Duplicate",
        values_by_year={2026: 10.0},
    )
    _set_year_column_row(
        worksheet,
        parameter_name=parameter_name,
        row=source.data_start_row + 4,
        country="Duplicate",
        values_by_year={2026: 11.0},
    )

    records, warnings, blocked_keys = parse_year_column_records(
        contract,
        parameter_name,
        parameter,
        worksheet,
    )
    workbook.close()

    records_by_key = {record.canonical_key: record for record in records}
    assert records_by_key[("Zero", 2026, 1)].value == 0
    assert {
        ("RefError", 2026, 1),
        ("Nonfinite", 2026, 1),
        ("Duplicate", 2026, 1),
    } <= blocked_keys
    assert any("invalid cached value" in warning for warning in warnings)
    assert any("conflicting duplicate exact key" in warning for warning in warnings)


@pytest.mark.parametrize("parameter_name", ["PMI", "Temperature"])
def test_year_column_reader_rejects_missing_contract_horizon_header(
    parameter_name: str,
) -> None:
    contract = load_workbook_contract()
    parameter = contract.parameters[parameter_name]
    source = parameter.reference_source
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = source.sheet
    first_year_column = column_index_from_string(source.columns["Month"]) + 1
    for offset, year in enumerate(contract.horizon.years[:-1]):
        worksheet.cell(source.header_row, first_year_column + offset, year)

    with pytest.raises(MIBaseError, match="does not contain every contract horizon year"):
        parse_year_column_records(
            contract,
            parameter_name,
            parameter,
            worksheet,
        )
    workbook.close()


def _liq_slot() -> dict[str, Any]:
    return _slot(
        "liq",
        {
            "Country": "United States",
            "LNG Plant": "Alpha LNG",
            "LNG Plant Train": "Train 1",
            "Year": 2027,
            "Month": 5,
        },
    )


def _liq_provenance(*, scope: str) -> dict[str, Any]:
    return {
        "scenario_dimension_key": "facility_outage",
        "source_event_ids": [101],
        "lever_code": "liquefaction_utilization",
        "direction": "decrease",
        "scope": scope,
        "time_window": "2027 Q2",
    }


def test_liq_evidence_does_not_merge_plant_and_train_across_provenance() -> None:
    candidate = _candidate("LiqUtilAdjustment", "liq")
    candidate["lever_provenance"] = [
        _liq_provenance(scope="Alpha LNG"),
        _liq_provenance(scope="Train 1"),
    ]
    candidate["source_dimensions"] = [
        {
            "scenario_dimension_key": "facility_outage",
            "source_dimension_description": "generic facility availability",
        },
    ]
    context = {"events": [{"mi_event_id": 101, "event_title": "generic outage"}]}

    decision = evaluate_liq_util_evidence(candidate, _liq_slot(), context)

    assert decision.allowed is False
    assert "specific_facility_evidence" in decision.missing_components


def test_liq_entity_resolution_note_is_preserved_for_service_user() -> None:
    candidate = _candidate("LiqUtilAdjustment", "liq")
    axes = {
        "Country": "United States",
        "LNG Plant": "Corpus Christi LNG Stage 3",
        "LNG Plant Train": "Corpus Christi LNG Stage 3 T1",
        "Year": 2026,
        "Month": 10,
    }
    slot = _slot("liq", axes, slot_key="slot-1")
    slot["_user_notes"] = [
        "근거의 한국어 설비/호기 표기를 Basecase 영문 좌표와 동일 실체로 정규화해 연결했습니다.",
    ]
    adjustment = LLMValueAdjustment(
        candidate_key="liq",
        rationale_ko="가동률 차질을 반영했습니다.",
        slot_values=[
            LLMValueCell(
                slot_key="slot-1",
                proposed_value=0.8,
                rationale_ko="단기 차질 반영",
            ),
        ],
    )

    sanitized, warnings = nodes._sanitize_llm_adjustments(
        [adjustment],
        [candidate],
        [slot],
        [_reference("liq", "LiqUtilAdjustment", axes, 0.9, slot_key="slot-1")],
        scenario_context=V4_CONTEXT,
    )

    assert warnings == []
    assert "참고:" in sanitized[0]["parameter_selection_rationale_ko"]
    assert "동일 실체로 정규화" in sanitized[0]["parameter_selection_rationale_ko"]


@pytest.mark.parametrize(
    ("mutation", "missing_component"),
    [
        ({"lever_code": "gas_demand"}, "direct_operational_lever"),
        ({"scenario_dimension_key": ""}, "scenario_dimension_lineage"),
        ({"source_event_ids": [999]}, "source_event"),
    ],
)
def test_liq_evidence_rejects_wrong_lever_or_missing_lineage(
    mutation: dict[str, Any],
    missing_component: str,
) -> None:
    candidate = _candidate("LiqUtilAdjustment", "liq")
    provenance = _liq_provenance(scope="Alpha LNG / Train 1")
    provenance.update(mutation)
    candidate["lever_provenance"] = [provenance]
    candidate["source_dimensions"] = [
        {
            "scenario_dimension_key": "facility_outage",
            "source_dimension_description": "Alpha LNG Train 1 outage",
        },
    ]
    context = {"events": [{"mi_event_id": 101, "event_title": "Alpha LNG Train 1 outage"}]}

    decision = evaluate_liq_util_evidence(candidate, _liq_slot(), context)

    assert decision.allowed is False
    assert missing_component in decision.missing_components


@pytest.mark.parametrize("scenario_context", [V1_CONTEXT, V3_CONTEXT])
def test_valid_legacy_routes_bypass_new_atomic_value_and_evidence_policies(
    scenario_context: dict[str, Any],
) -> None:
    power_candidate, power_slots, power_references = _power_mix_step3_inputs()
    partial_adjustment = LLMValueAdjustment(
        candidate_key="power",
        rationale_ko="legacy partial vector",
        slot_values=[
            LLMValueCell(
                slot_key="slot-1",
                proposed_value=POWER_MIX_VALUES["Liquids"],
                rationale_ko="legacy member",
            ),
        ],
    )

    sanitized_power, power_warnings = nodes._sanitize_llm_adjustments(
        [partial_adjustment],
        [power_candidate],
        power_slots,
        power_references,
        scenario_context=scenario_context,
    )

    assert len(sanitized_power[0]["value_grid"]) == 1
    assert not any("PowerMix Step3" in warning for warning in power_warnings)

    liq_candidate = _candidate("LiqUtilAdjustment", "liq")
    liq_axes = {
        "Country": "United States",
        "LNG Plant": "Alpha LNG",
        "LNG Plant Train": "Train 1",
        "Year": 2027,
        "Month": 5,
    }
    liq_slot = _slot("liq", liq_axes, slot_key="slot-1")
    liq_reference = _reference(
        "liq",
        "LiqUtilAdjustment",
        liq_axes,
        0.9,
        slot_key="slot-1",
    )
    negative_adjustment = LLMValueAdjustment(
        candidate_key="liq",
        rationale_ko="legacy negative value",
        slot_values=[
            LLMValueCell(
                slot_key="slot-1",
                proposed_value=-0.1,
                rationale_ko="legacy semantics",
            ),
        ],
    )
    sanitized_liq, liq_warnings = nodes._sanitize_llm_adjustments(
        [negative_adjustment],
        [liq_candidate],
        [liq_slot],
        [liq_reference],
        scenario_context=scenario_context,
    )
    assert sanitized_liq[0]["value_grid"][0]["proposed_value"] == -0.1
    assert not any("음수" in warning for warning in liq_warnings)

    registry = get_model_parameter_resource_paths().lut_registry
    basecase_index = build_basecase_index(
        [
            {
                "candidate_key": "liq",
                "parameter_name": "LiqUtilAdjustment",
                "reference_id": "legacy:liq:1",
                "axes": {
                    **liq_axes,
                    "Period": 1,
                    "Life Cycle Category": "Operational",
                    "Nameplate Capacity (MTPA)": 5.0,
                },
                "value": 0.9,
            },
        ],
        [liq_candidate],
        registry=registry,
    )
    state = ModelParameterProposalState(
        scenario_id=1,
        scenario_context=scenario_context,
        candidate_mappings=[liq_candidate],
        parameter_slots=[_slot("liq", liq_axes)],
        basecase_index=basecase_index,
        resolved_config={"model_parameter_lut_enabled": False},
    )

    filtered = nodes.filter_basecase_records_by_slots(state)

    assert len(filtered["parameter_slots"]) == 1
    assert "policy_excluded_slot_count" not in filtered["slot_selection_diagnostics"]
    assert not any(item.get("reason_code") == "ABSTAINED_INSUFFICIENT_EVIDENCE" for item in filtered["non_input_items"])
