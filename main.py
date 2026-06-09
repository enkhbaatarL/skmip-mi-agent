from __future__ import annotations

from http import HTTPStatus

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError, WebSocketRequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from apps.agents.scenario_group_agent.api import router as scenario_group_router
from apps.common.exceptions.custom import MIBaseError, UnknownMIError
from apps.common.logging.logger_config import logger


app = FastAPI(title="SKMIP MI Agent API")

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _request_info(request: Request) -> str:
    client_host = request.client.host if request.client else "-"
    return f"{request.method} {request.url.path} (client={client_host})"


def _resolve_status_code(exc: MIBaseError) -> HTTPStatus | int:
    return exc.status_code or HTTPStatus.INTERNAL_SERVER_ERROR


def _mi_error_response(exc: MIBaseError) -> JSONResponse:
    return JSONResponse(
        status_code=_resolve_status_code(exc),
        content={
            "error_code": exc.code,
            "error_name": exc.error_code.name,
            "error_message": exc.error_message,
        },
    )


def set_global_exception_handlers(app: FastAPI) -> FastAPI:
    @app.exception_handler(HTTPException)
    async def custom_http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        logger.info(f"HTTPException | request={_request_info(request)} | detail={exc.detail}")
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        logger.info(f"RequestValidationError | request={_request_info(request)} | errors={exc.errors()}")
        return JSONResponse(status_code=HTTPStatus.UNPROCESSABLE_ENTITY, content={"detail": exc.errors()})

    @app.exception_handler(WebSocketRequestValidationError)
    async def websocket_request_validation_exception_handler(
        request: Request,
        exc: WebSocketRequestValidationError,
    ) -> JSONResponse:
        logger.error(f"WebSocketRequestValidationError | request={_request_info(request)} | errors={exc.errors()}")
        return JSONResponse(status_code=HTTPStatus.UNPROCESSABLE_ENTITY, content={"detail": exc.errors()})

    @app.exception_handler(MIBaseError)
    async def mi_base_exception_handler(request: Request, exc: MIBaseError) -> JSONResponse:
        logger.error(f"MIBaseError | request={_request_info(request)} | error={exc!r}")
        return _mi_error_response(exc)

    @app.exception_handler(Exception)
    async def undefined_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        managed_exc = UnknownMIError(detail=str(exc))
        logger.exception(f"Unhandled Exception | request={_request_info(request)} | error={exc!r}")
        return _mi_error_response(managed_exc)

    return app


app.include_router(
    scenario_group_router,
    prefix="",
    tags=["scenario-group"],
)

app = set_global_exception_handlers(app)
