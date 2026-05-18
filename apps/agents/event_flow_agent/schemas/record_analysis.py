# apps/agents/event_flow_agent/schemas/record_analysis.py
# kmj20260417금
"""
record 분석 결과 스키마 모듈

역할:
- 개별 원천 record를 LLM으로 분석한 결과 구조를 정의한다.
- category, entity, timing, region, supply/demand 관점 등의 구조화 정보를 표현한다.

포함 정보:
- 엔티티 정보(Entity)
- 이벤트 시점(EventTiming)
- category 분석(CategoryAnalysis)
- record 전체 분석 결과(RecordAnalysis)

설계 의도:
- 비정형 뉴스/기사 텍스트를 event 추출 가능한 구조화 데이터로 변환
- 허용 taxonomy 조합을 검증하고, 중복 category를 정리하는 규칙 포함
- 이후 event 추출 단계에서 여러 record를 비교/통합할 수 있도록 표준 구조 제공
"""

from __future__ import annotations

from enum import Enum
from typing import List

from pydantic import BaseModel, Field, model_validator

from apps.agents.event_flow_agent.configs.event_type_taxonomy import (
    ALLOWED_CATEGORY_PAIRS,
    CATEGORY_GUIDE,
)


class EntityType(str, Enum):
    country = "country"
    company = "company"
    facility = "facility"
    organization = "organization"
    region = "region"
    other = "other"


class Entity(BaseModel):
    name: str = Field(description="엔티티 정규 명칭")
    entity_type: EntityType = Field(description="엔티티 유형")


class OccurrencePrecision(str, Enum):
    exact = "exact"
    day = "day"
    month = "month"
    quarter = "quarter"
    year = "year"
    unknown = "unknown"


class SupplyDemandSide(str, Enum):
    supply = "supply"
    demand = "demand"
    both = "both"
    none = "none"
    unclear = "unclear"


class EventTiming(BaseModel):
    occurrence_time: str = Field(
        default="",
        description=(
            "이벤트 실제 발생 시점. ISO-8601 또는 빈 문자열. 예: '2026-03-03T00:00:00Z'"
        )
    )
    occurrence_time_precision: OccurrencePrecision = Field(
        default=OccurrencePrecision.unknown,
        description="occurrence_time_precision: exact / day / month / quarter / year / unknown",
    )


class CategoryAnalysis(BaseModel):
    level_1: str = Field(description="이벤트 유형 대분류 코드")
    level_2: str = Field(description="이벤트 유형 소분류 코드")
    entities: List[Entity] = Field(default_factory=list)
    event_timing: EventTiming = Field(default_factory=EventTiming)
    regions: List[str] = Field(default_factory=list)
    supply_demand_side: SupplyDemandSide = Field(default=SupplyDemandSide.unclear)
    score: float = Field(default=0.0, ge=0, le=10)
    reason: str = Field(default="")

    @model_validator(mode="after")
    def validate_category_pair(self) -> "CategoryAnalysis":
        if (self.level_1, self.level_2) not in ALLOWED_CATEGORY_PAIRS:
            raise ValueError(
                f"유효하지 않은 category 조합: ({self.level_1}, {self.level_2}). "
                "event_type_taxonomy.json의 level_1_code + level_2_code 조합만 허용됩니다."
            )
        return self


class RecordAnalysis(BaseModel):
    categories: List[CategoryAnalysis] = Field(default_factory=list)
    analysis_time: str = Field(default="")

    @model_validator(mode="after")
    def deduplicate_categories(self) -> "RecordAnalysis":
        dedup: dict[tuple[str, str], CategoryAnalysis] = {}
        for category in self.categories:
            key = (category.level_1, category.level_2)
            if key not in dedup or category.score > dedup[key].score:
                dedup[key] = category
        self.categories = list(dedup.values())
        return self