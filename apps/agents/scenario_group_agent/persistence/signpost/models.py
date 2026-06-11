from __future__ import annotations

from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy import ForeignKey, Index
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from apps.agents.scenario_group_agent.persistence.scenario_group.models import AuditColumnsMixin, BIN, TABLE_ARGS
from apps.common.configs.database.sync_database.base import ORMBase


class MiSignpostModel(AuditColumnsMixin, ORMBase):
    __tablename__ = "tmm_mi_signpost_m"
    __table_args__ = (
        Index("idx_tmm_mi_signpost_m_01", "scenario_id"),
        TABLE_ARGS,
    )

    signpost_id: Mapped[int] = mapped_column(
        mysql.INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
        comment="Signpost ID",
    )
    scenario_id: Mapped[int] = mapped_column(
        mysql.INTEGER(unsigned=True),
        ForeignKey("tmm_mi_scenario_m.scenario_id", ondelete="CASCADE"),
        nullable=False,
    )
    label: Mapped[str] = mapped_column(sa.String(500, collation=BIN), nullable=False)
    probability_direction_code: Mapped[str | None] = mapped_column(sa.String(50, collation=BIN), nullable=True)
    probability_impact_score: Mapped[Decimal | None] = mapped_column(mysql.DECIMAL(5, 2), nullable=True)
    signpost_reason: Mapped[str | None] = mapped_column(sa.Text(collation=BIN), nullable=True)
    display_order: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default=sa.text("0"))
