#   apps/agents/event_flow_agent/repositories/sync_event_repository.py
#   kmj20260422수 수정

from __future__ import annotations

from sqlalchemy import text

from apps.common.configs.database.sync_database.base import BaseSyncSQLRepository


class SyncEventRepository(BaseSyncSQLRepository):
    def fetch_events(self, limit: int = 10) -> list[dict]:
        sql = """
        select
            mi_event_id,
            first_created,
            crt_dtm,
            event_title_ko,
            one_line_summary,
            detail_analysis,
            market_and_institution_view,
            occurred_at,
            probability,
            language,
            dedup_state,
            level_1_code,
            level_2_code,
            taxonomy_version,
            status_code,
            status_label_ko,
            status_taxonomy_version
        from tmm_mieventm
        where del_yn = 'N'
        order by first_created desc, mi_event_id desc
        limit :limit
        """
        rows = self.session.execute(
            text(sql),
            {"limit": limit},
        ).mappings().all()
        return [dict(row) for row in rows]

    def insert_event(self, payload: dict) -> int:
        sql = """
        insert into tmm_mieventm (
            first_created,
            crt_usr_logn_id,
            mod_usr_logn_id,
            del_yn,
            event_title_ko,
            one_line_summary,
            detail_analysis,
            market_and_institution_view,
            language,
            occurred_at,
            probability,
            dedup_state,
            level_1_code,
            level_2_code,
            taxonomy_version,
            status_code,
            status_label_ko,
            status_taxonomy_version
        ) values (
            :first_created,
            :crt_usr_logn_id,
            :mod_usr_logn_id,
            :del_yn,
            :event_title_ko,
            :one_line_summary,
            :detail_analysis,
            :market_and_institution_view,
            :language,
            :occurred_at,
            :probability,
            :dedup_state,
            :level_1_code,
            :level_2_code,
            :taxonomy_version,
            :status_code,
            :status_label_ko,
            :status_taxonomy_version
        )
        """
        result = self.session.execute(text(sql), payload)
        return int(result.lastrowid)