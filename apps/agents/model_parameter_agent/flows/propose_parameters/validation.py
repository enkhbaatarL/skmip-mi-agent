from __future__ import annotations

from typing import Any, NoReturn

from apps.agents.model_parameter_agent.flows.propose_parameters.state import ModelParameterProposalState
from apps.agents.model_parameter_agent.schemas.api.parameters import ProposalParameter
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


def _normalize_key(value: Any) -> str:
    return str(value or "").strip()


def _event_type_l2_id_from_context(scenario_context: dict[str, Any]) -> int | None:
    scenario_group = scenario_context.get("scenario_group") or {}
    event_type = scenario_context.get("event_type") or {}
    raw_value = (
        scenario_group.get("event_type_l2_id")
        or event_type.get("event_type_l2_id")
        or event_type.get("level_2_id")
    )
    if raw_value is None:
        return None
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return None


def _scenario_dimension_keys(scenario_context: dict[str, Any]) -> set[str]:
    scenario = scenario_context.get("scenario") or {}
    dimension_values = scenario.get("dimension_values") or {}
    keys = {
        _normalize_key(key)
        for key in dimension_values
        if _normalize_key(key)
    }
    if keys:
        return keys

    template = scenario_context.get("dimension_template") or []
    return {
        _normalize_key(item.get("dim_key") or item.get("dimension_key") or item.get("key"))
        for item in template
        if isinstance(item, dict)
        and _normalize_key(item.get("dim_key") or item.get("dimension_key") or item.get("key"))
    }


def _parameter_definitions_by_name(
    parameter_definitions: list[dict[str, Any]],
) -> set[str]:
    return {
        _normalize_key(
            definition.get("canonical_parameter_name")
            or definition.get("parameter_name"),
        )
        for definition in parameter_definitions
        if _normalize_key(
            definition.get("canonical_parameter_name")
            or definition.get("parameter_name"),
        )
        and _normalize_key(definition.get("model_file"))
        and _normalize_key(definition.get("model_sheet"))
    }


def _has_mapping_candidates_from_db_rows(
    *,
    scenario_context: dict[str, Any],
) -> bool:
    resources = scenario_context.get("parameter_mapping_resources") or {}
    mapping_rules = resources.get("mapping_rules") or []
    parameter_definitions = resources.get("parameter_definitions") or []
    if not mapping_rules or not parameter_definitions:
        raise MIBaseError(
            ErrorCode.INVALID_REQUEST,
            detail="parameter mapping resources not loaded from DB",
        )

    event_type_l2_id = _event_type_l2_id_from_context(scenario_context)
    dimension_keys = _scenario_dimension_keys(scenario_context)
    parameter_names = _parameter_definitions_by_name(parameter_definitions)
    if event_type_l2_id is None or not dimension_keys or not parameter_names:
        return False

    for rule in mapping_rules:
        if str(rule.get("mapping_method") or "").strip() not in {"direct", "routing"}:
            continue
        try:
            rule_event_type_l2_id = int(rule.get("event_type_l2_id"))
        except (TypeError, ValueError):
            continue
        if rule_event_type_l2_id != event_type_l2_id:
            continue
        if _normalize_key(rule.get("dimension_key")) not in dimension_keys:
            continue
        parameter_name = _normalize_key(
            rule.get("canonical_parameter_name")
            or rule.get("parameter_name"),
        )
        if parameter_name in parameter_names:
            return True
    return False


def _ensure_context_has_mapping_candidates(
    *,
    scenario_id: int,
    scenario_context: dict[str, Any],
) -> None:
    if _has_mapping_candidates_from_db_rows(
        scenario_context=scenario_context,
    ):
        return
    logger.warning(
        "[model-parameter] no DB mapping candidates before callback accept | scenario_id={}",
        scenario_id,
    )
    _raise_no_mapping_candidates({"scenario_id": scenario_id})
