# TODO: default_factory=list로 변경
from __future__ import annotations

from pydantic import Field

from apps.agents.mi_agent.schemas.mari_agent_input import MariAgentInput
from apps.agents.mi_agent.subgraphs.rdb_search.schemas import (
    RDBSearchCandidate,
    RDBSearchQuery,
    RDBSearchResults,
    RDBSimilarityAnalysis,
)
from apps.common.values.enums import AnalysisType


class RDBSearchState(MariAgentInput, RDBSimilarityAnalysis):
    rewritten_query: str | None = Field(
        default=None,
        description="사용자 질의를 LLM으로 정제/보완하여 얻은 최종 자연어 질의",
    )
    analysis_type: AnalysisType | None = Field(
        None,
        description="분석 유형",
        examples=["general_request"],
    )
    rdb_search_queries: list[RDBSearchQuery] | None = Field(
        default_factory=list,
        description="분리된 사용자 질의 및 추출 키워드 (RDB검색을 위한 VDB검색(후보군 데이터 추출) 시 사용)리스트",
    )
    rdb_search_queries_historical: list[RDBSearchQuery] = Field(
        default_factory=list,
        description="분리된 사용자 질의 및 추출 키워드 (RDB검색을 위한 VDB검색(후보군 데이터 추출) 시 사용)리스트(유사패턴 과거)",
    )
    candidate_items: list[RDBSearchCandidate] | None = Field(
        default=None,
        description="사용자 질의와 유사도 높은 데이터 리스트(벡터DB로 부터 추출)",
    )
    candidate_items_historical: list[RDBSearchCandidate] | None = Field(
        default=None,
        description="사용자 질의와 유사도 높은 데이터 리스트(벡터DB로 부터 추출)(과거)",
    )

    rdb_search_results: RDBSearchResults | None = Field(
        default=None,
        description="RDB검색결과(조회된 데이터 리스트, 관련 데이터 항목들, 관련 테이블들, 생성된 SQL)",
    )
