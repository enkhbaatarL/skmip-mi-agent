from __future__ import annotations

from typing import Any

from sqlalchemy import delete, or_, select

from apps.common.configs.database.sync_database.base import BaseSyncSQLRepository
from apps.persistence.scenario.models import MiScenarioModel
from apps.persistence.scenario_group.models import (
    MiScenarioGroupEventModel,
    MiScenarioGroupModel,
    MiScenarioSnapModel,
    MiSignpostSnapModel,
    MiSnapshotModel,
)
from apps.persistence.signpost.models import MiSignpostModel


class ScenarioGroupRepository(BaseSyncSQLRepository):
    def list_for_backoffice(
        self,
        *,
        include_deleted: bool = False,
        mi_event_id: int | None = None,
        keyword: str | None = None,
        status: str | None = None,
        stage: str | None = None,
        sort: str = "latest",
    ) -> list[MiScenarioGroupModel]:
        stmt = select(MiScenarioGroupModel)
        if not include_deleted:
            stmt = stmt.where(MiScenarioGroupModel.del_yn == "N")
        if mi_event_id is not None:
            stmt = stmt.where(
                or_(
                    MiScenarioGroupModel.mi_event_id == mi_event_id,
                    MiScenarioGroupModel.scenario_group_id.in_(
                        select(MiScenarioGroupEventModel.scenario_group_id).where(
                            MiScenarioGroupEventModel.mi_event_id == mi_event_id,
                            MiScenarioGroupEventModel.del_yn == "N",
                        ),
                    ),
                ),
            )
        if keyword:
            normalized = keyword.strip()
            like = f"%{normalized}%"
            filters = [MiScenarioGroupModel.title.like(like)]
            if normalized.isdecimal():
                numeric = int(normalized)
                filters.extend(
                    [
                        MiScenarioGroupModel.scenario_group_id == numeric,
                        MiScenarioGroupModel.mi_event_id == numeric,
                        MiScenarioGroupModel.scenario_group_id.in_(
                            select(
                                MiScenarioGroupEventModel.scenario_group_id,
                            ).where(
                                MiScenarioGroupEventModel.mi_event_id == numeric,
                                MiScenarioGroupEventModel.del_yn == "N",
                            ),
                        ),
                    ]
                )
            stmt = stmt.where(or_(*filters))
        if status:
            stmt = stmt.where(MiScenarioGroupModel.status == status)
        if stage:
            stmt = stmt.where(MiScenarioGroupModel.stage == stage)
        if sort == "oldest":
            stmt = stmt.order_by(MiScenarioGroupModel.mod_dtm.asc(), MiScenarioGroupModel.scenario_group_id.asc())
        else:
            stmt = stmt.order_by(MiScenarioGroupModel.mod_dtm.desc(), MiScenarioGroupModel.scenario_group_id.desc())
        return list(self.session.execute(stmt).scalars().all())

    def fetch_by_id(self, scenario_group_id: int) -> MiScenarioGroupModel | None:
        stmt = select(MiScenarioGroupModel).where(
            MiScenarioGroupModel.scenario_group_id == scenario_group_id,
            MiScenarioGroupModel.del_yn == "N",
        )
        return self.session.execute(stmt).scalars().one_or_none()

    def fetch_by_id_for_query(
        self, scenario_group_id: int, *, include_deleted: bool = False
    ) -> MiScenarioGroupModel | None:
        stmt = select(MiScenarioGroupModel).where(
            MiScenarioGroupModel.scenario_group_id == scenario_group_id,
        )
        if not include_deleted:
            stmt = stmt.where(MiScenarioGroupModel.del_yn == "N")
        return self.session.execute(stmt).scalars().one_or_none()

    def fetch_by_mi_event_id(self, mi_event_id: int) -> MiScenarioGroupModel | None:
        stmt = (
            select(MiScenarioGroupModel)
            .where(
                MiScenarioGroupModel.mi_event_id == mi_event_id,
                MiScenarioGroupModel.del_yn == "N",
            )
            .order_by(MiScenarioGroupModel.scenario_group_id.desc())
            .limit(1)
        )
        return self.session.execute(stmt).scalars().first()

    def fetch_by_any_event_id(
        self,
        mi_event_id: int,
    ) -> MiScenarioGroupModel | None:
        direct = self.fetch_by_mi_event_id(mi_event_id)
        if direct is not None:
            return direct
        stmt = (
            select(MiScenarioGroupModel)
            .join(
                MiScenarioGroupEventModel,
                MiScenarioGroupEventModel.scenario_group_id == MiScenarioGroupModel.scenario_group_id,
            )
            .where(
                MiScenarioGroupEventModel.mi_event_id == mi_event_id,
                MiScenarioGroupEventModel.del_yn == "N",
                MiScenarioGroupModel.del_yn == "N",
            )
            .order_by(MiScenarioGroupModel.scenario_group_id.desc())
            .limit(1)
        )
        return self.session.execute(stmt).scalars().first()

    def fetch_by_comparison_run(
        self,
        comparison_run_id: str,
        api_version: str,
    ) -> MiScenarioGroupModel | None:
        stmt = (
            select(MiScenarioGroupModel)
            .where(
                MiScenarioGroupModel.comparison_run_id == comparison_run_id,
                MiScenarioGroupModel.api_version == api_version,
                MiScenarioGroupModel.del_yn == "N",
            )
            .order_by(MiScenarioGroupModel.scenario_group_id.desc())
            .limit(1)
        )
        return self.session.execute(stmt).scalars().first()

    def fetch_all_by_comparison_run(
        self,
        comparison_run_id: str,
    ) -> list[MiScenarioGroupModel]:
        stmt = (
            select(MiScenarioGroupModel)
            .where(
                MiScenarioGroupModel.comparison_run_id == comparison_run_id,
                MiScenarioGroupModel.del_yn == "N",
            )
            .order_by(MiScenarioGroupModel.scenario_group_id)
        )
        return list(self.session.execute(stmt).scalars().all())

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

    def update_group(self, group: MiScenarioGroupModel, payload: dict[str, Any]) -> None:
        for field in (
            "title",
            "summary",
            "description",
            "dimension_selected",
            "scenario_count",
            "status",
            "stage",
            "mod_usr_logn_id",
            "api_version",
            "generation_strategy",
            "comparison_run_id",
            "target_market",
            "impact_catalog_version",
            "impact_catalog_checksum",
            "template_checksum",
            "parameter_mapping_ready",
            "dimension_definitions",
            "generation_diagnostics",
        ):
            if field in payload:
                setattr(group, field, payload[field])
        self.session.flush()

    def insert_group_event(self, payload: dict[str, Any]) -> int:
        relation = MiScenarioGroupEventModel(**payload)
        self.session.add(relation)
        self.session.flush()
        return int(relation.scenario_group_event_id)

    def fetch_group_events(
        self,
        scenario_group_id: int,
    ) -> list[MiScenarioGroupEventModel]:
        stmt = (
            select(MiScenarioGroupEventModel)
            .where(
                MiScenarioGroupEventModel.scenario_group_id == scenario_group_id,
                MiScenarioGroupEventModel.del_yn == "N",
            )
            .order_by(
                MiScenarioGroupEventModel.display_order,
                MiScenarioGroupEventModel.scenario_group_event_id,
            )
        )
        return list(self.session.execute(stmt).scalars().all())

    def soft_delete_group(self, group: MiScenarioGroupModel, user_id: int) -> int:
        if group.del_yn == "Y":
            return 0
        group.del_yn = "Y"
        group.mod_usr_logn_id = user_id
        self.session.flush()
        return 1

    def hard_delete_group(self, scenario_group_id: int) -> dict[str, int]:
        scenario_ids = list(
            self.session.execute(
                select(MiScenarioModel.scenario_id).where(
                    MiScenarioModel.scenario_group_id == scenario_group_id,
                )
            )
            .scalars()
            .all()
        )
        snapshot_ids = list(
            self.session.execute(
                select(MiSnapshotModel.snapshot_id).where(
                    MiSnapshotModel.scenario_group_id == scenario_group_id,
                )
            )
            .scalars()
            .all()
        )
        scenario_snap_ids = (
            list(
                self.session.execute(
                    select(MiScenarioSnapModel.scenario_snap_id).where(
                        MiScenarioSnapModel.snapshot_id.in_(snapshot_ids),
                    )
                )
                .scalars()
                .all()
            )
            if snapshot_ids
            else []
        )

        counts = {
            "tmm_mi_signpost_snap_m": self._delete_count(
                delete(MiSignpostSnapModel).where(MiSignpostSnapModel.snapshot_id.in_(snapshot_ids))
            )
            if snapshot_ids
            else 0,
            "tmm_mi_scenario_snap_m": self._delete_count(
                delete(MiScenarioSnapModel).where(MiScenarioSnapModel.scenario_snap_id.in_(scenario_snap_ids))
            )
            if scenario_snap_ids
            else 0,
            "tmm_mi_snapshot_m": self._delete_count(
                delete(MiSnapshotModel).where(MiSnapshotModel.snapshot_id.in_(snapshot_ids))
            )
            if snapshot_ids
            else 0,
            "tmm_mi_signpost_m": self._delete_count(
                delete(MiSignpostModel).where(MiSignpostModel.scenario_id.in_(scenario_ids))
            )
            if scenario_ids
            else 0,
            "tmm_mi_scenario_m": self._delete_count(
                delete(MiScenarioModel).where(MiScenarioModel.scenario_id.in_(scenario_ids))
            )
            if scenario_ids
            else 0,
            "tmm_mi_scenario_group_m": self._delete_count(
                delete(MiScenarioGroupModel).where(MiScenarioGroupModel.scenario_group_id == scenario_group_id)
            ),
        }
        self.session.flush()
        return counts

    def _delete_count(self, stmt: Any) -> int:
        result = self.session.execute(stmt)
        return int(result.rowcount or 0)

    def create_confirmation_snapshot(
        self,
        scenario_group_id: int,
        scenarios: list[MiScenarioModel],
        signposts_by_scenario_id: dict[int, list[MiSignpostModel]],
        stage_no: int = 2,
        phase_code: str = "AFTER",
    ) -> int:
        existing = (
            self.session.execute(
                select(MiSnapshotModel).where(
                    MiSnapshotModel.scenario_group_id == scenario_group_id,
                    MiSnapshotModel.stage_no == stage_no,
                    MiSnapshotModel.phase_code == phase_code,
                    MiSnapshotModel.del_yn == "N",
                )
            )
            .scalars()
            .first()
        )
        if existing is not None:
            return int(existing.snapshot_id)

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
                dimension_values=self._to_snapshot_dimension_values(scenario.dimension_values),
                probability_score=scenario.probability_score,
                baseline_yn=scenario.baseline_yn,
                global_pressure_band=scenario.global_pressure_band,
                scenario_role=scenario.scenario_role,
                global_pressure_rationale=scenario.global_pressure_rationale,
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

    @staticmethod
    def _to_snapshot_dimension_values(raw_dimension_values: Any) -> list[dict[str, Any]]:
        if isinstance(raw_dimension_values, list):
            return [item for item in raw_dimension_values if isinstance(item, dict) and item.get("dim_key")]
        if isinstance(raw_dimension_values, dict):
            return [
                {"dim_key": str(dim_key), "value": value}
                for dim_key, value in raw_dimension_values.items()
                if str(dim_key).strip()
            ]
        return []

    def model_to_dict(self, group: MiScenarioGroupModel, *, include_del_yn: bool = False) -> dict[str, Any]:
        payload = {
            "scenario_group_id": int(group.scenario_group_id),
            "mi_event_id": int(group.mi_event_id) if group.mi_event_id is not None else None,
            "event_type_l2_id": (int(group.event_type_l2_id) if group.event_type_l2_id is not None else None),
            "request_usr_id": (int(group.request_usr_id) if group.request_usr_id is not None else None),
            "title": group.title,
            "summary": group.summary,
            "description": group.description,
            "dimension_selected": group.dimension_selected,
            "scenario_count": int(group.scenario_count or 0),
            "status": group.status,
            "stage": group.stage,
            "api_version": group.api_version or "v1",
            "generation_strategy": (group.generation_strategy or "single_event_template_dimensions"),
            "comparison_run_id": group.comparison_run_id,
            "template_checksum": group.template_checksum,
            "parameter_mapping_ready": bool(group.parameter_mapping_ready),
            "dimension_definitions": group.dimension_definitions or [],
            "generation_diagnostics": group.generation_diagnostics or {},
        }
        if include_del_yn:
            payload["del_yn"] = group.del_yn
        return payload
