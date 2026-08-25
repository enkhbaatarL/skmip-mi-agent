from __future__ import annotations

# ruff: noqa: CPY001, S101
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from apps.agents.scenario_group_agent.persistence.scenario_group_service import (
    ScenarioGroupService,
)
from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode
from apps.persistence.scenario_group.repository import ScenarioGroupRepository


def _connection_module(session: Mock) -> ModuleType:
    module = ModuleType("apps.common.configs.database.sync_database.connection")
    module.get_sync_session = Mock(return_value=session)  # type: ignore[attr-defined]
    return module


def _repositories(*, owner: int = 7) -> tuple[Mock, Mock, Mock, Mock, Mock]:
    session = Mock()
    group_repository = Mock(spec=ScenarioGroupRepository)
    group_repository.fetch_by_id.return_value = SimpleNamespace(
        scenario_group_id=10,
        request_usr_id=owner,
        generation_strategy="multi_event_model_lever_dimensions",
        parameter_mapping_ready=True,
        dimension_selected=["d1"],
        dimension_definitions=[
            {
                "dimension_id": "d1",
                "values": [
                    {"value_id": "d1_v1", "label": "낮음"},
                    {"value_id": "d1_v2", "label": "높음"},
                ],
            },
        ],
    )
    scenario_repository = Mock()
    scenario_repository.fetch_models_by_group_id.return_value = [
        SimpleNamespace(
            scenario_id=100,
            dimension_values={"d1": "d1_v1"},
        ),
    ]
    signpost_repository = Mock()
    signpost_repository.fetch_models_by_scenario_ids.return_value = [
        SimpleNamespace(signpost_id=1000, scenario_id=100),
    ]
    return session, group_repository, scenario_repository, signpost_repository, Mock()


def test_confirmation_rejects_changed_dimension_values_without_any_write() -> None:
    session, groups, scenarios, signposts, _unused = _repositories()
    with (
        patch.dict(
            sys.modules,
            {
                "apps.common.configs.database.sync_database.connection": _connection_module(
                    session,
                ),
            },
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_service."
            "ScenarioGroupRepository",
            return_value=groups,
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_service."
            "ScenarioRepository",
            return_value=scenarios,
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_service."
            "SignpostRepository",
            return_value=signposts,
        ),
        pytest.raises(MIBaseError) as error,
    ):
        ScenarioGroupService().apply_confirmation(
            10,
            {"title": "확정 제목"},
            {
                "headers": [{"key": "d1", "label": "공급", "display_order": 1}],
                "rows": [
                    {
                        "scenario_id": 100,
                        "cells": {"d1": "d1_v2"},
                        "signposts": [{"signpost_id": 1000, "label": "신호"}],
                    },
                ],
            },
            user_id=7,
        )

    assert error.value.error_code is ErrorCode.SCENARIO_CONFIRMATION_STALE
    groups.fetch_by_id.assert_called_once_with(10, for_update=True)
    scenarios.fetch_models_by_group_id.assert_called_once_with(10, for_update=True)
    scenarios.update_from_payload.assert_not_called()
    scenarios.update_status.assert_not_called()
    signposts.update_from_payload.assert_not_called()
    groups.update_group.assert_not_called()
    session.commit.assert_not_called()
    session.rollback.assert_called_once_with()


def test_confirmation_rejects_stale_header_order_even_when_display_orders_claim_canonical_order() -> None:
    session, groups, scenarios, signposts, _unused = _repositories()
    groups.fetch_by_id.return_value.dimension_selected = ["b", "a"]
    with (
        patch.dict(
            sys.modules,
            {"apps.common.configs.database.sync_database.connection": _connection_module(session)},
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_service.ScenarioGroupRepository",
            return_value=groups,
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_service.ScenarioRepository",
            return_value=scenarios,
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_service.SignpostRepository",
            return_value=signposts,
        ),
        pytest.raises(MIBaseError) as error,
    ):
        ScenarioGroupService().apply_confirmation(
            10,
            {"title": "확정 제목"},
            {
                "headers": [
                    {"key": "a", "display_order": 2},
                    {"key": "b", "display_order": 1},
                ],
                "rows": [{"scenario_id": 100, "cells": {"a": "a1", "b": "b1"}}],
            },
            user_id=7,
        )

    assert error.value.error_code is ErrorCode.SCENARIO_CONFIRMATION_STALE
    assert "header" in error.value.error_message
    scenarios.update_from_payload.assert_not_called()
    session.commit.assert_not_called()


def test_confirmation_owner_mismatch_fails_before_loading_scenarios() -> None:
    session, groups, scenarios, signposts, _unused = _repositories(owner=8)
    with (
        patch.dict(
            sys.modules,
            {
                "apps.common.configs.database.sync_database.connection": _connection_module(
                    session,
                ),
            },
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_service."
            "ScenarioGroupRepository",
            return_value=groups,
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_service."
            "ScenarioRepository",
            return_value=scenarios,
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_service."
            "SignpostRepository",
            return_value=signposts,
        ),
        pytest.raises(MIBaseError) as error,
    ):
        ScenarioGroupService().apply_confirmation(
            10,
            {"title": "확정 제목"},
            {"headers": [], "rows": []},
            user_id=7,
        )

    assert error.value.error_code is ErrorCode.SCENARIO_GROUP_OWNERSHIP_CONFLICT
    scenarios.fetch_models_by_group_id.assert_not_called()
    session.rollback.assert_called_once_with()


def test_confirmation_commit_failure_rolls_back_all_changes() -> None:
    session, groups, scenarios, signposts, _unused = _repositories()
    session.commit.side_effect = RuntimeError("commit failed")
    groups.model_to_dict.return_value = {"scenario_group_id": 10}

    with (
        patch.dict(
            sys.modules,
            {
                "apps.common.configs.database.sync_database.connection": _connection_module(
                    session,
                ),
            },
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_service."
            "ScenarioGroupRepository",
            return_value=groups,
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_service."
            "ScenarioRepository",
            return_value=scenarios,
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_service."
            "SignpostRepository",
            return_value=signposts,
        ),
        pytest.raises(RuntimeError, match="commit failed"),
    ):
        ScenarioGroupService().apply_confirmation(
            10,
            {"title": "확정 제목"},
            {
                "headers": [{"key": "d1", "label": "공급", "display_order": 1}],
                "rows": [
                    {
                        "scenario_id": 100,
                        "cells": {"d1": "d1_v1"},
                        "signposts": [{"signpost_id": 1000, "label": "신호"}],
                    },
                ],
            },
            user_id=7,
        )

    scenarios.update_from_payload.assert_called_once()
    scenarios.update_status.assert_called_once()
    signposts.update_from_payload.assert_called_once()
    groups.update_group.assert_called_once()
    session.rollback.assert_called_once_with()
    session.close.assert_called_once_with()


def test_hard_delete_repository_deletes_only_master_tables() -> None:
    session = Mock()
    scenario_ids_result = Mock()
    scenario_ids_result.scalars.return_value.all.return_value = [100]
    session.execute.side_effect = [
        scenario_ids_result,
        SimpleNamespace(rowcount=2),
        SimpleNamespace(rowcount=1),
        SimpleNamespace(rowcount=1),
    ]

    counts = ScenarioGroupRepository(session=session).hard_delete_group(10)

    assert counts == {
        "tmm_mi_signpost_m": 2,
        "tmm_mi_scenario_m": 1,
        "tmm_mi_scenario_group_m": 1,
    }
    deleted_tables = [call.args[0].table.name for call in session.execute.call_args_list[1:]]
    assert deleted_tables == [
        "tmm_mi_signpost_m",
        "tmm_mi_scenario_m",
        "tmm_mi_scenario_group_m",
    ]


def test_hard_delete_foreign_key_failure_rolls_back_transaction() -> None:
    session = Mock()
    repository = Mock(spec=ScenarioGroupRepository)
    repository.fetch_by_id_for_query.return_value = SimpleNamespace(scenario_group_id=10)
    repository.hard_delete_group.side_effect = RuntimeError("child foreign key blocked delete")

    with (
        patch.dict(
            sys.modules,
            {
                "apps.common.configs.database.sync_database.connection": _connection_module(
                    session,
                ),
            },
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_service."
            "ScenarioGroupRepository",
            return_value=repository,
        ),
        patch.object(ScenarioGroupService, "_assert_delete_authorization"),
        pytest.raises(RuntimeError, match="child foreign key blocked delete"),
    ):
        ScenarioGroupService().hard_delete_group(
            10,
            user_id=7,
            confirm=True,
            authorization="Bearer test",
        )

    session.commit.assert_not_called()
    session.rollback.assert_called_once_with()
    session.close.assert_called_once_with()
