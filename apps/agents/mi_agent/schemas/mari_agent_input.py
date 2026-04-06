from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ContentProvider(StrEnum):
    OMDIA = "OMDIA"
    LSEG = "LSEG"
    WOODMAC = "WOODMAC"


class ContentProviderAccess(BaseModel):
    """content provider별 접근 가능한 상품 번호 매핑."""

    content_provider: ContentProvider = Field(
        ...,
        description="콘텐츠 프로바이더명",
    )
    authorized_product_nums: list[int] = Field(
        default_factory=list,
        description="해당 프로바이더에서 접근 가능한 상품 번호 리스트",
    )


class ContentProviderRdbAccess(BaseModel):
    """RDB 검색에 적용할 접근 권한 정보."""

    authorized_product_nums: list[int] = Field(
        default_factory=list,
        description="접근 가능한 상품 번호 목록",
    )


class MariAgentInput(BaseModel):
    """MI Agent 입력 스키마."""

    user_query: str | None = Field(
        default=None,
        description="사용자 입력 질의",
    )
    histories: list[dict] = Field(
        default_factory=list,
        description="대화 히스토리",
    )
    search_sources: list[str] = Field(
        default_factory=list,
        description="검색 소스 목록",
        examples=[["web", "rdb", "vdb"]],
        json_schema_extra={
            "default": ["web", "rdb", "vdb"],
            "default_factory": "list",
        },
    )
    company_code: str = Field(
        ...,
        description="회사 코드",
    )
    user_num: int | None = Field(
        default=None,
        description="사용자 번호(현재는 Agent에서 미사용. 요건 없음)",
    )
    content_provider_rdb_accesses: ContentProviderRdbAccess = Field(
        default_factory=ContentProviderRdbAccess,
        description="RDB 검색에 적용할 접근 권한 정보.",
    )
    content_provider_vdb_accesses: list[ContentProviderAccess] = Field(
        default_factory=list,
        description=(
            "VDB 검색에 적용할 콘텐츠 프로바이더별 접근 권한 목록. "
            "프로바이더명과 해당 프로바이더에서 접근 가능한 상품 번호를 포함한다."
        ),
    )
    rdb_search_metadata_repo_id: UUID | None = Field(
        default=None,
        description=(
            "RDB 메타데이터 설명 문서가 저장된 벡터DB 리포지토리 식별자. "
            "미지정 시 환경변수(RDB_SEARCH_METADATA_REPO_ID) 값을 사용한다."
        ),
    )

    @model_validator(mode="after")
    def require_search_sources(self) -> "MariAgentInput":
        if "search_sources" not in self.model_fields_set:
            msg = "search_sources is required"
            raise ValueError(msg)
        return self

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                # SKENS
                {
                    "company_code": "2013",
                    "user_num": 1000053,
                    "content_provider_rdb_accesses": {
                        "authorized_product_nums": [70038, 70033, 70032, 70037, 70029, 70031, 70043, 70039, 70045, 70048, 70028, 70049]
                    },
                    "content_provider_vdb_accesses": [
                        {
                            "authorized_product_nums": [
                            70008, 70053
                            ],
                            "content_provider": "LSEG"
                        },
                        {
                            "content_provider": "OMDIA",
                            "authorized_product_nums": [70052]
                        }
                    ],
                    "user_query": "최근12개월간 Brent Crude 1개월물 가격이 급변동한 시점을 알려줘",
                    "search_sources": ["rdb"],
                },                
                # SKHY
                # {
                #     "company_code": "2015",
                #     "user_num": 1000053,
                #     "content_provider_rdb_accesses": {
                #         "authorized_product_nums": [
                #             #70008, 70012, 70011, 70010, 70016, 70017, 70018, 70036, 70029, 70038, 70051, 70063, 70061, 70060, 70059, 70058, 70057, 70056, 70055, 70054
                #             70012, 70011, 70010, 70016, 70017, 70018, 70036, 70029, 70038, 70051, 70063, 70061, 70060, 70059, 70058, 70057, 70056, 70055, 70054
                #         ]
                #     },
                #     "content_provider_vdb_accesses": [
                #         {
                #             "authorized_product_nums": [
                #             70008, 70053
                #             ],
                #             "content_provider": "LSEG"
                #         },
                #         {
                #             "content_provider": "OMDIA",
                #             "authorized_product_nums": [70052]
                #         }
                #     ],
                #     # "user_query": "Please tell me the total volume of DRAM shipments for the third quarter of 2025, calculated based on 1Gb equivalent",
                #     "user_query": "최근12개월간 Brent Crude 1개월물 가격이 급변동한 시점을 알려줘",
                #     "search_sources": ["vdb"],
                # },
            ],
        },
    )
