# apps/agents/event_flow_agent/schemas/record_analysis.py

from __future__ import annotations
from enum import Enum
from typing import List
from pydantic import BaseModel, Field, model_validator

class EntityType(str, Enum):
    country = "country"
    company = "company"
    facility = "facility"
    organization = "organization"
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
        description="이벤트 실제 발생 시점. ISO-8601 또는 빈 문자열",
    )
    occurrence_time_precision: OccurrencePrecision = Field(
        default=OccurrencePrecision.unknown,
        description="occurrence_time 정밀도",
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