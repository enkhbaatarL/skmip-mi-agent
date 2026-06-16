from __future__ import annotations

from collections import defaultdict
from typing import Any

from apps.agents.scenario_group_agent.persistence.signpost.models import MiSignpostModel
from apps.agents.scenario_group_agent.persistence.signpost.repository import (
    SignpostRepository,
)
from apps.agents.scenario_group_agent.schemas.create_signposts import GeneratedSignpost


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
        signposts: list[GeneratedSignpost],
        user_id: int | None = None,
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
                scenario_id = int(signpost.scenario_id)
                display_order_by_scenario[scenario_id] += 1
                saved_ids.append(
                    repository.insert_signpost(
                        MiSignpostModel.convert_from_dto(
                            dto=signpost,
                            display_order=display_order_by_scenario[scenario_id],
                            user_id=user_id,
                        )
                    )
                )
            session.commit()
            return saved_ids
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
