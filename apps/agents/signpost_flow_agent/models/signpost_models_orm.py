"""
signpost_flow_agent ORM Models — Signpost Domain

tables:
  - tmm_signpostm
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    CHAR,
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column

from apps.common.configs.database.sync_database.base import ORMBase


class SignpostModel(ORMBase):
    __tablename__ = "tmm_signpostm"

    signpost_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="Signpost 일련번호 (PK)"
    )
    crt_dtm: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, comment="최초생성일시"
    )
    scenario_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tmm_scenariom.scenario_id"),
        nullable=False, comment="시나리오 FK"
    )
    crt_usr_logn_id: Mapped[str] = mapped_column(
        String(50), nullable=False, default="SYSTEM", comment="생성사용자로그인ID"
    )
    mod_usr_logn_id: Mapped[Optional[str]] = mapped_column(
        String(50), default="SYSTEM", comment="수정사용자로그인ID"
    )
    mod_dtm: Mapped[Optional[datetime]] = mapped_column(
        DateTime, default=datetime.utcnow, comment="수정일시"
    )
    del_yn: Mapped[str] = mapped_column(
        CHAR(1), nullable=False, default="N", comment="삭제여부 (Y/N)"
    )
    status_code: Mapped[str] = mapped_column(
        String(30), nullable=False, default="draft", comment="Signpost 상태"
    )
    language: Mapped[str] = mapped_column(
        String(10), nullable=False, default="ko", comment="문서 언어"
    )
    label: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="Signpost 레이블"
    )
    signpost_class: Mapped[Optional[str]] = mapped_column(
        String(30), default="observation", comment="Signpost 분류"
    )
    signpost_source: Mapped[str] = mapped_column(
        String(30), nullable=False, default="mi_record", comment="Signpost 출처 유형"
    )
    direction: Mapped[str] = mapped_column(
        String(10), nullable=False, default="SUP", comment="시나리오 영향 방향"
    )
    strength: Mapped[Optional[str]] = mapped_column(
        String(10), nullable=True, comment="신호 강도"
    )
    keyword_hints: Mapped[Any] = mapped_column(
        JSON, nullable=False, comment="모니터링용 검색 키워드 리스트"
    )

    __table_args__ = (
        Index("tmm_signpostm_ix01", "scenario_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"},
    )