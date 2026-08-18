from __future__ import annotations

from datetime import UTC, datetime
import secrets
import time
from typing import Any

from sqlalchemy.orm import Session

from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode
from apps.persistence.scenario_group.repository import ScenarioGroupRepository
from apps.persistence.scenario_group_operation.models import (
    MiScenarioGroupOperationEventModel,
    MiScenarioGroupOperationModel,
)
from apps.persistence.scenario_group_operation.repository import ScenarioGroupOperationRepository
from apps.persistence.scenario_group_operation.schema import (
    TERMINAL_EVENT_TYPES,
    TERMINAL_OPERATION_STATUSES,
    ScenarioGroupOperationEventPayload,
    ScenarioGroupOperationInternalPayload,
    ScenarioGroupOperationPayload,
    ValidationOperationResultPayload,
)


_CROCKFORD_BASE32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


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

    def touch_active_heartbeat(self, scenario_group_id: int, operation_id: str) -> bool:
        from apps.common.configs.database.sync_database.connection import get_sync_session

        session = get_sync_session()
        try:
            touched = ScenarioGroupOperationRepository(session=session).touch_active_heartbeat(
                scenario_group_id,
                operation_id,
                now=_db_now(),
            )
            session.commit()
            return touched
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
