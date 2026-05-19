"""
event_flow_agent ORM Models — MI Event Domain

tables:
  - tmm_mi_event_type_l1_m
  - tmm_mi_event_type_l2_m
  - tmm_mi_mievent_m
  - tmm_mi_mievent_record_map
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    CHAR,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.common.configs.database.sync_database.base import ORMBase


class MiEventTypeL1Model(ORMBase):
    __tablename__ = "tmm_mi_event_type_l1_m"

    event_type_l1_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="이벤트 유형 L1 PK"
    )
    level_1_code: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="이벤트 유형 L1 코드"
    )
    level_1_label: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="이벤트 유형 L1 한글명"
    )
    crt_usr_logn_id: Mapped[str] = mapped_column(
        String(100), nullable=False, default="system", comment="생성자"
    )
    crt_dtm: Mapped[datetime] = mapped_column(
        DateTime(6), nullable=False, default=datetime.utcnow, comment="생성일시"
    )
    mod_usr_logn_id: Mapped[str] = mapped_column(
        String(100), nullable=False, default="system", comment="수정자"
    )
    mod_dtm: Mapped[datetime] = mapped_column(
        DateTime(6), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, comment="수정일시"
    )
    del_yn: Mapped[str] = mapped_column(
        CHAR(1), nullable=False, default="N", comment="삭제여부"
    )

    __table_args__ = (
        UniqueConstraint("level_1_code", name="uk_tmm_mi_event_type_l1_m_01"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_bin"},
    )

    level_2_types: Mapped[list[MiEventTypeL2Model]] = relationship(
        "MiEventTypeL2Model", back_populates="level_1"
    )


class MiEventTypeL2Model(ORMBase):
    __tablename__ = "tmm_mi_event_type_l2_m"

    event_type_l2_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="이벤트 유형 L2 PK"
    )
    event_type_l1_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tmm_mi_event_type_l1_m.event_type_l1_id"),
        nullable=False, comment="이벤트 유형 L1 FK"
    )
    level_2_code: Mapped[str] = mapped_column(
        String(150), nullable=False, comment="이벤트 유형 L2 코드"
    )
    level_2_label: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="이벤트 유형 L2 한글명"
    )
    crt_usr_logn_id: Mapped[str] = mapped_column(
        String(100), nullable=False, default="system", comment="생성자"
    )
    crt_dtm: Mapped[datetime] = mapped_column(
        DateTime(6), nullable=False, default=datetime.utcnow, comment="생성일시"
    )
    mod_usr_logn_id: Mapped[str] = mapped_column(
        String(100), nullable=False, default="system", comment="수정자"
    )
    mod_dtm: Mapped[datetime] = mapped_column(
        DateTime(6), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, comment="수정일시"
    )
    del_yn: Mapped[str] = mapped_column(
        CHAR(1), nullable=False, default="N", comment="삭제여부"
    )

    __table_args__ = (
        UniqueConstraint("event_type_l1_id", "level_2_code",
                         name="uk_tmm_mi_event_type_l2_m_01"),
        Index("idx_tmm_mi_event_type_l2_m_01", "event_type_l1_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_bin"},
    )

    level_1: Mapped[MiEventTypeL1Model] = relationship(
        "MiEventTypeL1Model", back_populates="level_2_types"
    )


class MiEventModel(ORMBase):
    __tablename__ = "tmm_mi_mievent_m"

    mi_event_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="MI Event PK"
    )
    event_title: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="이벤트 제목"
    )
    one_line_summary: Mapped[Optional[str]] = mapped_column(
        String(300), nullable=True, comment="한줄 요약"
    )
    key_bullets_json: Mapped[Optional[Any]] = mapped_column(
        JSON, nullable=True, comment="핵심 bullet 목록 JSON"
    )
    event_summary: Mapped[str] = mapped_column(
        Text, nullable=False, comment="이벤트 상세 분석 본문"
    )
    market_and_institution_view: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="시장 반응 및 기관 전망"
    )
    tags_json: Mapped[Optional[Any]] = mapped_column(
        JSON, nullable=True, comment="이벤트 태그 목록 JSON"
    )
    event_type_l2_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tmm_mi_event_type_l2_m.event_type_l2_id"),
        nullable=False, comment="이벤트 유형 L2 FK"
    )
    mi_event_status_code: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="이벤트 상태 코드"
    )
    estimated_impact_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="Impact ID"
    )
    occurred_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(6), nullable=True, comment="이벤트 실제 발생 일시"
    )
    probability: Mapped[float] = mapped_column(
        Float(5), nullable=False, default=0, comment="이벤트 발생 확률 0.00 ~ 1.00"
    )
    dedup_state: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="중복처리 상태"
    )
    signal_yn: Mapped[str] = mapped_column(
        CHAR(1), nullable=False, default="Y", comment="신호 여부"
    )
    signal_confidence: Mapped[float] = mapped_column(
        Float(5), nullable=False, default=0, comment="신호 신뢰도"
    )
    signal_reason: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="신호 판정 근거"
    )
    crt_usr_logn_id: Mapped[str] = mapped_column(
        String(100), nullable=False, default="system", comment="생성자"
    )
    crt_dtm: Mapped[datetime] = mapped_column(
        DateTime(6), nullable=False, default=datetime.utcnow, comment="생성일시"
    )
    mod_usr_logn_id: Mapped[str] = mapped_column(
        String(100), nullable=False, default="system", comment="수정자"
    )
    mod_dtm: Mapped[datetime] = mapped_column(
        DateTime(6), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, comment="수정일시"
    )
    del_yn: Mapped[str] = mapped_column(
        CHAR(1), nullable=False, default="N", comment="삭제여부"
    )

    __table_args__ = (
        Index("idx_tmm_mi_mievent_m_01", "event_type_l2_id"),
        Index("idx_tmm_mi_mievent_m_02", "mi_event_status_code"),
        Index("idx_tmm_mi_mievent_m_03", "occurred_at"),
        Index("idx_tmm_mi_mievent_m_04", "dedup_state"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_bin"},
    )

    type_l2: Mapped[MiEventTypeL2Model] = relationship("MiEventTypeL2Model")
    record_maps: Mapped[list[MiEventRecordMapModel]] = relationship(
        "MiEventRecordMapModel", back_populates="event"
    )


class MiEventRecordMapModel(ORMBase):
    __tablename__ = "tmm_mi_mievent_record_map"

    mi_event_record_map_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="Event-Record 매핑 PK"
    )
    mi_event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tmm_mi_mievent_m.mi_event_id"),
        nullable=False, comment="MI Event ID"
    )
    mi_record_id: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="MI Record ID"
    )
    crt_usr_logn_id: Mapped[str] = mapped_column(
        String(100), nullable=False, default="system", comment="생성자"
    )
    crt_dtm: Mapped[datetime] = mapped_column(
        DateTime(6), nullable=False, default=datetime.utcnow, comment="생성일시"
    )
    mod_usr_logn_id: Mapped[str] = mapped_column(
        String(100), nullable=False, default="system", comment="수정자"
    )
    mod_dtm: Mapped[datetime] = mapped_column(
        DateTime(6), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, comment="수정일시"
    )
    del_yn: Mapped[str] = mapped_column(
        CHAR(1), nullable=False, default="N", comment="삭제여부"
    )

    __table_args__ = (
        UniqueConstraint("mi_event_id", "mi_record_id",
                         name="uk_tmm_mi_mievent_record_map_01"),
        Index("idx_tmm_mi_mievent_record_map_01", "mi_record_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_bin"},
    )

    event: Mapped[MiEventModel] = relationship(
        "MiEventModel", back_populates="record_maps"
    )