from __future__ import annotations

from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy import CheckConstraint, ForeignKey, Index
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from apps.common.configs.database.sync_database.base import ORMBase
from apps.persistence.scenario_group.models import BIN, TABLE_ARGS, AuditColumnsMixin


_OPERATION_TYPES = "'create','validation','signpost','confirmation'"
_OPERATION_STATUSES = "'queued','running','succeeded','failed','interrupted'"


class MiScenarioGroupOperationModel(AuditColumnsMixin, ORMBase):
    __tablename__ = "tmm_mi_scenario_group_operation_m"
    __table_args__ = (
        Index("idx_tmm_mi_scenario_group_operation_m_01", "scenario_group_id", "crt_dtm"),
        Index("idx_tmm_mi_scenario_group_operation_m_02", "status", "heartbeat_at"),
        CheckConstraint(f"operation_type IN ({_OPERATION_TYPES})", name="ck_tmm_mi_scenario_group_operation_m_01"),
        CheckConstraint(f"status IN ({_OPERATION_STATUSES})", name="ck_tmm_mi_scenario_group_operation_m_02"),
        TABLE_ARGS,
    )

    operation_id: Mapped[str] = mapped_column(sa.String(26, collation=BIN), primary_key=True)
    scenario_group_id: Mapped[int] = mapped_column(
        mysql.INTEGER(unsigned=True),
        ForeignKey("tmm_mi_scenario_group_m.scenario_group_id", ondelete="CASCADE"),
        nullable=False,
    )
    operation_type: Mapped[str] = mapped_column(sa.String(30, collation=BIN), nullable=False)
    engine_version: Mapped[str] = mapped_column(sa.String(20, collation=BIN), nullable=False)
    source: Mapped[str] = mapped_column(
        sa.String(50, collation=BIN),
        nullable=False,
        server_default=sa.text("'api'"),
    )
    status: Mapped[str] = mapped_column(sa.String(20, collation=BIN), nullable=False)
    current_phase: Mapped[str | None] = mapped_column(sa.String(50, collation=BIN), nullable=True)
    retry_summary: Mapped[Any] = mapped_column(sa.JSON, nullable=False, server_default=sa.text("(JSON_OBJECT())"))
    presentation_snapshot: Mapped[Any] = mapped_column(
        sa.JSON,
        nullable=False,
        server_default=sa.text("(JSON_OBJECT())"),
    )
    snapshot_revision: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default=sa.text("0"))
    latest_sequence: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default=sa.text("0"))
    last_error: Mapped[Any | None] = mapped_column(sa.JSON, nullable=True)
    mlflow_trace_id: Mapped[str | None] = mapped_column(sa.String(255, collation=BIN), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(mysql.DATETIME(fsp=6), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(mysql.DATETIME(fsp=6), nullable=True)
    heartbeat_at: Mapped[datetime | None] = mapped_column(mysql.DATETIME(fsp=6), nullable=True)


class MiScenarioGroupOperationEventModel(ORMBase):
    __tablename__ = "tmm_mi_scenario_group_operation_event_h"
    __table_args__ = (
        Index("idx_tmm_mi_scenario_group_operation_event_h_01", "operation_id", "sequence"),
        sa.UniqueConstraint(
            "operation_id",
            "sequence",
            name="uk_tmm_mi_scenario_group_operation_event_h_01",
        ),
        TABLE_ARGS,
    )

    operation_event_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )
    operation_id: Mapped[str] = mapped_column(
        sa.String(26, collation=BIN),
        ForeignKey("tmm_mi_scenario_group_operation_m.operation_id", ondelete="CASCADE"),
        nullable=False,
    )
    scenario_group_id: Mapped[int] = mapped_column(
        mysql.INTEGER(unsigned=True),
        ForeignKey("tmm_mi_scenario_group_m.scenario_group_id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(sa.String(50, collation=BIN), nullable=False)
    phase: Mapped[str | None] = mapped_column(sa.String(50, collation=BIN), nullable=True)
    title: Mapped[str] = mapped_column(sa.String(255, collation=BIN), nullable=False)
    message_markdown: Mapped[str] = mapped_column(sa.Text(collation=BIN), nullable=False)
    payload: Mapped[Any] = mapped_column(sa.JSON, nullable=False, server_default=sa.text("(JSON_OBJECT())"))
    snapshot_revision: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default=sa.text("0"))
    mlflow_trace_id: Mapped[str | None] = mapped_column(sa.String(255, collation=BIN), nullable=True)
    crt_dtm: Mapped[datetime] = mapped_column(
        mysql.DATETIME(fsp=6),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP(6)"),
    )

