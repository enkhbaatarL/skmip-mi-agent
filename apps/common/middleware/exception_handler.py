from http import HTTPStatus

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError, WebSocketRequestValidationError
from fastapi.responses import JSONResponse

from apps.common.exceptions.custom import MIBaseError
from apps.common.logging.logger_config import logger
from apps.common.values.error_codes import ErrorCode
from apps.common.values.response import CommonResponse


def _request_info(request: Request) -> str:
    client_host = request.client.host if request.client else "-"
    return f"{request.method} {request.url.path} (client={client_host})"


def _resolve_status_code(exc: MIBaseError) -> HTTPStatus | int:
    return exc.status_code


def _mi_error_response(exc: MIBaseError) -> JSONResponse:
    response = CommonResponse(
        status="error",
        message=exc.error_message,
        data={
            "error_code": exc.code,
            "error_name": exc.error_code.name,
        },
    )
    return JSONResponse(
        status_code=_resolve_status_code(exc),
        content=response.model_dump(),
    )


def register_exception_handlers(app: FastAPI) -> FastAPI:
    @app.exception_handler(HTTPException)
    async def custom_http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        logger.info(f"HTTPException | request={_request_info(request)} | detail={exc.detail}")
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        logger.info(f"RequestValidationError | request={_request_info(request)} | errors={exc.errors()}")
        return JSONResponse(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            content=jsonable_encoder({"detail": exc.errors()}),
        )

    @app.exception_handler(WebSocketRequestValidationError)
    async def websocket_request_validation_exception_handler(
        request: Request,
        exc: WebSocketRequestValidationError,
    ) -> JSONResponse:
        logger.error(f"WebSocketRequestValidationError | request={_request_info(request)} | errors={exc.errors()}")
        return JSONResponse(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            content=jsonable_encoder({"detail": exc.errors()}),
        )

    @app.exception_handler(MIBaseError)
    async def mi_base_exception_handler(request: Request, exc: MIBaseError) -> JSONResponse:
        logger.error(f"MIBaseError | request={_request_info(request)} | error={exc!r}")
        return _mi_error_response(exc)

    @app.exception_handler(Exception)
    async def undefined_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        managed_exc = MIBaseError(ErrorCode.UNKNOWN_ERROR, detail=str(exc))
        logger.exception(f"Unhandled Exception | request={_request_info(request)} | error={exc!r}")
        return _mi_error_response(managed_exc)

    return app
