from __future__ import annotations

from decimal import Decimal
from typing import Any

from apps.agents.scenario_design_agent.persistence.scenario.repository import ScenarioRepository


LIKELIHOOD_TO_SCORE = {
    "very_low": Decimal("10.00"),
    "low": Decimal("25.00"),
    "medium": Decimal("50.00"),
    "high": Decimal("75.00"),
    "very_high": Decimal("90.00"),
}


class ScenarioService:
    def load_by_group_id(self, scenario_group_id: int) -> list[dict[str, Any]]:
        from apps.common.configs.database.sync_database.connection import get_sync_session

        session = get_sync_session()
        try:
            repository = ScenarioRepository(session=session)
            return [repository.model_to_dict(model) for model in repository.fetch_models_by_group_id(scenario_group_id)]
        finally:
            session.close()

    def save_generated_scenarios(self, scenario_group_id: int, scenario_result: dict[str, Any]) -> list[int]:
        from apps.common.configs.database.sync_database.connection import get_sync_session

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
                    "dimension_values": self._dimension_values_to_array(scenario.get("dimension_values") or {}),
                    "probability_score": LIKELIHOOD_TO_SCORE.get(likelihood),
                    "probability_level": likelihood,
                    "probability_delta": None,
                    "impact_jkm": price_direction.get("jkm"),
                    "impact_ttf": price_direction.get("ttf"),
                    "impact_hh": price_direction.get("hh"),
                    "feasibility_score": 100 if scenario.get("compatibility_passed", True) else 0,
                    "judgment_status_code": "대기",
                    "display_order": index,
                    "baseline_yn": "Y" if likelihood in {"high", "very_high"} and index == 1 else "N",
                }
                saved_ids.append(repository.insert_scenario(payload))
            session.commit()
            return saved_ids
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update_judgment_status(self, scenario_group_id: int, status_code: str) -> int:
        from apps.common.configs.database.sync_database.connection import get_sync_session

        session = get_sync_session()
        try:
            count = ScenarioRepository(session=session).update_judgment_status(scenario_group_id, status_code)
            session.commit()
            return count
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _dimension_values_to_array(self, dimension_values: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            {"dimension_id": str(dimension_id), "value": value}
            for dimension_id, value in dimension_values.items()
        ]
