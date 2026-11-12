from __future__ import annotations

# ruff: noqa: CPY001
from typing import Any

from apps.agents.scenario_group_agent.flows.evaluate_scenarios.repair import build_repaired_snapshot, snapshot_hash
from apps.agents.scenario_group_agent.flows.validate_scenarios.v4_validation import (
    dimension_definition_fingerprint,
    scenario_fingerprint,
)
from apps.agents.scenario_group_agent.persistence.scenario_group_operation_service import (
    OperationAlreadyTerminalError,
    ScenarioGroupOperationService,
    _db_now,
    new_operation_id,
)
from apps.agents.scenario_group_agent.persistence.scenario_quality_evaluation_service import (
    ScenarioQualityEvaluationService,
)
from apps.agents.scenario_group_agent.prompts.scenario_quality_repair import (
    REPAIR_PROMPT_VERSION,
    QualityRepairPlan,
    QualityRepairReview,
)
from apps.common.configs.database.sync_database.connection import get_sync_session
from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode
from apps.persistence.scenario.repository import ScenarioRepository
from apps.persistence.scenario_group.repository import ScenarioGroupRepository
from apps.persistence.scenario_group_operation.repository import ScenarioGroupOperationRepository
from apps.persistence.scenario_group_operation.schema import (
    TERMINAL_OPERATION_STATUSES,
    ValidationApplicationPayload,
    ValidationOperationResultPayload,
    ValidationResultPayload,
)
from apps.persistence.scenario_quality_evaluation.repository import ScenarioQualityEvaluationRepository
from apps.persistence.scenario_quality_evaluation.schema import ScenarioQualityJudgment
from apps.persistence.signpost.repository import SignpostRepository


class ScenarioQualityRepairService:
    def claim(self, group_id: int, operation_id: str) -> dict[str, Any] | None:
        with get_sync_session() as session, session.begin():
            group = ScenarioGroupRepository(session=session).fetch_by_id(group_id, for_update=True)
            operation = ScenarioGroupOperationRepository(session=session).fetch_by_id(
                group_id,
                operation_id,
                for_update=True,
            )
            if operation is None or operation.status in TERMINAL_OPERATION_STATUSES:
                return None
            metadata = dict((operation.retry_summary or {}).get("qualityRepair") or {})
            if metadata.get("attempt") != 1 or metadata.get("state") != "pending":
                return None
            if group is None or group.stage != "scenario_validated":
                raise MIBaseError(
                    ErrorCode.SCENARIO_GROUP_OPERATION_CONFLICT,
                    detail="Repair requires pre-Signpost stage",
                )
            parent = ScenarioQualityEvaluationRepository(session=session).fetch_by_operation_id(
                metadata["parentEvaluationId"],
            )
            current = ScenarioQualityEvaluationService.build_snapshot(session, group)
            if parent is None or snapshot_hash(current) != parent.input_hash:
                raise MIBaseError(ErrorCode.SCENARIO_VALIDATION_STALE, detail="Evaluation input changed before repair")
            diagnostics = dict(group.generation_diagnostics or {})
            operation.retry_summary = {
                "qualityRepair": {
                    **metadata,
                    "state": "generating",
                    "diagnosticsHash": snapshot_hash({"diagnostics": diagnostics}),
                },
            }
            return {
                "inputSnapshot": current,
                "judgment": parent.result_payload,
                "diagnostics": diagnostics,
            }

    def record_planning(self, group_id: int, operation_id: str, planning: dict[str, Any]) -> None:
        with get_sync_session() as session, session.begin():
            operation = ScenarioGroupOperationRepository(session=session).fetch_by_id(
                group_id,
                operation_id,
                for_update=True,
            )
            if operation is None:
                raise MIBaseError(ErrorCode.ENTITY_NOT_FOUND)
            if operation.status in TERMINAL_OPERATION_STATUSES:
                raise OperationAlreadyTerminalError(operation_id, operation.status)
            metadata = dict((operation.retry_summary or {}).get("qualityRepair") or {})
            if metadata.get("state") != "generating":
                raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="Repair planning requires a claimed operation")
            operation.retry_summary = {
                **(operation.retry_summary or {}),
                "qualityRepair": {
                    **metadata,
                    "planning": planning,
                },
            }

    def apply(
        self,
        group_id: int,
        operation_id: str,
        plan: QualityRepairPlan,
        review: QualityRepairReview,
        *,
        llm_metadata: dict[str, Any],
    ) -> None:
        if not review.can_proceed:
            raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="Repair validation blocked: " + review.reason)
        with get_sync_session() as session, session.begin():
            groups = ScenarioGroupRepository(session=session)
            operations = ScenarioGroupOperationRepository(session=session)
            evaluations = ScenarioQualityEvaluationRepository(session=session)
            group = groups.fetch_by_id(group_id, for_update=True)
            operation = operations.fetch_by_id(group_id, operation_id, for_update=True)
            if operation is None:
                raise MIBaseError(ErrorCode.ENTITY_NOT_FOUND)
            if operation.status in TERMINAL_OPERATION_STATUSES:
                raise OperationAlreadyTerminalError(operation_id, operation.status)
            metadata = dict((operation.retry_summary or {}).get("qualityRepair") or {})
            if metadata.get("attempt") != 1 or metadata.get("state") != "generating":
                raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="Repair already applied or not claimed")
            if group is None or group.stage != "scenario_validated":
                raise MIBaseError(ErrorCode.SCENARIO_GROUP_OPERATION_CONFLICT)
            parent = evaluations.fetch_by_operation_id(metadata["parentEvaluationId"])
            before = ScenarioQualityEvaluationService.build_snapshot(session, group)
            policy_hash = snapshot_hash({"diagnostics": dict(group.generation_diagnostics or {})})
            if (
                parent is None
                or snapshot_hash(before) != parent.input_hash
                or metadata.get("diagnosticsHash") != policy_hash
            ):
                raise MIBaseError(ErrorCode.SCENARIO_VALIDATION_STALE, detail="Evaluation input or policy changed")
            candidate, checks = build_repaired_snapshot(
                before,
                ScenarioQualityJudgment.model_validate(parent.result_payload),
                plan,
                dict(group.generation_diagnostics or {}),
            )
            user_id = int(operation.crt_usr_logn_id)
            scenarios = ScenarioRepository(session=session)
            models = scenarios.fetch_models_by_group_id(group_id)
            before_fingerprint = scenario_fingerprint([scenarios.model_to_dict(model) for model in models])
            by_id = {row["scenario_id"]: row for row in candidate["scenarios"]}
            for model in models:
                row = by_id[model.scenario_id]
                fields = (
                    "title",
                    "narrative",
                    "global_pressure_rationale",
                    "dimension_values",
                    "global_pressure_band",
                    "baseline_yn",
                    "scenario_role",
                )
                changes = {key: row[key] for key in fields if getattr(model, key) != row[key]}
                if changes:
                    scenarios.update_from_payload(model, {**changes, "mod_usr_logn_id": str(user_id)})
            group_fields = ("title", "summary", "description", "dimension_definitions")
            groups.update_group(
                group,
                {
                    **{key: candidate["group"][key] for key in group_fields},
                    "mod_usr_logn_id": str(user_id),
                },
            )
            SignpostRepository(session=session).soft_delete_by_scenario_ids(
                list(by_id),
                user_id=user_id,
            )
            session.flush()
            for model in models:
                session.refresh(model)
            session.refresh(group)
            after = ScenarioQualityEvaluationService.build_snapshot(session, group)
            validation_id = new_operation_id()
            ScenarioGroupOperationService().create_accepted_in_session(
                session,
                scenario_group_id=group_id,
                operation_id=validation_id,
                operation_type="validation",
                engine_version="v4",
                source="automatic",
                user_id=user_id,
            )
            validation = operations.fetch_by_id(group_id, validation_id)
            # A new acceptance receipt preserves the earlier Validation history and the Signpost stale gate.
            validation.result_payload = ValidationOperationResultPayload(
                mode="changed",
                base_scenario_fingerprint=before_fingerprint,
                base_dimension_definition_fingerprint=dimension_definition_fingerprint(
                    before["group"]["dimension_definitions"],
                ),
                dimension_definition_fingerprint=dimension_definition_fingerprint(group.dimension_definitions),
                requested_dimension_ids=list(group.dimension_selected),
                requested_dimension_definitions=group.dimension_definitions,
                validation_result=ValidationResultPayload(
                    verdict="PASS_WITH_WARNINGS" if any(c.status == "WARN" for c in checks) else "PASS",
                    is_valid=True,
                    can_proceed=True,
                    checks=checks,
                    reason_markdown=review.reason,
                ),
                application=ValidationApplicationPayload(
                    applied_at=_db_now(),
                    applied_scenario_fingerprint=scenario_fingerprint(
                        [scenarios.model_to_dict(model) for model in models],
                    ),
                ),
            ).model_dump(mode="json", by_alias=True)
            validation.retry_summary = {"qualityRepair": {"evaluationId": operation_id}}
            operations.append_event(
                validation,
                event_type="completed",
                phase="validation",
                title="품질 수정 검증 완료",
                message_markdown=review.reason,
                payload={"canProceed": True},
                now=_db_now(),
                status="succeeded",
            )
            row = evaluations.fetch_by_operation_id(operation_id)
            row.input_snapshot = {**after, "sourceOperationId": validation_id}
            row.input_hash = snapshot_hash(after)
            row.mod_usr_logn_id = str(user_id)
            operation.current_phase = "quality_evaluation"
            operation.retry_summary = {
                "qualityRepair": {
                    **metadata,
                    "state": "applied",
                    "validationOperationId": validation_id,
                    "promptVersion": REPAIR_PROMPT_VERSION,
                    "plan": plan.model_dump(mode="json", by_alias=True),
                    "review": review.model_dump(mode="json", by_alias=True),
                    "llmMetadata": llm_metadata,
                },
            }
