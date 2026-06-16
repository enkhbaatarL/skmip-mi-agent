from __future__ import annotations

from typing import Any

from sqlalchemy import select

from apps.agents.scenario_group_agent.persistence.signpost.models import MiSignpostModel
from apps.common.configs.database.sync_database.base import BaseSyncSQLRepository


class SignpostRepository(BaseSyncSQLRepository):
    def fetch_models_by_scenario_ids(
        self, scenario_ids: list[int]
    ) -> list[MiSignpostModel]:
        if not scenario_ids:
            return []
        stmt = (
            select(MiSignpostModel)
            .where(
                MiSignpostModel.scenario_id.in_(scenario_ids),
                MiSignpostModel.del_yn == "N",
            )
            .order_by(
                MiSignpostModel.scenario_id,
                MiSignpostModel.display_order,
                MiSignpostModel.signpost_id,
            )
        )
        return list(self.session.execute(stmt).scalars().all())

    def exists_for_scenario(self, scenario_id: int) -> bool:
        stmt = (
            select(MiSignpostModel.signpost_id)
            .where(
                MiSignpostModel.scenario_id == scenario_id,
                MiSignpostModel.del_yn == "N",
            )
            .limit(1)
        )
        return self.session.execute(stmt).first() is not None

    def insert_signpost(self, signpost: MiSignpostModel) -> int:
        self.session.add(signpost)
        self.session.flush()
        return int(signpost.signpost_id)

    def update_from_payload(
        self, signpost: MiSignpostModel, payload: dict[str, Any]
    ) -> None:
        for field in (
            "label",
            "probability_direction_code",
            "probability_impact_score",
            "signpost_reason",
            "display_order",
            "mod_usr_logn_id",
        ):
            if field in payload:
                setattr(signpost, field, payload[field])
        self.session.flush()

    def model_to_dict(self, signpost: MiSignpostModel) -> dict[str, Any]:
        return {
            "signpost_id": int(signpost.signpost_id),
            "scenario_id": int(signpost.scenario_id),
            "label": signpost.label,
            "probability_direction_code": signpost.probability_direction_code,
            "probability_impact_score": signpost.probability_impact_score,
            "signpost_reason": signpost.signpost_reason,
            "display_order": signpost.display_order,
            "strength": signpost.strength,
            "use_yn": signpost.use_yn,
            "keyword_hints": signpost.keyword_hints or [],
        }
