from __future__ import annotations

import json
from typing import Literal

import httpx
from pydantic import BaseModel

from apps.common.exceptions.custom import MIBaseError
from apps.common.logging.decorators import log_connector
from apps.common.logging.logger_config import logger
from apps.common.values.error_codes import ErrorCode
from apps.connectors.callback.oauth2_token_manager import get_token_manager


CallbackDeliveryStage = Literal["token", "post"]


def _delivery_error(stage: CallbackDeliveryStage, url: str, exc: Exception) -> MIBaseError:
    status_code = exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else None
    return MIBaseError(
        ErrorCode.CALLBACK_DELIVERY_FAILED,
        detail=f"stage={stage} | url={url} | status_code={status_code} | error={exc!r}",
        context={"stage": stage, "url": url, "status_code": status_code},
    )


@log_connector(connector_type="CALLBACK", log_input=True, log_output=True)
async def send_callback(url: str, payload: BaseModel) -> None:
    """콜백 URL로 payload를 POST한다.

    흐름:
      1. 캐시된 토큰(또는 신규 발급)으로 요청
      2. 401 응답 → 토큰 강제 재발급 후 1회 재시도
      3. 재시도 후에도 실패하면 CALLBACK_DELIVERY_FAILED 예외 발생 (context.stage=token|post)
    """
    from apps.common.configs.config import get_settings

    cfg = get_settings()
    body = payload.model_dump(by_alias=True, mode="json")
    logger.debug(
        "[CONNECTOR][CALLBACK][send_callback] REQUEST BODY\n"
        f"url={url}\n"
        f"body=\n{json.dumps(body, ensure_ascii=False, indent=2, default=str)}"
    )

    if cfg.skip_callback:
        logger.info(f"[CONNECTOR][CALLBACK][send_callback] SKIPPED (skip_callback=true) | url={url}")
        return

    token_manager = get_token_manager()
    try:
        token = await token_manager.get_token()
    except Exception as exc:
        raise _delivery_error("token", url, exc) from exc

    try:
        async with httpx.AsyncClient(verify=cfg.http_verify, timeout=30.0) as client:
            resp = await client.post(
                url,
                json=body,
                headers={"Authorization": f"Bearer {token}"},
            )
    except httpx.HTTPError as exc:
        raise _delivery_error("post", url, exc) from exc

    if resp.status_code == 401:
        logger.warning(f"[CONNECTOR][CALLBACK] 401 detected, refreshing token | url={url}")
        try:
            token = await token_manager.refresh_token()
        except Exception as exc:
            raise _delivery_error("token", url, exc) from exc
        try:
            async with httpx.AsyncClient(verify=cfg.http_verify, timeout=30.0) as client:
                resp = await client.post(
                    url,
                    json=body,
                    headers={"Authorization": f"Bearer {token}"},
                )
        except httpx.HTTPError as exc:
            raise _delivery_error("post", url, exc) from exc

    try:
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise _delivery_error("post", url, exc) from exc
    logger.debug(f"[CONNECTOR][CALLBACK] Response | url={url} | status={resp.status_code}")
