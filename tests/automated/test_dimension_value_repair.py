from __future__ import annotations

# ruff: noqa: CPY001, S101
import importlib
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from typing import Any
from unittest.mock import Mock, patch


repair = importlib.import_module(
    "scripts.migrations.20260819_canonicalize_scenario_dimension_value_ids",
)


DEFINITIONS = [
    {
        "dimension_id": "d1",
        "values": [
            {"value_id": "d1_v1", "label": "낮음"},
            {"value_id": "d1_v2", "label": "높음"},
        ],
    },
]


def _result(items: list[Any]) -> SimpleNamespace:
    return SimpleNamespace(
        scalars=lambda: SimpleNamespace(all=lambda: items),
    )


def _session(
    scenario: SimpleNamespace,
    snapshot: SimpleNamespace,
) -> Mock:
    session = Mock()
    group_194 = SimpleNamespace(
        scenario_group_id=194,
        dimension_definitions=DEFINITIONS,
    )
    group_without_definitions = SimpleNamespace(
        scenario_group_id=200,
        dimension_definitions=[],
    )
    session.execute.side_effect = [
        _result([group_194, group_without_definitions]),
        _result([scenario]),
        _result([snapshot]),
    ]
    return session


def _connection_module(session: Mock) -> ModuleType:
    module = ModuleType("apps.common.configs.database.sync_database.connection")
    module.get_sync_session = Mock(return_value=session)  # type: ignore[attr-defined]
    return module


def _records() -> tuple[SimpleNamespace, SimpleNamespace]:
    return (
        SimpleNamespace(
            scenario_id=10,
            dimension_values={"d1": "높음"},
            mod_usr_logn_id="7",
        ),
        SimpleNamespace(
            snapshot_id=20,
            scenario_snap_id=21,
            dimension_values=[
                {"dim_key": "d1", "value": "낮음", "display_order": 1},
            ],
            mod_usr_logn_id="7",
        ),
    )


def test_repair_dry_run_prioritizes_group_194_and_writes_before_after_audit(
    tmp_path: Path,
) -> None:
    scenario, snapshot = _records()
    session = _session(scenario, snapshot)
    report_path = tmp_path / "dry-run.json"
    with patch.dict(
        sys.modules,
        {
            "apps.common.configs.database.sync_database.connection": _connection_module(
                session,
            ),
        },
    ):
        report = repair.run_repair(
            apply_changes=False,
            report_path=report_path,
        )

    first_statement = session.execute.call_args_list[0].args[0]
    assert 194 in first_statement.compile().params.values()
    assert report["mode"] == "dry-run"
    assert report["changedRecordCount"] == 2
    assert [item["recordType"] for item in report["records"]] == [
        "scenario",
        "scenarioSnapshot",
    ]
    assert report["records"][0]["before"] == {"d1": "높음"}
    assert report["records"][0]["after"] == {"d1": "d1_v2"}
    assert report["records"][1]["before"][0]["value"] == "낮음"
    assert report["records"][1]["after"][0]["value"] == "d1_v1"
    assert scenario.dimension_values == {"d1": "높음"}
    assert snapshot.dimension_values[0]["value"] == "낮음"
    session.rollback.assert_called_once_with()
    session.commit.assert_not_called()
    assert json.loads(report_path.read_text(encoding="utf-8"))["changedRecordCount"] == 2


def test_repair_apply_is_idempotent_for_scenario_and_snapshot(tmp_path: Path) -> None:
    scenario, snapshot = _records()
    first_session = _session(scenario, snapshot)
    with patch.dict(
        sys.modules,
        {
            "apps.common.configs.database.sync_database.connection": _connection_module(
                first_session,
            ),
        },
    ):
        first = repair.run_repair(
            apply_changes=True,
            report_path=tmp_path / "apply.json",
        )

    assert first["changedRecordCount"] == 2
    assert scenario.dimension_values == {"d1": "d1_v2"}
    assert snapshot.dimension_values[0]["value"] == "d1_v1"
    first_session.commit.assert_called_once_with()
    first_session.rollback.assert_not_called()

    second_session = _session(scenario, snapshot)
    with patch.dict(
        sys.modules,
        {
            "apps.common.configs.database.sync_database.connection": _connection_module(
                second_session,
            ),
        },
    ):
        second = repair.run_repair(
            apply_changes=True,
            report_path=tmp_path / "apply-again.json",
        )

    assert second["changedRecordCount"] == 0
    assert second["records"] == []
    second_session.commit.assert_called_once_with()


def test_repair_leaves_ambiguous_and_unknown_labels_unresolved() -> None:
    definitions = [
        {
            "dimension_id": "d1",
            "values": [
                {"value_id": "d1_v1", "label": "동일"},
                {"value_id": "d1_v2", "label": "동일"},
            ],
        },
    ]

    repaired, unresolved = repair.canonicalize_values_for_repair(
        definitions,
        {"d1": "동일", "missing": "알 수 없음"},
    )

    assert repaired == {"d1": "동일", "missing": "알 수 없음"}
    assert unresolved == [
        {"dimensionId": "d1", "value": "동일", "reason": "ambiguous_label"},
        {
            "dimensionId": "missing",
            "value": "알 수 없음",
            "reason": "definition_missing",
        },
    ]
