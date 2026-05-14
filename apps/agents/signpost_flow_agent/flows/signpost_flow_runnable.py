"""
Signpost Flow Runnable 진입 모듈

역할:
- signpost_flow_graph를 외부에서 실행 가능한 Runnable 형태로 감싼다.
- 입력(Input) → 내부 상태(State) → 최종 출력(Output) 변환 흐름을 연결한다.
- 실행 전 runtime 초기화와 실행 후 output 변환을 담당한다.
- 다수의 mi_event_id를 순회하며 각각 pipeline 실행 및 결과 집계 (batch 처리).

구성:
- SignpostFlowRunnable
  - graph 실행을 감싸는 Runnable 래퍼
  - sync invoke는 금지하고 async ainvoke만 허용
- build_runnable_graph
  - Runnable 객체를 생성하고 input/output 타입 정보를 부여
- runnable_graph
  - 실제 서버에서 import하여 사용하는 최종 실행 객체
"""
from __future__ import annotations

from typing import Any, Sequence

from langchain_core.runnables import Runnable

from apps.agents.signpost_flow_agent.flows.signpost_flow_adapters import (
    build_batch_output,
    to_output,
    to_state,
)
from apps.agents.signpost_flow_agent.flows.signpost_flow_graph import signpost_flow_graph
from apps.agents.signpost_flow_agent.flows.signpost_flow_runtime import ensure_runtime
from apps.agents.signpost_flow_agent.schemas.signpost_flow_input import SignpostFlowInput
from apps.agents.signpost_flow_agent.schemas.signpost_flow_output import SignpostFlowOutput
from apps.common.configs.settings import get_settings
from apps.common.logging.logger_config import logger as app_logger


class SignpostFlowRunnable(Runnable):
    def __init__(self, graph: Runnable, stream_modes: Sequence[str] | str | None = None) -> None:
        self._graph = graph
        self._stream_modes = stream_modes

    def invoke(self, input: Any, config: dict | None = None, **kwargs: Any) -> Any:
        msg = "SignpostFlowRunnable는 async 전용입니다. ainvoke를 사용하세요."
        raise RuntimeError(msg)

    async def ainvoke(self, input: Any, config: dict | None = None, **kwargs: Any) -> Any:
        # Parse input to get list of mi_event_ids
        parsed = SignpostFlowInput.model_validate(input)
        mi_event_ids = parsed.mi_event_ids

        await ensure_runtime(object(), **kwargs)

        results: list[dict[str, Any]] = []

        for mi_event_id in mi_event_ids:
            app_logger.info(
                "[SIGNPOST_BATCH] Processing mi_event_id={}",
                mi_event_id,
            )

            # Step 1: Process pipeline for this event
            try:
                state = to_state(mi_event_id)
                final_state = await self._graph.ainvoke(state, config=config)
                per_event = to_output(final_state)
                results.append(per_event)
            except Exception as e:
                app_logger.error(
                    "[SIGNPOST_BATCH] Pipeline failed for mi_event_id={}: {}",
                    mi_event_id,
                    e,
                )
                results.append({
                    "mi_event_id": mi_event_id,
                    "status": "failure",
                    "message": str(e),
                })

        # Step 2: Aggregate results
        return build_batch_output(results)


def build_runnable_graph(stream_modes: Sequence[str] | str | None = None) -> Runnable:
    runnable: Runnable = SignpostFlowRunnable(signpost_flow_graph, stream_modes=stream_modes)
    return runnable.with_types(input_type=SignpostFlowInput, output_type=SignpostFlowOutput)


runnable_graph: Runnable = build_runnable_graph(stream_modes=get_settings().streaming_mode)