"""가격전망 해석 비동기(async) 배경 실행 초안.

현재 활성 엔드포인트는 동기 preview(`flows/interpret_price/flow.py`의
`run_interpret_price`)만 제공한다. 이 파일은 추후 "요청 즉시 접수 응답 + 백그라운드
해석 후 콜백 전송" 비동기 전달 방식이 필요해질 때 바로 붙일 수 있도록 준비해 둔
초안이다(현재 어떤 라우터에도 연결되어 있지 않음).

패턴은 scenario_group_agent의 `flow_async` 배경 작업(prepare + run_*_background +
send_callback)을 따르며, 실제 해석 로직은 이미 구현된 interpret_price 그래프
(`run_interpret_price`)를 재사용한다. 활성화 시:
  1. 엔드포인트에서 `prepare_price_interpretation`으로 입력을 검증하고 접수 응답을 반환한다.
  2. FastAPI BackgroundTasks로 `run_price_interpretation_background`를 실행한다.
  3. 결과(PriceInterpretationResult)를 콜백 URL로 POST한다.

주의: 콜백 payload 스키마(PriceInterpretationCallbackOut)는 비동기 활성화 시점에
`flows/interpret_price/api_schema.py`로 옮기는 것을 권장한다(지금은 초안 자립성을 위해
이 파일에 둔다).
"""

from __future__ import annotations

import time

from apps.agents.interpret_agent.flows.interpret_price.api_schema import (
    PriceInterpretationResult,
)
from apps.agents.interpret_agent.flows.interpret_price.flow import run_interpret_price
from apps.common.logging.logger_config import logger
from apps.common.values.response import CallBackBody


class PriceInterpretationCallbackOut(CallBackBody):
    """가격전망 해석 비동기 콜백 payload.

    성공 시 해석 결과(data)를 실어 보내고, 실패 시 result="failure" + reason만 채운다.
    (result/reason 공통 필드는 CallBackBody에서 상속)
    """

    data: PriceInterpretationResult | None = None


def prepare_price_interpretation(
    scenario_group_id: int,
    scenario_ids: list[str],
) -> dict[str, object]:
    """비동기 요청 접수 전 경량 검증 후 즉시 응답 body를 구성한다.

    현재 입력은 샘플 파일에서 로드되므로 무거운 DB 검증은 두지 않는다.
    DB 전환 시 이곳에 그룹 존재/시나리오 소속 검증을 추가한다.
    """
    return {
        "scenario_group_id": scenario_group_id,
        "scenario_ids": list(scenario_ids),
        "status": "processing",
    }


def _resolve_callback_url(scenario_group_id: int) -> str:
    from apps.common.configs.config import get_settings

    cfg = get_settings()
    callback_path = cfg.callback_price_interpretations_path.format(
        scenario_group_id=scenario_group_id,
    )
    return cfg.callback_base_url.rstrip("/") + callback_path


async def run_price_interpretation_background(
    scenario_group_id: int,
    scenario_ids: list[str] | None = None,
) -> None:
    """백그라운드에서 interpret_price 그래프를 실행하고 결과를 콜백으로 전송한다."""
    from apps.connectors.callback.callback_client import send_callback

    callback_url = _resolve_callback_url(scenario_group_id)
    start = time.perf_counter()
    logger.info(
        f"[BG][interpret_price] START | group_id={scenario_group_id} "
        f"| scenario_ids={scenario_ids}"
    )
    try:
        result = await run_interpret_price(
            scenario_group_id=scenario_group_id,
            scenario_ids=list(scenario_ids or []),
        )
        payload = PriceInterpretationCallbackOut(result="success", data=result)
        await send_callback(callback_url, payload)
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        logger.info(
            f"[BG][interpret_price] END | group_id={scenario_group_id} | elapsed={elapsed_ms}ms"
        )
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        logger.error(
            f"[BG][interpret_price] FAILED | group_id={scenario_group_id} "
            f"| elapsed={elapsed_ms}ms | error={exc!r}"
        )
        error_payload = PriceInterpretationCallbackOut(result="failure", reason=str(exc))
        try:
            await send_callback(callback_url, error_payload)
        except Exception as callback_error:
            logger.error(
                f"[BG][interpret_price] CALLBACK_FAILED | group_id={scenario_group_id} "
                f"| error={callback_error!r}"
            )
