from __future__ import annotations

import hashlib
import json
import uuid
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.errors import ConflictAppError, NotFoundAppError, ValidationAppError
from app.learning.classifier import classify_feedback
from app.learning.diff import append_learning_line
from app.learning.evaluator import evaluate_candidate
from app.learning.memory_rules import learning_rule_payload
from app.models import AssetVersion, Feedback, LearningBatch, LearningCandidate
from app.persistence.asset_repository import asset_to_dict, get_active_asset
from app.persistence.feedback_repository import claim_pending_feedback
from app.persistence.learning_repository import (
    candidate_by_fingerprint,
    candidate_to_dict,
    get_candidate,
)
from app.seed import stable_content_hash


def _fingerprint(target_type: str, target_key: str, base_version: int, proposed_content: str) -> str:
    normalized = json.dumps(
        {
            "targetType": target_type,
            "targetKey": target_key,
            "baseVersion": base_version,
            "proposedContent": " ".join(proposed_content.split()),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _mark_feedback_failure(feedback: Feedback, error: str) -> None:
    feedback.last_error = error
    if feedback.attempt_count >= get_settings().worker_max_attempts:
        feedback.processing_status = "failed"
        feedback.next_retry_at = None
        return
    feedback.processing_status = "retry"
    delay_seconds = min(get_settings().worker_retry_max_seconds, 2 ** max(0, feedback.attempt_count - 1))
    feedback.next_retry_at = datetime.now(UTC) + timedelta(seconds=delay_seconds)


def _process_pending_once(session: Session, batch_size: int, claimed_ids: list[str]) -> dict[str, Any]:
    with session.begin():
        feedback_rows = claim_pending_feedback(session, batch_size)
        if not feedback_rows:
            return {"status": "idle", "processed": 0, "candidateCount": 0, "batchId": None}
        claimed_ids.extend(item.feedback_id for item in feedback_rows)
        batch = LearningBatch(
            batch_id=str(uuid.uuid4()),
            status="processing",
            reviewer_mode=get_settings().agent_mode,
            feedback_ids_json=[item.feedback_id for item in feedback_rows],
            interim_count=sum(item.tag == "interim" for item in feedback_rows),
            final_count=sum(item.tag == "final" for item in feedback_rows),
            candidate_count=0,
            classification_summary_json={},
            review_summary_json={},
        )
        session.add(batch)
        session.flush()
        classifications: Counter[str] = Counter()
        created_candidates: list[LearningCandidate] = []
        batch_fingerprints: set[str] = set()
        duplicate_count = 0
        for feedback in feedback_rows:
            classification = classify_feedback(feedback.raw_text, feedback.source, feedback.answer_json)
            kind = classification["classification"]
            classifications[kind] += 1
            feedback.learning_batch_id = batch.batch_id
            feedback.processing_status = "processed"
            feedback.attempt_count += 1
            if kind == "no_candidate":
                continue
            target_type = kind
            target_key = "default_memory" if kind == "memory" else "scenario_parameter_skill"
            active = get_active_asset(session, target_type, target_key, for_update=True)
            if active is None or active.content_text is None:
                _mark_feedback_failure(feedback, f"Active {target_type}:{target_key} asset이 없습니다.")
                feedback.learning_batch_id = None
                continue
            rule_payload = learning_rule_payload(
                kind,
                feedback.raw_text,
                feedback.context_json,
                feedback.answer_json,
                feedback.adjustment_json,
            )
            proposed, change_line, diff_text = append_learning_line(
                active.content_text,
                kind,
                feedback.raw_text,
                rule_payload,
            )
            fingerprint = _fingerprint(target_type, target_key, active.version, proposed)
            # Sessions intentionally disable autoflush, so candidates accumulated earlier in
            # this transaction are not visible to the repository query yet. Track them locally
            # as well as checking the database-backed uniqueness guard.
            duplicate = fingerprint in batch_fingerprints or candidate_by_fingerprint(session, fingerprint) is not None
            evaluation = evaluate_candidate(
                kind,
                target_type,
                active.content_text,
                proposed,
                feedback.feedback_id,
                duplicate,
            )
            if duplicate:
                duplicate_count += 1
                continue
            candidate = LearningCandidate(
                candidate_id=str(uuid.uuid4()),
                batch_id=batch.batch_id,
                source_feedback_id=feedback.feedback_id,
                source_run_id=feedback.run_id,
                source_tag=feedback.tag,
                source_context_json=feedback.context_json,
                target_type=target_type,
                target_asset_key=target_key,
                base_version=active.version,
                proposed_version=active.version + 1,
                proposed_content=proposed,
                change_line=change_line,
                diff_text=diff_text,
                classification=kind,
                matched_signals_json=classification["matchedSignals"],
                rationale=classification["rationale"],
                confidence=classification["confidence"],
                evaluation_json=evaluation,
                risks_json=["단일 관측 기반 Candidate"] if feedback.tag == "interim" else ["승인 전 회귀 검토 필요"],
                expected_impact="다음 신규 Run의 Asset Snapshot부터 반복 가능한 사용자 지침을 반영합니다.",
                status="pending",
                fingerprint=fingerprint,
            )
            session.add(candidate)
            created_candidates.append(candidate)
            batch_fingerprints.add(fingerprint)
        batch.status = "completed"
        batch.candidate_count = len(created_candidates)
        batch.classification_summary_json = dict(classifications)
        batch.review_summary_json = {
            "processed": len(feedback_rows),
            "created": len(created_candidates),
            "duplicatesSkipped": duplicate_count,
            "automaticApproval": False,
        }
        session.flush()
        return {
            "status": batch.status,
            "processed": len(feedback_rows),
            "candidateCount": len(created_candidates),
            "duplicatesSkipped": duplicate_count,
            "batchId": batch.batch_id,
            "candidateIds": [item.candidate_id for item in created_candidates],
        }


def process_pending(session: Session, limit: int | None = None) -> dict[str, Any]:
    batch_size = min(limit or get_settings().worker_batch_size, 100)
    claimed_ids: list[str] = []
    try:
        return _process_pending_once(session, batch_size, claimed_ids)
    except Exception as exc:
        session.rollback()
        if claimed_ids:
            with session.begin():
                feedback_rows = list(
                    session.scalars(
                        select(Feedback)
                        .where(
                            Feedback.feedback_id.in_(claimed_ids),
                            Feedback.learning_batch_id.is_(None),
                            Feedback.processing_status.in_(["pending", "retry"]),
                        )
                        .with_for_update(skip_locked=True)
                    )
                )
                for feedback in feedback_rows:
                    feedback.attempt_count += 1
                    _mark_feedback_failure(feedback, str(exc))
                if feedback_rows:
                    session.add(
                        LearningBatch(
                            batch_id=str(uuid.uuid4()),
                            status="failed",
                            reviewer_mode=get_settings().agent_mode,
                            feedback_ids_json=[item.feedback_id for item in feedback_rows],
                            interim_count=sum(item.tag == "interim" for item in feedback_rows),
                            final_count=sum(item.tag == "final" for item in feedback_rows),
                            candidate_count=0,
                            classification_summary_json={},
                            review_summary_json={"processed": 0, "automaticApproval": False},
                            error=str(exc),
                        )
                    )
        raise


def approve_candidate(session: Session, candidate_id: str, reviewer_note: str | None) -> dict[str, Any]:
    try:
        with session.begin():
            candidate = get_candidate(session, candidate_id, for_update=True)
            if candidate is None:
                raise NotFoundAppError("Candidate", candidate_id)
            if candidate.status != "pending":
                raise ConflictAppError("Pending Candidate만 승인할 수 있습니다.", {"status": candidate.status})
            if candidate.target_type not in {"memory", "skill"}:
                raise ValidationAppError("Memory와 Skill Candidate만 승인할 수 있습니다.")
            evaluation = candidate.evaluation_json
            if not isinstance(evaluation, dict) or evaluation.get("allPassed") is not True:
                raise ValidationAppError(
                    "모든 Candidate Evaluation을 통과한 경우에만 승인할 수 있습니다.",
                    {"candidateId": candidate_id, "evaluation": evaluation, "assetUnchanged": True},
                )
            active = get_active_asset(session, candidate.target_type, candidate.target_asset_key, for_update=True)
            if active is None:
                raise ConflictAppError("Active Asset이 없습니다.")
            if not active.learnable or active.locked:
                raise ConflictAppError(
                    "잠금 상태이거나 학습 불가능한 Asset은 변경할 수 없습니다.",
                    {
                        "candidateId": candidate_id,
                        "learnable": active.learnable,
                        "locked": active.locked,
                        "assetUnchanged": True,
                    },
                )
            if active.version != candidate.base_version:
                raise ConflictAppError(
                    "Candidate Base Version과 현재 Active Version이 일치하지 않습니다.",
                    {
                        "candidateId": candidate_id,
                        "baseVersion": candidate.base_version,
                        "activeVersion": active.version,
                        "assetUnchanged": True,
                    },
                )
            active.active = False
            session.flush()
            new_asset = AssetVersion(
                asset_version_id=str(uuid.uuid4()),
                asset_type=candidate.target_type,
                asset_key=candidate.target_asset_key,
                version=candidate.proposed_version,
                content_json=None,
                content_text=candidate.proposed_content,
                content_hash=stable_content_hash(None, candidate.proposed_content),
                learnable=True,
                locked=False,
                active=True,
                source_candidate_id=candidate.candidate_id,
            )
            session.add(new_asset)
            candidate.status = "applied"
            candidate.reviewer_note = reviewer_note
            candidate.reviewed_at = datetime.now(UTC)
            session.flush()
            result = {"candidate": candidate_to_dict(candidate), "assetVersion": asset_to_dict(new_asset)}
        return result
    except IntegrityError as exc:
        session.rollback()
        raise ConflictAppError(
            "Asset Version 활성화 충돌로 변경을 적용하지 않았습니다.", {"assetUnchanged": True}
        ) from exc


def reject_candidate(session: Session, candidate_id: str, reviewer_note: str | None) -> dict[str, Any]:
    if not reviewer_note or not reviewer_note.strip():
        raise ValidationAppError("거절 사유 reviewerNote가 필요합니다.")
    with session.begin():
        candidate = get_candidate(session, candidate_id, for_update=True)
        if candidate is None:
            raise NotFoundAppError("Candidate", candidate_id)
        if candidate.status != "pending":
            raise ConflictAppError("Pending Candidate만 거절할 수 있습니다.", {"status": candidate.status})
        candidate.status = "rejected"
        candidate.reviewer_note = reviewer_note.strip()
        candidate.reviewed_at = datetime.now(UTC)
        session.flush()
        return {"candidate": candidate_to_dict(candidate), "assetChanged": False}
