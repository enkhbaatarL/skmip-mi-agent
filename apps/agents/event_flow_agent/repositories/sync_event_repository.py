#   apps/agents/event_flow_agent/repositories/sync_event_repository.py

from __future__ import annotations
from sqlalchemy import text
from apps.common.configs.database.sync_database.base import BaseSyncSQLRepository


class SyncEventRepository(BaseSyncSQLRepository):
    def insert_event(self, payload: dict) -> None:
        sql = """
        insert into tmm_mieventm (
            mi_event_id,
            crt_user_id,
            mod_user_id,
            del_yn,
            mi_event_title_ko,
            mi_event_summary_ko,
            estimated_impact_id,
            occurred_at,
            updated_at,
            probability,
            language,
            dedup_state,
            merged_into_mi_event_id,
            mi_event_type_l1_code,
            mi_event_type_l2_code,
            mi_event_status_code,
            signal_noise_label,
            signal_noise_confidence
        ) values (
            :mi_event_id,
            :crt_user_id,
            :mod_user_id,
            :del_yn,
            :mi_event_title_ko,
            :mi_event_summary_ko,
            :estimated_impact_id,
            :occurred_at,
            :updated_at,
            :probability,
            :language,
            :dedup_state,
            :merged_into_mi_event_id,
            :mi_event_type_l1_code,
            :mi_event_type_l2_code,
            :mi_event_status_code,
            :signal_noise_label,
            :signal_noise_confidence
        )
        """
        self.session.execute(text(sql), payload)