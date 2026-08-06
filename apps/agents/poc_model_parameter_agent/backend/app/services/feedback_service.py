from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import ConflictAppError, NotFoundAppError, ValidationAppError
from app.models import AgentRun, Feedback, ParameterProposal
from app.persistence.asset_repository import seed_for_snapshot
from app.persistence.feedback_repository import final_feedback_for_run
from app.persistence.run_repository import create_run, feedback_to_dict, get_run, run_detail
from app.pipeline.orchestrator import PipelineOrchestrator
from app.schemas.pipeline import FinalFeedbackRequest, RunMetadata

REDUCE_WORDS = ("너무", "과도", "직접적", "완화", "낮음", "보수적", "줄임", "줄여", "과대", "강하다", "크다")
INCREASE_WORDS = ("너무 작다", "약하다", "과소", "키워", "강화")


def interpret_feedback(
    text: str,
    scope: str,
    scenario_key: str | None,
    parameter_code: str | None,
) -> dict[str, Any]:
    lowered = text.lower()
    reduce_signal = any(word in lowered for word in REDUCE_WORDS)
    if any(word in lowered for word in INCREASE_WORDS):
        return {
            "interpreted": True,
            "ruleCode": "SCOPE_INCREASE",
            "factor": 1.15,
            "parameterCode": parameter_code if scope == "parameter" else None,
            "scenarioKey": scenario_key if scope in {"parameter", "scenario"} else None,
            "matchedSignals": ["increase"],
        }
    if (
        all(any(word in lowered for word in group) for group in (("현물", "spot"), ("cargo", "카고", "화물")))
        and reduce_signal
    ):
        return {
            "interpreted": True,
            "ruleCode": "SPOT_CARGO_REDUCE",
            "factor": 0.7,
            "parameterCode": "asia_spot_cargo_availability_index",
            "scenarioKey": scenario_key,
            "matchedSignals": ["spot/cargo", "reduce"],
        }
    if any(word in lowered for word in ("위험 프리미엄", "risk", "심리", "헤드라인")) and reduce_signal:
        return {
            "interpreted": True,
            "ruleCode": "RISK_PROXY_REDUCE",
            "factor": 0.6,
            "parameterCode": "lng_market_risk_proxy_index",
            "scenarioKey": scenario_key,
            "matchedSignals": ["risk/sentiment", "reduce"],
        }
    if "공급" in lowered and reduce_signal:
        return {
            "interpreted": True,
            "ruleCode": "SUPPLY_DOMAIN_REDUCE",
            "factor": 0.8,
            "domain": "supply",
            "scenarioKey": scenario_key,
            "matchedSignals": ["supply", "reduce"],
        }
    if "수요" in lowered and reduce_signal:
        return {
            "interpreted": True,
            "ruleCode": "DEMAND_DOMAIN_REDUCE",
            "factor": 0.8,
            "domain": "demand",
            "scenarioKey": scenario_key,
            "matchedSignals": ["demand", "reduce"],
        }
    if any(word in lowered for word in ("너무 크다", "강하다", "과대", "줄여", "완화")):
        return {
            "interpreted": True,
            "ruleCode": "SCOPE_REDUCE",
            "factor": 0.85,
            "parameterCode": parameter_code if scope == "parameter" else None,
            "scenarioKey": scenario_key if scope in {"parameter", "scenario"} else None,
            "matchedSignals": ["reduce"],
        }
    return {"interpreted": False, "ruleCode": "NO_MATCH", "matchedSignals": []}


def build_feedback_context(
    session: Session,
    run: AgentRun,
    scope: str,
    scenario_key: str | None,
    parameter_code: str | None,
) -> dict[str, Any]:
    scenario = None
    if scenario_key and scenario_key.startswith("scenario-"):
        try:
            index = int(scenario_key.removeprefix("scenario-")) - 1
        except ValueError as exc:
            raise ValidationAppError("유효하지 않은 scenarioKey입니다.", {"scenarioKey": scenario_key}) from exc
        scenario_items = run.source_scenario_json.get("scenarios", [])
        if 0 <= index < len(scenario_items):
            scenario = scenario_items[index]
        else:
            raise ValidationAppError("Run에 존재하지 않는 scenarioKey입니다.", {"scenarioKey": scenario_key})
    proposals = list(session.scalars(select(ParameterProposal).where(ParameterProposal.run_id == run.run_id)))
    scoped_proposals = proposals
    if scenario_key:
        scoped_proposals = [item for item in scoped_proposals if item.scenario_key == scenario_key]
    if parameter_code:
        scoped_proposals = [item for item in scoped_proposals if item.parameter_code == parameter_code]
    if (scenario_key or parameter_code) and not scoped_proposals:
        raise ValidationAppError(
            "Feedback Scope 대상 Proposal을 Run에서 찾을 수 없습니다.",
            {"scenarioKey": scenario_key, "parameterCode": parameter_code},
        )
    evidence = [
        item
        for proposal in scoped_proposals
        for item in proposal.result_json.get("evidence", [])
        if isinstance(item, dict)
    ]
    event_ids = sorted({int(item["eventId"]) for item in evidence if item.get("eventId") is not None})
    lever_codes = sorted({str(item["leverCode"]) for item in evidence if item.get("leverCode")})
    return {
        "runId": run.run_id,
        "revision": run.revision,
        "scope": scope,
        "scenarioKey": scenario_key,
        "eventIds": event_ids or run.event_ids,
        "leverCodes": lever_codes,
        "parameterCodes": sorted({item.parameter_code for item in scoped_proposals}),
        "focusParameter": parameter_code,
        "dimensionValues": scenario.get("dimensionValues", {}) if scenario else {},
        "assetVersions": run.asset_snapshot_json,
    }


def create_interim_feedback(
    session: Session,
    run: AgentRun,
    answers: dict[str, Any],
    adjustment: dict[str, Any] | None,
) -> list[Feedback]:
    rows: list[Feedback] = []
    for question_id, raw_answer in answers.items():
        if isinstance(raw_answer, dict):
            raw_text = str(
                raw_answer.get("text") or raw_answer.get("choiceId") or raw_answer.get("value") or ""
            ).strip()
        else:
            raw_text = str(raw_answer).strip()
        if not raw_text:
            continue
        interpretation = (
            adjustment
            if question_id == "additional_instruction" and adjustment
            else {"interpreted": True, "ruleCode": "CLARIFICATION_ANSWER", "questionId": question_id}
        )
        row = Feedback(
            feedback_id=str(uuid.uuid4()),
            run_id=run.run_id,
            result_run_id=run.run_id,
            tag="interim",
            source="clarification",
            scope="run",
            raw_text=raw_text,
            context_json={**build_feedback_context(session, run, "run", None, None), "questionId": question_id},
            answer_json={"questionId": question_id, "value": raw_answer},
            interpretation_json=interpretation,
            adjustment_json=adjustment if question_id == "additional_instruction" and adjustment else {},
            processing_status="pending",
        )
        session.add(row)
        rows.append(row)
    session.flush()
    return rows


def submit_final_feedback(
    session: Session,
    run_id: str,
    request: FinalFeedbackRequest,
    orchestrator: PipelineOrchestrator,
) -> dict[str, Any]:
    try:
        with session.begin():
            parent = get_run(session, run_id, for_update=True)
            if parent is None:
                raise NotFoundAppError("Run", run_id)
            # The parent Run row is the serialization lock for Final Feedback. A locking
            # read of the feedback row would invert the Learning Worker lock order
            # (feedback -> candidate FK to run) and can deadlock with this path
            # (run -> feedback). A consistent read is sufficient under the parent lock;
            # the generated unique guard remains the final database-level safeguard.
            if final_feedback_for_run(session, run_id) is not None:
                raise ConflictAppError(
                    "동일 Revision에는 Final Feedback을 한 번만 제출할 수 있습니다.", {"runId": run_id}
                )
            interpretation = interpret_feedback(
                request.text, request.scope, request.scenario_key, request.parameter_code
            )
            adjustment = interpretation if interpretation.get("interpreted") else None
            inherited_adjustments = parent.normalized_input_json.get("appliedAdjustments", [])
            if not isinstance(inherited_adjustments, list):
                inherited_adjustments = []
            applied_adjustments = [item for item in inherited_adjustments if isinstance(item, dict)]
            if adjustment is not None:
                applied_adjustments.append({**adjustment, "source": "final_feedback"})
            metadata = RunMetadata.model_validate(parent.metadata_json)
            runtime_seed = seed_for_snapshot(session, parent.asset_snapshot_json, orchestrator.seed)
            pipeline_result = PipelineOrchestrator(runtime_seed).run(
                metadata,
                parent.source_scenario_json,
                parent.clarification_answers_json,
                parent.asset_snapshot_json,
                applied_adjustments,
            )
            child = create_run(
                session,
                metadata,
                parent.source_scenario_json,
                parent.clarification_answers_json,
                parent.asset_snapshot_json,
                pipeline_result,
                parent_run=parent,
            )
            feedback = Feedback(
                feedback_id=str(uuid.uuid4()),
                run_id=parent.run_id,
                result_run_id=child.run_id,
                tag="final",
                source="result_review",
                scope=request.scope,
                raw_text=request.text,
                context_json=build_feedback_context(
                    session, parent, request.scope, request.scenario_key, request.parameter_code
                ),
                answer_json={},
                interpretation_json=interpretation,
                adjustment_json=adjustment or {},
                processing_status="pending",
            )
            session.add(feedback)
            session.flush()
            child_detail = run_detail(session, child)
            response = {"feedback": feedback_to_dict(feedback), "resultRun": child_detail, "newRun": child_detail}
        return response
    except IntegrityError as exc:
        session.rollback()
        raise ConflictAppError(
            "동일 Revision에는 Final Feedback을 한 번만 제출할 수 있습니다.", {"runId": run_id}
        ) from exc
