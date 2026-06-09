from __future__ import annotations

from typing import Any

from sqlalchemy.exc import IntegrityError

from apps.agents.scenario_group_agent.persistence.scenario.models import MiScenarioModel
from apps.agents.scenario_group_agent.persistence.scenario.repository import ScenarioRepository
from apps.agents.scenario_group_agent.persistence.scenario_group.repository import ScenarioGroupRepository
from apps.agents.scenario_group_agent.persistence.signpost.repository import SignpostRepository


class ScenarioGroupService:
    def load_by_id(self, scenario_group_id: int) -> dict[str, Any] | None:
        from apps.common.configs.database.sync_database.connection import get_sync_session

        session = get_sync_session()
        try:
            repository = ScenarioGroupRepository(session=session)
            group = repository.fetch_by_id(scenario_group_id)
            return repository.model_to_dict(group) if group else None
        finally:
            session.close()

    def load_by_mi_event_id(self, mi_event_id: int) -> dict[str, Any] | None:
        from apps.common.configs.database.sync_database.connection import get_sync_session

        session = get_sync_session()
        try:
            repository = ScenarioGroupRepository(session=session)
            group = repository.fetch_by_mi_event_id(mi_event_id)
            return repository.model_to_dict(group) if group else None
        finally:
            session.close()

    def create_group(self, payload: dict[str, Any]) -> int:
        from apps.common.configs.database.sync_database.connection import get_sync_session

        session = get_sync_session()
        try:
            repository = ScenarioGroupRepository(session=session)
            scenario_group_id = repository.insert_group(payload)
            session.commit()
            return scenario_group_id
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update_scenario_count(self, scenario_group_id: int, scenario_count: int) -> None:
        from apps.common.configs.database.sync_database.connection import get_sync_session

        session = get_sync_session()
        try:
            ScenarioGroupRepository(session=session).update_scenario_count(scenario_group_id, scenario_count)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def create_confirmation_snapshot(self, scenario_group_id: int) -> dict[str, Any]:
        from apps.common.configs.database.sync_database.connection import get_sync_session

        session = get_sync_session()
        try:
            group_repository = ScenarioGroupRepository(session=session)
            scenario_repository = ScenarioRepository(session=session)
            signpost_repository = SignpostRepository(session=session)

            group = group_repository.fetch_by_id(scenario_group_id)
            if group is None:
                return {"status": "failure", "message": "Scenario group not found"}

            scenarios = scenario_repository.fetch_models_by_group_id(scenario_group_id)
            if not scenarios:
                return {"status": "failure", "message": "No scenarios to confirm"}

            signposts = signpost_repository.fetch_models_by_scenario_ids([int(s.scenario_id) for s in scenarios])
            if not signposts:
                return {"status": "failure", "message": "No signposts to confirm"}

            signposts_by_scenario_id: dict[int, list] = {}
            for signpost in signposts:
                signposts_by_scenario_id.setdefault(int(signpost.scenario_id), []).append(signpost)

            snapshot_id = group_repository.create_confirmation_snapshot(
                scenario_group_id=scenario_group_id,
                scenarios=scenarios,
                signposts_by_scenario_id=signposts_by_scenario_id,
            )
            scenario_repository.update_judgment_status(scenario_group_id, "확정")
            group_repository.update_scenario_count(scenario_group_id, len(scenarios))
            session.commit()
            return {
                "status": "success",
                "snapshot_id": snapshot_id,
                "scenario_count": len(scenarios),
                "signpost_count": len(signposts),
            }
        except IntegrityError as exc:
            session.rollback()
            return {"status": "failure", "message": f"Snapshot already exists or violates DB constraints: {exc}"}
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
