from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any

from apps.agents.scenario_group_agent.persistence.signpost.repository import (
    SignpostRepository,
)

STRENGTH_TO_IMPACT_SCORE = {
    "STRONG": Decimal("1.00"),
    "MEDIUM": Decimal("0.50"),
    "WEAK": Decimal("0.25"),
}


class SignpostService:
    def load_by_scenario_ids(self, scenario_ids: list[int]) -> list[dict[str, Any]]:
        from apps.common.configs.database.sync_database.connection import (
            get_sync_session,
        )

        session = get_sync_session()
        try:
            repository = SignpostRepository(session=session)
            return [
                repository.model_to_dict(model)
                for model in repository.fetch_models_by_scenario_ids(scenario_ids)
            ]
        finally:
            session.close()

    def has_signposts(self, scenario_id: int) -> bool:
        from apps.common.configs.database.sync_database.connection import (
            get_sync_session,
        )

        session = get_sync_session()
        try:
            return SignpostRepository(session=session).exists_for_scenario(scenario_id)
        finally:
            session.close()

    def save_generated_signposts(
        self,
        signposts: list[dict[str, Any]],
        user_id: str | None = None,
    ) -> list[int]:
        from apps.common.configs.database.sync_database.connection import (
            get_sync_session,
        )

        session = get_sync_session()
        try:
            repository = SignpostRepository(session=session)
            saved_ids: list[int] = []
            display_order_by_scenario: dict[int, int] = defaultdict(int)
            for signpost in signposts:
                rationale = signpost.get("rationale_ko") or ""
                keyword_hints = signpost.get("keyword_hints") or []
                if keyword_hints:
                    rationale = f"{rationale}\n\nkeyword_hints: {', '.join(map(str, keyword_hints))}".strip()
                scenario_id = int(signpost["scenario_id"])
                display_order_by_scenario[scenario_id] += 1
                payload = {
                    "scenario_id": scenario_id,
                    "label": (signpost.get("label") or "")[:500],
                    "probability_direction_code": signpost.get("direction"),
                    "probability_impact_score": STRENGTH_TO_IMPACT_SCORE.get(
                        signpost.get("strength")
                    ),
                    "signpost_reason": rationale,
                    "display_order": display_order_by_scenario[scenario_id],
                }
                if user_id:
                    payload["crt_usr_logn_id"] = user_id
                    payload["mod_usr_logn_id"] = user_id
                saved_ids.append(repository.insert_signpost(payload))
            session.commit()
            return saved_ids
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
