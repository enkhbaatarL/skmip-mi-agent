from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import BaseModel

from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode
from apps.persistence.event.repository import EventRepository
from apps.persistence.model_parameter.repository import ModelParameterRepository
from apps.persistence.scenario.repository import ScenarioRepository
from apps.persistence.scenario_group.repository import ScenarioGroupRepository

CONFIRMABLE_PROPOSAL_STATUSES = {"PROPOSED", "CONFIRMED"}


def _json_payload(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", by_alias=True)
    if isinstance(value, dict):
        return {str(key): _json_payload(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_payload(item) for item in value]
    return value


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
                    event = event_repository.fetch_event_by_id(int(group.mi_event_id))
                    event_type = event_repository.fetch_event_type_by_l2_id(
                        int(group.event_type_l2_id),
                    )
                    dimension_template = scenario_repository.fetch_dimension_template(
                        int(group.event_type_l2_id),
                    )
                    mapping_rules, parameter_definitions = (
                        model_parameter_repository.fetch_parameter_mapping_resources()
                    )
                    context = {
                        "scenario": _scenario_to_context_dict(scenario),
                        "scenario_group": _group_to_context_dict(group),
                        "event": event or {},
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
        mi_event_id = _required_int(
            event.get("mi_event_id") or scenario_group.get("mi_event_id"),
            field_name="event.mi_event_id",
        )
        request_usr_id = _optional_int(user_id)
        payload = _json_payload(proposal_parameters)

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
        mi_event_id = _required_int(
            event.get("mi_event_id") or scenario_group.get("mi_event_id"),
            field_name="event.mi_event_id",
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

        payload = _json_payload(proposal_parameters)
        session = get_sync_session()
        try:
            ModelParameterRepository(session=session).complete_model_param_proposal(
                model_param_proposal_id=model_param_proposal_id,
                proposal_parameters=payload,
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
            ModelParameterRepository(session=session).fail_model_param_proposal(
                model_param_proposal_id=model_param_proposal_id,
                error_code=error_code,
                error_message=error_message,
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

        session = get_sync_session()
        try:
            ModelParameterRepository(session=session).update_model_param_callback_status(
                model_param_proposal_id=model_param_proposal_id,
                callback_status=callback_status,
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

        payload = _json_payload(confirmation_parameters)
        session = get_sync_session()
        try:
            repository = ModelParameterRepository(session=session)
            proposal = repository.fetch_model_param_proposal(model_param_proposal_id)
            if proposal is None:
                raise MIBaseError(
                    ErrorCode.ENTITY_NOT_FOUND,
                    detail=(
                        "Model parameter proposal not found: "
                        f"model_param_proposal_id={model_param_proposal_id}"
                    ),
                )
            status = str(proposal.get("status") or "")
            if status not in CONFIRMABLE_PROPOSAL_STATUSES:
                raise MIBaseError(
                    ErrorCode.INVALID_REQUEST,
                    detail=(
                        "Model parameter proposal must be PROPOSED or CONFIRMED before confirmation: "
                        f"model_param_proposal_id={model_param_proposal_id}, status={status}"
                    ),
                )
            repository.confirm_model_param_proposal(
                model_param_proposal_id=model_param_proposal_id,
                user_id=_optional_int(user_id),
                confirmation_parameters=payload,
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
        "mi_event_id": int(group.mi_event_id),
        "event_type_l2_id": int(group.event_type_l2_id),
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
