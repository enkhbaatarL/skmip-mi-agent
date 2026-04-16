#   agents/event_flow_agent/flows/event_flow_runnable.py

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