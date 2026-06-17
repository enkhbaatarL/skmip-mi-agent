from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from apps.agents.scenario_group_agent.persistence.scenario.repository import (
    ScenarioRepository,
)
from apps.agents.scenario_group_agent.subgraphs.scenario_generation.pipeline import (
    ScenarioTemplate,
    TemplateDimension,
)

if TYPE_CHECKING:
    from apps.agents.scenario_group_agent.schemas.common import (
        ScenarioTemplate as CommonScenarioTemplate,
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

    def load_pipeline_template(self, event_type_l2_id: int) -> ScenarioTemplate:
        template_json = self.load_dimension_template(event_type_l2_id)
        return self._map_template_json_to_pipeline_template(
            template_json,
            event_type_l2_id,
        )

    def load_scenario_template(
        self, event_type_l2_id: int
    ) -> "CommonScenarioTemplate":
        from apps.agents.scenario_group_agent.schemas.common import (
            ScenarioTemplate as CommonScenarioTemplate,
            ScenarioTemplateDimension,
            ScenarioTemplateEnum,
        )

        pipeline_template = self.load_pipeline_template(event_type_l2_id)
        dimensions = [
            ScenarioTemplateDimension(
                dimension_id=dimension.dim_key,
                label_ko=dimension.label,
                description=dimension.label,
                required=dimension.required,
                enum=[
                    ScenarioTemplateEnum(
                        id=str(item["id"]),
                        label=str(item["label"]),
                        tail=bool(item.get("tail", False)),
                    )
                    for item in dimension.enum_items()
                ],
            )
            for dimension in pipeline_template.dimensions
        ]
        return CommonScenarioTemplate(
            template_dimensions_total=len(dimensions),
            dimensions=dimensions,
        )

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
    ) -> ScenarioTemplate:
        if not template_json:
            raise ValueError(
                f"template_json is empty: event_type_l2_id={event_type_l2_id}"
            )

        dimensions = [
            self._map_template_dimension(item, event_type_l2_id, index)
            for index, item in enumerate(template_json, start=1)
        ]
        return ScenarioTemplate(
            label_ko=f"event_type_l2_id={event_type_l2_id}",
            template_dimensions_total=len(dimensions),
            dimensions=dimensions,
            compatibility_rules=[],
        )

    def _map_template_dimension(
        self,
        raw_dimension: dict[str, Any],
        event_type_l2_id: int,
        index: int,
    ) -> TemplateDimension:
        if not isinstance(raw_dimension, dict):
            raise ValueError(
                "template_json item must be object: "
                f"event_type_l2_id={event_type_l2_id}, index={index}"
            )

        dim_key = str(raw_dimension.get("dim_key", "")).strip()
        if not dim_key:
            raise ValueError(
                "dim_key is required: "
                f"event_type_l2_id={event_type_l2_id}, index={index}"
            )

        raw_value_enums = raw_dimension.get("value_enums") or []
        if not isinstance(raw_value_enums, list):
            raise ValueError(
                "value_enums must be array: "
                f"event_type_l2_id={event_type_l2_id}, dim_key={dim_key}"
            )

        return TemplateDimension(
            label=str(raw_dimension.get("label", "")).strip() or dim_key,
            dim_key=dim_key,
            required=bool(raw_dimension.get("required", False)),
            value_enums=raw_value_enums,
            display_order=self._template_display_order(raw_dimension),
        )

    def _template_display_order(self, item: dict[str, Any]) -> int:
        if not isinstance(item, dict):
            return 999999
        try:
            return int(item.get("display_order", 999999))
        except (TypeError, ValueError):
            return 999999

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
                    "dimension_values": self._normalize_dimension_values_object(
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

    def _normalize_dimension_values_object(
        self, dimension_values: dict[str, Any]
    ) -> dict[str, Any]:
        return {
            str(dim_key): value
            for dim_key, value in dimension_values.items()
            if str(dim_key).strip()
        }

    def cells_to_dimension_values(
        self,
        event_type_l2_id: int,
        cells: dict[str, Any],
    ) -> dict[str, Any]:
        template_json = self._load_template_json_from_db(event_type_l2_id)
        template_by_key = {
            str(item.get("dim_key")): item
            for item in template_json
            if isinstance(item, dict) and item.get("dim_key")
        }
        converted: dict[str, Any] = {}
        for key, value in cells.items():
            if key in template_by_key:
                converted[key] = value
        return self._normalize_dimension_values_object(converted)
