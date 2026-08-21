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


def _connection_module(session: Mock) -> ModuleType:
    module = ModuleType("apps.common.configs.database.sync_database.connection")
    module.get_sync_session = Mock(return_value=session)  # type: ignore[attr-defined]
    return module


def _repositories(*, owner: int = 7) -> tuple[Mock, Mock, Mock, Mock, Mock]:
    session = Mock()
    group_repository = Mock()
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
    groups.create_confirmation_snapshot.assert_not_called()
    session.commit.assert_not_called()
    session.rollback.assert_called_once_with()


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
