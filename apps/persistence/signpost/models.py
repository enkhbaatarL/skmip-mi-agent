from __future__ import annotations

from decimal import Decimal
from typing import Any

import sqlalchemy as sa
from sqlalchemy import CheckConstraint, ForeignKey, Index
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from apps.common.configs.database.sync_database.base import ORMBase
from apps.persistence.scenario_group.models import BIN, TABLE_ARGS, AuditColumnsMixin


class MiSignpostModel(AuditColumnsMixin, ORMBase):
    __tablename__ = "tmm_mi_signpost_m"
    __table_args__ = (
        Index("idx_tmm_mi_signpost_m_01", "scenario_id"),
        CheckConstraint("keyword_hints IS NULL OR JSON_TYPE(keyword_hints) = 'ARRAY'", name="ck_tmm_mi_signpost_m_01"),
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
    strength: Mapped[str | None] = mapped_column(
        sa.String(50, collation=BIN),
        nullable=True,
        comment="signpost 강도 (VERYSTRONG/STRONG/MEDIUM/WEAK/VERYWEAK)",
    )
    probability_impact_score: Mapped[Decimal | None] = mapped_column(mysql.DECIMAL(5, 2), nullable=True)
    signpost_reason: Mapped[str | None] = mapped_column(sa.Text(collation=BIN), nullable=True)
    keyword_hints: Mapped[Any | None] = mapped_column(sa.JSON, nullable=True, comment="매칭 키워드 힌트 배열")
    display_order: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default=sa.text("0"))
    use_yn: Mapped[str] = mapped_column(sa.CHAR(1, collation=BIN), nullable=False, server_default=sa.text("'Y'"), comment="사용 여부")
