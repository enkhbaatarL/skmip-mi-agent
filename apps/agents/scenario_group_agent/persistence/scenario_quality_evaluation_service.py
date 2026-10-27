from __future__ import annotations

import contextlib

# ruff: noqa: CPY001
from decimal import Decimal
import hashlib
import json
from uuid import NAMESPACE_URL, uuid5

from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from apps.agents.scenario_group_agent.persistence.scenario_group_operation_service import (
    OperationAlreadyTerminalError,
    ScenarioGroupOperationService,
    _db_now,
    new_operation_id,
)
from apps.agents.scenario_group_agent.prompts.scenario_quality_evaluation import PROMPT_VERSION
from apps.common.configs.database.sync_database.connection import get_sync_session
from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode
from apps.persistence.event.repository import EventRepository
from apps.persistence.event.schema import EventPayload
from apps.persistence.scenario.repository import ScenarioRepository
from apps.persistence.scenario_group.models import MiScenarioGroupModel
from apps.persistence.scenario_group.repository import ScenarioGroupRepository
from apps.persistence.scenario_group_operation.models import MiScenarioGroupOperationModel
from apps.persistence.scenario_group_operation.repository import ScenarioGroupOperationRepository
from apps.persistence.scenario_group_operation.schema import TERMINAL_OPERATION_STATUSES
from apps.persistence.scenario_quality_evaluation.models import MiScenarioQualityEvaluationModel
from apps.persistence.scenario_quality_evaluation.repository import ScenarioQualityEvaluationRepository
from apps.persistence.scenario_quality_evaluation.schema import (
    QualityVerdict,
    ScenarioQualityEvaluationPayload,
    ScenarioQualityJudgment,
)


def automatic_request_id(source_operation_id: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"scenario-quality:{source_operation_id}"))


class ScenarioQualityEvaluationService:
    @staticmethod
    def build_snapshot(session: Session, group: MiScenarioGroupModel) -> dict[str, object]:
        group_repository = ScenarioGroupRepository(session=session)
        scenario_repository = ScenarioRepository(session=session)
        scenarios = scenario_repository.fetch_models_by_group_id(group.scenario_group_id)
        if not scenarios:
            raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="평가할 시나리오가 없습니다.")
        event_repository = EventRepository(session=session)
        events = []
        for relation in group_repository.fetch_group_events(group.scenario_group_id):
            payload = (
                event_repository.fetch_snapshot_by_id(relation.mi_event_snapshot_id)
                if relation.mi_event_snapshot_id is not None
                else event_repository.fetch_event_by_id(relation.mi_event_id)
            )
            if payload is None:
                raise MIBaseError(ErrorCode.INVALID_REQUEST, detail=f"Event 근거가 없습니다: {relation.mi_event_id}")
            events.append(
                {
                    "eventId": relation.mi_event_id,
                    "eventSnapshotId": relation.mi_event_snapshot_id,
                    "source": "generation_snapshot"
                    if relation.mi_event_snapshot_id is not None
                    else "live_at_evaluation",
                    "payload": EventPayload.model_validate(payload).model_dump(mode="json", by_alias=True),
                },
            )
        if not events:
            raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="평가할 Event 연결이 없습니다.")
        raw_group = group_repository.model_to_dict(group)
        group_fields = (
            "scenario_group_id",
            "title",
            "summary",
            "description",
            "dimension_definitions",
            "dimension_selected",
            "impact_catalog_version",
            "impact_catalog_checksum",
        )
        return jsonable_encoder(
            {
                "schemaVersion": 1,
                "group": {key: raw_group.get(key) for key in group_fields},
                "scenarios": [
                    {key: value for key, value in scenario_repository.model_to_dict(row).items() if key != "status"}
                    for row in scenarios
                ],
                "events": events,
            },
        )

    def prepare_in_session(
        self,
        session: Session,
        *,
        group: MiScenarioGroupModel,
        user_id: int,
        request_id: str,
        source_operation: MiScenarioGroupOperationModel | None = None,
    ) -> MiScenarioQualityEvaluationModel:
        repository = ScenarioQualityEvaluationRepository(session=session)
        existing = repository.fetch_by_request_id(request_id)
        if existing is not None:
            operation = ScenarioGroupOperationRepository(session=session).fetch_by_id(
                group.scenario_group_id,
                existing.operation_id,
            )
            if operation is None:
                raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="requestId는 다른 요청에 이미 사용되었습니다.")
            return existing
        if ScenarioGroupOperationRepository(session=session).fetch_active(group.scenario_group_id) is not None:
            raise MIBaseError(ErrorCode.SCENARIO_GROUP_OPERATION_CONFLICT, detail="실행 중인 그룹 작업이 있습니다.")
        snapshot = self.build_snapshot(session, group)
        digest = hashlib.sha256(
            json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"),
        ).hexdigest()
        operation_id = new_operation_id()
        ScenarioGroupOperationService().create_accepted_in_session(
            session,
            scenario_group_id=group.scenario_group_id,
            operation_id=operation_id,
            operation_type="quality_evaluation",
            engine_version=str(group.api_version or "v4"),
            source="automatic" if source_operation is not None else "api",
            user_id=user_id,
        )
        operation = ScenarioGroupOperationRepository(session=session).fetch_by_id(group.scenario_group_id, operation_id)
        snapshot_source = source_operation
        if snapshot_source is None or not snapshot_source.presentation_snapshot:
            snapshot_source = ScenarioGroupOperationRepository(session=session).fetch_latest_by_type(
                group.scenario_group_id,
                "create",
            )
        if snapshot_source is not None:
            operation.presentation_snapshot = dict(snapshot_source.presentation_snapshot or {})
        if source_operation is not None:
            snapshot = {**snapshot, "sourceOperationId": source_operation.operation_id}
        row = MiScenarioQualityEvaluationModel(
            operation_id=operation_id,
            request_id=request_id,
            input_snapshot=snapshot,
            input_hash=digest,
            prompt_version=PROMPT_VERSION,
            crt_usr_logn_id=str(user_id),
            mod_usr_logn_id=str(user_id),
        )
        repository.insert(row)
        return row

    def prepare_automatic_in_session(
        self, session: Session, source_operation: MiScenarioGroupOperationModel, *, changed: bool,
    ) -> None:
        if source_operation.operation_type != "validation" or source_operation.status != "succeeded":
            return
        group = ScenarioGroupRepository(session=session).fetch_by_id(
            source_operation.scenario_group_id, for_update=True,
        )
        if group is not None and str(group.api_version) == "v4":
            if not changed:
                latest = ScenarioGroupOperationRepository(session=session).fetch_latest_by_type(
                    group.scenario_group_id, "quality_evaluation",
                )
                if latest is not None and latest.status == "succeeded":
                    return
            self.prepare_in_session(
                session,
                group=group,
                user_id=int(source_operation.crt_usr_logn_id),
                request_id=automatic_request_id(source_operation.operation_id),
                source_operation=source_operation,
            )

    def prepare(self, group_id: int, user_id: int, request_id: str) -> tuple[ScenarioQualityEvaluationPayload, bool]:
        with get_sync_session() as session, session.begin():
            group = ScenarioGroupRepository(session=session).fetch_by_id(group_id, for_update=True)
            if group is None:
                raise MIBaseError(ErrorCode.ENTITY_NOT_FOUND, detail="Scenario group not found")
            if group.request_usr_id is not None and int(group.request_usr_id) != user_id:
                raise MIBaseError(ErrorCode.SCENARIO_GROUP_OWNERSHIP_CONFLICT)
            if group.stage not in {"scenario_validated", "signpost_created", "completed"}:
                raise MIBaseError(
                    ErrorCode.SCENARIO_GROUP_OPERATION_CONFLICT, detail="Validation 통과 후 평가하세요.",
                )
            existing = ScenarioQualityEvaluationRepository(session=session).fetch_by_request_id(request_id)
            row = self.prepare_in_session(session, group=group, user_id=user_id, request_id=request_id)
            return self._payload(session, group_id, row), existing is None

    @staticmethod
    def _payload(
        session: Session, group_id: int, row: MiScenarioQualityEvaluationModel,
    ) -> ScenarioQualityEvaluationPayload:
        operation = ScenarioGroupOperationRepository(session=session).fetch_by_id(group_id, row.operation_id)
        if operation is None or operation.operation_type != "quality_evaluation":
            raise MIBaseError(ErrorCode.ENTITY_NOT_FOUND, detail="Quality evaluation not found")
        return ScenarioQualityEvaluationPayload(
            **ScenarioGroupOperationService.operation_payload_from_model(operation).model_dump(),
            request_id=row.request_id,
            input_snapshot=row.input_snapshot,
            input_hash=row.input_hash,
            prompt_version=row.prompt_version,
            result=ScenarioQualityJudgment.model_validate(row.result_payload) if row.result_payload else None,
            verdict=row.verdict,
            average_score=float(row.average_score) if row.average_score is not None else None,
            llm_metadata=row.llm_metadata,
        )

    def get(self, group_id: int, operation_id: str) -> ScenarioQualityEvaluationPayload:
        with get_sync_session() as session:
            group = ScenarioGroupRepository(session=session).fetch_by_id(group_id)
            row = ScenarioQualityEvaluationRepository(session=session).fetch_by_operation_id(operation_id)
            if group is None or row is None or row.del_yn != "N":
                raise MIBaseError(ErrorCode.ENTITY_NOT_FOUND, detail="Quality evaluation not found")
            return self._payload(session, group_id, row)

    def automatic_operation_id(self, group_id: int, source_id: str) -> str | None:
        with get_sync_session() as session:
            row = ScenarioQualityEvaluationRepository(session=session).fetch_by_request_id(
                automatic_request_id(source_id),
            )
            if row is None:
                return None
            self._payload(session, group_id, row)
            return row.operation_id

    def complete(
        self,
        group_id: int,
        operation_id: str,
        *,
        result: ScenarioQualityJudgment,
        verdict: QualityVerdict,
        average_score: float,
        llm_metadata: dict[str, object],
    ) -> None:
        with get_sync_session() as session, session.begin():
            operation = ScenarioGroupOperationRepository(session=session).fetch_by_id(
                group_id, operation_id, for_update=True,
            )
            row = ScenarioQualityEvaluationRepository(session=session).fetch_by_operation_id(operation_id)
            if operation is None or row is None or operation.operation_type != "quality_evaluation":
                raise MIBaseError(ErrorCode.ENTITY_NOT_FOUND, detail="Quality evaluation not found")
            if operation.status in TERMINAL_OPERATION_STATUSES:
                raise OperationAlreadyTerminalError(operation_id, operation.status)
            row.result_payload = result.model_dump(mode="json", by_alias=True)
            row.verdict = verdict
            row.average_score = Decimal(str(average_score))
            row.llm_metadata = llm_metadata
            row.mod_usr_logn_id = operation.crt_usr_logn_id
            ScenarioGroupOperationRepository(session=session).append_event(
                operation,
                event_type="completed",
                phase="quality_evaluation",
                title="시나리오 평가를 완료했습니다",
                message_markdown=result.summary,
                payload={"verdict": verdict, "averageScore": average_score},
                now=_db_now(),
                status="succeeded",
            )
        self._notify(group_id, operation_id)

    def fail(
        self, group_id: int, operation_id: str, *, interrupted: bool = False, code: str = "EVALUATION_FAILED",
    ) -> None:
        status = "interrupted" if interrupted else "failed"
        with contextlib.suppress(OperationAlreadyTerminalError):
            ScenarioGroupOperationService().append_event(
                group_id,
                operation_id,
                event_type=status,
                phase="quality_evaluation",
                title="시나리오 평가가 중단되었습니다",
                message_markdown="평가 실행을 완료하지 못했습니다.",
                payload={"status": status},
                status=status,
                last_error={"code": code, "message": "Scenario quality evaluation did not complete"},
            )

    @staticmethod
    def _notify(group_id: int, operation_id: str) -> None:
        from apps.agents.scenario_group_agent.runtime import get_scenario_group_operation_event_hub

        operation = ScenarioGroupOperationService().get_operation(group_id, operation_id)
        get_scenario_group_operation_event_hub().publish(operation_id, operation.latest_sequence, terminal=True)
