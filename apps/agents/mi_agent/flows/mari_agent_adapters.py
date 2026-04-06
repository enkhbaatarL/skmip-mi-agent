from __future__ import annotations

from typing import Any
from uuid import UUID

from apps.agents.mi_agent.schemas.mari_agent_input import MariAgentInput
from apps.agents.mi_agent.schemas.mari_agent_output import (
    AnalysisResult,
    MariAgentOutput,
    RdbSearchResult,
    SearchResults,
    SourceModel,
)
from apps.agents.mi_agent.schemas.search_output import SearchOutput
from apps.agents.mi_agent.state.state import MariAgentState
from apps.common.configs.settings import get_settings
from apps.common.runtime.usage_context import get_accumulated_usage


def to_state(raw: dict[str, Any] | MariAgentInput, **_: Any) -> MariAgentState:
    mi = raw if isinstance(raw, MariAgentInput) else MariAgentInput.model_validate(raw)
    cfg = get_settings()

    rdb_search_metadata_repo_id = cfg.rdb_search_metadata_repo_id

    return MariAgentState(
        company_code=mi.company_code,
        user_num=mi.user_num,
        user_query=mi.user_query,
        content_provider_rdb_accesses=mi.content_provider_rdb_accesses,
        content_provider_vdb_accesses=mi.content_provider_vdb_accesses,
        histories=mi.histories,
        search_sources=mi.search_sources,
        rdb_search_metadata_repo_id=rdb_search_metadata_repo_id,
        current_node="rewrite_query",
        executed_nodes=[],
    )


def _to_uuid(v: Any | None) -> UUID | None:
    if v is None or isinstance(v, UUID):
        return v
    return UUID(str(v))


def to_output(state_dict: dict[str, Any], **_: Any) -> MariAgentOutput:
    # invoke는 전체 state를 반환, stream은 노드별 청크를 반환
    state_data = state_dict.get("analysis", state_dict)

    mari_agent_state = MariAgentState.model_validate(state_data)

    search_output: SearchOutput = mari_agent_state.search_output
    rdb = search_output.rdb_search_output
    vdb = search_output.vdb_search_output
    web = search_output.web_search_output

    # RDB 검색 결과
    rdb_search_result = None
    if rdb:
        sql_queries = [rdb.sqls] if rdb.sqls else []
        rdb_search_result = RdbSearchResult(
            sql_queries=sql_queries,
            used_tables=rdb.used_tables,
            product_numbers=rdb.related_data,
            product_data_numbers=rdb.product_data_nums,
        )

    # VDB 검색 결과
    vdb_search_result = None
    if vdb and vdb.vector_sources:
        vdb_search_result = [
            item.metadata.model_copy(update={"content": item.content})
            for item in vdb.vector_sources
        ]

    # Web 검색 결과
    web_search_result = None
    if web and web.web_results:
        web_search_result = [SourceModel(url=r.url, source_nm=r.title) for r in web.web_results]

    # Usage 정보 - contextvars에서 누적된 값을 가져옴
    usage = get_accumulated_usage()

    return MariAgentOutput(
        answer=AnalysisResult(
            content=mari_agent_state.analysis_content or "",
            suggested_questions=mari_agent_state.suggested_questions,
            analysis_summary=mari_agent_state.analysis_summary or "",
            timeseries_insights=mari_agent_state.timeseries_insights,
        ),
        evidence=SearchResults(
            rdb=rdb_search_result,
            vdb=vdb_search_result,
            web=web_search_result,
        ),
        usage=usage,
    )
