from __future__ import annotations

from decimal import Decimal
from typing import Any

import sqlalchemy as sa
from sqlalchemy import CheckConstraint, ForeignKey, Index
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from apps.common.configs.database.sync_database.base import ORMBase
from apps.persistence.enums import ScenarioStatus
from apps.persistence.scenario_group.models import BIN, TABLE_ARGS, AuditColumnsMixin


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
    event_type_definition: Mapped[str | None] = mapped_column(
        sa.Text(collation=BIN),
        nullable=True,
        comment="Event Type 정의",
    )
    lng_price_impact_examples: Mapped[str | None] = mapped_column(
        sa.Text(collation=BIN),
        nullable=True,
        comment="LNG 가격 영향 대표 사례",
    )


class MiScenarioModel(AuditColumnsMixin, ORMBase):
    __tablename__ = "tmm_mi_scenario_m"
    __table_args__ = (
        Index("idx_tmm_mi_scenario_m_01", "scenario_group_id"),
        CheckConstraint(
            f"status IN ({_SCENARIO_STATUS_CHECK_SQL})",
            name="ck_tmm_mi_scenario_m_02",
        ),
        CheckConstraint(
            "global_pressure_band IS NULL OR global_pressure_band IN "
            "('strong_bullish','bullish','balanced','bearish','strong_bearish')",
            name="ck_tmm_mi_scenario_m_03",
        ),
        CheckConstraint(
            "scenario_role IS NULL OR scenario_role IN ('floor','ceiling','mixed')",
            name="ck_tmm_mi_scenario_m_04",
        ),
        CheckConstraint(
            "baseline_yn IN ('Y','N')",
            name="ck_tmm_mi_scenario_m_05",
        ),
        CheckConstraint(
            "related_markets IS NULL OR JSON_TYPE(related_markets) = 'ARRAY'",
            name="ck_tmm_mi_scenario_m_06",
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
    global_pressure_band: Mapped[str | None] = mapped_column(
        sa.String(50, collation=BIN),
        nullable=True,
        comment="글로벌 LNG 가격 압력 구간",
    )
    scenario_role: Mapped[str | None] = mapped_column(
        sa.String(50, collation=BIN),
        nullable=True,
        comment="시나리오 상대 역할 (floor/ceiling/mixed)",
    )
    global_pressure_rationale: Mapped[str | None] = mapped_column(
        sa.Text(collation=BIN),
        nullable=True,
        comment="글로벌 가격 압력 판단 근거",
    )
    related_markets: Mapped[Any | None] = mapped_column(
        sa.JSON,
        nullable=True,
        comment="시나리오별 관련 지역 가격 허브와 근거",
    )


class MiDimensionValueMappingModel(AuditColumnsMixin, ORMBase):
    __tablename__ = "tmm_mi_dimension_value_mapping_m"
    __table_args__ = (
        Index("idx_tmm_mi_dimension_value_mapping_m_01", "scenario_group_id"),
        Index("idx_tmm_mi_dimension_value_mapping_m_02", "dimension_value_id"),
        sa.UniqueConstraint(
            "scenario_group_id",
            "dimension_value_id",
            name="uk_tmm_mi_dimension_value_mapping_m_01",
        ),
        CheckConstraint(
            "status IN ('pending','approved','rejected')",
            name="ck_tmm_mi_dimension_value_mapping_m_01",
        ),
        TABLE_ARGS,
    )

    dimension_value_mapping_id: Mapped[int] = mapped_column(
        mysql.INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )
    scenario_group_id: Mapped[int] = mapped_column(
        mysql.INTEGER(unsigned=True),
        ForeignKey("tmm_mi_scenario_group_m.scenario_group_id", ondelete="CASCADE"),
        nullable=False,
    )
    dimension_value_id: Mapped[str] = mapped_column(
        sa.String(255, collation=BIN),
        nullable=False,
    )
    dimension_id: Mapped[str] = mapped_column(
        sa.String(255, collation=BIN),
        nullable=False,
    )
    display_value: Mapped[str] = mapped_column(sa.Text(collation=BIN), nullable=False)
    source_projections: Mapped[Any] = mapped_column(sa.JSON, nullable=False)
    mapping_proposal: Mapped[Any] = mapped_column(sa.JSON, nullable=False)
    mapping_version: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default=sa.text("1"))
    status: Mapped[str] = mapped_column(
        sa.String(50, collation=BIN),
        nullable=False,
        server_default=sa.text("'pending'"),
        comment="pending/approved/rejected",
    )
