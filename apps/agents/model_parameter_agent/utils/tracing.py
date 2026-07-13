from __future__ import annotations

from apps.agents.model_parameter_agent.constants import AGENT_NAME
from apps.common.tracing.context import TraceContext, new_transaction_id


def build_trace_context(session_id: str | None = None) -> TraceContext:
    from apps.common.configs.config import get_settings

    cfg = get_settings()
    get_agent_config = getattr(cfg, "get_agent_config", None)
    agent_config = get_agent_config(AGENT_NAME) if callable(get_agent_config) else None
    return TraceContext(
        transaction_id=new_transaction_id(),
        app_identifier=getattr(agent_config, "aip_app_id", AGENT_NAME),
        agent_name=AGENT_NAME,
        session_id=session_id,
    )
