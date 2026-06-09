from __future__ import annotations

from decimal import Decimal
from typing import Any

import sqlalchemy as sa
from sqlalchemy import CheckConstraint, ForeignKey, Index
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from apps.agents.scenario_design_agent.persistence.scenario_group.models import AuditColumnsMixin, BIN, TABLE_ARGS
from apps.common.configs.database.sync_database.base import ORMBase


class MiScenarioModel(AuditColumnsMixin, ORMBase):
    __tablename__ = "tmm_mi_scenario_m"
    __table_args__ = (
        Index("idx_tmm_mi_scenario_m_01", "scenario_group_id"),
        CheckConstraint("JSON_TYPE(dimension_values) = 'ARRAY'", name="ck_tmm_mi_scenario_m_01"),
        TABLE_ARGS,
    )

    scenario_id: Mapped[int] = mapped_column(
        mysql.INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
        comment="시나리오 ID",
    )
    scenario_group_id: Mapped[int] = mapped_column(
        mysql.INTEGER(unsigned=True),
        ForeignKey("tmm_mi_scenario_group_m.scenario_group_id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(sa.String(255, collation=BIN), nullable=False)
    narrative: Mapped[str | None] = mapped_column(sa.Text(collation=BIN), nullable=True)
    dimension_values: Mapped[Any] = mapped_column(sa.JSON, nullable=False)
    probability_score: Mapped[Decimal | None] = mapped_column(mysql.DECIMAL(5, 2), nullable=True)
    probability_level: Mapped[str | None] = mapped_column(sa.String(50, collation=BIN), nullable=True)
    probability_delta: Mapped[Decimal | None] = mapped_column(mysql.DECIMAL(5, 2), nullable=True)
    impact_jkm: Mapped[str | None] = mapped_column(sa.String(50, collation=BIN), nullable=True)
    impact_ttf: Mapped[str | None] = mapped_column(sa.String(50, collation=BIN), nullable=True)
    impact_hh: Mapped[str | None] = mapped_column(sa.String(50, collation=BIN), nullable=True)
    feasibility_score: Mapped[int | None] = mapped_column(sa.SmallInteger, nullable=True)
    judgment_status_code: Mapped[str | None] = mapped_column(
        sa.String(50, collation=BIN),
        nullable=True,
        server_default=sa.text("'대기'"),
    )
    display_order: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default=sa.text("0"))
    baseline_yn: Mapped[str] = mapped_column(sa.CHAR(1, collation=BIN), nullable=False, server_default=sa.text("'N'"))
