from __future__ import annotations

# ruff: noqa: CPY001
import asyncio
import json

from apps.agents.scenario_group_agent.flows.evaluate_scenarios.repair import build_repaired_snapshot
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
    REVIEW_PROMPT,
    SYSTEM_PROMPT as REPAIR_SYSTEM_PROMPT,
    QualityRepairPlan,
    QualityRepairReview,
)
from apps.agents.scenario_group_agent.runtime import get_scenario_group_operation_task_runner
from apps.common.configs.config import get_settings
from apps.common.logging.logger_config import logger
from apps.connectors.llm.llm_client import invoke_llm_structured_output
from apps.persistence.scenario_group_operation.schema import TERMINAL_OPERATION_STATUSES
from apps.persistence.scenario_quality_evaluation.schema import (
    InputOnlyScenarioQualityJudgment,
    ScenarioQualityJudgment,
)


async def run_quality_evaluation(group_id: int, operation_id: str) -> None:
    service = ScenarioQualityEvaluationService()
    try:
        record = await asyncio.to_thread(service.get, group_id, operation_id)
        if record.status in TERMINAL_OPERATION_STATUSES:
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
        cfg = get_settings()
        response = await invoke_llm_structured_output(
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
        await asyncio.shield(
            asyncio.to_thread(service.fail, group_id, operation_id, interrupted=True, code="SERVER_SHUTDOWN"),
        )
        raise
    except Exception as exc:
        logger.error("Quality evaluation {} failed: {}", operation_id, type(exc).__name__)
        await asyncio.to_thread(service.fail, group_id, operation_id, code=type(exc).__name__)


async def _repair_once(group_id: int, operation_id: str) -> bool:
    service = ScenarioQualityRepairService()
    context = await asyncio.to_thread(service.claim, group_id, operation_id)
    if context is None:
        return False
    cfg = get_settings()
    response = await invoke_llm_structured_output(
        output_schema=QualityRepairPlan,
        messages=[
            {"role": "system", "content": REPAIR_SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
        ],
        temperature=0.0,
        max_retries=0,
        stream=cfg.llm_stream_enabled,
        reasoning_effort=cfg.llm_reasoning_effort,
        log_label="scenario_quality_repair",
    )
    candidate, _ = build_repaired_snapshot(
        context["inputSnapshot"],
        ScenarioQualityJudgment.model_validate(context["judgment"]),
        response.result,
        context["diagnostics"],
    )
    review = await invoke_llm_structured_output(
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
    return True


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
