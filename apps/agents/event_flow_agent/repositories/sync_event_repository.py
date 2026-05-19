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

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from apps.agents.event_flow_agent.models.mi_event_models_orm import (
    MiEventModel,
    MiEventTypeL1Model,
    MiEventTypeL2Model,
)
from apps.common.configs.database.sync_database.base import BaseSyncSQLRepository


class SyncEventRepository(BaseSyncSQLRepository):
    def fetch_events(self, limit: int = 10) -> list[dict]:
        """최신 event 목록을 ORM으로 조회하여 dict 리스트로 반환."""
        stmt = (
            select(MiEventModel)
            .options(
                joinedload(MiEventModel.type_l2).joinedload(MiEventTypeL2Model.level_1)
            )
            .where(MiEventModel.del_yn == "N")
            .order_by(MiEventModel.crt_dtm.desc(), MiEventModel.mi_event_id.desc())
            .limit(limit)
        )
        rows = self.session.execute(stmt).scalars().all()

        return [self._event_to_dict(event) for event in rows]

    def insert_event(self, payload: dict) -> int:
        """ORM을 사용하여 event를 저장하고 PK를 반환."""
        event = MiEventModel(**payload)
        self.session.add(event)
        self.session.flush()
        return int(event.mi_event_id)

    def resolve_event_type_l2_id(self, level_1_code: str, level_2_code: str) -> int | None:
        """level_1_code와 level_2_code로 event_type_l2_id를 조회."""
        stmt = (
            select(MiEventTypeL2Model.event_type_l2_id)
            .join(MiEventTypeL1Model, MiEventTypeL2Model.event_type_l1_id == MiEventTypeL1Model.event_type_l1_id)
            .where(
                MiEventTypeL1Model.level_1_code == level_1_code,
                MiEventTypeL2Model.level_2_code == level_2_code,
                MiEventTypeL1Model.del_yn == "N",
                MiEventTypeL2Model.del_yn == "N",
            )
        )
        row = self.session.execute(stmt).one_or_none()
        if row is None:
            return None
        return int(row[0])

    @staticmethod
    def _event_to_dict(event: MiEventModel) -> dict:
        """ORM MiEventModel → dict 변환 (Service 계층으로 이동 가능)."""
        l2 = event.type_l2
        l1 = l2.level_1 if l2 else None

        return {
            "mi_event_id": event.mi_event_id,
            "crt_dtm": event.crt_dtm.isoformat() if event.crt_dtm else None,
            "event_title": event.event_title,
            "one_line_summary": event.one_line_summary or "",
            "event_summary": event.event_summary,
            "market_and_institution_view": event.market_and_institution_view or "",
            "occurred_at": event.occurred_at.isoformat() if event.occurred_at else None,
            "probability": float(event.probability) if event.probability else 0,
            "dedup_state": event.dedup_state,
            "mi_event_status_code": event.mi_event_status_code,
            "key_bullets_json": event.key_bullets_json,
            "tags_json": event.tags_json,
            "signal_yn": event.signal_yn,
            "signal_confidence": float(event.signal_confidence) if event.signal_confidence else 0,
            "signal_reason": event.signal_reason,
            "level_1_code": l1.level_1_code if l1 else None,
            "level_1_label": l1.level_1_label if l1 else None,
            "level_2_code": l2.level_2_code if l2 else None,
            "level_2_label": l2.level_2_label if l2 else None,
        }