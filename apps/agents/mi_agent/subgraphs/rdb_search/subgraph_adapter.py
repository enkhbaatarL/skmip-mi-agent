from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from apps.agents.mi_agent.state.state import MariAgentState
from apps.agents.mi_agent.subgraphs.rdb_search.schemas import (
    RDBSearchInput,
    RDBSearchOutput,
    RDBSearchResults,
)
from apps.agents.mi_agent.subgraphs.rdb_search.state import RDBSearchState


def to_state(mari_state: MariAgentState | Mapping[str, Any]) -> RDBSearchState:
    mari_model = _ensure_mari_state(mari_state)
    rdb_search_input: RDBSearchInput = _to_input_from_agent_state(mari_model)

    return RDBSearchState(
        company_code=rdb_search_input.company_code,
        user_num=rdb_search_input.user_num,
        search_sources=mari_model.search_sources,
        rewritten_query=rdb_search_input.rewritten_query,
        analysis_type=rdb_search_input.analysis_type,
        histories=rdb_search_input.histories or [],
        rdb_search_metadata_repo_id=rdb_search_input.rdb_search_metadata_repo_id,
        content_provider_rdb_accesses=rdb_search_input.content_provider_rdb_accesses,
    )


def to_output(rdb_state: RDBSearchState | Mapping[str, Any]) -> RDBSearchOutput:
    rdb_model = _ensure_rdb_state(rdb_state)

    rdb_search_results = rdb_model.rdb_search_results
    if rdb_search_results is None:
        rdb_search_results = RDBSearchResults(sqls="")

    return RDBSearchOutput(
        used_tables=rdb_search_results.used_tables,
        metric_data=rdb_search_results.metric_data,
        related_data=rdb_search_results.related_data,
        product_data_nums=rdb_search_results.product_data_nums,
        sqls=rdb_search_results.sqls,
        similarity_current_data=rdb_search_results.similarity_current_data,
        similarity_historical_data=rdb_search_results.similarity_historical_data,
        similar_patterns=rdb_search_results.similar_patterns,
    )


def _to_input_from_agent_state(mari_state: MariAgentState) -> RDBSearchInput:
    return RDBSearchInput(
        company_code=mari_state.company_code,
        user_num=mari_state.user_num,
        rewritten_query=mari_state.rewritten_query,
        analysis_type=mari_state.analysis_type,
        histories=mari_state.histories or [],
        rdb_search_metadata_repo_id=mari_state.rdb_search_metadata_repo_id,
        content_provider_rdb_accesses=mari_state.content_provider_rdb_accesses,
    )


def _ensure_mari_state(mari_state: MariAgentState | Mapping[str, Any]) -> MariAgentState:
    if isinstance(mari_state, MariAgentState):
        return mari_state
    return MariAgentState.model_validate(cast("Mapping[str, Any]", mari_state))


def _ensure_rdb_state(rdb_state: RDBSearchState | Mapping[str, Any]) -> RDBSearchState:
    if isinstance(rdb_state, RDBSearchState):
        return rdb_state
    return RDBSearchState.model_validate(cast("Mapping[str, Any]", rdb_state))
