from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import NotFoundAppError
from app.persistence.feedback_repository import get_feedback, list_feedback, pending_counts
from app.persistence.run_repository import feedback_to_dict

router = APIRouter(tags=["feedback"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/feedback")
def get_feedback_ledger(
    session: DbSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100, alias="pageSize"),
    tag: str | None = None,
    source: str | None = None,
    processing_status: str | None = Query(default=None, alias="processingStatus"),
) -> dict[str, object]:
    rows, total = list_feedback(session, page, page_size, tag, source, processing_status)
    return {
        "items": [feedback_to_dict(item) for item in rows],
        "total": total,
        "page": page,
        "pageSize": page_size,
        "pendingCounts": pending_counts(session),
    }


@router.get("/feedback/{feedback_id}")
def get_feedback_detail(feedback_id: str, session: DbSession) -> dict[str, object]:
    row = get_feedback(session, feedback_id)
    if row is None:
        raise NotFoundAppError("Feedback", feedback_id)
    return feedback_to_dict(row)
