# Copyright (c) 2026 SK Innovation E&S.

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import math
from types import MappingProxyType
from typing import Literal

from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode


VARIATION_POLICY_RELEASE = "bounded-expert-v3"

VariationMode = Literal["strict", "balanced", "exploratory"]
VariationDirection = Literal["increase", "decrease", "unchanged"]
VariationSeverity = Literal["weak", "medium", "strong"]
VariationDuration = Literal["short", "medium", "long"]
VariationScope = Literal["narrow", "medium", "broad"]
VariationOffset = Literal["none", "partial", "strong"]
VariationConfidence = Literal["low", "medium", "high"]
VariationSiblingPosition = Literal["lower", "middle", "upper", "standalone"]
VariationMethod = Literal[
    "relative",
    "additive",
    "integer_step",
    "atomic_share",
]


@dataclass(frozen=True, slots=True)
class ParameterVariationPolicy:
    parameter_name: str
    unit: str
    method: VariationMethod
    weak: float
    medium: float
    strong: float
    zero_reference_weak: float = 0.0
    zero_reference_medium: float = 0.0
    zero_reference_strong: float = 0.0
    policy_note_ko: str = ""

    def magnitude(self, severity: VariationSeverity) -> float:
        return float(getattr(self, severity))

    def zero_reference_magnitude(self, severity: VariationSeverity) -> float:
        return float(getattr(self, f"zero_reference_{severity}"))


@dataclass(frozen=True, slots=True)
class VariationCalculation:
    proposed_value: float
    applied_severity: VariationSeverity
    calculation_ko: str
    clipped: bool = False
    applied_magnitude: float = 0.0
    profile_position: float | None = None


@dataclass(frozen=True, slots=True)
class VariationFactors:
    """Reviewable qualitative factors used only inside a severity guardrail.

    These factors cannot activate a Parameter or slot and never change the
    requested direction.  They only position a bounded assumption between the
    lower edge and cap of its already-approved severity band.
    """

    duration: VariationDuration
    scope: VariationScope
    offset: VariationOffset
    confidence: VariationConfidence
    sibling_position: VariationSiblingPosition
    rationale_ko: str


_DURATION_SCORE: Mapping[VariationDuration, float] = MappingProxyType(
    {"short": 0.0, "medium": 0.5, "long": 1.0},
)
_SCOPE_SCORE: Mapping[VariationScope, float] = MappingProxyType(
    {"narrow": 0.0, "medium": 0.5, "broad": 1.0},
)
_OFFSET_SCORE: Mapping[VariationOffset, float] = MappingProxyType(
    {"strong": 0.0, "partial": 0.5, "none": 1.0},
)
_CONFIDENCE_SCORE: Mapping[VariationConfidence, float] = MappingProxyType(
    {"low": 0.0, "medium": 0.5, "high": 1.0},
)
_SIBLING_POSITION_ADJUSTMENT: Mapping[VariationSiblingPosition, float] = MappingProxyType(
    {
        "lower": -0.15,
        "middle": 0.0,
        "upper": 0.15,
        "standalone": 0.0,
    },
)


@dataclass(frozen=True, slots=True)
class ConditionalRoutingPolicy:
    """Bound one Lever-to-parameter inference without inventing a new target."""

    lever_code: str
    parameter_name: str
    allow_policy_recovery: bool
    required_context_terms: tuple[str, ...]
    direction_map: Mapping[str, VariationDirection]
    increase_mechanism_ko: str
    decrease_mechanism_ko: str
    target_scope_ko: str
    eligibility_note_ko: str
    exclusion_note_ko: str

    def direction_for(self, value: object) -> VariationDirection | None:
        return self.direction_map.get(str(value or "").strip().casefold())

    def has_required_context(self, text: object) -> bool:
        normalized = str(text or "").casefold()
        return any(term.casefold() in normalized for term in self.required_context_terms)


# These values are proposal guardrails, not forecasts.  They intentionally encode
# parameter-specific, reviewable first-pass magnitudes instead of one universal %.
# An observed/derived numeric value remains eligible outside these steps when its
# source and calculation are explicitly supplied; the normal capability min/max
# validation still applies.
_POLICIES = {
    "GDP": ParameterVariationPolicy(
        "GDP",
        "fractional_yoy_growth",
        "additive",
        0.0025,
        0.005,
        0.01,
        policy_note_ko="연간 성장률에 25/50/100bp를 가감하는 보수적 초기값",
    ),
    "PMI": ParameterVariationPolicy(
        "PMI",
        "index",
        "additive",
        0.5,
        1.5,
        3.0,
        policy_note_ko="PMI 지수에 0.5/1.5/3.0pt를 가감",
    ),
    "PowerMix": ParameterVariationPolicy(
        "PowerMix",
        "fraction",
        "atomic_share",
        0.01,
        0.03,
        0.05,
        policy_note_ko="국가·연도 전체 벡터 합계 1을 유지하며 원별 share 이동폭을 제한",
    ),
    "Temperature": ParameterVariationPolicy(
        "Temperature",
        "celsius",
        "additive",
        0.5,
        1.5,
        3.0,
        policy_note_ko="기준 기온에 0.5/1.5/3.0°C를 가감",
    ),
    "Population": ParameterVariationPolicy(
        "Population",
        "thousand_people",
        "relative",
        0.001,
        0.003,
        0.01,
        1.0,
        5.0,
        10.0,
        "명시된 인구·이주 경로가 있을 때 기준 인구의 0.1/0.3/1.0%를 가감",
    ),
    "HurricaneIntensity": ParameterVariationPolicy(
        "HurricaneIntensity",
        "integer_intensity",
        "integer_step",
        1.0,
        2.0,
        3.0,
        1.0,
        2.0,
        3.0,
        "허리케인 강도 단계를 1/2/3단계 이동하고 capability 0~4를 준수",
    ),
    "LiqProdAdjustment": ParameterVariationPolicy(
        "LiqProdAdjustment",
        "Mt LNG/month",
        "relative",
        0.05,
        0.15,
        0.30,
        0.05,
        0.20,
        0.50,
        "검증된 설비·Train의 월 생산량을 5/15/30% 조정",
    ),
    "LiqUtilAdjustment": ParameterVariationPolicy(
        "LiqUtilAdjustment",
        "utilization_fraction",
        "additive",
        0.03,
        0.08,
        0.15,
        0.03,
        0.08,
        0.15,
        "검증된 설비·Train 이용률에 3/8/15%p를 가감",
    ),
    "PipelineAdjustment": ParameterVariationPolicy(
        "PipelineAdjustment",
        "Mt/y",
        "relative",
        0.05,
        0.15,
        0.30,
        0.20,
        0.75,
        1.50,
        "검증된 pipeline 흐름의 연간 물량을 5/15/30% 조정",
    ),
    "RegasAdjustment": ParameterVariationPolicy(
        "RegasAdjustment",
        "Mt LNG/month",
        "relative",
        0.05,
        0.15,
        0.30,
        0.05,
        0.20,
        0.50,
        "검증된 터미널의 월 기화 물량을 5/15/30% 조정",
    ),
    "SupplyDisruption": ParameterVariationPolicy(
        "SupplyDisruption",
        "Mt",
        "additive",
        0.05,
        0.20,
        0.50,
        0.05,
        0.20,
        0.50,
        "국가·기간별 공급 차질량에 0.05/0.20/0.50Mt를 가감",
    ),
    "PNG Contract Volume": ParameterVariationPolicy(
        "PNG Contract Volume",
        "Mt LNG",
        "relative",
        0.03,
        0.10,
        0.20,
        0.05,
        0.20,
        0.50,
        "검증된 송·수입국 계약 물량을 3/10/20% 조정",
    ),
    "ShippingCost": ParameterVariationPolicy(
        "ShippingCost",
        "$/d",
        "relative",
        0.05,
        0.15,
        0.30,
        5_000.0,
        15_000.0,
        30_000.0,
        "운항·우회 경로 근거가 있는 일 운송비를 5/15/30% 조정",
    ),
    "RegionalProductionAdjustment": ParameterVariationPolicy(
        "RegionalProductionAdjustment",
        "Bcm",
        "relative",
        0.03,
        0.10,
        0.20,
        0.50,
        2.0,
        5.0,
        "검증된 지역의 연간 생산량을 3/10/20% 조정",
    ),
    "ShippingFuelCost": ParameterVariationPolicy(
        "ShippingFuelCost",
        "$/tonne",
        "relative",
        0.05,
        0.15,
        0.30,
        20.0,
        60.0,
        120.0,
        "선박 연료 가격 근거가 있는 연도의 비용을 5/15/30% 조정",
    ),
    "CanalToll": ParameterVariationPolicy(
        "CanalToll",
        "$/crossing",
        "relative",
        0.05,
        0.15,
        0.30,
        50_000.0,
        200_000.0,
        500_000.0,
        "명시된 운하·연도의 통항료를 5/15/30% 조정",
    ),
    "Suez Canal Cost": ParameterVariationPolicy(
        "Suez Canal Cost",
        "$/crossing",
        "relative",
        0.05,
        0.15,
        0.30,
        50_000.0,
        200_000.0,
        500_000.0,
        "명시된 Suez·연도의 통항료를 5/15/30% 조정",
    ),
    "Panama Canal Cost": ParameterVariationPolicy(
        "Panama Canal Cost",
        "$/crossing",
        "relative",
        0.05,
        0.15,
        0.30,
        50_000.0,
        200_000.0,
        500_000.0,
        "명시된 Panama·연도의 통항료를 5/15/30% 조정",
    ),
}

PARAMETER_VARIATION_POLICIES: Mapping[str, ParameterVariationPolicy] = MappingProxyType(
    _POLICIES,
)


_ROUTE_DIRECTION_MAP: Mapping[str, VariationDirection] = MappingProxyType(
    {
        "disrupt": "increase",
        "increase": "increase",
        "recover": "decrease",
        "decrease": "decrease",
    },
)

_REGIONAL_SPREAD_SHIPPING_DIRECTION_MAP: Mapping[str, VariationDirection] = MappingProxyType(
    {
        "increase": "increase",
        "recover": "increase",
        "disrupt": "increase",
        "decrease": "decrease",
    },
)

# These policies govern whether a qualitative Scenario branch may be projected to
# an existing model input.  They never create a parameter, slot, or numeric value.
# Only ShippingCost currently permits deterministic recovery after an all-N/A LLM
# response.  The adjacent policies are explicit negative boundaries so fuel and
# toll values cannot be inferred from a generic route disruption.
_CONDITIONAL_ROUTING_POLICIES = {
    ("route_disruption", "ShippingCost"): ConditionalRoutingPolicy(
        lever_code="route_disruption",
        parameter_name="ShippingCost",
        allow_policy_recovery=True,
        required_context_terms=(
            "통항",
            "항로",
            "우회",
            "지연",
            "선박",
            "선적",
            "운항",
            "항만",
            "대기",
            "병목",
            "폐쇄",
            "봉쇄",
            "정상화",
            "route",
            "transit",
            "detour",
            "delay",
            "vessel",
            "shipping",
            "port",
        ),
        direction_map=_ROUTE_DIRECTION_MAP,
        increase_mechanism_ko="항차 시간·선복 수요 증가 또는 가용 선복 축소",
        decrease_mechanism_ko="항차 시간·선복 수요 정상화 또는 가용 선복 회복",
        target_scope_ko="Year별 전역 LNG charter rate",
        eligibility_note_ko=(
            "선택 branch에 LNG 물리 통항·우회·지연·대기·병목 또는 그 회복과 "
            "direction/scope/time_window가 있으면, 관측 운임 수치가 없어도 항차 시간과 "
            "선복 가용성 경로를 통해 Year별 전역 LNG charter rate에 bounded assumption을 허용"
        ),
        exclusion_note_ko=("가격 전망만 있거나 물리 운송 경로·방향·범위·기간 중 하나라도 없으면 제외"),
    ),
    ("route_disruption", "ShippingFuelCost"): ConditionalRoutingPolicy(
        lever_code="route_disruption",
        parameter_name="ShippingFuelCost",
        allow_policy_recovery=False,
        required_context_terms=(
            "ifo380",
            "선박 연료 가격",
            "선박 연료비",
            "bunker price",
            "bunker cost",
        ),
        direction_map=_ROUTE_DIRECTION_MAP,
        increase_mechanism_ko="Year별 LNG 선박 IFO380 가격 또는 비용 상승",
        decrease_mechanism_ko="Year별 LNG 선박 IFO380 가격 또는 비용 하락",
        target_scope_ko="Year별 LNG 선박 IFO380 연료비",
        eligibility_note_ko=("Year별 LNG 선박 IFO380 또는 bunker 가격·비용 방향이 직접 제시된 경우만 검토"),
        exclusion_note_ko=("우회 거리·통항 차질만으로 연료가격을 대신 추론하지 않으며 정책 복구도 하지 않음"),
    ),
    ("route_disruption", "CanalToll"): ConditionalRoutingPolicy(
        lever_code="route_disruption",
        parameter_name="CanalToll",
        allow_policy_recovery=False,
        required_context_terms=(
            "수에즈 통항료",
            "파나마 통항료",
            "suez toll",
            "panama toll",
            "canal toll",
        ),
        direction_map=_ROUTE_DIRECTION_MAP,
        increase_mechanism_ko="Suez 또는 Panama 통항료 상승",
        decrease_mechanism_ko="Suez 또는 Panama 통항료 하락",
        target_scope_ko="Suez 또는 Panama·Year별 통항료",
        eligibility_note_ko=("Suez 또는 Panama와 Year별 통항료 방향이 직접 제시된 경우만 검토"),
        exclusion_note_ko=("해협·항만·일반 운하 차질을 Suez/Panama 통항료로 치환하지 않으며 정책 복구도 하지 않음"),
    ),
    ("route_disruption", "Suez Canal Cost"): ConditionalRoutingPolicy(
        lever_code="route_disruption",
        parameter_name="Suez Canal Cost",
        allow_policy_recovery=False,
        required_context_terms=(
            "수에즈 통항료",
            "suez toll",
            "suez canal cost",
        ),
        direction_map=_ROUTE_DIRECTION_MAP,
        increase_mechanism_ko="Suez 통항료 상승",
        decrease_mechanism_ko="Suez 통항료 하락",
        target_scope_ko="Suez·Year별 통항료",
        eligibility_note_ko=("Suez와 Year별 통항료 방향이 직접 제시된 경우만 검토"),
        exclusion_note_ko=("Panama·해협·항만·일반 운하 차질을 Suez 통항료로 치환하지 않음"),
    ),
    ("route_disruption", "Panama Canal Cost"): ConditionalRoutingPolicy(
        lever_code="route_disruption",
        parameter_name="Panama Canal Cost",
        allow_policy_recovery=False,
        required_context_terms=(
            "파나마 통항료",
            "panama toll",
            "panama canal cost",
        ),
        direction_map=_ROUTE_DIRECTION_MAP,
        increase_mechanism_ko="Panama 통항료 상승",
        decrease_mechanism_ko="Panama 통항료 하락",
        target_scope_ko="Panama·Year별 통항료",
        eligibility_note_ko=("Panama와 Year별 통항료 방향이 직접 제시된 경우만 검토"),
        exclusion_note_ko=("Suez·해협·항만·일반 운하 차질을 Panama 통항료로 치환하지 않음"),
    ),
    ("regional_price_spread", "ShippingCost"): ConditionalRoutingPolicy(
        lever_code="regional_price_spread",
        parameter_name="ShippingCost",
        allow_policy_recovery=True,
        required_context_terms=(
            "카고",
            "화물",
            "선적",
            "항로",
            "운송비",
            "보험비",
            "재정거래",
            "유럽향",
            "아시아행",
            "배분",
            "cargo",
            "vessel",
            "shipping",
            "freight",
            "charter",
            "arbitrage",
            "reroute",
            "allocation",
        ),
        direction_map=_REGIONAL_SPREAD_SHIPPING_DIRECTION_MAP,
        increase_mechanism_ko="장거리 cargo 전환·재정거래 재개 또는 운송 불확실성 확대로 선복 수요 증가",
        decrease_mechanism_ko="장거리 cargo 전환·재정거래 축소 또는 운송 불확실성 완화로 선복 수요 감소",
        target_scope_ko="Year별 전역 LNG charter rate",
        eligibility_note_ko=(
            "가격 spread 자체가 아니라 LNG cargo의 지역 간 배분·재정거래·운송 경로 변화가 명시되고 "
            "direction/scope/time_window가 있을 때만 전역 charter rate bounded assumption을 허용"
        ),
        exclusion_note_ko=(
            "가격·프리미엄 방향만 있거나 물리 cargo 배분·운송 경로가 없으면 제외하며, "
            "선박 연료가격·운하 통행료·설비·공급량으로 확장하지 않음"
        ),
    ),
}

CONDITIONAL_ROUTING_POLICIES: Mapping[
    tuple[str, str],
    ConditionalRoutingPolicy,
] = MappingProxyType(_CONDITIONAL_ROUTING_POLICIES)


def get_conditional_routing_policy(
    *,
    lever_code: object,
    parameter_name: object,
) -> ConditionalRoutingPolicy | None:
    return CONDITIONAL_ROUTING_POLICIES.get(
        (
            str(lever_code or "").strip().casefold(),
            str(parameter_name or "").strip(),
        ),
    )


def conditional_routing_policy_prompt_payload(
    *,
    lever_code: object,
    parameter_name: object,
) -> dict[str, object] | None:
    policy = get_conditional_routing_policy(
        lever_code=lever_code,
        parameter_name=parameter_name,
    )
    if policy is None:
        return None
    return {
        "bounded_assumption_allowed": policy.allow_policy_recovery,
        "eligibility_rule_ko": policy.eligibility_note_ko,
        "exclusion_rule_ko": policy.exclusion_note_ko,
    }


def get_parameter_variation_policy(parameter_name: str) -> ParameterVariationPolicy:
    policy = PARAMETER_VARIATION_POLICIES.get(parameter_name)
    if policy is None:
        raise MIBaseError(
            ErrorCode.INVALID_REQUEST,
            detail=f"No variation policy is registered for parameter: {parameter_name}",
        )
    return policy


def policy_prompt_payload(parameter_name: str) -> dict[str, object]:
    policy = get_parameter_variation_policy(parameter_name)
    return {
        "release": VARIATION_POLICY_RELEASE,
        "parameter_name": policy.parameter_name,
        "unit": policy.unit,
        "method": policy.method,
        "severity_steps": {
            "weak": policy.weak,
            "medium": policy.medium,
            "strong": policy.strong,
        },
        "zero_reference_steps": {
            "weak": policy.zero_reference_weak,
            "medium": policy.zero_reference_medium,
            "strong": policy.zero_reference_strong,
        },
        "profile_contract": {
            "duration": ["short", "medium", "long"],
            "scope": ["narrow", "medium", "broad"],
            "offset": ["none", "partial", "strong"],
            "confidence": ["low", "medium", "high"],
            "sibling_position": ["lower", "middle", "upper", "standalone"],
            "rule": (
                "The server positions a bounded assumption inside the selected severity band. "
                "Sibling position is comparison-only and cannot activate a parameter or slot."
            ),
        },
        "policy_note_ko": policy.policy_note_ko,
    }


def allowed_assumption_severities(mode: VariationMode) -> tuple[VariationSeverity, ...]:
    if mode == "strict":
        return ()
    if mode == "balanced":
        return ("weak", "medium")
    if mode == "exploratory":
        return ("weak", "medium", "strong")
    raise MIBaseError(
        ErrorCode.INVALID_REQUEST,
        detail=f"Unsupported model parameter variation mode: {mode}",
    )


def _bounded_severity(
    severity: VariationSeverity,
    mode: VariationMode,
) -> tuple[VariationSeverity, bool]:
    allowed = allowed_assumption_severities(mode)
    if not allowed:
        raise MIBaseError(
            ErrorCode.INVALID_REQUEST,
            detail="strict variation mode does not allow bounded assumptions",
        )
    if severity in allowed:
        return severity, False
    return allowed[-1], True


def _variation_profile_position(factors: VariationFactors) -> float:
    evidence_score = (
        _DURATION_SCORE[factors.duration]
        + _SCOPE_SCORE[factors.scope]
        + _OFFSET_SCORE[factors.offset]
        + _CONFIDENCE_SCORE[factors.confidence]
    ) / 4.0
    return min(
        1.0,
        max(
            0.0,
            evidence_score + _SIBLING_POSITION_ADJUSTMENT[factors.sibling_position],
        ),
    )


def _severity_band(
    policy: ParameterVariationPolicy,
    severity: VariationSeverity,
    *,
    zero_reference: bool,
) -> tuple[float, float]:
    magnitude = policy.zero_reference_magnitude if zero_reference else policy.magnitude
    upper = magnitude(severity)
    if severity == "weak":
        lower = upper * 0.5
    elif severity == "medium":
        lower = magnitude("weak")
    else:
        lower = magnitude("medium")
    return min(lower, upper), max(lower, upper)


def _profiled_magnitude(
    policy: ParameterVariationPolicy,
    severity: VariationSeverity,
    factors: VariationFactors | None,
    *,
    zero_reference: bool,
    profile_enabled: bool,
) -> tuple[float, float | None]:
    if not profile_enabled or factors is None:
        magnitude = policy.zero_reference_magnitude(severity) if zero_reference else policy.magnitude(severity)
        return magnitude, None
    lower, upper = _severity_band(
        policy,
        severity,
        zero_reference=zero_reference,
    )
    position = _variation_profile_position(factors)
    return lower + ((upper - lower) * position), position


def calculate_bounded_assumption(
    *,
    parameter_name: str,
    reference_value: float,
    direction: VariationDirection,
    severity: VariationSeverity,
    mode: VariationMode,
    variation_factors: VariationFactors | None = None,
    profile_enabled: bool = True,
) -> VariationCalculation:
    policy = get_parameter_variation_policy(parameter_name)
    applied_severity, clipped = _bounded_severity(severity, mode)
    if direction == "unchanged":
        return VariationCalculation(
            proposed_value=reference_value,
            applied_severity=applied_severity,
            calculation_ko="방향을 중립으로 판단해 기준값을 유지",
            clipped=clipped,
            applied_magnitude=0.0,
            profile_position=(
                _variation_profile_position(variation_factors)
                if profile_enabled and variation_factors is not None
                else None
            ),
        )
    sign = 1.0 if direction == "increase" else -1.0
    if policy.method == "atomic_share":
        raise MIBaseError(
            ErrorCode.INVALID_REQUEST,
            detail="PowerMix bounded assumptions must be validated as one atomic vector",
        )
    if policy.method == "additive":
        magnitude, profile_position = _profiled_magnitude(
            policy,
            applied_severity,
            variation_factors,
            zero_reference=False,
            profile_enabled=profile_enabled,
        )
        delta = magnitude
        calculation = f"기준값 {reference_value:g}에 {applied_severity} 절대 변화 {sign * delta:g} 적용"
    elif policy.method == "integer_step":
        magnitude, profile_position = _profiled_magnitude(
            policy,
            applied_severity,
            variation_factors,
            zero_reference=False,
            profile_enabled=profile_enabled,
        )
        delta = max(1.0, float(math.floor(magnitude + 0.5)))
        magnitude = delta
        calculation = f"기준 단계 {reference_value:g}에 {applied_severity} 단계 변화 {sign * delta:g} 적용"
    else:
        if abs(reference_value) > 1e-12:
            magnitude, profile_position = _profiled_magnitude(
                policy,
                applied_severity,
                variation_factors,
                zero_reference=False,
                profile_enabled=profile_enabled,
            )
            delta = abs(reference_value) * magnitude
            calculation = f"기준값 {reference_value:g}에 {applied_severity} 상대 변화 {sign * magnitude * 100:g}% 적용"
        else:
            delta, profile_position = _profiled_magnitude(
                policy,
                applied_severity,
                variation_factors,
                zero_reference=True,
                profile_enabled=profile_enabled,
            )
            magnitude = delta
            calculation = f"기준값이 0이므로 {applied_severity} zero-reference 변화 {sign * delta:g} 적용"
    if profile_position is not None and variation_factors is not None:
        calculation = (
            f"{calculation}; 근거 profile 위치 {profile_position:.3f} "
            f"(지속={variation_factors.duration}, 범위={variation_factors.scope}, "
            f"상쇄={variation_factors.offset}, 신뢰도={variation_factors.confidence}, "
            f"trio위치={variation_factors.sibling_position})"
        )
    proposed = reference_value + (sign * delta)
    if policy.method == "integer_step":
        proposed = float(round(proposed))
    return VariationCalculation(
        proposed_value=round(proposed, 10),
        applied_severity=applied_severity,
        calculation_ko=calculation,
        clipped=clipped,
        applied_magnitude=magnitude,
        profile_position=profile_position,
    )


def validate_atomic_share_assumption(
    *,
    reference_value: float,
    proposed_value: float,
    severity: VariationSeverity,
    mode: VariationMode,
) -> tuple[VariationSeverity, bool]:
    policy = get_parameter_variation_policy("PowerMix")
    applied_severity, clipped = _bounded_severity(severity, mode)
    max_delta = policy.magnitude(applied_severity)
    if abs(proposed_value - reference_value) > max_delta + 1e-12:
        raise MIBaseError(
            ErrorCode.INVALID_REQUEST,
            detail=(
                "PowerMix bounded assumption exceeds the per-member share guardrail: "
                f"delta={abs(proposed_value - reference_value):g}, max={max_delta:g}"
            ),
        )
    return applied_severity, clipped
