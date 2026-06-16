from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

import sqlalchemy as sa
from sqlalchemy import CheckConstraint, ForeignKey, Index
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from apps.agents.scenario_group_agent.persistence.scenario_group.models import AuditColumnsMixin, BIN, TABLE_ARGS
from apps.agents.scenario_group_agent.schemas.scenario_enums import SignpostStrength
from apps.common.configs.database.sync_database.base import ORMBase

if TYPE_CHECKING:
    from apps.agents.scenario_group_agent.schemas.create_signposts import GeneratedSignpost


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

    @classmethod
    def convert_from_dto(
        cls,
        dto: "GeneratedSignpost",
        display_order: int,
        user_id: int | None = None,
    ) -> "MiSignpostModel":
        rationale = dto.rationale_ko or ""
        if dto.keyword_hints:
            rationale = (
                f"{rationale}\n\nkeyword_hints: {', '.join(map(str, dto.keyword_hints))}"
            ).strip()
        strength = (
            SignpostStrength.from_string(dto.strength)
            if isinstance(dto.strength, str)
            else dto.strength
        )
        strength_value = strength.to_string() if strength is not None else None
        impact_score = strength.to_impact_score() if strength is not None else None

        model = cls(
            scenario_id=int(dto.scenario_id),
            label=(dto.label or "")[:500],
            probability_direction_code=dto.direction.to_string(),
            strength=strength_value,
            probability_impact_score=impact_score,
            signpost_reason=rationale,
            display_order=display_order,
        )
        if user_id is not None:
            model.crt_usr_logn_id = user_id
            model.mod_usr_logn_id = user_id
        return model
