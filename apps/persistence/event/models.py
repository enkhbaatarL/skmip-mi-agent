"""
scenario_group_agent ORM Models - MI Event Domain

tables:
  - tmm_mi_event_type_l1_m
  - tmm_mi_event_type_l2_m
  - tmm_mi_mievent_m
  - tmm_mi_mievent_record_map
  - tmm_mi_mievent_snapshot_m
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import sqlalchemy
from sqlalchemy import ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects import mysql as mysql_types
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.common.configs.database.sync_database.base import ORMBase


class AuditColumnsMixin:
    crt_usr_logn_id: Mapped[str] = mapped_column(
        sqlalchemy.String(100, collation="utf8mb4_bin"),
        nullable=False,
        server_default=sqlalchemy.text("'system'"),
        comment="생성자",
    )
    crt_dtm: Mapped[datetime] = mapped_column(
        mysql_types.DATETIME(fsp=6),
        nullable=False,
        server_default=sqlalchemy.text("CURRENT_TIMESTAMP(6)"),
        comment="생성일시",
    )
    mod_usr_logn_id: Mapped[str] = mapped_column(
        sqlalchemy.String(100, collation="utf8mb4_bin"),
        nullable=False,
        server_default=sqlalchemy.text("'system'"),
        comment="수정자",
    )
    mod_dtm: Mapped[datetime] = mapped_column(
        mysql_types.DATETIME(fsp=6),
        nullable=False,
        server_default=sqlalchemy.text("CURRENT_TIMESTAMP(6)"),
        server_onupdate=sqlalchemy.text("CURRENT_TIMESTAMP(6)"),
        comment="수정일시",
    )
    del_yn: Mapped[str] = mapped_column(
        sqlalchemy.CHAR(1, collation="utf8mb4_bin"),
        nullable=False,
        server_default=sqlalchemy.text("'N'"),
        comment="삭제여부",
    )


class MiEventContentColumnsMixin:
    # Agent 공개 계약은 one_line_summary 를 제목으로, search_text 를 요약으로 사용한다.
    # 원본 Event 테이블의 DB 전용 event_title 존재 여부와 무관하게 이 ORM에서는 읽지 않는다.
    search_text: Mapped[str] = mapped_column(
        sqlalchemy.String(500, collation="utf8mb4_bin"),
        nullable=False,
        comment="검색용 요약 텍스트",
    )
    one_line_summary: Mapped[str] = mapped_column(
        sqlalchemy.String(300, collation="utf8mb4_bin"),
        nullable=False,
        comment="한줄 요약 (이벤트 제목)",
    )
    key_bullets_json: Mapped[Any] = mapped_column(
        sqlalchemy.JSON,
        nullable=False,
        comment="핵심 bullet 목록 JSON",
    )
    detail_analysis: Mapped[str] = mapped_column(
        mysql_types.LONGTEXT(collation="utf8mb4_bin"),
        nullable=False,
        comment="이벤트 상세 분석 본문",
    )
    numeric_facts_md: Mapped[str | None] = mapped_column(
        mysql_types.LONGTEXT(collation="utf8mb4_bin"),
        nullable=True,
        comment="이벤트 정량 근거 Markdown",
    )
    tags_json: Mapped[Any | None] = mapped_column(
        sqlalchemy.JSON,
        nullable=True,
        comment="이벤트 태그 목록 JSON",
    )
    occurred_at: Mapped[datetime | None] = mapped_column(
        mysql_types.DATETIME(fsp=6),
        nullable=True,
        comment="이벤트 실제 발생 일시",
    )


class MiEventTypeL1Model(AuditColumnsMixin, ORMBase):
    __tablename__ = "tmm_mi_event_type_l1_m"

    event_type_l1_id: Mapped[int] = mapped_column(
        mysql_types.INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
        comment="이벤트 유형 L1 PK",
    )
    level_1_code: Mapped[str] = mapped_column(
        sqlalchemy.String(100, collation="utf8mb4_bin"),
        nullable=False,
        comment="이벤트 유형 L1 코드",
    )
    level_1_label: Mapped[str] = mapped_column(
        sqlalchemy.String(200, collation="utf8mb4_bin"),
        nullable=False,
        comment="이벤트 유형 L1 한글명",
    )

    __table_args__ = (
        UniqueConstraint("level_1_code", name="uk_tmm_mi_event_type_l1_m_01"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_bin"},
    )

    level_2_types: Mapped[list[MiEventTypeL2Model]] = relationship(
        "MiEventTypeL2Model", back_populates="level_1"
    )


class MiEventTypeL2Model(AuditColumnsMixin, ORMBase):
    __tablename__ = "tmm_mi_event_type_l2_m"

    event_type_l2_id: Mapped[int] = mapped_column(
        mysql_types.INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
        comment="이벤트 유형 L2 PK",
    )
    event_type_l1_id: Mapped[int] = mapped_column(
        mysql_types.INTEGER(unsigned=True),
        ForeignKey("tmm_mi_event_type_l1_m.event_type_l1_id"),
        nullable=False,
        comment="이벤트 유형 L1 FK",
    )
    level_2_code: Mapped[str] = mapped_column(
        sqlalchemy.String(150, collation="utf8mb4_bin"),
        nullable=False,
        comment="이벤트 유형 L2 코드",
    )
    level_2_label: Mapped[str] = mapped_column(
        sqlalchemy.String(200, collation="utf8mb4_bin"),
        nullable=False,
        comment="이벤트 유형 L2 한글명",
    )

    __table_args__ = (
        UniqueConstraint("event_type_l1_id", "level_2_code", name="uk_tmm_mi_event_type_l2_m_01"),
        Index("idx_tmm_mi_event_type_l2_m_01", "event_type_l1_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_bin"},
    )

    level_1: Mapped[MiEventTypeL1Model] = relationship(
        "MiEventTypeL1Model", back_populates="level_2_types"
    )


class MiEventModel(MiEventContentColumnsMixin, AuditColumnsMixin, ORMBase):
    __tablename__ = "tmm_mi_mievent_m"

    mi_event_id: Mapped[int] = mapped_column(
        mysql_types.INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
        comment="MI Event PK",
    )
    event_type_l2_id: Mapped[int | None] = mapped_column(
        mysql_types.INTEGER(unsigned=True),
        ForeignKey("tmm_mi_event_type_l2_m.event_type_l2_id"),
        nullable=True,
        comment="이벤트 유형 L2 FK",
    )
    latest_record_first_created: Mapped[datetime | None] = mapped_column(
        mysql_types.DATETIME(fsp=6),
        nullable=True,
        comment="Event 관련 Record 중 최신 first_created 시각",
    )
    oldest_record_first_created: Mapped[datetime | None] = mapped_column(
        mysql_types.DATETIME(fsp=6),
        nullable=True,
        comment="Event 관련 Record 중 오래된 first_created 시각",
    )
    estimated_impact_id: Mapped[str | None] = mapped_column(
        sqlalchemy.String(100, collation="utf8mb4_bin"),
        nullable=True,
        comment="Impact ID",
    )
    signal_yn: Mapped[str] = mapped_column(
        sqlalchemy.CHAR(1, collation="utf8mb4_bin"),
        nullable=False,
        server_default=sqlalchemy.text("'Y'"),
        comment="신호 여부",
    )
    signal_confidence: Mapped[float | None] = mapped_column(
        mysql_types.DECIMAL(5, 4),
        nullable=True,
        server_default=sqlalchemy.text("0"),
        comment="신호 신뢰도",
    )
    signal_reason: Mapped[str | None] = mapped_column(
        sqlalchemy.String(100, collation="utf8mb4_bin"),
        nullable=True,
        comment="신호 판정 근거",
    )
    scenario_suggest_yn: Mapped[str] = mapped_column(
        sqlalchemy.CHAR(1, collation="utf8mb4_bin"),
        nullable=False,
        server_default=sqlalchemy.text("'N'"),
        comment="시나리오화 추천 여부",
    )
    scenario_suggest_reason: Mapped[str | None] = mapped_column(
        sqlalchemy.String(500, collation="utf8mb4_bin"),
        nullable=True,
        comment="시나리오화 추천 근거",
    )
    institution_view_synthesis: Mapped[str | None] = mapped_column(
        sqlalchemy.String(1000, collation="utf8mb4_bin"),
        nullable=True,
        comment="기관 전망 View 종합",
    )
    new_yn: Mapped[str] = mapped_column(
        sqlalchemy.CHAR(1, collation="utf8mb4_bin"),
        nullable=False,
        server_default=sqlalchemy.text("'Y'"),
        comment="신규생성 여부 (Y: 신규생성, N: 갱신)",
    )

    __table_args__ = (
        Index("idx_tmm_mi_mievent_m_01", "event_type_l2_id"),
        Index("idx_tmm_mi_mievent_m_02", "occurred_at"),
        Index("idx_tmm_mi_mievent_m_03", "latest_record_first_created"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_bin"},
    )

    type_l2: Mapped[MiEventTypeL2Model] = relationship("MiEventTypeL2Model")
    record_maps: Mapped[list[MiEventRecordMapModel]] = relationship(
        "MiEventRecordMapModel", back_populates="event"
    )

    @property
    def market_and_institution_view(self) -> str | None:
        """Compatibility shim for legacy code paths."""
        return None


class MiEventRecordMapModel(AuditColumnsMixin, ORMBase):
    __tablename__ = "tmm_mi_mievent_record_map"

    mi_event_record_map_id: Mapped[int] = mapped_column(
        mysql_types.INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
        comment="Event-Record 매핑 PK",
    )
    mi_event_id: Mapped[int] = mapped_column(
        mysql_types.INTEGER(unsigned=True),
        ForeignKey("tmm_mi_mievent_m.mi_event_id"),
        nullable=False,
        comment="MI Event ID",
    )
    mi_record_id: Mapped[int] = mapped_column(
        mysql_types.INTEGER(unsigned=True),
        nullable=False,
        comment="MI Record ID",
    )

    __table_args__ = (
        UniqueConstraint("mi_event_id", "mi_record_id", name="uk_tmm_mi_mievent_record_map_01"),
        Index("idx_tmm_mi_mievent_record_map_01", "mi_record_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_bin"},
    )

    event: Mapped[MiEventModel] = relationship(
        "MiEventModel", back_populates="record_maps"
    )


class MiEventSnapshotModel(MiEventContentColumnsMixin, ORMBase):
    """Event 콘텐츠 변경 이력 스냅샷 (외부 ingestion 파이프라인이 적재, 이 레포는 읽기 전용).

    mi_event_id / event_type_l2_id / previous_mi_event_snapshot_id는 DB에 FK가
    설정되어 있지 않음(원본이 갱신·삭제돼도 과거 스냅샷은 그대로 남아야 하므로).
    """

    __tablename__ = "tmm_mi_mievent_snapshot_m"

    mi_event_snapshot_id: Mapped[int] = mapped_column(
        mysql_types.INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
        comment="MI Event 스냅샷 PK",
    )
    mi_event_id: Mapped[int] = mapped_column(
        mysql_types.INTEGER(unsigned=True),
        nullable=False,
        comment="원본 MI Event ID",
    )
    snapshot_version_no: Mapped[int | None] = mapped_column(
        mysql_types.INTEGER(unsigned=True),
        nullable=True,
        comment="동일 MI Event 내 Snapshot 순차 버전 번호",
    )
    previous_mi_event_snapshot_id: Mapped[int | None] = mapped_column(
        mysql_types.INTEGER(unsigned=True),
        nullable=True,
        comment="직전 MI Event Snapshot ID",
    )
    snapshot_crt_usr_logn_id: Mapped[str] = mapped_column(
        sqlalchemy.String(100, collation="utf8mb4_bin"),
        nullable=False,
        server_default=sqlalchemy.text("'system'"),
        comment="스냅샷 생성 사용자 ID",
    )
    snapshot_crt_dtm: Mapped[datetime] = mapped_column(
        mysql_types.DATETIME(fsp=6),
        nullable=False,
        server_default=sqlalchemy.text("CURRENT_TIMESTAMP(6)"),
        comment="스냅샷 저장 일시",
    )
    update_trigger_cd: Mapped[str] = mapped_column(
        sqlalchemy.String(30, collation="utf8mb4_bin"),
        nullable=False,
        server_default=sqlalchemy.text("'RECORD_INGESTION'"),
        comment="Event 갱신 트리거 코드",
    )
    update_reason: Mapped[str | None] = mapped_column(
        mysql_types.TEXT(collation="utf8mb4_bin"),
        nullable=True,
        comment="MCP 사용자 Event 수정 사유",
    )
    changed_fields_json: Mapped[Any | None] = mapped_column(
        sqlalchemy.JSON,
        nullable=True,
        comment="갱신 시 실제 변경된 Event 컬럼명 목록",
    )
    event_type_l2_id: Mapped[int | None] = mapped_column(
        mysql_types.INTEGER(unsigned=True),
        nullable=True,
        comment="원본 이벤트 유형 L2 ID (FK 미설정)",
    )
    latest_record_first_created: Mapped[datetime | None] = mapped_column(
        mysql_types.DATETIME(fsp=6),
        nullable=True,
        comment="Event 관련 Record 중 최신 first_created 시각",
    )
    oldest_record_first_created: Mapped[datetime | None] = mapped_column(
        mysql_types.DATETIME(fsp=6),
        nullable=True,
        comment="Event 관련 Record 중 오래된 first_created 시각",
    )
    estimated_impact_id: Mapped[str | None] = mapped_column(
        sqlalchemy.String(100, collation="utf8mb4_bin"),
        nullable=True,
        comment="Impact ID",
    )
    signal_yn: Mapped[str] = mapped_column(
        sqlalchemy.CHAR(1, collation="utf8mb4_bin"),
        nullable=False,
        server_default=sqlalchemy.text("'Y'"),
        comment="신호 여부",
    )
    signal_confidence: Mapped[float | None] = mapped_column(
        mysql_types.DECIMAL(5, 4),
        nullable=True,
        server_default=sqlalchemy.text("0"),
        comment="신호 신뢰도",
    )
    signal_reason: Mapped[str | None] = mapped_column(
        sqlalchemy.String(100, collation="utf8mb4_bin"),
        nullable=True,
        comment="신호 판정 근거",
    )
    scenario_suggest_yn: Mapped[str] = mapped_column(
        sqlalchemy.CHAR(1, collation="utf8mb4_bin"),
        nullable=False,
        server_default=sqlalchemy.text("'N'"),
        comment="시나리오화 추천 여부",
    )
    scenario_suggest_reason: Mapped[str | None] = mapped_column(
        sqlalchemy.String(500, collation="utf8mb4_bin"),
        nullable=True,
        comment="시나리오화 추천 근거",
    )
    new_yn: Mapped[str] = mapped_column(
        sqlalchemy.CHAR(1, collation="utf8mb4_bin"),
        nullable=False,
        server_default=sqlalchemy.text("'Y'"),
        comment="신규생성 여부 (Y: 신규생성, N: 갱신)",
    )
    del_yn: Mapped[str] = mapped_column(
        sqlalchemy.CHAR(1, collation="utf8mb4_bin"),
        nullable=False,
        server_default=sqlalchemy.text("'N'"),
        comment="원본 Event 삭제여부",
    )
    institution_view_synthesis: Mapped[str | None] = mapped_column(
        sqlalchemy.String(1000, collation="utf8mb4_bin"),
        nullable=True,
        comment="기관 전망 View 종합",
    )
    event_crt_usr_logn_id: Mapped[str] = mapped_column(
        sqlalchemy.String(100, collation="utf8mb4_bin"),
        nullable=False,
        comment="원본 Event 생성 사용자 ID",
    )
    event_crt_dtm: Mapped[datetime] = mapped_column(
        mysql_types.DATETIME(fsp=6),
        nullable=False,
        comment="원본 Event 생성 일시",
    )
    event_mod_usr_logn_id: Mapped[str] = mapped_column(
        sqlalchemy.String(100, collation="utf8mb4_bin"),
        nullable=False,
        comment="스냅샷 저장 시점의 원본 Event 최종 수정 사용자 ID",
    )
    event_mod_dtm: Mapped[datetime] = mapped_column(
        mysql_types.DATETIME(fsp=6),
        nullable=False,
        comment="스냅샷 저장 시점의 원본 Event 최종 수정 일시",
    )

    __table_args__ = (
        UniqueConstraint("mi_event_id", "snapshot_version_no", name="uk_tmm_mi_mievent_snapshot_m_01"),
        Index("idx_tmm_mi_mievent_snapshot_m_01", "mi_event_id", "snapshot_crt_dtm"),
        Index("idx_tmm_mi_mievent_snapshot_m_02", "previous_mi_event_snapshot_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_bin"},
    )
