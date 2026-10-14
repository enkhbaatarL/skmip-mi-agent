from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
import secrets
import time
from typing import Any

from sqlalchemy.orm import Session

from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode
from apps.persistence.scenario.repository import ScenarioRepository
from apps.persistence.scenario_group.repository import ScenarioGroupRepository
from apps.persistence.scenario_group_operation.models import (
    MiScenarioGroupOperationEventModel,
    MiScenarioGroupOperationModel,
)
from apps.persistence.scenario_group_operation.repository import ScenarioGroupOperationRepository
from apps.persistence.scenario_group_operation.schema import (
    TERMINAL_EVENT_TYPES,
    TERMINAL_OPERATION_STATUSES,
    CallbackDeliveryStatus,
    OperationHeartbeatState,
    ScenarioGroupOperationEventPayload,
    ScenarioGroupOperationInternalPayload,
    ScenarioGroupOperationPayload,
    ValidationApplicationPayload,
    ValidationOperationResultPayload,
)
from apps.persistence.signpost.repository import SignpostRepository


_CROCKFORD_BASE32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_CALLBACK_EVENT_TITLES: dict[CallbackDeliveryStatus, str] = {
    "SUCCEEDED": "Callback을 전송했습니다",
    "FAILED": "Callback 전송에 실패했습니다",
    "SKIPPED": "Callback 전송을 건너뛰었습니다",
}


class OperationAlreadyTerminalError(RuntimeError):
    """Raised when a producer attempts to mutate an operation after it became terminal."""

    def __init__(self, operation_id: str, status: str) -> None:
        super().__init__(f"Operation is already terminal: operation_id={operation_id}, status={status}")
        self.operation_id = operation_id
        self.status = status


def new_operation_id() -> str:
    """Return a monotonic-friendly ULID-shaped identifier without a new dependency."""
    value = (int(time.time_ns() // 1_000_000) << 80) | secrets.randbits(80)
    chars = ["0"] * 26
    for index in range(25, -1, -1):
        chars[index] = _CROCKFORD_BASE32[value & 31]
        value >>= 5
    return "".join(chars)


def _db_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _api_datetime(value: datetime | None) -> datetime | None:
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=UTC)


class ScenarioGroupOperationService:
    def create_accepted_in_session(
        self,
        session: Session,
        *,
        scenario_group_id: int,
        operation_id: str,
        operation_type: str = "create",
        engine_version: str = "v4",
        source: str = "api",
        user_id: int,
    ) -> ScenarioGroupOperationPayload:
        repository = ScenarioGroupOperationRepository(session=session)
        now = _db_now()
        operation = repository.insert_operation(
            {
                "operation_id": operation_id,
                "scenario_group_id": scenario_group_id,
                "operation_type": operation_type,
                "engine_version": engine_version,
                "source": source,
                "status": "queued",
                "current_phase": None,
                "retry_summary": {},
                "presentation_snapshot": {},
                "snapshot_revision": 0,
                "latest_sequence": 0,
                "last_error": None,
                "started_at": None,
                "completed_at": None,
                "heartbeat_at": now,
                "crt_usr_logn_id": str(user_id),
                "mod_usr_logn_id": str(user_id),
            }
        )
        title = (
            "시나리오 그룹 생성을 접수했습니다" if operation_type == "create" else "Scenario Group 작업을 접수했습니다"
        )
        message = (
            "선택한 Event를 바탕으로 시나리오 그룹 생성을 시작합니다."
            if operation_type == "create"
            else f"{operation_type} 작업을 시작합니다."
        )
        repository.append_event(
            operation,
            event_type="accepted",
            phase=None,
            title=title,
            message_markdown=message,
            payload={
                "operationType": operation_type,
                "engineVersion": engine_version,
                "status": "queued",
            },
            now=now,
        )
        return self.operation_payload_from_model(operation)

    def create_validation_operation(
        self,
        *,
        scenario_group_id: int,
        user_id: int,
    ) -> ScenarioGroupOperationPayload:
        from apps.common.configs.database.sync_database.connection import get_sync_session

        session = get_sync_session()
        try:
            group_repository = ScenarioGroupRepository(session=session)
            group = group_repository.fetch_by_id(scenario_group_id, for_update=True)
            if group is None:
                raise MIBaseError(
                    ErrorCode.ENTITY_NOT_FOUND,
                    detail=f"Scenario group not found: {scenario_group_id}",
                )
            if group.request_usr_id is not None and int(group.request_usr_id) != user_id:
                raise MIBaseError(
                    ErrorCode.SCENARIO_GROUP_OWNERSHIP_CONFLICT,
                    detail=f"이미 사용자 {group.request_usr_id}가 점유하고 있습니다.",
                )
            operation_repository = ScenarioGroupOperationRepository(session=session)
            active = operation_repository.fetch_active(scenario_group_id)
            if active is not None:
                raise MIBaseError(
                    ErrorCode.SCENARIO_GROUP_OPERATION_CONFLICT,
                    detail=f"실행 중인 operation이 있습니다: {active.operation_id}",
                )
            group_repository.update_group(
                group,
                {
                    "stage": "scenario_created",
                    "mod_usr_logn_id": user_id,
                },
            )
            operation = self.create_accepted_in_session(
                session,
                scenario_group_id=scenario_group_id,
                operation_id=new_operation_id(),
                operation_type="validation",
                engine_version=str(group.api_version or "v1"),
                user_id=user_id,
            )
            session.commit()
            return operation
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def start_operation(self, scenario_group_id: int, operation_id: str, *, phase: str) -> None:
        self.append_event(
            scenario_group_id,
            operation_id,
            event_type="phase_started",
            phase=phase,
            title="작업을 시작했습니다",
            message_markdown=f"{phase} 단계를 실행합니다.",
            status="running",
        )

    def complete_validation(
        self,
        *,
        scenario_group_id: int,
        operation_id: str,
        result_payload: ValidationOperationResultPayload,
        user_id: int,
    ) -> dict[str, Any]:
        from apps.common.configs.database.sync_database.connection import get_sync_session

        session = get_sync_session()
        try:
            operation_repository = ScenarioGroupOperationRepository(session=session)
            group_repository = ScenarioGroupRepository(session=session)
            operation = operation_repository.fetch_by_id(scenario_group_id, operation_id, for_update=True)
            group = group_repository.fetch_by_id(scenario_group_id, for_update=True)
            if operation is None or operation.operation_type != "validation":
                raise MIBaseError(
                    ErrorCode.ENTITY_NOT_FOUND,
                    detail=f"Validation operation not found: {operation_id}",
                )
            if group is None:
                raise MIBaseError(ErrorCode.ENTITY_NOT_FOUND, detail=f"Scenario group not found: {scenario_group_id}")
            if operation.status in TERMINAL_OPERATION_STATUSES:
                raise OperationAlreadyTerminalError(operation_id, operation.status)
            if result_payload.validation_result.can_proceed:
                from apps.agents.scenario_group_agent.flows.validate_scenarios.v4_validation import (
                    dimension_definition_fingerprint,
                    scenario_fingerprint,
                )
                from apps.agents.scenario_group_agent.persistence.scenario_service import ScenarioService
                from apps.persistence.enums import ScenarioStatus

                scenario_repository = ScenarioRepository(session=session)
                signpost_repository = SignpostRepository(session=session)
                scenarios = scenario_repository.fetch_models_by_group_id(scenario_group_id, for_update=True)
                scenario_dicts = [scenario_repository.model_to_dict(item) for item in scenarios]
                current_scenario_fingerprint = scenario_fingerprint(scenario_dicts)
                current_definition_fingerprint = dimension_definition_fingerprint(
                    list(group.dimension_definitions or [])
                )
                base_definition_fingerprint = (
                    result_payload.base_dimension_definition_fingerprint
                    or result_payload.dimension_definition_fingerprint
                )
                if (
                    current_scenario_fingerprint != result_payload.base_scenario_fingerprint
                    or current_definition_fingerprint != base_definition_fingerprint
                ):
                    raise MIBaseError(
                        ErrorCode.SCENARIO_VALIDATION_STALE,
                        detail="Validation 실행 중 Scenario 또는 정식 Dimension definition이 변경되었습니다.",
                    )

                formal_definitions = [item for item in (group.dimension_definitions or []) if isinstance(item, dict)]
                formal_by_id = {
                    str(item.get("dimension_id") or item.get("dimensionId") or ""): item for item in formal_definitions
                }
                current_selected = [str(item) for item in (getattr(group, "dimension_selected", None) or [])]
                requested_ids = list(result_payload.requested_dimension_ids or current_selected or formal_by_id)
                current_selected_set = set(current_selected)
                if (
                    current_selected
                    and [item for item in requested_ids if item in current_selected_set] != current_selected
                ):
                    raise MIBaseError(
                        ErrorCode.SCENARIO_VALIDATION_STALE,
                        detail="Validation 실행 중 Dimension header 순서가 변경되었습니다.",
                    )
                promoted_ids = [item for item in requested_ids if item not in formal_by_id]
                if promoted_ids != list(result_payload.promoted_dimension_ids):
                    raise MIBaseError(
                        ErrorCode.SCENARIO_DIMENSION_CANDIDATE_STALE,
                        detail="Validation candidate header가 현재 정식 Dimension과 일치하지 않습니다.",
                    )

                candidate_by_id: dict[str, dict[str, Any]] = {}
                if promoted_ids:
                    from apps.agents.scenario_group_agent.persistence.scenario_group_service import (
                        ScenarioGroupService,
                    )

                    diagnostics = dict(group.generation_diagnostics or {})
                    generation = diagnostics.get("additional_dimension_generation") or diagnostics.get(
                        "additionalDimensionGeneration",
                        {},
                    )
                    if (
                        generation.get("status") != "ready"
                        or generation.get("source_fingerprint", generation.get("sourceFingerprint"))
                        != result_payload.candidate_source_fingerprint
                    ):
                        raise MIBaseError(
                            ErrorCode.SCENARIO_DIMENSION_CANDIDATE_STALE,
                            detail="Additional Dimension source fingerprint가 변경되었습니다.",
                        )
                    _unused_uncertainties, current_candidate_fingerprint = (
                        ScenarioGroupService._additional_dimension_source(group)
                    )
                    if current_candidate_fingerprint != result_payload.candidate_source_fingerprint:
                        raise MIBaseError(
                            ErrorCode.SCENARIO_DIMENSION_CANDIDATE_STALE,
                            detail="Additional Dimension active source pool이 변경되었습니다.",
                        )
                    candidates = diagnostics.get("additional_dimension_candidates") or diagnostics.get(
                        "additionalDimensionCandidates",
                        [],
                    )
                    candidate_by_id = {
                        str(item.get("dimension_id") or item.get("dimensionId")): item
                        for item in candidates
                        if isinstance(item, dict)
                    }
                    missing_candidates = set(promoted_ids) - set(candidate_by_id)
                    if missing_candidates:
                        raise MIBaseError(
                            ErrorCode.SCENARIO_DIMENSION_CANDIDATE_STALE,
                            detail=f"Additional Dimension 후보가 없습니다: {sorted(missing_candidates)}",
                        )
                    reserved_sources = {
                        str(source_id)
                        for definition in (group.dimension_definitions or [])
                        if isinstance(definition, dict)
                        for source_id in (
                            definition.get("source_uncertainty_ids") or definition.get("sourceUncertaintyIds") or []
                        )
                    }
                    for candidate_id in promoted_ids:
                        candidate_sources = {
                            str(item)
                            for item in (
                                candidate_by_id[candidate_id].get("source_uncertainty_ids")
                                or candidate_by_id[candidate_id].get("sourceUncertaintyIds")
                                or []
                            )
                        }
                        if reserved_sources.intersection(candidate_sources):
                            raise MIBaseError(
                                ErrorCode.SCENARIO_DIMENSION_CANDIDATE_STALE,
                                detail=f"Additional Dimension source가 이미 사용 중입니다: {candidate_id}",
                            )
                        reserved_sources.update(candidate_sources)

                definition_by_id = {**candidate_by_id, **formal_by_id}
                missing_definitions = [item for item in requested_ids if item not in definition_by_id]
                if missing_definitions:
                    raise MIBaseError(
                        ErrorCode.SCENARIO_DIMENSION_CANDIDATE_STALE,
                        detail=f"Validation Dimension definition이 없습니다: {missing_definitions}",
                    )
                target_definitions = [definition_by_id[item] for item in requested_ids]
                if (
                    dimension_definition_fingerprint(target_definitions)
                    != result_payload.dimension_definition_fingerprint
                ):
                    raise MIBaseError(
                        ErrorCode.SCENARIO_DIMENSION_CANDIDATE_STALE,
                        detail="Validation requested Dimension definition이 변경되었습니다.",
                    )
                result_payload.requested_dimension_ids = requested_ids
                result_payload.requested_dimension_definitions = target_definitions
                result_payload.promoted_dimension_ids = promoted_ids

                updated_diagnostics: dict[str, Any] | None = None
                if promoted_ids:
                    used_sources = {
                        str(source_id)
                        for definition in target_definitions
                        for source_id in (
                            definition.get("source_uncertainty_ids")
                            or definition.get("sourceUncertaintyIds")
                            or []
                        )
                    }
                    remaining_candidates = [
                        item
                        for item in candidates
                        if isinstance(item, dict)
                        and str(item.get("dimension_id") or item.get("dimensionId") or "") not in promoted_ids
                        and not used_sources.intersection(
                            {
                                str(source_id)
                                for source_id in (
                                    item.get("source_uncertainty_ids")
                                    or item.get("sourceUncertaintyIds")
                                    or []
                                )
                            },
                        )
                    ]
                    remaining_uncertainties, remaining_fingerprint = (
                        ScenarioGroupService._additional_dimension_source_from_payload(
                            diagnostics=diagnostics,
                            definitions=target_definitions,
                        )
                    )
                    generation = dict(generation)
                    generation.pop("sourceFingerprint", None)
                    generation.pop("sourceUncertaintyIds", None)
                    generation["source_fingerprint"] = remaining_fingerprint
                    generation["source_uncertainty_ids"] = [
                        str(
                            ScenarioGroupService._diagnostic_field(
                                item,
                                "uncertainty_id",
                                "uncertaintyId",
                            ),
                        )
                        for item in remaining_uncertainties
                    ]
                    ScenarioGroupService._store_additional_generation(diagnostics, generation)
                    diagnostics.pop("additionalDimensionCandidates", None)
                    diagnostics["additional_dimension_candidates"] = remaining_candidates
                    updated_diagnostics = diagnostics

                change_set = result_payload.scenario_change_set
                new_id_map: dict[str, int] = {}
                if result_payload.mode == "changed" and change_set is not None:
                    scenarios_by_id = {int(item.scenario_id): item for item in scenarios}
                    existing_upsert_ids = {
                        int(item.scenario_id) for item in change_set.upserts if item.scenario_id is not None
                    }
                    if not existing_upsert_ids.issubset(scenarios_by_id) or not set(
                        change_set.delete_scenario_ids
                    ).issubset(scenarios_by_id):
                        raise MIBaseError(
                            ErrorCode.SCENARIO_VALIDATION_STALE,
                            detail="Validation Change Set의 Scenario ID가 현재 그룹과 일치하지 않습니다.",
                        )
                    updated_ids: list[int] = []
                    for upsert in change_set.upserts:
                        fields = upsert.generated_fields
                        payload = {
                            "title": upsert.title,
                            "narrative": fields.narrative,
                            "dimension_values": upsert.dimension_values,
                            "probability_score": Decimal(str(fields.probability_score)),
                            "probability_delta": Decimal("0"),
                            "display_order": upsert.display_order,
                            "baseline_yn": "N",
                            "global_pressure_band": fields.pressure_band,
                            "scenario_role": None,
                            "global_pressure_rationale": fields.pressure_rationale,
                            "related_markets": fields.related_markets,
                            "status": ScenarioStatus.CREATING.value,
                            "mod_usr_logn_id": user_id,
                        }
                        if upsert.scenario_id is None:
                            inserted_id = scenario_repository.insert_scenario(
                                {
                                    **payload,
                                    "scenario_group_id": scenario_group_id,
                                    "crt_usr_logn_id": user_id,
                                }
                            )
                            new_id_map[upsert.client_row_key] = inserted_id
                        else:
                            scenario_id = int(upsert.scenario_id)
                            scenario_repository.update_from_payload(scenarios_by_id[scenario_id], payload)
                            updated_ids.append(scenario_id)
                    scenario_repository.soft_delete_by_ids(change_set.delete_scenario_ids, user_id=user_id)
                    signpost_repository.soft_delete_by_scenario_ids(
                        [*updated_ids, *change_set.delete_scenario_ids],
                        user_id=user_id,
                    )

                active_scenarios = scenario_repository.fetch_models_by_group_id(scenario_group_id)
                ScenarioService()._apply_v4_baseline_and_roles(
                    active_scenarios,
                    target_definitions,
                    user_id=user_id,
                )
                group_update = {
                    "dimension_definitions": target_definitions,
                    "dimension_selected": requested_ids,
                    "scenario_count": len(active_scenarios),
                    "mod_usr_logn_id": user_id,
                }
                if updated_diagnostics is not None:
                    group_update["generation_diagnostics"] = updated_diagnostics
                group_repository.update_group(group, group_update)
                session.flush()
                for scenario in active_scenarios:
                    session.refresh(scenario)
                applied_fingerprint = scenario_fingerprint(
                    [scenario_repository.model_to_dict(item) for item in active_scenarios],
                )
                result_payload.application = ValidationApplicationPayload(
                    applied_at=datetime.now(UTC),
                    applied_scenario_fingerprint=applied_fingerprint,
                    new_scenario_id_map=new_id_map,
                )

            operation.result_payload = result_payload.model_dump(mode="json", by_alias=True)
            next_stage = "scenario_validated" if result_payload.validation_result.can_proceed else "scenario_created"
            group_repository.update_group(
                group,
                {
                    "stage": next_stage,
                    "status": "creating",
                    "mod_usr_logn_id": user_id,
                },
            )
            operation_repository.append_event(
                operation,
                event_type="completed",
                phase="validation",
                title="Scenario Validation을 완료했습니다",
                message_markdown=result_payload.validation_result.reason_markdown,
                payload={
                    "verdict": result_payload.validation_result.verdict,
                    "isValid": result_payload.validation_result.is_valid,
                    "canProceed": result_payload.validation_result.can_proceed,
                },
                now=_db_now(),
                status="succeeded",
            )
            session.commit()
            return group_repository.model_to_dict(group)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def fail_validation(
        self,
        *,
        scenario_group_id: int,
        operation_id: str,
        user_id: int,
        error: Exception,
    ) -> None:
        from apps.common.configs.database.sync_database.connection import get_sync_session

        session = get_sync_session()
        try:
            operation_repository = ScenarioGroupOperationRepository(session=session)
            group_repository = ScenarioGroupRepository(session=session)
            operation = operation_repository.fetch_by_id(scenario_group_id, operation_id, for_update=True)
            group = group_repository.fetch_by_id(scenario_group_id, for_update=True)
            if operation is None or group is None or operation.status in TERMINAL_OPERATION_STATUSES:
                return
            group_repository.update_group(
                group,
                {
                    "stage": "scenario_created",
                    "mod_usr_logn_id": user_id,
                },
            )
            operation_repository.append_event(
                operation,
                event_type="failed",
                phase="validation",
                title="Scenario Validation에 실패했습니다",
                message_markdown=str(error),
                payload={"status": "failed"},
                now=_db_now(),
                status="failed",
                last_error={"message": str(error)},
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def complete_operation(
        self,
        *,
        scenario_group_id: int,
        operation_id: str,
        phase: str,
        message_markdown: str,
    ) -> None:
        self.append_event(
            scenario_group_id,
            operation_id,
            event_type="completed",
            phase=phase,
            title="작업을 완료했습니다",
            message_markdown=message_markdown,
            payload={"status": "succeeded"},
            status="succeeded",
        )

    def fail_signpost(
        self,
        *,
        scenario_group_id: int,
        operation_id: str,
        user_id: int,
        error: Exception,
    ) -> None:
        from apps.common.configs.database.sync_database.connection import get_sync_session

        session = get_sync_session()
        try:
            operation_repository = ScenarioGroupOperationRepository(session=session)
            group_repository = ScenarioGroupRepository(session=session)
            operation = operation_repository.fetch_by_id(scenario_group_id, operation_id, for_update=True)
            group = group_repository.fetch_by_id(scenario_group_id, for_update=True)
            if operation is None or group is None or operation.status in TERMINAL_OPERATION_STATUSES:
                return
            group_repository.update_group(
                group,
                {
                    "stage": "scenario_validated",
                    "mod_usr_logn_id": user_id,
                },
            )
            operation_repository.append_event(
                operation,
                event_type="failed",
                phase="signpost",
                title="Signpost 생성에 실패했습니다",
                message_markdown=str(error),
                payload={"status": "failed"},
                now=_db_now(),
                status="failed",
                last_error={"message": str(error)},
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def append_event(
        self,
        scenario_group_id: int,
        operation_id: str,
        *,
        event_type: str,
        title: str,
        message_markdown: str,
        phase: str | None = None,
        payload: dict[str, Any] | None = None,
        status: str | None = None,
        presentation_snapshot: dict[str, Any] | None = None,
        last_error: dict[str, Any] | None = None,
        retry_summary: dict[str, Any] | None = None,
        mlflow_trace_id: str | None = None,
    ) -> ScenarioGroupOperationEventPayload:
        from apps.common.configs.database.sync_database.connection import get_sync_session

        session = get_sync_session()
        try:
            repository = ScenarioGroupOperationRepository(session=session)
            operation = repository.fetch_by_id(scenario_group_id, operation_id, for_update=True)
            if operation is None:
                raise MIBaseError(
                    ErrorCode.ENTITY_NOT_FOUND,
                    detail=f"Operation not found: scenarioGroupId={scenario_group_id}, operationId={operation_id}",
                )
            if operation.status in TERMINAL_OPERATION_STATUSES:
                if status == operation.status:
                    last_event = repository.fetch_last_event(operation_id)
                    if last_event is not None:
                        return self._event_payload(last_event)
                raise OperationAlreadyTerminalError(operation_id, operation.status)
            event = repository.append_event(
                operation,
                event_type=event_type,
                phase=phase,
                title=title,
                message_markdown=message_markdown,
                payload=payload or {},
                now=_db_now(),
                status=status,
                presentation_snapshot=presentation_snapshot,
                last_error=last_error,
                retry_summary=retry_summary,
                mlflow_trace_id=mlflow_trace_id,
            )
            session.commit()
            event_payload = self._event_payload(event)
            from apps.agents.scenario_group_agent.runtime import get_scenario_group_operation_event_hub

            get_scenario_group_operation_event_hub().publish(
                operation_id,
                event_payload.sequence,
                terminal=event_payload.event_type in TERMINAL_EVENT_TYPES,
            )
            return event_payload
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def record_callback_delivery(
        self,
        scenario_group_id: int,
        operation_id: str,
        *,
        callback_status: CallbackDeliveryStatus,
        result: str,
        error: Exception | None = None,
    ) -> None:
        """callback 전송 결과를 operation 이력에 남긴다.

        callback은 operation이 terminal이 된 뒤 전송되므로 terminal 여부와 무관하게 기록하며,
        operation status·last_error는 바꾸지 않는다. SSE stream은 terminal event에서 종료되므로 publish하지 않는다.
        """
        from apps.common.configs.database.sync_database.connection import get_sync_session

        payload: dict[str, Any] = {"callbackStatus": callback_status, "result": result}
        if isinstance(error, MIBaseError):
            payload.update(
                {
                    "stage": error.context.get("stage"),
                    "url": error.context.get("url"),
                    "statusCode": error.context.get("status_code"),
                },
            )
        if error is not None:
            payload["error"] = repr(error.__cause__ or error)

        session = get_sync_session()
        try:
            repository = ScenarioGroupOperationRepository(session=session)
            operation = repository.fetch_by_id(scenario_group_id, operation_id, for_update=True)
            if operation is None:
                raise MIBaseError(
                    ErrorCode.ENTITY_NOT_FOUND,
                    detail=f"Operation not found: scenarioGroupId={scenario_group_id}, operationId={operation_id}",
                )
            repository.append_event(
                operation,
                event_type=f"callback_{callback_status.lower()}",
                phase=None,
                title=_CALLBACK_EVENT_TITLES[callback_status],
                message_markdown=str(error) if error is not None else "",
                payload=payload,
                now=_db_now(),
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def touch_active_heartbeat(self, scenario_group_id: int, operation_id: str) -> OperationHeartbeatState:
        from apps.common.configs.database.sync_database.connection import get_sync_session

        session = get_sync_session()
        try:
            status = ScenarioGroupOperationRepository(session=session).touch_active_heartbeat(
                scenario_group_id,
                operation_id,
                now=_db_now(),
            )
            session.commit()
            if status in {"queued", "running", "succeeded", "failed", "interrupted"}:
                return status
            return "missing"
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def interrupt_stale_operations(
        self,
        heartbeat_cutoff: datetime,
        *,
        limit: int = 100,
    ) -> list[ScenarioGroupOperationEventPayload]:
        from apps.common.configs.database.sync_database.connection import get_sync_session

        session = get_sync_session()
        event_payloads: list[ScenarioGroupOperationEventPayload] = []
        try:
            repository = ScenarioGroupOperationRepository(session=session)
            now = _db_now()
            interrupted_message = " ".join(
                (
                    "서버 재시작 후 heartbeat가 만료되어 작업을 중단 처리했습니다.",
                    "자동 재개는 지원하지 않습니다.",
                )
            )
            for operation in repository.fetch_stale_active(heartbeat_cutoff, limit=limit):
                effective_heartbeat = operation.heartbeat_at or operation.crt_dtm
                if operation.status not in {"queued", "running"} or effective_heartbeat > heartbeat_cutoff:
                    continue
                event = repository.append_event(
                    operation,
                    event_type="interrupted",
                    phase=operation.current_phase,
                    title="작업 응답이 없어 중단 처리되었습니다",
                    message_markdown=interrupted_message,
                    payload={"status": "interrupted", "reason": "stale_heartbeat"},
                    now=now,
                    status="interrupted",
                    last_error={
                        "code": "STALE_HEARTBEAT",
                        "message": "Operation heartbeat expired before recovery",
                    },
                )
                event_payloads.append(self._event_payload(event))
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

        if event_payloads:
            from apps.agents.scenario_group_agent.runtime import get_scenario_group_operation_event_hub

            event_hub = get_scenario_group_operation_event_hub()
            for event_payload in event_payloads:
                event_hub.publish(event_payload.operation_id, event_payload.sequence, terminal=True)
        return event_payloads

    def get_operation(self, scenario_group_id: int, operation_id: str) -> ScenarioGroupOperationPayload:
        from apps.common.configs.database.sync_database.connection import get_sync_session

        session = get_sync_session()
        try:
            operation = ScenarioGroupOperationRepository(session=session).fetch_by_id(
                scenario_group_id,
                operation_id,
            )
            if operation is None:
                raise MIBaseError(
                    ErrorCode.ENTITY_NOT_FOUND,
                    detail=f"Operation not found: scenarioGroupId={scenario_group_id}, operationId={operation_id}",
                )
            return self.operation_payload_from_model(operation)
        finally:
            session.close()

    def get_latest(self, scenario_group_id: int) -> ScenarioGroupOperationPayload | None:
        from apps.common.configs.database.sync_database.connection import get_sync_session

        session = get_sync_session()
        try:
            operation = ScenarioGroupOperationRepository(session=session).fetch_latest(scenario_group_id)
            return self.operation_payload_from_model(operation) if operation is not None else None
        finally:
            session.close()

    def get_latest_internal_by_type(
        self,
        scenario_group_id: int,
        operation_type: str,
    ) -> ScenarioGroupOperationInternalPayload | None:
        from apps.common.configs.database.sync_database.connection import get_sync_session

        session = get_sync_session()
        try:
            operation = ScenarioGroupOperationRepository(session=session).fetch_latest_by_type(
                scenario_group_id,
                operation_type,
            )
            if operation is None:
                return None
            result_payload: ValidationOperationResultPayload | dict[str, Any] | None = operation.result_payload
            if operation_type == "validation" and isinstance(result_payload, dict):
                result_payload = ValidationOperationResultPayload.model_validate(result_payload)
            return ScenarioGroupOperationInternalPayload(
                operation_id=operation.operation_id,
                scenario_group_id=int(operation.scenario_group_id),
                operation_type=operation.operation_type,
                status=operation.status,
                result_payload=result_payload,
            )
        finally:
            session.close()

    def get_active(self, scenario_group_id: int) -> ScenarioGroupOperationPayload | None:
        from apps.common.configs.database.sync_database.connection import get_sync_session

        session = get_sync_session()
        try:
            operation = ScenarioGroupOperationRepository(session=session).fetch_active(scenario_group_id)
            return self.operation_payload_from_model(operation) if operation is not None else None
        finally:
            session.close()

    def get_last_event(self, operation_id: str) -> ScenarioGroupOperationEventPayload | None:
        from apps.common.configs.database.sync_database.connection import get_sync_session

        session = get_sync_session()
        try:
            event = ScenarioGroupOperationRepository(session=session).fetch_last_event(operation_id)
            return self._event_payload(event) if event is not None else None
        finally:
            session.close()

    def list_events_after(
        self,
        scenario_group_id: int,
        operation_id: str,
        sequence: int,
        *,
        limit: int = 100,
    ) -> list[ScenarioGroupOperationEventPayload]:
        from apps.common.configs.database.sync_database.connection import get_sync_session

        session = get_sync_session()
        try:
            repository = ScenarioGroupOperationRepository(session=session)
            if repository.fetch_by_id(scenario_group_id, operation_id) is None:
                raise MIBaseError(
                    ErrorCode.ENTITY_NOT_FOUND,
                    detail=f"Operation not found: scenarioGroupId={scenario_group_id}, operationId={operation_id}",
                )
            return [
                self._event_payload(event)
                for event in repository.list_events_after(operation_id, sequence, limit=limit)
            ]
        finally:
            session.close()

    @staticmethod
    def operation_payload_from_model(operation: MiScenarioGroupOperationModel) -> ScenarioGroupOperationPayload:
        return ScenarioGroupOperationPayload(
            operation_id=operation.operation_id,
            scenario_group_id=int(operation.scenario_group_id),
            operation_type=operation.operation_type,
            engine_version=operation.engine_version,
            source=operation.source,
            status=operation.status,
            current_phase=operation.current_phase,
            retry_summary=operation.retry_summary or {},
            presentation_snapshot=operation.presentation_snapshot or {},
            snapshot_revision=int(operation.snapshot_revision or 0),
            latest_sequence=int(operation.latest_sequence or 0),
            last_error=operation.last_error,
            mlflow_trace_id=operation.mlflow_trace_id,
            started_at=_api_datetime(operation.started_at),
            completed_at=_api_datetime(operation.completed_at),
            heartbeat_at=_api_datetime(operation.heartbeat_at),
            created_at=_api_datetime(operation.crt_dtm),
            updated_at=_api_datetime(operation.mod_dtm),
        )

    @staticmethod
    def _event_payload(event: MiScenarioGroupOperationEventModel) -> ScenarioGroupOperationEventPayload:
        return ScenarioGroupOperationEventPayload(
            operation_id=event.operation_id,
            scenario_group_id=int(event.scenario_group_id),
            sequence=int(event.sequence),
            event_type=event.event_type,
            phase=event.phase,
            title=event.title,
            message_markdown=event.message_markdown,
            payload=event.payload or {},
            snapshot_revision=int(event.snapshot_revision or 0),
            mlflow_trace_id=event.mlflow_trace_id,
            created_at=_api_datetime(event.crt_dtm),
        )
