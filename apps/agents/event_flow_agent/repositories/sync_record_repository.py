# apps/agents/event_flow_agent/repositories/sync_record_repository.py

from __future__ import annotations
from typing import Any
from sqlalchemy import text
from sqlalchemy.orm import Session
from apps.common.configs.database.sync_database.base import BaseSyncSQLRepository

class SyncRecordRepository(BaseSyncSQLRepository):
    """MI Record 원천 조회용 Repository."""

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def fetch_news_records(
        self,
        market_category: str = "LNG",
        limit: int = 50,
        from_first_created: str | None = None,
        to_first_created: str | None = None,
    ) -> list[dict[str, Any]]:
        where_clauses = [
            "r.record_type = 'NEWS'",
            "i.nws_mrkt_ctgr_cd = :market_category",
        ]
        params: dict[str, Any] = {
            "market_category": market_category,
            "limit": limit,
        }

        if from_first_created:
            where_clauses.append("r.first_created >= :from_first_created")
            params["from_first_created"] = from_first_created

        if to_first_created:
            where_clauses.append("r.first_created <= :to_first_created")
            params["to_first_created"] = to_first_created

        sql = f"""
        select
            r.mi_record_id,
            r.first_created,
            r.record_type,
            r.source_obj_id,
            g.gds_no,
            d.title,
            s.smry,
            i.nws_mrkt_ctgr_cd
        from tmd_mi_record as r
        join tmd_nws_smry as s
            on r.source_obj_id = s.nws_smry_id
           and r.record_type = 'NEWS'
        join tif_refinewsdatar as d
            on s.data_reg_sn = d.data_reg_sn
           and s.first_created = d.first_created
        join tmd_gdsm as g
            on g.gds_id = s.gds_id
        join tmd_nws_sig as i
            on s.nws_smry_id = i.nws_smry_id
        where {" and ".join(where_clauses)}
        order by r.first_created desc
        limit :limit
        """

        rows = self.session.execute(text(sql), params).mappings().all()
        return [dict(row) for row in rows]