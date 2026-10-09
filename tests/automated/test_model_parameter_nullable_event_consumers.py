# ruff: noqa: S101, SLF001

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from apps.agents.interpret_agent.persistence import proposal_parameter_service
from apps.agents.interpret_agent.persistence.proposal_parameter_service import (
    ProposalParameterService,
)
from apps.agents.model_parameter_agent.presentation import (
    _callback_error_output,
    _callback_success_output,
    _to_response_data,
)
from apps.persistence.model_parameter.repository import ModelParameterRepository
from tests.manual.model_parameter_agent.evaluate_event_type_proposals import (
    _fetch_proposal_db_row,
)


class _ScalarRows:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def all(self) -> list[object]:
        return self._rows

    def one_or_none(self) -> object | None:
        return self._rows[0] if self._rows else None


class _ExecuteResult:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def scalars(self) -> _ScalarRows:
        return _ScalarRows(self._rows)


def _proposal_parameters() -> list[dict[str, object]]:
    return [
        {
            "parameterName": "GDP",
            "modelTarget": {
                "slotAxesFieldNames": ["Country", "Year"],
            },
            "values": [
                {
                    "Country": "South Korea",
                    "Year": 2027,
                    "basecaseValue": 0.02,
                    "proposedValue": 0.018,
                },
            ],
        },
    ]


def _proposal_model() -> SimpleNamespace:
    return SimpleNamespace(
        model_param_proposal_id=901,
        scenario_id=100,
        scenario_group_id=20,
        mi_event_id=None,
        mi_base_case_id=15,
        request_usr_id=None,
        status="PROPOSED",
        callback_status="SKIPPED",
        proposal_completed_dtm=None,
        callback_sent_dtm=None,
        confirmed_dtm=None,
        error_code=None,
        error_message=None,
        proposal_parameters=_proposal_parameters(),
        confirmation_parameters=None,
        mod_usr_logn_id="system",
        mod_dtm=None,
    )


def test_repository_null_event_row_is_consumed_by_interpret_normalization() -> None:
    session = Mock()
    session.execute.return_value = _ExecuteResult([_proposal_model()])

    proposals = ModelParameterRepository(session=session).fetch_proposals_by_group(20)
    scenario_features, base_features, target_ids = ProposalParameterService()._normalize_features(proposals)

    assert proposals[0]["mi_event_id"] is None
    assert proposals[0]["model_param_proposal_id"] == 901
    assert proposals[0]["mi_base_case_id"] == 15
    assert target_ids == ["100"]
    assert base_features[0].values == [0.02]
    assert scenario_features["100"].features[0].values == [0.018]


def test_interpret_loader_does_not_require_proposal_event_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposal = {
        "model_param_proposal_id": 901,
        "scenario_id": 100,
        "scenario_group_id": 20,
        "mi_event_id": None,
        "mi_base_case_id": 15,
        "status": "PROPOSED",
        "proposal_parameters": _proposal_parameters(),
    }
    session = Mock()
    repository = Mock()
    repository.fetch_proposals_by_group.return_value = [proposal]

    from apps.common.configs.database.sync_database import connection

    monkeypatch.setattr(connection, "get_sync_session", lambda: session)
    monkeypatch.setattr(
        proposal_parameter_service,
        "ModelParameterRepository",
        lambda session: repository,
    )
    monkeypatch.setattr(
        ProposalParameterService,
        "_load_prices",
        lambda self, session, scenario_group_id, target_ids, *, mi_base_case_id: ({}, 501, {}),
    )

    result = ProposalParameterService().load_interpret_input(scenario_group_id=20)

    assert result.scenario_group_id == 20
    assert result.mi_base_case_id == 15
    assert result.mi_base_price_run_seq == 501
    assert result.model_param_proposal_ids == {"100": 901}
    assert result.scenario_ids == ["100"]
    assert result.features == ["GDP"]
    repository.fetch_proposals_by_group.assert_called_once_with(20, None)
    session.close.assert_called_once_with()


def test_v3_api_and_callbacks_serialize_event_id_as_explicit_null() -> None:
    response_data = _to_response_data(
        {
            "scenario_id": 100,
            "scenario_context": {
                "scenario": {"scenario_id": 100, "scenario_group_id": 20},
                "scenario_group": {
                    "scenario_group_id": 20,
                    "mi_event_id": None,
                    "generation_strategy": "multi_event_composite_dimensions",
                },
                "events": [{"mi_event_id": 101}, {"mi_event_id": 102}],
            },
        },
        model_param_proposal_id=901,
        proposal_parameters=[],
    )

    response_payload = response_data.model_dump(by_alias=True, exclude_none=False)
    success_payload = _callback_success_output(response_data).model_dump(
        by_alias=True,
        mode="json",
    )
    error_payload = _callback_error_output(
        message="proposal failed",
        error_code="UNKNOWN_ERROR",
        model_param_proposal_id=901,
        scenario_id=100,
        scenario_group_id=20,
        event_id=None,
    ).model_dump(by_alias=True, mode="json")

    assert response_payload["scenarioGroupId"] == 20
    assert response_payload["eventId"] is None
    assert success_payload["data"]["eventId"] is None
    assert error_payload["data"]["eventId"] is None


def test_event_type_manual_runner_readback_preserves_null_event_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposal = _proposal_model()
    session = Mock()
    session.execute.return_value = _ExecuteResult([proposal])

    from apps.common.configs.database.sync_database import connection

    monkeypatch.setattr(connection, "get_sync_session", lambda: session)

    row = _fetch_proposal_db_row(901)

    assert row["model_param_proposal_id"] == 901
    assert row["scenario_group_id"] == 20
    assert row["mi_event_id"] is None
    session.close.assert_called_once_with()
