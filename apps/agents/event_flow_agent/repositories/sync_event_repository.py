#   apps/agents/event_flow_agent/repositories/sync_event_repository.py
#   kmj20260422수 수정
"""
event 저장/조회용 Repository 모듈

역할:
- 추출된 event를 tmm_mi_mievent_m 테이블에 저장한다.
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
- 신규 tmm_mi_mievent_m 스키마에 맞춘 컬럼 구조 사용
  (정규화된 event_type_l2_id FK, JSON key_bullets, signal 필드 등)
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import text

from apps.common.configs.database.sync_database.base import BaseSyncSQLRepository


class SyncEventRepository(BaseSyncSQLRepository):
    @staticmethod
    def _convert_row(row: dict) -> dict:
        """Convert Decimal values to float for JSON serialization."""
        return {
            k: float(v) if isinstance(v, Decimal) else v
            for k, v in row.items()
        }

    def fetch_events(self, limit: int = 10) -> list[dict]:
        sql = """
        select
            e.mi_event_id,
            e.crt_dtm,
            e.event_title,
            e.one_line_summary,
            e.event_summary,
            e.market_and_institution_view,
            e.occurred_at,
            e.probability,
            e.dedup_state,
            e.mi_event_status_code,
            e.key_bullets_json,
            e.tags_json,
            e.signal_yn,
            e.signal_confidence,
            e.signal_reason,
            l1.level_1_code,
            l1.level_1_label,
            l2.level_2_code,
            l2.level_2_label
        from tmm_mi_mievent_m e
        left join tmm_mi_event_type_l2_m l2 on e.event_type_l2_id = l2.event_type_l2_id
        left join tmm_mi_event_type_l1_m l1 on l2.event_type_l1_id = l1.event_type_l1_id
        where e.del_yn = 'N'
        order by e.crt_dtm desc, e.mi_event_id desc
        limit :limit
        """
        rows = self.session.execute(
            text(sql),
            {"limit": limit},
        ).mappings().all()
        return [self._convert_row(dict(row)) for row in rows]

    def insert_event(self, payload: dict) -> int:
        sql = """
        insert into tmm_mi_mievent_m (
            crt_usr_logn_id,
            mod_usr_logn_id,
            del_yn,
            event_title,
            one_line_summary,
            event_summary,
            market_and_institution_view,
            occurred_at,
            probability,
            dedup_state,
            mi_event_status_code,
            key_bullets_json,
            tags_json,
            event_type_l2_id,
            signal_yn,
            signal_confidence,
            signal_reason
        ) values (
            :crt_usr_logn_id,
            :mod_usr_logn_id,
            :del_yn,
            :event_title,
            :one_line_summary,
            :event_summary,
            :market_and_institution_view,
            :occurred_at,
            :probability,
            :dedup_state,
            :mi_event_status_code,
            :key_bullets_json,
            :tags_json,
            :event_type_l2_id,
            :signal_yn,
            :signal_confidence,
            :signal_reason
        )
        """
        result = self.session.execute(text(sql), payload)
        return int(result.lastrowid)

    def resolve_event_type_l2_id(self, level_1_code: str, level_2_code: str) -> int | None:
        """level_1_code와 level_2_code로 event_type_l2_id를 조회."""
        sql = """
        select l2.event_type_l2_id
        from tmm_mi_event_type_l2_m l2
        join tmm_mi_event_type_l1_m l1 on l2.event_type_l1_id = l1.event_type_l1_id
        where l1.level_1_code = :level_1_code
          and l2.level_2_code = :level_2_code
          and l1.del_yn = 'N'
          and l2.del_yn = 'N'
        """
        row = self.session.execute(
            text(sql),
            {"level_1_code": level_1_code, "level_2_code": level_2_code},
        ).mappings().one_or_none()
        if row is None:
            return None
        return int(row["event_type_l2_id"])