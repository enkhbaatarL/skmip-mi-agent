from __future__ import annotations

from collections.abc import Collection, Mapping
from decimal import Decimal
from typing import Any

from pydantic import BaseModel

from apps.agents.model_parameter_agent.utils.lut.keys import (
    apply_numeric_precision,
)
from apps.agents.model_parameter_agent.utils.lut.precision import (
    NumericPrecisionMode,
)
from apps.common.configs.config import get_settings
from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode
from apps.persistence.event.repository import EventRepository
from apps.persistence.model_parameter.repository import ModelParameterRepository
from apps.persistence.model_parameter.service import ModelImpactLeverService
from apps.persistence.scenario.repository import ScenarioRepository
from apps.persistence.scenario_group.repository import ScenarioGroupRepository


CONFIRMABLE_PROPOSAL_STATUSES = ("PROPOSED", "CONFIRMED")
PROCESSING_PROPOSAL_STATUSES = ("PROCESSING",)
CALLBACK_READY_PROPOSAL_STATUSES = ("PROPOSED", "CONFIRMED", "FAILED")
CALLBACK_TARGET_STATUSES = {"SUCCEEDED", "FAILED", "SKIPPED"}
PERSISTED_PARAMETER_VALUE_FIELDS = frozenset({"basecaseValue", "proposedValue"})
ParameterValuePrecision = Mapping[str, tuple[int, NumericPrecisionMode]]


def _json_payload(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", by_alias=True)
    if isinstance(value, dict):
        return {str(key): _json_payload(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_payload(item) for item in value]
    return value


def _normalize_persisted_parameter_values(
    value: Any,
    *,
    field_precision: ParameterValuePrecision,
    path: str = "parameters",
) -> Any:
    """Bound stored basecase/proposed values regardless of the caller path."""
    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            field_path = f"{path}.{key}"
            if key in PERSISTED_PARAMETER_VALUE_FIELDS and item is not None:
                max_decimal_places, precision_mode = field_precision[key]
                normalized[key] = apply_numeric_precision(
                    item,
                    label=field_path,
                    max_decimal_places=max_decimal_places,
                    mode=precision_mode,
                )
            else:
                normalized[key] = _normalize_persisted_parameter_values(
                    item,
                    field_precision=field_precision,
                    path=field_path,
                )
        return normalized
    if isinstance(value, list):
        return [
            _normalize_persisted_parameter_values(
                item,
                field_precision=field_precision,
                path=f"{path}[{index}]",
            )
            for index, item in enumerate(value)
        ]
    return value


def _parameter_json_payload(value: Any) -> Any:
    settings = get_settings()
    return _normalize_persisted_parameter_values(
        _json_payload(value),
        field_precision={
            "basecaseValue": (
                settings.model_parameter_basecase_value_max_decimal_places,
                settings.model_parameter_basecase_value_precision_mode,
            ),
            "proposedValue": (
                settings.model_parameter_proposed_value_max_decimal_places,
                settings.model_parameter_proposed_value_precision_mode,
            ),
        },
    )


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if hasattr(value, "value"):
        return value.value
    return value


def _proposal_for_update(
    repository: ModelParameterRepository,
    model_param_proposal_id: int,
) -> dict[str, Any]:
    proposal = repository.fetch_model_param_proposal_for_update(
        model_param_proposal_id,
    )
    if proposal is None:
        raise MIBaseError(
            ErrorCode.ENTITY_NOT_FOUND,
            detail=(
                "Model parameter proposal not found: "
                f"model_param_proposal_id={model_param_proposal_id}"
            ),
        )
    return proposal


def _ensure_proposal_status(
    proposal: dict[str, Any],
    *,
    model_param_proposal_id: int,
    allowed_statuses: Collection[str],
    action: str,
) -> None:
    status = str(proposal.get("status") or "")
    if status in allowed_statuses:
        return
    expected = " or ".join(allowed_statuses)
    raise MIBaseError(
        ErrorCode.INVALID_REQUEST,
        detail=(
            f"Model parameter proposal must be {expected} before {action}: "
            f"model_param_proposal_id={model_param_proposal_id}, status={status}"
        ),
    )


def _ensure_transition_updated(
    updated: bool,
    *,
    model_param_proposal_id: int,
) -> None:
    if updated:
        return
    raise MIBaseError(
        ErrorCode.ENTITY_NOT_FOUND,
        detail=(
            "Model parameter proposal disappeared during state transition: "
            f"model_param_proposal_id={model_param_proposal_id}"
        ),
    )


class ModelParameterService:
    def load_context(self, scenario_id: int) -> dict[str, Any]:
        from apps.common.configs.database.sync_database.connection import get_sync_session

        session = get_sync_session()
        try:
            scenario_repository = ScenarioRepository(session=session)
            group_repository = ScenarioGroupRepository(session=session)
            event_repository = EventRepository(session=session)
            model_parameter_repository = ModelParameterRepository(session=session)

            scenario = scenario_repository.fetch_model_by_id(scenario_id)
            if scenario is None:
                context = None
            else:
                group = group_repository.fetch_by_id(int(scenario.scenario_group_id))
                if group is None:
                    context = None
                else:
                    is_v4 = (
                        getattr(group, "generation_strategy", None)
                        == "multi_event_model_lever_dimensions"
                    )
                    if is_v4:
                        relations = group_repository.fetch_group_events(
                            int(group.scenario_group_id),
                        )
                        events = [
                            event_repository.fetch_event_by_id(
                                int(relation.mi_event_id),
                            )
                            for relation in relations
                        ]
                        events = [event for event in events if event is not None]
                        event = {
                            "event_title_ko": " / ".join(
                                str(
                                    item.get("event_title_ko")
                                    or item.get("event_title")
                                    or "",
                                )
                                for item in events
                                if isinstance(item, dict)
                            ),
                            "one_line_summary": "\n".join(
                                str(item.get("one_line_summary") or "")
                                for item in events
                                if isinstance(item, dict)
                            ),
                            "key_bullets": [
                                bullet
                                for item in events
                                if isinstance(item, dict)
                                for bullet in item.get("key_bullets") or []
                            ],
                            "detail_analysis": "\n".join(
                                str(item.get("detail_analysis") or "")
                                for item in events
                                if isinstance(item, dict)
                            ),
                        }
                        event_type = {}
                        dimension_template = (
                            getattr(group, "dimension_definitions", None) or []
                        )
                    else:
                        events = []
                        event = event_repository.fetch_event_by_id(
                            int(group.mi_event_id),
                        )
                        event_type = event_repository.fetch_event_type_by_l2_id(
                            int(group.event_type_l2_id),
                        )
                        dimension_template = (
                            scenario_repository.fetch_dimension_template(
                                int(group.event_type_l2_id),
                            )
                        )
                    mapping_rules, parameter_definitions = (
                        model_parameter_repository.fetch_parameter_mapping_resources()
                    )
                    context = {
                        "scenario": _scenario_to_context_dict(scenario),
                        "scenario_group": _group_to_context_dict(group),
                        "event": event or {},
                        "events": events,
                        "event_type": event_type or {},
                        "dimension_template": dimension_template,
                        "parameter_mapping_resources": {
                            "mapping_rules": mapping_rules,
                            "parameter_definitions": parameter_definitions,
                        },
                    }
        finally:
            session.close()

        if context is None:
            raise MIBaseError(
                ErrorCode.ENTITY_NOT_FOUND,
                detail=f"Scenario context not found: scenario_id={scenario_id}",
            )
        if (
            context["scenario_group"].get("generation_strategy")
            == "multi_event_model_lever_dimensions"
        ):
            impact_levers, catalog_version, catalog_checksum = (
                ModelImpactLeverService().load_active_catalog()
            )
            expected_checksum = context["scenario_group"].get(
                "impact_catalog_checksum",
            )
            if expected_checksum and expected_checksum != catalog_checksum:
                raise MIBaseError(
                    ErrorCode.INVALID_REQUEST,
                    detail=(
                        "Scenario group impact lever catalog revision no longer "
                        "matches the active catalog; regenerate the scenario group"
                    ),
                )
            context["impact_lever_catalog"] = [
                lever.model_dump() for lever in impact_levers
            ]
            context["impact_catalog_version"] = catalog_version
            context["impact_catalog_checksum"] = catalog_checksum
        return context

    def load_parameter_mapping_resources(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        from apps.common.configs.database.sync_database.connection import get_sync_session

        session = get_sync_session()
        try:
            return ModelParameterRepository(session=session).fetch_parameter_mapping_resources()
        finally:
            session.close()

    def load_model_parameter_definitions(self) -> list[dict[str, Any]]:
        from apps.common.configs.database.sync_database.connection import get_sync_session

        session = get_sync_session()
        try:
            return ModelParameterRepository(session=session).fetch_model_parameter_definitions()
        finally:
            session.close()

    def save_proposal_result(
        self,
        *,
        scenario_context: dict[str, Any],
        user_id: int | None = None,
        proposal_parameters: list[Any],
    ) -> int:
        from apps.common.configs.database.sync_database.connection import get_sync_session

        scenario = scenario_context.get("scenario") or {}
        scenario_group = scenario_context.get("scenario_group") or {}
        event = scenario_context.get("event") or {}
        scenario_id = _required_int(
            scenario.get("scenario_id"),
            field_name="scenario.scenario_id",
        )
        scenario_group_id = _required_int(
            scenario.get("scenario_group_id") or scenario_group.get("scenario_group_id"),
            field_name="scenario_group.scenario_group_id",
        )
        mi_event_id = _optional_int(
            event.get("mi_event_id") or scenario_group.get("mi_event_id"),
        )
        request_usr_id = _optional_int(user_id)
        payload = _parameter_json_payload(proposal_parameters)

        session = get_sync_session()
        try:
            proposal_id = ModelParameterRepository(session=session).create_model_param_proposal(
                scenario_id=scenario_id,
                scenario_group_id=scenario_group_id,
                mi_event_id=mi_event_id,
                request_usr_id=request_usr_id,
                proposal_parameters=payload,
            )
            session.commit()
            return proposal_id
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def create_processing_proposal(
        self,
        *,
        scenario_context: dict[str, Any],
        user_id: int | None = None,
    ) -> int:
        from apps.common.configs.database.sync_database.connection import get_sync_session

        scenario = scenario_context.get("scenario") or {}
        scenario_group = scenario_context.get("scenario_group") or {}
        event = scenario_context.get("event") or {}
        scenario_id = _required_int(
            scenario.get("scenario_id"),
            field_name="scenario.scenario_id",
        )
        scenario_group_id = _required_int(
            scenario.get("scenario_group_id") or scenario_group.get("scenario_group_id"),
            field_name="scenario_group.scenario_group_id",
        )
        mi_event_id = _optional_int(
            event.get("mi_event_id") or scenario_group.get("mi_event_id"),
        )
        request_usr_id = _optional_int(user_id)

        session = get_sync_session()
        try:
            proposal_id = ModelParameterRepository(
                session=session,
            ).create_processing_model_param_proposal(
                scenario_id=scenario_id,
                scenario_group_id=scenario_group_id,
                mi_event_id=mi_event_id,
                request_usr_id=request_usr_id,
            )
            session.commit()
            return proposal_id
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def complete_proposal_result(
        self,
        *,
        model_param_proposal_id: int,
        proposal_parameters: list[Any],
    ) -> None:
        from apps.common.configs.database.sync_database.connection import get_sync_session

        payload = _parameter_json_payload(proposal_parameters)
        session = get_sync_session()
        try:
            repository = ModelParameterRepository(session=session)
            proposal = _proposal_for_update(repository, model_param_proposal_id)
            _ensure_proposal_status(
                proposal,
                model_param_proposal_id=model_param_proposal_id,
                allowed_statuses=PROCESSING_PROPOSAL_STATUSES,
                action="completion",
            )
            updated = repository.complete_model_param_proposal(
                model_param_proposal_id=model_param_proposal_id,
                proposal_parameters=payload,
            )
            _ensure_transition_updated(
                updated,
                model_param_proposal_id=model_param_proposal_id,
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def fail_proposal_result(
        self,
        *,
        model_param_proposal_id: int,
        error_code: str,
        error_message: str,
    ) -> None:
        from apps.common.configs.database.sync_database.connection import get_sync_session

        session = get_sync_session()
        try:
            repository = ModelParameterRepository(session=session)
            proposal = _proposal_for_update(repository, model_param_proposal_id)
            _ensure_proposal_status(
                proposal,
                model_param_proposal_id=model_param_proposal_id,
                allowed_statuses=PROCESSING_PROPOSAL_STATUSES,
                action="failure",
            )
            updated = repository.fail_model_param_proposal(
                model_param_proposal_id=model_param_proposal_id,
                error_code=error_code,
                error_message=error_message,
            )
            _ensure_transition_updated(
                updated,
                model_param_proposal_id=model_param_proposal_id,
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update_callback_status(
        self,
        *,
        model_param_proposal_id: int,
        callback_status: str,
    ) -> None:
        from apps.common.configs.database.sync_database.connection import get_sync_session

        if callback_status not in CALLBACK_TARGET_STATUSES:
            raise MIBaseError(
                ErrorCode.INVALID_REQUEST,
                detail=f"Unsupported model parameter callback status: {callback_status}",
            )
        session = get_sync_session()
        try:
            repository = ModelParameterRepository(session=session)
            proposal = _proposal_for_update(repository, model_param_proposal_id)
            _ensure_proposal_status(
                proposal,
                model_param_proposal_id=model_param_proposal_id,
                allowed_statuses=CALLBACK_READY_PROPOSAL_STATUSES,
                action="callback status update",
            )
            current_callback_status = str(proposal.get("callback_status") or "")
            if current_callback_status != "PENDING":
                raise MIBaseError(
                    ErrorCode.INVALID_REQUEST,
                    detail=(
                        "Model parameter callback status must be PENDING before update: "
                        f"model_param_proposal_id={model_param_proposal_id}, "
                        f"callback_status={current_callback_status}"
                    ),
                )
            updated = repository.update_model_param_callback_status(
                model_param_proposal_id=model_param_proposal_id,
                callback_status=callback_status,
            )
            _ensure_transition_updated(
                updated,
                model_param_proposal_id=model_param_proposal_id,
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def confirm_proposal_result(
        self,
        *,
        model_param_proposal_id: int,
        user_id: int | None = None,
        confirmation_parameters: list[Any],
    ) -> dict[str, Any]:
        from apps.common.configs.database.sync_database.connection import get_sync_session

        payload = _parameter_json_payload(confirmation_parameters)
        session = get_sync_session()
        try:
            repository = ModelParameterRepository(session=session)
            proposal = _proposal_for_update(repository, model_param_proposal_id)
            _ensure_proposal_status(
                proposal,
                model_param_proposal_id=model_param_proposal_id,
                allowed_statuses=CONFIRMABLE_PROPOSAL_STATUSES,
                action="confirmation",
            )
            updated = repository.confirm_model_param_proposal(
                model_param_proposal_id=model_param_proposal_id,
                user_id=_optional_int(user_id),
                confirmation_parameters=payload,
            )
            _ensure_transition_updated(
                updated,
                model_param_proposal_id=model_param_proposal_id,
            )
            session.commit()
            return {
                "model_param_proposal_id": model_param_proposal_id,
                "status": "CONFIRMED",
            }
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


def _scenario_to_context_dict(scenario: Any) -> dict[str, Any]:
    return {
        "scenario_id": int(scenario.scenario_id),
        "scenario_group_id": int(scenario.scenario_group_id),
        "title": scenario.title,
        "narrative": scenario.narrative or "",
        "status": _json_safe(scenario.status),
        "dimension_values": _json_safe(scenario.dimension_values or {}),
        "probability_score": _json_safe(scenario.probability_score),
        "probability_delta": _json_safe(scenario.probability_delta),
        "impact": {
            "jkm": scenario.impact_jkm,
            "ttf": scenario.impact_ttf,
            "hh": scenario.impact_hh,
        },
        "baseline_yn": scenario.baseline_yn,
    }


def _group_to_context_dict(group: Any) -> dict[str, Any]:
    return {
        "scenario_group_id": int(group.scenario_group_id),
        "mi_event_id": _optional_int(group.mi_event_id),
        "event_type_l2_id": _optional_int(group.event_type_l2_id),
        "request_usr_id": (
            int(group.request_usr_id) if group.request_usr_id is not None else None
        ),
        "title": group.title,
        "summary": group.summary,
        "description": group.description,
        "dimension_selected": group.dimension_selected or [],
        "scenario_count": int(group.scenario_count or 0),
        "status": _json_safe(group.status),
        "stage": _json_safe(group.stage),
        "api_version": getattr(group, "api_version", None),
        "generation_strategy": getattr(group, "generation_strategy", None),
        "target_market": getattr(group, "target_market", None),
        "impact_catalog_version": getattr(
            group,
            "impact_catalog_version",
            None,
        ),
        "impact_catalog_checksum": getattr(
            group,
            "impact_catalog_checksum",
            None,
        ),
        "dimension_definitions": _json_safe(
            getattr(group, "dimension_definitions", None) or [],
        ),
    }


def _required_int(value: Any, *, field_name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise MIBaseError(
            ErrorCode.INVALID_REQUEST,
            detail=f"{field_name} is required for model parameter proposal persistence",
        ) from exc


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
