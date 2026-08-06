from __future__ import annotations

from fastapi import APIRouter

from app.api.assets import router as assets_router
from app.api.examples import router as examples_router
from app.api.feedback import router as feedback_router
from app.api.learning import router as learning_router
from app.api.plans import router as plans_router
from app.api.runs import router as runs_router

api_router = APIRouter(prefix="/api")
api_router.include_router(examples_router)
api_router.include_router(plans_router)
api_router.include_router(runs_router)
api_router.include_router(feedback_router)
api_router.include_router(learning_router)
api_router.include_router(assets_router)
