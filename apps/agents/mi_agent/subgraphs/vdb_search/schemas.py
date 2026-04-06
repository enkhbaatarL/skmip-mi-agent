from __future__ import annotations

from pydantic import BaseModel, Field

from apps.agents.mi_agent.schemas.mari_agent_input import ContentProviderAccess


class VDBSearchInput(BaseModel):
    company_code: str = Field(
        ...,
        description="회사 코드",
    )
    user_num: int | None = Field(
        default=None,
        description="사용자 번호",
    )
    rewritten_query: str | None = Field(
        default=None,
        description="사용자 입력 질의",
    )
    histories: list[dict] = Field(default_factory=list, description="대화 히스토리")
    content_provider_vdb_accesses: list[ContentProviderAccess] = Field(
        default_factory=list,
        description="VDB 검색에 적용할 콘텐츠 프로바이더별 접근 권한 목록",
    )

class VdbStructuredQuery(BaseModel):
    rewritten_query: str = Field(
        ...,
        description=(
            "사용자 질의 ()"
        ),
        examples=[
            "China AI semiconductor shipments in Q4 2025",
            "SoC market outlook for 2024 and 2025",
            "Server GPU demand and server silicon trends",
        ],
    )

    keywords: list[str] = Field(
        ...,
        description=(
            "영문 검색용 키워드 목록. "
            "사용자 질의의 직접 키워드뿐 아니라 리포트 검색 recall을 높이기 위한 "
            "상위 개념, 정규화된 산업 용어, 확장 검색 키워드를 포함한다."
        ),
        min_length=4,
        max_length=10,
        examples=[
            [
                "China AI semiconductor",
                "AI chips",
                "semiconductor shipments",
                "China semiconductor market",
                "AI processors",
                "quarterly update",
            ]
        ],
    )

    keywords_kr: list[str] = Field(
        default_factory=list,
        description=(
            "한글 검색용 키워드 목록. "
            "사용자 질의의 직접 키워드와 함께, 질의 해석 및 검색 보조에 도움이 되는 "
            "상위 개념 또는 정규화된 산업 용어를 포함한다."
        ),
        max_length=10,
        examples=[
            [
                "중국 AI 반도체",
                "AI 칩",
                "반도체 출하량",
                "중국 반도체 시장",
                "AI 프로세서",
                "분기 업데이트",
            ]
        ],
    )

    year: int | None = Field(
        default=None,
        description=(
            "대표 단일 연도. "
            "질의에 하나의 대표 연도를 명확히 특정할 수 있을 때만 설정한다."
        ),
        examples=[2025],
    )

    years: list[int] = Field(
        default_factory=list,
        description=(
            "질의에서 식별된 전체 관련 연도 목록. "
            "예: '2024~2025 SoC 시장 전망'이면 [2024, 2025]."
        ),
        examples=[[2024, 2025]],
    )

    period_key: str | None = Field(
        default=None,
        description=(
            "정규화된 대표 기간 키. "
            "예: 4Q25, 1H25, 2025-10, FY24, 2025."
        ),
        examples=["4Q25", "1H25", "2025-10", "FY24", "2025"],
    )

    period_start_at: str | None = Field(
        default=None,
        description=(
            "대표 기간의 시작 시각(UTC ISO-8601). "
            "예: 2025-10-01T00:00:00Z"
        ),
        examples=["2025-10-01T00:00:00Z"],
    )

    period_end_at: str | None = Field(
        default=None,
        description=(
            "대표 기간의 종료 시각(UTC ISO-8601). "
            "예: 2025-12-31T23:59:59Z"
        ),
        examples=["2025-12-31T23:59:59Z"],
    )

    period_aliases: list[str] = Field(
        default_factory=list,
        description=(
            "대표 기간을 검색어 또는 문서 title에서 다양하게 표현할 수 있는 별칭 목록. "
            "예: ['4Q25', 'Q4 2025', '2025 Q4', 'quarter 4 2025']"
        ),
        examples=[["4Q25", "Q4 2025", "2025 Q4", "quarter 4 2025"]],
    )

class VectorSourceModel(BaseModel):
    source: str = Field(..., description="벡터 소스 경로/ID")
    title: str = Field(..., description="문서 제목")
    product_num: int = Field(..., description="내부 GDS 식별 번호")
    product_data_num: str | None = Field(default=None, description="내부 데이터 식별자")
    document_id: str | None = Field(default=None, description="문서 고유 ID")
    content: str = Field(default="", description="검색된 본문 내용")


class VDBSearchItem(BaseModel):
    content: str = Field(
        ...,
        title="검색된 본문 내용",
        description="검색 쿼리에 대응하는 문서의 본문 내용 조각입니다.",
    )
    metadata: VectorSourceModel = Field(
        ...,
        title="문서 메타데이터",
        description="검색된 문서의 출처 및 식별 정보입니다.",
    )
    score: float = Field(
        ...,
        title="검색 점수",
        description="검색 쿼리와의 일치도를 나타내는 점수입니다. 높은 점수는 더 높은 관련성을 의미합니다.",
    )


class VDBSearchOutput(BaseModel):
    vector_sources: list[VDBSearchItem] = Field(
        default_factory=list,
        description="VectorDB에서 수집한 문서 목록 (본문 및 출처 메타데이터 포함)",
    )
