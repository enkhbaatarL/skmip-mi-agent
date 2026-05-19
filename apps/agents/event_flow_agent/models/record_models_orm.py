"""
event_flow_agent ORM Models — External Record Domain (Read-Only)

tables (external, outside MI domain):
  - tmd_mi_record
  - tmd_nws_smry
  - tif_refinewsdatar
  - tmd_gdsm
  - tmd_nws_sig

These are read-only models — the MI Agent does not own these tables.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from apps.common.configs.database.sync_database.base import ORMBase


class MiRecordModel(ORMBase):
    """tmd_mi_record — MI Record master (read-only)"""
    __tablename__ = "tmd_mi_record"

    mi_record_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, comment="MI Record ID PK"
    )
    first_created: Mapped[Optional[datetime]] = mapped_column(
        DateTime(6), nullable=True, comment="최초 생성 일시"
    )
    record_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="레코드 유형"
    )
    source_obj_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="원천 객체 ID"
    )


class NewsSummaryModel(ORMBase):
    """tmd_nws_smry — News Summary (read-only)"""
    __tablename__ = "tmd_nws_smry"

    nws_smry_id: Mapped[str] = mapped_column(
        String(100), primary_key=True, comment="뉴스 요약 ID"
    )
    data_reg_sn: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="데이터 등록 일련번호"
    )
    gds_id: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="상품 ID"
    )
    first_created: Mapped[Optional[datetime]] = mapped_column(
        DateTime(6), nullable=True, comment="최초 생성 일시"
    )
    smry: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="요약문"
    )


class RefineNewsDataModel(ORMBase):
    """tif_refinewsdatar — Refined News Data (read-only)"""
    __tablename__ = "tif_refinewsdatar"

    data_reg_sn: Mapped[int] = mapped_column(
        Integer, primary_key=True, comment="데이터 등록 일련번호"
    )
    first_created: Mapped[Optional[datetime]] = mapped_column(
        DateTime(6), nullable=True, comment="최초 생성 일시"
    )
    title: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="제목"
    )


class GoodsMasterModel(ORMBase):
    """tmd_gdsm — Goods Master (read-only)"""
    __tablename__ = "tmd_gdsm"

    gds_id: Mapped[str] = mapped_column(
        String(50), primary_key=True, comment="상품 ID"
    )
    gds_no: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="상품 번호"
    )


class NewsSignalModel(ORMBase):
    """tmd_nws_sig — News Signal (read-only)"""
    __tablename__ = "tmd_nws_sig"

    nws_smry_id: Mapped[str] = mapped_column(
        String(100), primary_key=True, comment="뉴스 요약 ID FK"
    )
    nws_mrkt_ctgr_cd: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="뉴스 시장 구분 코드"
    )