"""Web search subgraph state definition."""

from typing import Any

from pydantic import BaseModel, Field

from apps.agents.mi_agent.subgraphs.web_search.schemas import WebSearchResult


class WebSearchState(BaseModel):
    """State for web search subgraph execution."""

    # Input fields
    rewritten_query: str = Field(description="재작성된 사용자 질의")
    search_periods: list[dict[str, str]] = Field(
        default_factory=list,
        description="검색할 기간 목록 [{'start': 'YYYY-MM-DD', 'end': 'YYYY-MM-DD'}]",
    )

    # Configuration fields
    search_config: dict[str, Any] = Field(
        default_factory=dict,
        description="검색 설정 (search_params, result_filter 등)",
    )

    # Output fields
    web_search_results: list[WebSearchResult] = Field(
        default_factory=list,
        description="웹 검색 결과",
    )

    # Metadata fields
    total_results: int = Field(default=0, description="총 검색 결과 수")
    search_duration_ms: float = Field(default=0.0, description="검색 소요 시간(ms)")
