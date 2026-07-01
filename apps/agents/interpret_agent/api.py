from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks

from apps.agents.interpret_agent.flows.create_interpretation.flow_async import (
    get_interpretation_job,
    prepare_create_interpretation,
    remove_finished_jobs,
    run_create_interpretation_background,
)
from apps.agents.interpret_agent.schemas.api.interpretation import (
    CreateInterpretationIn,
    InterpretationAcceptedData,
    InterpretationAcceptedOut,
    InterpretationJobStatusData,
    InterpretationJobStatusOut,
)


router = APIRouter()


@router.post(
    "/interpretations",
    response_model=InterpretationAcceptedOut,
    summary="해석 작업 접수",
    description=(
        "시나리오 그룹 ID와 시나리오별 forecast 시계열을 입력받아 해석 작업을 접수합니다. "
        "실제 처리는 백그라운드에서 수행되고, 콜백 URL은 서버 설정값(callback_base_url + callback_create_interpretations_path)을 사용합니다."
    ),
)
async def create_interpretation(
    payload: CreateInterpretationIn,
    background_tasks: BackgroundTasks,
) -> InterpretationAcceptedOut:
    remove_finished_jobs()
    prepared = prepare_create_interpretation(
        scenario_group_id=payload.scenario_group_id,
        scenarios=payload.scenarios,
    )
    job_id = str(prepared["job_id"])
    background_tasks.add_task(run_create_interpretation_background, job_id)
    return InterpretationAcceptedOut(
        data=InterpretationAcceptedData(
            job_id=job_id,
            scenario_group_id=int(prepared["scenario_group_id"]),
            status=str(prepared["status"]),
            stage=str(prepared["stage"]),
            accepted_at=str(prepared["accepted_at"]),
        )
    )


@router.get(
    "/interpretations/{job_id}",
    response_model=InterpretationJobStatusOut,
    summary="해석 작업 상태 조회",
)
async def get_interpretation_status(job_id: str) -> InterpretationJobStatusOut:
    job = get_interpretation_job(job_id)
    return InterpretationJobStatusOut(
        data=InterpretationJobStatusData(
            job_id=str(job["job_id"]),
            scenario_group_id=int(job["scenario_group_id"]),
            status=str(job["status"]),
            stage=str(job["stage"]),
            updated_at=str(job["updated_at"]),
            error=job.get("error"),
        )
    )

