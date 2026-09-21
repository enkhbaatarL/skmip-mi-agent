# Copyright (c) 2026 SK Innovation E&S.

from __future__ import annotations

# ruff: noqa: S101
from unittest.mock import patch

import pytest

from apps.agents.scenario_group_agent.flows.confirm_generation.nodes import (
    load_scenario_group,
    load_signposts,
)
from apps.agents.scenario_group_agent.flows.confirm_generation.state import (
    ConfirmGenerationState,
)
from apps.common.exceptions.custom import MIBaseError
from apps.persistence.scenario.schema import ScenarioPayload
from apps.persistence.scenario_group.schema import ScenarioGroupPayload


V4_STRATEGY = "multi_event_model_lever_dimensions"


def test_v4_direct_confirmation_reuses_latest_validation_gate() -> None:
    accepted_group = {
        "scenario_group_id": 10,
        "request_usr_id": 101,
        "api_version": "v4",
        "generation_strategy": V4_STRATEGY,
        "stage": "scenario_validated",
    }
    with (
        patch(
            "apps.agents.scenario_group_agent.flows.confirm_generation.nodes."
            "ScenarioGroupService.load_by_id",
            return_value=accepted_group,
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.confirm_generation.nodes."
            "ScenarioService.accept_validation_change_set",
            return_value={"scenario_group": accepted_group},
        ) as accept_validation,
    ):
        result = load_scenario_group(ConfirmGenerationState(scenario_group_id=10, user_id=101))

    assert result["scenario_group"] == accepted_group
    accept_validation.assert_called_once_with(
        scenario_group_id=10,
        user_id=101,
        create_signpost_operation=False,
    )


def test_v4_confirmation_allows_empty_signpost_collection() -> None:
    state = ConfirmGenerationState(
        scenario_group_id=10,
        user_id=101,
        scenario_group=ScenarioGroupPayload(
            scenario_group_id=10,
            generation_strategy=V4_STRATEGY,
        ),
        scenarios=[ScenarioPayload(scenario_id=100, scenario_group_id=10)],
    )

    with patch(
        "apps.agents.scenario_group_agent.flows.confirm_generation.nodes."
        "SignpostService.load_by_scenario_ids",
        return_value=[],
    ):
        result = load_signposts(state)

    assert result == {"signposts": []}


def test_v4_direct_confirmation_rejects_group_without_validation() -> None:
    group = {
        "scenario_group_id": 10,
        "request_usr_id": 101,
        "api_version": "v4",
        "generation_strategy": V4_STRATEGY,
        "stage": "scenario_created",
    }
    with (
        patch(
            "apps.agents.scenario_group_agent.flows.confirm_generation.nodes."
            "ScenarioGroupService.load_by_id",
            return_value=group,
        ),
        pytest.raises(MIBaseError, match="Validation"),
    ):
        load_scenario_group(ConfirmGenerationState(scenario_group_id=10, user_id=101))


def test_legacy_confirmation_still_requires_signposts() -> None:
    state = ConfirmGenerationState(
        scenario_group_id=10,
        user_id=101,
        scenario_group=ScenarioGroupPayload(
            scenario_group_id=10,
            generation_strategy="multi_event_composite_dimensions",
        ),
        scenarios=[ScenarioPayload(scenario_id=100, scenario_group_id=10)],
    )

    with (
        patch(
            "apps.agents.scenario_group_agent.flows.confirm_generation.nodes."
            "SignpostService.load_by_scenario_ids",
            return_value=[],
        ),
        pytest.raises(MIBaseError, match="No signposts found"),
    ):
        load_signposts(state)
