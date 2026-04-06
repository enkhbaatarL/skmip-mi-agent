from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

# 타입 순환 방지: 런타임 import 지연
from apps.agents.mi_agent.subgraphs.rdb_search.state import RDBSearchState
from apps.agents.mi_agent.subgraphs.vdb_search.state import VDBSearchState
from apps.agents.mi_agent.subgraphs.web_search.state import WebSearchState


class SearchState(BaseModel):
    rewritten_query: str = Field(description="사용자 질의를 LLM에 의해 재작성해 얻은 보완 질의")
    histories: list[dict] = Field(default_factory=list, description="대화 히스토리")
    web_search_enabled: bool | None = Field(default=True, description="웹 검색 사용 여부")

    rdb: RDBSearchState = Field(
        default_factory=RDBSearchState,
        description="RDB 검색 정보",
    )
    vdb: VDBSearchState = Field(
        default_factory=VDBSearchState,
        description="VDB 검색 정보",
    )
    web: WebSearchState = Field(
        default_factory=WebSearchState,
        description="WEB 검색 정보",
    )

    results: list[dict[str, Any]] = Field(default_factory=list)
