from __future__ import annotations

import time

from apps.agents.interpret_agent.schemas.api.interpretation import (
    PriceInterpretationCallbackOut,
    PriceInterpretationItem,
)
from apps.agents.interpret_agent.schemas.enums import PriceInterpretationStatus
from apps.agents.scenario_group_agent.persistence.event.service import EventService
from apps.agents.scenario_group_agent.persistence.scenario.service import ScenarioService
from apps.agents.scenario_group_agent.persistence.scenario_group.service import (
    ScenarioGroupService,
)
from apps.common.exceptions.custom import MIBaseError
from apps.common.logging.logger_config import logger
from apps.common.values.error_codes import ErrorCode


def _load_group_or_raise(scenario_group_id: int):
    group = ScenarioGroupService().load_by_id(scenario_group_id)
    if group is None:
        raise MIBaseError(
            ErrorCode.ENTITY_NOT_FOUND,
            detail=f"Scenario group not found: scenario_group_id={scenario_group_id}",
        )
    return group


def _validate_scenario_ids(scenario_group_id: int, scenario_ids: list[int]) -> None:
    if len(set(scenario_ids)) != len(scenario_ids):
        raise MIBaseError(
            ErrorCode.INVALID_REQUEST,
            detail="scenarioIds must be unique within the request",
        )

    existing_ids = {
        int(s.scenario_id)
        for s in ScenarioService().load_by_group_id(scenario_group_id)
    }
    missing_ids = sorted(set(scenario_ids) - existing_ids)
    if missing_ids:
        raise MIBaseError(
            ErrorCode.ENTITY_NOT_FOUND,
            detail=(
                f"Scenario IDs not found in scenario_group_id={scenario_group_id}: {missing_ids}"
            ),
        )


def prepare_create_interpretation(
    scenario_group_id: int,
    scenario_ids: list[int],
) -> dict[str, object]:
    """생성 요청 접수 전 유효성 검증(그룹 존재 + 시나리오 소속 확인)."""
    _load_group_or_raise(scenario_group_id)
    _validate_scenario_ids(scenario_group_id, scenario_ids)
    return {
        "scenario_group_id": scenario_group_id,
        "scenario_ids": scenario_ids,
        "status": PriceInterpretationStatus.PROCESSING.value,
    }


def _build_interpretation_items(
    scenario_group_id: int,
    scenario_ids: list[int],
) -> list[PriceInterpretationItem]:
    group = _load_group_or_raise(scenario_group_id)
    event = EventService().load_event(int(group.mi_event_id))
    event_summary = event.one_line_summary if event is not None else ""

    db_by_id = {
        int(s.scenario_id): s
        for s in ScenarioService().load_by_group_id(scenario_group_id)
    }

    items: list[PriceInterpretationItem] = []
    for scenario_id in scenario_ids:
        db_scenario = db_by_id.get(scenario_id)
        if db_scenario is None:
            raise MIBaseError(
                ErrorCode.ENTITY_NOT_FOUND,
                detail=f"Scenario not found while building interpretation: {scenario_id}",
            )
        items.append(
            PriceInterpretationItem(
                scenario_id=scenario_id,
                content=_build_content(
                    scenario_title=db_scenario.title,
                    scenario_narrative=db_scenario.narrative,
                    event_summary=event_summary,
                ),
            )
        )
    return items


def _build_content(
    scenario_title: str,
    scenario_narrative: str,
    event_summary: str,
) -> str:
    """최신 MI 수급모델 결과 기준 가격전망 해석 원본을 생성한다.

    실제 산출 로직은 최신 수급모델(가격) 결과를 반영하여 대체된다.
    """
    lines = [f"[{scenario_title}] 가격전망 해석"]
    if event_summary:
        lines.append(f"이벤트 개요: {event_summary}")
    if scenario_narrative:
        lines.append(f"시나리오 요지: {scenario_narrative}")
    lines.append("최신 MI 수급모델 결과를 기준으로 산출된 가격전망 해석입니다.")
    return "\n".join(lines)


async def run_create_interpretation_background(
    scenario_group_id: int,
    scenario_ids: list[int],
) -> None:
    from apps.common.configs.config import get_settings

    from apps.connectors.callback.callback_client import send_callback

    cfg = get_settings()
    callback_path = cfg.callback_price_interpretations_path.format(
        scenario_group_id=scenario_group_id,
    )
    callback_url = cfg.callback_base_url.rstrip("/") + callback_path

    start = time.perf_counter()
    logger.info(
        f"[BG][interpret] START | group_id={scenario_group_id} | scenario_ids={scenario_ids}"
    )
    try:
        items = _build_interpretation_items(scenario_group_id, scenario_ids)
        payload = PriceInterpretationCallbackOut(
            result="success",
            reason=None,
            interpretations=items,
        )
        await send_callback(callback_url, payload)
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        logger.info(
            f"[BG][interpret] END | group_id={scenario_group_id} | elapsed={elapsed_ms}ms"
        )
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        logger.error(
            f"[BG][interpret] FAILED | group_id={scenario_group_id} | "
            f"elapsed={elapsed_ms}ms | error={exc!r}"
        )
        error_payload = PriceInterpretationCallbackOut(
            result="failure",
            reason=str(exc),
            interpretations=None,
        )
        try:
            await send_callback(callback_url, error_payload)
        except Exception as callback_error:
            logger.error(
                f"[BG][interpret] CALLBACK_FAILED | group_id={scenario_group_id} | "
                f"error={callback_error!r}"
            )
