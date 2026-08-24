from __future__ import annotations

from typing import Any

from sqlalchemy import delete, or_, select

from apps.common.configs.database.sync_database.base import BaseSyncSQLRepository
from apps.persistence.scenario.models import MiScenarioModel
from apps.persistence.scenario_group.models import (
    MiScenarioGroupEventModel,
    MiScenarioGroupModel,
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
                MiScenarioGroupModel.scenario_group_id.in_(
                    select(MiScenarioGroupEventModel.scenario_group_id).where(
                        MiScenarioGroupEventModel.mi_event_id == mi_event_id,
                        MiScenarioGroupEventModel.del_yn == "N",
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

    def fetch_by_id(
        self,
        scenario_group_id: int,
        *,
        for_update: bool = False,
    ) -> MiScenarioGroupModel | None:
        stmt = select(MiScenarioGroupModel).where(
            MiScenarioGroupModel.scenario_group_id == scenario_group_id,
            MiScenarioGroupModel.del_yn == "N",
        )
        if for_update:
            stmt = stmt.with_for_update()
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

    def fetch_by_any_event_id(
        self,
        mi_event_id: int,
    ) -> MiScenarioGroupModel | None:
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

    def fetch_event_set_candidates(
        self,
        *,
        engine_version: str,
        event_set_hash: str,
        for_update: bool = False,
    ) -> list[MiScenarioGroupModel]:
        stmt = (
            select(MiScenarioGroupModel)
            .where(
                MiScenarioGroupModel.api_version == engine_version,
                MiScenarioGroupModel.event_set_hash == event_set_hash,
                MiScenarioGroupModel.del_yn == "N",
            )
            .order_by(MiScenarioGroupModel.scenario_group_id.desc())
        )
        if for_update:
            stmt = stmt.with_for_update()
        return list(self.session.execute(stmt).scalars().all())

    def fetch_event_ids_by_group_ids(
        self,
        scenario_group_ids: list[int],
    ) -> dict[int, list[int]]:
        if not scenario_group_ids:
            return {}
        stmt = (
            select(
                MiScenarioGroupEventModel.scenario_group_id,
                MiScenarioGroupEventModel.mi_event_id,
            )
            .where(
                MiScenarioGroupEventModel.scenario_group_id.in_(scenario_group_ids),
                MiScenarioGroupEventModel.del_yn == "N",
            )
            .order_by(
                MiScenarioGroupEventModel.scenario_group_id,
                MiScenarioGroupEventModel.mi_event_id,
            )
        )
        event_ids_by_group_id: dict[int, list[int]] = {}
        for scenario_group_id, mi_event_id in self.session.execute(stmt):
            event_ids_by_group_id.setdefault(int(scenario_group_id), []).append(int(mi_event_id))
        return event_ids_by_group_id

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

    def fetch_single_active_group_event(
        self,
        scenario_group_id: int,
    ) -> MiScenarioGroupEventModel | None:
        relations = self.fetch_group_events(scenario_group_id)
        return relations[0] if len(relations) == 1 else None

    def fetch_active_group_events_by_group_ids(
        self,
        scenario_group_ids: list[int],
    ) -> dict[int, list[MiScenarioGroupEventModel]]:
        if not scenario_group_ids:
            return {}
        stmt = (
            select(MiScenarioGroupEventModel)
            .where(
                MiScenarioGroupEventModel.scenario_group_id.in_(scenario_group_ids),
                MiScenarioGroupEventModel.del_yn == "N",
            )
            .order_by(
                MiScenarioGroupEventModel.scenario_group_id,
                MiScenarioGroupEventModel.display_order,
                MiScenarioGroupEventModel.scenario_group_event_id,
            )
        )
        relations_by_group_id: dict[int, list[MiScenarioGroupEventModel]] = {}
        for relation in self.session.execute(stmt).scalars():
            relations_by_group_id.setdefault(int(relation.scenario_group_id), []).append(relation)
        return relations_by_group_id

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
        counts = {
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

    def model_to_dict(self, group: MiScenarioGroupModel, *, include_del_yn: bool = False) -> dict[str, Any]:
        event_relation = self.fetch_single_active_group_event(int(group.scenario_group_id))
        payload = {
            "scenario_group_id": int(group.scenario_group_id),
            "mi_event_id": int(event_relation.mi_event_id) if event_relation is not None else None,
            "event_type_l2_id": int(event_relation.event_type_l2_id) if event_relation is not None else None,
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
            "template_checksum": group.template_checksum,
            "parameter_mapping_ready": bool(group.parameter_mapping_ready),
            "dimension_definitions": group.dimension_definitions or [],
            "generation_diagnostics": group.generation_diagnostics or {},
            "updated_at": group.mod_dtm,
        }
        if include_del_yn:
            payload["del_yn"] = group.del_yn
        return payload
