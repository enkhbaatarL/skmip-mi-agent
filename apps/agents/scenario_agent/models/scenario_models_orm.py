"""
scenario_flow_agent ORM Models — Scenario Domain

tables:
  - tmm_scenariom
  - tmm_scenarioversionm
  - tmm_drivertreenodem
  - tmm_priceforecastm
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
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column

from apps.common.configs.database.sync_database.base import ORMBase


class ScenarioModel(ORMBase):
    __tablename__ = "tmm_scenariom"

    scenario_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="시나리오 일련번호 (PK)"
    )
    crt_dtm: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, comment="시나리오 최초생성일시"
    )
    scenario_group_id: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="시나리오 그룹 키"
    )
    crt_usr_logn_id: Mapped[str] = mapped_column(
        String(50), nullable=False, default="SYSTEM", comment="생성사용자로그인ID"
    )
    mod_usr_logn_id: Mapped[str] = mapped_column(
        String(50), nullable=False, default="SYSTEM", comment="수정사용자로그인ID"
    )
    mod_dtm: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, comment="수정일시"
    )
    del_yn: Mapped[str] = mapped_column(
        CHAR(1), nullable=False, default="N", comment="삭제여부 (Y/N)"
    )
    name: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="시나리오 명칭"
    )
    description: Mapped[str] = mapped_column(
        Text, nullable=False, comment="시나리오 설명"
    )
    mi_event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tmm_mi_mievent_m.mi_event_id"),
        nullable=False, comment="Base MI Event FK"
    )
    status_code: Mapped[str] = mapped_column(
        String(30), nullable=False, default="draft", comment="시나리오 상태"
    )
    valid_from: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, comment="유효기간 시작 일시"
    )
    valid_to: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, comment="유효기간 종료 일시"
    )
    language: Mapped[str] = mapped_column(
        String(10), nullable=False, default="ko", comment="문서 언어"
    )
    dimension_values: Mapped[Any] = mapped_column(
        JSON, nullable=False, comment="Stage 4 결과"
    )
    likelihood: Mapped[str] = mapped_column(
        String(10), nullable=False, comment="시나리오 발생 가능성"
    )
    price_direction: Mapped[Any] = mapped_column(
        JSON, nullable=False, comment="시나리오 가격 영향 강도"
    )

    __table_args__ = (
        Index("tmm_scenariom_ix01", "scenario_group_id"),
        Index("tmm_scenariom_ix02", "mi_event_id"),
        Index("tmm_scenariom_ix03", "status_code"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"},
    )


class ScenarioVersionModel(ORMBase):
    __tablename__ = "tmm_scenarioversionm"

    version_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="시나리오 버전 ID PK"
    )
    crt_user_id: Mapped[str] = mapped_column(
        String(50), nullable=False, default="SYSTEM", comment="생성 사용자 ID"
    )
    crt_dtm: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, comment="생성 일시"
    )
    mod_user_id: Mapped[str] = mapped_column(
        String(50), nullable=False, default="SYSTEM", comment="수정 사용자 ID"
    )
    mod_dtm: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, comment="수정 일시"
    )
    del_yn: Mapped[str] = mapped_column(
        CHAR(1), nullable=False, default="N", comment="삭제 여부 Y/N"
    )
    scenario_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tmm_scenariom.scenario_id"),
        nullable=False, comment="시나리오 ID FK"
    )
    version_number: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="버전 번호"
    )
    scenario_snapshot: Mapped[Optional[Any]] = mapped_column(
        JSON, nullable=True, comment="시나리오 스냅샷 데이터"
    )
    change_summary: Mapped[Optional[str]] = mapped_column(
        String(1000), nullable=True, comment="변경 사항 요약"
    )
    created_by: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="버전 생성 사용자"
    )

    __table_args__ = (
        Index("tmm_scenarioversionm_ix01", "scenario_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"},
    )


class DriverTreeNodeModel(ORMBase):
    __tablename__ = "tmm_drivertreenodem"

    node_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="Driver Tree 노드 ID PK"
    )
    crt_user_id: Mapped[str] = mapped_column(
        String(50), nullable=False, default="SYSTEM", comment="생성 사용자 ID"
    )
    crt_dtm: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, comment="생성 일시"
    )
    mod_user_id: Mapped[str] = mapped_column(
        String(50), nullable=False, default="SYSTEM", comment="수정 사용자 ID"
    )
    mod_dtm: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, comment="수정 일시"
    )
    del_yn: Mapped[str] = mapped_column(
        CHAR(1), nullable=False, default="N", comment="삭제 여부 Y/N"
    )
    scenario_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tmm_scenariom.scenario_id"),
        nullable=False, comment="시나리오 ID FK"
    )
    driver_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="Driver 명칭"
    )
    driver_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="Driver 유형"
    )
    impact_level: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="영향 레벨"
    )
    weight: Mapped[Optional[float]] = mapped_column(
        Float(8), nullable=True, comment="가중치"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Driver 설명"
    )
    sort_order: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="정렬 순서"
    )

    __table_args__ = (
        Index("tmm_drivertreenodem_ix01", "scenario_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"},
    )


class PriceForecastModel(ORMBase):
    __tablename__ = "tmm_priceforecastm"

    forecast_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="가격 예측 ID PK"
    )
    crt_user_id: Mapped[str] = mapped_column(
        String(50), nullable=False, default="SYSTEM", comment="생성 사용자 ID"
    )
    crt_dtm: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, comment="생성 일시"
    )
    mod_user_id: Mapped[str] = mapped_column(
        String(50), nullable=False, default="SYSTEM", comment="수정 사용자 ID"
    )
    mod_dtm: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, comment="수정 일시"
    )
    del_yn: Mapped[str] = mapped_column(
        CHAR(1), nullable=False, default="N", comment="삭제 여부 Y/N"
    )
    scenario_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tmm_scenariom.scenario_id"),
        nullable=False, comment="시나리오 ID FK"
    )
    benchmark: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="벤치마크"
    )
    base_price: Mapped[Optional[float]] = mapped_column(
        Float(12), nullable=True, comment="기준 가격"
    )
    forecast_low: Mapped[Optional[float]] = mapped_column(
        Float(12), nullable=True, comment="예측 가격 하한"
    )
    forecast_high: Mapped[Optional[float]] = mapped_column(
        Float(12), nullable=True, comment="예측 가격 상한"
    )
    forecast_median: Mapped[Optional[float]] = mapped_column(
        Float(12), nullable=True, comment="예측 가격 중간값"
    )
    currency: Mapped[str] = mapped_column(
        String(10), nullable=False, default="USD", comment="통화 단위"
    )
    unit: Mapped[str] = mapped_column(
        String(10), nullable=False, default="MMBtu", comment="에너지 단위"
    )
    forecast_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, comment="예측 일시"
    )
    valid_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, comment="유효 기간"
    )
    confidence_interval: Mapped[Optional[float]] = mapped_column(
        Float(5), nullable=True, comment="신뢰 구간 0~1"
    )

    __table_args__ = (
        Index("tmm_priceforecastm_ix01", "scenario_id"),
        Index("tmm_priceforecastm_ix02", "benchmark"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"},
    )