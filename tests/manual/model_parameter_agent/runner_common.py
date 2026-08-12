# Copyright (c) 2026 SK Innovation E&S.
# ruff: noqa: ANN401, SLF001

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
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
    """Serialize proposal evidence without coercing a v3 NULL event ID."""
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


async def run_existing_confirmation_workflow(
    proposal_row: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Reuse the established confirmation contract and shared DB read-back."""
    from tests.manual.model_parameter_agent import (
        evaluate_event_type_proposals as event_type_runner,
    )

    return await event_type_runner._run_confirmation_workflow(proposal_row)


async def execute_proposal_and_confirmation(scenario_id: int) -> dict[str, Any]:
    """Run the existing proposal graph, persist it, and verify confirmation."""
    from tests.manual.model_parameter_agent.evaluate_proposals import (
        _evaluate_scenario,
    )

    record = await _evaluate_scenario(scenario_id)
    model_param_proposal_id = proposal_id(record.get("final_response") or {})
    proposal_row = fetch_proposal_db_row(model_param_proposal_id)
    confirmation, confirmed_row = await run_existing_confirmation_workflow(
        proposal_row,
    )
    record["proposal_db_row"] = confirmed_row
    record["confirmation"] = confirmation
    return record


__all__ = [
    "execute_proposal_and_confirmation",
    "fetch_proposal_db_row",
    "json_safe",
    "proposal_id",
    "run_existing_confirmation_workflow",
    "serialize_proposal_row",
]
