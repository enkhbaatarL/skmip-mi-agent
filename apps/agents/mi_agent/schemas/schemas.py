from pydantic import BaseModel, Field


class SearchQuery(BaseModel):
    """VDB/RDB 검색을 위해 분리·정제된 단일 질의 및 키워드."""

    query: str = Field(
        ...,
        description="사용자 질의(단일 질의로 분리, 정제한 질의)",
        min_length=1,
    )
    search_text: str | None = Field(
        default=None,
        description="사용자 질의로부터 추출한 키워드 (벡터/풀텍스트 검색 시 사용)",
    )


class RewriteQueryResult(BaseModel):
    rewritten_query: str | None = Field(
        default=None,
        description="사용자 질의를 LLM에 의해 재작성해 얻은 보완 질의",
    )

    user_query_language: str | None = Field(
        default=None,
        description="사용자 입력 질의 언어(영어, 한국어)",
    )


class KeyIndicatorItem(BaseModel):
    """주요 지표 항목."""

    label: str = Field(..., description="지표 라벨 (예: 최고가, 최저가)")
    value: float | str = Field(..., description="지표 값")
    date: str | None = Field(default=None, description="기준 날짜 (YYYY-MM-DD)")
    unit: str | None = Field(default=None, description="단위 (예: USD/bbl, pts, $/oz)")
    sources: list[str] | None = Field(default=None, description="데이터 출처 목록")


class TimelineColumnDef(BaseModel):
    """타임라인 컬럼 정의."""

    key: str = Field(..., description="컬럼 키 (예: date, value, event)")
    label: str = Field(..., description="컬럼 라벨 (예: 날짜, 종가, 주요 이벤트/원인)")
    type: str = Field(..., description="컬럼 타입 (date, number, string)")
    unit: str | None = Field(default=None, description="단위 (예: USD/bbl)")


class TimelineRowItem(BaseModel):
    """타임라인 행 데이터."""

    date: str = Field(..., description="날짜 (YYYY-MM-DD)")
    value: float | str = Field(..., description="값")
    event: str | None = Field(default=None, description="주요 이벤트/원인")
    sources: list[str] | None = Field(default=None, description="데이터 출처 목록")


class TimelineHighlights(BaseModel):
    """시계열 주요 하이라이트."""

    columns: list[TimelineColumnDef] = Field(
        default_factory=list, description="컬럼 정의 목록"
    )
    rows: list[TimelineRowItem] = Field(default_factory=list, description="행 데이터 목록")


class ChartItem(BaseModel):
    """차트 데이터 항목."""

    order: int = Field(..., description="차트 순서 (1-based)")
    legend: str = Field(..., description="시계열 라인의 범례(시리즈 이름). 예: 'DXY', 'WTI'")
    date: list[str] = Field(default_factory=list, description="시계열 x축 날짜 리스트")
    value: list[float] = Field(default_factory=list, description="date와 동일한 길이의 값 리스트")


class TimeSeriesInsights(BaseModel):
    """시계열 인사이트 통합 모델."""

    key_indicators: list[KeyIndicatorItem] = Field(
        default_factory=list, description="주요 지표 목록"
    )
    timeline_highlights: TimelineHighlights | None = Field(
        default=None, description="시계열 주요 하이라이트"
    )
    charts: list[ChartItem] = Field(default_factory=list, description="차트 데이터 목록")
    requested_range: str | None = Field(
        default=None, description="요청 기간 (예: 2025-04-01 ~ 2026-01-23)"
    )
    available_range: str | None = Field(
        default=None, description="실제 데이터 가용 기간 (예: 2025-04-01 ~ 2026-01-23)"
    )
    primary_value_field: str | None = Field(
        default=None, description="대표 값 필드명 (예: price, close)"
    )
    unit: str | None = Field(default=None, description="단위 (예: USD/bbl)")


class AnalysisOutput(BaseModel):
    """분석 결과 및 추가 질문을 담는 모델."""

    content: str = Field(
        default="",
        description="상세 분석 내용",
    )
    suggested_questions: list[str] = Field(
        default_factory=list,
        description="추가로 궁금하실 수 있는 질문들",
    )
    analysis_summary: str = Field(
        default="",
        description="핵심 인사이트 (2-3문장)",
    )
