from __future__ import annotations

import time
from datetime import datetime, timezone
from statistics import mean
from typing import Any
from uuid import uuid4

from apps.agents.interpret_agent.schemas.api.interpretation import (
    BaseEventOut,
    DimensionDefinitionOut,
    InterpretationCallbackData,
    InterpretationCallbackOut,
    InterpretationMetaOut,
    InterpretationResultOut,
    InterpretationScenarioIn,
    InterpretationScenarioOut,
)
from apps.agents.scenario_group_agent.persistence.event.service import EventService
from apps.agents.scenario_group_agent.persistence.scenario.service import ScenarioService
from apps.agents.scenario_group_agent.persistence.scenario_group.service import (
    ScenarioGroupService,
)
from apps.common.exceptions.custom import MIBaseError
from apps.common.logging.logger_config import logger
from apps.common.values.error_codes import ErrorCode
from apps.connectors.callback.callback_client import send_callback


_JOB_STORE: dict[str, dict[str, Any]] = {}


def _utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _load_job_or_raise(job_id: str) -> dict[str, Any]:
    job = _JOB_STORE.get(job_id)
    if job is None:
        raise MIBaseError(
            ErrorCode.ENTITY_NOT_FOUND,
            detail=f"Interpretation job not found: {job_id}",
        )
    return job


def _set_job(job_id: str, **changes: Any) -> None:
    job = _load_job_or_raise(job_id)
    job.update(changes)
    job["updated_at"] = _utc_now_iso()


def _validate_request_scenarios(
    scenario_group_id: int,
    scenarios: list[InterpretationScenarioIn],
) -> None:
    scenario_service = ScenarioService()
    existing_scenarios = scenario_service.load_by_group_id(scenario_group_id)
    existing_ids = {int(s.scenario_id) for s in existing_scenarios}
    requested_ids = [int(s.scenario_id) for s in scenarios]

    if len(set(requested_ids)) != len(requested_ids):
        raise MIBaseError(
            ErrorCode.INVALID_REQUEST,
            detail="scenario_id must be unique within request.scenarios",
        )

    missing_ids = sorted(set(requested_ids) - existing_ids)
    if missing_ids:
        raise MIBaseError(
            ErrorCode.ENTITY_NOT_FOUND,
            detail=f"Scenario IDs not found in scenario_group_id={scenario_group_id}: {missing_ids}",
        )


def prepare_create_interpretation(
    scenario_group_id: int,
    scenarios: list[InterpretationScenarioIn],
) -> dict[str, Any]:
    group = ScenarioGroupService().load_by_id(scenario_group_id)
    if group is None:
        raise MIBaseError(
            ErrorCode.ENTITY_NOT_FOUND,
            detail=f"Scenario group not found: {scenario_group_id}",
        )

    _validate_request_scenarios(scenario_group_id, scenarios)

    job_id = uuid4().hex
    now = _utc_now_iso()
    _JOB_STORE[job_id] = {
        "job_id": job_id,
        "scenario_group_id": scenario_group_id,
        "status": "accepted",
        "stage": "queued",
        "accepted_at": now,
        "updated_at": now,
        "error": None,
        "request_scenarios": [scenario.model_dump() for scenario in scenarios],
    }
    return _JOB_STORE[job_id]


def get_interpretation_job(job_id: str) -> dict[str, Any]:
    return _load_job_or_raise(job_id)


def _build_base_event(scenario_group_id: int) -> BaseEventOut:
    group = ScenarioGroupService().load_by_id(scenario_group_id)
    if group is None:
        raise MIBaseError(
            ErrorCode.ENTITY_NOT_FOUND,
            detail=f"Scenario group not found: {scenario_group_id}",
        )

    event = EventService().load_event(int(group.mi_event_id))
    if event is None:
        raise MIBaseError(
            ErrorCode.ENTITY_NOT_FOUND,
            detail=f"MI event not found: {group.mi_event_id}",
        )

    event_type = event.event_type or {}
    return BaseEventOut(
        event_id=int(event.mi_event_id),
        title=event.event_title_ko,
        summary=event.one_line_summary,
        event_type={
            "l1_code": str(event_type.get("l1_code", "")),
            "l2_code": str(event_type.get("l2_code", "")),
        },
        key_drivers=[str(item) for item in event.key_bullets],
        occurred_at=event.occurred_at or None,
    )


def _build_dimensions(scenario_group_id: int) -> list[DimensionDefinitionOut]:
    group = ScenarioGroupService().load_by_id(scenario_group_id)
    if group is None:
        raise MIBaseError(
            ErrorCode.ENTITY_NOT_FOUND,
            detail=f"Scenario group not found: {scenario_group_id}",
        )

    template = ScenarioService().load_scenario_template(int(group.event_type_l2_id))
    return [
        DimensionDefinitionOut(
            dimension_id=dimension.dimension_id,
            label=dimension.label_ko,
            rationale=dimension.description or None,
            enum_used=[enum_item.label for enum_item in dimension.enum],
        )
        for dimension in template.dimensions
    ]


def _build_scenarios(
    scenario_group_id: int,
    requested_scenarios: list[dict[str, Any]],
) -> list[InterpretationScenarioOut]:
    scenario_service = ScenarioService()
    db_scenarios = scenario_service.load_by_group_id(scenario_group_id)
    db_by_id = {int(s.scenario_id): s for s in db_scenarios}

    out: list[InterpretationScenarioOut] = []
    for request_scenario in requested_scenarios:
        scenario_id = int(request_scenario["scenario_id"])
        db_scenario = db_by_id.get(scenario_id)
        if db_scenario is None:
            raise MIBaseError(
                ErrorCode.ENTITY_NOT_FOUND,
                detail=f"Scenario not found while building callback payload: {scenario_id}",
            )
        forecast_points = request_scenario["forecast"]
        pattern = _build_pattern_from_forecast(forecast_points)
        out.append(
            InterpretationScenarioOut(
                scenario_id=scenario_id,
                title=db_scenario.title,
                description=db_scenario.narrative,
                dimension_values=db_scenario.dimension_values or {},
                pattern=pattern,
                causal_narrative=_build_causal_narrative(
                    db_scenario.title,
                    db_scenario.dimension_values or {},
                    pattern,
                ),
                likelihood_prior=_to_likelihood_prior(db_scenario.probability_score),
                forecast=forecast_points,
            )
        )
    return out


def _build_pattern_from_forecast(forecast_points: list[dict[str, Any]]) -> dict[str, Any]:
    if not forecast_points:
        return {"A": {"peaks": {}}, "B": {}, "C": {}}
    peak = max(forecast_points, key=lambda point: float(point.get("value", 0.0)))
    first = forecast_points[0]
    last = forecast_points[-1]
    avg = mean(float(point.get("value", 0.0)) for point in forecast_points)
    return {
        "A": {
            "peaks": {
                "forecast": {
                    "index": "forecast",
                    "month": str(peak.get("month", "")),
                    "value": float(peak.get("value", 0.0)),
                    "type": "max",
                }
            }
        },
        "B": {
            "stabilization_start": str(last.get("month", "")),
            "stabilized_levels": {"forecast": float(last.get("value", 0.0))},
        },
        "C": {
            "period_start": str(first.get("month", "")),
            "period_end": str(last.get("month", "")),
            "averages": {"forecast": round(avg, 3)},
        },
    }


def _to_likelihood_prior(probability_score: Any) -> str:
    try:
        value = float(probability_score)
    except (TypeError, ValueError):
        return "medium"
    if value < 10:
        return "very_low"
    if value < 20:
        return "low"
    if value < 40:
        return "medium"
    if value < 70:
        return "high"
    return "very_high"


def _build_causal_narrative(
    scenario_title: str,
    dimension_values: dict[str, Any],
    pattern: dict[str, Any],
) -> str:
    peak_info = (
        pattern.get("A", {})
        .get("peaks", {})
        .get("forecast", {})
    )
    peak_month = peak_info.get("month", "")
    peak_value = peak_info.get("value", "")
    dims = ", ".join(f"{key}={value}" for key, value in dimension_values.items()) or "기본 가정"
    return (
        f"{scenario_title} 시나리오에서 ({dims}) 조합이 반영되며, "
        f"예측값은 {peak_month}에 최대 {peak_value} 수준을 보인 뒤 점진적으로 안정화되는 패턴입니다."
    )


def _build_synthesis(scenarios: list[InterpretationScenarioOut]) -> dict[str, Any]:
    if not scenarios:
        return {}

    def _avg(points: list[Any] | None) -> float:
        if not points:
            return 0.0
        return float(mean(float(point.value) for point in points))

    def _peak(points: list[Any] | None) -> tuple[float, str]:
        if not points:
            return (0.0, "")
        max_point = max(points, key=lambda point: float(point.value))
        return (float(max_point.value), str(max_point.month))

    by_avg = sorted(
        (
            {"scenario_id": scenario.scenario_id, "forecast_avg": round(_avg(scenario.forecast), 3)}
            for scenario in scenarios
        ),
        key=lambda item: item["forecast_avg"],
        reverse=True,
    )
    by_peak = sorted(
        (
            {
                "scenario_id": scenario.scenario_id,
                "index": "forecast",
                "value": round(_peak(scenario.forecast)[0], 3),
                "month": _peak(scenario.forecast)[1],
            }
            for scenario in scenarios
        ),
        key=lambda item: item["value"],
        reverse=True,
    )

    return {
        "ranking": {
            "most_bullish": by_avg[0]["scenario_id"],
            "most_bearish": by_avg[-1]["scenario_id"],
            "by_peak": by_peak,
            "by_avg": by_avg,
        },
        "commonalities": [
            "모든 시나리오는 동일 이벤트 컨텍스트에서 파생된 분기 케이스입니다.",
            "입력된 forecast 시계열을 기반으로 고점/평균/안정화 구간을 요약합니다.",
        ],
        "differences": [
            "시나리오별 dimension_values 조합에 따라 forecast 고점 시점과 평균 수준이 달라집니다.",
            "상대적으로 평균이 높은 시나리오는 상방 리스크가 큰 케이스로 해석됩니다.",
        ],
        "summary_message": "입력 forecast를 기반으로 시나리오 간 상대 강도와 패턴을 비교한 결과입니다.",
    }


def _build_callback_payload(job_id: str) -> InterpretationCallbackOut:
    job = _load_job_or_raise(job_id)
    scenario_group_id = int(job["scenario_group_id"])
    base_event = _build_base_event(scenario_group_id)
    dimensions = _build_dimensions(scenario_group_id)
    scenarios = _build_scenarios(scenario_group_id, job.get("request_scenarios", []))
    interpretation = InterpretationResultOut(
        meta=InterpretationMetaOut(
            scenario_group_id=scenario_group_id,
            base_event_id=base_event.event_id,
            interpretation_date=datetime.now(tz=timezone.utc).date().isoformat(),
            indices=["JKM", "TTF", "HH"],
            unit="$/MMBtu",
        ),
        scenarios=scenarios,
        synthesis=_build_synthesis(scenarios),
        base_event=base_event,
        dimensions=dimensions,
    )
    return InterpretationCallbackOut(
        result="success",
        reason=None,
        data=InterpretationCallbackData(
            job_id=job_id,
            scenario_group_id=scenario_group_id,
            interpretation=interpretation,
        ),
    )


async def run_create_interpretation_background(job_id: str) -> None:
    from apps.common.configs.config import get_settings

    cfg = get_settings()
    job = _load_job_or_raise(job_id)
    scenario_group_id = int(job["scenario_group_id"])
    callback_path = cfg.callback_create_interpretations_path.format(
        job_id=job_id,
        scenario_group_id=scenario_group_id,
    )
    callback_url = cfg.callback_base_url.rstrip("/") + callback_path

    _set_job(job_id, status="processing", stage="loading_db")
    start = time.perf_counter()
    logger.info(f"[BG][interpret] START | job_id={job_id} | group_id={scenario_group_id}")
    try:
        _set_job(job_id, stage="generating")
        callback_payload = _build_callback_payload(job_id)
        _set_job(job_id, stage="callback_pending")
        await send_callback(callback_url, callback_payload)
        _set_job(job_id, status="completed", stage="callback_sent", error=None)
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        logger.info(f"[BG][interpret] END | job_id={job_id} | elapsed={elapsed_ms}ms")
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        logger.error(
            f"[BG][interpret] FAILED | job_id={job_id} | elapsed={elapsed_ms}ms | error={exc!r}"
        )
        _set_job(
            job_id,
            status="failed",
            stage="failed",
            error={"code": ErrorCode.UNKNOWN_ERROR.name, "detail": str(exc)},
        )
        error_payload = InterpretationCallbackOut(result="failure", reason=str(exc))
        try:
            await send_callback(callback_url, error_payload)
        except Exception as callback_error:
            logger.error(f"[BG][interpret] CALLBACK_FAILED | job_id={job_id} | error={callback_error!r}")


def remove_finished_jobs(max_items: int = 1000) -> None:
    if len(_JOB_STORE) <= max_items:
        return
    keys_to_remove = []
    for job_id, job in _JOB_STORE.items():
        if job.get("status") in {"completed", "failed"}:
            keys_to_remove.append(job_id)
        if len(_JOB_STORE) - len(keys_to_remove) <= max_items:
            break
    for job_id in keys_to_remove:
        _JOB_STORE.pop(job_id, None)

