from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from apps.agents.model_parameter_agent.persistence.model_input.repository import (
    ModelInputRepository,
)
from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode


def _json_payload(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", by_alias=True)
    if isinstance(value, dict):
        return {str(key): _json_payload(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_payload(item) for item in value]
    return value


class ModelInputService:
    def load_context(self, scenario_id: int) -> dict[str, Any]:
        from apps.common.configs.database.sync_database.connection import get_sync_session

        session = get_sync_session()
        try:
            repository = ModelInputRepository(session=session)
            context = repository.fetch_context_by_scenario_id(scenario_id)
            if context is not None:
                mapping_rules, parameter_definitions = (
                    repository.fetch_parameter_mapping_resources()
                )
                context["parameter_mapping_resources"] = {
                    "mapping_rules": mapping_rules,
                    "parameter_definitions": parameter_definitions,
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
            return ModelInputRepository(session=session).fetch_parameter_mapping_resources()
        finally:
            session.close()

    def save_proposal_result(
        self,
        *,
        scenario_context: dict[str, Any],
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
        request_usr_id = _optional_int(scenario_group.get("request_usr_id"))
        payload = _json_payload(proposal_parameters)

        session = get_sync_session()
        try:
            proposal_id = ModelInputRepository(session=session).create_model_param_proposal(
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
