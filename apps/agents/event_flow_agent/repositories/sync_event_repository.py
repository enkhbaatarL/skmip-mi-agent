#   apps/agents/event_flow_agent/repositories/sync_event_repository.py
#   kmj20260422수 수정
"""
event 저장/조회용 Repository 모듈

역할:
- 추출된 event를 tmm_mieventm 테이블에 저장한다.
- 저장된 event를 최신순으로 조회하여 후속 요약 단계에 전달한다.

입력:
- event 저장 payload
- 조회 건수 제한(limit)

출력:
- insert 결과 ID
- 저장된 event 목록(list[dict])

설계 의도:
- event 테이블 접근 SQL을 repository 계층으로 분리
- service는 트랜잭션과 payload 구성에 집중하고,
  repository는 insert/select SQL 실행만 담당
- 현재는 신규 로컬 midb 스키마에 맞춘 컬럼 구조를 사용
"""

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
            status_taxonomy_version,
            key_bullets,
            tags
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
            status_taxonomy_version,
            key_bullets,
            tags
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
            :status_taxonomy_version,
            :key_bullets,
            :tags
        )
        """
        result = self.session.execute(text(sql), payload)
        return int(result.lastrowid)