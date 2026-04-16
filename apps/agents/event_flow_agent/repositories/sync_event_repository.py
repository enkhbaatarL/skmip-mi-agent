from __future__ import annotations

from sqlalchemy import text

from apps.common.configs.database.sync_database.base import BaseSyncSQLRepository


class SyncEventRepository(BaseSyncSQLRepository):
    def fetch_events(self, limit: int = 10) -> list[dict]:
        query = text("""
            SELECT
                mi_event_id AS id,
                mi_event_title_ko AS title,
                mi_event_summary_ko AS content,
                crt_dtm AS created_at
            FROM tmm_mieventm
            WHERE del_yn = 'N'
            ORDER BY crt_dtm DESC
            LIMIT :limit
        """)

        result = self.session.execute(query, {"limit": limit})
        return [dict(row._mapping) for row in result]