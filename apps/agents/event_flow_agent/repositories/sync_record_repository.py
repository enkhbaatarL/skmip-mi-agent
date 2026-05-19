# apps/agents/event_flow_agent/repositories/sync_record_repository.py
#   kmj20260423목
"""
원천 record 조회용 Repository 모듈

역할:
- event_flow_agent가 분석 대상으로 사용할 원천 뉴스/레코드를 DB에서 조회한다.
- tmd_mi_record를 중심으로 요약문, 제목, 상품, 시장구분 등 관련 테이블을 조인하여
  분석에 필요한 형태의 원천 데이터를 반환한다.

입력:
- market_category
- limit
- from_first_created
- to_first_created

출력:
- 원천 record 목록(list[dict])

설계 의도:
- 도메인별 SQL 책임을 repository 계층에 집중
- service/node가 SQL 세부 구현을 알지 않도록 분리
- 공통 DB 세션/베이스는 common 패키지를 사용하고,
  실제 조회 쿼리는 event_flow_agent 도메인 repository가 담당
"""

from __future__ import annotations
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from apps.agents.event_flow_agent.models.record_models_orm import (
    MiRecordModel,
    NewsSummaryModel,
    RefineNewsDataModel,
    GoodsMasterModel,
    NewsSignalModel,
)
from apps.common.configs.database.sync_database.base import BaseSyncSQLRepository


class SyncRecordRepository(BaseSyncSQLRepository):
    """MI Record 원천 조회용 Repository."""

    def __init__(self, session: Any) -> None:
        super().__init__(session)

    def fetch_news_records(
        self,
        market_category: str = "LNG",
        limit: int = 50,
        from_first_created: str | None = None,
        to_first_created: str | None = None,
    ) -> list[dict[str, Any]]:
        """ORM을 사용하여 원천 record를 조회한다."""
        stmt = (
            select(
                MiRecordModel.mi_record_id,
                MiRecordModel.first_created,
                MiRecordModel.record_type,
                MiRecordModel.source_obj_id,
                GoodsMasterModel.gds_no,
                RefineNewsDataModel.title,
                NewsSummaryModel.smry,
                NewsSignalModel.nws_mrkt_ctgr_cd,
            )
            .join(NewsSummaryModel, MiRecordModel.source_obj_id == NewsSummaryModel.nws_smry_id)
            .join(
                RefineNewsDataModel,
                (NewsSummaryModel.data_reg_sn == RefineNewsDataModel.data_reg_sn)
                & (NewsSummaryModel.first_created == RefineNewsDataModel.first_created),
            )
            .join(GoodsMasterModel, GoodsMasterModel.gds_id == NewsSummaryModel.gds_id)
            .join(NewsSignalModel, NewsSummaryModel.nws_smry_id == NewsSignalModel.nws_smry_id)
            .where(
                MiRecordModel.record_type == "NEWS",
                NewsSignalModel.nws_mrkt_ctgr_cd == market_category,
            )
            .order_by(MiRecordModel.first_created.desc())
            .limit(limit)
        )

        if from_first_created:
            stmt = stmt.where(MiRecordModel.first_created >= from_first_created)
        if to_first_created:
            stmt = stmt.where(MiRecordModel.first_created <= to_first_created)

        rows = self.session.execute(stmt).all()

        results: list[dict[str, Any]] = []
        for row in rows:
            first_created = row.first_created
            if isinstance(first_created, datetime):
                first_created = first_created.isoformat()

            results.append({
                "mi_record_id": row.mi_record_id,
                "first_created": first_created,
                "record_type": row.record_type,
                "source_obj_id": row.source_obj_id,
                "gds_no": row.gds_no,
                "title": row.title,
                "smry": row.smry,
                "nws_mrkt_ctgr_cd": row.nws_mrkt_ctgr_cd,
            })

        return results