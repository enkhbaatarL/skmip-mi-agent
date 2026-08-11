from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from sqlalchemy import CheckConstraint, Index, UniqueConstraint
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from apps.common.configs.database.sync_database.base import ORMBase
from apps.persistence.scenario_group.models import BIN, TABLE_ARGS, AuditColumnsMixin


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


__all__ = ["MiModelImpactLeverModel"]
