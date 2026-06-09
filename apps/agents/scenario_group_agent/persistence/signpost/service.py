from __future__ import annotations

from decimal import Decimal
from typing import Any

from apps.agents.scenario_group_agent.persistence.signpost.repository import SignpostRepository


STRENGTH_TO_IMPACT_SCORE = {
    "STRONG": Decimal("1.00"),
    "MEDIUM": Decimal("0.50"),
    "WEAK": Decimal("0.25"),
}


class SignpostService:
    def load_by_scenario_ids(self, scenario_ids: list[int]) -> list[dict[str, Any]]:
        from apps.common.configs.database.sync_database.connection import get_sync_session

        session = get_sync_session()
        try:
            repository = SignpostRepository(session=session)
            return [repository.model_to_dict(model) for model in repository.fetch_models_by_scenario_ids(scenario_ids)]
        finally:
            session.close()

    def has_signposts(self, scenario_id: int) -> bool:
        from apps.common.configs.database.sync_database.connection import get_sync_session

        session = get_sync_session()
        try:
            return SignpostRepository(session=session).exists_for_scenario(scenario_id)
        finally:
            session.close()

    def save_generated_signposts(self, signposts: list[dict[str, Any]]) -> list[int]:
        from apps.common.configs.database.sync_database.connection import get_sync_session

        session = get_sync_session()
        try:
            repository = SignpostRepository(session=session)
            saved_ids: list[int] = []
            for index, signpost in enumerate(signposts, start=1):
                rationale = signpost.get("rationale_ko") or ""
                keyword_hints = signpost.get("keyword_hints") or []
                if keyword_hints:
                    rationale = f"{rationale}\n\nkeyword_hints: {', '.join(map(str, keyword_hints))}".strip()
                payload = {
                    "scenario_id": signpost.get("scenario_id"),
                    "label": (signpost.get("label") or "")[:500],
                    "probability_direction_code": signpost.get("direction"),
                    "probability_impact_score": STRENGTH_TO_IMPACT_SCORE.get(signpost.get("strength")),
                    "signpost_reason": rationale,
                    "display_order": index,
                }
                saved_ids.append(repository.insert_signpost(payload))
            session.commit()
            return saved_ids
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
