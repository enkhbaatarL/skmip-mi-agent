"""Web search schemas for input, output, and results."""

from typing import Any

from pydantic import BaseModel, Field


class WebSearchResult(BaseModel):
    """Individual web search result item."""

    query: str = Field(description="검색 쿼리")
    period: str = Field(description="검색 기간 (start_end)")
    score: float = Field(description="관련성 점수")
    title: str = Field(description="문서 제목")
    url: str = Field(description="문서 URL")
    content: str = Field(description="문서 내용")
    published_date: str | None = Field(default=None, description="발행일")
    raw_content: str | None = Field(default=None, description="원본 콘텐츠")


class WebSearchOutput(BaseModel):
    """Web search output containing results and metadata."""

    web_results: list[WebSearchResult] = Field(
        default_factory=list,
        description="웹 검색 결과 목록",
    )
    web_sources: list[str] = Field(
        default_factory=list,
        description="웹 검색 소스 (하위 호환성)",
    )
    total_results: int = Field(default=0, description="총 결과 수")
    search_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="검색 메타데이터 (응답 시간 등)",
    )
