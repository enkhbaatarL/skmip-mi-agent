from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from app.pipeline.baseline import clamp, synthetic_baseline
from app.pipeline.interactions import interaction_factor
from app.pipeline.timing import add_months, months_between, ramp_factor, recovery_factor
from app.schemas.seed import SeedDocument

BAND_STEPS = {
    "strong_bearish": -2,
    "bearish": -1,
    "balanced": 0,
    "bullish": 1,
    "strong_bullish": 2,
}


def _feedback_factor(
    adjustments: list[dict[str, Any]],
    parameter: dict[str, Any],
    scenario_key: str,
) -> tuple[float, list[dict[str, Any]]]:
    factor = 1.0
    matched: list[dict[str, Any]] = []
    for adjustment in adjustments:
        target_parameter = adjustment.get("parameterCode")
        target_domain = adjustment.get("domain")
        target_scenario = adjustment.get("scenarioKey")
        if target_parameter and target_parameter != parameter["parameterCode"]:
            continue
        if target_domain and target_domain != parameter["domain"]:
            continue
        if target_scenario and target_scenario != scenario_key:
            continue
        factor *= float(adjustment.get("factor", 1.0))
        matched.append(adjustment)
    return factor, matched


def _month_weight(impact: dict[str, Any], month: date) -> tuple[float, str]:
    start = date.fromisoformat(f"{impact['start']}-01")
    end = date.fromisoformat(f"{impact['end']}-01")
    event_months = months_between(start, end)
    if month in event_months:
        return ramp_factor(event_months.index(month), len(event_months)), "event"
    recovery_months = int(impact.get("recoveryMonths", 0))
    for index in range(1, recovery_months + 1):
        if month == add_months(end, index):
            return recovery_factor(index, recovery_months), "recovery"
    return 0.0, "outside"


def _horizon(mapped_impacts: list[dict[str, Any]], include_recovery: bool) -> list[date]:
    starts = [date.fromisoformat(f"{item['start']}-01") for item in mapped_impacts]
    ends = [
        add_months(
            date.fromisoformat(f"{item['end']}-01"), int(item.get("recoveryMonths", 0)) if include_recovery else 0
        )
        for item in mapped_impacts
    ]
    return months_between(min(starts), max(ends)) if starts else []


def _pressure_band(score: float) -> str:
    if score <= -10:
        return "strong_bearish"
    if score < -2.5:
        return "bearish"
    if score <= 2.5:
        return "balanced"
    if score < 10:
        return "bullish"
    return "strong_bullish"


def _pressure_validation(declared: str, calculated: str) -> tuple[str, list[dict[str, Any]]]:
    declared_step = BAND_STEPS.get(declared, 0)
    calculated_step = BAND_STEPS.get(calculated, 0)
    difference = abs(declared_step - calculated_step)
    opposite = declared_step * calculated_step < 0
    if opposite:
        return "error", [
            {
                "level": "error",
                "code": "PRESSURE_DIRECTION_CONFLICT",
                "message": "선언 Pressure Band와 계산된 순압력의 방향이 충돌합니다.",
            }
        ]
    if difference >= 2:
        return "warning", [
            {
                "level": "warning",
                "code": "PRESSURE_BAND_DISTANCE",
                "message": "선언 Pressure Band와 계산 Band가 2단계 이상 차이납니다.",
            }
        ]
    return "pass", []


def build_proposals(
    mapped_impacts: list[dict[str, Any]],
    all_impacts: list[dict[str, Any]],
    seed: SeedDocument,
    scenario_key: str,
    include_recovery: bool,
    adjustments: list[dict[str, Any]],
    interactions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for impact in mapped_impacts:
        grouped[impact["parameterCode"]].append(impact)
    proposals: list[dict[str, Any]] = []
    for parameter_code, parameter_impacts in sorted(grouped.items()):
        parameter = seed.parameters[parameter_code]
        months = _horizon(parameter_impacts, include_recovery)
        feedback_factor, matched_adjustments = _feedback_factor(adjustments, parameter, scenario_key)
        series: list[dict[str, Any]] = []
        all_contributions: list[dict[str, Any]] = []
        for month in months:
            baseline = synthetic_baseline(parameter, month)
            contributions: list[dict[str, Any]] = []
            for impact in parameter_impacts:
                temporal_factor, phase = _month_weight(impact, month)
                if temporal_factor == 0:
                    continue
                interaction, interaction_reasons = interaction_factor(
                    impact,
                    all_impacts,
                    month.strftime("%Y-%m"),
                    interactions,
                )
                direction_sign = 1.0 if impact["changeDirection"] == "increase" else -1.0
                mapping_weight = float(impact["mapping"]["weight"])
                raw_value = (
                    baseline
                    * direction_sign
                    * float(impact["intensity"])
                    * mapping_weight
                    * temporal_factor
                    * interaction
                    * feedback_factor
                )
                contribution = {
                    "impactId": impact["impactId"],
                    "eventId": impact["eventId"],
                    "dimensionId": impact["dimensionId"],
                    "dimensionValue": impact["dimensionValue"],
                    "leverCode": impact["leverCode"],
                    "phase": phase,
                    "signedIntensity": direction_sign * float(impact["intensity"]),
                    "mappingWeight": mapping_weight,
                    "temporalFactor": temporal_factor,
                    "interactionFactor": interaction,
                    "interactionReasons": interaction_reasons,
                    "feedbackFactor": feedback_factor,
                    "value": round(raw_value, 6),
                }
                contributions.append(contribution)
                all_contributions.append({"month": month.strftime("%Y-%m"), **contribution})
            total = sum(item["value"] for item in contributions)
            constraints = parameter["valueConstraints"]
            proposed = clamp(baseline + total, float(constraints["min"]), float(constraints["max"]))
            series.append(
                {
                    "month": month.strftime("%Y-%m"),
                    "baseline": round(baseline, 6),
                    "proposed": round(proposed, 6),
                    "delta": round(proposed - baseline, 6),
                    "deltaPercent": round(((proposed - baseline) / baseline * 100) if baseline else 0, 6),
                    "phase": (
                        "event"
                        if any(item["phase"] == "event" for item in contributions)
                        else "recovery"
                        if any(item["phase"] == "recovery" for item in contributions)
                        else "baseline"
                    ),
                    "contributions": contributions,
                }
            )
        peak_point = max(series, key=lambda item: abs(item["deltaPercent"]))
        # The summary table, trace, formula, and selected point on the plot must
        # describe one calculation point.  "Peak" here means the month with the
        # largest absolute proposal delta, not independent maxima from different
        # months.
        baseline_peak = peak_point["baseline"]
        proposed_peak = peak_point["proposed"]
        confidence = sum(
            float(item["mapping"]["confidence"]) * float(item["confidence"]) for item in parameter_impacts
        ) / len(parameter_impacts)
        first_impact = parameter_impacts[0]
        trace = [
            {
                "stepId": "event_evidence",
                "label": "Event Evidence",
                "data": {
                    "eventIds": sorted({item["eventId"] for item in parameter_impacts}),
                    "evidenceText": [item["evidenceText"] for item in parameter_impacts],
                },
            },
            {
                "stepId": "dimension_value",
                "label": "Dimension Value",
                "data": [
                    {"dimensionId": item["dimensionId"], "valueId": item["dimensionValue"]}
                    for item in parameter_impacts
                ],
            },
            {
                "stepId": "lever_activation",
                "label": "Lever Activation",
                "data": {"leverCode": first_impact["leverCode"]},
            },
            {
                "stepId": "parameter_mapping",
                "label": "Parameter Mapping",
                "data": {"parameterCode": parameter_code, "mappingReason": first_impact["mapping"]["reason"]},
            },
            {
                "stepId": "temporal_transformation",
                "label": "Temporal Transformation",
                "data": {"start": months[0].strftime("%Y-%m"), "end": months[-1].strftime("%Y-%m")},
            },
            {
                "stepId": "event_interaction",
                "label": "Event Interaction",
                "data": {"maxFactor": max((item["interactionFactor"] for item in all_contributions), default=1.0)},
            },
        ]
        if feedback_factor != 1.0:
            trace.append(
                {
                    "stepId": "user_feedback_adjustment",
                    "label": "User Feedback Adjustment",
                    "data": {
                        "factor": feedback_factor,
                        "rules": [item.get("ruleCode") for item in matched_adjustments],
                        "adjustments": matched_adjustments,
                    },
                }
            )
        trace.append(
            {
                "stepId": "final_value",
                "label": "Final Value",
                "data": {
                    "peakMonth": peak_point["month"],
                    "baseline": peak_point["baseline"],
                    "proposed": peak_point["proposed"],
                },
            }
        )
        peak_terms = [
            (
                f"{peak_point['baseline']:.6f}×{item['signedIntensity']:.6f}×{item['mappingWeight']:.6f}"
                f"×{item['temporalFactor']:.6f}×{item['interactionFactor']:.6f}×{item['feedbackFactor']:.6f}"
            )
            for item in peak_point["contributions"]
        ]
        formula = (
            f"{parameter_code}[{peak_point['month']}] = clamp({peak_point['baseline']:.6f} + "
            f"({' + '.join(peak_terms) if peak_terms else '0'}), "
            f"{parameter['valueConstraints']['min']}, {parameter['valueConstraints']['max']}) "
            f"= {peak_point['proposed']:.6f}"
        )
        proposals.append(
            {
                "proposalId": None,
                "scenarioKey": scenario_key,
                "parameterCode": parameter_code,
                "parameterName": parameter["parameterName"],
                "domain": parameter["domain"],
                "unit": parameter["unit"],
                "baselineType": "synthetic",
                "baselineLabel": "Prototype synthetic baseline",
                "valueConstraints": parameter["valueConstraints"],
                "applicationPeriod": {"start": months[0].strftime("%Y-%m"), "end": months[-1].strftime("%Y-%m")},
                "baselinePeak": round(baseline_peak, 6),
                "proposedPeak": round(proposed_peak, 6),
                "delta": round(peak_point["delta"], 6),
                "deltaPercent": round(peak_point["deltaPercent"], 6),
                "confidence": round(confidence, 4),
                "warningCount": 0,
                "feedbackAdjustment": (
                    {"factor": feedback_factor, "adjustments": matched_adjustments} if feedback_factor != 1.0 else None
                ),
                "series": series,
                "trace": trace,
                "formula": formula,
                "evidence": [
                    {
                        **item,
                        "direction": next(
                            impact["changeDirection"]
                            for impact in parameter_impacts
                            if impact["impactId"] == item["impactId"]
                        ),
                        "strength": abs(item["signedIntensity"]),
                        "confidence": next(
                            impact["confidence"]
                            for impact in parameter_impacts
                            if impact["impactId"] == item["impactId"]
                        ),
                        "mappingReason": next(
                            impact["mapping"]["reason"]
                            for impact in parameter_impacts
                            if impact["impactId"] == item["impactId"]
                        ),
                        "evidenceText": next(
                            impact["evidenceText"]
                            for impact in parameter_impacts
                            if impact["impactId"] == item["impactId"]
                        ),
                    }
                    for item in all_contributions
                ],
                "rationale": f"{first_impact['leverCode']} 영향과 Catalog Mapping을 월별 synthetic baseline에 적용했습니다.",
            }
        )
    return proposals


def build_scenario_result(
    scenario: dict[str, Any],
    scenario_item: dict[str, Any],
    scenario_index: int,
    mapped_impacts: list[dict[str, Any]],
    all_impacts: list[dict[str, Any]],
    seed: SeedDocument,
    include_recovery: bool,
    adjustments: list[dict[str, Any]],
) -> dict[str, Any]:
    scenario_key = f"scenario-{scenario_index + 1}"
    proposals = build_proposals(
        mapped_impacts,
        all_impacts,
        seed,
        scenario_key,
        include_recovery,
        adjustments,
        scenario.get("interactions", []),
    )
    directional_peaks: list[float] = []
    for proposal in proposals:
        value = float(proposal["deltaPercent"])
        if proposal["domain"] == "supply":
            value = -value
        directional_peaks.append(value)
    pressure_score = sum(directional_peaks) / len(directional_peaks) if directional_peaks else 0.0
    calculated_band = _pressure_band(pressure_score)
    declared_band = scenario_item.get("targetMarketPressureBand", "balanced")
    status, validation_messages = _pressure_validation(declared_band, calculated_band)
    definitions = {item["dimensionId"]: item for item in scenario.get("dimensionDefinitions", [])}
    dimension_values: list[dict[str, Any]] = []
    for dimension_id, value_id in scenario_item.get("dimensionValues", {}).items():
        definition = definitions.get(dimension_id, {})
        value_def = next((item for item in definition.get("values", []) if item.get("valueId") == value_id), {})
        dimension_values.append(
            {
                "dimensionId": dimension_id,
                "valueId": value_id,
                "meaning": value_def.get("label", value_id),
                "leverCodes": definition.get("leverRefs", []),
                "eventIds": definition.get("sourceEventIds", []),
            }
        )
    return {
        "scenarioKey": scenario_key,
        "title": scenario_item.get("title", scenario_key),
        "narrative": scenario_item.get("narrative", ""),
        "probabilityScore": scenario_item.get("probabilityScore"),
        "mixedFactors": scenario_item.get("mixedFactors", []),
        "dimensionValues": dimension_values,
        "pressure": {
            "declaredBand": declared_band,
            "calculatedBand": calculated_band,
            "netPressureScore": round(pressure_score, 6),
            "status": status,
            "declaredRationale": scenario_item.get("targetMarketPressureRationale", ""),
        },
        "validationMessages": validation_messages,
        "proposals": proposals,
    }
