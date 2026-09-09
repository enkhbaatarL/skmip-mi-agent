# Copyright (c) 2026 SK Innovation E&S.
# ruff: noqa: ANN401

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import date, datetime
from decimal import Decimal
import time
from typing import Any

from sqlalchemy import select

from apps.persistence.model_parameter.models import MiModelParamProposalModel


def json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [json_safe(item) for item in value]
    if hasattr(value, "value"):
        return value.value
    return value


def proposal_id(final_response: dict[str, Any]) -> int | None:
    data = final_response.get("data") or {}
    raw = data.get("modelParamProposalId") or data.get("model_param_proposal_id")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def serialize_proposal_row(proposal: Any) -> dict[str, Any]:
    """Serialize proposal evidence without coercing a multi-event NULL event ID."""
    return {
        "model_param_proposal_id": int(proposal.model_param_proposal_id),
        "scenario_id": int(proposal.scenario_id),
        "scenario_group_id": int(proposal.scenario_group_id),
        "mi_event_id": (int(proposal.mi_event_id) if proposal.mi_event_id is not None else None),
        "request_usr_id": (int(proposal.request_usr_id) if proposal.request_usr_id is not None else None),
        "status": str(proposal.status),
        "callback_status": str(proposal.callback_status),
        "proposal_completed_dtm": proposal.proposal_completed_dtm,
        "callback_sent_dtm": proposal.callback_sent_dtm,
        "confirmed_dtm": proposal.confirmed_dtm,
        "error_code": proposal.error_code,
        "error_message": proposal.error_message,
        "proposal_parameters": json_safe(proposal.proposal_parameters or []),
        "confirmation_parameters": json_safe(proposal.confirmation_parameters),
        "mod_usr_logn_id": proposal.mod_usr_logn_id,
        "mod_dtm": proposal.mod_dtm,
    }


def fetch_proposal_db_row(model_param_proposal_id: int | None) -> dict[str, Any]:
    if model_param_proposal_id is None:
        return {}
    from apps.common.configs.database.sync_database.connection import get_sync_session

    session = get_sync_session()
    try:
        proposal = (
            session.execute(
                select(MiModelParamProposalModel).where(
                    MiModelParamProposalModel.model_param_proposal_id == model_param_proposal_id,
                    MiModelParamProposalModel.del_yn == "N",
                ),
            )
            .scalars()
            .one_or_none()
        )
        if proposal is None:
            return {
                "model_param_proposal_id": model_param_proposal_id,
                "fetch_status": "NOT_FOUND",
            }
        return serialize_proposal_row(proposal)
    finally:
        session.close()


_ROLLBACK_SNAPSHOT_FIELDS = (
    "status",
    "proposal_parameters",
    "confirmation_parameters",
    "confirmed_dtm",
    "mod_usr_logn_id",
    "mod_dtm",
)

ConfirmationInvoker = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]
ProposalFetcher = Callable[[int | None], dict[str, Any]]
RUNNER_RECORD_ATTR = "_model_parameter_runner_record"


def attach_runner_record(exc: BaseException, record: dict[str, Any]) -> None:
    """Attach retained workflow evidence without replacing the original error."""
    try:
        setattr(exc, RUNNER_RECORD_ATTR, record)
    except Exception:  # Third-party exceptions may reject attributes.
        return


def runner_record_from_exception(exc: BaseException) -> dict[str, Any]:
    record = getattr(exc, RUNNER_RECORD_ATTR, None)
    return record if isinstance(record, dict) else {}


def _rollback_snapshot(row: dict[str, Any]) -> dict[str, Any]:
    return {field: row.get(field) for field in _ROLLBACK_SNAPSHOT_FIELDS}


def _confirmation_request_payload(
    *,
    proposal_row: dict[str, Any],
    confirmation_parameters: list[dict[str, Any]],
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model_param_proposal_id": int(proposal_row["model_param_proposal_id"]),
        "data": {"confirmationParameters": confirmation_parameters},
    }
    if proposal_row.get("request_usr_id") is not None:
        payload["userId"] = int(proposal_row["request_usr_id"])
    return payload


async def _invoke_confirmation(payload: dict[str, Any]) -> dict[str, Any]:
    from apps.agents.model_parameter_agent.flows.confirm_parameters.flow import (
        run_confirm_parameters,
    )

    response = await run_confirm_parameters(payload)
    return response.model_dump(by_alias=True, exclude_none=False)


def _confirmation_failure(
    *,
    elapsed_seconds: float,
    message: str,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": "FAIL",
        "elapsed_seconds": elapsed_seconds,
        "message": message,
    }
    if before is not None:
        result["before"] = before
    if after is not None:
        result["after"] = after
    return result


async def run_confirmation_workflow(
    proposal_row: dict[str, Any],
    *,
    invoke_confirmation: ConfirmationInvoker = _invoke_confirmation,
    fetch_proposal: ProposalFetcher = fetch_proposal_db_row,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run the reusable confirmation contract without importing a legacy runner."""
    from apps.common.exceptions.custom import MIBaseError
    from apps.common.values.error_codes import ErrorCode

    workflow_started = time.perf_counter()
    model_param_proposal_id = proposal_row.get("model_param_proposal_id")
    proposal_parameters = proposal_row.get("proposal_parameters")
    result: dict[str, Any] = {
        "status": "FAIL",
        "model_param_proposal_id": model_param_proposal_id,
        "invalid_payload": {"status": "NOT_RUN"},
        "valid_confirmation": {"status": "NOT_RUN"},
        "reconfirmation": {"status": "NOT_RUN"},
    }
    if (
        model_param_proposal_id is None
        or proposal_row.get("status") != "PROPOSED"
        or not isinstance(proposal_parameters, list)
        or not proposal_parameters
    ):
        result["message"] = (
            "confirmation precondition failed: a PROPOSED row with non-empty proposal_parameters is required"
        )
        result["elapsed_seconds"] = time.perf_counter() - workflow_started
        return result, proposal_row

    empty_before = _rollback_snapshot(proposal_row)
    empty_started = time.perf_counter()
    empty_error: Exception | None = None
    try:
        await invoke_confirmation(
            _confirmation_request_payload(
                proposal_row=proposal_row,
                confirmation_parameters=[],
            ),
        )
    except Exception as exc:
        empty_error = exc
    empty_elapsed = time.perf_counter() - empty_started
    after_empty = fetch_proposal(int(model_param_proposal_id))
    empty_rollback_ok = _rollback_snapshot(after_empty) == empty_before
    if (
        isinstance(empty_error, MIBaseError)
        and empty_error.error_code is ErrorCode.INVALID_REQUEST
        and empty_rollback_ok
    ):
        result["invalid_payload"] = {
            "status": "PASS",
            "elapsed_seconds": empty_elapsed,
            "error_code": empty_error.error_code.name,
            "rollback_verified": True,
        }
    else:
        result["invalid_payload"] = _confirmation_failure(
            elapsed_seconds=empty_elapsed,
            message=(
                "empty confirmation must raise INVALID_REQUEST without changing the row; "
                f"error={empty_error!r}, rollback_verified={empty_rollback_ok}"
            ),
            before=empty_before,
            after=_rollback_snapshot(after_empty),
        )
        result["message"] = (
            "confirmation workflow stopped because the empty-payload rollback "
            "contract failed"
        )
        result["elapsed_seconds"] = time.perf_counter() - workflow_started
        return result, after_empty

    valid_started = time.perf_counter()
    valid_response: dict[str, Any] | None = None
    valid_error: Exception | None = None
    try:
        valid_response = await invoke_confirmation(
            _confirmation_request_payload(
                proposal_row=proposal_row,
                confirmation_parameters=proposal_parameters,
            ),
        )
    except Exception as exc:
        valid_error = exc
    valid_elapsed = time.perf_counter() - valid_started
    after_valid = fetch_proposal(int(model_param_proposal_id))
    valid_data = (valid_response or {}).get("data") or {}
    valid_checks = {
        "call_succeeded": valid_error is None,
        "response_success": (valid_response or {}).get("status") == "success",
        "response_id_matches": valid_data.get("modelParamProposalId") == model_param_proposal_id,
        "response_status_confirmed": valid_data.get("status") == "CONFIRMED",
        "db_status_confirmed": after_valid.get("status") == "CONFIRMED",
        "confirmation_payload_matches": after_valid.get("confirmation_parameters") == proposal_parameters,
        "confirmed_dtm_populated": after_valid.get("confirmed_dtm") is not None,
        "proposal_payload_unchanged": after_valid.get("proposal_parameters") == proposal_parameters,
    }
    request_usr_id = proposal_row.get("request_usr_id")
    if request_usr_id is not None:
        valid_checks["modifier_matches_request_user"] = str(after_valid.get("mod_usr_logn_id")) == str(request_usr_id)
    if all(valid_checks.values()):
        result["valid_confirmation"] = {
            "status": "PASS",
            "elapsed_seconds": valid_elapsed,
            "checks": valid_checks,
        }
    else:
        result["valid_confirmation"] = _confirmation_failure(
            elapsed_seconds=valid_elapsed,
            message=f"valid confirmation contract failed: error={valid_error!r}, checks={valid_checks}",
            before=_rollback_snapshot(proposal_row),
            after=_rollback_snapshot(after_valid),
        )

    if result["valid_confirmation"]["status"] == "PASS":
        first_confirmed_dtm = after_valid.get("confirmed_dtm")
        reconfirm_started = time.perf_counter()
        reconfirm_response: dict[str, Any] | None = None
        reconfirm_error: Exception | None = None
        try:
            reconfirm_response = await invoke_confirmation(
                _confirmation_request_payload(
                    proposal_row=proposal_row,
                    confirmation_parameters=proposal_parameters,
                ),
            )
        except Exception as exc:
            reconfirm_error = exc
        reconfirm_elapsed = time.perf_counter() - reconfirm_started
        after_reconfirm = fetch_proposal(int(model_param_proposal_id))
        reconfirm_data = (reconfirm_response or {}).get("data") or {}
        refreshed_dtm = after_reconfirm.get("confirmed_dtm")
        reconfirm_checks = {
            "call_succeeded": reconfirm_error is None,
            "response_success": (reconfirm_response or {}).get("status") == "success",
            "response_id_matches": reconfirm_data.get("modelParamProposalId") == model_param_proposal_id,
            "response_status_confirmed": reconfirm_data.get("status") == "CONFIRMED",
            "db_status_confirmed": after_reconfirm.get("status") == "CONFIRMED",
            "confirmation_payload_matches": after_reconfirm.get("confirmation_parameters") == proposal_parameters,
            "proposal_payload_unchanged": after_reconfirm.get("proposal_parameters") == proposal_parameters,
            "confirmed_dtm_refreshed": (
                first_confirmed_dtm is not None
                and refreshed_dtm is not None
                and refreshed_dtm > first_confirmed_dtm
            ),
        }
        if all(reconfirm_checks.values()):
            result["reconfirmation"] = {
                "status": "PASS",
                "elapsed_seconds": reconfirm_elapsed,
                "checks": reconfirm_checks,
            }
        else:
            result["reconfirmation"] = _confirmation_failure(
                elapsed_seconds=reconfirm_elapsed,
                message=f"reconfirmation contract failed: error={reconfirm_error!r}, checks={reconfirm_checks}",
                before=_rollback_snapshot(after_valid),
                after=_rollback_snapshot(after_reconfirm),
            )
    else:
        after_reconfirm = after_valid
        result["reconfirmation"] = {
            "status": "N/A",
            "message": "valid confirmation failed",
        }

    required_subcases = (
        result["invalid_payload"]["status"],
        result["valid_confirmation"]["status"],
        result["reconfirmation"]["status"],
    )
    result["status"] = "PASS" if required_subcases == ("PASS", "PASS", "PASS") else "FAIL"
    result["elapsed_seconds"] = time.perf_counter() - workflow_started
    return result, after_reconfirm


async def execute_proposal_and_confirmation(scenario_id: int) -> dict[str, Any]:
    """Run the existing proposal graph, persist it, and verify confirmation."""
    from tests.manual.model_parameter_agent.evaluate_proposals import (
        _evaluate_scenario,
        _failure_trace_from_exception,
    )

    try:
        record = await _evaluate_scenario(scenario_id)
    except Exception as exc:
        failure_trace = _failure_trace_from_exception(exc)
        record = {
            **failure_trace,
            "scenario_id": scenario_id,
            "failed_stage": (
                failure_trace.get("failed_stage") or "proposal graph"
            ),
        }
        attach_runner_record(exc, record)
        raise

    record.setdefault("scenario_id", scenario_id)
    model_param_proposal_id = proposal_id(record.get("final_response") or {})
    record["model_param_proposal_id"] = model_param_proposal_id
    try:
        proposal_row = fetch_proposal_db_row(model_param_proposal_id)
    except Exception as exc:
        record["failed_stage"] = "proposal DB read-back"
        attach_runner_record(exc, record)
        raise
    record["proposal_db_row"] = proposal_row
    try:
        confirmation, confirmed_row = await run_confirmation_workflow(
            proposal_row,
        )
    except Exception as exc:
        record["failed_stage"] = "confirmation workflow"
        attach_runner_record(exc, record)
        raise
    record["proposal_db_row"] = confirmed_row
    record["confirmation"] = confirmation
    return record


__all__ = [
    "RUNNER_RECORD_ATTR",
    "attach_runner_record",
    "execute_proposal_and_confirmation",
    "fetch_proposal_db_row",
    "json_safe",
    "proposal_id",
    "run_confirmation_workflow",
    "runner_record_from_exception",
    "serialize_proposal_row",
]
