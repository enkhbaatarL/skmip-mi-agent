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

from sqlalchemy import select, exists
from sqlalchemy.orm import joinedload

from apps.agents.event_flow_agent.models.mi_event_models_orm import (
    MiEventModel,
    MiEventTypeL1Model,
    MiEventTypeL2Model,
    MiEventRecordMapModel,
)
from apps.agents.scenario_flow_agent.models.scenario_models_orm import ScenarioModel
from apps.common.configs.database.sync_database.base import BaseSyncSQLRepository


class SyncScenarioRepository(BaseSyncSQLRepository):
    def fetch_event_by_id(self, mi_event_id: int) -> dict[str, Any] | None:
        """tmm_mi_mievent_m에서 단일 Event를 mi_event_id로 ORM 조회.

        반환 형식은 sample_event_ev_2a58da7f4ff2.json과 동일한 dict 구조.
        """
        stmt = (
            select(MiEventModel)
            .options(
                joinedload(MiEventModel.type_l2).joinedload(MiEventTypeL2Model.level_1),
                joinedload(MiEventModel.record_maps),
            )
            .where(
                MiEventModel.mi_event_id == mi_event_id,
                MiEventModel.del_yn == "N",
            )
        )
        event = self.session.execute(stmt).scalars().unique().one_or_none()

        if event is None:
            return None

        return self._event_to_sample_dict(event)

    def check_scenarios_exist(self, mi_event_id: int) -> bool:
        """tmm_scenariom에서 해당 mi_event_id에 시나리오가 이미 존재하는지 확인."""
        stmt = select(
            exists().where(
                ScenarioModel.mi_event_id == mi_event_id,
                ScenarioModel.del_yn == "N",
            )
        )
        return bool(self.session.execute(stmt).scalar())

    def insert_scenario(self, payload: dict) -> int:
        """tmm_scenariom에 시나리오 1건을 저장하고 PK(scenario_id)를 반환."""
        scenario = ScenarioModel(**payload)
        self.session.add(scenario)
        self.session.flush()
        return int(scenario.scenario_id)

    def _fetch_source_record_ids(self, mi_event_id: int) -> list[int]:
        """tmm_mi_mievent_record_map에서 연결된 mi_record_id 리스트 조회."""
        stmt = (
            select(MiEventRecordMapModel.mi_record_id)
            .where(MiEventRecordMapModel.mi_event_id == mi_event_id)
            .order_by(MiEventRecordMapModel.mi_record_id)
        )
        rows = self.session.execute(stmt).all()
        return [int(r[0]) for r in rows if r[0]]

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

    def _event_to_sample_dict(self, event: MiEventModel) -> dict[str, Any]:
        """ORM MiEventModel → sample_event JSON dict 변환."""
        l2 = event.type_l2
        l1 = l2.level_1 if l2 else None

        key_bullets = self._parse_key_bullets_from_json(event.key_bullets_json)

        source_record_ids = [rm.mi_record_id for rm in event.record_maps]

        # tags 파싱
        tags: list[str] = []
        raw_tags = event.tags_json
        if raw_tags:
            if isinstance(raw_tags, str):
                try:
                    tags = json.loads(raw_tags)
                except (json.JSONDecodeError, TypeError):
                    tags = []
            elif isinstance(raw_tags, list):
                tags = raw_tags

        return {
            "mi_event_id": str(event.mi_event_id),
            "event_title_ko": event.event_title or "",
            "one_line_summary": event.one_line_summary or "",
            "key_bullets": key_bullets,
            "detail_analysis": event.event_summary or "",
            "market_and_institution_view": event.market_and_institution_view or "",
            "source_mi_record_ids": source_record_ids,
            "created_at": event.crt_dtm.isoformat() if event.crt_dtm else "",
            "updated_at": event.crt_dtm.isoformat() if event.crt_dtm else "",
            "event_type": {
                "level_1_code": l1.level_1_code if l1 else "",
                "level_2_code": l2.level_2_code if l2 else "",
            },
            "event_status": {
                "status_code": event.mi_event_status_code or "",
            },
            "dedup_state": event.dedup_state or "raw",
            "language": "ko",
            "occurred_at": event.occurred_at.isoformat() if event.occurred_at else "",
            "probability": float(event.probability) if event.probability else 0,
            "tags": tags,
        }