"""
Scenario DB Repository 모듈

역할:
- tmm_mi_mievent_m에서 Base Event를 mi_event_id로 조회한다.
- 조회된 event를 sample_event JSON 형식과 동일하게 재구성한다.
- tmm_scenariom에 시나리오 pipeline 결과를 저장한다.

설계 의도:
- event_flow_agent의 SyncEventRepository 패턴을 동일하게 적용
- Repository 계층에서 SQL 실행만 담당하고, service 계층에서 트랜잭션 처리
- SELECT 결과를 pipeline이 사용할 dict 형태로 변환
- 신규 tmm_mi_mievent_m 스키마 반영 (정규화된 event_type, JSON key_bullets 등)
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text

from apps.common.configs.database.sync_database.base import BaseSyncSQLRepository


class SyncScenarioRepository(BaseSyncSQLRepository):
    def fetch_event_by_id(self, mi_event_id: int) -> dict[str, Any] | None:
        """tmm_mi_mievent_m에서 단일 Event를 mi_event_id로 조회.

        반환 형식은 sample_event_ev_2a58da7f4ff2.json과 동일한 dict 구조.
        """
        sql = """
        select
            e.mi_event_id,
            e.event_title,
            e.one_line_summary,
            e.key_bullets_json,
            e.event_summary,
            e.market_and_institution_view,
            e.occurred_at,
            e.probability,
            e.dedup_state,
            e.mi_event_status_code,
            e.tags_json,
            e.crt_dtm,
            l1.level_1_code,
            l1.level_1_label,
            l2.level_2_code,
            l2.level_2_label,
            l2.event_type_l2_id
        from tmm_mi_mievent_m e
        left join tmm_mi_event_type_l2_m l2 on e.event_type_l2_id = l2.event_type_l2_id
        left join tmm_mi_event_type_l1_m l1 on l2.event_type_l1_id = l1.event_type_l1_id
        where e.mi_event_id = :mi_event_id
          and e.del_yn = 'N'
        """
        row = self.session.execute(
            text(sql),
            {"mi_event_id": mi_event_id},
        ).mappings().one_or_none()

        if row is None:
            return None

        row_dict = dict(row)

        # key_bullets from JSON column (tmd_mievent_key_bulletsm migrated to JSON column)
        key_bullets = self._parse_key_bullets_from_json(row_dict.get("key_bullets_json"))

        # source_mi_record_ids from new mapping table
        source_record_ids = self._fetch_source_record_ids(mi_event_id)

        # tags 파싱
        tags = []
        raw_tags = row_dict.get("tags_json")
        if raw_tags:
            if isinstance(raw_tags, str):
                try:
                    tags = json.loads(raw_tags)
                except (json.JSONDecodeError, TypeError):
                    tags = []
            elif isinstance(raw_tags, list):
                tags = raw_tags

        # event dict 구성 (sample_event JSON 형식과 일치)
        return {
            "mi_event_id": str(row_dict["mi_event_id"]),
            "event_title_ko": row_dict["event_title"] or "",
            "one_line_summary": row_dict["one_line_summary"] or "",
            "key_bullets": key_bullets,
            "detail_analysis": row_dict["event_summary"] or "",
            "market_and_institution_view": row_dict["market_and_institution_view"] or "",
            "source_mi_record_ids": source_record_ids,
            "created_at": row_dict["crt_dtm"].isoformat() if row_dict.get("crt_dtm") else "",
            "updated_at": row_dict["crt_dtm"].isoformat() if row_dict.get("crt_dtm") else "",
            "event_type": {
                "level_1_code": row_dict.get("level_1_code") or "",
                "level_2_code": row_dict.get("level_2_code") or "",
            },
            "event_status": {
                "status_code": row_dict.get("mi_event_status_code") or "",
            },
            "dedup_state": row_dict.get("dedup_state") or "raw",
            "language": "ko",
            "occurred_at": row_dict["occurred_at"].isoformat() if row_dict.get("occurred_at") else "",
            "probability": row_dict.get("probability") or 0,
            "tags": tags,
        }

    def _parse_key_bullets_from_json(self, raw_json: Any) -> list[str]:
        """key_bullets_json JSON 컬럼에서 bullet 텍스트 리스트를 추출."""
        if raw_json is None:
            return []
        if isinstance(raw_json, list):
            return [str(item).strip() for item in raw_json if item]
        if isinstance(raw_json, str):
            try:
                parsed = json.loads(raw_json)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if item]
            except (json.JSONDecodeError, TypeError):
                pass
        return []

    def _fetch_source_record_ids(self, mi_event_id: int) -> list[int]:
        """tmm_mi_mievent_record_map에서 연결된 mi_record_id 리스트 조회."""
        sql = """
        select mi_record_id
        from tmm_mi_mievent_record_map
        where mi_event_id = :mi_event_id
        order by mi_record_id
        """
        rows = self.session.execute(
            text(sql),
            {"mi_event_id": mi_event_id},
        ).mappings().all()
        return [int(r["mi_record_id"]) for r in rows if r.get("mi_record_id")]

    def check_scenarios_exist(self, mi_event_id: int) -> bool:
        """tmm_scenariom에서 해당 mi_event_id에 시나리오가 이미 존재하는지 확인."""
        sql = """
        select count(*) as cnt
        from tmm_scenariom
        where mi_event_id = :mi_event_id
          and del_yn = 'N'
        """
        row = self.session.execute(
            text(sql),
            {"mi_event_id": mi_event_id},
        ).mappings().one()
        return int(row["cnt"]) > 0

    def insert_scenario(self, payload: dict) -> int:
        """tmm_scenariom에 시나리오 1건을 저장하고 PK(scenario_id)를 반환."""
        sql = """
        insert into tmm_scenariom (
            scenario_group_id,
            crt_usr_logn_id,
            mod_usr_logn_id,
            del_yn,
            name,
            description,
            mi_event_id,
            status_code,
            valid_from,
            valid_to,
            language,
            dimension_values,
            likelihood,
            price_direction
        ) values (
            :scenario_group_id,
            :crt_usr_logn_id,
            :mod_usr_logn_id,
            :del_yn,
            :name,
            :description,
            :mi_event_id,
            :status_code,
            :valid_from,
            :valid_to,
            :language,
            :dimension_values,
            :likelihood,
            :price_direction
        )
        """
        result = self.session.execute(text(sql), payload)
        return int(result.lastrowid)