# Copyright (c) 2026 SK Innovation E&S.
# ruff: noqa: S101

from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import UTC, datetime, timedelta

import pytest

from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode
from tests.manual.model_parameter_agent import runner_common
from tests.manual.model_parameter_agent.runner_common import run_confirmation_workflow


pytestmark = pytest.mark.model_parameter_core


def _proposal_row() -> dict[str, object]:
    return {
        "model_param_proposal_id": 901,
        "request_usr_id": 55,
        "status": "PROPOSED",
        "proposal_parameters": [
            {
                "parameterName": "GDP",
                "values": [{"proposedValue": 1.0}],
            },
        ],
        "confirmation_parameters": None,
        "confirmed_dtm": None,
        "mod_usr_logn_id": "40",
        "mod_dtm": datetime(2026, 9, 7, 9, 0, tzinfo=UTC),
    }


def test_confirmation_workflow_is_self_contained_and_verifies_all_required_cases() -> None:
    row = _proposal_row()
    confirmation_count = 0

    async def invoke(payload: dict[str, object]) -> dict[str, object]:
        nonlocal confirmation_count
        parameters = payload["data"]["confirmationParameters"]  # type: ignore[index]
        if not parameters:
            raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="empty")
        confirmation_count += 1
        row["status"] = "CONFIRMED"
        row["confirmation_parameters"] = deepcopy(parameters)
        row["confirmed_dtm"] = datetime(2026, 9, 7, 9, 0, tzinfo=UTC) + timedelta(
            seconds=confirmation_count,
        )
        row["mod_usr_logn_id"] = str(payload["userId"])
        return {
            "status": "success",
            "data": {
                "modelParamProposalId": 901,
                "status": "CONFIRMED",
            },
        }

    result, confirmed_row = asyncio.run(
        run_confirmation_workflow(
            deepcopy(row),
            invoke_confirmation=invoke,
            fetch_proposal=lambda _proposal_id: deepcopy(row),
        ),
    )

    assert result["status"] == "PASS"
    assert result["invalid_payload"]["rollback_verified"] is True
    assert result["valid_confirmation"]["status"] == "PASS"
    assert result["reconfirmation"]["status"] == "PASS"
    assert confirmation_count == 2
    assert confirmed_row["status"] == "CONFIRMED"


def test_confirmation_workflow_fails_without_a_persisted_proposed_payload() -> None:
    row = _proposal_row()
    row["proposal_parameters"] = []
    invoked = False

    async def invoke(_payload: dict[str, object]) -> dict[str, object]:
        nonlocal invoked
        invoked = True
        return {}

    result, final_row = asyncio.run(
        run_confirmation_workflow(
            row,
            invoke_confirmation=invoke,
            fetch_proposal=lambda _proposal_id: {},
        ),
    )

    assert result["status"] == "FAIL"
    assert "precondition failed" in result["message"]
    assert final_row is row
    assert invoked is False


def test_confirmation_workflow_stops_after_empty_payload_contract_failure() -> None:
    row = _proposal_row()
    calls = 0

    async def invoke(_payload: dict[str, object]) -> dict[str, object]:
        nonlocal calls
        calls += 1
        row["status"] = "CONFIRMED"
        return {"status": "success"}

    result, final_row = asyncio.run(
        run_confirmation_workflow(
            deepcopy(row),
            invoke_confirmation=invoke,
            fetch_proposal=lambda _proposal_id: deepcopy(row),
        ),
    )

    assert result["status"] == "FAIL"
    assert result["valid_confirmation"]["status"] == "NOT_RUN"
    assert result["reconfirmation"]["status"] == "NOT_RUN"
    assert final_row["status"] == "CONFIRMED"
    assert calls == 1


def test_proposal_workflow_exception_retains_persisted_proposal_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tests.manual.model_parameter_agent import evaluate_proposals

    async def persisted_proposal(_scenario_id: int) -> dict[str, object]:
        return {
            "final_response": {
                "status": "success",
                "data": {"modelParamProposalId": 902},
            },
        }

    def fail_readback(_proposal_id: int | None) -> dict[str, object]:
        message = "read-back failed"
        raise RuntimeError(message)

    monkeypatch.setattr(evaluate_proposals, "_evaluate_scenario", persisted_proposal)
    monkeypatch.setattr(runner_common, "fetch_proposal_db_row", fail_readback)

    with pytest.raises(RuntimeError) as caught:
        asyncio.run(runner_common.execute_proposal_and_confirmation(501))

    retained = runner_common.runner_record_from_exception(caught.value)
    assert retained["scenario_id"] == 501
    assert retained["model_param_proposal_id"] == 902
    assert retained["failed_stage"] == "proposal DB read-back"
    assert retained["final_response"]["data"]["modelParamProposalId"] == 902


def test_output_failure_after_commit_retains_proposal_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tests.manual.model_parameter_agent import evaluate_proposals

    def committed_save(*_args: object, **_kwargs: object) -> int:
        return 903

    def fail_response_build(_raw_state: dict[str, object]) -> object:
        evaluate_proposals.ModelParameterService().save_proposal_result(
            scenario_context={},
            proposal_parameters=[],
        )
        message = "response serialization failed"
        raise RuntimeError(message)

    monkeypatch.setattr(
        evaluate_proposals.ModelParameterService,
        "save_proposal_result",
        committed_save,
    )
    monkeypatch.setattr(evaluate_proposals, "to_output", fail_response_build)
    failure_trace: dict[str, object] = {}

    with pytest.raises(RuntimeError):
        evaluate_proposals._serialize_output_with_persistence_trace(  # noqa: SLF001
            {},
            failure_trace,
        )

    assert failure_trace["proposal_persisted"] is True
    assert failure_trace["model_param_proposal_id"] == 903
