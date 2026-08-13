# ruff: noqa: S101

from __future__ import annotations

from argparse import Namespace
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.manual.model_parameter_agent import export_v3_scenario_model_inputs
from tests.manual.model_parameter_agent.export_v3_scenario_model_inputs import (
    _load_v3_scenarios,
    _parse_args,
    _patch_calc_chain,
)


def test_parse_args_defaults_to_all_v3_groups() -> None:
    args = _parse_args(["--experiment-id", "group-filter-test"])

    assert args.scenario_group_id is None


def test_parse_args_accepts_single_scenario_group_id() -> None:
    args = _parse_args(
        ["--experiment-id", "group-filter-test", "--scenario-group-id", "182"],
    )

    assert args.scenario_group_id == 182


def test_load_v3_scenarios_filters_select_and_fails_for_missing_group() -> None:
    session = MagicMock()
    session.execute.return_value.scalars.return_value.all.return_value = []

    with (
        patch.object(
            export_v3_scenario_model_inputs,
            "get_sync_session",
            return_value=session,
        ),
        pytest.raises(
            RuntimeError,
            match=r"api_version=v3 scenario group was found: scenario_group_id=182",
        ),
    ):
        _load_v3_scenarios(182)

    statement = session.execute.call_args.args[0]
    sql = str(statement.compile(compile_kwargs={"literal_binds": True}))
    where_clause = sql.partition("WHERE ")[2].partition(" ORDER BY")[0]
    assert "api_version = 'v3'" in where_clause
    assert "scenario_group_id = 182" in where_clause
    session.close.assert_called_once_with()


def test_load_v3_scenarios_without_filter_keeps_all_v3_group_select() -> None:
    session = MagicMock()
    session.execute.return_value.scalars.return_value.all.return_value = []

    with (
        patch.object(
            export_v3_scenario_model_inputs,
            "get_sync_session",
            return_value=session,
        ),
        pytest.raises(RuntimeError, match="No exact api_version=v3 scenario groups were found"),
    ):
        _load_v3_scenarios()

    statement = session.execute.call_args.args[0]
    sql = str(statement.compile(compile_kwargs={"literal_binds": True}))
    where_clause = sql.partition("WHERE ")[2].partition(" ORDER BY")[0]
    assert "api_version = 'v3'" in where_clause
    assert "scenario_group_id =" not in where_clause
    session.close.assert_called_once_with()


def test_main_forwards_scenario_group_id_to_run() -> None:
    output_root = Path("model-parameter-v3-export-test")
    args = Namespace(
        experiment_id="group-filter-test",
        output_root=output_root,
        scenario_group_id=182,
    )

    with (
        patch.object(export_v3_scenario_model_inputs, "_parse_args", return_value=args),
        patch.object(
            export_v3_scenario_model_inputs,
            "_run",
            new_callable=AsyncMock,
        ) as run,
    ):
        export_v3_scenario_model_inputs.main()

    run.assert_awaited_once_with("group-filter-test", output_root, 182)


def test_calc_chain_removes_inherited_sheet_reference() -> None:
    calc_chain = (
        b'<?xml version="1.0" encoding="UTF-8"?>'
        b'<calcChain xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        b'<c r="A1" i="42"/><c r="A2"/><c r="A3" i="63"/>'
        b"</calcChain>"
    )

    patched, removed = _patch_calc_chain(calc_chain, {("42", "A2")})

    assert removed == 1
    assert b'<c r="A1" i="42"/>' in patched
    assert b'<c r="A2"/>' not in patched
    assert b'<c r="A3" i="63"/>' in patched
