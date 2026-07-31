from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

import sqlalchemy as sa
from sqlalchemy import CheckConstraint, ForeignKey, Index
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from apps.common.configs.database.sync_database.base import ORMBase
from apps.persistence.enums import (
    ScenarioGroupStage,
    ScenarioGroupStatus,
)


BIN = "utf8mb4_bin"
TABLE_ARGS = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": BIN}
_SCENARIO_GROUP_STATUS_CHECK_SQL = ", ".join(f"'{status.value}'" for status in ScenarioGroupStatus)
_SCENARIO_GROUP_STAGE_CHECK_SQL = ", ".join(f"'{stage.value}'" for stage in ScenarioGroupStage)
_SCENARIO_GROUP_STAGE_COMMENT = " / ".join(stage.value for stage in ScenarioGroupStage)


class AuditColumnsMixin:
    crt_usr_logn_id: Mapped[str] = mapped_column(
        sa.String(100, collation=BIN),
        nullable=False,
        server_default=sa.text("'system'"),
        comment="생성자",
    )
    crt_dtm: Mapped[datetime] = mapped_column(
        mysql.DATETIME(fsp=6),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP(6)"),
        comment="생성일시",
    )
    mod_usr_logn_id: Mapped[str] = mapped_column(
        sa.String(100, collation=BIN),
        nullable=False,
        server_default=sa.text("'system'"),
        comment="수정자",
    )
    mod_dtm: Mapped[datetime] = mapped_column(
        mysql.DATETIME(fsp=6),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP(6)"),
        server_onupdate=sa.text("CURRENT_TIMESTAMP(6)"),
        comment="수정일시",
    )
    del_yn: Mapped[str] = mapped_column(
        sa.CHAR(1, collation=BIN),
        nullable=False,
        server_default=sa.text("'N'"),
        comment="삭제여부",
    )


class MiScenarioGroupModel(AuditColumnsMixin, ORMBase):
    __tablename__ = "tmm_mi_scenario_group_m"
    __table_args__ = (
        Index("idx_tmm_mi_scenario_group_m_01", "event_type_l2_id"),
        Index("idx_tmm_mi_scenario_group_m_02", "mi_event_id"),
        CheckConstraint("JSON_TYPE(dimension_selected) = 'ARRAY'", name="ck_tmm_mi_scenario_group_m_01"),
        CheckConstraint(f"status IN ({_SCENARIO_GROUP_STATUS_CHECK_SQL})", name="ck_tmm_mi_scenario_group_m_02"),
        CheckConstraint(f"stage IN ({_SCENARIO_GROUP_STAGE_CHECK_SQL})", name="ck_tmm_mi_scenario_group_m_03"),
        CheckConstraint(
            "api_version IN ('v1','v2','v3','v4')",
            name="ck_tmm_mi_scenario_group_m_04",
        ),
        CheckConstraint(
            "generation_strategy IN "
            "('single_event_template_dimensions',"
            "'multi_event_source_dimensions',"
            "'multi_event_composite_dimensions',"
            "'multi_event_model_lever_dimensions')",
            name="ck_tmm_mi_scenario_group_m_05",
        ),
        TABLE_ARGS,
    )

    scenario_group_id: Mapped[int] = mapped_column(
        mysql.INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
        comment="시나리오 그룹 ID",
    )
    mi_event_id: Mapped[int | None] = mapped_column(
        mysql.INTEGER(unsigned=True),
        ForeignKey("tmm_mi_mievent_m.mi_event_id"),
        nullable=True,
        comment="단일 이벤트 방식의 대표 MI 이벤트 ID",
    )
    event_type_l2_id: Mapped[int | None] = mapped_column(
        mysql.INTEGER(unsigned=True),
        ForeignKey("tmm_mi_event_type_l2_m.event_type_l2_id"),
        nullable=True,
        comment="단일 이벤트 방식의 이벤트 유형 L2 ID",
    )
    request_usr_id: Mapped[int | None] = mapped_column(
        mysql.INTEGER(unsigned=True),
        nullable=True,
        comment="요청 사용자 ID",
    )
    title: Mapped[str] = mapped_column(sa.String(255, collation=BIN), nullable=False)
    summary: Mapped[str | None] = mapped_column(sa.Text(collation=BIN), nullable=True)
    description: Mapped[str | None] = mapped_column(sa.Text(collation=BIN), nullable=True)
    dimension_selected: Mapped[Any] = mapped_column(sa.JSON, nullable=False)
    scenario_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default=sa.text("0"))
    status: Mapped[ScenarioGroupStatus] = mapped_column(
        sa.String(50, collation=BIN),
        nullable=False,
        server_default=sa.text(f"'{ScenarioGroupStatus.CREATING.value}'"),
        comment="상태 (creating:생성중 / created:생성완료 / realized:실현 / discarded:폐기)",
    )
    stage: Mapped[ScenarioGroupStage] = mapped_column(
        sa.String(50, collation=BIN),
        nullable=False,
        server_default=sa.text(f"'{ScenarioGroupStage.READY.value}'"),
        comment=f"단계 ({_SCENARIO_GROUP_STAGE_COMMENT})",
    )
    api_version: Mapped[str] = mapped_column(
        sa.String(20, collation=BIN),
        nullable=False,
        server_default=sa.text("'v1'"),
    )
    generation_strategy: Mapped[str] = mapped_column(
        sa.String(100, collation=BIN),
        nullable=False,
        server_default=sa.text("'single_event_template_dimensions'"),
    )
    comparison_run_id: Mapped[str | None] = mapped_column(
        sa.String(255, collation=BIN),
        nullable=True,
    )
    impact_catalog_version: Mapped[str | None] = mapped_column(
        sa.String(255, collation=BIN),
        nullable=True,
        comment="v4 모델 영향 레버 카탈로그 버전",
    )
    impact_catalog_checksum: Mapped[str | None] = mapped_column(
        sa.String(64, collation=BIN),
        nullable=True,
        comment="v4 모델 영향 레버 카탈로그 checksum",
    )
    template_checksum: Mapped[str | None] = mapped_column(
        sa.String(64, collation=BIN),
        nullable=True,
    )
    parameter_mapping_ready: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        server_default=sa.false(),
    )
    dimension_definitions: Mapped[Any] = mapped_column(
        sa.JSON,
        nullable=False,
        server_default=sa.text("(JSON_ARRAY())"),
    )
    generation_diagnostics: Mapped[Any] = mapped_column(
        sa.JSON,
        nullable=False,
        server_default=sa.text("(JSON_OBJECT())"),
    )


class MiScenarioGroupEventModel(AuditColumnsMixin, ORMBase):
    __tablename__ = "tmm_mi_scenario_group_event_m"
    __table_args__ = (
        Index("idx_tmm_mi_scenario_group_event_m_01", "scenario_group_id"),
        Index("idx_tmm_mi_scenario_group_event_m_02", "mi_event_id"),
        sa.UniqueConstraint(
            "scenario_group_id",
            "mi_event_id",
            name="uk_tmm_mi_scenario_group_event_m_01",
        ),
        TABLE_ARGS,
    )

    scenario_group_event_id: Mapped[int] = mapped_column(
        mysql.INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )
    scenario_group_id: Mapped[int] = mapped_column(
        mysql.INTEGER(unsigned=True),
        ForeignKey("tmm_mi_scenario_group_m.scenario_group_id", ondelete="CASCADE"),
        nullable=False,
    )
    mi_event_id: Mapped[int] = mapped_column(
        mysql.INTEGER(unsigned=True),
        ForeignKey("tmm_mi_mievent_m.mi_event_id"),
        nullable=False,
    )
    event_type_l2_id: Mapped[int] = mapped_column(
        mysql.INTEGER(unsigned=True),
        ForeignKey("tmm_mi_event_type_l2_m.event_type_l2_id"),
        nullable=False,
    )
    scenario_dimension_template_id: Mapped[int | None] = mapped_column(
        mysql.INTEGER(unsigned=True),
        ForeignKey("tmm_mi_scenario_dimension_template_m.scenario_dimension_template_id"),
        nullable=True,
    )
    template_checksum: Mapped[str | None] = mapped_column(
        sa.String(64, collation=BIN),
        nullable=True,
    )
    display_order: Mapped[int] = mapped_column(sa.Integer, nullable=False)


class MiSnapshotModel(AuditColumnsMixin, ORMBase):
    __tablename__ = "tmm_mi_snapshot_m"
    __table_args__ = (
        Index("idx_tmm_mi_snapshot_m_01", "scenario_group_id"),
        TABLE_ARGS,
    )

    snapshot_id: Mapped[int] = mapped_column(
        mysql.INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
        comment="스냅샷 ID",
    )
    scenario_group_id: Mapped[int] = mapped_column(
        mysql.INTEGER(unsigned=True),
        ForeignKey("tmm_mi_scenario_group_m.scenario_group_id", ondelete="CASCADE"),
        nullable=False,
    )
    stage_no: Mapped[int] = mapped_column(sa.SmallInteger, nullable=False)
    phase_code: Mapped[str] = mapped_column(sa.String(50, collation=BIN), nullable=False)


class MiScenarioSnapModel(AuditColumnsMixin, ORMBase):
    __tablename__ = "tmm_mi_scenario_snap_m"
    __table_args__ = (
        Index("idx_tmm_mi_scenario_snap_m_01", "snapshot_id"),
        CheckConstraint("JSON_TYPE(dimension_values) = 'ARRAY'", name="ck_tmm_mi_scenario_snap_m_01"),
        CheckConstraint(
            "related_markets IS NULL OR JSON_TYPE(related_markets) = 'ARRAY'",
            name="ck_tmm_mi_scenario_snap_m_02",
        ),
        TABLE_ARGS,
    )

    scenario_snap_id: Mapped[int] = mapped_column(
        mysql.INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )
    snapshot_id: Mapped[int] = mapped_column(
        mysql.INTEGER(unsigned=True),
        ForeignKey("tmm_mi_snapshot_m.snapshot_id", ondelete="CASCADE"),
        nullable=False,
    )
    src_scenario_id: Mapped[int] = mapped_column(mysql.INTEGER(unsigned=True), nullable=False)
    dimension_values: Mapped[Any] = mapped_column(sa.JSON, nullable=False)
    probability_score: Mapped[Decimal | None] = mapped_column(mysql.DECIMAL(5, 2), nullable=True)
    baseline_yn: Mapped[str] = mapped_column(sa.CHAR(1, collation=BIN), nullable=False, server_default=sa.text("'N'"))
    global_pressure_band: Mapped[str | None] = mapped_column(
        sa.String(50, collation=BIN),
        nullable=True,
    )
    scenario_role: Mapped[str | None] = mapped_column(
        sa.String(50, collation=BIN),
        nullable=True,
    )
    global_pressure_rationale: Mapped[str | None] = mapped_column(
        sa.Text(collation=BIN),
        nullable=True,
    )
    related_markets: Mapped[Any | None] = mapped_column(sa.JSON, nullable=True)


class MiSignpostSnapModel(AuditColumnsMixin, ORMBase):
    __tablename__ = "tmm_mi_signpost_snap_m"
    __table_args__ = (
        Index("idx_tmm_mi_signpost_snap_m_01", "snapshot_id"),
        Index("idx_tmm_mi_signpost_snap_m_02", "scenario_snap_id"),
        CheckConstraint(
            "keyword_hints IS NULL OR JSON_TYPE(keyword_hints) = 'ARRAY'", name="ck_tmm_mi_signpost_snap_m_01"
        ),
        TABLE_ARGS,
    )

    signpost_snap_id: Mapped[int] = mapped_column(
        mysql.INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )
    snapshot_id: Mapped[int] = mapped_column(
        mysql.INTEGER(unsigned=True),
        ForeignKey("tmm_mi_snapshot_m.snapshot_id", ondelete="CASCADE"),
        nullable=False,
    )
    scenario_snap_id: Mapped[int] = mapped_column(
        mysql.INTEGER(unsigned=True),
        ForeignKey("tmm_mi_scenario_snap_m.scenario_snap_id", ondelete="CASCADE"),
        nullable=False,
    )
    src_signpost_id: Mapped[int] = mapped_column(mysql.INTEGER(unsigned=True), nullable=False)
    label: Mapped[str] = mapped_column(sa.String(500, collation=BIN), nullable=False)
    probability_direction_code: Mapped[str | None] = mapped_column(sa.String(50, collation=BIN), nullable=True)
    strength: Mapped[str | None] = mapped_column(
        sa.String(50, collation=BIN), nullable=True, comment="signpost 강도 (동결, STRONG/MEDIUM/WEAK)"
    )
    probability_impact_score: Mapped[Decimal | None] = mapped_column(mysql.DECIMAL(5, 2), nullable=True)
    keyword_hints: Mapped[Any | None] = mapped_column(sa.JSON, nullable=True, comment="매칭 키워드 힌트 배열 (동결)")
