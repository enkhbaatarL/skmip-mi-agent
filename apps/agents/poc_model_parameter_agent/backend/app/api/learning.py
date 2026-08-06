from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import NotFoundAppError
from app.models import Feedback, LearningCandidate
from app.persistence.learning_repository import (
    batch_to_dict,
    candidate_to_dict,
    get_batch,
    get_candidate,
    list_batches,
    list_candidates,
)
from app.persistence.run_repository import feedback_to_dict
from app.schemas.pipeline import ReviewRequest
from app.services.learning_service import approve_candidate, process_pending, reject_candidate

router = APIRouter(tags=["learning"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/learning/batches")
def get_batches(
    session: DbSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100, alias="pageSize"),
) -> dict[str, object]:
    rows, total = list_batches(session, page, page_size)
    return {"items": [batch_to_dict(item) for item in rows], "total": total, "page": page, "pageSize": page_size}


@router.get("/learning/batches/{batch_id}")
def get_batch_detail(batch_id: str, session: DbSession) -> dict[str, object]:
    row = get_batch(session, batch_id)
    if row is None:
        raise NotFoundAppError("Learning Batch", batch_id)
    candidates = list(session.scalars(select(LearningCandidate).where(LearningCandidate.batch_id == batch_id)))
    return {**batch_to_dict(row), "candidates": [candidate_to_dict(item) for item in candidates]}


@router.get("/learning/candidates")
def get_candidates(
    session: DbSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100, alias="pageSize"),
    status: str | None = None,
) -> dict[str, object]:
    rows, total = list_candidates(session, page, page_size, status)
    return {"items": [candidate_to_dict(item) for item in rows], "total": total, "page": page, "pageSize": page_size}


@router.get("/learning/candidates/{candidate_id}")
def get_candidate_detail(candidate_id: str, session: DbSession) -> dict[str, object]:
    row = get_candidate(session, candidate_id)
    if row is None:
        raise NotFoundAppError("Candidate", candidate_id)
    feedback = session.scalar(select(Feedback).where(Feedback.feedback_id == row.source_feedback_id))
    return {**candidate_to_dict(row), "sourceFeedback": feedback_to_dict(feedback) if feedback else None}


@router.post("/learning/process-pending")
def run_learning_cycle(session: DbSession) -> dict[str, object]:
    return process_pending(session)


@router.post("/learning/candidates/{candidate_id}/approve")
def approve(candidate_id: str, request: ReviewRequest, session: DbSession) -> dict[str, object]:
    return approve_candidate(session, candidate_id, request.reviewer_note)


@router.post("/learning/candidates/{candidate_id}/reject")
def reject(candidate_id: str, request: ReviewRequest, session: DbSession) -> dict[str, object]:
    return reject_candidate(session, candidate_id, request.reviewer_note)
