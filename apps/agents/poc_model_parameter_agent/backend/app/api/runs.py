from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import NotFoundAppError
from app.persistence.run_repository import get_run, list_runs, run_detail, run_summary
from app.pipeline.orchestrator import PipelineOrchestrator
from app.schemas.pipeline import FinalFeedbackRequest, RunRequest
from app.services.feedback_service import submit_final_feedback
from app.services.run_service import create_new_run

router = APIRouter(tags=["runs"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post("/runs", status_code=201)
def create_run(request: RunRequest, session: DbSession) -> dict[str, object]:
    return create_new_run(session, request, PipelineOrchestrator())


@router.get("/runs")
def get_runs(
    session: DbSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100, alias="pageSize"),
) -> dict[str, object]:
    rows, total = list_runs(session, page, page_size)
    return {"items": [run_summary(session, item) for item in rows], "total": total, "page": page, "pageSize": page_size}


@router.get("/runs/{run_id}")
def get_run_detail(run_id: str, session: DbSession) -> dict[str, object]:
    row = get_run(session, run_id)
    if row is None:
        raise NotFoundAppError("Run", run_id)
    return run_detail(session, row)


@router.post("/runs/{run_id}/feedback", status_code=201)
def create_final_feedback(
    run_id: str,
    request: FinalFeedbackRequest,
    session: DbSession,
) -> dict[str, object]:
    return submit_final_feedback(session, run_id, request, PipelineOrchestrator())
