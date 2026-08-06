from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from sqlalchemy.exc import SQLAlchemyError

from app.api.router import api_router
from app.config import get_settings
from app.db import check_database, get_session_factory
from app.errors import AppError
from app.persistence.asset_repository import asset_snapshot, missing_runtime_assets


class PayloadLimitMiddleware:
    def __init__(self, app: Callable[..., Awaitable[None]], max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(
        self,
        scope: dict[str, Any],
        receive: Callable[..., Awaitable[dict[str, Any]]],
        send: Callable[..., Awaitable[None]],
    ) -> None:
        if scope.get("type") == "http" and scope.get("method") in {"POST", "PUT", "PATCH"}:
            headers = dict(scope.get("headers", []))
            content_length = headers.get(b"content-length")
            if content_length and int(content_length) > self.max_bytes:
                response = JSONResponse(
                    status_code=413,
                    content={
                        "code": "PAYLOAD_TOO_LARGE",
                        "message": "요청 Payload가 허용 크기를 초과했습니다.",
                        "details": {"maxBytes": self.max_bytes},
                        "requestId": str(uuid.uuid4()),
                    },
                )
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


settings = get_settings()
app = FastAPI(
    title="LNG Scenario-to-Parameter Learning Agent",
    version="0.1.0",
    description="Deterministic mock main pipeline and separately operated learning worker",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(PayloadLimitMiddleware, max_bytes=settings.payload_limit_bytes)
app.include_router(api_router)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next: Callable[[Request], Awaitable[Any]]) -> Any:
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(AppError)
async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "message": exc.message,
            "details": exc.details,
            "requestId": getattr(request.state, "request_id", str(uuid.uuid4())),
        },
    )


@app.exception_handler(RequestValidationError)
async def handle_request_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "code": "REQUEST_VALIDATION_ERROR",
            "message": "요청 Body 또는 Query가 유효하지 않습니다.",
            "details": {"errors": jsonable_encoder(exc.errors())},
            "requestId": getattr(request.state, "request_id", str(uuid.uuid4())),
        },
    )


@app.exception_handler(SQLAlchemyError)
async def handle_database_error(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.exception("Database operation failed: {}", exc)
    return JSONResponse(
        status_code=500,
        content={
            "code": "DATABASE_ERROR",
            "message": "Database 작업 중 오류가 발생했습니다.",
            "details": {},
            "requestId": getattr(request.state, "request_id", str(uuid.uuid4())),
        },
    )


@app.get("/health")
def health(response: Response) -> dict[str, Any]:
    database_ready = check_database()
    assets: dict[str, Any] = {}
    missing_assets: list[str] = []
    if database_ready:
        session = get_session_factory()()
        try:
            assets = asset_snapshot(session)
            missing_assets = missing_runtime_assets(assets)
        finally:
            session.close()
    ready = database_ready and not missing_assets
    if not ready:
        response.status_code = 503
    return {
        "status": "ok" if ready else "degraded",
        "mode": settings.agent_mode,
        "database": {"status": "connected" if database_ready else "unavailable", "dialect": "mysql"},
        "assets": assets,
        "assetsReady": not missing_assets,
        "missingAssets": missing_assets,
        "mainPipeline": "api",
        "learningPipeline": "separate_worker",
    }
