from pydantic import BaseModel, ConfigDict, Field

from apps.agents.mi_agent.schemas.schemas import TimeSeriesInsights
from apps.agents.mi_agent.subgraphs.vdb_search.schemas import VectorSourceModel


class ChartModel(BaseModel):
    """시계열 차트 데이터."""

    order: int = Field(default=0, description="차트 렌더링/정렬 순서 (0-based 권장)")
    legend: str = Field(..., description="차트 범례명")
    date: list[str] = Field(..., description="x축 날짜 라벨 목록 (YYYY-MM-DD 등)")
    value: list[float] = Field(..., description="y축 값 목록 (date와 길이 매칭)")
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "order": 0,
                    "legend": "브렌트유 가격 (USD/bbl)",
                    "date": ["2024-04-01", "2024-04-02"],
                    "value": [123.4, 125.6],
                },
            ],
        },
    )


class SourceModel(BaseModel):
    """웹 검색 출처 정보."""

    url: str = Field(..., description="출처 URL")
    source_nm: str = Field(..., description="출처명(사이트/문서 이름 등)")
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "url": "https://example.com/oil-market-news",
                    "source_nm": "Oil Market News",
                },
            ],
        },
    )


class PromptTokensDetails(BaseModel):
    """프롬프트 토큰 세부 사용량."""

    cached_tokens: int = Field(
        default=0,
        description="캐시된 프롬프트 토큰 수",
    )
    audio_tokens: int = Field(
        default=0,
        description="오디오 프롬프트 토큰 수",
    )
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
    )


class CompletionTokensDetails(BaseModel):
    """완성 토큰 세부 사용량."""

    reasoning_tokens: int = Field(
        default=0,
        description="추론 토큰 수",
    )
    audio_tokens: int = Field(
        default=0,
        description="오디오 응답 토큰 수",
    )
    accepted_prediction_tokens: int = Field(
        default=0,
        description="수용된 예측 토큰 수",
    )
    rejected_prediction_tokens: int = Field(
        default=0,
        description="거부된 예측 토큰 수",
    )
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
    )


class UsageModel(BaseModel):
    """LLM 사용량 정보."""

    prompt_tokens: int = Field(
        default=0,
        description="프롬프트 토큰 수",
    )
    completion_tokens: int = Field(
        default=0,
        description="응답 생성 토큰 수",
    )
    total_tokens: int = Field(
        default=0,
        description="총 토큰 수 (prompt + completion)",
    )
    prompt_tokens_details: PromptTokensDetails | None = Field(
        default=None,
        description="프롬프트 토큰 세부 사용량",
    )
    completion_tokens_details: CompletionTokensDetails | None = Field(
        default=None,
        description="응답 토큰 세부 사용량",
    )
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        json_schema_extra={
            "examples": [
                {
                    "prompt_tokens": 1500,
                    "completion_tokens": 800,
                    "total_tokens": 2300,
                    "prompt_tokens_details": {
                        "cached_tokens": 0,
                        "audio_tokens": 0,
                    },
                    "completion_tokens_details": {
                        "reasoning_tokens": 0,
                        "audio_tokens": 0,
                        "accepted_prediction_tokens": 0,
                        "rejected_prediction_tokens": 0,
                    },
                },
            ],
        },
    )


class RdbSearchResult(BaseModel):
    """RDB 검색 결과."""

    sql_queries: list[str] = Field(
        default_factory=list,
        description="실행된 SQL 쿼리 목록",
    )
    used_tables: list[str] = Field(
        default_factory=list,
        description="질의에 사용된 테이블명 목록",
    )
    product_numbers: list[int] = Field(
        default_factory=list,
        description="관련 상품 번호 목록 (product_num)",
    )
    product_data_numbers: list[int] = Field(
        default_factory=list,
        description="관련 상품 데이터 번호 목록 (product_data_num)",
    )
    charts: list[ChartModel] = Field(
        default_factory=list,
        description="시각화용 차트 데이터 목록",
    )
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "sql_queries": [
                        "SELECT date, price FROM oil_prices WHERE date >= '2024-01-01'",
                    ],
                    "used_tables": ["oil_prices", "commodity_index"],
                    "product_numbers": [12345, 12346],
                    "product_data_numbers": [586343],
                    "charts": [
                        {
                            "order": 0,
                            "legend": "브렌트유 가격 (USD/bbl)",
                            "date": ["2024-04-01", "2024-04-02"],
                            "value": [85.1, 85.3],
                        },
                    ],
                },
            ],
        },
    )


class VdbSearchResult(BaseModel):
    """VDB(벡터DB) 검색 결과."""

    sources: list[VectorSourceModel] = Field(
        default_factory=list,
        description="벡터DB 검색 문서 출처 목록",
    )
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "sources": [
                        {
                            "source": "/docs/oil_report_2024.pdf",
                            "title": "2024 원유 시장 분석 보고서",
                            "product_num": 1001,
                            "product_data_num": "586343",
                        },
                    ],
                },
            ],
        },
    )


class WebSearchResult(BaseModel):
    """웹 검색 결과."""

    sources: list[SourceModel] = Field(
        default_factory=list,
        description="웹 검색 출처 목록",
    )
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "sources": [
                        {
                            "url": "https://example.com/oil-market-news",
                            "source_nm": "Oil Market News",
                        },
                    ],
                },
            ],
        },
    )


class SearchResults(BaseModel):
    """검색 결과 통합 카테고리."""

    rdb: RdbSearchResult | None = Field(
        default=None,
        description="RDB 검색 결과 (SQL, 테이블, 상품번호, 차트)",
    )
    vdb: list[VectorSourceModel] | None = Field(
        default=None,
        description="VDB(벡터DB) 검색 출처 목록",
    )
    web: list[SourceModel] | None = Field(
        default=None,
        description="웹 검색 출처 목록",
    )
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "rdb": {
                        "sql_queries": ["SELECT ..."],
                        "used_tables": ["oil_prices"],
                        "product_numbers": [12345],
                        "charts": [],
                    },
                    "vdb": [],
                    "web": [],
                },
            ],
        },
    )


class AnalysisResult(BaseModel):
    """분석 결과 카테고리."""

    content: str = Field(
        default="",
        description="검색 결과 기반 상세 분석 텍스트",
    )
    suggested_questions: list[str] = Field(
        default_factory=list,
        description="추가로 궁금하실 수 있는 질문들",
    )
    analysis_summary: str = Field(
        default="",
        description="핵심 인사이트 (2-3문장)",
    )
    timeseries_insights: TimeSeriesInsights | None = Field(
        default=None,
        description="시계열 인사이트 (주요 지표, 하이라이트, 차트 포함)",
    )
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "content": "2024년 4월 브렌트유 가격은 평균 $85.2/bbl로, 전월 대비 2.3% 상승했습니다...",
                    "suggested_questions": [
                        "브렌트유와 WTI 가격 차이는 어떻게 되나요?",
                        "최근 원유 가격 상승의 주요 원인은 무엇인가요?",
                        "향후 원유 가격 전망은 어떻게 되나요?",
                    ],
                    "analysis_summary": "브렌트유 가격이 OPEC+ 감산 연장 발표 영향으로 상승세를 보이고 있습니다.",
                    "timeseries_insights": {
                        "key_indicators": [
                            {
                                "label": "최고가",
                                "value": 91.0,
                                "date": "2024-04-01",
                                "unit": "USD/bbl",
                                "sources": ["S1", "S3"],
                            },
                        ],
                        "timeline_highlights": {
                            "columns": [
                                {"key": "date", "label": "날짜", "type": "date"},
                                {"key": "value", "label": "종가", "type": "number", "unit": "USD/bbl"},
                                {"key": "event", "label": "주요 이벤트/원인", "type": "string"},
                            ],
                            "rows": [
                                {
                                    "date": "2024-04-01",
                                    "value": 91.0,
                                    "event": "OPEC+ 감산 연장 발표",
                                    "sources": ["S2", "S4"],
                                },
                            ],
                        },
                        "charts": [],
                        "requested_range": "2024-04-01 ~ 2024-04-30",
                        "available_range": "2024-04-01 ~ 2024-04-30",
                        "primary_value_field": "price",
                        "unit": "USD/bbl",
                    },
                },
            ],
        },
    )


class MariAgentOutput(BaseModel):
    """MI Agent 최종 출력 스키마."""

    answer: AnalysisResult = Field(
        default_factory=AnalysisResult,
        description="검색 결과 기반 분석 내용",
    )
    evidence: SearchResults = Field(
        default_factory=SearchResults,
        description="RDB/VDB/웹 검색 결과",
    )
    usage: UsageModel | None = Field(
        default=None,
        description="LLM 사용량 (토큰 수)",
    )
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "answer": {
                        "content": "2024년 4월 브렌트유 가격은 평균 $85.2/bbl로...",
                    },
                    "evidence": {
                        "rdb": {
                            "sql_queries": ["SELECT date, price FROM oil_prices..."],
                            "used_tables": ["oil_prices"],
                            "product_numbers": [12345, 12346],
                            "charts": [],
                        },
                        "vdb": [],
                        "web": [],
                    },
                    "usage": {
                        "prompt_tokens": 1500,
                        "completion_tokens": 800,
                        "total_tokens": 2300,
                    },
                },
            ],
        },
    )
