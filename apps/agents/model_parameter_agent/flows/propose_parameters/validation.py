from __future__ import annotations

from typing import Any, NoReturn

from apps.agents.model_parameter_agent.flows.propose_parameters.state import ModelParameterProposalState
from apps.agents.model_parameter_agent.schemas.api.parameters import ProposalParameter
from apps.agents.model_parameter_agent.utils.parameter_mapping import (
    get_parameter_knowledge_base_from_resources,
    match_parameter_candidates,
)
from apps.common.exceptions.custom import MIBaseError
from apps.common.logging.logger_config import logger
from apps.common.values.error_codes import ErrorCode


def _route_after_candidate_validation(state: ModelParameterProposalState | dict[str, Any]) -> str:
    candidates = (
        state.candidate_mappings
        if isinstance(state, ModelParameterProposalState)
        else state.get("candidate_mappings") or []
    )
    if candidates:
        return "load_basecase_samples"
    _raise_no_mapping_candidates(state)


def _route_after_basecase_filter(state: ModelParameterProposalState | dict[str, Any]) -> str:
    slots = (
        state.parameter_slots
        if isinstance(state, ModelParameterProposalState)
        else state.get("parameter_slots") or []
    )
    selected_slots = [
        slot
        for slot in slots
        if slot.get("selected", True) is not False
    ]
    if selected_slots:
        return "propose_parameter_values"
    return "finalize_empty_parameter_values"


def _scenario_id_from_state(state: ModelParameterProposalState | dict[str, Any]) -> Any:
    if isinstance(state, ModelParameterProposalState):
        return state.scenario_id
    return state.get("scenario_id")


def _raise_no_mapping_candidates(state: ModelParameterProposalState | dict[str, Any]) -> NoReturn:
    scenario_id = _scenario_id_from_state(state)
    raise MIBaseError(
        ErrorCode.INVALID_REQUEST,
        detail=(
            "No model parameter mapping candidates found"
            f" for scenario_id={scenario_id}"
        ),
    )


def _ensure_mapping_candidates(data: dict[str, Any]) -> None:
    if not data.get("candidate_mappings"):
        _raise_no_mapping_candidates(data)


def _raise_no_proposal_parameters(
    data: dict[str, Any],
    *,
    reason: str | None = None,
) -> NoReturn:
    scenario_id = _scenario_id_from_state(data)
    detail = (
        "No valid model parameter proposal parameters generated"
        f" for scenario_id={scenario_id}"
    )
    if reason:
        detail = f"{detail}: {reason}"
    raise MIBaseError(ErrorCode.INVALID_REQUEST, detail=detail)


def _ensure_proposal_parameters(
    data: dict[str, Any],
    proposal_parameters: list[ProposalParameter],
) -> None:
    if proposal_parameters:
        return
    warnings = [
        str(warning)
        for warning in (data.get("validation_warnings") or [])
        if str(warning).strip()
    ]
    _raise_no_proposal_parameters(
        data,
        reason="; ".join(warnings[-3:]) if warnings else None,
    )


def _mapping_candidates_for_context(
    *,
    scenario_id: int,
    scenario_context: dict[str, Any],
) -> list[dict[str, Any]]:
    state = ModelParameterProposalState(scenario_id=scenario_id)
    resources = scenario_context.get("parameter_mapping_resources") or {}
    mapping_rules = resources.get("mapping_rules") or []
    parameter_definitions = resources.get("parameter_definitions") or []
    if not mapping_rules or not parameter_definitions:
        raise MIBaseError(
            ErrorCode.INVALID_REQUEST,
            detail="parameter mapping resources not loaded from DB",
        )

    knowledge_base = get_parameter_knowledge_base_from_resources(
        mapping_rows=mapping_rules,
        parameter_rows=parameter_definitions,
        basecase_dir_path=state.basecase_dir_path,
        max_sample_rows=state.max_basecase_sample_rows,
        max_sample_cols=state.max_basecase_cols,
    )
    candidates, _non_inputs, warnings = match_parameter_candidates(
        knowledge_base,
        scenario_context,
        max_candidates=state.max_candidates,
    )
    if not candidates:
        logger.warning(
            "[model-parameter] no mapping candidates before callback accept | scenario_id={} warnings={}",
            scenario_id,
            warnings,
        )
    return candidates


def _ensure_context_has_mapping_candidates(
    *,
    scenario_id: int,
    scenario_context: dict[str, Any],
) -> None:
    candidates = _mapping_candidates_for_context(
        scenario_id=scenario_id,
        scenario_context=scenario_context,
    )
    if not candidates:
        _raise_no_mapping_candidates({"scenario_id": scenario_id})
