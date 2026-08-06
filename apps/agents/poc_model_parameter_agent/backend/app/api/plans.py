from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.persistence.asset_repository import asset_snapshot, seed_for_snapshot
from app.pipeline.orchestrator import PipelineOrchestrator
from app.schemas.pipeline import PlanRequest

router = APIRouter(tags=["plans"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post("/plans")
def create_plan(request: PlanRequest, session: DbSession) -> dict[str, object]:
    snapshot = asset_snapshot(session)
    fallback_orchestrator = PipelineOrchestrator()
    runtime_seed = seed_for_snapshot(session, snapshot, fallback_orchestrator.seed)
    return PipelineOrchestrator(runtime_seed).plan(request.metadata, request.scenario_json, snapshot)
