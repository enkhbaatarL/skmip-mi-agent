#   agents/event_flow_agent/flows/event_flow_runnable.py
#   kmj20260423목
"""
Event Flow Runnable 진입 모듈

역할:
- event_flow_graph를 외부에서 실행 가능한 Runnable 형태로 감싼다.
- 입력(Input) → 내부 상태(State) → 최종 출력(Output) 변환 흐름을 연결한다.
- 실행 전 runtime 초기화와 실행 후 output 변환을 담당한다.

구성:
- EventFlowRunnable
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
  event_flow_agent를 배포 가능한 실행 단위로 제공한다.
"""

from __future__ import annotations

from typing import Any, Sequence

from langchain_core.runnables import Runnable

from apps.agents.event_flow_agent.flows.event_flow_adapters import to_output, to_state
from apps.agents.event_flow_agent.flows.event_flow_graph import _event_flow_agent
from apps.agents.event_flow_agent.flows.event_flow_runtime import ensure_runtime
from apps.agents.event_flow_agent.schemas.event_flow_input import EventFlowInput
from apps.agents.event_flow_agent.schemas.event_flow_output import EventFlowOutput
from apps.common.configs.settings import get_settings


class EventFlowRunnable(Runnable):
    def __init__(self, graph: Runnable, stream_modes: Sequence[str] | str | None = None) -> None:
        self._graph = graph
        self._stream_modes = stream_modes

    def invoke(self, input: Any, config: dict | None = None, **kwargs: Any) -> Any:
        msg = "EventFlowRunnable는 async 전용입니다. ainvoke를 사용하세요."
        raise RuntimeError(msg)

    async def ainvoke(self, input: Any, config: dict | None = None, **kwargs: Any) -> Any:
        state = to_state(input, **kwargs)
        await ensure_runtime(state, **kwargs)
        final_state = await self._graph.ainvoke(state, config=config)
        return to_output(final_state)


def build_runnable_graph(stream_modes: Sequence[str] | str | None = None) -> Runnable:
    runnable: Runnable = EventFlowRunnable(_event_flow_agent, stream_modes=stream_modes)
    return runnable.with_types(input_type=EventFlowInput, output_type=EventFlowOutput)


runnable_graph: Runnable = build_runnable_graph(stream_modes=get_settings().streaming_mode)