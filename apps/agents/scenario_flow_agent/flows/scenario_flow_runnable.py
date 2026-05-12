"""
Scenario Flow Runnable 진입 모듈

역할:
- scenario_flow_graph를 외부에서 실행 가능한 Runnable 형태로 감싼다.
- 입력(Input) → 내부 상태(State) → 최종 출력(Output) 변환 흐름을 연결한다.
- 실행 전 runtime 초기화와 실행 후 output 변환을 담당한다.
- 다수의 mi_event_id를 순회하며 각각 pipeline 실행 및 결과 집계 (batch 처리).

구성:
- ScenarioFlowRunnable
  - graph 실행을 감싸는 Runnable 래퍼
  - sync invoke는 금지하고 async ainvoke만 허용
- build_runnable_graph
  - Runnable 객체를 생성하고 input/output 타입 정보를 부여
- runnable_graph
  - 실제 서버에서 import하여 사용하는 최종 실행 객체

설계 의도:
- graph 자체는 상태 기반 실행만 담당하고,
  외부 인터페이스와 runtime 초기화는 runnable 계층에서 처리한다.
- LangServe / adxp-cli가 기대하는 Runnable 인터페이스에 맞춰
  scenario_flow_agent를 배포 가능한 실행 단위로 제공한다.
"""
from __future__ import annotations

from typing import Any, Sequence

from langchain_core.runnables import Runnable

from apps.agents.scenario_flow_agent.flows.scenario_flow_adapters import (
    build_batch_output,
    to_output,
    to_state,
)
from apps.agents.scenario_flow_agent.flows.scenario_flow_graph import scenario_flow_graph
from apps.agents.scenario_flow_agent.flows.scenario_flow_runtime import ensure_runtime
from apps.agents.scenario_flow_agent.schemas.scenario_flow_input import ScenarioFlowInput
from apps.agents.scenario_flow_agent.schemas.scenario_flow_output import ScenarioFlowOutput
from apps.agents.scenario_flow_agent.services.scenario_db_service import ScenarioDbService
from apps.common.configs.settings import get_settings
from apps.common.logging.logger_config import logger as app_logger


class ScenarioFlowRunnable(Runnable):
    def __init__(self, graph: Runnable, stream_modes: Sequence[str] | str | None = None) -> None:
        self._graph = graph
        self._stream_modes = stream_modes

    def invoke(self, input: Any, config: dict | None = None, **kwargs: Any) -> Any:
        msg = "ScenarioFlowRunnable는 async 전용입니다. ainvoke를 사용하세요."
        raise RuntimeError(msg)

    async def ainvoke(self, input: Any, config: dict | None = None, **kwargs: Any) -> Any:
        # Parse input to get list of mi_event_ids
        parsed = ScenarioFlowInput.model_validate(input)
        mi_event_ids = parsed.mi_event_ids

        await ensure_runtime(object(), **kwargs)

        db_service = ScenarioDbService()
        results: list[dict[str, Any]] = []

        for mi_event_id in mi_event_ids:
            app_logger.info(
                "[SCENARIO_BATCH] Processing mi_event_id=%s",
                mi_event_id,
            )

            # Step 1: Check if scenarios already exist
            try:
                exists = db_service.check_scenarios_exist(mi_event_id)
            except Exception as e:
                app_logger.error(
                    "[SCENARIO_BATCH] Existence check failed for mi_event_id=%s: %s",
                    mi_event_id,
                    e,
                )
                results.append({
                    "mi_event_id": mi_event_id,
                    "status": "failure",
                    "message": f"Existence check failed: {e}",
                })
                continue

            if exists:
                app_logger.info(
                    "[SCENARIO_BATCH] Already exist, skipping mi_event_id=%s",
                    mi_event_id,
                )
                results.append({
                    "mi_event_id": mi_event_id,
                    "status": "already_exist",
                    "message": "Scenarios already exist",
                })
                continue

            # Step 2: Process pipeline for this event
            try:
                state = to_state(mi_event_id)
                final_state = await self._graph.ainvoke(state, config=config)
                per_event = to_output(final_state)
                results.append(per_event)
            except Exception as e:
                app_logger.error(
                    "[SCENARIO_BATCH] Pipeline failed for mi_event_id=%s: %s",
                    mi_event_id,
                    e,
                )
                results.append({
                    "mi_event_id": mi_event_id,
                    "status": "failure",
                    "message": str(e),
                })

        # Step 3: Aggregate results
        return build_batch_output(results)


def build_runnable_graph(stream_modes: Sequence[str] | str | None = None) -> Runnable:
    runnable: Runnable = ScenarioFlowRunnable(scenario_flow_graph, stream_modes=stream_modes)
    return runnable.with_types(input_type=ScenarioFlowInput, output_type=ScenarioFlowOutput)


runnable_graph: Runnable = build_runnable_graph(stream_modes=get_settings().streaming_mode)
