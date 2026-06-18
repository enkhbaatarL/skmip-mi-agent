from __future__ import annotations

import json

import httpx

from apps.common.logging.decorators import log_connector
from apps.common.logging.logger_config import logger
from apps.common.values.response import CallBackBody
from apps.connectors.callback.oauth2_token_manager import get_token_manager


@log_connector(connector_type="CALLBACK", log_input=True, log_output=True)
async def send_callback(url: str, payload: CallBackBody) -> None:
    """콜백 URL로 payload를 POST한다.

    흐름:
      1. 캐시된 토큰(또는 신규 발급)으로 요청
      2. 401 응답 → 토큰 강제 재발급 후 1회 재시도
      3. 재시도 후에도 실패하면 예외 발생
    """
    from apps.common.configs.settings import get_settings

    cfg = get_settings()
    token_manager = get_token_manager()
    body = payload.model_dump(by_alias=True, mode="json")
    logger.debug(
        "[CONNECTOR][CALLBACK][send_callback] REQUEST BODY\n"
        f"url={url}\n"
        f"body=\n{json.dumps(body, ensure_ascii=False, indent=2, default=str)}"
    )

    token = await token_manager.get_token()

    async with httpx.AsyncClient(verify=cfg.http_verify, timeout=30.0) as client:
        resp = await client.post(
            url,
            json=body,
            headers={"Authorization": f"Bearer {token}"},
        )

    if resp.status_code == 401:
        logger.warning(f"[CONNECTOR][CALLBACK] 401 detected, refreshing token | url={url}")
        token = await token_manager.refresh_token()
        async with httpx.AsyncClient(verify=cfg.http_verify, timeout=30.0) as client:
            resp = await client.post(
                url,
                json=body,
                headers={"Authorization": f"Bearer {token}"},
            )

    resp.raise_for_status()
    logger.debug(f"[CONNECTOR][CALLBACK] Response | url={url} | status={resp.status_code}")
