from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from apps.agents.mi_agent.state.state import MariAgentState
from apps.agents.mi_agent.subgraphs.vdb_search.schemas import (
    VDBSearchInput,
    VDBSearchItem,
    VDBSearchOutput,
    VectorSourceModel,
)
from apps.agents.mi_agent.subgraphs.vdb_search.state import VDBSearchState


def _ensure_mari_state(mari_state: MariAgentState | Mapping[str, Any]) -> MariAgentState:
    if isinstance(mari_state, MariAgentState):
        return mari_state
    return MariAgentState.model_validate(mari_state)


def _to_input_from_agent_state(mari_state: MariAgentState) -> VDBSearchInput:
    return VDBSearchInput(
        company_code=mari_state.company_code,
        user_num=mari_state.user_num,
        rewritten_query=mari_state.rewritten_query,
        histories=mari_state.histories or [],
        content_provider_vdb_accesses=mari_state.content_provider_vdb_accesses,
    )


def to_state(mari_state: MariAgentState | Mapping[str, Any]) -> VDBSearchState:
    mari_model = _ensure_mari_state(mari_state)
    vdb_search_input: VDBSearchInput = _to_input_from_agent_state(mari_model)
    return VDBSearchState(
        company_code=vdb_search_input.company_code,
        user_num=vdb_search_input.user_num,
        search_sources=mari_model.search_sources,
        histories=vdb_search_input.histories or [],
        rewritten_query=vdb_search_input.rewritten_query,
        content_provider_vdb_accesses=vdb_search_input.content_provider_vdb_accesses,
        rdb_search_metadata_repo_id=mari_model.rdb_search_metadata_repo_id,
    )


def to_output(vdb_state: VDBSearchState | Mapping[str, Any]) -> VDBSearchOutput:
    raw_sources = vdb_state["vector_sources"] or []
    vector_sources: list[VDBSearchItem] = _convert_to_vdb_item_list(raw_sources)
    return VDBSearchOutput(vector_sources=vector_sources)


def _convert_to_vdb_item_list(raw: list[Any]) -> list[VDBSearchItem]:
    result: list[VDBSearchItem] = []
    for item in raw:
        if isinstance(item, VDBSearchItem):
            result.append(item)
        elif isinstance(item, dict):
            metadata_raw = item.get("metadata", {})
            metadata = (
                metadata_raw
                if isinstance(metadata_raw, VectorSourceModel)
                else VectorSourceModel.model_validate(metadata_raw)
            )
            result.append(
                VDBSearchItem(
                    content=item.get("content", ""),
                    metadata=metadata,
                    score=float(item.get("score", 0.0) or 0.0),
                ),
            )
    return result
