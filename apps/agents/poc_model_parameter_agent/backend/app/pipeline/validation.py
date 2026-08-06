from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from app.pipeline.timing import parse_month_range
from app.schemas.pipeline import RunMetadata, ScenarioDocument
from app.schemas.seed import SeedDocument


def message(level: str, code: str, text: str, path: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"level": level, "code": code, "message": text}
    if path:
        result["path"] = path
    return result


def validate_input(
    metadata: RunMetadata,
    scenario: dict[str, Any],
    seed: SeedDocument,
    payload_limit_bytes: int,
) -> dict[str, Any]:
    messages: list[dict[str, Any]] = []
    encoded_size = len(json.dumps(scenario, ensure_ascii=False).encode("utf-8"))
    if encoded_size > payload_limit_bytes:
        messages.append(message("error", "PAYLOAD_TOO_LARGE", "Scenario JSON이 허용 크기를 초과했습니다."))

    try:
        ScenarioDocument.model_validate(scenario)
    except ValidationError as exc:
        for error in exc.errors(include_context=False):
            path = ".".join(str(part) for part in error["loc"])
            messages.append(message("error", "SCHEMA_ERROR", error["msg"], path))
        return {
            "status": "error",
            "errorCount": len(messages),
            "warningCount": 0,
            "payloadBytes": encoded_size,
            "messages": messages,
        }

    required_fields = ["groupTitle", "eventImpactFacts", "dimensionDefinitions", "scenarios"]
    for field in required_fields:
        if field not in scenario:
            messages.append(message("error", "REQUIRED_FIELD", f"필수 Field가 없습니다: {field}", field))

    facts = scenario.get("eventImpactFacts", [])
    fact_event_id_values = [fact.get("eventId") for fact in facts if isinstance(fact, dict)]
    fact_event_ids = set(fact_event_id_values)
    duplicate_event_ids = sorted(
        {
            event_id
            for event_id in fact_event_id_values
            if fact_event_id_values.count(event_id) > 1 and event_id is not None
        }
    )
    for duplicate in duplicate_event_ids:
        messages.append(
            message(
                "error",
                "DUPLICATE_EVENT_ID",
                f"Event Impact Fact의 Event ID가 중복되었습니다: {duplicate}",
                "eventImpactFacts",
            )
        )
    metadata_event_ids = list(metadata.mi_event_ids)
    duplicate_metadata_event_ids = sorted(
        {event_id for event_id in metadata_event_ids if metadata_event_ids.count(event_id) > 1}
    )
    for duplicate in duplicate_metadata_event_ids:
        messages.append(
            message(
                "error",
                "DUPLICATE_METADATA_EVENT_ID",
                f"Metadata miEventIds가 중복되었습니다: {duplicate}",
                "metadata.miEventIds",
            )
        )
    if fact_event_ids != set(metadata_event_ids):
        messages.append(
            message(
                "error",
                "EVENT_ID_MISMATCH",
                "Metadata miEventIds와 Scenario Event ID가 일치하지 않습니다.",
                "eventImpactFacts",
            )
        )
    for index, fact in enumerate(facts):
        lever = fact.get("leverCode")
        if lever not in seed.levers:
            messages.append(
                message("error", "UNKNOWN_LEVER", f"Catalog에 없는 Lever입니다: {lever}", f"eventImpactFacts.{index}")
            )
        if not fact.get("timing"):
            messages.append(
                message("error", "REQUIRED_TIMING", "Event timing이 필요합니다.", f"eventImpactFacts.{index}.timing")
            )

    definitions = scenario.get("dimensionDefinitions", [])
    definition_ids = [definition.get("dimensionId") for definition in definitions]
    duplicates = sorted({item for item in definition_ids if definition_ids.count(item) > 1 and item is not None})
    for duplicate in duplicates:
        messages.append(message("error", "DUPLICATE_DIMENSION", f"Dimension ID가 중복되었습니다: {duplicate}"))

    definition_map = {definition.get("dimensionId"): definition for definition in definitions}
    known_bands = {item["key"] for item in seed.pressure_bands}
    for index, definition in enumerate(definitions):
        unknown_events = set(definition.get("sourceEventIds", [])) - fact_event_ids
        unknown_levers = set(definition.get("leverRefs", [])) - set(seed.levers)
        if unknown_events:
            messages.append(
                message(
                    "error",
                    "UNKNOWN_DIMENSION_EVENT",
                    f"Dimension sourceEventIds가 Event Fact에 없습니다: {sorted(unknown_events)}",
                    f"dimensionDefinitions.{index}",
                )
            )
        if unknown_levers:
            messages.append(
                message(
                    "error",
                    "UNKNOWN_DIMENSION_LEVER",
                    f"Dimension leverRefs가 Catalog에 없습니다: {sorted(unknown_levers)}",
                    f"dimensionDefinitions.{index}",
                )
            )
    for scenario_index, scenario_item in enumerate(scenario.get("scenarios", [])):
        values = scenario_item.get("dimensionValues", {})
        unknown_dimensions = set(values) - set(definition_map)
        if unknown_dimensions:
            messages.append(
                message(
                    "error",
                    "UNKNOWN_DIMENSION",
                    f"정의되지 않은 Dimension 값이 있습니다: {sorted(unknown_dimensions)}",
                    f"scenarios.{scenario_index}.dimensionValues",
                )
            )
        if scenario_item.get("targetMarketPressureBand") not in known_bands:
            messages.append(
                message(
                    "error",
                    "UNKNOWN_PRESSURE_BAND",
                    "Pressure Band가 Catalog에 없습니다.",
                    f"scenarios.{scenario_index}.targetMarketPressureBand",
                )
            )
        for dimension_id, definition in definition_map.items():
            if definition.get("required") and dimension_id not in values:
                messages.append(
                    message(
                        "error",
                        "REQUIRED_DIMENSION",
                        f"Required Dimension 값이 없습니다: {dimension_id}",
                        f"scenarios.{scenario_index}.dimensionValues",
                    )
                )
            if dimension_id in values:
                allowed = {value.get("valueId") for value in definition.get("values", [])}
                if values[dimension_id] not in allowed:
                    messages.append(
                        message(
                            "error",
                            "UNKNOWN_DIMENSION_VALUE",
                            f"Definition에 없는 값입니다: {dimension_id}={values[dimension_id]}",
                        )
                    )

    for index, interaction in enumerate(scenario.get("interactions", [])):
        unknown = set(interaction.get("eventIds", [])) - fact_event_ids
        if unknown:
            messages.append(
                message(
                    "error",
                    "UNKNOWN_INTERACTION_EVENT",
                    f"Interaction에 알 수 없는 Event가 있습니다: {sorted(unknown)}",
                    f"interactions.{index}",
                )
            )
        if interaction.get("relation") not in {"amplification", "offset"}:
            messages.append(
                message(
                    "error", "UNKNOWN_INTERACTION", "Interaction relation은 amplification 또는 offset이어야 합니다."
                )
            )

    if not scenario.get("excludedScenarios"):
        messages.append(message("warning", "NO_EXCLUDED_SCENARIO", "제외 Scenario가 선언되지 않았습니다."))

    errors = sum(item["level"] == "error" for item in messages)
    warnings = sum(item["level"] == "warning" for item in messages)
    return {
        "status": "error" if errors else ("warning" if warnings else "pass"),
        "errorCount": errors,
        "warningCount": warnings,
        "payloadBytes": encoded_size,
        "messages": messages,
    }


def build_clarifications(scenario: dict[str, Any]) -> list[dict[str, Any]]:
    questions: list[dict[str, Any]] = []
    facts = scenario.get("eventImpactFacts", [])
    if not isinstance(facts, list):
        facts = []
    for fact in facts:
        if not isinstance(fact, dict):
            continue
        if parse_month_range(str(fact.get("timing", ""))) is None:
            event_id = fact.get("eventId")
            questions.append(
                {
                    "questionId": f"timing_event_{event_id}",
                    "label": f"Event {event_id} 적용 월 범위를 선택하거나 직접 입력해 주세요.",
                    "required": True,
                    "kind": "choice_or_text",
                    "choices": [
                        {"choiceId": "2027-12:2028-02", "label": "2027년 12월부터 2028년 2월"},
                        {"choiceId": "2028-01:2028-02", "label": "2028년 1월부터 2월"},
                    ],
                    "allowText": True,
                    "sourceEventIds": [event_id],
                }
            )
    questions.extend(
        [
            {
                "questionId": "parameter_horizon",
                "label": "Parameter Horizon",
                "required": False,
                "kind": "choice",
                "choices": [
                    {"choiceId": "event_only", "label": "Event 기간만"},
                    {"choiceId": "event_recovery", "label": "Event + Recovery"},
                ],
                "allowText": False,
            },
            {
                "questionId": "additional_instruction",
                "label": "Optional Additional Instruction",
                "required": False,
                "kind": "text",
                "choices": [],
                "allowText": True,
            },
        ]
    )
    return questions
