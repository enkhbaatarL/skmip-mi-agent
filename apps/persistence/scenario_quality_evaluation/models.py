from __future__ import annotations

# ruff: noqa: CPY001
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from apps.common.configs.database.sync_database.base import ORMBase
from apps.persistence.scenario_group.models import BIN, TABLE_ARGS, AuditColumnsMixin


class MiScenarioQualityEvaluationModel(AuditColumnsMixin, ORMBase):
    __tablename__ = "tmm_mi_scenario_quality_eval_m"
    __table_args__ = (
        UniqueConstraint("request_id", name="uk_tmm_mi_scenario_quality_eval_m_01"),
        CheckConstraint(
            "verdict IS NULL OR verdict IN ('PASS','WARN','FAIL','NEEDS_FACT')",
            name="ck_tmm_mi_scenario_quality_eval_m_01",
        ),
        {**TABLE_ARGS, "comment": "시나리오 집합 품질 평가 이력"},
    )

    operation_id: Mapped[str] = mapped_column(
        mysql.VARCHAR(26, collation=BIN),
        ForeignKey(
            "tmm_mi_scenario_group_operation_m.operation_id",
            name="fk_tmm_mi_scenario_quality_eval_m_01",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )
    request_id: Mapped[str] = mapped_column(mysql.VARCHAR(36, collation=BIN), nullable=False)
    input_snapshot: Mapped[dict[str, object]] = mapped_column(mysql.JSON(), nullable=False)
    input_hash: Mapped[str] = mapped_column(mysql.CHAR(64, collation=BIN), nullable=False)
    prompt_version: Mapped[str] = mapped_column(mysql.VARCHAR(64, collation=BIN), nullable=False)
    result_payload: Mapped[dict[str, object] | None] = mapped_column(mysql.JSON(), nullable=True)
    verdict: Mapped[str | None] = mapped_column(mysql.VARCHAR(16, collation=BIN), nullable=True)
    average_score: Mapped[Decimal | None] = mapped_column(mysql.DECIMAL(5, 4), nullable=True)
    llm_metadata: Mapped[dict[str, object] | None] = mapped_column(mysql.JSON(), nullable=True)
