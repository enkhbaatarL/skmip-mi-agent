from __future__ import annotations

from fastapi import APIRouter, Query

from apps.agents.scenario_group_agent.flows.create_signposts.flow import (
    prepare_create_signposts,
    run_create_signposts_inline,
)
from apps.agents.scenario_group_agent.flows.validate_scenarios.api_schema import (
    ValidateScenariosIn,
    ValidateScenariosSyncOut,
)
from apps.agents.scenario_group_agent.flows.validate_scenarios.flow import (
    prepare_validate_scenarios,
    run_validate_scenarios_inline,
)
from apps.agents.scenario_group_agent.persistence.scenario_group_service import ScenarioGroupService
from apps.agents.scenario_group_agent.presentation import (
    build_presentation_follow_up_request_bodies,
    build_scenario_group_presentation,
)
from apps.agents.scenario_group_agent.schemas.api.presentation_followup_requests import (
    PresentationFollowUpRequestBodiesOut,
)
from apps.agents.scenario_group_agent.schemas.endpoint import (
    CreateSignpostsIn,
    CreateSignpostsSyncOut,
)
from apps.common.configs.config import get_settings
from apps.common.logging.logger_config import logger
from apps.common.runtime.usage_context import get_accumulated_usage, reset_usage


router = APIRouter(tags=["scenario-groups-sync-test"])


@router.get(
    "/scenario-groups/{scenario_group_id}/presentation/follow-up-request-bodies",
    response_model=PresentationFollowUpRequestBodiesOut,
    summary="Presentation 기반 Validation/Signpost request body 생성",
)
async def get_presentation_follow_up_request_bodies(
    scenario_group_id: int,
    user_id: int = Query(alias="userId"),
    operation_id: str | None = Query(default=None, alias="operationId"),
) -> PresentationFollowUpRequestBodiesOut:
    context = ScenarioGroupService().load_presentation_detail(
        scenario_group_id,
        operation_id=operation_id,
    )
    hide_price_pressure = get_settings().hide_price_pressure
    presentation = build_scenario_group_presentation(
        **context,
        hide_price_pressure=hide_price_pressure,
    )
    return build_presentation_follow_up_request_bodies(presentation, user_id=user_id)


@router.post(
    "/scenario-groups/{scenario_group_id}/validation/sync",
    response_model=ValidateScenariosSyncOut,
    summary="시나리오 테이블 검증 동기 테스트",
)
async def validate_scenarios_sync(
    scenario_group_id: int,
    payload: ValidateScenariosIn,
) -> ValidateScenariosSyncOut:
    reset_usage()
    result = prepare_validate_scenarios(
        scenario_group_id,
        payload.user_id,
        payload.table.model_dump(),
    )
    try:
        run_kwargs = {
            "scenario_group_id": result["scenario_group_id"],
            "user_id": result["user_id"],
            "request_table": result["request_table"],
        }
        if result.get("operation_id") is not None:
            run_kwargs["operation_id"] = result["operation_id"]
        output = await run_validate_scenarios_inline(**run_kwargs)
        return ValidateScenariosSyncOut.model_validate(
            {**output.model_dump(), "usage": get_accumulated_usage()},
        )
    except Exception as exc:
        logger.error(
            "[SYNC][validate_scenarios] FAILED | group_id={} | error={!r}",
            result["scenario_group_id"],
            exc,
        )
        return ValidateScenariosSyncOut(result="failure", reason=str(exc), usage=get_accumulated_usage())


@router.post(
    "/scenario-groups/{scenario_group_id}/signposts/sync",
    response_model=CreateSignpostsSyncOut,
    summary="Signpost 생성 동기 테스트",
)
async def create_signposts_sync(
    scenario_group_id: int,
    payload: CreateSignpostsIn,
) -> CreateSignpostsSyncOut:
    reset_usage()
    result = prepare_create_signposts(
        scenario_group_id,
        payload.user_id,
        payload.table.model_dump() if payload.table is not None else None,
    )
    try:
        run_kwargs = {
            "scenario_group_id": result["scenario_group_id"],
            "user_id": result["user_id"],
            "request_table": result["request_table"],
        }
        if result.get("operation_id") is not None:
            run_kwargs["operation_id"] = result["operation_id"]
            run_kwargs["signpost_target_scenario_ids"] = result.get("signpost_target_scenario_ids")
        output = await run_create_signposts_inline(**run_kwargs)
        return CreateSignpostsSyncOut.model_validate(
            {**output.model_dump(), "usage": get_accumulated_usage()},
        )
    except Exception as exc:
        logger.error(
            "[SYNC][create_signposts] FAILED | group_id={} | error={!r}",
            result["scenario_group_id"],
            exc,
        )
        return CreateSignpostsSyncOut(result="failure", reason=str(exc), usage=get_accumulated_usage())
