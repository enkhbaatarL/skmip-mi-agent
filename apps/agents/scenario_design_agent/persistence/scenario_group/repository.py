from __future__ import annotations

from typing import Any

from sqlalchemy import select

from apps.agents.scenario_design_agent.persistence.scenario.models import MiScenarioModel
from apps.agents.scenario_design_agent.persistence.scenario_group.models import (
    MiScenarioGroupModel,
    MiScenarioSnapModel,
    MiSignpostSnapModel,
    MiSnapshotModel,
)
from apps.agents.scenario_design_agent.persistence.signpost.models import MiSignpostModel
from apps.common.configs.database.sync_database.base import BaseSyncSQLRepository


class ScenarioGroupRepository(BaseSyncSQLRepository):
    def fetch_by_id(self, scenario_group_id: int) -> MiScenarioGroupModel | None:
        stmt = select(MiScenarioGroupModel).where(
            MiScenarioGroupModel.scenario_group_id == scenario_group_id,
            MiScenarioGroupModel.del_yn == "N",
        )
        return self.session.execute(stmt).scalars().one_or_none()

    def fetch_by_mi_event_id(self, mi_event_id: int) -> MiScenarioGroupModel | None:
        stmt = select(MiScenarioGroupModel).where(
            MiScenarioGroupModel.mi_event_id == mi_event_id,
            MiScenarioGroupModel.del_yn == "N",
        )
        return self.session.execute(stmt).scalars().one_or_none()

    def insert_group(self, payload: dict[str, Any]) -> int:
        group = MiScenarioGroupModel(**payload)
        self.session.add(group)
        self.session.flush()
        return int(group.scenario_group_id)

    def update_scenario_count(self, scenario_group_id: int, scenario_count: int) -> None:
        group = self.fetch_by_id(scenario_group_id)
        if group is None:
            return
        group.scenario_count = scenario_count

    def create_confirmation_snapshot(
        self,
        scenario_group_id: int,
        scenarios: list[MiScenarioModel],
        signposts_by_scenario_id: dict[int, list[MiSignpostModel]],
        stage_no: int = 2,
        phase_code: str = "AFTER",
    ) -> int:
        snapshot = MiSnapshotModel(
            scenario_group_id=scenario_group_id,
            stage_no=stage_no,
            phase_code=phase_code,
        )
        self.session.add(snapshot)
        self.session.flush()

        scenario_snap_ids: dict[int, int] = {}
        for scenario in scenarios:
            scenario_snap = MiScenarioSnapModel(
                snapshot_id=snapshot.snapshot_id,
                src_scenario_id=scenario.scenario_id,
                dimension_values=scenario.dimension_values,
                probability_score=scenario.probability_score,
                judgment_status_code=scenario.judgment_status_code,
                baseline_yn=scenario.baseline_yn,
            )
            self.session.add(scenario_snap)
            self.session.flush()
            scenario_snap_ids[int(scenario.scenario_id)] = int(scenario_snap.scenario_snap_id)

        for scenario in scenarios:
            scenario_snap_id = scenario_snap_ids[int(scenario.scenario_id)]
            for signpost in signposts_by_scenario_id.get(int(scenario.scenario_id), []):
                self.session.add(
                    MiSignpostSnapModel(
                        snapshot_id=snapshot.snapshot_id,
                        scenario_snap_id=scenario_snap_id,
                        src_signpost_id=signpost.signpost_id,
                        label=signpost.label,
                        probability_direction_code=signpost.probability_direction_code,
                        probability_impact_score=signpost.probability_impact_score,
                    )
                )

        self.session.flush()
        return int(snapshot.snapshot_id)

    def model_to_dict(self, group: MiScenarioGroupModel) -> dict[str, Any]:
        return {
            "scenario_group_id": int(group.scenario_group_id),
            "mi_event_id": int(group.mi_event_id),
            "event_type_l2_id": int(group.event_type_l2_id),
            "title": group.title,
            "summary": group.summary,
            "description": group.description,
            "dimension_selected": group.dimension_selected,
            "scenario_count": int(group.scenario_count or 0),
        }
