# Copyright (c) 2026 SK Innovation E&S.
# ruff: noqa: S101

from __future__ import annotations

from types import MappingProxyType, SimpleNamespace

import pytest

from apps.agents.model_parameter_agent.utils.lut.models import (
    BasecaseReference,
    EffectiveReference,
)
from tests.manual.model_parameter_agent.export_confirmed_scenario_model_inputs import (
    _confirmed_proposals_statement,
    _latest_confirmed_by_scenario,
    _match_basecase_reference,
    _match_lut_backed_matrix_reference,
    _matrix_time_column_index,
    _parse_args,
    _validated_confirmation_parameters,
)


def _reference(
    reference_id: str = "Supply:LiqUtilAdjustment:R17C9",
    *,
    basecase_value: float = 0.90738,
) -> BasecaseReference:
    axes = {
        "Country": "Angola",
        "LNG Plant": "Angola LNG",
        "LNG Plant Train": "Angola LNG T1",
        "Year": 2026,
        "Month": 8,
        "Period": 104,
    }
    metadata = {
        "Life Cycle Category": "Operational",
        "Nameplate Capacity (MTPA)": 5.2,
    }
    return BasecaseReference(
        candidate_key="confirmed-liq-util",
        parameter_name="LiqUtilAdjustment",
        canonical_key=tuple(axes.values()),
        axes=MappingProxyType(axes),
        value=basecase_value,
        metadata=MappingProxyType(metadata),
        reference_id=reference_id,
    )


def _value() -> dict[str, object]:
    return {
        "Country": "Angola",
        "LNG Plant": "Angola LNG",
        "LNG Plant Train": "Angola LNG T1",
        "Year": 2026,
        "Month": 8,
        "Period": 104,
        "Life Cycle Category": "Operational",
        "Nameplate Capacity (MTPA)": 5.2,
        "basecaseValue": 0.90738,
        "proposedValue": 0.84,
        "rationale": "confirmed",
    }


SLOT_AXES = (
    "Country",
    "LNG Plant",
    "LNG Plant Train",
    "Year",
    "Month",
    "Period",
    "Life Cycle Category",
    "Nameplate Capacity (MTPA)",
)


def _liq_prod_candidate() -> dict[str, object]:
    return {
        "candidate_key": "confirmed-liq-prod",
        "model_file": "Supply",
        "model_sheet": "LiqProdAdjustment",
        "canonical_parameter_name": "LiqProdAdjustment",
        "parameter_name": "LiqProdAdjustment",
        "basecase_read_mode": "matrix_time_columns",
        "basecase_header_row": 10,
        "basecase_data_start_row": 11,
        "basecase_column_roles": (
            "B:Country,C:LNG Plant,D:LNG Plant Train,E:Life Cycle Category,F:Nameplate Capacity (MTPA)"
        ),
        "basecase_year_row": 7,
        "basecase_month_row": 8,
        "basecase_period_row": 9,
        "basecase_value_start_col": "G",
        "basecase_value_end_col": "DA",
        "basecase_stop_rule": "stop_when_all_key_columns_empty",
    }


def _liq_prod_value() -> dict[str, object]:
    return {
        **_value(),
        "basecaseValue": None,
        "lutValue": 0.35698,
        "proposedValue": 0.34546,
    }


def _liq_prod_metadata_reference() -> BasecaseReference:
    return BasecaseReference(
        candidate_key="confirmed-liq-prod",
        parameter_name="LiqProdAdjustment",
        canonical_key=("Angola", "Angola LNG", "Angola LNG T1", 2026, 1),
        axes=MappingProxyType(
            {
                "Country": "Angola",
                "LNG Plant": "Angola LNG",
                "LNG Plant Train": "Angola LNG T1",
                "Year": 2026,
                "Month": 1,
            },
        ),
        value=None,
        metadata=MappingProxyType(
            {
                "Period": 97,
                "Life Cycle Category": "Operational",
                "Nameplate Capacity (MTPA)": 5.2,
            },
        ),
        reference_id="Supply:LiqProdAdjustment:R15C34",
    )


def _liq_prod_effective_reference() -> EffectiveReference:
    return EffectiveReference(
        candidate_key="confirmed-liq-prod",
        parameter_name="LiqProdAdjustment",
        canonical_slot_key=("Angola", "Angola LNG", "Angola LNG T1", 2026, 8),
        axes=MappingProxyType(
            {
                "Country": "Angola",
                "LNG Plant": "Angola LNG",
                "LNG Plant Train": "Angola LNG T1",
                "Year": 2026,
                "Month": 8,
            },
        ),
        metadata=MappingProxyType(
            {
                "Period": 104,
                "Life Cycle Category": "Operational",
                "Nameplate Capacity (MTPA)": 5.2,
            },
        ),
        actual_basecase_value=None,
        lut_default_value=0.35698,
        llm_reference_value=0.35698,
        effective_source="lut",
        basecase_reference_id="Supply:LiqProdAdjustment:R15C34",
        lut_reference_id="lut:LiqProdAdjustment:Angola:2026:8",
        lut_version="test",
        diagnostics=("basecase_non_time_axes_with_lut_value",),
    )


def _proposal(
    proposal_id: int,
    confirmation_parameters: list[object] | dict[str, str] | None,
    *,
    scenario_id: int = 1075,
) -> SimpleNamespace:
    return SimpleNamespace(
        model_param_proposal_id=proposal_id,
        scenario_id=scenario_id,
        confirmation_parameters=confirmation_parameters,
    )


def test_parse_args_requires_one_group_and_output_directory() -> None:
    args = _parse_args(
        [
            "--scenario-group-id",
            "183",
            "--output-dir",
            "evidence/group_183",
        ],
    )

    assert args.scenario_group_id == 183
    assert args.output_dir.as_posix() == "evidence/group_183"


def test_confirmed_query_does_not_filter_invalid_latest_payload_before_selection() -> None:
    statement = str(_confirmed_proposals_statement(183))

    assert "confirmation_parameters IS NOT NULL" not in statement
    assert "status" in statement
    assert "del_yn" in statement


@pytest.mark.parametrize(
    ("invalid_payload", "message"),
    [
        (None, "non-empty confirmation_parameters"),
        ([], "non-empty confirmation_parameters"),
        ({"parameterName": "LiqUtilAdjustment"}, "non-empty confirmation_parameters"),
        (["malformed"], "JSON objects only"),
    ],
)
def test_latest_confirmed_row_is_validated_without_falling_back(
    invalid_payload: list[object] | dict[str, str] | None,
    message: str,
) -> None:
    older_valid = _proposal(256, [{"parameterName": "LiqUtilAdjustment"}])
    latest_invalid = _proposal(261, invalid_payload)

    latest = _latest_confirmed_by_scenario([latest_invalid, older_valid])

    assert latest[1075].model_param_proposal_id == 261
    with pytest.raises(RuntimeError, match=message):
        _validated_confirmation_parameters(latest[1075])


def test_latest_confirmed_selection_is_independent_of_query_order() -> None:
    rows = [
        _proposal(260, [{"parameterName": "PMI"}], scenario_id=1076),
        _proposal(258, [{"parameterName": "GDP"}], scenario_id=1075),
        _proposal(257, [{"parameterName": "PMI"}], scenario_id=1076),
        _proposal(261, [{"parameterName": "GDP"}], scenario_id=1075),
    ]

    latest = _latest_confirmed_by_scenario(rows)

    assert {scenario_id: row.model_param_proposal_id for scenario_id, row in latest.items()} == {
        1075: 261,
        1076: 260,
    }


def test_confirmed_value_matches_one_exact_basecase_reference() -> None:
    reference, coordinates = _match_basecase_reference(
        parameter_name="LiqUtilAdjustment",
        slot_axes=SLOT_AXES,
        value=_value(),
        records=[_reference()],
    )

    assert reference.reference_id == "Supply:LiqUtilAdjustment:R17C9"
    assert coordinates["Year"] == 2026
    assert coordinates["Nameplate Capacity (MTPA)"] == 5.2


def test_confirmed_value_rejects_ambiguous_basecase_reference() -> None:
    with pytest.raises(RuntimeError, match="one exact canonical Basecase reference"):
        _match_basecase_reference(
            parameter_name="LiqUtilAdjustment",
            slot_axes=SLOT_AXES,
            value=_value(),
            records=[
                _reference(),
                _reference("Supply:LiqUtilAdjustment:R18C9"),
            ],
        )


def test_confirmed_value_rejects_basecase_value_drift() -> None:
    value = _value()
    value["basecaseValue"] = 0.8

    with pytest.raises(RuntimeError, match="basecaseValue disagrees"):
        _match_basecase_reference(
            parameter_name="LiqUtilAdjustment",
            slot_axes=SLOT_AXES,
            value=value,
            records=[_reference()],
        )


def test_confirmed_value_rejects_undeclared_coordinate() -> None:
    value = _value()
    value["Route"] = "unexpected"

    with pytest.raises(RuntimeError, match="not declared"):
        _match_basecase_reference(
            parameter_name="LiqUtilAdjustment",
            slot_axes=SLOT_AXES,
            value=value,
            records=[_reference()],
        )


def test_liq_prod_null_basecase_resolves_exact_existing_matrix_cell() -> None:
    reference, coordinates = _match_lut_backed_matrix_reference(
        parameter_name="LiqProdAdjustment",
        candidate=_liq_prod_candidate(),
        slot_axes=SLOT_AXES,
        value=_liq_prod_value(),
        records=[_liq_prod_metadata_reference()],
        effective_reference=_liq_prod_effective_reference(),
        time_columns={(2026, 8, 104): 41},
    )

    assert reference.reference_id == "Supply:LiqProdAdjustment:R15C41"
    assert reference.value is None
    assert coordinates["Period"] == 104


def test_liq_prod_matrix_headers_resolve_packaged_2026_august_slot() -> None:
    time_columns = _matrix_time_column_index(candidate=_liq_prod_candidate())

    assert time_columns[(2026, 8, 104)] == 41


def test_liq_prod_null_basecase_rejects_lut_value_drift() -> None:
    value = _liq_prod_value()
    value["lutValue"] = 0.4

    with pytest.raises(RuntimeError, match="lutValue disagrees"):
        _match_lut_backed_matrix_reference(
            parameter_name="LiqProdAdjustment",
            candidate=_liq_prod_candidate(),
            slot_axes=SLOT_AXES,
            value=value,
            records=[_liq_prod_metadata_reference()],
            effective_reference=_liq_prod_effective_reference(),
            time_columns={(2026, 8, 104): 41},
        )


def test_liq_prod_null_basecase_requires_same_row_metadata_anchor() -> None:
    with pytest.raises(RuntimeError, match="same-row Basecase metadata reference"):
        _match_lut_backed_matrix_reference(
            parameter_name="LiqProdAdjustment",
            candidate=_liq_prod_candidate(),
            slot_axes=SLOT_AXES,
            value=_liq_prod_value(),
            records=[],
            effective_reference=_liq_prod_effective_reference(),
            time_columns={(2026, 8, 104): 41},
        )


def test_liq_prod_null_basecase_requires_exact_matrix_time_column() -> None:
    with pytest.raises(RuntimeError, match="no exact Year/Month/Period column"):
        _match_lut_backed_matrix_reference(
            parameter_name="LiqProdAdjustment",
            candidate=_liq_prod_candidate(),
            slot_axes=SLOT_AXES,
            value=_liq_prod_value(),
            records=[_liq_prod_metadata_reference()],
            effective_reference=_liq_prod_effective_reference(),
            time_columns={},
        )
