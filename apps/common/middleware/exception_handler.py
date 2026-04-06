from http import HTTPStatus

from fastapi import Request
from fastapi.responses import JSONResponse

from apps.common.exceptions.custom import MIBaseError


# 필요시 FASTAPI 앱에 핸들러 등록하여 사용(현재는 jupyter notebook환경에서 Langraph기반 Agent로 구동중)
async def mi_exception_handler(request: Request, exc: MIBaseError) -> JSONResponse:
    return JSONResponse(
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        content={
            "error_code": exc.error_code,
            "error_message": exc.error_message,
        },
    )
