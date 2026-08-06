from __future__ import annotations

import copy
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AgentRun, Feedback, ParameterProposal, RunArtifact
from app.schemas.pipeline import RunMetadata


def create_run(
    session: Session,
    metadata: RunMetadata,
    scenario_json: dict[str, Any],
    clarification_answers: dict[str, Any],
    asset_snapshot: dict[str, Any],
    pipeline_result: dict[str, Any],
    *,
    parent_run: AgentRun | None = None,
) -> AgentRun:
    run_id = str(uuid.uuid4())
    root_run_id = parent_run.root_run_id if parent_run else run_id
    revision = parent_run.revision + 1 if parent_run else 1
    scenario_summaries = []
    proposal_count = 0
    for scenario_result in pipeline_result["scenarios"]:
        summary = {key: copy.deepcopy(value) for key, value in scenario_result.items() if key != "proposals"}
        scenario_summaries.append(summary)
        proposal_count += len(scenario_result["proposals"])
    validation_record = {
        **pipeline_result["validationReport"],
        "evaluationInvariants": pipeline_result["evaluationInvariants"],
        "scenarioSummaries": scenario_summaries,
        "syntheticBaselineLabel": pipeline_result["syntheticBaselineLabel"],
    }
    row = AgentRun(
        run_id=run_id,
        root_run_id=root_run_id,
        parent_run_id=parent_run.run_id if parent_run else None,
        revision=revision,
        comparison_run_id=metadata.comparison_run_id,
        status="completed",
        target_market=metadata.target_market,
        event_ids=metadata.mi_event_ids,
        horizon_start=pipeline_result["horizon"]["start"],
        horizon_end=pipeline_result["horizon"]["end"],
        include_recovery=pipeline_result["horizon"]["includeRecovery"],
        metadata_json=metadata.model_dump(by_alias=True),
        source_scenario_json=scenario_json,
        normalized_input_json=pipeline_result["normalizedInput"],
        clarification_answers_json=clarification_answers,
        asset_snapshot_json=asset_snapshot,
        validation_report_json=validation_record,
        scenario_count=len(pipeline_result["scenarios"]),
        proposal_count=proposal_count,
        adjustment_count=len(pipeline_result.get("appliedAdjustments", [])),
    )
    session.add(row)
    session.flush()
    for artifact in pipeline_result["artifacts"]:
        output_json = copy.deepcopy(artifact["output"])
        if artifact["stepId"] == "persist_result":
            output_json.update({"runId": run_id, "proposalCount": proposal_count, "status": "persisted"})
        session.add(
            RunArtifact(
                artifact_id=str(uuid.uuid4()),
                run_id=run_id,
                step_id=artifact["stepId"],
                ordinal=artifact["ordinal"],
                status="completed",
                input_json=artifact.get("input", {}),
                output_json=output_json,
                validation_messages_json=artifact.get("validationMessages", []),
                exclusion_log_json=artifact.get("exclusionLog", []),
                duration_ms=artifact.get("durationMs", 0),
            )
        )
    for scenario_result in pipeline_result["scenarios"]:
        for proposal in scenario_result["proposals"]:
            proposal_id = str(uuid.uuid4())
            proposal["proposalId"] = proposal_id
            session.add(
                ParameterProposal(
                    proposal_id=proposal_id,
                    run_id=run_id,
                    scenario_key=scenario_result["scenarioKey"],
                    parameter_code=proposal["parameterCode"],
                    parameter_name=proposal["parameterName"],
                    domain=proposal["domain"],
                    application_start=proposal["applicationPeriod"]["start"],
                    application_end=proposal["applicationPeriod"]["end"],
                    baseline_peak=proposal["baselinePeak"],
                    proposed_peak=proposal["proposedPeak"],
                    delta_peak=proposal["delta"],
                    delta_percent=proposal["deltaPercent"],
                    confidence=proposal["confidence"],
                    warning_count=proposal["warningCount"],
                    result_json=proposal,
                )
            )
    session.flush()
    return row


def get_run(session: Session, run_id: str, for_update: bool = False) -> AgentRun | None:
    statement = select(AgentRun).where(AgentRun.run_id == run_id)
    if for_update:
        statement = statement.with_for_update()
    return session.scalar(statement)


def list_runs(session: Session, page: int, page_size: int) -> tuple[list[AgentRun], int]:
    total = int(session.scalar(select(func.count()).select_from(AgentRun)) or 0)
    rows = list(
        session.scalars(
            select(AgentRun)
            .order_by(AgentRun.created_at.desc(), AgentRun.revision.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return rows, total


def run_summary(session: Session, row: AgentRun) -> dict[str, Any]:
    feedback_rows = list(session.scalars(select(Feedback).where(Feedback.run_id == row.run_id)))
    return {
        "runId": row.run_id,
        "rootRunId": row.root_run_id,
        "parentRunId": row.parent_run_id,
        "revision": row.revision,
        "comparisonRunId": row.comparison_run_id,
        "targetMarket": row.target_market,
        "eventIds": row.event_ids,
        "createdAt": row.created_at.isoformat(),
        "status": row.status,
        "scenarioCount": row.scenario_count,
        "proposalCount": row.proposal_count,
        "interimFeedbackCount": sum(item.tag == "interim" for item in feedback_rows),
        "finalFeedbackCount": sum(item.tag == "final" for item in feedback_rows),
        "adjustmentCount": row.adjustment_count,
        "assetVersions": row.asset_snapshot_json,
        "horizon": {"start": row.horizon_start, "end": row.horizon_end, "includesRecovery": row.include_recovery},
    }


def run_detail(session: Session, row: AgentRun) -> dict[str, Any]:
    artifacts = list(
        session.scalars(select(RunArtifact).where(RunArtifact.run_id == row.run_id).order_by(RunArtifact.ordinal))
    )
    proposals = list(
        session.scalars(
            select(ParameterProposal)
            .where(ParameterProposal.run_id == row.run_id)
            .order_by(ParameterProposal.scenario_key, ParameterProposal.parameter_code)
        )
    )
    feedback_rows = list(
        session.scalars(select(Feedback).where(Feedback.run_id == row.run_id).order_by(Feedback.created_at))
    )
    chain = list(
        session.scalars(select(AgentRun).where(AgentRun.root_run_id == row.root_run_id).order_by(AgentRun.revision))
    )
    scenario_summaries = row.validation_report_json.get("scenarioSummaries", [])
    scenarios = []
    for summary in scenario_summaries:
        scenario_proposals = [item.result_json for item in proposals if item.scenario_key == summary["scenarioKey"]]
        scenarios.append({**summary, "proposals": scenario_proposals})
    children = list(
        session.scalars(select(AgentRun).where(AgentRun.parent_run_id == row.run_id).order_by(AgentRun.revision))
    )
    return {
        **run_summary(session, row),
        "metadata": row.metadata_json,
        "sourceScenarioJson": row.source_scenario_json,
        "normalizedInput": row.normalized_input_json,
        "clarificationAnswers": row.clarification_answers_json,
        "validationReport": {
            key: value for key, value in row.validation_report_json.items() if key != "scenarioSummaries"
        },
        "assetSnapshot": row.asset_snapshot_json,
        "parentRun": run_summary(session, get_run(session, row.parent_run_id)) if row.parent_run_id else None,
        "childRuns": [run_summary(session, item) for item in children],
        "revisionChain": [
            {
                "runId": item.run_id,
                "revision": item.revision,
                "status": item.status,
                "createdAt": item.created_at.isoformat(),
            }
            for item in chain
        ],
        "artifacts": [
            {
                "artifactId": item.artifact_id,
                "stepId": item.step_id,
                "ordinal": item.ordinal,
                "status": item.status,
                "input": item.input_json,
                "output": item.output_json,
                "validationMessages": item.validation_messages_json,
                "exclusionLog": item.exclusion_log_json,
                "durationMs": item.duration_ms,
            }
            for item in artifacts
        ],
        "feedbacks": [feedback_to_dict(item) for item in feedback_rows],
        "scenarios": scenarios,
        "evaluationInvariants": row.validation_report_json.get("evaluationInvariants", {}),
        "syntheticBaselineLabel": row.validation_report_json.get("syntheticBaselineLabel"),
    }


def feedback_to_dict(row: Feedback) -> dict[str, Any]:
    return {
        "feedbackId": row.feedback_id,
        "runId": row.run_id,
        "resultRunId": row.result_run_id,
        "tag": row.tag,
        "source": row.source,
        "scope": row.scope,
        "rawText": row.raw_text,
        "context": row.context_json,
        "answer": row.answer_json,
        "interpretation": row.interpretation_json,
        "adjustment": row.adjustment_json,
        "processingStatus": row.processing_status,
        "attemptCount": row.attempt_count,
        "learningBatchId": row.learning_batch_id,
        "createdAt": row.created_at.isoformat(),
        "recordJson": {
            "feedback_id": row.feedback_id,
            "run_id": row.run_id,
            "result_run_id": row.result_run_id,
            "tag": row.tag,
            "source": row.source,
            "scope": row.scope,
            "raw_text": row.raw_text,
            "context_json": row.context_json,
            "answer_json": row.answer_json,
            "interpretation_json": row.interpretation_json,
            "adjustment_json": row.adjustment_json,
            "processing_status": row.processing_status,
            "learning_batch_id": row.learning_batch_id,
        },
    }
