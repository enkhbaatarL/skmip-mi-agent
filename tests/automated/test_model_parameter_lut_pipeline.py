# ruff: noqa: S101, SLF001

from __future__ import annotations

from collections.abc import Iterator, Mapping
import os
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest


os.environ.setdefault("METADATA_DB_PORT", "3306")

from apps.agents.model_parameter_agent.flows.propose_parameters import nodes
from apps.agents.model_parameter_agent.flows.propose_parameters.flow import build_graph
from apps.agents.model_parameter_agent.flows.propose_parameters.state import (
    ModelParameterProposalState,
)
from apps.agents.model_parameter_agent.presentation import (
    _build_proposal_parameters,
    _callback_success_output,
    _to_response_data,
)
from apps.agents.model_parameter_agent.schemas.model_parameter_proposal import (
    LLMSlotAxis,
    LLMSlotProposal,
    LLMValueAdjustment,
    LLMValueCell,
)
from apps.agents.model_parameter_agent.utils.lut import (
    LutCatalog,
    LutLoadPolicy,
    ParameterSpecRegistry,
    build_basecase_index,
    build_slot_catalog,
    clear_lut_runtime_cache,
    get_lut_catalog,
    get_parameter_spec_registry,
    resolve_effective_reference,
)


def _candidate(parameter_name: str, candidate_key: str) -> dict[str, Any]:
    column_roles = {
        "GDP": "A:Country,B:Year,C:GDP",
        "PMI": "A:Country,B:Year,C:Month,D:PMI",
        "PowerMix": "A:Country,B:Year,C:Energy Source,D:PowerMix",
        "LiqUtilAdjustment": (
            "B:Country,C:LNG Plant,D:LNG Plant Train,"
            "E:Life Cycle Category,F:Nameplate Capacity (MTPA),G:LiqUtilAdjustment"
        ),
    }[parameter_name]
    return {
        "candidate_key": candidate_key,
        "canonical_parameter_name": parameter_name,
        "parameter_name": parameter_name,
        "model_file": "Supply" if parameter_name == "LiqUtilAdjustment" else "Demand",
        "model_sheet": f"{parameter_name}Adjustment",
        "model_table": "table1",
        "basecase_read_mode": "fixed_columns",
        "basecase_column_roles": column_roles,
    }


def _slot(candidate_key: str, axes: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "candidate_key": candidate_key,
        "selected": True,
        "slot_axes": [{"axis_name": axis_name, "axis_value": axis_value} for axis_name, axis_value in axes.items()],
    }


def _reference(
    candidate_key: str,
    parameter_name: str,
    axes: Mapping[str, Any],
    *,
    actual_basecase_value: float | None,
    lut_default_value: float | None,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    llm_reference_value = actual_basecase_value if actual_basecase_value is not None else lut_default_value
    assert llm_reference_value is not None
    return {
        "candidate_key": candidate_key,
        "parameter_name": parameter_name,
        "axes": dict(axes),
        "metadata": dict(metadata or {}),
        "actual_basecase_value": actual_basecase_value,
        "lut_default_value": lut_default_value,
        "llm_reference_value": llm_reference_value,
        "effective_source": ("basecase" if actual_basecase_value is not None else "lut"),
        "basecase_reference_id": (
            f"base:{candidate_key}:{len(str(axes))}" if actual_basecase_value is not None else None
        ),
        "lut_reference_id": (f"lut:{candidate_key}:{len(str(axes))}" if lut_default_value is not None else None),
        "lut_version": "test-lut-version" if lut_default_value is not None else None,
        "diagnostics": [],
    }


def _all_mapping_keys(value: object) -> set[str]:
    if isinstance(value, Mapping):
        keys = {str(key) for key in value}
        for nested in value.values():
            keys.update(_all_mapping_keys(nested))
        return keys
    if isinstance(value, list | tuple):
        keys: set[str] = set()
        for nested in value:
            keys.update(_all_mapping_keys(nested))
        return keys
    return set()


@pytest.fixture(scope="module")
def real_domain() -> tuple[ParameterSpecRegistry, LutCatalog]:
    clear_lut_runtime_cache()
    policy = LutLoadPolicy()
    registry = get_parameter_spec_registry()
    return registry, get_lut_catalog(policy, registry=registry)


@pytest.fixture(autouse=True)
def fixed_pipeline_settings() -> Iterator[SimpleNamespace]:
    settings = SimpleNamespace(
        model_parameter_max_parameter_slots=100,
        model_parameter_max_value_prompt_basecase_records=100,
        model_parameter_lut_enabled=True,
        model_parameter_lut_horizon_start_year=2026,
        model_parameter_lut_horizon_end_year=2030,
        model_parameter_llm_stream_enabled=False,
        model_parameter_llm_reasoning_effort="default",
    )
    with patch.object(nodes, "get_settings", return_value=settings):
        yield settings


def test_compact_slot_catalog_payload_and_parameter_caps_are_independent(
    real_domain: tuple[ParameterSpecRegistry, LutCatalog],
) -> None:
    registry, _ = real_domain
    candidates = [_candidate("GDP", "gdp"), _candidate("PMI", "pmi")]
    basecase_index = build_basecase_index(
        [
            {
                "candidate_key": "gdp",
                "reference_id": "gdp-jp-2026",
                "axes": {"Country": "Japan", "Year": 2026},
                "value": 0.02,
            },
            {
                "candidate_key": "gdp",
                "reference_id": "gdp-jp-2027",
                "axes": {"Country": "Japan", "Year": 2027},
                "value": 0.03,
            },
            {
                "candidate_key": "pmi",
                "reference_id": "pmi-us-2026-1",
                "axes": {"Country": "United States", "Year": 2026, "Month": 1},
                "value": 50.0,
            },
        ],
        candidates,
        registry=registry,
    )
    prompt_catalog = nodes._slot_catalog_for_prompt(
        build_slot_catalog(basecase_index),
    )
    packet = nodes._build_slot_proposal_prompt_packet(
        {"scenario": {"scenario_id": 1}},
        candidates,
        prompt_catalog,
        [],
    )

    assert len(packet["parameter_slot_tasks"]) == 2
    assert all(
        task["limits"]
        == {
            "maxParameterSlots": 100,
            "instruction": "관련된 slot만 선택하며 최대치를 채울 필요는 없음",
        }
        for task in packet["parameter_slot_tasks"]
    )
    compact_keys = _all_mapping_keys(prompt_catalog)
    assert {
        "actual_basecase_value",
        "lut_default_value",
        "llm_reference_value",
        "records",
        "value",
    }.isdisjoint(compact_keys)
    gdp_catalog = next(item for item in prompt_catalog if item["candidate_key"] == "gdp")
    assert gdp_catalog["leaves"] == [
        {
            "fixed_axes": {"Country": "Japan"},
            "available_periods": [{"Year": 2026}, {"Year": 2027}],
        },
    ]

    llm_slots = [
        LLMSlotProposal(
            candidate_key=candidate_key,
            selected=True,
            slot_axes=[
                LLMSlotAxis(axis_name="Country", axis_value=f"Country-{index}"),
                LLMSlotAxis(axis_name="Year", axis_value=2026),
            ],
        )
        for candidate_key in ("gdp", "pmi")
        for index in range(101)
    ]
    sanitized, warnings = nodes._sanitize_llm_slots(
        llm_slots,
        candidates,
        max_selected_slots=100,
    )
    selected_by_candidate = {
        candidate_key: sum(1 for slot in sanitized if slot["candidate_key"] == candidate_key and slot["selected"])
        for candidate_key in ("gdp", "pmi")
    }
    assert selected_by_candidate == {"gdp": 100, "pmi": 100}
    assert len([slot for slot in sanitized if not slot["selected"]]) == 2
    assert len(warnings) == 2


def test_exact_miss_is_rejected_without_nearest_and_all_reference_modes_resolve(
    real_domain: tuple[ParameterSpecRegistry, LutCatalog],
) -> None:
    registry, catalog = real_domain
    candidate = _candidate("GDP", "gdp")
    basecase_index = build_basecase_index(
        [
            {
                "candidate_key": "gdp",
                "reference_id": "base-china-2026",
                "axes": {"Country": "China", "Year": 2026},
                "value": 9.0,
            },
            {
                "candidate_key": "gdp",
                "reference_id": "base-only-2026",
                "axes": {"Country": "Basecase Only", "Year": 2026},
                "value": 1.5,
            },
        ],
        [candidate],
        registry=registry,
    )
    state = ModelParameterProposalState(
        scenario_id=1,
        candidate_mappings=[candidate],
        basecase_index=basecase_index,
        resolved_config={"model_parameter_lut_enabled": True},
        parameter_slots=[
            _slot("gdp", {"Country": "China", "Year": 2026}),
            _slot("gdp", {"Country": "China", "Year": 2026}),
            _slot("gdp", {"Country": "Basecase Only", "Year": 2026}),
            _slot("gdp", {"Country": "Japan", "Year": 2026}),
            _slot("gdp", {"Country": "Exact Miss", "Year": 2026}),
        ],
    )

    with (
        patch.object(nodes, "get_parameter_spec_registry", return_value=registry),
        patch.object(nodes, "get_lut_catalog", return_value=catalog),
    ):
        result = nodes.filter_basecase_records_by_slots(state)

    assert [slot["selected"] for slot in result["parameter_slots"]] == [
        True,
        False,
        True,
        True,
        False,
    ]
    assert result["parameter_slots"][-1]["slot_axes"] == []
    references = {reference["axes"]["Country"]: reference for reference in result["effective_references"]}
    assert set(references) == {"China", "Basecase Only", "Japan"}
    assert references["China"]["actual_basecase_value"] == 9.0
    assert references["China"]["lut_default_value"] is not None
    assert references["China"]["llm_reference_value"] == 9.0
    assert references["Basecase Only"]["lut_default_value"] is None
    assert references["Basecase Only"]["effective_source"] == "basecase"
    assert references["Japan"]["actual_basecase_value"] is None
    assert references["Japan"]["effective_source"] == "lut"
    assert references["Japan"]["llm_reference_value"] == references["Japan"]["lut_default_value"]
    assert result["reference_diagnostics"]["selected_references"]["rejected_exact_slot_count"] == 2
    assert any("중복 반환" in warning for warning in result["validation_warnings"])
    assert any("Exact Miss" in warning for warning in result["validation_warnings"])


def test_step3_prompt_exposes_only_one_llm_reference_value() -> None:
    candidate = _candidate("GDP", "gdp")
    slots = [
        _slot("gdp", {"Country": "China", "Year": 2026}),
        _slot("gdp", {"Country": "Japan", "Year": 2026}),
    ]
    references = [
        _reference(
            "gdp",
            "GDP",
            {"Country": "China", "Year": 2026},
            actual_basecase_value=0.09,
            lut_default_value=0.04,
        ),
        _reference(
            "gdp",
            "GDP",
            {"Country": "Japan", "Year": 2026},
            actual_basecase_value=None,
            lut_default_value=0.02,
        ),
    ]

    packet = nodes._build_value_proposal_prompt_packet(
        {"scenario": {"scenario_id": 1}},
        [candidate],
        slots,
        references,
        [],
    )
    groups = packet["parameter_value_tasks"][0]["basecase_value_groups"]
    cells = [cell for group in groups for cell in group["cells"]]

    assert {cell["llm_reference_value"] for cell in cells} == {0.09, 0.02}
    prompt_keys = _all_mapping_keys(packet)
    assert {
        "actual_basecase_value",
        "lut_default_value",
        "effective_source",
        "basecase_reference_id",
        "lut_reference_id",
    }.isdisjoint(prompt_keys)


def test_partial_valid_cell_and_explicit_no_change_survive_with_diagnostics() -> None:
    candidate = _candidate("PMI", "pmi")
    slots = [_slot("pmi", {"Country": "Japan", "Year": 2026, "Month": month}) for month in (1, 2, 3)]
    references = [
        _reference(
            "pmi",
            "PMI",
            {"Country": "Japan", "Year": 2026, "Month": month},
            actual_basecase_value=None,
            lut_default_value=value,
        )
        for month, value in ((1, 50.0), (2, 51.0), (3, 52.0))
    ]
    adjustment = LLMValueAdjustment(
        candidate_key="pmi",
        rationale_ko="PMI 제안",
        value_grid=[
            LLMValueCell(
                coordinates={"Country": "Japan", "Year": 2026, "Month": 1},
                proposed_value=50.0,
                rationale_ko="명시적인 no-change",
            ),
            LLMValueCell(
                coordinates={"Country": "Japan", "Year": 2026, "Month": 4},
                proposed_value=47.0,
                rationale_ko="요청되지 않은 좌표",
            ),
        ],
    )

    sanitized, warnings, diagnostics = nodes._sanitize_llm_adjustments(
        [adjustment],
        [candidate],
        slots,
        references,
    )

    assert sanitized[0]["selected"] is True
    assert len(sanitized[0]["value_grid"]) == 1
    cell = sanitized[0]["value_grid"][0]
    assert cell["coordinates"] == {"Country": "Japan", "Year": 2026, "Month": 1}
    assert cell["proposed_value"] == 50.0
    assert cell["basecase_value"] is None
    assert cell["basecase_reference_ids"] == []
    assert diagnostics == {
        "selected_cell_count": 3,
        "returned_cell_count": 2,
        "valid_cell_count": 1,
        "missing_cell_count": 2,
        "invalid_cell_count": 1,
        "by_candidate": {
            "pmi": {
                "selected_cell_count": 3,
                "returned_cell_count": 2,
                "valid_cell_count": 1,
                "missing_cell_count": 2,
                "invalid_cell_count": 1,
            },
        },
    }
    assert any("누락" in warning for warning in warnings)

    operational = _build_proposal_parameters(sanitized, [candidate])[0].model_dump(
        by_alias=True,
    )
    assert operational["values"][0]["basecaseValue"] is None
    assert operational["values"][0]["proposedValue"] == 50.0


def test_step3_projects_canonical_effective_reference_axes_to_operational_cell() -> None:
    candidate = _candidate("GDP", "gdp")
    authoritative_axes = {"Country": "United States", "Year": 2026}
    slots = [_slot("gdp", authoritative_axes)]
    references = [
        _reference(
            "gdp",
            "GDP",
            authoritative_axes,
            actual_basecase_value=0.03,
            lut_default_value=0.02,
        ),
    ]
    adjustment = LLMValueAdjustment(
        candidate_key="gdp",
        rationale_ko="canonical representation test",
        value_grid=[
            LLMValueCell(
                coordinates={"Country": "united states ", "Year": "2026"},
                proposed_value=0.01,
                rationale_ko="LLM representation differs",
            ),
        ],
    )

    sanitized, warnings, diagnostics = nodes._sanitize_llm_adjustments(
        [adjustment],
        [candidate],
        slots,
        references,
    )

    assert warnings == []
    assert diagnostics["valid_cell_count"] == 1
    assert sanitized[0]["value_grid"][0]["coordinates"] == authoritative_axes
    operational = _build_proposal_parameters(sanitized, [candidate])[0].model_dump(
        by_alias=True,
    )
    assert operational["values"][0]["Country"] == "United States"
    assert operational["values"][0]["Year"] == 2026


@pytest.mark.parametrize("proposed_values", [(1.1, 1.1), (1.1, 9.9)])
def test_step3_rejects_all_duplicate_candidate_adjustments_deterministically(
    proposed_values: tuple[float, float],
) -> None:
    candidate = _candidate("GDP", "gdp")
    axes = {"Country": "Japan", "Year": 2026}
    slots = [_slot("gdp", axes)]
    references = [
        _reference(
            "gdp",
            "GDP",
            axes,
            actual_basecase_value=0.02,
            lut_default_value=0.03,
        ),
    ]

    def adjustment(value: float) -> LLMValueAdjustment:
        return LLMValueAdjustment(
            candidate_key="gdp",
            rationale_ko=f"duplicate {value}",
            value_grid=[
                LLMValueCell(
                    coordinates=axes,
                    proposed_value=value,
                    rationale_ko="duplicate cell",
                ),
            ],
        )

    first = [adjustment(value) for value in proposed_values]
    second = list(reversed(first))
    first_result = nodes._sanitize_llm_adjustments(
        first,
        [candidate],
        slots,
        references,
    )
    second_result = nodes._sanitize_llm_adjustments(
        second,
        [candidate],
        slots,
        references,
    )

    for sanitized, warnings, diagnostics in (first_result, second_result):
        assert len(sanitized) == 1
        assert sanitized[0]["selected"] is False
        assert sanitized[0]["value_grid"] == []
        assert diagnostics == {
            "selected_cell_count": 1,
            "returned_cell_count": 2,
            "valid_cell_count": 0,
            "missing_cell_count": 1,
            "invalid_cell_count": 2,
            "by_candidate": {
                "gdp": {
                    "selected_cell_count": 1,
                    "returned_cell_count": 2,
                    "valid_cell_count": 0,
                    "missing_cell_count": 1,
                    "invalid_cell_count": 2,
                },
            },
        }
        assert any("동일 candidate_key" in warning for warning in warnings)
    assert first_result[0] == second_result[0]
    assert first_result[2] == second_result[2]


def test_liq_metadata_is_restored_from_exact_effective_reference(
    real_domain: tuple[ParameterSpecRegistry, LutCatalog],
) -> None:
    registry, catalog = real_domain
    candidate = _candidate("LiqUtilAdjustment", "liq")
    lut_record = catalog.records_for_parameter("LiqUtilAdjustment")[0]
    basecase_index = build_basecase_index(
        [
            {
                "candidate_key": "liq",
                "reference_id": "base-liq-exact",
                "axes": {
                    **dict(lut_record.axes),
                    "Period": 999,
                    "Life Cycle Category": "Basecase Lifecycle",
                    "Nameplate Capacity (MTPA)": 77.7,
                },
                "value": 0.42,
            },
        ],
        [candidate],
        registry=registry,
    )
    effective = resolve_effective_reference(
        "liq",
        lut_record.axes,
        basecase_index,
        catalog,
    )
    assert effective is not None
    reference = nodes._effective_reference_to_state(effective)
    slot = _slot("liq", effective.axes)
    adjustment = LLMValueAdjustment(
        candidate_key="liq",
        rationale_ko="가동률 조정",
        value_grid=[
            LLMValueCell(
                coordinates=dict(effective.axes),
                proposed_value=0.4,
                rationale_ko="exact cell",
            ),
        ],
    )

    sanitized, _, diagnostics = nodes._sanitize_llm_adjustments(
        [adjustment],
        [candidate],
        [slot],
        [reference],
    )

    cell = sanitized[0]["value_grid"][0]
    assert cell["basecase_value"] == 0.42
    assert cell["basecase_reference_ids"] == ["base-liq-exact"]
    assert {
        key: cell["coordinates"][key] for key in ("Period", "Life Cycle Category", "Nameplate Capacity (MTPA)")
    } == {
        "Period": 999,
        "Life Cycle Category": "Basecase Lifecycle",
        "Nameplate Capacity (MTPA)": 77.7,
    }
    assert diagnostics["valid_cell_count"] == 1
    assert diagnostics["missing_cell_count"] == 0


def test_powermix_keeps_only_explicit_source_cell_without_normalization() -> None:
    candidate = _candidate("PowerMix", "power")
    gas_axes = {"Country": "Japan", "Year": 2026, "Energy Source": "Gas"}
    coal_axes = {"Country": "Japan", "Year": 2026, "Energy Source": "Coal"}
    slots = [_slot("power", gas_axes), _slot("power", coal_axes)]
    references = [
        _reference(
            "power",
            "PowerMix",
            gas_axes,
            actual_basecase_value=None,
            lut_default_value=0.6,
        ),
        _reference(
            "power",
            "PowerMix",
            coal_axes,
            actual_basecase_value=None,
            lut_default_value=0.4,
        ),
    ]
    adjustment = LLMValueAdjustment(
        candidate_key="power",
        rationale_ko="Gas만 독립 override",
        value_grid=[
            LLMValueCell(
                coordinates=gas_axes,
                proposed_value=0.8,
                rationale_ko="Gas cell만 명시",
            ),
        ],
    )

    sanitized, _, diagnostics = nodes._sanitize_llm_adjustments(
        [adjustment],
        [candidate],
        slots,
        references,
    )

    assert sanitized[0]["selected"] is True
    assert sanitized[0]["value_grid"] == [
        {
            "coordinates": gas_axes,
            "basecase_value": None,
            "proposed_value": 0.8,
            "rationale_ko": "Gas cell만 명시",
            "basecase_reference_ids": [],
        },
    ]
    assert diagnostics["valid_cell_count"] == 1
    assert diagnostics["missing_cell_count"] == 1
    operational = _build_proposal_parameters(sanitized, [candidate])[0].model_dump(
        by_alias=True,
    )
    assert len(operational["values"]) == 1
    assert operational["values"][0]["Energy Source"] == "Gas"
    assert operational["values"][0]["proposedValue"] == 0.8


def test_state_dump_excludes_basecase_index_and_contains_no_full_rows(
    real_domain: tuple[ParameterSpecRegistry, LutCatalog],
) -> None:
    registry, _ = real_domain
    candidate = _candidate("GDP", "gdp")
    basecase_index = build_basecase_index(
        [
            {
                "candidate_key": "gdp",
                "reference_id": "base-japan",
                "axes": {"Country": "Japan", "Year": 2026},
                "value": 0.02,
            },
        ],
        [candidate],
        registry=registry,
    )
    compact_catalog = nodes._slot_catalog_for_prompt(
        build_slot_catalog(basecase_index),
    )
    state = ModelParameterProposalState(
        scenario_id=1,
        candidate_mappings=[candidate],
        basecase_index=basecase_index,
        basecase_records=[],
        slot_catalog=compact_catalog,
        effective_references=[
            _reference(
                "gdp",
                "GDP",
                {"Country": "Japan", "Year": 2026},
                actual_basecase_value=0.02,
                lut_default_value=None,
            ),
        ],
    )

    dumped = state.model_dump()

    assert "basecase_index" not in dumped
    assert dumped["basecase_records"] == []
    assert dumped["slot_catalog"] == compact_catalog
    assert "records" not in _all_mapping_keys(dumped["slot_catalog"])


def test_graph_output_excludes_request_local_runtime_indexes() -> None:
    graph = build_graph()

    assert "basecase_index" not in graph.output_channels
    assert "parameter_knowledge_base" not in graph.output_channels


def test_sync_diagnostics_are_projected_but_operational_callback_stays_signal_only() -> None:
    candidate = _candidate("PMI", "pmi")
    adjustments = [
        {
            "candidate_key": "pmi",
            "model_file": "Demand",
            "model_sheet": "PMIAdjustment",
            "parameter_name": "PMI",
            "selected": True,
            "slot_axes": [],
            "value_grid": [
                {
                    "coordinates": {"Country": "Japan", "Year": 2026, "Month": 1},
                    "basecase_value": None,
                    "proposed_value": 49.0,
                    "rationale_ko": "LUT-only 진단",
                    "basecase_reference_ids": [],
                },
            ],
            "parameter_selection_rationale_ko": "PMI 조정",
        },
    ]
    proposal_parameters = _build_proposal_parameters(adjustments, [candidate])
    diagnostics = {
        "selected_references": {
            "effective_source_counts": {"basecase": 0, "lut": 1},
            "references": [
                _reference(
                    "pmi",
                    "PMI",
                    {"Country": "Japan", "Year": 2026, "Month": 1},
                    actual_basecase_value=None,
                    lut_default_value=50.0,
                ),
            ],
        },
        "cell_validation": {
            "selected_cell_count": 1,
            "valid_cell_count": 1,
            "missing_cell_count": 0,
            "invalid_cell_count": 0,
        },
    }

    response_data = _to_response_data(
        {
            "scenario_id": 1,
            "scenario_context": {
                "scenario": {"scenario_id": 1, "scenario_group_id": 2},
                "scenario_group": {"scenario_group_id": 2, "mi_event_id": 3},
                "event": {"mi_event_id": 3},
            },
            "reference_diagnostics": diagnostics,
        },
        model_param_proposal_id=10,
        proposal_parameters=proposal_parameters,
    )
    sync_payload = response_data.model_dump(by_alias=True)

    assert sync_payload["diagnostics"] == diagnostics
    assert sync_payload["proposalParameters"][0]["values"][0]["basecaseValue"] is None
    callback_payload = _callback_success_output(response_data).model_dump(by_alias=True)
    assert "diagnostics" not in callback_payload
    assert callback_payload["data"] == {
        "modelParamProposalId": 10,
        "scenarioId": 1,
        "scenarioGroupId": 2,
        "eventId": 3,
        "status": "PROPOSED",
    }
