from __future__ import annotations

from typing import Any

from sqlalchemy.exc import IntegrityError

from apps.agents.scenario_group_agent.persistence.scenario.repository import (
    ScenarioRepository,
)
from apps.agents.scenario_group_agent.persistence.scenario.service import (
    ScenarioService,
)
from apps.agents.scenario_group_agent.persistence.scenario_group.repository import (
    ScenarioGroupRepository,
)
from apps.agents.scenario_group_agent.persistence.signpost.repository import (
    SignpostRepository,
)


class ScenarioGroupService:
    def load_by_id(self, scenario_group_id: int) -> dict[str, Any] | None:
        from apps.common.configs.database.sync_database.connection import (
            get_sync_session,
        )

        session = get_sync_session()
        try:
            repository = ScenarioGroupRepository(session=session)
            group = repository.fetch_by_id(scenario_group_id)
            return repository.model_to_dict(group) if group else None
        finally:
            session.close()

    def load_by_mi_event_id(self, mi_event_id: int) -> dict[str, Any] | None:
        from apps.common.configs.database.sync_database.connection import (
            get_sync_session,
        )

        session = get_sync_session()
        try:
            repository = ScenarioGroupRepository(session=session)
            group = repository.fetch_by_mi_event_id(mi_event_id)
            return repository.model_to_dict(group) if group else None
        finally:
            session.close()

    def create_group(self, payload: dict[str, Any]) -> int:
        from apps.common.configs.database.sync_database.connection import (
            get_sync_session,
        )

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

    def update_scenario_count(
        self, scenario_group_id: int, scenario_count: int
    ) -> None:
        from apps.common.configs.database.sync_database.connection import (
            get_sync_session,
        )

        session = get_sync_session()
        try:
            ScenarioGroupRepository(session=session).update_scenario_count(
                scenario_group_id, scenario_count
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update_state(
        self,
        scenario_group_id: int,
        *,
        status: str | None = None,
        stage: str | None = None,
        user_id: int | None = None,
    ) -> dict[str, Any] | None:
        from apps.common.configs.database.sync_database.connection import (
            get_sync_session,
        )

        session = get_sync_session()
        try:
            repository = ScenarioGroupRepository(session=session)
            group = repository.fetch_by_id(scenario_group_id)
            if group is None:
                return None
            payload: dict[str, Any] = {}
            if status is not None:
                payload["status"] = status
            if stage is not None:
                payload["stage"] = stage
            if user_id is not None:
                payload["mod_usr_logn_id"] = user_id
            repository.update_group(group, payload)
            session.commit()
            return repository.model_to_dict(group)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def apply_confirmation(
        self,
        scenario_group_id: int,
        scenario_group_payload: dict[str, Any],
        table_payload: dict[str, Any],
    ) -> dict[str, Any]:
        from apps.common.configs.database.sync_database.connection import (
            get_sync_session,
        )

        session = get_sync_session()
        try:
            group_repository = ScenarioGroupRepository(session=session)
            scenario_repository = ScenarioRepository(session=session)
            signpost_repository = SignpostRepository(session=session)

            group = group_repository.fetch_by_id(scenario_group_id)
            if group is None:
                return {"status": "failure", "message": "Scenario group not found"}
            if int(scenario_group_payload["scenario_group_id"]) != scenario_group_id:
                return {
                    "status": "failure",
                    "message": "Path and body scenarioGroupId do not match",
                }
            if int(scenario_group_payload["mi_event_id"]) != int(
                group.mi_event_id
            ) or int(scenario_group_payload["event_type_l2_id"]) != int(
                group.event_type_l2_id
            ):
                return {
                    "status": "failure",
                    "message": "Body scenarioGroup identifiers do not match persisted group",
                }

            scenarios = scenario_repository.fetch_models_by_group_id(scenario_group_id)
            scenarios_by_id = {
                int(scenario.scenario_id): scenario for scenario in scenarios
            }
            signposts = signpost_repository.fetch_models_by_scenario_ids(
                list(scenarios_by_id)
            )
            signposts_by_id = {
                int(signpost.signpost_id): signpost for signpost in signposts
            }

            for row in table_payload.get("rows", []):
                scenario_id = int(row["scenario_id"])
                scenario = scenarios_by_id.get(scenario_id)
                if scenario is None:
                    return {
                        "status": "failure",
                        "message": f"Scenario does not belong to group: {scenario_id}",
                    }
                scenario_update: dict[str, Any] = {
                    "dimension_values": ScenarioService().cells_to_dimension_values(
                        int(group.event_type_l2_id),
                        row["cells"],
                    ),
                }
                for field in ("title", "narrative", "display_order", "baseline_yn"):
                    if field in row:
                        scenario_update[field] = row[field]
                if "metrics" in row and row["metrics"] is not None:
                    metrics = row["metrics"]
                    if "probability_score" in metrics:
                        scenario_update["probability_score"] = metrics[
                            "probability_score"
                        ]
                    if "probability_delta" in metrics:
                        scenario_update["probability_delta"] = metrics[
                            "probability_delta"
                        ]
                if "impact" in row and row["impact"] is not None:
                    impact = row["impact"]
                    for source, target in (
                        ("jkm", "impact_jkm"),
                        ("ttf", "impact_ttf"),
                        ("hh", "impact_hh"),
                    ):
                        if source in impact:
                            scenario_update[target] = impact[source]
                scenario_repository.update_from_payload(
                    scenario,
                    scenario_update,
                )
                for signpost_payload in row.get("signposts", []):
                    signpost_id = int(signpost_payload["signpost_id"])
                    signpost = signposts_by_id.get(signpost_id)
                    if signpost is None or int(signpost.scenario_id) != scenario_id:
                        return {
                            "status": "failure",
                            "message": f"Signpost does not belong to scenario: {signpost_id}",
                        }
                    signpost_repository.update_from_payload(signpost, signpost_payload)

            group_update: dict[str, Any] = {"scenario_count": len(scenarios)}
            for field in ("title", "summary", "description", "dimension_selected"):
                if field in scenario_group_payload:
                    group_update[field] = scenario_group_payload[field]
            group_repository.update_group(group, group_update)
            if not scenarios:
                return {"status": "failure", "message": "No scenarios to confirm"}
            if not signposts:
                return {"status": "failure", "message": "No signposts to confirm"}

            signposts_by_scenario_id: dict[int, list] = {}
            for signpost in signposts:
                signposts_by_scenario_id.setdefault(
                    int(signpost.scenario_id), []
                ).append(signpost)
            snapshot_id = group_repository.create_confirmation_snapshot(
                scenario_group_id=scenario_group_id,
                scenarios=scenarios,
                signposts_by_scenario_id=signposts_by_scenario_id,
            )
            group_repository.update_group(
                group, {"status": "created", "stage": "completed"}
            )
            session.commit()
            return {
                "status": "success",
                "snapshot_id": snapshot_id,
                "scenario_count": len(scenarios),
                "signpost_count": len(signposts),
                "group": group_repository.model_to_dict(group),
            }
        except IntegrityError as exc:
            session.rollback()
            return {
                "status": "failure",
                "message": f"Snapshot already exists or violates DB constraints: {exc}",
            }
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def create_confirmation_snapshot(self, scenario_group_id: int) -> dict[str, Any]:
        from apps.common.configs.database.sync_database.connection import (
            get_sync_session,
        )

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

            signposts = signpost_repository.fetch_models_by_scenario_ids(
                [int(s.scenario_id) for s in scenarios]
            )
            if not signposts:
                return {"status": "failure", "message": "No signposts to confirm"}

            signposts_by_scenario_id: dict[int, list] = {}
            for signpost in signposts:
                signposts_by_scenario_id.setdefault(
                    int(signpost.scenario_id), []
                ).append(signpost)

            snapshot_id = group_repository.create_confirmation_snapshot(
                scenario_group_id=scenario_group_id,
                scenarios=scenarios,
                signposts_by_scenario_id=signposts_by_scenario_id,
            )
            group_repository.update_scenario_count(scenario_group_id, len(scenarios))
            group_repository.update_group(
                group, {"status": "created", "stage": "completed"}
            )
            session.commit()
            return {
                "status": "success",
                "snapshot_id": snapshot_id,
                "scenario_count": len(scenarios),
                "signpost_count": len(signposts),
            }
        except IntegrityError as exc:
            session.rollback()
            return {
                "status": "failure",
                "message": f"Snapshot already exists or violates DB constraints: {exc}",
            }
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
