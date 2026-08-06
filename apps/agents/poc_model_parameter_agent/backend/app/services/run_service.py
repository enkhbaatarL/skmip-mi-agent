from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.learning.memory_rules import (
    MEMORY_RULE_MARKER,
    apply_clarification_defaults,
    parse_embedded_rules,
)
from app.persistence.asset_repository import asset_snapshot, seed_for_snapshot
from app.persistence.run_repository import create_run, run_detail
from app.pipeline.orchestrator import PipelineOrchestrator
from app.schemas.pipeline import RunRequest
from app.services.feedback_service import create_interim_feedback, interpret_feedback


def _active_memory_adjustments(memory_content: str) -> list[dict[str, Any]]:
    adjustments: list[dict[str, Any]] = []
    embedded = parse_embedded_rules(memory_content, MEMORY_RULE_MARKER)
    for rule in embedded:
        if rule.get("kind") == "adjustment" and isinstance(rule.get("adjustment"), dict):
            adjustments.append({**rule["adjustment"], "source": "active_memory"})
            continue
        if rule.get("kind") != "preference":
            continue
        context = rule.get("context") if isinstance(rule.get("context"), dict) else {}
        learned = interpret_feedback(
            str(rule.get("instruction", "")),
            str(context.get("scope") or "run"),
            context.get("scenarioKey"),
            context.get("focusParameter"),
        )
        if learned.get("interpreted"):
            adjustments.append({**learned, "source": "active_memory"})

    if not embedded:
        for line in memory_content.splitlines():
            prefix = "- 사용자 검토 선호:"
            if not line.startswith(prefix):
                continue
            learned = interpret_feedback(line.removeprefix(prefix).strip(), "run", None, None)
            if learned.get("interpreted"):
                adjustments.append({**learned, "source": "active_memory_legacy"})
    return adjustments


def create_new_run(session: Session, request: RunRequest, orchestrator: PipelineOrchestrator) -> dict[str, Any]:
    with session.begin():
        snapshot = asset_snapshot(session)
        runtime_seed = seed_for_snapshot(session, snapshot, orchestrator.seed)
        runtime_orchestrator = PipelineOrchestrator(runtime_seed)
        effective_answers = apply_clarification_defaults(
            runtime_seed.memory_v2,
            request.clarification_answers,
        )
        instruction = request.clarification_answers.get("additional_instruction")
        if isinstance(instruction, dict):
            instruction_text = str(instruction.get("text") or instruction.get("value") or "")
        else:
            instruction_text = str(instruction or "")
        interpreted = interpret_feedback(instruction_text, "run", None, None) if instruction_text else None
        explicit_adjustment = interpreted if interpreted and interpreted.get("interpreted") else None
        adjustments = _active_memory_adjustments(runtime_seed.memory_v2)
        if explicit_adjustment is not None:
            adjustments.append({**explicit_adjustment, "source": "interim_feedback"})
        pipeline_result = runtime_orchestrator.run(
            request.metadata,
            request.scenario_json,
            effective_answers,
            snapshot,
            adjustments,
        )
        row = create_run(
            session,
            request.metadata,
            request.scenario_json,
            effective_answers,
            snapshot,
            pipeline_result,
        )
        create_interim_feedback(session, row, request.clarification_answers, explicit_adjustment)
        return run_detail(session, row)
