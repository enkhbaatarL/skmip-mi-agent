# TODO: metric_data
from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from apps.agents.mi_agent.schemas.mari_agent_input import ContentProviderRdbAccess
from apps.common.values.enums import AnalysisType


class RDBSearchInput(BaseModel):
    company_code: str = Field(
        ...,
        description="회사 코드",
    )
    user_num: int | None = Field(
        default=None,
        description="사용자 번호",
    )
    rewritten_query: str = Field(
        ...,
        description="사용자 입력 질의",
    )
    analysis_type: AnalysisType | None = Field(
        None,
        description="분석 유형",
        examples=["general_request"],
    )
    histories: list[dict] = Field(default_factory=list, description="대화 히스토리")
    rdb_search_metadata_repo_id: UUID | None = Field(
        default=None,
        description=(
            "RDB 메타데이터 설명 문서가 저장된 벡터DB 리포지토리 식별자. "
            "미지정 시 환경변수(RDB_SEARCH_METADATA_REPO_ID) 값을 사용한다."
        ),
    )
    content_provider_rdb_accesses: ContentProviderRdbAccess = Field(
        default_factory=ContentProviderRdbAccess,
        description="RDB 검색에 적용할 접근 권한 정보",
    )


class RDBSearchResult(BaseModel):
    used_table: str = Field(
        ...,
        description="생성/실행된 SQL에서 참조된 테이블명",
    )
    metric_data: dict[str, Any] = Field(
        ...,
        description="RDB 검색 결과(직렬화된 문자열 등; 사용 형식은 상위 레이어에서 해석)",
    )
    related_data: list[int] = Field(
        default_factory=list,
        description="관련 상품 번호 목록 (예: product_num)",
    )
    product_data_nums: list[int] = Field(
        default_factory=list,
        description="관련 상품 데이터 번호 목록 (예: product_data_num)",
    )
    sql: str = Field(  # TODO: 리스트로 전달 & sql_queries로 명칭 변경 MI BE와 논의 후, 수정 예정, int로 변환 검토(MI BE와 논의)
        ...,
        description="생성된 sql",
    )


class RDBQueryResults(BaseModel):
    used_tables: list[str] = Field(
        default_factory=list,
        description="생성/실행된 SQL에서 참조된 테이블명 목록",
    )
    metric_data: list[dict[str, Any]] = Field(
        default_factory=list,
        description="RDB 검색 결과(직렬화된 문자열 등; 사용 형식은 상위 레이어에서 해석)",
    )
    related_data: list[int] = Field(
        default_factory=list,
        description="관련 상품 번호 목록 (예: product_num 리스트)",
    )
    product_data_nums: list[int] = Field(
        default_factory=list,
        description="관련 상품 데이터 번호 목록 (예: product_data_num 리스트)",
    )
    sqls: str | None = Field(  # TODO: 리스트로 전달 & sql_queries로 명칭 변경 MI BE와 논의 후, 수정 예정
        default=None,
        description="생성된 sql들",
    )


class RDBSimilarityAnalysis(BaseModel):
    similarity_current_data: list[dict] | None = Field(
        default_factory=list,
        description="유사 패턴 데이터 (현재)",
    )
    similarity_historical_data: list[dict] | None = Field(
        default_factory=list,
        description="유사 패턴 데이터 (과거: 최근1년)",
    )
    similar_patterns: list[dict] | None = Field(
        default_factory=list,
        description="유사 패턴",
    )


class RDBSearchResults(RDBQueryResults, RDBSimilarityAnalysis):
    charts: list[str] = Field(
        default_factory=list,
        description="차트",
    )


class RDBSearchOutput(RDBSearchResults):
    pass


class RDBSearchQuery(BaseModel):
    query: str = Field(
        ...,
        description="사용자 질의(단일 질의로 분리, 정제한 질의)",
        min_length=1,
    )
    search_text: str | None = Field(
        default=None,
        description="사용자 질의로 부터 추출한 키워드 (RDB검색을 위한 VDB검색(후보군 데이터 추출) 시 사용)",
    )


class SimilarityRdbQueryTexts(BaseModel):
    metric_subject: str = Field(
        ...,
        description="유사 패턴 분석을 위한 metric 주제(추출 실패 시 rewritten_query로 대체)",
        min_length=1,
    )
    current_query_text: str = Field(
        ...,
        description="현재 구간 데이터 조회용 RDB 질의 텍스트",
        min_length=1,
    )
    historical_query_text: str = Field(
        ...,
        description="과거(비교) 구간 데이터 조회용 RDB 질의 텍스트",
        min_length=1,
    )


class VDBSearchCandidate(BaseModel):
    tbl_expn: str = Field(
        ...,
        description="원본 사용자 질의와 유사도 높은 후보데이터의 테이블 설명",
    )

    agtmtm_id: int = Field(
        ...,
        description="원본 사용자 질의와 유사도 높은 후보데이터의 메타데이터 ID",
    )


class RDBSearchCandidate(BaseModel):
    query: str = Field(
        ...,
        description="사용자 질의(단일 질의로 분리, 정제한 질의)",
        min_length=1,
    )
    company_code: str | None = Field(
        default=None,
        description="회사 코드",
    )
    vdb_search_candidates: list[VDBSearchCandidate] = Field(
        ...,
        description="사용자 질의와 유사도 높은 정보를 VectorDB로 부터 조회한 결과(테이블명, 데이터 설명, 메타데이터ID)",
    )


class RDBSearchNltoSqlMapping(BaseModel):
    rdb_search_nl_query: str = Field(
        ...,
        description="RDB 검색을 위해 정제·보정된 자연어 질의(NL)",
        min_length=1,
    )
    sql: str | None = Field(
        default=None,
        description="해당 자연어 질의로부터 생성된 SQL(생성되지 않은 경우 None)",
    )


class SimilarityPatternQueryParams(BaseModel):
    metric_subject: str = Field(
        ...,
        description="metric 주제",
    )
    start_date: str | None = Field(
        default=None,
        description="시작 날짜 (YYYY-MM-DD) 또는 None",
    )
    end_date: str | None = Field(
        default=None,
        description="끝 날짜 (YYYY-MM-DD) 또는 None",
    )


class TimeSeriesItem(BaseModel):
    legend: str = Field(
        ...,
        description="시계열 라인의 범례(시리즈 이름). 예: 'DXY', 'WTI'",
        min_length=1,
    )
    date: list[str] = Field(
        default_factory=list,
        description="시계열 x축 날짜 리스트(ISO-8601 권장). 예: ['2025-08-01', '2025-08-02']",
    )
    value: list[float] = Field(
        default_factory=list,
        description="date와 동일한 길이의 값 리스트. 예: [102.1, 103.4]",
    )


class TimeSeriesResult(BaseModel):
    results: list[TimeSeriesItem] = Field(
        default_factory=list,
        description="생성된 시계열 차트 시리즈 목록",
    )
