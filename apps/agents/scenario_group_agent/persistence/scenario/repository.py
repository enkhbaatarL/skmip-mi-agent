from __future__ import annotations

from typing import Any

from sqlalchemy import select

from apps.agents.scenario_group_agent.persistence.scenario.models import (
    MiScenarioDimensionTemplateModel,
    MiScenarioModel,
)
from apps.common.configs.database.sync_database.base import BaseSyncSQLRepository


class ScenarioRepository(BaseSyncSQLRepository):
    def _load_template_json_from_db(self, event_type_l2_id: int) -> Any | None:
        stmt = select(MiScenarioDimensionTemplateModel.template_json).where(
            MiScenarioDimensionTemplateModel.event_type_l2_id == event_type_l2_id,
            MiScenarioDimensionTemplateModel.del_yn == "N",
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def fetch_models_by_group_id(self, scenario_group_id: int) -> list[MiScenarioModel]:
        stmt = (
            select(MiScenarioModel)
            .where(MiScenarioModel.scenario_group_id == scenario_group_id, MiScenarioModel.del_yn == "N")
            .order_by(MiScenarioModel.display_order, MiScenarioModel.scenario_id)
        )
        return list(self.session.execute(stmt).scalars().all())

    def insert_scenario(self, payload: dict[str, Any]) -> int:
        scenario = MiScenarioModel(**payload)
        self.session.add(scenario)
        self.session.flush()
        return int(scenario.scenario_id)

    def update_judgment_status(self, scenario_group_id: int, status_code: str) -> int:
        scenarios = self.fetch_models_by_group_id(scenario_group_id)
        for scenario in scenarios:
            scenario.judgment_status_code = status_code
        self.session.flush()
        return len(scenarios)

    def model_to_dict(self, scenario: MiScenarioModel) -> dict[str, Any]:
        dimension_values = scenario.dimension_values or []
        dim_dict = {
            item.get("dimension_id"): item.get("value")
            for item in dimension_values
            if isinstance(item, dict) and item.get("dimension_id")
        }
        price_direction = {
            "jkm": scenario.impact_jkm,
            "ttf": scenario.impact_ttf,
            "hh": scenario.impact_hh,
        }
        return {
            "scenario_id": int(scenario.scenario_id),
            "scenario_group_id": int(scenario.scenario_group_id),
            "title": scenario.title,
            "description": scenario.narrative or "",
            "narrative": scenario.narrative,
            "dimension_values": dim_dict,
            "dimension_values_array": dimension_values,
            "price_direction": price_direction,
            "likelihood": scenario.probability_level,
            "probability_score": scenario.probability_score,
            "probability_level": scenario.probability_level,
            "probability_delta": scenario.probability_delta,
            "impact_jkm": scenario.impact_jkm,
            "impact_ttf": scenario.impact_ttf,
            "impact_hh": scenario.impact_hh,
            "feasibility_score": scenario.feasibility_score,
            "judgment_status_code": scenario.judgment_status_code,
            "display_order": scenario.display_order,
            "baseline_yn": scenario.baseline_yn,
        }
