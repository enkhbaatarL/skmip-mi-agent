from __future__ import annotations

from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models import LearningBatch, LearningCandidate


def get_batch(session: Session, batch_id: str) -> LearningBatch | None:
    return session.scalar(select(LearningBatch).where(LearningBatch.batch_id == batch_id))


def list_batches(session: Session, page: int, page_size: int) -> tuple[list[LearningBatch], int]:
    total = int(session.scalar(select(func.count()).select_from(LearningBatch)) or 0)
    rows = list(
        session.scalars(
            select(LearningBatch)
            .order_by(LearningBatch.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return rows, total


def get_candidate(session: Session, candidate_id: str, for_update: bool = False) -> LearningCandidate | None:
    statement = select(LearningCandidate).where(LearningCandidate.candidate_id == candidate_id)
    if for_update:
        statement = statement.with_for_update()
    return session.scalar(statement)


def candidate_by_fingerprint(session: Session, fingerprint: str) -> LearningCandidate | None:
    return session.scalar(
        select(LearningCandidate).where(
            LearningCandidate.fingerprint == fingerprint,
            LearningCandidate.status.in_(["pending", "approved", "applied"]),
        )
    )


def list_candidates(
    session: Session, page: int, page_size: int, status: str | None = None
) -> tuple[list[LearningCandidate], int]:
    filters = [LearningCandidate.status == status] if status else []
    total = int(session.scalar(select(func.count()).select_from(LearningCandidate).where(*filters)) or 0)
    status_order = case((LearningCandidate.status == "pending", 0), else_=1)
    rows = list(
        session.scalars(
            select(LearningCandidate)
            .where(*filters)
            .order_by(status_order, LearningCandidate.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return rows, total


def batch_to_dict(row: LearningBatch) -> dict[str, Any]:
    return {
        "batchId": row.batch_id,
        "createdAt": row.created_at.isoformat(),
        "feedbackIds": row.feedback_ids_json,
        "interimCount": row.interim_count,
        "finalCount": row.final_count,
        "status": row.status,
        "reviewerMode": row.reviewer_mode,
        "candidateCount": row.candidate_count,
        "classificationSummary": row.classification_summary_json,
        "reviewSummary": row.review_summary_json,
        "error": row.error,
    }


def candidate_to_dict(row: LearningCandidate) -> dict[str, Any]:
    return {
        "candidateId": row.candidate_id,
        "batchId": row.batch_id,
        "sourceFeedbackId": row.source_feedback_id,
        "sourceRunId": row.source_run_id,
        "sourceTag": row.source_tag,
        "sourceContext": row.source_context_json,
        "targetType": row.target_type,
        "targetAssetKey": row.target_asset_key,
        "baseVersion": row.base_version,
        "proposedVersion": row.proposed_version,
        "proposedContent": row.proposed_content,
        "changeLine": row.change_line,
        "diff": row.diff_text,
        "classification": row.classification,
        "matchedSignals": row.matched_signals_json,
        "rationale": row.rationale,
        "confidence": row.confidence,
        "evaluation": row.evaluation_json,
        "risks": row.risks_json,
        "expectedImpact": row.expected_impact,
        "status": row.status,
        "reviewerNote": row.reviewer_note,
        "reviewedAt": row.reviewed_at.isoformat() if row.reviewed_at else None,
        "createdAt": row.created_at.isoformat(),
    }
