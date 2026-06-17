from __future__ import annotations

from decimal import Decimal
from typing import Any

from apps.agents.scenario_group_agent.persistence.scenario.repository import (
    ScenarioRepository,
)

LIKELIHOOD_TO_SCORE = {
    "very_low": Decimal("10.00"),
    "low": Decimal("25.00"),
    "medium": Decimal("50.00"),
    "high": Decimal("75.00"),
    "very_high": Decimal("90.00"),
}


class ScenarioService:
    def load_dimension_template(
        self, event_type_l2_id: int
    ) -> list[dict[str, Any]]:
        return self._load_template_json_from_db(event_type_l2_id)

    def load_pipeline_template(self, event_type_l2_id: int) -> dict[str, Any]:
        template_json = self.load_dimension_template(event_type_l2_id)
        return self._map_template_json_to_pipeline_template(
            template_json,
            event_type_l2_id,
        )

    def load_scenario_template(self, event_type_l2_id: int) -> "ScenarioTemplate":
        from apps.agents.scenario_group_agent.schemas.common import ScenarioTemplate

        pipeline_template = self.load_pipeline_template(event_type_l2_id)
        return ScenarioTemplate.model_validate(pipeline_template)

    def _load_template_json_from_db(
        self, event_type_l2_id: int
    ) -> list[dict[str, Any]]:
        from apps.common.configs.database.sync_database.connection import (
            get_sync_session,
        )

        session = get_sync_session()
        try:
            template_json = ScenarioRepository(
                session=session
            )._load_template_json_from_db(event_type_l2_id)
        finally:
            session.close()

        if template_json is None:
            raise KeyError(
                f"scenario dimension template 없음: event_type_l2_id={event_type_l2_id}"
            )

        if not isinstance(template_json, list):
            raise ValueError(
                "tmm_mi_scenario_dimension_template_m.template_json must be JSON ARRAY "
                f"(event_type_l2_id={event_type_l2_id})"
            )
        return template_json

    def _map_template_json_to_pipeline_template(
        self,
        template_json: list[dict[str, Any]],
        event_type_l2_id: int,
    ) -> dict[str, Any]:
        if not template_json:
            raise ValueError(
                f"template_json is empty: event_type_l2_id={event_type_l2_id}"
            )

        ordered_items = sorted(
            template_json,
            key=self._template_display_order,
        )
        dimensions = [
            self._map_template_dimension(item, event_type_l2_id, index)
            for index, item in enumerate(ordered_items, start=1)
        ]
        if len(dimensions) < 3:
            raise ValueError(
                "template_json must include at least three dimensions: "
                f"event_type_l2_id={event_type_l2_id}"
            )
        dimension_ids = [dimension["dimension_id"] for dimension in dimensions]
        if len(set(dimension_ids)) != len(dimension_ids):
            raise ValueError(
                "template_json contains duplicate dim_key: "
                f"event_type_l2_id={event_type_l2_id}"
            )

        return {
            "label_ko": f"event_type_l2_id={event_type_l2_id}",
            "template_dimensions_total": len(dimensions),
            "dimensions": dimensions,
            "compatibility_rules": [],
        }

    def _map_template_dimension(
        self,
        raw_dimension: dict[str, Any],
        event_type_l2_id: int,
        index: int,
    ) -> dict[str, Any]:
        if not isinstance(raw_dimension, dict):
            raise ValueError(
                "template_json item must be object: "
                f"event_type_l2_id={event_type_l2_id}, index={index}"
            )

        dimension_id = str(raw_dimension.get("dim_key", "")).strip()
        if not dimension_id:
            raise ValueError(
                "dim_key is required: "
                f"event_type_l2_id={event_type_l2_id}, index={index}"
            )

        label = str(raw_dimension.get("label", "")).strip() or dimension_id
        raw_value_enums = raw_dimension.get("value_enums") or []
        if not isinstance(raw_value_enums, list):
            raise ValueError(
                "value_enums must be array: "
                f"event_type_l2_id={event_type_l2_id}, dim_key={dimension_id}"
            )

        value_enums = [
            str(value).strip() for value in raw_value_enums if str(value).strip()
        ]
        if len(value_enums) < 2:
            raise ValueError(
                "value_enums must include at least two non-empty values: "
                f"event_type_l2_id={event_type_l2_id}, dim_key={dimension_id}"
            )

        return {
            "dimension_id": dimension_id,
            "label_ko": label,
            "description": label,
            "required": bool(raw_dimension.get("required", False)),
            "enum": self._build_enum_list(value_enums, dimension_id),
        }

    def _template_display_order(self, item: dict[str, Any]) -> int:
        if not isinstance(item, dict):
            return 999999
        try:
            return int(item.get("display_order", 999999))
        except (TypeError, ValueError):
            return 999999

    def _build_enum_list(
        self,
        value_enums: list[str],
        dimension_id: str,
    ) -> list[dict[str, Any]]:
        total = len(value_enums)
        tail_threshold = total if total < 5 else total - 1
        return [
            {
                "id": f"{dimension_id}_v{index}",
                "label": enum_label,
                "tail": index >= tail_threshold,
            }
            for index, enum_label in enumerate(value_enums, start=1)
        ]

    def load_by_group_id(self, scenario_group_id: int) -> list[dict[str, Any]]:
        from apps.common.configs.database.sync_database.connection import (
            get_sync_session,
        )

        session = get_sync_session()
        try:
            repository = ScenarioRepository(session=session)
            return [
                repository.model_to_dict(model)
                for model in repository.fetch_models_by_group_id(scenario_group_id)
            ]
        finally:
            session.close()

    def save_generated_scenarios(
        self,
        scenario_group_id: int,
        scenario_result: dict[str, Any],
        user_id: int,
    ) -> list[int]:
        from apps.common.configs.database.sync_database.connection import (
            get_sync_session,
        )

        stage4 = scenario_result.get("stage4_scenario_synthesis", {}) or {}
        stage5 = scenario_result.get("stage5_validation", {}) or {}
        scenarios = stage4.get("scenarios", []) or []
        likelihood_prior = stage5.get("likelihood_prior", {}) or {}

        session = get_sync_session()
        try:
            repository = ScenarioRepository(session=session)
            saved_ids: list[int] = []
            for index, scenario in enumerate(scenarios, start=1):
                scenario_key = scenario.get("scenario_id", "")
                likelihood = likelihood_prior.get(scenario_key, "medium")
                price_direction = scenario.get("price_direction", {}) or {}
                payload = {
                    "scenario_group_id": scenario_group_id,
                    "title": (scenario.get("title") or "")[:255],
                    "narrative": scenario.get("description") or "",
                    "status": "created",
                    "dimension_values": self._dimension_values_to_array(
                        scenario.get("dimension_values") or {}
                    ),
                    "probability_score": LIKELIHOOD_TO_SCORE.get(likelihood),
                    "probability_delta": None,
                    "impact_jkm": price_direction.get("jkm"),
                    "impact_ttf": price_direction.get("ttf"),
                    "impact_hh": price_direction.get("hh"),
                    "display_order": index,
                    "baseline_yn": (
                        "Y"
                        if likelihood in {"high", "very_high"} and index == 1
                        else "N"
                    ),
                    "crt_usr_logn_id": user_id,
                    "mod_usr_logn_id": user_id,
                }
                saved_ids.append(repository.insert_scenario(payload))
            session.commit()
            return saved_ids
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update_status(self, scenario_group_id: int, status: str) -> int:
        from apps.common.configs.database.sync_database.connection import (
            get_sync_session,
        )

        session = get_sync_session()
        try:
            count = ScenarioRepository(session=session).update_status(
                scenario_group_id, status
            )
            session.commit()
            return count
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _dimension_values_to_array(
        self, dimension_values: dict[str, Any]
    ) -> list[dict[str, Any]]:
        return [
            {"dimension_id": str(dimension_id), "value": value}
            for dimension_id, value in dimension_values.items()
        ]

    def cells_to_dimension_values(
        self,
        event_type_l2_id: int,
        cells: dict[str, Any],
    ) -> list[dict[str, Any]]:
        template_json = self._load_template_json_from_db(event_type_l2_id)
        template_by_key = {
            str(item.get("dim_key")): item
            for item in template_json
            if isinstance(item, dict) and item.get("dim_key")
        }
        converted: dict[str, Any] = {}
        for key, value in cells.items():
            template = template_by_key.get(key)
            value_enums = template.get("value_enums", []) if template else []
            if value in value_enums:
                converted[key] = f"{key}_v{value_enums.index(value) + 1}"
            else:
                converted[key] = value
        return self._dimension_values_to_array(converted)
