from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from apps.agents.scenario_group_agent.persistence.scenario.service import ScenarioService


class ScenarioGenerationService:
    """Generate scenario groups using templates stored in the database."""

    def __init__(self) -> None:
        from apps.connectors.llm.llm_client import ModelPreference, invoke_llm_structured_output, invoke_llm_text

        self.llm_invoke_structured = invoke_llm_structured_output
        self.llm_invoke_text = invoke_llm_text
        self.ModelPreference = ModelPreference

    def generate_scenario_group(self, event_file_path: str) -> dict[str, Any]:
        with open(event_file_path, encoding="utf-8") as file:
            event = json.load(file)
        return self.generate_scenario_group_from_event(event)

    def generate_scenario_group_from_event(self, event: dict[str, Any]) -> dict[str, Any]:
        from apps.agents.scenario_agent.services.scenario_pipeline import (
            stage1_build_context_pack,
            stage2_select_dimensions,
            stage3_reduce_values,
            stage4_synthesize_scenarios,
            stage5_validate,
        )

        event_type_l2_id = int(event.get("event_type_l2_id") or 0)
        template_json = ScenarioService()._load_template_json_from_db(event_type_l2_id)
        template = self._map_template_json_to_pipeline_template(template_json, event_type_l2_id)

        pack = stage1_build_context_pack(event)
        stage2 = stage2_select_dimensions(pack, event, template, llm_client=self)
        stage3 = stage3_reduce_values(pack, stage2, template, llm_client=self)
        stage4 = stage4_synthesize_scenarios(pack, stage3, template, llm_client=self)
        stage5 = stage5_validate(pack, stage4, llm_client=self)

        return {
            "scenario_group_id": f"scg_{uuid.uuid4().hex[:10]}",
            "created_at": datetime.utcnow().isoformat(),
            "stage1_context_pack": pack.model_dump(),
            "stage2_dimension_selection": stage2.model_dump(),
            "stage3_value_selection": stage3.model_dump(),
            "stage4_scenario_synthesis": stage4.model_dump(),
            "stage5_validation": stage5.model_dump(),
            "cartesian_total": stage4.cartesian_total,
            "filtered_by_compatibility": stage4.filtered_by_compatibility,
            "scenario_count": len(stage4.scenarios),
            "mece_passed": stage5.mece_check.mutually_exclusive,
            "mi_event_id": event.get("mi_event_id"),
            "event_type_l1_l2": pack.C1_base_event.event_type_l1_l2,
            "template_id": str(event_type_l2_id),
        }

    def save_result(self, result: dict[str, Any], output_path: str) -> None:
        with open(output_path, "w", encoding="utf-8") as file:
            json.dump(result, file, ensure_ascii=False, indent=2)

    def _map_template_json_to_pipeline_template(
        self,
        template_json: list[dict[str, Any]],
        event_type_l2_id: int,
    ) -> dict[str, Any]:
        if not template_json:
            raise ValueError(f"template_json is empty: event_type_l2_id={event_type_l2_id}")

        ordered_items = sorted(
            template_json,
            key=lambda item: (
                int(item.get("display_order", 999999))
                if isinstance(item, dict) and str(item.get("display_order", "")).isdigit()
                else 999999
            ),
        )

        dimensions: list[dict[str, Any]] = []
        for index, raw_dimension in enumerate(ordered_items, start=1):
            if not isinstance(raw_dimension, dict):
                raise ValueError(
                    f"template_json item must be object: event_type_l2_id={event_type_l2_id}, index={index}"
                )

            dimension_id = str(raw_dimension.get("dim_key", "")).strip() or f"dimension_{index}"
            label = str(raw_dimension.get("label", "")).strip() or dimension_id
            raw_value_enums = raw_dimension.get("value_enums") or []
            if not isinstance(raw_value_enums, list) or not raw_value_enums:
                raise ValueError(
                    f"value_enums must be non-empty array: "
                    f"event_type_l2_id={event_type_l2_id}, dim_key={dimension_id}"
                )

            value_enums = [str(value).strip() for value in raw_value_enums if str(value).strip()]
            if not value_enums:
                raise ValueError(
                    f"value_enums must include at least one non-empty value: "
                    f"event_type_l2_id={event_type_l2_id}, dim_key={dimension_id}"
                )

            dimensions.append(
                {
                    "dimension_id": dimension_id,
                    "label_ko": label,
                    "description": label,
                    "enum": self._build_enum_list(value_enums, dimension_id),
                }
            )

        return {
            "label_ko": f"event_type_l2_id={event_type_l2_id}",
            "template_dimensions_total": len(dimensions),
            "dimensions": dimensions,
            "compatibility_rules": [],
        }

    def _build_enum_list(self, value_enums: list[str], dimension_id: str) -> list[dict[str, Any]]:
        total = len(value_enums)
        tail_threshold = max(1, total - 1 if total < 5 else total - 2)
        return [
            {
                "id": f"{dimension_id}_v{index}",
                "label": enum_label,
                "tail": index >= tail_threshold,
            }
            for index, enum_label in enumerate(value_enums, start=1)
        ]
