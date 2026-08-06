from __future__ import annotations

from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy import CheckConstraint, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from apps.common.configs.database.sync_database.base import ORMBase
from apps.persistence.scenario_group.models import (
    BIN,
    TABLE_ARGS,
    AuditColumnsMixin,
)


class MiModelParamProposalModel(AuditColumnsMixin, ORMBase):
    __tablename__ = "tmm_mi_model_param_proposal_m"
    __table_args__ = (
        Index("idx_tmm_mi_model_param_proposal_m_01", "scenario_id", "model_param_proposal_id"),
        Index("idx_tmm_mi_model_param_proposal_m_02", "status", "model_param_proposal_id"),
        Index("idx_tmm_mi_model_param_proposal_m_03", "callback_status", "model_param_proposal_id"),
        Index("idx_tmm_mi_model_param_proposal_m_04", "scenario_group_id"),
        Index("idx_tmm_mi_model_param_proposal_m_05", "mi_event_id"),
        CheckConstraint(
            "status IN ('PROCESSING','PROPOSED','CONFIRMED','FAILED')",
            name="ck_tmm_mi_model_param_proposal_m_01",
        ),
        CheckConstraint(
            "callback_status IN ('PENDING','SUCCEEDED','FAILED','SKIPPED')",
            name="ck_tmm_mi_model_param_proposal_m_02",
        ),
        CheckConstraint(
            "proposal_parameters IS NULL OR JSON_TYPE(proposal_parameters) = 'ARRAY'",
            name="ck_tmm_mi_model_param_proposal_m_03",
        ),
        CheckConstraint(
            "confirmation_parameters IS NULL OR JSON_TYPE(confirmation_parameters) = 'ARRAY'",
            name="ck_tmm_mi_model_param_proposal_m_04",
        ),
        TABLE_ARGS,
    )

    model_param_proposal_id: Mapped[int] = mapped_column(
        mysql.INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
        comment="수급모델 파라미터 제안 ID",
    )
    scenario_id: Mapped[int] = mapped_column(
        mysql.INTEGER(unsigned=True),
        ForeignKey(
            "tmm_mi_scenario_m.scenario_id",
            name="fk_tmm_mi_model_param_proposal_m_01",
            ondelete="RESTRICT",
        ),
        nullable=False,
        comment="시나리오 ID",
    )
    scenario_group_id: Mapped[int] = mapped_column(
        mysql.INTEGER(unsigned=True),
        ForeignKey(
            "tmm_mi_scenario_group_m.scenario_group_id",
            name="fk_tmm_mi_model_param_proposal_m_02",
            ondelete="RESTRICT",
        ),
        nullable=False,
        comment="시나리오 그룹 ID",
    )
    mi_event_id: Mapped[int | None] = mapped_column(
        mysql.INTEGER(unsigned=True),
        ForeignKey(
            "tmm_mi_mievent_m.mi_event_id",
            name="fk_tmm_mi_model_param_proposal_m_03",
            ondelete="RESTRICT",
        ),
        nullable=True,
        comment="대표 MI 이벤트 ID (다중 이벤트 그룹은 NULL)",
    )
    request_usr_id: Mapped[int | None] = mapped_column(
        mysql.INTEGER(unsigned=True),
        nullable=True,
        comment="요청자 사용자 ID",
    )
    status: Mapped[str] = mapped_column(
        sa.String(50, collation=BIN),
        nullable=False,
        server_default=sa.text("'PROCESSING'"),
        comment="상태 (PROCESSING/PROPOSED/CONFIRMED/FAILED)",
    )
    proposal_parameters: Mapped[Any | None] = mapped_column(
        mysql.JSON(),
        nullable=True,
        comment="제안 파라미터 배열 JSON",
    )
    confirmation_parameters: Mapped[Any | None] = mapped_column(
        mysql.JSON(),
        nullable=True,
        comment="확정 파라미터 배열 JSON",
    )
    proposal_completed_dtm: Mapped[datetime | None] = mapped_column(
        mysql.DATETIME(fsp=6),
        nullable=True,
        comment="제안 완료일시",
    )
    confirmed_dtm: Mapped[datetime | None] = mapped_column(
        mysql.DATETIME(fsp=6),
        nullable=True,
        comment="확정일시",
    )
    error_code: Mapped[str | None] = mapped_column(
        sa.String(100, collation=BIN),
        nullable=True,
        comment="오류 코드",
    )
    error_message: Mapped[str | None] = mapped_column(
        sa.Text(collation=BIN),
        nullable=True,
        comment="오류 메시지",
    )
    callback_status: Mapped[str] = mapped_column(
        sa.String(50, collation=BIN),
        nullable=False,
        server_default=sa.text("'PENDING'"),
        comment="Callback 상태",
    )
    callback_sent_dtm: Mapped[datetime | None] = mapped_column(
        mysql.DATETIME(fsp=6),
        nullable=True,
        comment="Callback 성공일시",
    )


class MiModelParamModel(AuditColumnsMixin, ORMBase):
    __tablename__ = "tmm_mi_model_param_m"
    __table_args__ = (
        UniqueConstraint("parameter_name", name="uk_tmm_mi_model_param_m_01"),
        Index("idx_tmm_mi_model_param_m_01", "model_file", "model_sheet"),
        CheckConstraint("use_yn IN ('Y','N')", name="ck_tmm_mi_model_param_m_01"),
        CheckConstraint("del_yn IN ('Y','N')", name="ck_tmm_mi_model_param_m_02"),
        CheckConstraint(
            "basecase_read_mode IN ('fixed_columns','matrix_time_columns')",
            name="ck_tmm_mi_model_param_m_03",
        ),
        TABLE_ARGS,
    )

    model_param_id: Mapped[int] = mapped_column(
        mysql.INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
        comment="수급모델 파라미터 ID",
    )
    use_yn: Mapped[str] = mapped_column(
        sa.CHAR(1, collation=BIN),
        nullable=False,
        server_default=sa.text("'Y'"),
        comment="사용 여부",
    )
    parameter_name: Mapped[str] = mapped_column(
        sa.String(150, collation=BIN),
        nullable=False,
        comment="수급모델 파라미터명",
    )
    parameter_hint: Mapped[str] = mapped_column(
        sa.Text(collation=BIN),
        nullable=False,
        comment="수급모델 파라미터 설명",
    )
    model_file: Mapped[str] = mapped_column(
        sa.String(100, collation=BIN),
        nullable=False,
        comment="모델 파일 구분",
    )
    model_sheet: Mapped[str] = mapped_column(
        sa.String(150, collation=BIN),
        nullable=False,
        comment="모델 시트명",
    )
    model_table: Mapped[str] = mapped_column(
        sa.String(50, collation=BIN),
        nullable=False,
        comment="모델 시트 내 테이블명",
    )
    semantic_axes: Mapped[str | None] = mapped_column(
        sa.Text(collation=BIN),
        nullable=True,
        comment="의미 축 설명",
    )
    basecase_read_mode: Mapped[str] = mapped_column(
        sa.String(50, collation=BIN),
        nullable=False,
        comment="Basecase 읽기 방식",
    )
    basecase_header_row: Mapped[int] = mapped_column(
        mysql.SMALLINT(unsigned=True),
        nullable=False,
        comment="Basecase header row",
    )
    basecase_data_start_row: Mapped[int] = mapped_column(
        mysql.SMALLINT(unsigned=True),
        nullable=False,
        comment="Basecase data start row",
    )
    basecase_column_roles: Mapped[str] = mapped_column(
        sa.String(1000, collation=BIN),
        nullable=False,
        comment="Basecase column role mapping",
    )
    basecase_row_filter: Mapped[str | None] = mapped_column(
        sa.String(200, collation=BIN),
        nullable=True,
        comment="Basecase row filter",
    )
    basecase_year_row: Mapped[int | None] = mapped_column(
        mysql.SMALLINT(unsigned=True),
        nullable=True,
        comment="Basecase year row",
    )
    basecase_month_row: Mapped[int | None] = mapped_column(
        mysql.SMALLINT(unsigned=True),
        nullable=True,
        comment="Basecase month row",
    )
    basecase_period_row: Mapped[int | None] = mapped_column(
        mysql.SMALLINT(unsigned=True),
        nullable=True,
        comment="Basecase period row",
    )
    basecase_value_start_col: Mapped[str | None] = mapped_column(
        sa.String(10, collation=BIN),
        nullable=True,
        comment="Basecase value start column",
    )
    basecase_value_end_col: Mapped[str | None] = mapped_column(
        sa.String(10, collation=BIN),
        nullable=True,
        comment="Basecase value end column",
    )
    basecase_stop_rule: Mapped[str] = mapped_column(
        sa.String(100, collation=BIN),
        nullable=False,
        comment="Basecase scan stop rule",
    )


class MiModelImpactLeverModel(AuditColumnsMixin, ORMBase):
    __tablename__ = "tmm_mi_model_impact_lever_m"
    __table_args__ = (
        UniqueConstraint("lever_code", name="uk_tmm_mi_model_impact_lever_m_01"),
        Index("idx_tmm_mi_model_impact_lever_m_01", "domain", "lever_code"),
        CheckConstraint("use_yn IN ('Y','N')", name="ck_tmm_mi_model_impact_lever_m_02"),
        CheckConstraint("del_yn IN ('Y','N')", name="ck_tmm_mi_model_impact_lever_m_03"),
        CheckConstraint(
            "JSON_TYPE(parameter_bindings) = 'ARRAY'",
            name="ck_tmm_mi_model_impact_lever_m_04",
        ),
        TABLE_ARGS,
    )

    impact_lever_id: Mapped[int] = mapped_column(
        mysql.INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
        comment="모델 영향 레버 ID",
    )
    lever_code: Mapped[str] = mapped_column(
        sa.String(150, collation=BIN),
        nullable=False,
        comment="안정적인 모델 영향 레버 코드",
    )
    domain: Mapped[str] = mapped_column(
        sa.String(30, collation=BIN),
        nullable=False,
        comment="demand/supply/trade/price_only",
    )
    label: Mapped[str] = mapped_column(
        sa.String(200, collation=BIN),
        nullable=False,
        comment="영향 레버 표시명",
    )
    description: Mapped[str] = mapped_column(
        sa.Text(collation=BIN),
        nullable=False,
        comment="영향 레버 의미",
    )
    applicability_hint: Mapped[str | None] = mapped_column(
        sa.Text(collation=BIN),
        nullable=True,
        comment="Event에서 레버를 선택하는 기준",
    )
    parent_lever_code: Mapped[str | None] = mapped_column(
        sa.String(150, collation=BIN),
        nullable=True,
        comment="선택적인 상위 레버 코드",
    )
    parameter_bindings: Mapped[Any] = mapped_column(
        mysql.JSON(),
        nullable=False,
        comment="연결 파라미터와 지원 상태 배열",
    )
    catalog_version: Mapped[str] = mapped_column(
        sa.String(100, collation=BIN),
        nullable=False,
        server_default=sa.text("'v1'"),
        comment="영향 레버 카탈로그 버전",
    )
    use_yn: Mapped[str] = mapped_column(
        sa.CHAR(1, collation=BIN),
        nullable=False,
        server_default=sa.text("'Y'"),
        comment="사용 여부",
    )


class MiModelParamDimensionMapModel(AuditColumnsMixin, ORMBase):
    __tablename__ = "tmm_mi_model_param_dimension_map"
    __table_args__ = (
        UniqueConstraint(
            "event_type_l2_id",
            "dimension_key",
            "model_param_id",
            name="uk_tmm_mi_model_param_dimension_map_01",
        ),
        Index("idx_tmm_mi_model_param_dimension_map_01", "event_type_l2_id", "dimension_key"),
        Index("idx_tmm_mi_model_param_dimension_map_02", "model_param_id"),
        CheckConstraint("use_yn IN ('Y','N')", name="ck_tmm_mi_model_param_dimension_map_01"),
        CheckConstraint("del_yn IN ('Y','N')", name="ck_tmm_mi_model_param_dimension_map_02"),
        CheckConstraint(
            "mapping_method IN ('direct','indirect','routing','na')",
            name="ck_tmm_mi_model_param_dimension_map_03",
        ),
        TABLE_ARGS,
    )

    model_param_dimension_map_id: Mapped[int] = mapped_column(
        mysql.INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
        comment="수급모델 파라미터 dimension 매핑 ID",
    )
    use_yn: Mapped[str] = mapped_column(
        sa.CHAR(1, collation=BIN),
        nullable=False,
        server_default=sa.text("'Y'"),
        comment="사용 여부",
    )
    event_type_l2_id: Mapped[int] = mapped_column(
        mysql.INTEGER(unsigned=True),
        ForeignKey(
            "tmm_mi_event_type_l2_m.event_type_l2_id",
            name="fk_tmm_mi_model_param_dimension_map_01",
            ondelete="RESTRICT",
        ),
        nullable=False,
        comment="이벤트 유형 L2 ID",
    )
    dimension_key: Mapped[str] = mapped_column(
        sa.String(150, collation=BIN),
        nullable=False,
        comment="시나리오 dimension key",
    )
    dimension_label: Mapped[str] = mapped_column(
        sa.String(200, collation=BIN),
        nullable=False,
        comment="시나리오 dimension label",
    )
    mapping_method: Mapped[str] = mapped_column(
        sa.String(50, collation=BIN),
        nullable=False,
        comment="매핑 방식",
    )
    model_param_id: Mapped[int | None] = mapped_column(
        mysql.INTEGER(unsigned=True),
        ForeignKey(
            "tmm_mi_model_param_m.model_param_id",
            name="fk_tmm_mi_model_param_dimension_map_02",
            ondelete="RESTRICT",
        ),
        nullable=True,
        comment="수급모델 파라미터 ID",
    )
    mapping_comment: Mapped[str | None] = mapped_column(
        "comment",
        sa.Text(collation=BIN),
        nullable=True,
        comment="매핑 설명",
    )


__all__ = [
    "MiModelImpactLeverModel",
    "MiModelParamDimensionMapModel",
    "MiModelParamModel",
    "MiModelParamProposalModel",
]
