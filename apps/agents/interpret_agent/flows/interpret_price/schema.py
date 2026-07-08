"""interpret_price flow 내부 도메인 DTO.

- 입력 파일(proposal_parameters, price_forecast)을 정규화한 파싱 구조
- 결정적(deterministic) 차이 지표(feature diff / price diff) 구조

API request/response schema는 `api_schema.py`에 둔다.
"""

from __future__ import annotations

from pydantic import Field

from apps.agents.interpret_agent.schemas.base import ApiModel


# --------------------------------------------------------------------------- #
# 정규화된 입력 구조
# --------------------------------------------------------------------------- #
class FeatureSeries(ApiModel):
    """단일 시나리오·단일 지역의 한 입력 feature 시계열.

    granularity에 따라 periods 키가 달라진다(monthly=YYYY-MM, annual=YYYY).
    """

    feature: str = Field(description="입력 feature 이름(예: Temperature)")
    region: str = Field(
        description="임의 geo 라벨(country/region/continent 무엇이든 들어온 값, 예: South Korea/Asia)"
    )
    geo_level: str | None = Field(
        default=None,
        description="region 라벨의 종류(country|region|continent). 라벨 품질 힌트용",
    )
    index: str | None = Field(
        default=None,
        description="상류가 명시한 대응 지수(JKM/TTF/HH). 없으면 None(코드가 매핑하지 않음)",
    )
    unit: str = Field(default="", description="feature 단위(예: °C, %)")
    granularity: str = Field(default="monthly", description="monthly | annual")
    qualifier: str | None = Field(
        default=None, description="feature 부가 구분(예: energy_source=Gas)"
    )
    group_keys: dict[str, str] = Field(
        default_factory=dict,
        description="비-시간 축(Country/Region/DegreeDayType 등) → 값. 매칭·표시의 원천",
    )
    periods: list[str] = Field(
        default_factory=list, description="정렬된 기간 키(YYYY-MM 또는 YYYY)"
    )
    values: list[float] = Field(default_factory=list)

    @property
    def label(self) -> str:
        return f"{self.feature}({self.qualifier})" if self.qualifier else self.feature


class ScenarioFeatures(ApiModel):
    scenario_id: str
    features: list[FeatureSeries] = Field(default_factory=list)


class PriceSeries(ApiModel):
    """단일 시나리오·단일 지수의 예측 가격 시계열."""

    index: str
    months: list[str] = Field(default_factory=list)
    values: list[float] = Field(default_factory=list)


class ScenarioPrices(ApiModel):
    scenario_id: str
    prices: list[PriceSeries] = Field(default_factory=list)


class InterpretInput(ApiModel):
    """해석 파이프라인의 정규화된 입력 묶음."""

    scenario_group_id: int | None = None
    base_scenario_id: str
    scenario_ids: list[str] = Field(default_factory=list)
    features: list[str] = Field(default_factory=list, description="등장하는 feature 목록")
    period_start: str | None = None
    period_end: str | None = None
    scenario_features: dict[str, ScenarioFeatures] = Field(default_factory=dict)
    scenario_prices: dict[str, ScenarioPrices] = Field(default_factory=dict)


# --------------------------------------------------------------------------- #
# 결정적 차이 지표(MI Base 대비)
# --------------------------------------------------------------------------- #
class DiffPoint(ApiModel):
    month: str
    diff: float = Field(description="scenario - base")
    base_value: float
    scenario_value: float


class DiffSegment(ApiModel):
    start: str
    end: str
    direction: str = Field(description="above(양수) / below(음수)")
    peak_month: str
    peak_diff: float


class AnomalyPoint(ApiModel):
    month: str
    kind: str = Field(description="이상치 유형(예: extreme_diff, negative_price, spike)")
    value: float
    detail: str = ""


class FeatureDiffMetric(ApiModel):
    """단일 시나리오·지역(feature) 기준 MI Base 대비 차이 지표."""

    feature: str
    region: str = Field(
        default="", description="임의 geo 라벨(country/region/continent 무엇이든)"
    )
    geo_level: str | None = Field(
        default=None, description="region 라벨의 종류(country|region|continent)"
    )
    index: str | None = Field(
        default=None, description="상류가 명시한 대응 지수(없으면 None, 매핑 안 함)"
    )
    unit: str = ""
    granularity: str = "monthly"
    qualifier: str | None = None
    group_keys: dict[str, str] = Field(default_factory=dict)
    mean_diff: float = 0.0
    max_pos: DiffPoint | None = None
    max_neg: DiffPoint | None = None
    notable_segments: list[DiffSegment] = Field(default_factory=list)
    convergence_from: str | None = None
    anomalies: list[AnomalyPoint] = Field(default_factory=list)
    auto_summary: str = ""

    @property
    def label(self) -> str:
        return f"{self.feature}({self.qualifier})" if self.qualifier else self.feature


class PriceDiffMetric(ApiModel):
    """단일 시나리오·지수 기준 MI Base 대비 예측 가격 차이 지표."""

    index: str
    unit: str = "$/MMBtu"
    mean_base: float = 0.0
    mean_scenario: float = 0.0
    mean_diff: float = 0.0
    max_pos: DiffPoint | None = None
    max_neg: DiffPoint | None = None
    convergence_from: str | None = None
    anomalies: list[AnomalyPoint] = Field(default_factory=list)
    auto_summary: str = ""


class ScenarioDiffBundle(ApiModel):
    """한 시나리오의 feature/price 결정적 지표 묶음."""

    scenario_id: str
    feature_diffs: list[FeatureDiffMetric] = Field(default_factory=list)
    price_diffs: list[PriceDiffMetric] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)
