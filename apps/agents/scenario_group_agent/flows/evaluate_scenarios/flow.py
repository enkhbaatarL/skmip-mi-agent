from __future__ import annotations

# ruff: noqa: CPY001
import asyncio
import json
from typing import Any

from pydantic import BaseModel

from apps.agents.scenario_group_agent.flows.evaluate_scenarios.repair import (
    build_repaired_snapshot,
    validate_repair_strategies,
)
from apps.agents.scenario_group_agent.persistence.scenario_group_operation_service import ScenarioGroupOperationService
from apps.agents.scenario_group_agent.persistence.scenario_quality_evaluation_service import (
    ScenarioQualityEvaluationService,
)
from apps.agents.scenario_group_agent.persistence.scenario_quality_repair_service import ScenarioQualityRepairService
from apps.agents.scenario_group_agent.prompts.scenario_quality_evaluation import (
    SYSTEM_PROMPT,
    summarize,
    validate_targets,
)
from apps.agents.scenario_group_agent.prompts.scenario_quality_repair import (
    PLAN_COMPARISON_PROMPT,
    PLANNING_PROMPT,
    REVIEW_PROMPT,
    SYSTEM_PROMPT as REPAIR_SYSTEM_PROMPT,
    QualityRepairPlan,
    QualityRepairReview,
    QualityRepairStrategies,
    QualityRepairStrategyComparison,
)
from apps.agents.scenario_group_agent.runtime import get_scenario_group_operation_task_runner
from apps.agents.scenario_group_agent.utils.execution_log import (
    execution_event,
    logged_run,
    persist_execution_events,
    traced_llm_call,
)
from apps.common.configs.config import get_settings
from apps.common.exceptions.custom import MIBaseError
from apps.common.logging.logger_config import logger
from apps.common.values.error_codes import ErrorCode
from apps.connectors.llm.llm_client import LLMStructuredResult, invoke_llm_structured_output
from apps.persistence.scenario_group_operation.schema import TERMINAL_OPERATION_STATUSES
from apps.persistence.scenario_quality_evaluation.schema import (
    InputOnlyScenarioQualityJudgment,
    ScenarioQualityJudgment,
)


@logged_run("quality_evaluation", operation_arg=1)
async def run_quality_evaluation(group_id: int, operation_id: str) -> None:
    service = ScenarioQualityEvaluationService()
    try:
        record = await asyncio.to_thread(service.get, group_id, operation_id)
        if record.status in TERMINAL_OPERATION_STATUSES:
            execution_event("outcome", "이미 종료된 평가이므로 다시 실행하지 않습니다.", status="skipped")
            return
        is_repair = (record.retry_summary.get("qualityRepair") or {}).get("attempt") == 1
        await asyncio.to_thread(
            ScenarioGroupOperationService().start_operation,
            group_id,
            operation_id,
            phase="quality_repair" if is_repair else "quality_evaluation",
        )
        if is_repair:
            if not await _repair_once(group_id, operation_id):
                return
            record = await asyncio.to_thread(service.get, group_id, operation_id)
        execution_event(
            "evaluation",
            "수정 반영 후 동일한 7개 기준으로 재평가합니다."
            if is_repair
            else "입력 Event와 시나리오의 근거·논리를 7개 기준으로 평가합니다.",
            status="started",
            groupId=group_id,
            operationId=operation_id,
            inputHash=record.input_hash,
            afterApplication=is_repair,
        )
        await persist_execution_events(group_id, operation_id, "quality_evaluation")
        cfg = get_settings()
        response = await traced_llm_call(
            invoke_llm_structured_output,
            output_schema=InputOnlyScenarioQualityJudgment,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(record.input_snapshot, ensure_ascii=False)},
            ],
            temperature=0.0,
            max_retries=0,
            stream=cfg.llm_stream_enabled,
            reasoning_effort=cfg.llm_reasoning_effort,
            log_label="scenario_quality_evaluation",
        )
        validate_targets(response.result, record.input_snapshot)
        verdict, score = summarize(response.result)
        execution_event(
            "diagnosis",
            response.result.summary,
            verdict=verdict,
            averageScore=score,
            criteria=[
                {
                    "judgeId": item.judge_id,
                    "verdict": item.verdict,
                    "score": item.score,
                    "violationCount": len(item.violations),
                }
                for item in response.result.items
            ],
        )
        if is_repair:
            parent_id = record.retry_summary["qualityRepair"]["parentEvaluationId"]
            parent = await asyncio.to_thread(service.get, group_id, parent_id)
            if parent.result is not None:
                old = {item.judge_id: item for item in parent.result.items}
                regressions = [
                    item.judge_id
                    for item in response.result.items
                    if old[item.judge_id].verdict == "PASS" and item.verdict != "PASS"
                ]
                delta = round(score - float(parent.average_score), 6)
                execution_event(
                    "comparison",
                    "수정 전후 평가를 비교했습니다. 반영된 수정은 유지합니다.",
                    status="warning" if regressions or delta < 0 else "completed",
                    beforeScore=parent.average_score,
                    afterScore=score,
                    scoreDelta=delta,
                    beforeVerdict=parent.verdict,
                    afterVerdict=verdict,
                    newViolations=regressions,
                    scoreChange="improved" if delta > 0 else "declined" if delta < 0 else "unchanged",
                    reviewRequired=bool(regressions or delta < 0 or verdict != "PASS"),
                )
        await persist_execution_events(group_id, operation_id, "quality_evaluation")
        retry_id = await asyncio.to_thread(
            service.complete,
            group_id,
            operation_id,
            result=response.result,
            verdict=verdict,
            average_score=score,
            llm_metadata={
                "model": response.model,
                "usage": response.usage.model_dump(mode="json") if response.usage else None,
            },
            repair_once=True,
        )
        if retry_id is not None:
            await get_scenario_group_operation_task_runner().run_with_heartbeat(
                group_id,
                retry_id,
                run_quality_evaluation(group_id, retry_id),
            )
    except asyncio.CancelledError:
        execution_event("outcome", "평가 실행이 취소되었습니다. 이미 반영된 수정은 유지됩니다.", status="interrupted")
        await asyncio.shield(persist_execution_events(group_id, operation_id, "quality_evaluation"))
        await asyncio.shield(
            asyncio.to_thread(service.fail, group_id, operation_id, interrupted=True, code="SERVER_SHUTDOWN"),
        )
        raise
    except Exception as exc:
        execution_event(
            "outcome",
            "평가를 완료하지 못했습니다. 반영 여부는 qualityRepair.state를 확인하세요.",
            status="failed",
            errorType=type(exc).__name__,
        )
        await persist_execution_events(group_id, operation_id, "quality_evaluation")
        logger.error("Quality evaluation {} failed: {}", operation_id, type(exc).__name__)
        await asyncio.to_thread(service.fail, group_id, operation_id, code=type(exc).__name__)


async def _repair_once(group_id: int, operation_id: str) -> bool:
    service = ScenarioQualityRepairService()
    context = await asyncio.to_thread(service.claim, group_id, operation_id)
    if context is None:
        execution_event("outcome", "수정 실행 권한을 확보하지 못해 중복 실행을 생략합니다.", status="skipped")
        return False
    execution_event(
        "planning",
        "평가 위반을 해결할 서로 다른 수정 계획 2개를 수립합니다.",
        status="started",
        planningMode="generated",
        maxCandidates=2,
        maxRepairAttempts=1,
    )
    await persist_execution_events(group_id, operation_id, "quality_repair")
    strategies_response = await _planning_call(
        QualityRepairStrategies, PLANNING_PROMPT, context, "scenario_quality_repair_planning",
    )
    strategies = QualityRepairStrategies.model_validate(strategies_response.result)
    validate_repair_strategies(
        context["inputSnapshot"], ScenarioQualityJudgment.model_validate(context["judgment"]), strategies,
    )
    planning = {
        "candidates": strategies.model_dump(mode="json", by_alias=True)["candidates"],
        "selectionRule": "feasible; totalScore DESC, evidenceScore DESC, candidateId ASC",
        "llmMetadata": {"planning": _metadata(strategies_response)},
    }
    await asyncio.to_thread(service.record_planning, group_id, operation_id, planning)
    execution_event(
        "planning", "수정 계획 A/B를 생성하고 수정 대상의 허용 범위를 확인했습니다.", candidates=planning["candidates"],
    )
    execution_event(
        "plan_comparison",
        "해결 가능성·근거 보존·최소 변경을 비교합니다.",
        status="started",
        scoreMeaning="계획의 예상 적합도이며 실제 개선 점수가 아님",
    )
    await persist_execution_events(group_id, operation_id, "quality_repair")
    comparison_response = await _planning_call(
        QualityRepairStrategyComparison,
        PLAN_COMPARISON_PROMPT,
        {**context, "strategies": planning["candidates"]},
        "scenario_quality_repair_plan_comparison",
    )
    comparison = QualityRepairStrategyComparison.model_validate(comparison_response.result)
    selected = comparison.select()
    planning.update(
        {
            "comparison": comparison.model_dump(mode="json", by_alias=True),
            "selectedCandidateId": selected.candidate_id if selected else None,
        },
    )
    planning["llmMetadata"]["comparison"] = _metadata(comparison_response)
    await asyncio.to_thread(service.record_planning, group_id, operation_id, planning)
    execution_event(
        "selection",
        selected.reason if selected else "실행 가능한 수정 계획이 없어 수정을 중단합니다.",
        status="completed" if selected else "warning",
        **planning,
    )
    await persist_execution_events(group_id, operation_id, "quality_repair")
    if selected is None:
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="No feasible repair strategy")
    strategy = next(item for item in strategies.candidates if item.candidate_id == selected.candidate_id)
    execution_event(
        "self_correction",
        "선택한 계획에 따라 수정안을 생성합니다.",
        status="started",
        candidateId=strategy.candidate_id,
        stepCount=len(strategy.steps),
    )
    await persist_execution_events(group_id, operation_id, "quality_repair")
    cfg = get_settings()
    response = await traced_llm_call(
        invoke_llm_structured_output,
        output_schema=QualityRepairPlan,
        messages=[
            {"role": "system", "content": REPAIR_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps(
                    {**context, "selectedStrategy": strategy.model_dump(mode="json", by_alias=True)},
                    ensure_ascii=False,
                ),
            },
        ],
        temperature=0.0,
        max_retries=0,
        stream=cfg.llm_stream_enabled,
        reasoning_effort=cfg.llm_reasoning_effort,
        log_label="scenario_quality_repair",
    )
    allowed = {(target.judge_id, target.violation_index, target.path) for target in strategy.targets}
    if any((change.judge_id, change.violation_index, change.path) not in allowed for change in response.result.changes):
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="Repair exceeds selected strategy targets")
    candidate, _ = build_repaired_snapshot(
        context["inputSnapshot"],
        ScenarioQualityJudgment.model_validate(context["judgment"]),
        response.result,
        context["diagnostics"],
    )
    execution_event(
        "validation",
        "수정안의 구조 검증을 통과했습니다. 근거 보존 여부를 검토합니다.",
        changedPaths=[change.path for change in response.result.changes],
    )
    await persist_execution_events(group_id, operation_id, "quality_repair")
    review = await traced_llm_call(
        invoke_llm_structured_output,
        output_schema=QualityRepairReview,
        messages=[
            {"role": "system", "content": REVIEW_PROMPT},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "before": context["inputSnapshot"],
                        "after": candidate,
                        "judgment": context["judgment"],
                    },
                    ensure_ascii=False,
                ),
            },
        ],
        temperature=0.0,
        max_retries=0,
        stream=cfg.llm_stream_enabled,
        reasoning_effort=cfg.llm_reasoning_effort,
        log_label="scenario_quality_repair_validation",
    )
    execution_event(
        "validation",
        review.result.reason,
        status="completed" if review.result.can_proceed else "warning",
        canProceed=review.result.can_proceed,
    )
    await persist_execution_events(group_id, operation_id, "quality_repair")
    await asyncio.to_thread(
        service.apply,
        group_id,
        operation_id,
        response.result,
        review.result,
        llm_metadata={
            "repair": {
                "model": response.model,
                "usage": response.usage.model_dump(mode="json") if response.usage else None,
            },
            "review": {"model": review.model, "usage": review.usage.model_dump(mode="json") if review.usage else None},
        },
    )
    execution_event(
        "application",
        "수정안을 실제 반영했습니다. 저장된 값을 기준으로 재평가합니다.",
        changedPaths=[change.path for change in response.result.changes],
        automaticRollback=False,
    )
    await persist_execution_events(group_id, operation_id, "quality_evaluation")
    return True


def _metadata(response: LLMStructuredResult) -> dict[str, Any]:
    return {"model": response.model, "usage": response.usage.model_dump(mode="json") if response.usage else None}


async def _planning_call[T: BaseModel](
    schema: type[T],
    prompt: str,
    payload: dict[str, Any],
    label: str,
) -> LLMStructuredResult[T]:
    cfg = get_settings()
    return await traced_llm_call(
        invoke_llm_structured_output,
        output_schema=schema,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        temperature=0.0,
        max_retries=0,
        stream=cfg.llm_stream_enabled,
        reasoning_effort=cfg.llm_reasoning_effort,
        log_label=label,
    )


def submit_quality_evaluation(group_id: int, operation_id: str) -> None:
    get_scenario_group_operation_task_runner().submit(
        group_id,
        operation_id,
        run_quality_evaluation(group_id, operation_id),
    )


async def submit_automatic_evaluation(group_id: int, source_operation_id: str) -> None:
    service = ScenarioQualityEvaluationService()
    try:
        operation_id = await asyncio.to_thread(service.automatic_operation_id, group_id, source_operation_id)
        if operation_id is not None:
            try:
                submit_quality_evaluation(group_id, operation_id)
            except Exception:
                await asyncio.to_thread(service.fail, group_id, operation_id, code="EVALUATION_SUBMIT_FAILED")
                raise
    except Exception as exc:
        logger.error("Automatic evaluation submission failed for {}: {}", source_operation_id, type(exc).__name__)
