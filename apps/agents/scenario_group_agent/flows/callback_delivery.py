from __future__ import annotations

import asyncio

from apps.agents.scenario_group_agent.persistence.scenario_group_operation_service import (
    ScenarioGroupOperationService,
)
from apps.common.logging.logger_config import logger
from apps.common.values.response import CallBackBody
from apps.connectors.callback.callback_client import send_callback
from apps.persistence.scenario_group_operation.schema import CallbackDeliveryStatus


async def deliver_operation_callback(
    *,
    log_tag: str,
    callback_url: str,
    payload: CallBackBody,
    scenario_group_id: int,
    operation_id: str | None,
) -> None:
    """작업 결과가 확정된 payload를 1회 전송하고, operation이 있으면 전송 결과를 이력에 남긴다.

    전송 실패가 반대 결과(failure) callback으로 이어지지 않도록 예외를 밖으로 전파하지 않는다.
    """
    from apps.common.configs.config import get_settings

    callback_status: CallbackDeliveryStatus
    error: Exception | None = None
    try:
        await send_callback(callback_url, payload)
        callback_status = "SKIPPED" if get_settings().skip_callback else "SUCCEEDED"
        logger.info(
            f"[BG][{log_tag}] CALLBACK_DONE | group_id={scenario_group_id} "
            f"| result={payload.result} | callback_status={callback_status}",
        )
    except Exception as exc:
        callback_status = "FAILED"
        error = exc
        logger.error(
            f"[BG][{log_tag}] CALLBACK_FAILED | group_id={scenario_group_id} "
            f"| result={payload.result} | error={exc!r}",
        )

    if operation_id is None:
        return
    try:
        await asyncio.to_thread(
            ScenarioGroupOperationService().record_callback_delivery,
            scenario_group_id,
            operation_id,
            callback_status=callback_status,
            result=payload.result,
            error=error,
        )
    except Exception as record_exc:
        logger.error(
            f"[BG][{log_tag}] CALLBACK_RECORD_FAILED | group_id={scenario_group_id} "
            f"| operation_id={operation_id} | callback_status={callback_status} | error={record_exc!r}",
        )
