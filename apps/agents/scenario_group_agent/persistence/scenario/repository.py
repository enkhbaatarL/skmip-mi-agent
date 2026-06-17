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
        return self.session.execute(stmt).scalars().first()

    def fetch_models_by_group_id(self, scenario_group_id: int) -> list[MiScenarioModel]:
        stmt = (
            select(MiScenarioModel)
            .where(
                MiScenarioModel.scenario_group_id == scenario_group_id,
                MiScenarioModel.del_yn == "N",
            )
            .order_by(MiScenarioModel.display_order, MiScenarioModel.scenario_id)
        )
        return list(self.session.execute(stmt).scalars().all())

    def insert_scenario(self, payload: dict[str, Any]) -> int:
        scenario = MiScenarioModel(**payload)
        self.session.add(scenario)
        self.session.flush()
        return int(scenario.scenario_id)

    def update_status(self, scenario_group_id: int, status: str) -> int:
        scenarios = self.fetch_models_by_group_id(scenario_group_id)
        for scenario in scenarios:
            scenario.status = status
        self.session.flush()
        return len(scenarios)

    def update_from_payload(
        self, scenario: MiScenarioModel, payload: dict[str, Any]
    ) -> None:
        for field in (
            "title",
            "narrative",
            "dimension_values",
            "probability_score",
            "probability_delta",
            "impact_jkm",
            "impact_ttf",
            "impact_hh",
            "display_order",
            "baseline_yn",
            "mod_usr_logn_id",
        ):
            if field in payload:
                setattr(scenario, field, payload[field])
        self.session.flush()

    def model_to_dict(self, scenario: MiScenarioModel) -> dict[str, Any]:
        raw_dimension_values = scenario.dimension_values
        if isinstance(raw_dimension_values, dict):
            dim_dict = {
                str(dim_key): value
                for dim_key, value in raw_dimension_values.items()
                if str(dim_key).strip()
            }
        elif isinstance(raw_dimension_values, list):
            dim_dict = {
                str(item.get("dim_key")): item.get("value")
                for item in raw_dimension_values
                if isinstance(item, dict) and item.get("dim_key")
            }
        else:
            dim_dict = {}
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
            "status": scenario.status,
            "dimension_values": dim_dict,
            "price_direction": price_direction,
            "probability_score": scenario.probability_score,
            "probability_delta": scenario.probability_delta,
            "impact_jkm": scenario.impact_jkm,
            "impact_ttf": scenario.impact_ttf,
            "impact_hh": scenario.impact_hh,
            "display_order": scenario.display_order,
            "baseline_yn": scenario.baseline_yn,
        }
