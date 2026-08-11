from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import and_, or_, select, update

from apps.common.configs.database.sync_database.base import BaseSyncSQLRepository
from apps.persistence.scenario_group_operation.models import (
    MiScenarioGroupOperationEventModel,
    MiScenarioGroupOperationModel,
)


class ScenarioGroupOperationRepository(BaseSyncSQLRepository):
    def insert_operation(self, payload: dict[str, Any]) -> MiScenarioGroupOperationModel:
        operation = MiScenarioGroupOperationModel(**payload)
        self.session.add(operation)
        self.session.flush()
        return operation

    def fetch_by_id(
        self,
        scenario_group_id: int,
        operation_id: str,
        *,
        for_update: bool = False,
    ) -> MiScenarioGroupOperationModel | None:
        stmt = select(MiScenarioGroupOperationModel).where(
            MiScenarioGroupOperationModel.scenario_group_id == scenario_group_id,
            MiScenarioGroupOperationModel.operation_id == operation_id,
            MiScenarioGroupOperationModel.del_yn == "N",
        )
        if for_update:
            stmt = stmt.with_for_update()
        return self.session.execute(stmt).scalars().one_or_none()

    def fetch_latest(self, scenario_group_id: int) -> MiScenarioGroupOperationModel | None:
        stmt = (
            select(MiScenarioGroupOperationModel)
            .where(
                MiScenarioGroupOperationModel.scenario_group_id == scenario_group_id,
                MiScenarioGroupOperationModel.del_yn == "N",
            )
            .order_by(
                MiScenarioGroupOperationModel.crt_dtm.desc(),
                MiScenarioGroupOperationModel.operation_id.desc(),
            )
            .limit(1)
        )
        return self.session.execute(stmt).scalars().first()

    def fetch_latest_by_group_ids(
        self,
        scenario_group_ids: list[int],
        *,
        for_update: bool = False,
    ) -> dict[int, MiScenarioGroupOperationModel]:
        if not scenario_group_ids:
            return {}
        stmt = (
            select(MiScenarioGroupOperationModel)
            .where(
                MiScenarioGroupOperationModel.scenario_group_id.in_(scenario_group_ids),
                MiScenarioGroupOperationModel.del_yn == "N",
            )
            .order_by(
                MiScenarioGroupOperationModel.scenario_group_id,
                MiScenarioGroupOperationModel.crt_dtm.desc(),
                MiScenarioGroupOperationModel.operation_id.desc(),
            )
        )
        if for_update:
            stmt = stmt.with_for_update()
        latest_by_group_id: dict[int, MiScenarioGroupOperationModel] = {}
        for operation in self.session.execute(stmt).scalars():
            latest_by_group_id.setdefault(int(operation.scenario_group_id), operation)
        return latest_by_group_id

    def fetch_active_by_group_ids(
        self,
        scenario_group_ids: list[int],
        *,
        for_update: bool = False,
    ) -> dict[int, MiScenarioGroupOperationModel]:
        if not scenario_group_ids:
            return {}
        stmt = (
            select(MiScenarioGroupOperationModel)
            .where(
                MiScenarioGroupOperationModel.scenario_group_id.in_(scenario_group_ids),
                MiScenarioGroupOperationModel.status.in_(("queued", "running")),
                MiScenarioGroupOperationModel.del_yn == "N",
            )
            .order_by(
                MiScenarioGroupOperationModel.scenario_group_id,
                MiScenarioGroupOperationModel.crt_dtm.desc(),
                MiScenarioGroupOperationModel.operation_id.desc(),
            )
        )
        if for_update:
            stmt = stmt.with_for_update()
        active_by_group_id: dict[int, MiScenarioGroupOperationModel] = {}
        for operation in self.session.execute(stmt).scalars():
            active_by_group_id.setdefault(int(operation.scenario_group_id), operation)
        return active_by_group_id

    def fetch_active(self, scenario_group_id: int) -> MiScenarioGroupOperationModel | None:
        stmt = (
            select(MiScenarioGroupOperationModel)
            .where(
                MiScenarioGroupOperationModel.scenario_group_id == scenario_group_id,
                MiScenarioGroupOperationModel.status.in_(("queued", "running")),
                MiScenarioGroupOperationModel.del_yn == "N",
            )
            .order_by(MiScenarioGroupOperationModel.crt_dtm.desc())
            .limit(1)
        )
        return self.session.execute(stmt).scalars().first()

    def fetch_stale_active(
        self,
        heartbeat_cutoff: datetime,
        *,
        limit: int = 100,
    ) -> list[MiScenarioGroupOperationModel]:
        stmt = (
            select(MiScenarioGroupOperationModel)
            .where(
                MiScenarioGroupOperationModel.status.in_(("queued", "running")),
                MiScenarioGroupOperationModel.del_yn == "N",
                or_(
                    MiScenarioGroupOperationModel.heartbeat_at <= heartbeat_cutoff,
                    and_(
                        MiScenarioGroupOperationModel.heartbeat_at.is_(None),
                        MiScenarioGroupOperationModel.crt_dtm <= heartbeat_cutoff,
                    ),
                ),
            )
            .order_by(
                MiScenarioGroupOperationModel.heartbeat_at,
                MiScenarioGroupOperationModel.crt_dtm,
                MiScenarioGroupOperationModel.operation_id,
            )
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return list(self.session.execute(stmt).scalars().all())

    def touch_active_heartbeat(
        self,
        scenario_group_id: int,
        operation_id: str,
        *,
        now: datetime,
    ) -> bool:
        stmt = (
            update(MiScenarioGroupOperationModel)
            .where(
                MiScenarioGroupOperationModel.scenario_group_id == scenario_group_id,
                MiScenarioGroupOperationModel.operation_id == operation_id,
                MiScenarioGroupOperationModel.status.in_(("queued", "running")),
                MiScenarioGroupOperationModel.del_yn == "N",
            )
            .values(heartbeat_at=now)
        )
        result = self.session.execute(stmt)
        return bool(result.rowcount)

    def list_events_after(
        self,
        operation_id: str,
        sequence: int,
        *,
        limit: int = 100,
    ) -> list[MiScenarioGroupOperationEventModel]:
        stmt = (
            select(MiScenarioGroupOperationEventModel)
            .where(
                MiScenarioGroupOperationEventModel.operation_id == operation_id,
                MiScenarioGroupOperationEventModel.sequence > sequence,
            )
            .order_by(MiScenarioGroupOperationEventModel.sequence)
            .limit(limit)
        )
        return list(self.session.execute(stmt).scalars().all())

    def fetch_last_event(self, operation_id: str) -> MiScenarioGroupOperationEventModel | None:
        stmt = (
            select(MiScenarioGroupOperationEventModel)
            .where(MiScenarioGroupOperationEventModel.operation_id == operation_id)
            .order_by(MiScenarioGroupOperationEventModel.sequence.desc())
            .limit(1)
        )
        return self.session.execute(stmt).scalars().first()

    def append_event(
        self,
        operation: MiScenarioGroupOperationModel,
        *,
        event_type: str,
        phase: str | None,
        title: str,
        message_markdown: str,
        payload: dict[str, Any],
        now: datetime,
        status: str | None = None,
        presentation_snapshot: dict[str, Any] | None = None,
        last_error: dict[str, Any] | None = None,
        retry_summary: dict[str, Any] | None = None,
        mlflow_trace_id: str | None = None,
    ) -> MiScenarioGroupOperationEventModel:
        sequence = int(operation.latest_sequence or 0) + 1
        snapshot_revision = int(operation.snapshot_revision or 0)
        event_payload = dict(payload)
        if presentation_snapshot is not None:
            snapshot_revision += 1
            operation.presentation_snapshot = presentation_snapshot
            operation.snapshot_revision = snapshot_revision
            if event_type == "section_ready":
                ready_sections = []
                for key, section in (presentation_snapshot.get("sections") or {}).items():
                    if not isinstance(section, dict):
                        continue
                    ready_sections.append({"key": key, "status": section.get("status", "ready")})
                event_payload["details"] = {
                    "sections": ready_sections,
                    "snapshotRevision": snapshot_revision,
                }
        operation.latest_sequence = sequence
        operation.heartbeat_at = now
        if phase is not None:
            operation.current_phase = phase
        if status is not None:
            operation.status = status
            if status == "running" and operation.started_at is None:
                operation.started_at = now
            if status in {"succeeded", "failed", "interrupted"}:
                operation.completed_at = now
        if last_error is not None:
            operation.last_error = last_error
        if retry_summary is not None:
            operation.retry_summary = retry_summary
        if mlflow_trace_id is not None:
            operation.mlflow_trace_id = mlflow_trace_id
        event = MiScenarioGroupOperationEventModel(
            operation_id=operation.operation_id,
            scenario_group_id=operation.scenario_group_id,
            sequence=sequence,
            event_type=event_type,
            phase=phase,
            title=title,
            message_markdown=message_markdown,
            payload=event_payload,
            snapshot_revision=snapshot_revision,
            mlflow_trace_id=mlflow_trace_id or operation.mlflow_trace_id,
            crt_dtm=now,
        )
        self.session.add(event)
        self.session.flush()
        return event
