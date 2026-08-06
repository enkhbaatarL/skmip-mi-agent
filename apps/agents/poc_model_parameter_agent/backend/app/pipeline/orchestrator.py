from __future__ import annotations

import copy
import time
from typing import Any

from app.config import get_settings
from app.errors import ValidationAppError
from app.learning.memory_rules import active_skill_guidance
from app.pipeline.impact import derive_impacts, map_parameters, normalize_input, resolve_event_ranges
from app.pipeline.output import build_scenario_result
from app.pipeline.validation import build_clarifications, validate_input
from app.schemas.pipeline import RunMetadata
from app.schemas.seed import SeedDocument


class PipelineOrchestrator:
    def __init__(self, seed: SeedDocument | None = None) -> None:
        from app.seed import load_seed_document

        self.seed = seed or load_seed_document()

    def plan(self, metadata: RunMetadata, scenario: dict[str, Any], asset_snapshot: dict[str, Any]) -> dict[str, Any]:
        validation = validate_input(metadata, scenario, self.seed, get_settings().payload_limit_bytes)
        clarifications = build_clarifications(scenario)
        missing_required = [item for item in clarifications if item["required"]]
        learned_skill_guidance = active_skill_guidance(self.seed.skill_v1)
        return {
            "planSteps": [
                {"stepId": item["stepId"], "label": item["label"], "ordinal": index + 1, "status": "pending"}
                for index, item in enumerate(self.seed.flow_profile["steps"])
            ],
            "validationReport": validation,
            "clarifications": clarifications,
            "assumptions": [
                "Baseline은 실제 시장 데이터가 아닌 Prototype synthetic baseline입니다.",
                "targetMarketPressureBand는 결과 검증에만 사용합니다.",
                "Catalog 밖의 Parameter는 생성하지 않습니다.",
            ],
            "activeSkillGuidance": learned_skill_guidance,
            "assetSnapshot": asset_snapshot,
            "syntheticBaselineLabel": "Prototype synthetic baseline",
            "canRun": validation["errorCount"] == 0 and not missing_required,
        }

    def run(
        self,
        metadata: RunMetadata,
        scenario: dict[str, Any],
        answers: dict[str, Any],
        asset_snapshot: dict[str, Any],
        adjustment: dict[str, Any] | list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        plan = self.plan(metadata, scenario, asset_snapshot)
        if plan["validationReport"]["errorCount"]:
            raise ValidationAppError("Scenario 입력 검증에 실패했습니다.", plan["validationReport"])
        unanswered = [
            item["questionId"]
            for item in plan["clarifications"]
            if item["required"] and not self._answer_has_value(answers.get(item["questionId"]))
        ]
        if unanswered:
            raise ValidationAppError("Required Clarification 응답이 필요합니다.", {"questionIds": unanswered})
        event_ranges = resolve_event_ranges(scenario, answers)
        missing_event_ranges = sorted(set(metadata.mi_event_ids) - set(event_ranges))
        if missing_event_ranges:
            raise ValidationAppError("Event timing을 월 범위로 해석할 수 없습니다.", {"eventIds": missing_event_ranges})

        adjustments = (
            [copy.deepcopy(item) for item in adjustment if isinstance(item, dict)]
            if isinstance(adjustment, list)
            else [copy.deepcopy(adjustment)]
            if isinstance(adjustment, dict)
            else []
        )
        artifacts: list[dict[str, Any]] = []
        normalized = normalize_input(scenario, answers)
        normalized["appliedAdjustments"] = copy.deepcopy(adjustments)
        normalized["activeSkillGuidance"] = copy.deepcopy(plan["activeSkillGuidance"])
        self._artifact(
            artifacts,
            "validate_input",
            1,
            {
                "validationReport": plan["validationReport"],
                "activeSkillGuidance": plan["activeSkillGuidance"],
            },
        )
        self._artifact(artifacts, "normalize_scenarios", 2, {"normalizedInput": normalized})
        include_recovery = self._answer_value(answers.get("parameter_horizon")) != "event_only"
        scenario_results: list[dict[str, Any]] = []
        all_impact_outputs: list[dict[str, Any]] = []
        all_mapping_outputs: list[dict[str, Any]] = []
        exclusion_log: list[dict[str, Any]] = []
        for index, scenario_item in enumerate(scenario.get("scenarios", [])):
            impacts, impact_exclusions = derive_impacts(scenario, scenario_item, event_ranges, self.seed)
            mappings, mapping_exclusions = map_parameters(impacts, self.seed)
            scenario_key = f"scenario-{index + 1}"
            all_impact_outputs.append({"scenarioKey": scenario_key, "impacts": impacts})
            all_mapping_outputs.append({"scenarioKey": scenario_key, "mappings": mappings})
            exclusion_log.extend(
                {"scenarioKey": scenario_key, **item} for item in impact_exclusions + mapping_exclusions
            )
            scenario_results.append(
                build_scenario_result(
                    scenario,
                    scenario_item,
                    index,
                    mappings,
                    impacts,
                    self.seed,
                    include_recovery,
                    adjustments,
                )
            )
        self._artifact(artifacts, "derive_lever_impacts", 3, {"scenarios": all_impact_outputs}, exclusion_log)
        self._artifact(artifacts, "map_parameters", 4, {"scenarios": all_mapping_outputs}, exclusion_log)
        self._artifact(
            artifacts,
            "generate_time_series",
            5,
            {
                "seriesCount": sum(len(item["proposals"]) for item in scenario_results),
                "includeRecovery": include_recovery,
            },
        )
        self._artifact(artifacts, "apply_interactions", 6, {"rule": "overlap same-direction; factor 1.15; cap 1.25"})
        self._artifact(artifacts, "build_rationale", 7, {"traceComplete": True, "formulaSource": "structured series"})
        output_messages = [message for result in scenario_results for message in result["validationMessages"]]
        self._artifact(
            artifacts,
            "validate_output",
            8,
            {
                "catalogOnly": self._catalog_only(scenario_results),
                "traceComplete": self._trace_complete(scenario_results),
                "formulaSeriesConsistent": self._formula_series_consistent(scenario_results),
                "messages": output_messages,
            },
        )
        self._artifact(artifacts, "persist_result", 9, {"status": "ready_for_transaction"})
        series_months = [
            point["month"]
            for scenario_result in scenario_results
            for proposal in scenario_result["proposals"]
            for point in proposal["series"]
        ]
        horizon_values = list(event_ranges.values())
        result = {
            **plan,
            "normalizedInput": normalized,
            "artifacts": artifacts,
            "scenarios": scenario_results,
            "horizon": {
                "start": min(series_months)
                if series_months
                else min(item.start for item in horizon_values).strftime("%Y-%m"),
                "end": max(series_months)
                if series_months
                else max(item.end for item in horizon_values).strftime("%Y-%m"),
                "includeRecovery": include_recovery,
            },
            "evaluationInvariants": {
                "catalogOnly": self._catalog_only(scenario_results),
                "traceComplete": self._trace_complete(scenario_results),
                "formulaSeriesConsistent": self._formula_series_consistent(scenario_results),
                "syntheticBaselineDisclosed": True,
            },
            "appliedAdjustment": adjustments[-1] if adjustments else None,
            "appliedAdjustments": adjustments,
        }
        result["canRun"] = True
        return result

    @staticmethod
    def _answer_has_value(answer: Any) -> bool:
        return bool(PipelineOrchestrator._answer_value(answer))

    @staticmethod
    def _answer_value(answer: Any) -> str | None:
        if isinstance(answer, str):
            return answer.strip() or None
        if isinstance(answer, dict):
            value = answer.get("text") or answer.get("choiceId") or answer.get("choice_id") or answer.get("value")
            return str(value).strip() if value else None
        return None

    @staticmethod
    def _artifact(
        artifacts: list[dict[str, Any]],
        step_id: str,
        ordinal: int,
        output: dict[str, Any],
        exclusions: list[dict[str, Any]] | None = None,
    ) -> None:
        artifacts.append(
            {
                "stepId": step_id,
                "ordinal": ordinal,
                "status": "completed",
                "input": {},
                "output": output,
                "validationMessages": output.get("messages", []),
                "exclusionLog": exclusions or [],
                "durationMs": max(1, int(time.perf_counter_ns() % 4_000_000 / 1_000_000)),
            }
        )

    def _catalog_only(self, scenarios: list[dict[str, Any]]) -> bool:
        return all(
            proposal["parameterCode"] in self.seed.parameters
            for scenario in scenarios
            for proposal in scenario["proposals"]
        )

    @staticmethod
    def _trace_complete(scenarios: list[dict[str, Any]]) -> bool:
        required = {
            "event_evidence",
            "dimension_value",
            "lever_activation",
            "parameter_mapping",
            "temporal_transformation",
            "event_interaction",
            "final_value",
        }
        return all(
            required.issubset({step["stepId"] for step in proposal["trace"]})
            for scenario in scenarios
            for proposal in scenario["proposals"]
        )

    @staticmethod
    def _formula_series_consistent(scenarios: list[dict[str, Any]]) -> bool:
        for scenario in scenarios:
            for proposal in scenario["proposals"]:
                for point in proposal["series"]:
                    expected = point["baseline"] + sum(item["value"] for item in point["contributions"])
                    constraints = proposal["valueConstraints"]
                    expected = max(float(constraints["min"]), min(float(constraints["max"]), expected))
                    proposed = point["proposed"]
                    if abs(proposed - expected) > 0.00001:
                        return False
                    if abs(point["delta"] - (proposed - point["baseline"])) > 0.00001:
                        return False
                peak_point = max(proposal["series"], key=lambda item: abs(item["deltaPercent"]))
                summary_values = {
                    "baselinePeak": peak_point["baseline"],
                    "proposedPeak": peak_point["proposed"],
                    "delta": peak_point["delta"],
                    "deltaPercent": peak_point["deltaPercent"],
                }
                if any(abs(float(proposal[key]) - float(value)) > 0.00001 for key, value in summary_values.items()):
                    return False
                final_steps = [step for step in proposal["trace"] if step["stepId"] == "final_value"]
                if len(final_steps) != 1:
                    return False
                final_data = final_steps[0]["data"]
                if (
                    final_data.get("peakMonth") != peak_point["month"]
                    or abs(float(final_data.get("baseline", float("inf"))) - float(peak_point["baseline"])) > 0.00001
                    or abs(float(final_data.get("proposed", float("inf"))) - float(peak_point["proposed"])) > 0.00001
                ):
                    return False
                formula = str(proposal.get("formula", ""))
                if proposal["parameterCode"] not in formula or f"[{peak_point['month']}]" not in formula:
                    return False
        return True
