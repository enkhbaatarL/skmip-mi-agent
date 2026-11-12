from __future__ import annotations

import asyncio
from copy import deepcopy
from typing import Any

from apps.agents.scenario_group_agent.constants import AGENT_NAME, API_IDENTIFIER_CREATE_SCENARIOS
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.api_schema import (
    AdditionalDimensionGeneration,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.state import V4MultiEventGenerationState
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.v4_flow import (
    V4_GENERATION_STRATEGY,
    run_v4_multi_event_scenarios_with_progress,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.v4_nodes import MAX_STAGE_ATTEMPTS
from apps.agents.scenario_group_agent.persistence.scenario_group_operation_service import (
    OperationAlreadyTerminalError,
    ScenarioGroupOperationService,
)
from apps.agents.scenario_group_agent.persistence.scenario_group_service import ScenarioGroupService
from apps.agents.scenario_group_agent.utils.execution_log import execution_event, execution_events, logged_run
from apps.common.logging.logger_config import logger
from apps.common.tracing.context import TraceContext, mlflow_trace_context, new_transaction_id


_NODE_PHASES = {
    "analyze_event_impacts": "event_analysis",
    "validate_event_impacts": "event_analysis",
    "analyze_event_interactions": "event_analysis",
    "validate_event_interactions": "event_analysis",
    "design_model_lever_dimensions": "dimension_design",
    "validate_model_lever_dimensions": "dimension_design",
    "synthesize_v4_scenarios": "scenario_synthesis",
    "finalize_v4_scenarios": "scenario_synthesis",
    "generate_v4_group_title": "scenario_synthesis",
    "persist_generation": "persistence",
}
_VALIDATION_NODES = {
    "validate_event_impacts": ("analysis", "Event 분석"),
    "validate_event_interactions": ("interaction", "Event 상호작용 분석"),
    "validate_model_lever_dimensions": ("dimension", "Dimension 설계"),
    "finalize_v4_scenarios": ("scenario", "Scenario 합성"),
}
_RETRY_STAGE_LABELS = {
    "event_impact_analysis": "Event 분석",
    "event_interaction_analysis": "Event 상호작용 분석",
    "dimension_design": "Dimension 설계",
    "scenario_synthesis": "Scenario 합성",
}


class V4OperationProgressRecorder:
    def __init__(self, scenario_group_id: int, operation_id: str, trace_id: str) -> None:
        self.scenario_group_id = scenario_group_id
        self.operation_id = operation_id
        self.trace_id = trace_id
        self._log_offset = 0
        self._started_phases: set[str] = set()
        self.current_phase: str | None = None
        self._recorded_retries: set[tuple[str, int, str | None, tuple[str, ...]]] = set()
        self._presentation: dict[str, Any] = {
            "schemaVersion": "v1",
            "apiVersion": "v4",
            "generationStrategy": V4_GENERATION_STRATEGY,
            "sections": {},
        }

    async def on_node_start(self, node_name: str) -> None:
        phase = _NODE_PHASES.get(node_name)
        execution_event(
            "node",
            f"{node_name} 단계를 시작합니다.",
            status="started",
            node=node_name,
            groupId=self.scenario_group_id,
            operationId=self.operation_id,
        )
        if phase is not None:
            await self._ensure_phase_started(phase)

    async def on_node_update(
        self,
        node_name: str,
        update: dict[str, Any],
        state: V4MultiEventGenerationState,
    ) -> None:
        if node_name == "__custom__" and update.get("kind") == "stage_retry":
            retry_phase = str(update.get("phase") or "unknown")
            retry_stage = str(update.get("stage") or "")
            await self._ensure_phase_started(retry_phase)
            await self._record_retry(
                phase=retry_phase,
                attempt=int(update.get("attempt") or 1),
                validation_code=(str(update["validationCode"]) if update.get("validationCode") else None),
                reference_ids=[str(item) for item in (update.get("referenceIds") or [])],
                label=_RETRY_STAGE_LABELS.get(retry_stage),
            )
            return
        phase = _NODE_PHASES.get(node_name)
        if phase is not None:
            await self._ensure_phase_started(phase)
        validation = _VALIDATION_NODES.get(node_name)
        if validation is None:
            return
        prefix, label = validation
        error = getattr(state, f"{prefix}_error")
        error_code = getattr(state, f"{prefix}_error_code")
        retryable = bool(getattr(state, f"{prefix}_retryable"))
        attempt = int(getattr(state, f"{prefix}_attempt"))
        if error and retryable and attempt < MAX_STAGE_ATTEMPTS:
            await self._record_retry(
                phase=str(phase),
                attempt=attempt + 1,
                validation_code=error_code,
                reference_ids=[],
                label=label,
            )
            return
        if error is not None:
            await self._append(
                event_type="progress",
                phase=phase,
                title=f"{label} 검증을 통과하지 못했습니다",
                message_markdown=f"{label} 검증 기준을 충족하지 못했습니다.",
                payload={"validationCode": error_code, "attempt": attempt},
            )
            return
        title = f"{label}이 완료되었습니다"
        message_markdown = f"{label} 결과가 검증되었습니다."
        if prefix == "analysis" and self._will_analyze_event_interactions(state):
            title = "Event 분석이 완료되었습니다. 이제 Event 상호작용 분석을 시작합니다"
            message_markdown = "Event 분석 결과가 검증되었습니다. 이제 Event 상호작용 분석을 시작합니다."
        await self._append(
            event_type="validated",
            phase=phase,
            title=title,
            message_markdown=message_markdown,
            payload={
                "attempt": attempt,
                "maxAttempts": MAX_STAGE_ATTEMPTS,
                "decision": self._decision_details(prefix, state),
            },
        )
        section = self._safe_section(prefix, state)
        if section is not None:
            self._merge_projection(prefix, state, section)
            await self._append(
                event_type="section_ready",
                phase=phase,
                title=f"{label} 화면을 갱신할 수 있습니다",
                message_markdown=f"검증된 {label} 결과가 준비되었습니다.",
                presentation_snapshot=deepcopy(self._presentation),
            )

    async def _ensure_phase_started(self, phase: str) -> None:
        self.current_phase = phase
        if phase in self._started_phases:
            return
        self._started_phases.add(phase)
        await self._append(
            event_type="phase_started",
            phase=phase,
            title=f"{self._phase_label(phase)}을 시작했습니다",
            message_markdown=self._phase_started_message(phase),
            status="running",
        )

    def _merge_projection(
        self,
        prefix: str,
        state: V4MultiEventGenerationState,
        section: dict[str, Any],
    ) -> None:
        if prefix in {"analysis", "interaction"} and state.analysis_draft is not None:
            self._presentation["events"] = [event.model_dump(mode="json", by_alias=True) for event in state.events]
            self._presentation["generationDiagnostics"] = state.analysis_draft.model_dump(
                mode="json",
                by_alias=True,
            )
            self._presentation["sections"]["eventAnalysis"] = section
            return
        if prefix == "dimension" and state.dimension_draft is not None:
            definitions = getattr(state.dimension_draft, "dimension_definitions", [])
            self._presentation["dimensionDefinitions"] = [
                definition.model_dump(mode="json", by_alias=True) for definition in definitions
            ]
            self._presentation["sections"]["scenarioDesign"] = section

    async def _record_retry(
        self,
        *,
        phase: str,
        attempt: int,
        validation_code: str | None,
        reference_ids: list[str],
        label: str | None = None,
    ) -> None:
        base_key = (phase, attempt, validation_code)
        reference_key = tuple(sorted(reference_ids))
        key = (*base_key, reference_key)
        if not reference_key and any(recorded[:3] == base_key for recorded in self._recorded_retries):
            return
        if key in self._recorded_retries:
            return
        self._recorded_retries.add(key)
        retry_summary = {
            "phase": phase,
            "attempt": attempt,
            "maxAttempts": MAX_STAGE_ATTEMPTS,
            "validationCode": validation_code,
            "referenceIds": reference_ids,
        }
        retry_label = label or self._phase_label(phase)
        await self._append(
            event_type="retrying",
            phase=phase,
            title=f"{retry_label}을 다시 수행합니다",
            message_markdown=f"검증 기준을 충족하지 못해 {retry_label}을 다시 수행합니다.",
            payload=retry_summary,
            retry_summary=retry_summary,
        )

    @property
    def log_offset(self) -> int:
        return self._log_offset

    async def _append(self, **kwargs: Any) -> None:
        event_type = kwargs.get("event_type")
        execution_event(
            "retry" if event_type == "retrying" else str(kwargs.get("phase") or "design"),
            str(kwargs.get("message_markdown") or kwargs["title"]),
            status="started"
            if event_type == "phase_started"
            else "warning"
            if event_type == "retrying" or (kwargs.get("payload") or {}).get("validationCode")
            else "completed",
            groupId=self.scenario_group_id,
            operationId=self.operation_id,
            eventType=event_type,
            context=kwargs.get("payload") or {},
        )
        events = execution_events()
        kwargs["payload"] = {
            **(kwargs.get("payload") or {}),
            "executionLog": [event.model_dump(mode="json", by_alias=True) for event in events[self._log_offset :]],
        }
        await asyncio.to_thread(
            ScenarioGroupOperationService().append_event,
            self.scenario_group_id,
            self.operation_id,
            mlflow_trace_id=self.trace_id,
            **kwargs,
        )
        self._log_offset = len(events)

    @staticmethod
    def _decision_details(prefix: str, state: V4MultiEventGenerationState) -> dict[str, Any]:
        """Expose existing validated explanations and references, without generating new reasoning."""
        if prefix in {"analysis", "interaction"}:
            result = getattr(state, "analysis_draft", None)
            data = result.model_dump(mode="json", by_alias=True) if result else {}
            return {
                "factCount": len(data.get("eventFacts", [])),
                "forecastClaimCount": len(data.get("forecastClaims", [])),
                "decisionBasis": data.get("decisionBasis", []),
                "excludedEvents": data.get("eventExclusions", []),
                "impactPaths": [
                    {key: item.get(key) for key in ("impactPathId", "eventId", "sourceFactIds", "mechanism")}
                    for item in data.get("impactPaths", [])
                ],
                "interactions": data.get("interactions", []),
                "validationWarnings": data.get("validationWarnings", []),
            }
        result = getattr(state, "dimension_draft" if prefix == "dimension" else "finalized_result", None)
        data = result.model_dump(mode="json", by_alias=True) if result else {}
        return {
            "dimensions": [
                {
                    key: item.get(key)
                    for key in ("dimensionId", "label", "rationale", "sourceImpactPathIds", "sourceUncertaintyIds")
                }
                for item in data.get("dimensionDefinitions", [])
            ],
            "excludedDimensions": data.get("excludedDimensions", []),
            "scenarioCount": len(data.get("scenarios", [])),
            "excludedScenarios": data.get("excludedScenarios", []),
            "validationWarnings": data.get("validationWarnings", []),
        }

    @staticmethod
    def _safe_section(prefix: str, state: V4MultiEventGenerationState) -> dict[str, Any] | None:
        if prefix == "analysis" and state.analysis_draft is not None:
            return {
                "status": "partial",
            }
        if prefix == "interaction" and state.analysis_draft is not None:
            return {
                "status": "ready",
            }
        if prefix == "dimension" and state.dimension_draft is not None:
            return {
                "status": "partial",
                "dimensionDefinitions": {"status": "ready"},
                "scenarioTable": {"status": "pending"},
            }
        return None

    @staticmethod
    def _will_analyze_event_interactions(state: V4MultiEventGenerationState) -> bool:
        impact_paths = getattr(state.analysis_draft, "impact_paths", [])
        return len({path.event_id for path in impact_paths}) >= 2

    @staticmethod
    def _phase_label(phase: str) -> str:
        return {
            "event_analysis": "Event 분석",
            "dimension_design": "Dimension 설계",
            "scenario_synthesis": "Scenario 합성",
            "persistence": "결과 저장",
        }.get(phase, phase)

    @staticmethod
    def _phase_started_message(phase: str) -> str:
        if phase == "event_analysis":
            return "선택한 Event의 LNG 시장 영향 경로를 분석하고 있습니다."
        return f"{V4OperationProgressRecorder._phase_label(phase)}을 진행하고 있습니다."


@logged_run("scenario_design", operation_arg=1)
async def run_v4_create_operation(prepared: dict[str, Any], operation_id: str) -> None:
    group = prepared["scenario_group"]
    scenario_group_id = int(group.scenario_group_id)
    service = ScenarioGroupOperationService()
    trace_id = new_transaction_id()
    from apps.common.configs.config import get_settings

    agent_config = get_settings().get_agent_config(AGENT_NAME)
    trace_context = TraceContext(
        transaction_id=trace_id,
        app_identifier=agent_config.aip_app_id,
        agent_name=AGENT_NAME,
        api_identifier=API_IDENTIFIER_CREATE_SCENARIOS,
        session_id=str(scenario_group_id),
        tags={"api_version": "v4", "operation_id": operation_id},
    )
    execution_event(
        "workflow",
        "Event 영향·상호작용 분석 → Dimension 설계 → 시나리오 합성 → 검증·저장 순서로 진행합니다.",
        status="started",
        planningMode="fixed_workflow",
        groupId=scenario_group_id,
        operationId=operation_id,
    )
    recorder = V4OperationProgressRecorder(scenario_group_id, operation_id, trace_id)
    try:
        with mlflow_trace_context(trace_context):
            output = await run_v4_multi_event_scenarios_with_progress(
                prepared,
                on_node_start=recorder.on_node_start,
                on_node_update=recorder.on_node_update,
                trace_context=trace_context,
            )
        if output.data is None:
            msg = "v4 operation output is empty"
            raise RuntimeError(msg)
        group_service = ScenarioGroupService()
        try:
            generation = await asyncio.to_thread(
                group_service.queue_additional_dimension_generation,
                scenario_group_id,
                user_id=int(prepared["user_id"]),
            )
        except Exception as exc:
            generation = {
                "status": "failed",
                "error_code": "ADDITIONAL_DIMENSION_ENQUEUE_FAILED",
            }
            try:
                generation = await asyncio.to_thread(
                    group_service.fail_additional_dimension_enqueue,
                    scenario_group_id,
                    user_id=int(prepared["user_id"]),
                    error_code="ADDITIONAL_DIMENSION_ENQUEUE_FAILED",
                )
            except Exception as status_exc:
                logger.error(
                    "Additional Dimension enqueue failure status update failed | group_id={} | "
                    "operation_id={} | error={!r}",
                    scenario_group_id,
                    operation_id,
                    status_exc,
                )
            logger.error(
                "Additional Dimension enqueue failed without failing create operation | group_id={} | "
                "operation_id={} | error_code=ADDITIONAL_DIMENSION_ENQUEUE_FAILED | error={!r}",
                scenario_group_id,
                operation_id,
                exc,
            )
        presentation = {
            "schemaVersion": "v1",
            **output.data.model_dump(mode="json", by_alias=True),
        }
        presentation.setdefault("generationDiagnostics", {})["additionalDimensionGeneration"] = (
            AdditionalDimensionGeneration.model_validate(generation).model_dump(mode="json", by_alias=True)
        )
        execution_event(
            "outcome",
            "검증된 시나리오를 저장했습니다.",
            groupId=scenario_group_id,
            scenarioCount=len(output.data.table.rows),
        )
        await asyncio.to_thread(
            service.append_event,
            scenario_group_id,
            operation_id,
            event_type="completed",
            phase="persistence",
            title="시나리오 그룹 생성이 완료되었습니다",
            message_markdown=f"{len(output.data.table.rows)}개 Scenario를 생성했습니다.",
            payload={
                "status": "succeeded",
                "executionLog": [
                    event.model_dump(mode="json", by_alias=True) for event in execution_events()[recorder.log_offset :]
                ],
            },
            status="succeeded",
            presentation_snapshot=presentation,
            mlflow_trace_id=trace_id,
        )
        if generation.get("status") == "queued":
            from apps.agents.scenario_group_agent.runtime import get_additional_dimension_task_runner

            try:
                get_additional_dimension_task_runner().submit(scenario_group_id)
            except Exception as exc:
                try:
                    await asyncio.to_thread(
                        group_service.fail_additional_dimension_enqueue,
                        scenario_group_id,
                        user_id=int(prepared["user_id"]),
                        error_code="ADDITIONAL_DIMENSION_ENQUEUE_FAILED",
                    )
                except Exception as status_exc:
                    logger.error(
                        "Additional Dimension submit failure status update failed | group_id={} | "
                        "operation_id={} | error={!r}",
                        scenario_group_id,
                        operation_id,
                        status_exc,
                    )
                logger.error(
                    "Additional Dimension task submit failed without failing create operation | group_id={} | "
                    "operation_id={} | error_code=ADDITIONAL_DIMENSION_ENQUEUE_FAILED | error={!r}",
                    scenario_group_id,
                    operation_id,
                    exc,
                )
    except asyncio.CancelledError:
        execution_event("outcome", "서버 종료로 시나리오 설계가 중단되었습니다.", status="interrupted")
        await asyncio.shield(
            asyncio.to_thread(
                service.append_event,
                scenario_group_id,
                operation_id,
                event_type="interrupted",
                phase=recorder.current_phase or "event_analysis",
                title="서버 종료로 작업이 중단되었습니다",
                message_markdown="서버가 종료되어 작업이 중단되었습니다. 자동 재개는 아직 지원하지 않습니다.",
                payload={
                    "status": "interrupted",
                    "executionLog": [
                        event.model_dump(mode="json", by_alias=True)
                        for event in execution_events()[recorder.log_offset :]
                    ],
                },
                status="interrupted",
                last_error={"code": "SERVER_SHUTDOWN", "message": "Operation producer was interrupted"},
                mlflow_trace_id=trace_id,
            ),
        )
        raise
    except OperationAlreadyTerminalError:
        execution_event("outcome", "이미 종료된 작업이므로 실행을 중단합니다.", status="interrupted")
        logger.warning(
            "Scenario Group operation producer stopped because the operation is already terminal | "
            "group_id={} | operation_id={}",
            scenario_group_id,
            operation_id,
        )
    except Exception as exc:
        execution_event("outcome", "시나리오 설계 실행에 실패했습니다.", status="failed", errorType=type(exc).__name__)
        error_message = str(exc)[:1000]
        logger.error(
            "Scenario Group operation failed | group_id={} | operation_id={} | error={!r}",
            scenario_group_id,
            operation_id,
            exc,
        )
        await asyncio.to_thread(
            service.append_event,
            scenario_group_id,
            operation_id,
            event_type="failed",
            phase=recorder.current_phase or "event_analysis",
            title="시나리오 그룹 생성에 실패했습니다",
            message_markdown="시나리오 그룹 생성 중 오류가 발생했습니다.",
            payload={
                "status": "failed",
                "errorCode": type(exc).__name__,
                "executionLog": [
                    event.model_dump(mode="json", by_alias=True) for event in execution_events()[recorder.log_offset :]
                ],
            },
            status="failed",
            last_error={"code": type(exc).__name__, "message": error_message},
            mlflow_trace_id=trace_id,
        )
