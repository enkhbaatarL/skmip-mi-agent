from __future__ import annotations

from decimal import Decimal
from typing import Any

import sqlalchemy as sa
from sqlalchemy import CheckConstraint, ForeignKey, Index
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from apps.common.configs.database.sync_database.base import ORMBase
from apps.persistence.scenario_group.models import BIN, TABLE_ARGS, AuditColumnsMixin
from apps.persistence.schemas.enums import ScenarioStatus


_SCENARIO_STATUS_CHECK_SQL = ", ".join(f"'{status.value}'" for status in ScenarioStatus)


class MiScenarioDimensionTemplateModel(AuditColumnsMixin, ORMBase):
    __tablename__ = "tmm_mi_scenario_dimension_template_m"
    __table_args__ = (
        Index("idx_tmm_mi_scenario_dimension_template_m_01", "event_type_l2_id"),
        CheckConstraint("JSON_TYPE(template_json) = 'ARRAY'", name="ck_tmm_mi_scenario_dimension_template_m_01"),
        TABLE_ARGS,
    )

    scenario_dimension_template_id: Mapped[int] = mapped_column(
        mysql.INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
        comment="시나리오 Dimension Template ID",
    )
    event_type_l2_id: Mapped[int] = mapped_column(
        mysql.INTEGER(unsigned=True),
        ForeignKey("tmm_mi_event_type_l2_m.event_type_l2_id"),
        nullable=False,
        comment="이벤트 유형 L2 ID",
    )
    template_json: Mapped[Any] = mapped_column(
        mysql.JSON(),
        nullable=False,
        comment="Dimension 정의 배열 JSON",
    )


class MiScenarioModel(AuditColumnsMixin, ORMBase):
    __tablename__ = "tmm_mi_scenario_m"
    __table_args__ = (
        Index("idx_tmm_mi_scenario_m_01", "scenario_group_id"),
        CheckConstraint(
            f"status IN ({_SCENARIO_STATUS_CHECK_SQL})",
            name="ck_tmm_mi_scenario_m_02",
        ),
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
    status: Mapped[ScenarioStatus] = mapped_column(
        sa.String(50, collation=BIN),
        nullable=False,
        server_default=sa.text(f"'{ScenarioStatus.CREATING.value}'"),
        comment="상태 (creating:생성중 / created:생성완료 / realized:실현 / discarded:폐기)",
    )
    dimension_values: Mapped[Any] = mapped_column(sa.JSON, nullable=False)
    probability_score: Mapped[Decimal | None] = mapped_column(mysql.DECIMAL(5, 2), nullable=True)
    probability_delta: Mapped[Decimal | None] = mapped_column(mysql.DECIMAL(5, 2), nullable=True)
    impact_jkm: Mapped[str | None] = mapped_column(sa.String(50, collation=BIN), nullable=True)
    impact_ttf: Mapped[str | None] = mapped_column(sa.String(50, collation=BIN), nullable=True)
    impact_hh: Mapped[str | None] = mapped_column(sa.String(50, collation=BIN), nullable=True)
    display_order: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default=sa.text("0"))
    baseline_yn: Mapped[str] = mapped_column(sa.CHAR(1, collation=BIN), nullable=False, server_default=sa.text("'N'"))
