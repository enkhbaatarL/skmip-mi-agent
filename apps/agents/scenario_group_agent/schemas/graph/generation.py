from __future__ import annotations

from typing import Any, Dict, List, Literal, Tuple

from pydantic import BaseModel, Field, conlist, model_validator

from apps.agents.scenario_group_agent.schemas.base import ApiModel
from apps.agents.scenario_group_agent.schemas.enums import (
    DirectionCode,
    SignpostStrength,
)


PRICE_TIERS: Tuple[str, ...] = (
    "strong_bull",
    "bull",
    "mild_bull",
    "neutral",
    "mild_bear",
    "bear",
    "strong_bear",
)
LIKELIHOOD_TIERS: Tuple[str, ...] = (
    "very_low",
    "low",
    "medium",
    "high",
    "very_high",
)

PriceTier = Literal[
    "strong_bull",
    "bull",
    "mild_bull",
    "neutral",
    "mild_bear",
    "bear",
    "strong_bear",
]
LikelihoodTier = Literal["very_low", "low", "medium", "high", "very_high"]
DimensionValueMap = Dict[str, str]


class C1BaseEvent(BaseModel):
    event_id: str = Field(default="", description="MIEvent 고유 ID (mi_event_id)")
    title: str = Field(default="", description="이벤트 한글 제목")
    event_type_l1_l2: str = Field(default="", description="'l1_code::l2_code' 형태")
    summary: str = Field(default="", description="이벤트 한 줄 요약 (one_line_summary)")
    driver: str = Field(default="", description="핵심 드라이버 (자유 서술)")


class C2LinkedRecords(BaseModel):
    window_days: int = Field(default=30, description="연관 Record 조회 시간창 (일)")
    records: List[Dict] = Field(default_factory=list, description="연관 Record 요약 리스트(stub)")


class C3HistoricalAnalog(BaseModel):
    analog_event_id: str = Field(default="", description="과거 유사 이벤트 ID")
    trajectory: List[str] = Field(default_factory=list, description="전개 단계 라벨 시퀀스")


class Stage1ContextPack(BaseModel):
    C1_base_event: C1BaseEvent = Field(description="필수 — 단일 Base Event")
    C2_linked_records: C2LinkedRecords = Field(
        default_factory=C2LinkedRecords,
        description="형식적 stub — 실제 구현은 본 파이프라인 범위 밖.",
    )
    C3_historical_analogs: List[C3HistoricalAnalog] = Field(
        default_factory=list,
        description="형식적 stub — RAG 미연결.",
    )
    C4_related_events: List[Dict] = Field(
        default_factory=list,
        description="형식적 stub — Graph 미연결.",
    )


class TemplateDimension(BaseModel):
    label: str = Field(description="Dimension 표시명")
    dim_key: str = Field(description="Dimension key")
    required: bool = Field(default=False, description="필수 여부")
    value_enums: List[str] = Field(
        default_factory=list,
        description="Dimension 값 후보 목록",
    )
    display_order: int = Field(default=999999, description="표시 순서")

    @model_validator(mode="after")
    def _validate_template_dimension(self):
        dim_key = str(self.dim_key).strip()
        if not dim_key:
            raise ValueError("dim_key is required.")
        enums = [str(value).strip() for value in self.value_enums if str(value).strip()]
        if len(enums) < 2:
            raise ValueError(f"value_enums must include at least two values: dim_key={dim_key}")
        if len(set(enums)) != len(enums):
            raise ValueError(f"value_enums contains duplicates: dim_key={dim_key}")
        self.dim_key = dim_key
        self.label = str(self.label).strip() or dim_key
        self.value_enums = enums
        return self

    def enum_items(self) -> list[dict[str, Any]]:
        return [
            {
                "id": enum_label,
                "label": enum_label,
                "tail": False,
            }
            for enum_label in self.value_enums
        ]

    def to_runtime_dimension(self) -> dict[str, Any]:
        return {
            "dim_key": self.dim_key,
            "label_ko": self.label,
            "description": self.label,
            "enum": self.enum_items(),
        }


class ScenarioTemplate(BaseModel):
    label_ko: str = Field(default="", description="템플릿 라벨")
    template_dimensions_total: int | None = Field(
        default=None,
        description="템플릿 전체 Dimension 수",
    )
    dimensions: List[TemplateDimension] = Field(
        default_factory=list,
        description="Dimension 템플릿 정의",
    )
    compatibility_rules: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="조합 호환성 규칙",
    )

    @model_validator(mode="after")
    def _validate_template(self):
        ordered = self.ordered_dimensions()
        if len(ordered) < 3:
            raise ValueError("template must include at least three dimensions.")
        dim_keys = [dimension.dim_key for dimension in ordered]
        if len(set(dim_keys)) != len(dim_keys):
            raise ValueError("template contains duplicate dim_key.")
        return self

    def ordered_dimensions(self) -> list[TemplateDimension]:
        return sorted(
            self.dimensions,
            key=lambda dimension: (dimension.display_order, dimension.dim_key),
        )

    def resolved_total(self) -> int:
        return self.template_dimensions_total or len(self.dimensions)


class SelectedDimension(BaseModel):
    dim_key: str = Field(description="템플릿의 dim_key")
    rationale: str = Field(
        description=(
            "선택 근거. 반드시 '(a)' 또는 '(c)' 또는 '(a)(c)' 코드로 시작하고, "
            "한국어 근거문을 1줄로 부연."
        )
    )


class ExcludedDimension(BaseModel):
    dim_key: str = Field(description="제외된 템플릿 dim_key")
    reason: str = Field(description="제외 사유 한국어 1줄.")


class Stage2DimensionSelection(BaseModel):
    template_id: str = Field(description="event_type_l1_l2 형태의 템플릿 키")
    template_dimensions_total: int = Field(description="템플릿 전체 Dim 수 (보통 8)")
    selected_dimensions: conlist(SelectedDimension, min_length=3, max_length=5) = Field(  # type: ignore[valid-type]
        description="선택된 Dim 3~5개. (b) 기준 사용 금지.",
    )
    excluded_dimensions: List[ExcludedDimension] = Field(
        default_factory=list,
        description="선택되지 않은 Dim + 사유.",
    )


class PerDimensionValue(BaseModel):
    dim_key: str = Field(description="템플릿의 dim_key")
    template_enum_full: List[str] = Field(
        default_factory=list,
        description="해당 Dim 의 원본 value_enums 전체.",
    )
    selected_enum: conlist(str, min_length=2, max_length=4) = Field(  # type: ignore[valid-type]
        description="채택한 Enum ID 2~4개. 인접 병합 금지.",
    )


class Stage3ValueSelection(BaseModel):
    per_dimension: List[PerDimensionValue] = Field(
        default_factory=list,
        description="Dim 별 Value 축소 결과 리스트.",
    )


class PriceDirection(BaseModel):
    jkm: PriceTier = Field(description="JKM 방향성 7단계")
    ttf: PriceTier = Field(description="TTF 방향성 7단계")
    hh: PriceTier = Field(description="Henry Hub 방향성 7단계")


class Scenario(BaseModel):
    scenario_id: str = Field(description="S_01 형태")
    title: str = Field(description="시장 참여자 관점 한 줄 요약. 공백과 문장부호를 포함해 100자 이내.")
    dimension_values: Dict[str, str] = Field(
        description="dim_key -> value 의 1:1 매핑.",
    )
    description: str = Field(
        description="3~5줄. 주요 Dim 가정치 조합 + 전개 양상 서술. 공백과 문장부호를 포함해 300~500자.",
    )
    derivation_rationale: str = Field(
        description="이 시나리오를 도출한 근거.",
    )
    price_direction: PriceDirection = Field(description="JKM/TTF/HH 7단계 방향성.")
    compatibility_passed: bool = Field(
        default=True,
        description="Compat Rule 통과 여부",
    )


class Stage4ScenarioSynthesis(BaseModel):
    cartesian_total: int = Field(description="Stage3 결과 기준 Dim Cartesian 조합 수.")
    filtered_by_compatibility: int = Field(
        description="Compat Rule 통과 후 남은 조합 수",
    )
    scenarios: conlist(Scenario, min_length=1, max_length=10) = Field(  # type: ignore[valid-type]
        description="최종 시나리오 5~7건 권장.",
    )


class Stage5RepairInstruction(BaseModel):
    scenario_ref: str = Field(description="수정 대상 입력 시나리오 참조값. 예: S_03")
    issue_type: Literal[
        "baseline_contrast",
        "value_diversity",
        "compatibility",
        "duplicate",
    ] = Field(description="Stage 5 quick validation 실패 유형")
    dim_key: str = Field(description="수정할 dimension key")
    current_value: str = Field(description="현재 값")
    recommended_value: str = Field(description="Stage 4 재생성 시 우선 반영할 권장 값")
    reason: str = Field(default="", description="수정 사유")


class MECECheck(BaseModel):
    mutually_exclusive: bool = Field(
        description="시나리오 간 동시 성립 사례 부재 시 True.",
    )


class Stage5Validation(BaseModel):
    mece_check: MECECheck = Field(default_factory=lambda: MECECheck(mutually_exclusive=True))
    likelihood_prior: Dict[str, LikelihoodTier] = Field(
        default_factory=dict,
        description="scenario_id -> 5단계 카테고리.",
    )


class ScenarioGroupMetadata(BaseModel):
    title: str = Field(description="시나리오 그룹명. 공백과 문장부호를 포함해 100자 이내.")
    description: str = Field(description="시나리오 그룹 설명. 공백과 문장부호를 포함해 300~400자.")


class ScenarioGenerationResult(ApiModel):
    stage1_context_pack: Stage1ContextPack | None = None
    stage2_dimension_selection: Stage2DimensionSelection | None = None
    stage3_value_selection: Stage3ValueSelection | None = None
    stage4_scenario_synthesis: Stage4ScenarioSynthesis | None = None
    stage5_validation: Stage5Validation | None = None
    scenario_group_metadata: ScenarioGroupMetadata | None = None
    scenario_count: int = 0
    template_id: str | None = None
    mi_event_id: int | str | None = None
    event_type_l1_l2: str | None = None
    cartesian_total: int = 0
    filtered_by_compatibility: int = 0
    mece_passed: bool = False
    scenario_group_id: int | str | None = None


class GeneratedSignpost(ApiModel):
    scenario_id: int
    signpost_id: int | None = None
    signpost_class: Literal["observation"] = "observation"
    label: str
    signpost_source: Literal["mi_record"] = "mi_record"
    direction: DirectionCode = DirectionCode.SUP
    strength: SignpostStrength | None = None
    rationale_ko: str = ""
    keyword_hints: list[str] = Field(default_factory=list)


class SignpostGenerationResult(ApiModel):
    scenario_group_id: int | None = None
    scenario_results: list[dict[str, Any]] = Field(default_factory=list)
    signposts: list[GeneratedSignpost] = Field(default_factory=list)
